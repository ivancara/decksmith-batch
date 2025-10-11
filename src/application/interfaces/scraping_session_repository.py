"""
Interface do repositório de sessões de scraping.
Define os contratos para persistência de ScrapingSession.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ...domain.entities import ScrapingSession


class IScrapingSessionRepository(ABC):
    """Interface do repositório de sessões de scraping."""
    
    @abstractmethod
    async def save(self, session: ScrapingSession) -> None:
        """Salva uma sessão de scraping."""
        pass
    
    @abstractmethod
    async def find_by_id(self, session_id: str) -> Optional[ScrapingSession]:
        """Busca uma sessão por ID."""
        pass
    
    @abstractmethod
    async def find_recent_sessions(self, limit: int = 10) -> List[ScrapingSession]:
        """Busca sessões recentes."""
        pass