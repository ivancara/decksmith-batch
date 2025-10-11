"""
DeckSmith Batch Processing System
Application Layer - Archidekt Scraping Use Case

Use case principal para orquestrar o processo de scraping do Archidekt.
Segue Clean Architecture e SOLID principles.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...domain.entities import Card, Deck, DeckCard, ScrapingSession, ScrapingStatus
from ...domain.repositories import ICardRepository, IDeckRepository, IScrapingSessionRepository
from ...infrastructure.scraping.archidekt_scraping_service import ArchidektScrapingService, ArchidektAPIError


class ArchidektScrapingUseCase:
    """
    Use case para coordenar o scraping de dados do Archidekt.
    Responsável por orquestrar serviços de scraping e persistência.
    """
    
    def __init__(self,
                 card_repository: ICardRepository,
                 deck_repository: IDeckRepository,
                 session_repository: IScrapingSessionRepository,
                 scraping_service: ArchidektScrapingService):
        self.card_repository = card_repository
        self.deck_repository = deck_repository
        self.session_repository = session_repository
        self.scraping_service = scraping_service
        self.logger = logging.getLogger(__name__)
    
    async def execute_scraping_session(self,
                                     max_pages: int = 10,
                                     format_filter: Optional[str] = None,
                                     featured_only: bool = False,
                                     update_existing: bool = False) -> UUID:
        """
        Executa uma sessão completa de scraping do Archidekt.
        
        Args:
            max_pages: Número máximo de páginas para buscar
            format_filter: Filtro por formato específico
            featured_only: Apenas decks em destaque
            update_existing: Se deve atualizar decks existentes
            
        Returns:
            UUID da sessão de scraping criada
        """
        # Criar sessão de scraping
        session = ScrapingSession(
            source="archidekt",
            configuration={
                "max_pages": max_pages,
                "format_filter": format_filter,
                "featured_only": featured_only,
                "update_existing": update_existing
            }
        )
        
        await self.session_repository.save(session)
        self.logger.info(f"Started scraping session {session.id}")
        
        try:
            # Iniciar sessão
            session.start()
            await self.session_repository.save(session)
            
            # Executar scraping
            await self._execute_scraping_process(session, max_pages, format_filter, featured_only, update_existing)
            
            # Finalizar com sucesso
            session.mark_completed()
            self.logger.info(f"Scraping session {session.id} completed successfully")
            
        except Exception as e:
            # Finalizar com erro
            session.mark_failed(str(e))
            self.logger.error(f"Scraping session {session.id} failed: {e}")
            raise
        
        finally:
            await self.session_repository.save(session)
        
        return session.id
    
    async def _execute_scraping_process(self,
                                      session: ScrapingSession,
                                      max_pages: int,
                                      format_filter: Optional[str],
                                      featured_only: bool,
                                      update_existing: bool) -> None:
        """Executa o processo principal de scraping"""
        
        processed_decks = 0
        saved_decks = 0
        saved_cards = 0
        errors = []
        
        try:
            async with self.scraping_service:
                self.logger.info(f"Starting deck search with max_pages={max_pages}, format={format_filter}")
                
                # Buscar decks
                async for deck_basic_info in self.scraping_service.search_decks(
                    format_filter=format_filter,
                    featured_only=featured_only,
                    max_pages=max_pages
                ):
                    try:
                        processed_decks += 1
                        
                        # Verificar se deck já existe
                        archidekt_id = deck_basic_info.get('archidekt_id')
                        if not archidekt_id:
                            self.logger.warning("Deck without archidekt_id, skipping")
                            continue
                        
                        existing_deck = await self.deck_repository.find_by_archidekt_id(archidekt_id)
                        if existing_deck and not update_existing:
                            self.logger.debug(f"Deck {archidekt_id} already exists, skipping")
                            continue
                        
                        # Obter detalhes completos do deck
                        deck_details = await self.scraping_service.get_deck_details(archidekt_id)
                        if not deck_details:
                            self.logger.warning(f"Could not get details for deck {archidekt_id}")
                            continue
                        
                        # Processar e salvar deck com cartas
                        deck_entity, cards_count = await self._process_and_save_deck(deck_details)
                        if deck_entity:
                            saved_decks += 1
                            saved_cards += cards_count
                            
                            # Atualizar progresso da sessão
                            session.update_progress(
                                pages_scraped=processed_decks // 20 + 1,  # Aproximadamente 20 decks por página
                                decks_found=processed_decks,
                                cards_found=saved_cards
                            )
                            
                            self.logger.info(f"Saved deck: {deck_entity.name} ({cards_count} cards)")
                        
                        # Rate limiting entre decks
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        error_msg = f"Error processing deck {deck_basic_info.get('archidekt_id', 'unknown')}: {e}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                        session.add_error(error_msg)
                        
                        # Continuar com próximo deck em caso de erro
                        continue
        
        except Exception as e:
            self.logger.error(f"Fatal error in scraping process: {e}")
            raise
        
        # Atualizar estatísticas finais da sessão
        session.decks_found = processed_decks
        session.decks_saved = saved_decks
        session.cards_saved = saved_cards
        
        self.logger.info(f"Scraping completed: {saved_decks}/{processed_decks} decks saved, {saved_cards} cards")
    
    async def _process_and_save_deck(self, deck_data: Dict[str, Any]) -> tuple[Optional[Deck], int]:
        """
        Processa dados de um deck e salva no banco.
        
        Returns:
            Tupla com (deck_entity, cards_count)
        """
        try:
            # Criar entidade Deck
            deck = Deck.create_from_archidekt(
                name=deck_data['name'],
                archidekt_id=deck_data['archidekt_id'],
                archidekt_url=deck_data['url'],
                format=deck_data.get('format'),
                description=deck_data.get('description', ''),
                owner_name=deck_data.get('owner_name'),
                is_public=deck_data.get('is_public', True),
                view_count=deck_data.get('view_count', 0),
                like_count=deck_data.get('like_count', 0)
            )
            
            # Processar cartas do deck
            cards_saved = 0
            for card_data in deck_data.get('cards', []):
                try:
                    # Processar carta
                    card_entity = await self._process_card(card_data)
                    if card_entity:
                        # Adicionar carta ao deck
                        deck.add_card(
                            card_id=card_entity.id,
                            quantity=card_data.get('quantity', 1),
                            category=card_data.get('category', 'main')
                        )
                        cards_saved += 1
                
                except Exception as e:
                    self.logger.error(f"Error processing card {card_data.get('name', 'unknown')}: {e}")
                    continue
            
            # Salvar deck
            await self.deck_repository.save(deck)
            
            self.logger.debug(f"Processed deck: {deck.name} with {cards_saved} cards")
            return deck, cards_saved
            
        except Exception as e:
            self.logger.error(f"Error processing deck {deck_data.get('name', 'unknown')}: {e}")
            return None, 0
    
    async def _process_card(self, card_data: Dict[str, Any]) -> Optional[Card]:
        """
        Processa dados de uma carta e salva no banco se necessário.
        
        Returns:
            Entidade Card ou None se houve erro
        """
        try:
            card_name = card_data.get('name', '').strip()
            if not card_name:
                return None
            
            # Verificar se carta já existe por nome
            existing_card = await self.card_repository.find_by_name(card_name)
            if existing_card:
                # Atualizar dados se necessário (Archidekt ID, preços, etc.)
                if card_data.get('archidekt_id') and not existing_card.archidekt_id:
                    existing_card.archidekt_id = card_data['archidekt_id']
                    await self.card_repository.save(existing_card)
                return existing_card
            
            # Verificar por Archidekt ID
            archidekt_id = card_data.get('archidekt_id')
            if archidekt_id:
                existing_card = await self.card_repository.find_by_archidekt_id(archidekt_id)
                if existing_card:
                    return existing_card
            
            # Criar nova carta
            card = Card.create_from_archidekt(
                name=card_name,
                mana_cost=card_data.get('mana_cost', ''),
                type_line=card_data.get('type_line', ''),
                oracle_text=card_data.get('oracle_text', ''),
                power=card_data.get('power'),
                toughness=card_data.get('toughness'),
                colors=card_data.get('colors', []),
                rarity=card_data.get('rarity'),
                set_code=card_data.get('set_code', ''),
                archidekt_id=archidekt_id
            )
            
            # Adicionar dados específicos do Archidekt
            if card_data.get('set_name'):
                card.set_name = card_data['set_name']
            if card_data.get('collector_number'):
                card.collector_number = card_data['collector_number']
            if card_data.get('image_uri'):
                card.image_uri = card_data['image_uri']
            if card_data.get('loyalty'):
                card.loyalty = card_data['loyalty']
            
            # Salvar carta
            await self.card_repository.save(card)
            
            self.logger.debug(f"Saved new card: {card.name}")
            return card
            
        except Exception as e:
            self.logger.error(f"Error processing card {card_data.get('name', 'unknown')}: {e}")
            return None
    
    async def get_session_status(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Obtém status detalhado de uma sessão de scraping.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dict com dados da sessão ou None se não encontrada
        """
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            return None
        
        duration = session.get_duration_seconds()
        
        return {
            "id": str(session.id),
            "source": session.source,
            "status": session.status.value,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_seconds": duration,
            "pages_scraped": session.pages_scraped,
            "decks_found": session.decks_found,
            "decks_saved": session.decks_saved,
            "cards_found": session.cards_found,
            "cards_saved": session.cards_saved,
            "errors_count": len(session.errors),
            "errors": session.errors[-5:],  # Últimos 5 erros
            "configuration": session.configuration
        }
    
    async def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém sessões recentes de scraping.
        
        Args:
            limit: Número máximo de sessões
            
        Returns:
            Lista com dados das sessões
        """
        sessions = await self.session_repository.find_recent_sessions(limit)
        
        results = []
        for session in sessions:
            duration = session.get_duration_seconds()
            
            results.append({
                "id": str(session.id),
                "source": session.source,
                "status": session.status.value,
                "start_time": session.start_time.isoformat(),
                "duration_seconds": duration,
                "decks_found": session.decks_found,
                "decks_saved": session.decks_saved,
                "cards_saved": session.cards_saved,
                "success_rate": (session.decks_saved / session.decks_found * 100) if session.decks_found > 0 else 0
            })
        
        return results