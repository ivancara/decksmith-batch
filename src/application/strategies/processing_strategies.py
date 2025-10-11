"""
Application Layer - Estratégias de Processamento
Implementando Strategy Pattern para diferentes operações
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from ...domain.interfaces import (
    IProcessingStrategy, 
    BatchResult, 
    IDeckLoadingService, 
    IDataExportService,
    IModelTrainingService,
    IModelVersionRepository,
    IDeckRepository,
    IConfigurationManager,
    ModelType,
    ExportFormat
)

logger = logging.getLogger(__name__)


class DeckLoadingStrategy(IProcessingStrategy):
    """Estratégia para carregamento de decks"""
    
    def __init__(
        self, 
        deck_service: IDeckLoadingService,
        config_manager: IConfigurationManager
    ):
        self._deck_service = deck_service
        self._config_manager = config_manager
    
    async def execute(self, params: Dict[str, Any]) -> BatchResult:
        """Executa carregamento de decks"""
        start_time = datetime.now()
        
        try:
            count = params.get('count', 100)
            source = params.get('source', 'archidekt')
            
            logger.info(f"🚀 Iniciando carregamento de {count} decks da fonte {source}")
            
            # Carregar decks
            result = await self._deck_service.load_decks(count, source)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Carregamento concluído: {result.successful}/{result.total_processed} decks em {execution_time:.2f}s")
            
            return BatchResult(
                operation_type="deck_loading",
                total_processed=result.total_processed,
                successful=result.successful,
                failed=result.failed,
                errors=result.errors,
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={
                    "source": source,
                    "requested_count": count,
                    "decks_per_second": result.successful / execution_time if execution_time > 0 else 0
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Erro no carregamento de decks: {e}")
            
            return BatchResult(
                operation_type="deck_loading",
                total_processed=0,
                successful=0,
                failed=1,
                errors=[str(e)],
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "DeckLoadingStrategy"
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Valida parâmetros de entrada"""
        count = params.get('count')
        if count is not None and (not isinstance(count, int) or count <= 0):
            return False
        
        source = params.get('source', 'archidekt')
        if source not in ['archidekt', 'edhrec', 'tappedout']:
            return False
        
        return True


class DataExportStrategy(IProcessingStrategy):
    """Estratégia para exportação de dados para Parquet"""
    
    def __init__(
        self,
        deck_repository: IDeckRepository,
        export_service: IDataExportService,
        config_manager: IConfigurationManager
    ):
        self._deck_repository = deck_repository
        self._export_service = export_service
        self._config_manager = config_manager
    
    async def execute(self, params: Dict[str, Any]) -> BatchResult:
        """Executa exportação de dados"""
        start_time = datetime.now()
        
        try:
            # Parâmetros
            export_format = ExportFormat(params.get('format', 'parquet'))
            limit = params.get('limit')
            output_path = params.get('output_path')
            
            # Configurações
            export_config = await self._config_manager.get_export_config()
            
            if not output_path:
                base_path = export_config.get('base_path', './exports')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"decks_export_{timestamp}"
                
                if export_format == ExportFormat.PARQUET:
                    output_path = f"{base_path}/{filename}.parquet"
                elif export_format == ExportFormat.CSV:
                    output_path = f"{base_path}/{filename}.csv"
                else:
                    output_path = f"{base_path}/{filename}.json"
            
            # Criar diretório se não existir
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📊 Iniciando exportação de dados para {output_path}")
            
            # Buscar dados
            deck_data = await self._deck_repository.get_decks_for_export(limit)
            
            if not deck_data:
                raise ValueError("Nenhum dado encontrado para exportação")
            
            # Exportar conforme formato
            output_file = ""
            if export_format == ExportFormat.PARQUET:
                output_file = await self._export_service.export_to_parquet(deck_data, output_path)
            elif export_format == ExportFormat.CSV:
                output_file = await self._export_service.export_to_csv(deck_data, output_path)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Exportação concluída: {len(deck_data)} registros em {execution_time:.2f}s")
            
            return BatchResult(
                operation_type="data_export",
                total_processed=len(deck_data),
                successful=len(deck_data),
                failed=0,
                errors=[],
                execution_time_seconds=execution_time,
                output_files=[output_file],
                metadata={
                    "format": export_format.value,
                    "output_path": output_file,
                    "file_size_mb": Path(output_file).stat().st_size / (1024 * 1024) if Path(output_file).exists() else 0,
                    "records_per_second": len(deck_data) / execution_time if execution_time > 0 else 0
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Erro na exportação de dados: {e}")
            
            return BatchResult(
                operation_type="data_export",
                total_processed=0,
                successful=0,
                failed=1,
                errors=[str(e)],
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "DataExportStrategy"
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Valida parâmetros de entrada"""
        format_param = params.get('format', 'parquet')
        try:
            ExportFormat(format_param)
        except ValueError:
            return False
        
        limit = params.get('limit')
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            return False
        
        return True


class ModelTrainingStrategy(IProcessingStrategy):
    """Estratégia para treinamento de modelos ML"""
    
    def __init__(
        self,
        training_service: IModelTrainingService,
        model_repository: IModelVersionRepository,
        config_manager: IConfigurationManager
    ):
        self._training_service = training_service
        self._model_repository = model_repository
        self._config_manager = config_manager
    
    async def execute(self, params: Dict[str, Any]) -> BatchResult:
        """Executa treinamento de modelo"""
        start_time = datetime.now()
        
        try:
            # Parâmetros
            model_type_str = params.get('model_type', 'card_recommendation')
            model_type = ModelType(model_type_str)
            training_config = params.get('config', {})
            auto_activate = params.get('auto_activate', False)
            
            logger.info(f"🤖 Iniciando treinamento do modelo {model_type.value}")
            
            # Configurações do sistema
            ml_config = await self._config_manager.get_ml_models_config()
            
            # Mesclar configurações
            final_config = {**ml_config, **training_config}
            
            # Treinar modelo
            model_version = await self._training_service.train_model(model_type, final_config)
            
            # Salvar no repositório
            saved_model = await self._model_repository.save_model_version(model_version)
            
            # Validar modelo
            validation_metrics = await self._training_service.validate_model(saved_model)
            
            # Ativar automaticamente se solicitado
            if auto_activate:
                await self._model_repository.activate_model_version(model_type, saved_model.version)
                logger.info(f"🎯 Modelo {model_type.value} v{saved_model.version} ativado automaticamente")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Treinamento concluído: {model_type.value} v{saved_model.version} em {execution_time:.2f}s")
            
            return BatchResult(
                operation_type="model_training",
                total_processed=1,
                successful=1,
                failed=0,
                errors=[],
                execution_time_seconds=execution_time,
                output_files=[saved_model.file_path],
                metadata={
                    "model_type": model_type.value,
                    "model_version": saved_model.version,
                    "model_id": saved_model.id,
                    "file_path": saved_model.file_path,
                    "file_size_mb": saved_model.file_size_bytes / (1024 * 1024),
                    "performance_metrics": saved_model.performance_metrics,
                    "validation_metrics": validation_metrics,
                    "auto_activated": auto_activate,
                    "tensorflow_version": saved_model.tensorflow_version
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Erro no treinamento do modelo: {e}")
            
            return BatchResult(
                operation_type="model_training",
                total_processed=1,
                successful=0,
                failed=1,
                errors=[str(e)],
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={"error": str(e)}
            )
    
    def get_strategy_name(self) -> str:
        return "ModelTrainingStrategy"
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Valida parâmetros de entrada"""
        model_type_str = params.get('model_type', 'card_recommendation')
        try:
            ModelType(model_type_str)
        except ValueError:
            return False
        
        config = params.get('config', {})
        if not isinstance(config, dict):
            return False
        
        auto_activate = params.get('auto_activate', False)
        if not isinstance(auto_activate, bool):
            return False
        
        return True


class StrategyFactory:
    """Factory para criar estratégias (Factory Pattern)"""
    
    def __init__(
        self,
        deck_service: IDeckLoadingService,
        export_service: IDataExportService,
        training_service: IModelTrainingService,
        deck_repository: IDeckRepository,
        model_repository: IModelVersionRepository,
        config_manager: IConfigurationManager
    ):
        self._deck_service = deck_service
        self._export_service = export_service
        self._training_service = training_service
        self._deck_repository = deck_repository
        self._model_repository = model_repository
        self._config_manager = config_manager
    
    def create_strategy(self, strategy_type: str) -> IProcessingStrategy:
        """Cria estratégia baseada no tipo"""
        strategies = {
            "deck_loading": lambda: DeckLoadingStrategy(
                self._deck_service,
                self._config_manager
            ),
            "data_export": lambda: DataExportStrategy(
                self._deck_repository,
                self._export_service,
                self._config_manager
            ),
            "model_training": lambda: ModelTrainingStrategy(
                self._training_service,
                self._model_repository,
                self._config_manager
            )
        }
        
        if strategy_type not in strategies:
            raise ValueError(f"Estratégia não suportada: {strategy_type}")
        
        return strategies[strategy_type]()
    
    def get_available_strategies(self) -> List[str]:
        """Retorna lista de estratégias disponíveis"""
        return ["deck_loading", "data_export", "model_training"]