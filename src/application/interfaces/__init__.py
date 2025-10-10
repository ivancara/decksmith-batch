"""
DeckSmith Batch Processing System
Application Layer - Interfaces para Serviços Externos
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from ..dto import (
    ScrapingRequestDTO, ScrapingResponseDTO,
    MLTrainingRequestDTO, MLTrainingResponseDTO,
    DataExportRequestDTO, DataExportResponseDTO,
    CardDataDTO, DeckDataDTO, MLFeatureVectorDTO
)


class IWebScraper(ABC):
    """Interface para serviços de web scraping"""
    
    @abstractmethod
    async def scrape_deck_list(
        self,
        formato: str,
        max_pages: Optional[int] = None,
        start_page: int = 1
    ) -> AsyncIterator[Dict[str, Any]]:
        """Scraping de lista de decks de um formato"""
        pass
    
    @abstractmethod
    async def scrape_deck_details(self, deck_url: str) -> Optional[DeckDataDTO]:
        """Scraping detalhado de um deck específico"""
        pass
    
    @abstractmethod
    async def scrape_card_details(self, card_name: str) -> Optional[CardDataDTO]:
        """Scraping de detalhes de uma carta"""
        pass
    
    @abstractmethod
    async def get_available_formats(self) -> List[str]:
        """Obtém formatos disponíveis para scraping"""
        pass
    
    @abstractmethod
    async def estimate_total_pages(self, formato: str) -> int:
        """Estima número total de páginas para um formato"""
        pass
    
    @abstractmethod
    def configure_stealth_mode(self, enabled: bool) -> None:
        """Configura modo stealth para evitar detecção"""
        pass
    
    @abstractmethod
    def configure_delays(self, min_delay: float, max_delay: float) -> None:
        """Configura delays entre requisições"""
        pass
    
    @abstractmethod
    def set_proxy_config(self, proxy_config: Dict[str, Any]) -> None:
        """Configura proxy para requisições"""
        pass


class IMLEngine(ABC):
    """Interface para engine de Machine Learning"""
    
    @abstractmethod
    async def prepare_dataset(
        self,
        deck_data: List[DeckDataDTO],
        target_variable: str
    ) -> List[MLFeatureVectorDTO]:
        """Prepara dataset para treinamento"""
        pass
    
    @abstractmethod
    async def train_model(
        self,
        algorithm: str,
        features: List[MLFeatureVectorDTO],
        hyperparameters: Dict[str, Any]
    ) -> MLTrainingResponseDTO:
        """Treina um modelo de ML"""
        pass
    
    @abstractmethod
    async def evaluate_model(
        self,
        model_id: str,
        test_features: List[MLFeatureVectorDTO]
    ) -> Dict[str, float]:
        """Avalia performance de um modelo"""
        pass
    
    @abstractmethod
    async def predict(
        self,
        model_id: str,
        features: MLFeatureVectorDTO
    ) -> Dict[str, Any]:
        """Faz predição com modelo treinado"""
        pass
    
    @abstractmethod
    async def get_feature_importance(self, model_id: str) -> Dict[str, float]:
        """Obtém importância das features"""
        pass
    
    @abstractmethod
    async def save_model(self, model_id: str, file_path: str) -> bool:
        """Salva modelo treinado em arquivo"""
        pass
    
    @abstractmethod
    async def load_model(self, file_path: str) -> str:
        """Carrega modelo de arquivo"""
        pass
    
    @abstractmethod
    async def get_available_algorithms(self) -> List[str]:
        """Retorna algoritmos disponíveis"""
        pass


class IDataExporter(ABC):
    """Interface para exportação de dados"""
    
    @abstractmethod
    async def export_cards(
        self,
        export_format: str,
        destination_path: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> DataExportResponseDTO:
        """Exporta dados de cartas"""
        pass
    
    @abstractmethod
    async def export_decks(
        self,
        export_format: str,
        destination_path: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> DataExportResponseDTO:
        """Exporta dados de decks"""
        pass
    
    @abstractmethod
    async def export_ml_features(
        self,
        export_format: str,
        destination_path: str,
        feature_version: str = "latest"
    ) -> DataExportResponseDTO:
        """Exporta features preparadas para ML"""
        pass
    
    @abstractmethod
    async def export_full_dataset(
        self,
        export_format: str,
        destination_path: str,
        include_metadata: bool = True
    ) -> DataExportResponseDTO:
        """Exporta dataset completo"""
        pass
    
    @abstractmethod
    async def validate_export_path(self, path: str) -> bool:
        """Valida se o caminho de exportação é válido"""
        pass
    
    @abstractmethod
    async def get_export_status(self, export_id: str) -> Dict[str, Any]:
        """Obtém status de uma exportação"""
        pass
    
    @abstractmethod
    async def cleanup_old_exports(self, max_age_days: int = 7) -> int:
        """Remove exports antigos"""
        pass


class INotificationService(ABC):
    """Interface para serviço de notificações"""
    
    @abstractmethod
    async def send_scraping_completed(
        self,
        session_id: str,
        result: ScrapingResponseDTO
    ) -> bool:
        """Notifica conclusão de scraping"""
        pass
    
    @abstractmethod
    async def send_training_completed(
        self,
        model_id: str,
        result: MLTrainingResponseDTO
    ) -> bool:
        """Notifica conclusão de treinamento"""
        pass
    
    @abstractmethod
    async def send_export_completed(
        self,
        export_id: str,
        result: DataExportResponseDTO
    ) -> bool:
        """Notifica conclusão de exportação"""
        pass
    
    @abstractmethod
    async def send_system_alert(
        self,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Envia alerta do sistema"""
        pass
    
    @abstractmethod
    async def send_health_report(
        self,
        health_status: Dict[str, Any]
    ) -> bool:
        """Envia relatório de saúde"""
        pass


class IJobQueue(ABC):
    """Interface para fila de jobs"""
    
    @abstractmethod
    async def enqueue_scraping_job(
        self,
        request: ScrapingRequestDTO,
        priority: int = 5
    ) -> str:
        """Adiciona job de scraping na fila"""
        pass
    
    @abstractmethod
    async def enqueue_training_job(
        self,
        request: MLTrainingRequestDTO,
        priority: int = 5
    ) -> str:
        """Adiciona job de treinamento na fila"""
        pass
    
    @abstractmethod
    async def enqueue_export_job(
        self,
        request: DataExportRequestDTO,
        priority: int = 5
    ) -> str:
        """Adiciona job de exportação na fila"""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Obtém status de um job"""
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancela um job"""
        pass
    
    @abstractmethod
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da fila"""
        pass
    
    @abstractmethod
    async def retry_failed_job(self, job_id: str) -> bool:
        """Reprocessa job falhado"""
        pass


class IFileStorage(ABC):
    """Interface para armazenamento de arquivos"""
    
    @abstractmethod
    async def save_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Salva arquivo"""
        pass
    
    @abstractmethod
    async def load_file(self, file_path: str) -> Optional[bytes]:
        """Carrega arquivo"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Remove arquivo"""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Verifica se arquivo existe"""
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Obtém informações do arquivo"""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        directory: str,
        pattern: Optional[str] = None
    ) -> List[str]:
        """Lista arquivos em diretório"""
        pass
    
    @abstractmethod
    async def cleanup_old_files(
        self,
        directory: str,
        max_age_days: int
    ) -> int:
        """Remove arquivos antigos"""
        pass


class ICacheService(ABC):
    """Interface para serviço de cache"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Define valor no cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Verifica se chave existe"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Remove chaves que correspondem ao padrão"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do cache"""
        pass


class IConfigManager(ABC):
    """Interface para gerenciamento de configurações"""
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Obtém configuração"""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> bool:
        """Define configuração"""
        pass
    
    @abstractmethod
    def get_database_config(self) -> Dict[str, Any]:
        """Obtém configurações do banco"""
        pass
    
    @abstractmethod
    def get_scraping_config(self) -> Dict[str, Any]:
        """Obtém configurações de scraping"""
        pass
    
    @abstractmethod
    def get_ml_config(self) -> Dict[str, Any]:
        """Obtém configurações de ML"""
        pass
    
    @abstractmethod
    def get_export_config(self) -> Dict[str, Any]:
        """Obtém configurações de exportação"""
        pass
    
    @abstractmethod
    def reload_config(self) -> bool:
        """Recarrega configurações"""
        pass


class IMonitoringService(ABC):
    """Interface para serviço de monitoramento"""
    
    @abstractmethod
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Registra métrica"""
        pass
    
    @abstractmethod
    async def increment_counter(
        self,
        counter_name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Incrementa contador"""
        pass
    
    @abstractmethod
    async def start_timer(self, operation_name: str) -> str:
        """Inicia timer para operação"""
        pass
    
    @abstractmethod
    async def stop_timer(self, timer_id: str) -> float:
        """Para timer e retorna duração"""
        pass
    
    @abstractmethod
    async def get_metrics(
        self,
        metric_name: str,
        time_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """Obtém métricas por período"""
        pass
    
    @abstractmethod
    async def get_system_health(self) -> Dict[str, Any]:
        """Obtém saúde do sistema"""
        pass