"""
Infrastructure Layer - Serviços Mock
Implementações temporárias para desenvolvimento e teste
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from ...domain.interfaces import (
    IDeckLoadingService,
    IDataExportService,
    IModelTrainingService,
    ModelType,
    ModelVersion,
    ModelStatus,
    BatchResult
)

logger = logging.getLogger(__name__)


class MockDeckLoadingService(IDeckLoadingService):
    """Serviço mock para carregamento de decks"""
    
    async def load_decks(self, count: int, source: str = "archidekt") -> BatchResult:
        """Carrega decks de uma fonte"""
        return await self.load_decks_from_source(source, count)
    
    async def load_decks_from_source(
        self, 
        source: str, 
        limit: Optional[int] = None,
        batch_size: int = 100
    ) -> BatchResult:
        """Simula carregamento de decks"""
        logger.info(f"Mock: Carregando decks da fonte {source}")
        
        # Simular processamento
        await asyncio.sleep(1)
        
        # Simular resultados
        processed = min(limit or 1000, 1000)
        success_rate = 0.95
        success_count = int(processed * success_rate)
        error_count = processed - success_count
        
        errors = []
        if error_count > 0:
            errors = [f"Erro simulado {i+1}" for i in range(min(error_count, 3))]
        
        return BatchResult(
            operation_type="load_decks",
            total_processed=processed,
            successful=success_count,
            failed=error_count,
            errors=errors,
            execution_time_seconds=1.0,
            output_files=[],
            metadata={
                "source": source,
                "batch_size": batch_size,
                "success_rate": success_rate
            }
        )


class MockDataExportService(IDataExportService):
    """Serviço mock para exportação de dados"""
    
    async def export_to_parquet(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        compression: str = "snappy"
    ) -> str:
        """Simula exportação para parquet"""
        logger.info(f"Mock: Exportando {len(data)} registros para {output_path}")
        
        # Simular processamento
        await asyncio.sleep(0.5)
        
        # Retornar caminho do arquivo gerado
        return output_path
    
    async def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        output_path: str
    ) -> str:
        """Simula exportação para CSV"""
        logger.info(f"Mock: Exportando {len(data)} registros para CSV")
        
        await asyncio.sleep(0.3)
        
        # Retornar caminho do arquivo gerado
        return output_path


class MockModelTrainingService(IModelTrainingService):
    """Serviço mock para treinamento de modelos"""
    
    async def train_model(
        self,
        model_type: ModelType,
        config: Dict[str, Any]
    ) -> ModelVersion:
        """Simula treinamento de modelo"""
        logger.info(f"Mock: Treinando modelo {model_type.value}")
        
        # Simular treinamento
        epochs = config.get('epochs', 10)
        await asyncio.sleep(epochs * 0.1)  # Simular tempo de treinamento
        
        # Gerar versão
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{model_type.value}_{version}"
        
        # Simular métricas baseadas no tipo de modelo
        if model_type == ModelType.CARD_RECOMMENDATION:
            performance_metrics = {
                "accuracy": 0.85 + (epochs * 0.01),
                "loss": 0.5 - (epochs * 0.02),
                "val_accuracy": 0.82 + (epochs * 0.008),
                "val_loss": 0.55 - (epochs * 0.015)
            }
        elif model_type == ModelType.WIN_RATE_PREDICTOR:
            performance_metrics = {
                "mae": 0.1 - (epochs * 0.005),
                "mse": 0.02 - (epochs * 0.001),
                "val_mae": 0.12 - (epochs * 0.004),
                "val_mse": 0.025 - (epochs * 0.0008)
            }
        else:
            performance_metrics = {
                "accuracy": 0.80 + (epochs * 0.008),
                "f1_score": 0.78 + (epochs * 0.009)
            }
        
        # Criar modelo
        model = ModelVersion(
            id=None,  # Será definido pelo repositório
            model_name=model_name,
            version=version,
            model_type=model_type,
            file_path=f"./models/{model_name}/model.keras",
            file_size_bytes=2000000 + (epochs * 50000),  # ~2MB base + crescimento
            tensorflow_version="2.20.0",
            architecture_config={
                "layers": config.get('layers', 5),
                "input_shape": config.get('input_shape', [50]),
                "output_shape": config.get('output_shape', [10]),
                "total_params": config.get('total_params', 15000)
            },
            training_config={
                "epochs": epochs,
                "batch_size": config.get('batch_size', 32),
                "learning_rate": config.get('learning_rate', 0.001),
                "optimizer": config.get('optimizer', "adam")
            },
            performance_metrics=performance_metrics,
            status=ModelStatus.TRAINED,
            is_active=False,
            is_default=False,
            created_at=datetime.now(),
            trained_at=datetime.now(),
            activated_at=None,
            created_by="mock_training",
            tags=config.get('tags', []),
            description=config.get('description') or f"Modelo {model_type.value} treinado automaticamente",
            training_notes=f"Modelo treinado via mock service com {epochs} épocas"
        )
        
        logger.info(f"Mock: Modelo {model_name} treinado com sucesso")
        return model
    
    async def validate_model(self, model_version: ModelVersion) -> Dict[str, Any]:
        """Simula validação de modelo"""
        logger.info(f"Mock: Validando modelo {model_version.model_name}")
        
        await asyncio.sleep(0.2)
        
        # Simular validação
        validation_metrics = {
            "validation_passed": True,
            "test_accuracy": (model_version.performance_metrics or {}).get("accuracy", 0.8) * 0.95,
            "robustness_score": 0.88,
            "consistency_score": 0.92
        }
        
        return validation_metrics
    
    async def deploy_model(self, model: ModelVersion, environment: str) -> bool:
        """Simula deploy de modelo"""
        logger.info(f"Mock: Fazendo deploy do modelo {model.model_name} para {environment}")
        
        await asyncio.sleep(0.3)
        
        # Simular sucesso na maioria dos casos
        return True