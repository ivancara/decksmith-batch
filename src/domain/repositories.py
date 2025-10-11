"""
DeckSmith Batch Processing System
Domain Layer - Repository Interfaces

Interfaces dos repositórios seguindo o padrão Repository e DDD.
Define contratos para persistência sem dependência de infraestrutura.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from .entities import Card, Deck, ScrapingSession


class ICardRepository(ABC):
    """Interface do repositório de cartas"""
    
    @abstractmethod
    async def save(self, card: Card) -> None:
        """Salva uma carta"""
        pass
    
    @abstractmethod
    async def find_by_id(self, card_id: UUID) -> Optional[Card]:
        """Busca carta por ID"""
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Card]:
        """Busca carta por nome"""
        pass
    
    @abstractmethod
    async def find_by_archidekt_id(self, archidekt_id: str) -> Optional[Card]:
        """Busca carta por ID do Archidekt"""
        pass
    
    @abstractmethod
    async def find_by_scryfall_id(self, scryfall_id: str) -> Optional[Card]:
        """Busca carta por ID do Scryfall"""
        pass
    
    @abstractmethod
    async def search_by_name(self, name_pattern: str, limit: int = 50) -> List[Card]:
        """Busca cartas por padrão no nome"""
        pass
    
    @abstractmethod
    async def find_by_set(self, set_code: str) -> List[Card]:
        """Busca cartas por código do set"""
        pass
    
    @abstractmethod
    async def find_by_colors(self, colors: List[str]) -> List[Card]:
        """Busca cartas por cores"""
        pass
    
    @abstractmethod
    async def find_by_rarity(self, rarity: str) -> List[Card]:
        """Busca cartas por raridade"""
        pass
    
    @abstractmethod
    async def exists_by_name(self, name: str) -> bool:
        """Verifica se carta existe por nome"""
        pass
    
    @abstractmethod
    async def count_total(self) -> int:
        """Conta total de cartas"""
        pass
    
    @abstractmethod
    async def find_recent(self, limit: int = 100) -> List[Card]:
        """Busca cartas mais recentes"""
        pass
    
    @abstractmethod
    async def delete(self, card_id: UUID) -> bool:
        """Remove uma carta"""
        pass


class IDeckRepository(ABC):
    """Interface do repositório de decks"""
    
    @abstractmethod
    async def save(self, deck: Deck) -> None:
        """Salva um deck"""
        pass
    
    @abstractmethod
    async def find_by_id(self, deck_id: UUID) -> Optional[Deck]:
        """Busca deck por ID"""
        pass
    
    @abstractmethod
    async def find_by_archidekt_id(self, archidekt_id: str) -> Optional[Deck]:
        """Busca deck por ID do Archidekt"""
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> List[Deck]:
        """Busca decks por nome"""
        pass
    
    @abstractmethod
    async def find_by_format(self, format: str) -> List[Deck]:
        """Busca decks por formato"""
        pass
    
    @abstractmethod
    async def find_by_owner(self, owner_name: str) -> List[Deck]:
        """Busca decks por proprietário"""
        pass
    
    @abstractmethod
    async def find_by_colors(self, colors: List[str]) -> List[Deck]:
        """Busca decks por identidade de cor"""
        pass
    
    @abstractmethod
    async def find_public_decks(self, limit: int = 100) -> List[Deck]:
        """Busca decks públicos"""
        pass
    
    @abstractmethod
    async def find_featured_decks(self, limit: int = 50) -> List[Deck]:
        """Busca decks em destaque"""
        pass
    
    @abstractmethod
    async def find_popular_decks(self, limit: int = 100) -> List[Deck]:
        """Busca decks populares (ordenados por views/likes)"""
        pass
    
    @abstractmethod
    async def find_recent(self, limit: int = 100) -> List[Deck]:
        """Busca decks mais recentes"""
        pass
    
    @abstractmethod
    async def exists_by_archidekt_id(self, archidekt_id: str) -> bool:
        """Verifica se deck existe por ID do Archidekt"""
        pass
    
    @abstractmethod
    async def count_total(self) -> int:
        """Conta total de decks"""
        pass
    
    @abstractmethod
    async def count_by_format(self, format: str) -> int:
        """Conta decks por formato"""
        pass
    
    @abstractmethod
    async def find_decks_with_card(self, card_id: UUID) -> List[Deck]:
        """Busca decks que contêm uma carta específica"""
        pass
    
    @abstractmethod
    async def get_deck_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais dos decks"""
        pass
    
    @abstractmethod
    async def delete(self, deck_id: UUID) -> bool:
        """Remove um deck"""
        pass


class IScrapingSessionRepository(ABC):
    """Interface do repositório de sessões de scraping"""
    
    @abstractmethod
    async def save(self, session: ScrapingSession) -> None:
        """Salva uma sessão de scraping"""
        pass
    
    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> Optional[ScrapingSession]:
        """Busca sessão por ID"""
        pass
    
    @abstractmethod
    async def find_active_sessions(self) -> List[ScrapingSession]:
        """Busca sessões ativas (running)"""
        pass
    
    @abstractmethod
    async def find_completed_sessions(self, limit: int = 50) -> List[ScrapingSession]:
        """Busca sessões completadas"""
        pass
    
    @abstractmethod
    async def find_failed_sessions(self, limit: int = 50) -> List[ScrapingSession]:
        """Busca sessões com falha"""
        pass
    
    @abstractmethod
    async def find_recent_sessions(self, limit: int = 20) -> List[ScrapingSession]:
        """Busca sessões mais recentes"""
        pass
    
    @abstractmethod
    async def find_by_source(self, source: str) -> List[ScrapingSession]:
        """Busca sessões por fonte (archidekt, etc)"""
        pass
    
    @abstractmethod
    async def find_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ScrapingSession]:
        """Busca sessões por período"""
        pass
    
    @abstractmethod
    async def get_session_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas das sessões"""
        pass
    
    @abstractmethod
    async def count_total(self) -> int:
        """Conta total de sessões"""
        pass
    
    @abstractmethod
    async def delete_old_sessions(self, days_old: int = 30) -> int:
        """Remove sessões antigas e retorna quantidade removida"""
        pass


class IBatchMetricsRepository(ABC):
    """Interface do repositório de métricas de batch"""
    
    @abstractmethod
    async def record_metric(self, name: str, value: float, timestamp: datetime) -> None:
        """Registra uma métrica"""
        pass
    
    @abstractmethod
    async def get_metric_history(
        self, 
        name: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Busca histórico de uma métrica"""
        pass
    
    @abstractmethod
    async def get_latest_metrics(self) -> Dict[str, Any]:
        """Busca métricas mais recentes"""
        pass
    
    @abstractmethod
    async def get_system_health(self) -> Dict[str, Any]:
        """Retorna indicadores de saúde do sistema"""
        pass


class IArchidektDataRepository(ABC):
    """Interface específica para dados do Archidekt"""
    
    @abstractmethod
    async def save_deck_with_cards(self, deck: Deck, cards: List[Card]) -> None:
        """
        Salva deck com suas cartas em uma transação.
        Cria cartas que não existem e atualiza o relacionamento.
        """
        pass
    
    @abstractmethod
    async def get_or_create_card(self, card_data: Dict[str, Any]) -> Card:
        """
        Obtém carta existente ou cria uma nova a partir de dados do Archidekt
        """
        pass
    
    @abstractmethod
    async def bulk_save_cards(self, cards: List[Card]) -> None:
        """Salva múltiplas cartas de forma otimizada"""
        pass
    
    @abstractmethod
    async def update_deck_statistics(self, deck_id: UUID) -> None:
        """Recalcula e atualiza estatísticas do deck"""
        pass
    
    @abstractmethod
    async def find_cards_not_in_archidekt(self) -> List[Card]:
        """Busca cartas que não vieram do Archidekt"""
        pass
    
    @abstractmethod
    async def sync_card_prices(self, cards: List[Card]) -> None:
        """Sincroniza preços das cartas"""
        pass