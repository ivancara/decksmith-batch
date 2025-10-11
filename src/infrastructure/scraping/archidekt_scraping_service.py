"""
DeckSmith Batch Processing System
Infrastructure Layer - Archidekt Scraping Service

Serviço responsável por fazer scraping de dados do Archidekt.
Implementa SOLID principles e Clean Architecture.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import re

from ...domain.entities import Card, Deck, DeckCard


class ArchidektAPIError(Exception):
    """Exceção para erros da API do Archidekt"""
    pass


class ArchidektRateLimitError(ArchidektAPIError):
    """Exceção para rate limiting"""
    pass


class ArchidektScrapingService:
    """
    Serviço para scraping de dados do Archidekt.
    Segue Single Responsibility Principle e Interface Segregation.
    """
    
    def __init__(self, 
                 delay_between_requests: float = 1.0,
                 max_retries: int = 3,
                 timeout: int = 30):
        self.base_url = "https://archidekt.com"
        self.api_base_url = "https://archidekt.com/api"
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers para simular navegador
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Inicializa o serviço de scraping"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        
        self.logger.info("Archidekt scraping service initialized")
    
    async def close(self):
        """Fecha recursos do serviço"""
        if self.session:
            await self.session.close()
        self.logger.info("Archidekt scraping service closed")
    
    async def search_decks(self, 
                          format_filter: Optional[str] = None,
                          color_filter: Optional[List[str]] = None,
                          featured_only: bool = False,
                          max_pages: int = 10) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Busca decks no Archidekt com filtros específicos.
        
        Args:
            format_filter: Filtro por formato (Commander, Standard, etc.)
            color_filter: Filtro por cores ['W', 'U', 'B', 'R', 'G']
            featured_only: Apenas decks em destaque
            max_pages: Número máximo de páginas para buscar
            
        Yields:
            Dict com dados básicos do deck
        """
        if not self.session:
            await self.initialize()
        
        if not self.session:
            raise ArchidektAPIError("Failed to initialize session")
        
        page = 1
        total_decks_found = 0
        
        while page <= max_pages:
            try:
                self.logger.info(f"Searching decks page {page}/{max_pages}")
                
                # Construir URL de busca
                search_url = self._build_search_url(
                    page=page,
                    format_filter=format_filter,
                    color_filter=color_filter,
                    featured_only=featured_only
                )
                
                # Fazer requisição
                async with self.session.get(search_url) as response:
                    if response.status == 429:
                        self.logger.warning("Rate limited, waiting...")
                        await asyncio.sleep(5)
                        continue
                    
                    response.raise_for_status()
                    data = await response.json()
                
                # Processar resultados
                decks = data.get('results', [])
                if not decks:
                    self.logger.info("No more decks found, stopping search")
                    break
                
                for deck_data in decks:
                    deck_info = self._extract_deck_basic_info(deck_data)
                    if deck_info:
                        total_decks_found += 1
                        yield deck_info
                
                # Rate limiting
                await asyncio.sleep(self.delay_between_requests)
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error searching decks page {page}: {e}")
                if page == 1:  # Se falhou na primeira página, reraiser
                    raise
                break  # Para outras páginas, apenas para a busca
        
        self.logger.info(f"Search completed. Found {total_decks_found} decks across {page-1} pages")
    
    async def get_deck_details(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes completos de um deck específico.
        
        Args:
            deck_id: ID do deck no Archidekt
            
        Returns:
            Dict com dados completos do deck ou None se não encontrado
        """
        if not self.session:
            await self.initialize()
        
        if not self.session:
            raise ArchidektAPIError("Failed to initialize session")
        
        for attempt in range(self.max_retries):
            try:
                url = f"{self.api_base_url}/decks/{deck_id}/"
                
                async with self.session.get(url) as response:
                    if response.status == 404:
                        self.logger.warning(f"Deck {deck_id} not found")
                        return None
                    
                    if response.status == 429:
                        wait_time = (attempt + 1) * 2
                        self.logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    deck_data = await response.json()
                
                # Processar dados do deck
                processed_deck = await self._process_deck_details(deck_data)
                
                self.logger.debug(f"Retrieved details for deck {deck_id}: {processed_deck.get('name', 'Unknown')}")
                return processed_deck
                
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error getting deck {deck_id} (attempt {attempt+1}): {e}")
                if attempt == self.max_retries - 1:
                    raise ArchidektAPIError(f"Failed to get deck {deck_id} after {self.max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                self.logger.error(f"Unexpected error getting deck {deck_id}: {e}")
                raise
        
        return None
    
    async def get_popular_decks(self, 
                               format_filter: Optional[str] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca decks populares ordenados por views/likes.
        
        Args:
            format_filter: Filtro por formato
            limit: Número máximo de decks
            
        Returns:
            Lista de dados básicos dos decks populares
        """
        decks = []
        
        # Buscar com ordenação por popularidade
        async for deck in self.search_decks(
            format_filter=format_filter,
            max_pages=max(1, limit // 20)  # Aproximadamente 20 decks por página
        ):
            decks.append(deck)
            if len(decks) >= limit:
                break
        
        # Ordenar por popularidade (views + likes)
        decks.sort(key=lambda d: d.get('view_count', 0) + d.get('like_count', 0) * 2, reverse=True)
        
        return decks[:limit]
    
    def _build_search_url(self, 
                         page: int = 1,
                         format_filter: Optional[str] = None,
                         color_filter: Optional[List[str]] = None,
                         featured_only: bool = False) -> str:
        """Constrói URL de busca com filtros"""
        params = {
            'page': page,
            'pageSize': 20,
            'orderBy': '-updatedAt'  # Ordenar por mais recentes
        }
        
        if format_filter:
            params['formats'] = format_filter
        
        if color_filter:
            params['colors'] = ','.join(color_filter)
        
        if featured_only:
            params['featured'] = 'true'
        
        # Construir query string
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{self.api_base_url}/decks/?{query_string}"
    
    def _extract_deck_basic_info(self, deck_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrai informações básicas de um deck da API"""
        try:
            return {
                'archidekt_id': str(deck_data.get('id')),
                'name': deck_data.get('name', '').strip(),
                'description': deck_data.get('description', '').strip(),
                'format': deck_data.get('format', {}).get('name') if deck_data.get('format') else None,
                'owner_name': deck_data.get('owner', {}).get('username') if deck_data.get('owner') else None,
                'is_public': deck_data.get('visibility') == 0,  # 0 = público
                'is_featured': deck_data.get('featured', False),
                'view_count': deck_data.get('viewCount', 0),
                'like_count': deck_data.get('likeCount', 0),
                'created_at': deck_data.get('createdAt'),
                'updated_at': deck_data.get('updatedAt'),
                'url': f"{self.base_url}/decks/{deck_data.get('id')}/",
                'card_count': len(deck_data.get('cards', [])),
                'color_identity': self._extract_color_identity(deck_data)
            }
        except Exception as e:
            self.logger.error(f"Error extracting basic deck info: {e}")
            return None
    
    async def _process_deck_details(self, deck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados completos de um deck"""
        try:
            basic_info = self._extract_deck_basic_info(deck_data)
            if not basic_info:
                raise ValueError("Failed to extract basic deck info")
            
            # Extrair cartas do deck
            cards_data = []
            for card_entry in deck_data.get('cards', []):
                card_info = await self._process_card_entry(card_entry)
                if card_info:
                    cards_data.append(card_info)
            
            # Calcular estatísticas
            main_deck_size = sum(card['quantity'] for card in cards_data if card['category'] == 'main')
            sideboard_size = sum(card['quantity'] for card in cards_data if card['category'] == 'sideboard')
            
            # Calcular CMC médio
            total_cmc = sum(card['converted_mana_cost'] * card['quantity'] 
                           for card in cards_data if card['category'] == 'main')
            avg_cmc = total_cmc / main_deck_size if main_deck_size > 0 else 0
            
            # Adicionar dados processados
            basic_info.update({
                'cards': cards_data,
                'total_cards': len(cards_data),
                'main_deck_size': main_deck_size,
                'sideboard_size': sideboard_size,
                'average_cmc': round(avg_cmc, 2),
                'color_identity': self._calculate_deck_color_identity(cards_data)
            })
            
            return basic_info
            
        except Exception as e:
            self.logger.error(f"Error processing deck details: {e}")
            raise
    
    async def _process_card_entry(self, card_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processa entrada de carta do deck"""
        try:
            card_data = card_entry.get('card', {})
            if not card_data:
                return None
            
            # Determinar categoria da carta
            category = 'main'
            categories = card_entry.get('categories', [])
            if any(cat.get('name') == 'Sideboard' for cat in categories):
                category = 'sideboard'
            elif any(cat.get('name') == 'Commander' for cat in categories):
                category = 'commander'
            elif any(cat.get('name') == 'Companion' for cat in categories):
                category = 'companion'
            
            # Processar dados da carta
            colors = []
            if card_data.get('colors'):
                colors = [color['symbol'] for color in card_data['colors']]
            
            # Extrair informações básicas
            card_info = {
                'archidekt_id': str(card_data.get('uid', '')),
                'name': card_data.get('oracleCard', {}).get('name', '').strip(),
                'mana_cost': card_data.get('oracleCard', {}).get('manaCost', ''),
                'converted_mana_cost': card_data.get('oracleCard', {}).get('convertedManaCost', 0),
                'type_line': card_data.get('oracleCard', {}).get('typeLine', ''),
                'oracle_text': card_data.get('oracleCard', {}).get('oracleText', ''),
                'colors': colors,
                'rarity': card_data.get('rarity', {}).get('name', '').lower() if card_data.get('rarity') else None,
                'set_code': card_data.get('edition', {}).get('editioncode', ''),
                'set_name': card_data.get('edition', {}).get('name', ''),
                'collector_number': card_data.get('collectorNumber', ''),
                'quantity': card_entry.get('quantity', 1),
                'category': category,
                'image_uri': self._extract_image_uri(card_data),
                'power': card_data.get('oracleCard', {}).get('power'),
                'toughness': card_data.get('oracleCard', {}).get('toughness'),
                'loyalty': card_data.get('oracleCard', {}).get('loyalty')
            }
            
            return card_info
            
        except Exception as e:
            self.logger.error(f"Error processing card entry: {e}")
            return None
    
    def _extract_color_identity(self, deck_data: Dict[str, Any]) -> List[str]:
        """Extrai identidade de cor do deck"""
        colors = set()
        
        for card_entry in deck_data.get('cards', []):
            card_data = card_entry.get('card', {})
            if card_data.get('colors'):
                for color in card_data['colors']:
                    colors.add(color.get('symbol', ''))
        
        return sorted(list(colors))
    
    def _calculate_deck_color_identity(self, cards_data: List[Dict[str, Any]]) -> List[str]:
        """Calcula identidade de cor baseada nas cartas"""
        colors = set()
        
        for card in cards_data:
            if card.get('colors'):
                colors.update(card['colors'])
        
        return sorted(list(colors))
    
    def _extract_image_uri(self, card_data: Dict[str, Any]) -> Optional[str]:
        """Extrai URI da imagem da carta"""
        try:
            images = card_data.get('oracleCard', {}).get('images', {})
            if images:
                # Preferir imagem normal, depois small
                return images.get('normal') or images.get('small')
        except:
            pass
        return None
    
    def _normalize_mana_cost(self, mana_cost: str) -> str:
        """Normaliza custo de mana para formato padrão"""
        if not mana_cost:
            return ""
        
        # Remove espaços e normaliza formato
        normalized = re.sub(r'\s+', '', mana_cost)
        # Converte {X} para formato padrão se necessário
        normalized = re.sub(r'\{(\w+)\}', r'{\1}', normalized)
        
        return normalized