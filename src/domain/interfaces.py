"""
Domain Layer - Interfaces e Abstrações
Aplicando Interface Segregation Principle (ISP) e Dependency Inversion Principle (DIP)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ModelType(Enum):
    """Tipos de modelos ML suportados"""
    CARD_RECOMMENDATION = "card_recommendation"
    WIN_RATE_PREDICTOR = "win_rate_predictor"
    SYNERGY_DETECTOR = "synergy_detector"


class ModelStatus(Enum):
    """Status de um modelo ML"""
    TRAINED = "trained"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExportFormat(Enum):
    """Formatos de exportação suportados"""
    PARQUET = "parquet"
    CSV = "csv"
    JSON = "json"


@dataclass
class ModelVersion:
    """Value Object para versão de modelo"""
    id: Optional[int]
    model_name: str
    version: str
    model_type: ModelType
    file_path: str
    file_size_bytes: int
    tensorflow_version: str
    architecture_config: Dict[str, Any]
    training_config: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    status: ModelStatus
    is_active: bool
    is_default: bool
    created_at: datetime
    trained_at: Optional[datetime]
    activated_at: Optional[datetime]
    created_by: str
    tags: List[str]
    description: str
    training_notes: str


@dataclass
class AdminSetting:
    """Value Object para configuração administrativa"""
    id: Optional[int]
    setting_key: str
    setting_value: Dict[str, Any]
    setting_category: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


@dataclass
class BatchResult:
    """Value Object para resultado de operação em lote"""
    operation_type: str
    total_processed: int
    successful: int
    failed: int
    errors: List[str]
    execution_time_seconds: float
    output_files: List[str]
    metadata: Dict[str, Any]


# ============================================================================
# Repository Interfaces (DIP)
# ============================================================================

class IAdminSettingsRepository(ABC):
    """Interface para repositório de configurações administrativas"""
    
    @abstractmethod
    async def get_setting(self, key: str) -> Optional[AdminSetting]:
        """Busca uma configuração por chave"""
        pass
    
    @abstractmethod
    async def get_settings_by_category(self, category: str) -> List[AdminSetting]:
        """Busca configurações por categoria"""
        pass
    
    @abstractmethod
    async def update_setting(self, key: str, value: Dict[str, Any], updated_by: str) -> bool:
        """Atualiza uma configuração"""
        pass
    
    @abstractmethod
    async def create_setting(self, setting: AdminSetting) -> AdminSetting:
        """Cria nova configuração"""
        pass


class IModelVersionRepository(ABC):
    """Interface para repositório de versões de modelos"""
    
    @abstractmethod
    async def save_model_version(self, model: ModelVersion) -> ModelVersion:
        """Salva nova versão de modelo"""
        pass
    
    @abstractmethod
    async def get_active_model(self, model_type: ModelType) -> Optional[ModelVersion]:
        """Busca modelo ativo por tipo"""
        pass
    
    @abstractmethod
    async def get_all_versions(self, model_type: ModelType) -> List[ModelVersion]:
        """Lista todas as versões de um tipo de modelo"""
        pass
    
    @abstractmethod
    async def activate_model_version(self, model_type: ModelType, version: str) -> bool:
        """Ativa uma versão específica do modelo"""
        pass
    
    @abstractmethod
    async def get_model_by_version(self, model_type: ModelType, version: str) -> Optional[ModelVersion]:
        """Busca modelo por tipo e versão"""
        pass


class IDeckRepository(ABC):
    """Interface para repositório de decks"""
    
    @abstractmethod
    async def save_deck(self, deck_data: Dict[str, Any]) -> bool:
        """Salva dados de um deck"""
        pass
    
    @abstractmethod
    async def get_deck_count(self) -> int:
        """Retorna total de decks"""
        pass
    
    @abstractmethod
    async def get_decks_for_export(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca decks para exportação"""
        pass


# ============================================================================
# Service Interfaces (ISP)
# ============================================================================

class IDataExportService(ABC):
    """Interface para serviço de exportação de dados"""
    
    @abstractmethod
    async def export_to_parquet(self, data: List[Dict[str, Any]], output_path: str) -> str:
        """Exporta dados para formato Parquet"""
        pass
    
    @abstractmethod
    async def export_to_csv(self, data: List[Dict[str, Any]], output_path: str) -> str:
        """Exporta dados para formato CSV"""
        pass


class IModelTrainingService(ABC):
    """Interface para serviço de treinamento de modelos"""
    
    @abstractmethod
    async def train_model(self, model_type: ModelType, config: Dict[str, Any]) -> ModelVersion:
        """Treina um novo modelo"""
        pass
    
    @abstractmethod
    async def validate_model(self, model_version: ModelVersion) -> Dict[str, Any]:
        """Valida um modelo treinado"""
        pass


class IDeckLoadingService(ABC):
    """Interface para serviço de carregamento de decks"""
    
    @abstractmethod
    async def load_decks(self, count: int, source: str = "archidekt") -> BatchResult:
        """Carrega decks de uma fonte"""
        pass


class IFileStorageService(ABC):
    """Interface para serviço de armazenamento de arquivos"""
    
    @abstractmethod
    async def save_file(self, file_path: str, content: bytes) -> bool:
        """Salva arquivo"""
        pass
    
    @abstractmethod
    async def get_file_size(self, file_path: str) -> int:
        """Retorna tamanho do arquivo"""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Verifica se arquivo existe"""
        pass


# ============================================================================
# Command Pattern Interfaces
# ============================================================================

class ICommand(ABC):
    """Interface base para comandos (Command Pattern)"""
    
    @abstractmethod
    async def execute(self) -> BatchResult:
        """Executa o comando"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Retorna descrição do comando"""
        pass


# ============================================================================
# Strategy Pattern Interfaces
# ============================================================================

class IProcessingStrategy(ABC):
    """Interface base para estratégias de processamento (Strategy Pattern)"""
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> BatchResult:
        """Executa a estratégia"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Nome da estratégia"""
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Valida parâmetros da estratégia"""
        pass


# ============================================================================
# Configuration Management
# ============================================================================

class IConfigurationManager(ABC):
    """Interface para gerenciamento de configurações"""
    
    @abstractmethod
    async def get_config(self, key: str) -> Any:
        """Busca configuração por chave"""
        pass
    
    @abstractmethod
    async def get_ml_models_config(self) -> Dict[str, Any]:
        """Busca configurações de modelos ML"""
        pass
    
    @abstractmethod
    async def get_export_config(self) -> Dict[str, Any]:
        """Busca configurações de exportação"""
        pass
    
    @abstractmethod
    async def get_batch_processing_config(self) -> Dict[str, Any]:
        """Busca configurações de processamento em lote"""
        pass