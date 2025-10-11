"""
DeckSmith Batch Processing System
Domain Layer - Repository Interfaces
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from .entities import Card, Deck, ScrapingSession, MLModel, DataExportJob


class ICardRepository(ABC):
    """Interface para repositório de cartas"""
    
    @abstractmethod
    async def save(self, card: Card) -> Card:
        """Salva uma carta"""
        pass
    
    @abstractmethod
    async def find_by_id(self, card_id: UUID) -> Optional[Card]:
        """Busca carta por ID"""
        pass
    
    @abstractmethod
    async def find_by_name(self, nome: str) -> Optional[Card]:
        """Busca carta por nome"""
        pass
    
    @abstractmethod
    async def find_by_liga_magic_id(self, liga_id: str) -> Optional[Card]:
        """Busca carta por ID do Liga Magic"""
        pass
    
    @abstractmethod
    async def save_batch(self, cards: List[Card]) -> List[Card]:
        """Salva múltiplas cartas em batch"""
        pass
    
    @abstractmethod
    async def get_all_for_export(self, 
                                date_from: Optional[datetime] = None,
                                date_to: Optional[datetime] = None) -> List[Card]:
        """Busca todas as cartas para exportação"""
        pass
    
    @abstractmethod
    async def count_total(self) -> int:
        """Conta total de cartas"""
        pass


class IDeckRepository(ABC):
    """Interface para repositório de decks"""
    
    @abstractmethod
    async def save(self, deck: Deck) -> Deck:
        """Salva um deck"""
        pass
    
    @abstractmethod
    async def find_by_id(self, deck_id: UUID) -> Optional[Deck]:
        """Busca deck por ID"""
        pass
    
    @abstractmethod
    async def find_by_name_and_format(self, nome: str, formato: str) -> Optional[Deck]:
        """Busca deck por nome e formato"""
        pass
    
    @abstractmethod
    async def find_by_liga_magic_id(self, liga_id: str) -> Optional[Deck]:
        """Busca deck por ID do Liga Magic"""
        pass
    
    @abstractmethod
    async def save_batch(self, decks: List[Deck]) -> List[Deck]:
        """Salva múltiplos decks em batch"""
        pass
    
    @abstractmethod
    async def get_all_for_ml_training(self,
                                    formatos: Optional[List[str]] = None,
                                    competitive_only: bool = False,
                                    min_cards: int = 60) -> List[Deck]:
        """Busca decks para treinamento ML"""
        pass
    
    @abstractmethod
    async def get_deck_with_cards(self, deck_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca deck com suas cartas para ML"""
        pass
    
    @abstractmethod
    async def count_by_format(self) -> Dict[str, int]:
        """Conta decks por formato"""
        pass


class IScrapingSessionRepository(ABC):
    """Interface para repositório de sessões de scraping"""
    
    @abstractmethod
    async def save(self, session: ScrapingSession) -> ScrapingSession:
        """Salva sessão de scraping"""
        pass
    
    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> Optional[ScrapingSession]:
        """Busca sessão por ID"""
        pass
    
    @abstractmethod
    async def find_active_sessions(self) -> List[ScrapingSession]:
        """Busca sessões ativas"""
        pass
    
    @abstractmethod
    async def find_recent_sessions(self, limit: int = 10) -> List[ScrapingSession]:
        """Busca sessões recentes"""
        pass
    
    @abstractmethod
    async def find_last_successful_session(self) -> Optional[ScrapingSession]:
        """Busca última sessão bem-sucedida"""
        pass
    
    @abstractmethod
    async def update_progress(self, session_id: UUID, 
                            current_page: int,
                            decks_found: int,
                            cards_found: int) -> None:
        """Atualiza progresso da sessão"""
        pass


class IMLModelRepository(ABC):
    """Interface para repositório de modelos ML"""
    
    @abstractmethod
    async def save(self, model: MLModel) -> MLModel:
        """Salva modelo ML"""
        pass
    
    @abstractmethod
    async def find_by_id(self, model_id: UUID) -> Optional[MLModel]:
        """Busca modelo por ID"""
        pass
    
    @abstractmethod
    async def find_by_name_version(self, nome: str, versao: str) -> Optional[MLModel]:
        """Busca modelo por nome e versão"""
        pass
    
    @abstractmethod
    async def find_active_models(self) -> List[MLModel]:
        """Busca modelos ativos"""
        pass
    
    @abstractmethod
    async def find_latest_by_algorithm(self, algoritmo: str) -> Optional[MLModel]:
        """Busca modelo mais recente por algoritmo"""
        pass
    
    @abstractmethod
    async def deactivate_all(self) -> None:
        """Desativa todos os modelos"""
        pass
    
    @abstractmethod
    async def get_model_performance_history(self, 
                                          algoritmo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca histórico de performance dos modelos"""
        pass


class IDataExportRepository(ABC):
    """Interface para repositório de jobs de exportação"""
    
    @abstractmethod
    async def save(self, job: DataExportJob) -> DataExportJob:
        """Salva job de exportação"""
        pass
    
    @abstractmethod
    async def find_by_id(self, job_id: UUID) -> Optional[DataExportJob]:
        """Busca job por ID"""
        pass
    
    @abstractmethod
    async def find_running_jobs(self) -> List[DataExportJob]:
        """Busca jobs em execução"""
        pass
    
    @abstractmethod
    async def find_recent_jobs(self, limit: int = 10) -> List[DataExportJob]:
        """Busca jobs recentes"""
        pass


class IBatchMetricsRepository(ABC):
    """Interface para métricas do sistema batch"""
    
    @abstractmethod
    async def record_scraping_metrics(self, session_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de scraping"""
        pass
    
    @abstractmethod
    async def record_ml_training_metrics(self, model_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de treinamento ML"""
        pass
    
    @abstractmethod
    async def record_export_metrics(self, job_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de exportação"""
        pass
    
    @abstractmethod
    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """Busca métricas de saúde do sistema"""
        pass
    
    @abstractmethod
    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Busca tendências de performance"""
        pass