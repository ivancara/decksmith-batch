"""
DeckSmith Batch Processing System
Application Layer - Data Transfer Objects (DTOs)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


# Enums para DTOs
class ScrapeRequestType(Enum):
    FULL_SYNC = "full_sync"
    INCREMENTAL = "incremental" 
    SPECIFIC_DECK = "specific_deck"
    FORMAT_SYNC = "format_sync"


class ExportFormat(Enum):
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"


class ExportType(Enum):
    CARDS_ONLY = "cards_only"
    DECKS_ONLY = "decks_only"
    FULL_DATASET = "full_dataset"
    ML_FEATURES = "ml_features"


# DTOs de Request
@dataclass
class ScrapingRequestDTO:
    """DTO para requisições de scraping"""
    url: str
    page_type: str  # "deck", "card", "metagame"
    request_type: ScrapeRequestType = ScrapeRequestType.INCREMENTAL
    target_formats: Optional[List[str]] = None
    specific_deck_id: Optional[str] = None
    max_pages: Optional[int] = None
    delay_seconds: Optional[float] = 1.0
    use_stealth: bool = True
    priority: int = 5  # 1-10, onde 10 é máxima prioridade
    
    # Configurações avançadas
    retry_config: Optional[Dict[str, Any]] = None
    proxy_config: Optional[Dict[str, Any]] = None
    headers_config: Optional[Dict[str, Any]] = None
    
    # Metadados
    requested_by: Optional[str] = None
    request_source: str = "batch_system"
    notes: Optional[str] = None


@dataclass
class ScrapingResultDTO:
    """DTO para resultados de scraping"""
    url: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    scraping_timestamp: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: Optional[float] = None


@dataclass 
class MLTrainingRequestDTO:
    """DTO para requisições de treinamento ML"""
    model_id: str
    training_data: List[Dict[str, Any]]
    target_column: str
    algorithm: str = "random_forest"  # "random_forest", "neural_network", "xgboost"
    target_formats: Optional[List[str]] = None
    training_size: float = 0.8  # Porcentagem para treino
    validation_size: float = 0.2
    
    # Hiperparâmetros
    hyperparameters: Optional[Dict[str, Any]] = None
    
    # Configurações de treino
    max_training_time_minutes: int = 120
    early_stopping: bool = True
    cross_validation_folds: int = 5
    
    # Features
    feature_selection: Optional[List[str]] = None
    feature_engineering: bool = True
    
    # Metadados
    model_name: Optional[str] = None
    description: Optional[str] = None
    experiment_tags: List[str] = field(default_factory=list)


@dataclass
class MLTrainingResultDTO:
    """DTO para resultados de treinamento ML"""
    model_id: str
    success: bool
    model_path: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    training_duration: float = 0.0
    training_timestamp: datetime = field(default_factory=datetime.utcnow)
    feature_names: Optional[List[str]] = None
    algorithm: Optional[str] = None


@dataclass
class MLPredictionRequestDTO:
    """DTO para requisições de predição ML"""
    model_id: str
    input_data: Dict[str, Any]


@dataclass
class MLPredictionResultDTO:
    """DTO para resultados de predição ML"""
    model_id: str
    success: bool
    predictions: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    prediction_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataExportRequestDTO:
    """DTO para requisições de exportação de dados"""
    export_id: str
    data_type: str  # "cards", "decks", "scraping_sessions", "ml_models"
    data: List[Dict[str, Any]]
    format: Optional[str] = None  # "parquet", "csv", "json"
    filters: Optional[Dict[str, Any]] = None
    
    # Configurações de exportação
    compress: bool = True
    include_metadata: bool = True
    partition_by: Optional[str] = None  # "formato", "data", etc.
    
    # Configurações específicas por formato
    format_specific_config: Dict[str, Any] = field(default_factory=dict)
    
    # Metadados
    requested_by: Optional[str] = None
    purpose: Optional[str] = None


@dataclass
class DataExportResultDTO:
    """DTO para resultados de exportação"""
    export_id: str
    success: bool
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    rows_exported: Optional[int] = None
    export_format: Optional[str] = None
    error_message: Optional[str] = None
    export_duration: float = 0.0
    export_timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthCheckRequestDTO:
    """DTO para requisições de health check"""
    check_components: List[str] = field(default_factory=lambda: ["all"])
    include_metrics: bool = True
    include_recommendations: bool = True
    
    # Configurações específicas
    scraping_health_hours: int = 24  # Verificar últimas X horas
    ml_model_max_age_days: int = 7
    export_failure_threshold: int = 5


# DTOs de Response
@dataclass
class ScrapingResponseDTO:
    """DTO para respostas de scraping"""
    session_id: str
    status: str
    total_pages_scraped: int
    total_decks_found: int
    total_cards_found: int
    
    # Métricas de performance
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Estatísticas detalhadas
    pages_success: int = 0
    pages_failed: int = 0
    decks_new: int = 0
    decks_updated: int = 0
    cards_new: int = 0
    cards_updated: int = 0
    
    # Erros e avisos
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Próximos passos recomendados
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MLTrainingResponseDTO:
    """DTO para respostas de treinamento ML"""
    model_id: str
    algorithm: str
    status: str
    
    # Métricas de performance
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    
    # Informações de treinamento
    training_start: datetime = field(default_factory=datetime.now)
    training_end: Optional[datetime] = None
    training_duration_seconds: Optional[float] = None
    
    # Dataset info
    total_samples: int = 0
    training_samples: int = 0
    validation_samples: int = 0
    
    # Features utilizadas
    features_used: List[str] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Validação
    cross_validation_scores: List[float] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    
    # Hiperparâmetros finais
    final_hyperparameters: Dict[str, Any] = field(default_factory=dict)
    
    # Próximos passos
    is_production_ready: bool = False
    deployment_recommendations: List[str] = field(default_factory=list)


@dataclass
class DataExportResponseDTO:
    """DTO para respostas de exportação"""
    export_id: str
    status: str
    file_path: str
    
    # Informações do arquivo
    file_size_mb: Optional[float] = None
    total_records: int = 0
    compression_ratio: Optional[float] = None
    
    # Timing
    export_start: datetime = field(default_factory=datetime.now)
    export_end: Optional[datetime] = None
    export_duration_seconds: Optional[float] = None
    
    # Estatísticas por tipo
    export_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Qualidade dos dados
    data_quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Metadados do arquivo
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Erros e avisos
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResponseDTO:
    """DTO para respostas de health check"""
    overall_status: str  # "healthy", "warning", "critical"
    check_timestamp: datetime
    
    # Status por componente
    component_health: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Métricas do sistema
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Alertas ativos
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recomendações
    recommendations: List[str] = field(default_factory=list)
    
    # Tendências (opcional)
    performance_trends: Optional[Dict[str, List[float]]] = None


# DTOs para comunicação interna
@dataclass
class CardDataDTO:
    """DTO para dados de carta"""
    nome: str
    custo_mana: str
    cmc: int
    tipo: str
    texto: str
    cores: List[str]
    raridade: str
    
    # Dados adicionais
    set_code: Optional[str] = None
    collector_number: Optional[str] = None
    artist: Optional[str] = None
    flavor_text: Optional[str] = None
    
    # Metadados de scraping
    source_url: Optional[str] = None
    scraped_at: Optional[datetime] = None


@dataclass
class DeckDataDTO:
    """DTO para dados de deck"""
    nome: str
    formato: str
    total_cartas: int
    comandante: Optional[str] = None
    
    # Composição
    cartas: List[Dict[str, Any]] = field(default_factory=list)
    cores: List[str] = field(default_factory=list)
    
    # Análise
    custo_medio_mana: Optional[float] = None
    curva_mana: Dict[int, int] = field(default_factory=dict)
    distribuicao_tipos: Dict[str, int] = field(default_factory=dict)
    
    # Metadados
    source_url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    author: Optional[str] = None
    
    # Tags e categorização
    tags: List[str] = field(default_factory=list)
    competitive_tier: Optional[str] = None


@dataclass
class MLFeatureVectorDTO:
    """DTO para vetor de features de ML"""
    deck_id: str
    
    # Features numéricas
    numeric_features: Dict[str, float] = field(default_factory=dict)
    
    # Features categóricas
    categorical_features: Dict[str, str] = field(default_factory=dict)
    
    # Features booleanas
    boolean_features: Dict[str, bool] = field(default_factory=dict)
    
    # Features de array (ex: cores, tipos)
    array_features: Dict[str, List[Union[str, int, float]]] = field(default_factory=dict)
    
    # Target (para treinamento supervisionado)
    target: Optional[Union[str, float, int]] = None
    
    # Metadados
    feature_version: str = "1.0"
    extracted_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchJobStatusDTO:
    """DTO para status de jobs batch"""
    job_id: str
    job_type: str  # "scraping", "ml_training", "data_export"
    status: str  # "pending", "running", "completed", "failed"
    
    # Timing
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    progress_percentage: float = 0.0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    # Resultados
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Metadados
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 3