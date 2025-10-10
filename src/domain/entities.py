"""
DeckSmith Batch Processing System
Domain Layer - Entities
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum


class ScrapingStatus(Enum):
    """Status do processo de scraping"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MLModelStatus(Enum):
    """Status do modelo ML"""
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class Card:
    """Entidade que representa uma carta MTG"""
    id: UUID = field(default_factory=uuid4)
    nome: str = ""
    tipo: str = ""
    custo_mana: str = ""
    cmc: Optional[int] = None
    cores: List[str] = field(default_factory=list)
    raridade: str = ""
    texto: str = ""
    poder: Optional[str] = None
    resistencia: Optional[str] = None
    edicao: str = ""
    preco_usd: Optional[float] = None
    liga_magic_id: Optional[str] = None
    scryfall_id: Optional[str] = None
    
    # Metadados para ML
    is_creature: bool = False
    is_spell: bool = False
    is_artifact: bool = False
    is_land: bool = False
    is_planeswalker: bool = False
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Processa dados após inicialização"""
        self._categorize_card_type()
        self._normalize_colors()
    
    def _categorize_card_type(self):
        """Categoriza o tipo da carta para features ML"""
        tipo_lower = self.tipo.lower()
        self.is_creature = "creature" in tipo_lower or "criatura" in tipo_lower
        self.is_spell = any(t in tipo_lower for t in ["instant", "sorcery", "instantaneo", "feitico"])
        self.is_artifact = "artifact" in tipo_lower or "artefato" in tipo_lower
        self.is_land = "land" in tipo_lower or "terra" in tipo_lower
        self.is_planeswalker = "planeswalker" in tipo_lower
    
    def _normalize_colors(self):
        """Normaliza as cores para padrão"""
        color_map = {
            "white": "W", "branco": "W",
            "blue": "U", "azul": "U", 
            "black": "B", "preto": "B",
            "red": "R", "vermelho": "R",
            "green": "G", "verde": "G"
        }
        
        normalized = []
        for cor in self.cores:
            normalized.append(color_map.get(cor.lower(), cor))
        self.cores = sorted(list(set(normalized)))
    
    def get_color_identity(self) -> str:
        """Retorna identidade de cor como string"""
        return "".join(sorted(self.cores)) if self.cores else "C"
    
    def to_ml_features(self) -> Dict[str, Any]:
        """Converte carta para features ML"""
        return {
            "cmc": self.cmc or 0,
            "color_count": len(self.cores),
            "color_identity": self.get_color_identity(),
            "is_creature": self.is_creature,
            "is_spell": self.is_spell,
            "is_artifact": self.is_artifact,
            "is_land": self.is_land,
            "is_planeswalker": self.is_planeswalker,
            "rarity": self.raridade.lower(),
            "has_power": self.poder is not None,
            "has_toughness": self.resistencia is not None,
            "text_length": len(self.texto) if self.texto else 0,
            "price_usd": self.preco_usd or 0.0
        }
    
    @classmethod
    def create_from_scraping(
        cls,
        nome: str,
        custo_mana: str,
        tipo: str,
        texto: str,
        cores: List[str],
        raridade: str,
        **kwargs
    ) -> "Card":
        """Cria carta a partir de dados de scraping"""
        # Calcular CMC a partir do custo de mana
        cmc = cls._calculate_cmc_from_mana_cost(custo_mana)
        
        return cls(
            nome=nome,
            custo_mana=custo_mana,
            cmc=cmc,
            tipo=tipo,
            texto=texto,
            cores=cores,
            raridade=raridade,
            **kwargs
        )
    
    @staticmethod
    def _calculate_cmc_from_mana_cost(custo_mana: str) -> int:
        """Calcula CMC a partir do custo de mana"""
        if not custo_mana:
            return 0
        
        # Lógica simplificada - pode ser expandida
        import re
        
        # Extrair números do custo
        numbers = re.findall(r'\d+', custo_mana)
        generic_cost = sum(int(num) for num in numbers)
        
        # Contar símbolos de mana colorido
        colored_symbols = len(re.findall(r'[WUBRG]', custo_mana))
        
        return generic_cost + colored_symbols


@dataclass
class Deck:
    """Entidade que representa um deck MTG"""
    id: UUID = field(default_factory=uuid4)
    nome: str = ""
    formato: str = "Commander"
    comandante: Optional[str] = None
    cores: List[str] = field(default_factory=list)
    cartas: List[Dict[str, Any]] = field(default_factory=list)  # {carta_id, quantidade}
    dono: str = ""
    
    # Estatísticas calculadas
    total_cartas: int = 0
    custo_medio_mana: float = 0.0
    curva_mana: Dict[int, int] = field(default_factory=dict)
    distribuicao_tipos: Dict[str, int] = field(default_factory=dict)
    
    # Metadados
    liga_magic_id: Optional[str] = None
    is_competitive: bool = False
    tags: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_card(self, card_id: UUID, quantidade: int = 1):
        """Adiciona carta ao deck"""
        # Verificar se carta já existe
        for carta in self.cartas:
            if carta["carta_id"] == card_id:
                carta["quantidade"] += quantidade
                return
        
        # Adicionar nova carta
        self.cartas.append({
            "carta_id": card_id,
            "quantidade": quantidade
        })
        self._recalculate_stats()
    
    def _recalculate_stats(self):
        """Recalcula estatísticas do deck"""
        self.total_cartas = sum(carta["quantidade"] for carta in self.cartas)
        self.updated_at = datetime.now()
    
    def get_card_names_list(self) -> List[str]:
        """Retorna lista de nomes de cartas para ML"""
        # Esta função seria implementada com acesso ao repositório
        # Por agora retorna placeholder
        return [f"carta_{carta['carta_id']}" for carta in self.cartas]
    
    def to_ml_dataset_row(self, card_repository) -> Dict[str, Any]:
        """Converte deck para row do dataset ML"""
        card_names = []
        card_features = []
        
        for deck_card in self.cartas:
            card = card_repository.find_by_id(deck_card["carta_id"])
            if card:
                card_names.extend([card.nome] * deck_card["quantidade"])
                card_features.append(card.to_ml_features())
        
        return {
            "deck_id": str(self.id),
            "formato": self.formato,
            "cores": ",".join(sorted(self.cores)),
            "total_cartas": self.total_cartas,
            "custo_medio_mana": self.custo_medio_mana,
            "card_names": card_names,
            "is_competitive": self.is_competitive
        }
    
    @classmethod
    def create_from_scraping(
        cls,
        nome: str,
        formato: str,
        cartas_data: List[Any],
        comandante: Optional[str] = None,
        source_url: Optional[str] = None,
        **kwargs
    ) -> "Deck":
        """Cria deck a partir de dados de scraping"""
        deck = cls(
            nome=nome,
            formato=formato,
            comandante=comandante,
            **kwargs
        )
        
        # Processar cartas
        for carta_data in cartas_data:
            if hasattr(carta_data, 'id'):
                deck.add_card(carta_data.id, carta_data.get("quantidade", 1))
        
        # Calcular estatísticas básicas
        deck._calculate_basic_stats()
        
        return deck
    
    def _calculate_basic_stats(self):
        """Calcula estatísticas básicas do deck"""
        self.total_cartas = sum(carta["quantidade"] for carta in self.cartas)
        # Mais estatísticas podem ser calculadas aqui
    
    def add_analysis_data(self, analysis: Dict[str, Any]):
        """Adiciona dados de análise ao deck"""
        if "competitive_score" in analysis:
            self.is_competitive = analysis["competitive_score"] > 0.7
        
        # Adicionar outras análises como tags
        if "mana_curve_quality" in analysis:
            quality = analysis["mana_curve_quality"]
            if isinstance(quality, dict) and quality.get("quality_score", 0) > 0.8:
                self.tags.append("good_mana_curve")


@dataclass 
class ScrapingSession:
    """Entidade que representa uma sessão de scraping"""
    id: UUID = field(default_factory=uuid4)
    fonte: str = "ligamagic"
    status: ScrapingStatus = ScrapingStatus.PENDING
    
    # Parâmetros
    total_pages: int = 0
    current_page: int = 0
    delay_seconds: float = 1.0
    concurrent_workers: int = 4
    
    # Progresso
    decks_found: int = 0
    decks_processed: int = 0
    cards_found: int = 0
    cards_processed: int = 0
    errors_count: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Logs e erros
    error_message: Optional[str] = None
    log_entries: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def start(self):
        """Inicia a sessão de scraping"""
        self.status = ScrapingStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete(self):
        """Completa a sessão de scraping"""
        self.status = ScrapingStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def fail(self, error_message: str):
        """Marca sessão como falha"""
        self.status = ScrapingStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
    
    def add_log(self, message: str):
        """Adiciona entrada de log"""
        timestamp = datetime.now().isoformat()
        self.log_entries.append(f"[{timestamp}] {message}")
    
    def get_progress_percentage(self) -> float:
        """Retorna progresso em porcentagem"""
        if self.total_pages == 0:
            return 0.0
        return (self.current_page / self.total_pages) * 100
    
    @classmethod
    def create_new(
        cls,
        request_type: str,
        target_formats: List[str],
        max_pages: Optional[int] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> "ScrapingSession":
        """Cria nova sessão de scraping"""
        config = configuration or {}
        
        session = cls(
            total_pages=max_pages or 0,
            delay_seconds=config.get("delay_seconds", 1.0),
            concurrent_workers=config.get("concurrent_workers", 4)
        )
        
        session.add_log(f"Sessão criada - Tipo: {request_type}, Formatos: {target_formats}")
        
        return session
    
    def complete_successfully(self, total_pages: int, total_decks: int, total_cards: int):
        """Completa sessão com sucesso"""
        self.status = ScrapingStatus.COMPLETED
        self.completed_at = datetime.now()
        self.total_pages = total_pages
        self.decks_found = total_decks
        self.cards_found = total_cards
        self.add_log("Sessão completada com sucesso")
    
    def mark_as_failed(self, error_message: str):
        """Marca sessão como falha"""
        self.status = ScrapingStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
        self.add_log(f"Sessão falhou: {error_message}")
    
    @property
    def start_time(self) -> datetime:
        """Retorna tempo de início"""
        return self.started_at or self.created_at
    
    @property
    def end_time(self) -> Optional[datetime]:
        """Retorna tempo de fim"""
        return self.completed_at
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Retorna duração em segundos"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class MLModel:
    """Entidade que representa um modelo ML treinado"""
    id: UUID = field(default_factory=uuid4)
    nome: str = ""
    versao: str = "1.0.0"
    algoritmo: str = "deep_learning"
    status: MLModelStatus = MLModelStatus.TRAINING
    
    # Configuração do treinamento
    hiperparametros: Dict[str, Any] = field(default_factory=dict)
    dataset_info: Dict[str, Any] = field(default_factory=dict)
    
    # Métricas de performance
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    loss: Optional[float] = None
    
    # Arquivos
    model_file_path: Optional[str] = None
    preprocessor_path: Optional[str] = None
    metadata_path: Optional[str] = None
    
    # Timing
    training_started_at: Optional[datetime] = None
    training_completed_at: Optional[datetime] = None
    training_duration_seconds: Optional[int] = None
    
    # Metadados
    created_by: str = "batch_system"
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def start_training(self):
        """Inicia treinamento do modelo"""
        self.status = MLModelStatus.TRAINING
        self.training_started_at = datetime.now()
    
    def complete_training(self, metrics: Dict[str, float]):
        """Completa treinamento com métricas"""
        self.status = MLModelStatus.COMPLETED
        self.training_completed_at = datetime.now()
        
        if self.training_started_at:
            duration = self.training_completed_at - self.training_started_at
            self.training_duration_seconds = int(duration.total_seconds())
        
        # Atualizar métricas
        self.accuracy = metrics.get("accuracy")
        self.precision = metrics.get("precision")
        self.recall = metrics.get("recall")
        self.f1_score = metrics.get("f1_score")
        self.loss = metrics.get("loss")
    
    def fail_training(self, error_message: str):
        """Marca treinamento como falha"""
        self.status = MLModelStatus.FAILED
        self.training_completed_at = datetime.now()
    
    def activate(self):
        """Ativa modelo para uso em produção"""
        self.is_active = True
        self.status = MLModelStatus.ACTIVE
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Retorna resumo da performance"""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "loss": self.loss,
            "training_duration_hours": (
                self.training_duration_seconds / 3600 
                if self.training_duration_seconds else None
            )
        }
    
    @classmethod
    def create_new(
        cls,
        algorithm: str,
        hyperparameters: Dict[str, Any],
        target_formats: Optional[List[str]] = None,
        name: Optional[str] = None
    ) -> "MLModel":
        """Cria novo modelo ML"""
        model_name = name or f"model_{algorithm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return cls(
            nome=model_name,
            algoritmo=algorithm,
            hiperparametros=hyperparameters.copy(),
            dataset_info={
                "target_formats": target_formats or [],
                "created_at": datetime.now().isoformat()
            }
        )
    
    def start_training(self):
        """Inicia treinamento do modelo"""
        self.status = MLModelStatus.TRAINING
        self.training_started_at = datetime.now()
    
    def complete_training(
        self,
        accuracy: Optional[float] = None,
        precision: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        loss: Optional[float] = None
    ):
        """Completa treinamento com métricas"""
        self.status = MLModelStatus.COMPLETED
        self.training_completed_at = datetime.now()
        
        if self.training_started_at:
            duration = self.training_completed_at - self.training_started_at
            self.training_duration_seconds = int(duration.total_seconds())
        
        # Atualizar métricas
        self.accuracy = accuracy
        self.precision = precision
        self.recall = recall
        self.f1_score = f1_score
        self.loss = loss
    
    def mark_as_failed(self, error_message: str):
        """Marca treinamento como falha"""
        self.status = MLModelStatus.FAILED
        self.training_completed_at = datetime.now()
    
    def mark_as_production_ready(self):
        """Marca modelo como pronto para produção"""
        self.is_active = True
        self.status = MLModelStatus.ACTIVE


@dataclass
class DataExportJob:
    """Entidade que representa um job de exportação de dados"""
    id: UUID = field(default_factory=uuid4)
    export_type: str = "parquet"  # parquet, csv, json
    format_config: Dict[str, Any] = field(default_factory=dict)
    
    # Filtros
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    formatos: List[str] = field(default_factory=list)
    include_competitive_only: bool = False
    
    # Status
    status: str = "pending"  # pending, running, completed, failed
    records_processed: int = 0
    total_records: int = 0
    
    # Output
    output_file_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def start(self):
        """Inicia job de exportação"""
        self.status = "running"
        self.started_at = datetime.now()
    
    def complete(self, output_path: str, file_size_mb: float):
        """Completa exportação"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.output_file_path = output_path
        self.file_size_mb = file_size_mb
    
    def fail(self, error_message: str):
        """Marca exportação como falha"""
        self.status = "failed"
        self.completed_at = datetime.now()
    
    @classmethod
    def create_new(
        cls,
        export_type: str,
        export_format: str,
        destination_path: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> "DataExportJob":
        """Cria novo job de exportação"""
        return cls(
            export_type=export_type,
            format_config=filters or {},
            output_file_path=destination_path
        )
    
    def complete_successfully(self, file_size_mb: Optional[float], total_records: int):
        """Completa exportação com sucesso"""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.file_size_mb = file_size_mb
        self.total_records = total_records
    
    def mark_as_failed(self, error_message: str):
        """Marca exportação como falha"""
        self.status = "failed"
        self.completed_at = datetime.now()
        self.completed_at = datetime.now()
        self.output_file_path = output_path
        self.file_size_mb = file_size_mb
    
    def get_progress_percentage(self) -> float:
        """Retorna progresso da exportação"""
        if self.total_records == 0:
            return 0.0
        return (self.records_processed / self.total_records) * 100