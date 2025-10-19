"""
Infrastructure Layer - Repositórios e Persistência
Implementação dos repositórios seguindo SOLID e Clean Architecture
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

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

from .database_connection import PostgreSQLRepository, DatabaseConnection

logger = logging.getLogger(__name__)


class PostgreSQLAdminSettingsRepository(PostgreSQLRepository, IAdminSettingsRepository):
    """Implementação PostgreSQL para configurações administrativas"""
    
    async def get_setting(self, key: str) -> Optional[AdminSetting]:
        """Busca uma configuração por chave"""
        record = await self._db.fetchrow(
            "SELECT * FROM admin_settings WHERE setting_key = $1 AND is_active = true",
            key
        )
        
        if not record:
            return None
        
        return AdminSetting(
            id=record['id'],
            setting_key=record['setting_key'],
            setting_value=record['setting_value'],
            setting_category=record['setting_category'],
            description=record['description'],
            is_active=record['is_active'],
            created_at=record['created_at'],
            updated_at=record['updated_at'],
            created_by=record['created_by'] or '',
            updated_by=record['updated_by'] or ''
        )
    
    async def get_settings_by_category(self, category: str) -> List[AdminSetting]:
        """Busca configurações por categoria"""
        records = await self._db.fetch(
            "SELECT * FROM admin_settings WHERE setting_category = $1 AND is_active = true ORDER BY setting_key",
            category
        )
        
        settings = []
        for record in records:
            setting = AdminSetting(
                id=record['id'],
                setting_key=record['setting_key'],
                setting_value=record['setting_value'],
                setting_category=record['setting_category'],
                description=record['description'],
                is_active=record['is_active'],
                created_at=record['created_at'],
                updated_at=record['updated_at'],
                created_by=record['created_by'] or '',
                updated_by=record['updated_by'] or ''
            )
            settings.append(setting)
        
        return settings
    
    async def update_setting(self, key: str, value: Dict[str, Any], updated_by: str) -> bool:
        """Atualiza uma configuração"""
        try:
            result = await self._db.execute(
                """UPDATE admin_settings 
                   SET setting_value = $1, updated_by = $2, updated_at = CURRENT_TIMESTAMP 
                   WHERE setting_key = $3 AND is_active = true""",
                json.dumps(value), updated_by, key
            )
            
            # Verificar se alguma linha foi afetada
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração {key}: {e}")
            return False
    
    async def create_setting(self, setting: AdminSetting) -> AdminSetting:
        """Cria nova configuração"""
        try:
            new_id = await self._db.fetchval(
                """INSERT INTO admin_settings 
                   (setting_key, setting_value, setting_category, description, created_by, updated_by)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                setting.setting_key,
                json.dumps(setting.setting_value),
                setting.setting_category,
                setting.description,
                setting.created_by,
                setting.updated_by
            )
            
            setting.id = new_id
            setting.created_at = datetime.now()
            setting.updated_at = datetime.now()
            
            return setting
            
        except Exception as e:
            logger.error(f"Erro ao criar configuração {setting.setting_key}: {e}")
            raise
    
    async def get_all_settings(self) -> List[Dict[str, Any]]:
        """Busca todas as configurações ativas"""
        records = await self._db.fetch(
            "SELECT setting_key, setting_value, setting_category, description, is_active FROM admin_settings WHERE is_active = true ORDER BY setting_category, setting_key"
        )
        
        result = []
        for record in records:
            result.append({
                'setting_key': record['setting_key'],
                'setting_value': record['setting_value'],
                'setting_category': record['setting_category'], 
                'description': record['description'],
                'is_active': record['is_active']
            })
        
        return result


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
    
    async def get_all_settings(self) -> List[Dict[str, Any]]:
        """Busca todas as configurações ativas"""
        return [
            {
                'setting_key': setting.setting_key,
                'setting_value': setting.setting_value.get('value', setting.setting_value),
                'setting_category': setting.setting_category,
                'description': setting.description,
                'is_active': setting.is_active
            }
            for setting in self._settings.values()
            if setting.is_active
        ]


class PostgreSQLModelVersionRepository(PostgreSQLRepository, IModelVersionRepository):
    """Implementação PostgreSQL para versões de modelos"""
    
    async def save_model_version(self, model: ModelVersion) -> ModelVersion:
        """Salva nova versão de modelo"""
        try:
            # Inserir na tabela ml_models 
            model_id = await self._db.fetchval(
                """INSERT INTO ml_models 
                   (name, version, algorithm, model_type, architecture, status, accuracy, 
                    loss, val_accuracy, val_loss, precision_score, recall_score, f1_score,
                    training_epochs, batch_size, learning_rate, hyperparameters,
                    model_size_mb, is_active, model_path, trained_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                   RETURNING id""",
                model.model_name,
                model.version,
                model.model_type.value,
                "classification",  # model_type default
                json.dumps(model.architecture_config),
                model.status.value,
                model.performance_metrics.get('accuracy') if model.performance_metrics else None,
                model.performance_metrics.get('loss') if model.performance_metrics else None,
                model.performance_metrics.get('val_accuracy') if model.performance_metrics else None,
                model.performance_metrics.get('val_loss') if model.performance_metrics else None,
                model.performance_metrics.get('precision_score') if model.performance_metrics else None,
                model.performance_metrics.get('recall_score') if model.performance_metrics else None,
                model.performance_metrics.get('f1_score') if model.performance_metrics else None,
                model.training_config.get('epochs') if model.training_config else None,
                model.training_config.get('batch_size') if model.training_config else None,
                model.training_config.get('learning_rate') if model.training_config else None,
                json.dumps(model.training_config),
                model.file_size_bytes / (1024 * 1024) if model.file_size_bytes else None,
                model.is_active,
                model.file_path,
                model.trained_at
            )
            
            # Converter UUID string para objeto se necessário
            if isinstance(model_id, str):
                model_id = uuid.UUID(model_id)
            
            model.id = model_id
            model.created_at = datetime.now()
            
            logger.info(f"Modelo salvo: {model.model_type.value} v{model.version} (ID: {model_id})")
            return model
            
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {e}")
            raise
    
    async def get_active_model(self, model_type: ModelType) -> Optional[ModelVersion]:
        """Busca modelo ativo por tipo"""
        record = await self._db.fetchrow(
            "SELECT * FROM ml_models WHERE algorithm = $1 AND is_active = true LIMIT 1",
            model_type.value
        )
        
        if not record:
            return None
        
        return self._record_to_model_version(record)
    
    async def get_all_versions(self, model_type: ModelType) -> List[ModelVersion]:
        """Lista todas as versões de um tipo de modelo"""
        records = await self._db.fetch(
            "SELECT * FROM ml_models WHERE algorithm = $1 ORDER BY created_at DESC",
            model_type.value
        )
        
        models = []
        for record in records:
            model = self._record_to_model_version(record)
            models.append(model)
        
        return models
    
    async def activate_model_version(self, model_type: ModelType, version: str) -> bool:
        """Ativa uma versão específica do modelo"""
        try:
            async with self._db.acquire() as conn:
                async with conn.transaction():
                    # Desativar todos os modelos do mesmo tipo
                    await conn.execute(
                        """UPDATE ml_models 
                           SET is_active = false, is_production = false 
                           WHERE algorithm = $1""",
                        model_type.value
                    )
                    
                    # Ativar modelo específico
                    result = await conn.execute(
                        """UPDATE ml_models 
                           SET is_active = true, is_production = true, status = 'active', deployed_at = CURRENT_TIMESTAMP
                           WHERE algorithm = $1 AND version = $2""",
                        model_type.value, version
                    )
                    
                    return result == "UPDATE 1"
                
        except Exception as e:
            logger.error(f"Erro ao ativar modelo {model_type.value} v{version}: {e}")
            return False
    
    async def get_model_by_version(self, model_type: ModelType, version: str) -> Optional[ModelVersion]:
        """Busca modelo por tipo e versão"""
        record = await self._db.fetchrow(
            "SELECT * FROM ml_models WHERE algorithm = $1 AND version = $2",
            model_type.value, version
        )
        
        if not record:
            return None
        
        return self._record_to_model_version(record)
    
    def _record_to_model_version(self, record) -> ModelVersion:
        """Converte record do banco para ModelVersion"""
        return ModelVersion(
            id=record['id'],
            model_name=record['name'],
            version=record['version'], 
            model_type=ModelType(record['algorithm']),
            file_path=record['model_path'] or '',
            file_size_bytes=int(record['model_size_mb'] * 1024 * 1024) if record['model_size_mb'] else 0,
            tensorflow_version="2.20.0",  # Default
            architecture_config=record['architecture'] or {},
            training_config=record['hyperparameters'] or {},
            performance_metrics={
                'accuracy': record['accuracy'],
                'loss': record['loss'],
                'val_accuracy': record['val_accuracy'],
                'val_loss': record['val_loss'],
                'precision_score': record['precision_score'],
                'recall_score': record['recall_score'],
                'f1_score': record['f1_score']
            },
            status=ModelStatus(record['status']),
            is_active=record['is_active'],
            is_default=record['is_production'],
            created_at=record['created_at'],
            trained_at=record['trained_at'],
            activated_at=record['deployed_at'],
            created_by="system",
            tags=[],
            description="Modelo carregado do banco",
            training_notes=""
        )


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
            self._models[int(model.id)] = model
        
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


class PostgreSQLDeckRepository(PostgreSQLRepository, IDeckRepository):
    """Implementação PostgreSQL para decks"""
    
    async def save_deck(self, deck_data: Dict[str, Any]) -> bool:
        """Salva dados de um deck"""
        try:
            # Criar deck principal
            deck_id = await self._db.fetchval(
                """INSERT INTO decks (name, description, format_id, colors, total_cards, estimated_price, user_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
                deck_data.get('name', 'Deck Importado'),
                deck_data.get('description', ''),
                1,  # Default format_id (Commander)
                deck_data.get('colors', []),
                deck_data.get('card_count', 0),
                0.0,  # Será calculado pelos triggers
                1  # Default user_id (será configurado)
            )
            
            # Salvar cartas se fornecidas
            cards = deck_data.get('cards', [])
            for card_data in cards:
                await self._save_deck_card(deck_id, card_data)
            
            logger.info(f"Deck salvo com ID: {deck_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar deck: {e}")
            return False
    
    async def _save_deck_card(self, deck_id: Any, card_data: Dict[str, Any]):
        """Salva carta no deck"""
        # Primeiro, verificar se a carta existe, senão criar
        card_id = await self._get_or_create_card(card_data)
        
        if card_id:
            await self._db.execute(
                """INSERT INTO deck_cards (deck_id, card_id, quantity, is_commander)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (deck_id, card_id, is_sideboard) 
                   DO UPDATE SET quantity = EXCLUDED.quantity""",
                deck_id, card_id, 
                card_data.get('quantity', 1),
                card_data.get('is_commander', False)
            )
    
    async def _get_or_create_card(self, card_data: Dict[str, Any]) -> Optional[Any]:
        """Busca ou cria uma carta"""
        card_name = card_data.get('name', '')
        if not card_name:
            return None
        
        # Verificar se carta já existe
        card_id = await self._db.fetchval(
            "SELECT id FROM cards WHERE name = $1 LIMIT 1",
            card_name
        )
        
        if card_id:
            return card_id
        
        # Criar nova carta
        try:
            new_card_id = await self._db.fetchval(
                """INSERT INTO cards (name, mana_cost, converted_mana_cost, type_line, 
                                     colors, color_identity, rarity, set_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
                card_name,
                card_data.get('mana_cost', ''),
                card_data.get('cmc', 0),
                card_data.get('type_line', ''),
                card_data.get('colors', []),
                card_data.get('color_identity', []),
                card_data.get('rarity', 'common'),
                1  # Default set_id
            )
            
            logger.debug(f"Carta criada: {card_name} (ID: {new_card_id})")
            return new_card_id
            
        except Exception as e:
            logger.error(f"Erro ao criar carta {card_name}: {e}")
            return None
    
    async def get_deck_count(self) -> int:
        """Retorna total de decks"""
        count = await self._db.fetchval("SELECT COUNT(*) FROM decks")
        return count or 0
    
    async def get_decks_for_export(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca decks para exportação"""
        query = """
            SELECT d.id, d.name, d.description, d.colors, d.total_cards, 
                   d.estimated_price, d.created_at, u.name as user_name,
                   gf.name as format_name
            FROM decks d
            LEFT JOIN users u ON d.user_id = u.id
            LEFT JOIN game_formats gf ON d.format_id = gf.id
            ORDER BY d.created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        records = await self._db.fetch(query)
        return self.records_to_dict_list(records)


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