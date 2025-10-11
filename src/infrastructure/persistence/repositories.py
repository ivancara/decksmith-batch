"""
Infrastructure Layer - Repositórios e Persistência
Implementação dos repositórios seguindo SOLID e Clean Architecture
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from ...domain.interfaces import (
    IAdminSettingsRepository,
    IModelVersionRepository,
    IDeckRepository,
    IConfigurationManager,
    ModelVersion,
    AdminSetting,
    ModelType,
    ModelStatus
)

logger = logging.getLogger(__name__)


class InMemoryAdminSettingsRepository(IAdminSettingsRepository):
    """Implementação em memória para configurações administrativas"""
    
    def __init__(self):
        self._settings = {
            'ml_models_base_path': AdminSetting(
                id=1,
                setting_key='ml_models_base_path',
                setting_value={'value': '/app/models'},
                setting_category='ml_models',
                description='Caminho base para armazenar modelos ML',
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by='system',
                updated_by='system'
            ),
            'data_export_base_path': AdminSetting(
                id=2,
                setting_key='data_export_base_path',
                setting_value={'value': '/app/exports'},
                setting_category='data_export',
                description='Caminho base para exportações',
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by='system',
                updated_by='system'
            ),
            'batch_processing_chunk_size': AdminSetting(
                id=3,
                setting_key='batch_processing_chunk_size',
                setting_value={'value': 1000},
                setting_category='batch_processing',
                description='Tamanho do chunk para processamento',
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by='system',
                updated_by='system'
            )
        }
    
    async def get_setting(self, key: str) -> Optional[AdminSetting]:
        """Busca uma configuração por chave"""
        return self._settings.get(key)
    
    async def get_settings_by_category(self, category: str) -> List[AdminSetting]:
        """Busca configurações por categoria"""
        return [setting for setting in self._settings.values() 
                if setting.setting_category == category and setting.is_active]
    
    async def update_setting(self, key: str, value: Dict[str, Any], updated_by: str) -> bool:
        """Atualiza uma configuração"""
        if key in self._settings:
            setting = self._settings[key]
            setting.setting_value = value
            setting.updated_at = datetime.now()
            setting.updated_by = updated_by
            return True
        return False
    
    async def create_setting(self, setting: AdminSetting) -> AdminSetting:
        """Cria nova configuração"""
        existing_ids = [s.id for s in self._settings.values() if s.id is not None]
        new_id = max(existing_ids, default=0) + 1
        setting.id = new_id
        setting.created_at = datetime.now()
        setting.updated_at = datetime.now()
        self._settings[setting.setting_key] = setting
        return setting


class InMemoryModelVersionRepository(IModelVersionRepository):
    """Implementação em memória para versões de modelos"""
    
    def __init__(self):
        self._models: Dict[int, ModelVersion] = {}
        self._next_id = 1
        
        # Modelos de exemplo
        self._init_sample_models()
    
    def _init_sample_models(self):
        """Inicializa modelos de exemplo"""
        sample_models = [
            ModelVersion(
                id=1,
                model_name="card_recommendation_v1",
                version="20251011_104500",
                model_type=ModelType.CARD_RECOMMENDATION,
                file_path="./models/card_recommendation_20251011_104500/model.keras",
                file_size_bytes=2516582,  # ~2.4 MB
                tensorflow_version="2.20.0",
                architecture_config={
                    "layers": 6,
                    "input_shape": [50],
                    "output_shape": [10],
                    "total_params": 17194
                },
                training_config={
                    "epochs": 10,
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "optimizer": "adam"
                },
                performance_metrics={
                    "accuracy": 0.887,
                    "loss": 0.342,
                    "val_accuracy": 0.856,
                    "val_loss": 0.389
                },
                status=ModelStatus.ACTIVE,
                is_active=True,
                is_default=True,
                created_at=datetime(2025, 10, 11, 10, 45, 0),
                trained_at=datetime(2025, 10, 11, 10, 45, 0),
                activated_at=datetime(2025, 10, 11, 10, 45, 0),
                created_by="system",
                tags=["production", "v1"],
                description="Modelo principal de recomendação de cartas",
                training_notes="Treinado com dataset completo"
            ),
            ModelVersion(
                id=2,
                model_name="win_rate_predictor_v2",
                version="20251011_103200",
                model_type=ModelType.WIN_RATE_PREDICTOR,
                file_path="./models/win_rate_predictor_20251011_103200/model.keras",
                file_size_bytes=1887436,  # ~1.8 MB
                tensorflow_version="2.20.0",
                architecture_config={
                    "layers": 5,
                    "input_shape": [30],
                    "output_shape": [1],
                    "total_params": 4609
                },
                training_config={
                    "epochs": 15,
                    "batch_size": 64,
                    "learning_rate": 0.0005,
                    "optimizer": "adam"
                },
                performance_metrics={
                    "mae": 0.045,
                    "mse": 0.003,
                    "val_mae": 0.052,
                    "val_mse": 0.004
                },
                status=ModelStatus.ACTIVE,
                is_active=True,
                is_default=True,
                created_at=datetime(2025, 10, 11, 10, 32, 0),
                trained_at=datetime(2025, 10, 11, 10, 32, 0),
                activated_at=datetime(2025, 10, 11, 10, 32, 0),
                created_by="system",
                tags=["production", "v2", "optimized"],
                description="Preditor de taxa de vitória v2 - otimizado",
                training_notes="Melhorias na arquitetura e hiperparâmetros"
            ),
            ModelVersion(
                id=3,
                model_name="card_recommendation_old",
                version="20251010_152300",
                model_type=ModelType.CARD_RECOMMENDATION,
                file_path="./models/card_recommendation_20251010_152300/model.keras",
                file_size_bytes=2202009,  # ~2.1 MB
                tensorflow_version="2.20.0",
                architecture_config={
                    "layers": 5,
                    "input_shape": [50],
                    "output_shape": [10],
                    "total_params": 15432
                },
                training_config={
                    "epochs": 8,
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "optimizer": "adam"
                },
                performance_metrics={
                    "accuracy": 0.834,
                    "loss": 0.421,
                    "val_accuracy": 0.812,
                    "val_loss": 0.445
                },
                status=ModelStatus.DEPRECATED,
                is_active=False,
                is_default=False,
                created_at=datetime(2025, 10, 10, 15, 23, 0),
                trained_at=datetime(2025, 10, 10, 15, 23, 0),
                activated_at=None,
                created_by="system",
                tags=["deprecated", "v0"],
                description="Versão anterior do recomendador",
                training_notes="Versão inicial - substituída por modelo melhor"
            )
        ]
        
        for model in sample_models:
            self._models[model.id] = model
        
        self._next_id = 4
    
    async def save_model_version(self, model: ModelVersion) -> ModelVersion:
        """Salva nova versão de modelo"""
        if model.id is None:
            model.id = self._next_id
            self._next_id += 1
        
        model.created_at = datetime.now()
        if model.id is not None:
            self._models[model.id] = model
        
        logger.info(f"Modelo salvo: {model.model_type.value} v{model.version}")
        return model
    
    async def get_active_model(self, model_type: ModelType) -> Optional[ModelVersion]:
        """Busca modelo ativo por tipo"""
        for model in self._models.values():
            if model.model_type == model_type and model.is_active:
                return model
        return None
    
    async def get_all_versions(self, model_type: ModelType) -> List[ModelVersion]:
        """Lista todas as versões de um tipo de modelo"""
        models = [model for model in self._models.values() 
                 if model.model_type == model_type]
        return sorted(models, key=lambda x: x.created_at, reverse=True)
    
    async def activate_model_version(self, model_type: ModelType, version: str) -> bool:
        """Ativa uma versão específica do modelo"""
        target_model = None
        
        # Encontrar modelo alvo
        for model in self._models.values():
            if model.model_type == model_type and model.version == version:
                target_model = model
                break
        
        if not target_model:
            logger.error(f"Modelo {model_type.value} v{version} não encontrado")
            return False
        
        # Desativar todos os modelos do mesmo tipo
        for model in self._models.values():
            if model.model_type == model_type:
                model.is_active = False
                model.is_default = False
                model.activated_at = None
                if model.status == ModelStatus.ACTIVE:
                    model.status = ModelStatus.TRAINED
        
        # Ativar modelo alvo
        target_model.is_active = True
        target_model.is_default = True
        target_model.status = ModelStatus.ACTIVE
        target_model.activated_at = datetime.now()
        
        logger.info(f"Modelo ativado: {model_type.value} v{version}")
        return True
    
    async def get_model_by_version(self, model_type: ModelType, version: str) -> Optional[ModelVersion]:
        """Busca modelo por tipo e versão"""
        for model in self._models.values():
            if model.model_type == model_type and model.version == version:
                return model
        return None
    
    async def get_models_filtered(
        self, 
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ModelVersion]:
        """Busca modelos com filtros"""
        models = list(self._models.values())
        
        # Filtrar por tipo
        if model_type and model_type != 'all':
            try:
                model_type_enum = ModelType(model_type)
                models = [m for m in models if m.model_type == model_type_enum]
            except ValueError:
                return []
        
        # Filtrar por status
        if status and status != 'all':
            try:
                status_enum = ModelStatus(status)
                models = [m for m in models if m.status == status_enum]
            except ValueError:
                return []
        
        # Ordenar por data de criação (mais recente primeiro)
        models.sort(key=lambda x: x.created_at, reverse=True)
        
        # Aplicar limite
        if limit:
            models = models[:limit]
        
        return models


class InMemoryDeckRepository(IDeckRepository):
    """Implementação em memória para decks"""
    
    def __init__(self):
        self._decks: List[Dict[str, Any]] = []
        self._init_sample_decks()
    
    def _init_sample_decks(self):
        """Inicializa decks de exemplo"""
        for i in range(100):
            deck = {
                "id": i + 1,
                "name": f"Deck Exemplo {i + 1}",
                "commander": f"Commander {i + 1}",
                "colors": ["W", "U", "B", "R", "G"][:((i % 5) + 1)],
                "card_count": 100,
                "created_at": datetime.now().isoformat(),
                "source": "archidekt",
                "url": f"https://archidekt.com/decks/{1000000 + i}"
            }
            self._decks.append(deck)
    
    async def save_deck(self, deck_data: Dict[str, Any]) -> bool:
        """Salva dados de um deck"""
        deck_data["id"] = len(self._decks) + 1
        deck_data["created_at"] = datetime.now().isoformat()
        self._decks.append(deck_data)
        return True
    
    async def get_deck_count(self) -> int:
        """Retorna total de decks"""
        return len(self._decks)
    
    async def get_decks_for_export(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca decks para exportação"""
        if limit:
            return self._decks[:limit]
        return self._decks.copy()


class ConfigurationManager(IConfigurationManager):
    """Gerenciador de configurações do sistema"""
    
    def __init__(self, settings_repo: IAdminSettingsRepository):
        self._settings_repo = settings_repo
    
    async def get_config(self, key: str) -> Any:
        """Busca configuração por chave"""
        setting = await self._settings_repo.get_setting(key)
        if setting:
            return setting.setting_value.get('value')
        return None
    
    async def get_ml_models_config(self) -> Dict[str, Any]:
        """Busca configurações de modelos ML"""
        settings = await self._settings_repo.get_settings_by_category('ml_models')
        
        config = {
            'base_path': './models',
            'max_versions_per_type': 10,
            'auto_cleanup': True,
            'backup_enabled': True,
            'tensorflow_version': '2.20.0'
        }
        
        for setting in settings:
            key = setting.setting_key.replace('ml_models_', '')
            value = setting.setting_value.get('value')
            if value is not None:
                config[key] = value
        
        return config
    
    async def get_export_config(self) -> Dict[str, Any]:
        """Busca configurações de exportação"""
        settings = await self._settings_repo.get_settings_by_category('data_export')
        
        config = {
            'base_path': './exports',
            'format': 'parquet',
            'compression': 'snappy',
            'max_file_size_mb': 100
        }
        
        for setting in settings:
            key = setting.setting_key.replace('data_export_', '')
            value = setting.setting_value.get('value')
            if value is not None:
                config[key] = value
        
        return config
    
    async def get_batch_processing_config(self) -> Dict[str, Any]:
        """Busca configurações de processamento em lote"""
        settings = await self._settings_repo.get_settings_by_category('batch_processing')
        
        config = {
            'chunk_size': 1000,
            'max_parallel': 4,
            'timeout_minutes': 30
        }
        
        for setting in settings:
            key = setting.setting_key.replace('batch_processing_', '')
            value = setting.setting_value.get('value')
            if value is not None:
                config[key] = value
        
        return config