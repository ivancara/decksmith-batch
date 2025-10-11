"""
Application Layer - Comandos
Implementando Command Pattern para operações CLI
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...domain.interfaces import ICommand, BatchResult, IProcessingStrategy

logger = logging.getLogger(__name__)


class BaseCommand(ICommand):
    """Comando base com funcionalidades comuns"""
    
    def __init__(self, strategy: IProcessingStrategy):
        self._strategy = strategy
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
    
    async def execute(self) -> BatchResult:
        """Template method para execução de comandos"""
        self._start_time = datetime.now()
        
        try:
            logger.info(f"🚀 Executando comando: {self.get_description()}")
            
            # Validar parâmetros antes da execução
            params = self._get_execution_params()
            if not self._strategy.validate_params(params):
                raise ValueError("Parâmetros inválidos para o comando")
            
            # Executar estratégia
            result = await self._strategy.execute(params)
            
            self._end_time = datetime.now()
            
            if result.failed == 0:
                logger.info(f"✅ Comando concluído com sucesso em {result.execution_time_seconds:.2f}s")
            else:
                logger.warning(f"⚠️ Comando concluído com {result.failed} falhas em {result.execution_time_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            self._end_time = datetime.now()
            execution_time = (self._end_time - self._start_time).total_seconds()
            
            logger.error(f"❌ Erro na execução do comando: {e}")
            
            return BatchResult(
                operation_type=self._strategy.get_strategy_name(),
                total_processed=0,
                successful=0,
                failed=1,
                errors=[str(e)],
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={"command_error": str(e)}
            )
    
    def _get_execution_params(self) -> Dict[str, Any]:
        """Método abstrato para obter parâmetros de execução"""
        return {}
    
    def get_execution_time(self) -> float:
        """Retorna tempo de execução se comando já foi executado"""
        if self._start_time and self._end_time:
            return (self._end_time - self._start_time).total_seconds()
        return 0.0


class LoadDecksCommand(BaseCommand):
    """Comando para carregamento de decks"""
    
    def __init__(self, strategy: IProcessingStrategy, count: int = 100, source: str = "archidekt"):
        super().__init__(strategy)
        self._count = count
        self._source = source
    
    def _get_execution_params(self) -> Dict[str, Any]:
        return {
            "count": self._count,
            "source": self._source
        }
    
    def get_description(self) -> str:
        return f"Carregar {self._count} decks da fonte {self._source}"


class GenerateParquetCommand(BaseCommand):
    """Comando para geração de arquivo Parquet"""
    
    def __init__(
        self, 
        strategy: IProcessingStrategy, 
        format_type: str = "parquet",
        limit: Optional[int] = None,
        output_path: Optional[str] = None
    ):
        super().__init__(strategy)
        self._format_type = format_type
        self._limit = limit
        self._output_path = output_path
    
    def _get_execution_params(self) -> Dict[str, Any]:
        params = {"format": self._format_type}
        
        if self._limit:
            params["limit"] = self._limit
        
        if self._output_path:
            params["output_path"] = self._output_path
        
        return params
    
    def get_description(self) -> str:
        limit_desc = f" (limitado a {self._limit})" if self._limit else ""
        return f"Gerar arquivo {self._format_type.upper()}{limit_desc}"


class TrainModelCommand(BaseCommand):
    """Comando para treinamento de modelo"""
    
    def __init__(
        self, 
        strategy: IProcessingStrategy,
        model_type: str = "card_recommendation",
        training_config: Optional[Dict[str, Any]] = None,
        auto_activate: bool = False
    ):
        super().__init__(strategy)
        self._model_type = model_type
        self._training_config = training_config or {}
        self._auto_activate = auto_activate
    
    def _get_execution_params(self) -> Dict[str, Any]:
        return {
            "model_type": self._model_type,
            "config": self._training_config,
            "auto_activate": self._auto_activate
        }
    
    def get_description(self) -> str:
        auto_desc = " (ativar automaticamente)" if self._auto_activate else ""
        return f"Treinar modelo {self._model_type}{auto_desc}"


class CommandInvoker:
    """Invoker para executar comandos (Command Pattern)"""
    
    def __init__(self):
        self._history: list = []
    
    async def execute_command(self, command: ICommand) -> BatchResult:
        """Executa um comando e armazena no histórico"""
        result = await command.execute()
        
        # Armazenar no histórico
        self._history.append({
            "command": command.get_description(),
            "result": result,
            "timestamp": datetime.now(),
            "execution_time": getattr(command, 'get_execution_time', lambda: 0)()
        })
        
        return result
    
    def get_command_history(self) -> list:
        """Retorna histórico de comandos executados"""
        return self._history.copy()
    
    def get_last_command_result(self) -> Optional[Dict[str, Any]]:
        """Retorna resultado do último comando executado"""
        if self._history:
            return self._history[-1]
        return None
    
    def clear_history(self):
        """Limpa histórico de comandos"""
        self._history.clear()


class CommandFactory:
    """Factory para criar comandos (Factory Pattern)"""
    
    def __init__(self, strategy_factory):
        self._strategy_factory = strategy_factory
    
    def create_command(self, command_type: str, **kwargs) -> ICommand:
        """Cria comando baseado no tipo"""
        command_creators = {
            "load_decks": self._create_load_decks_command,
            "generate_parquet": self._create_generate_parquet_command,
            "train_model": self._create_train_model_command
        }
        
        if command_type not in command_creators:
            raise ValueError(f"Tipo de comando não suportado: {command_type}")
        
        return command_creators[command_type](**kwargs)
    
    def _create_load_decks_command(self, **kwargs) -> LoadDecksCommand:
        """Cria comando de carregamento de decks"""
        count = kwargs.get('limit', 100)
        source = kwargs.get('source', 'archidekt')
        strategy = self._strategy_factory.create_strategy("deck_loading")
        return LoadDecksCommand(strategy, count, source)
    
    def _create_generate_parquet_command(self, **kwargs) -> GenerateParquetCommand:
        """Cria comando de geração de Parquet"""
        format_type = kwargs.get('format', 'parquet')
        limit = kwargs.get('limit')
        output_path = kwargs.get('output_path')
        strategy = self._strategy_factory.create_strategy("data_export")
        return GenerateParquetCommand(strategy, format_type, limit, output_path)
    
    def _create_train_model_command(self, **kwargs) -> TrainModelCommand:
        """Cria comando de treinamento de modelo"""
        model_type = kwargs.get('model_type', 'card_recommendation')
        
        # Montar config de treinamento
        training_config = {
            'epochs': kwargs.get('epochs', 10),
            'batch_size': kwargs.get('batch_size', 32),
            'learning_rate': kwargs.get('learning_rate', 0.001),
            'validation_split': kwargs.get('validation_split', 0.2),
            'description': kwargs.get('description'),
            'tags': kwargs.get('tags', [])
        }
        
        auto_activate = kwargs.get('auto_activate', False)
        strategy = self._strategy_factory.create_strategy("model_training")
        return TrainModelCommand(strategy, model_type, training_config, auto_activate)
    
    def create_load_decks_command(self, count: int = 100, source: str = "archidekt") -> LoadDecksCommand:
        """Cria comando de carregamento de decks"""
        strategy = self._strategy_factory.create_strategy("deck_loading")
        return LoadDecksCommand(strategy, count, source)
    
    def create_generate_parquet_command(
        self, 
        format_type: str = "parquet",
        limit: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> GenerateParquetCommand:
        """Cria comando de geração de Parquet"""
        strategy = self._strategy_factory.create_strategy("data_export")
        return GenerateParquetCommand(strategy, format_type, limit, output_path)
    
    def create_train_model_command(
        self,
        model_type: str = "card_recommendation",
        training_config: Optional[Dict[str, Any]] = None,
        auto_activate: bool = False
    ) -> TrainModelCommand:
        """Cria comando de treinamento de modelo"""
        strategy = self._strategy_factory.create_strategy("model_training")
        return TrainModelCommand(strategy, model_type, training_config, auto_activate)


class BatchCommandExecutor:
    """Executor para múltiplos comandos em sequência"""
    
    def __init__(self, invoker: CommandInvoker):
        self._invoker = invoker
    
    async def execute_batch(self, commands: list) -> Dict[str, Any]:
        """Executa múltiplos comandos em sequência"""
        start_time = datetime.now()
        results = []
        total_successful = 0
        total_failed = 0
        
        logger.info(f"🔄 Executando lote de {len(commands)} comandos")
        
        for i, command in enumerate(commands, 1):
            logger.info(f"📋 Comando {i}/{len(commands)}: {command.get_description()}")
            
            result = await self._invoker.execute_command(command)
            results.append(result)
            
            total_successful += result.successful
            total_failed += result.failed
            
            if result.failed > 0:
                logger.warning(f"⚠️ Comando {i} completou com falhas")
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        batch_result = {
            "batch_execution": {
                "total_commands": len(commands),
                "successful_operations": total_successful,
                "failed_operations": total_failed,
                "execution_time_seconds": total_time,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            "command_results": results
        }
        
        if total_failed == 0:
            logger.info(f"✅ Lote executado com sucesso: {total_successful} operações em {total_time:.2f}s")
        else:
            logger.warning(f"⚠️ Lote executado com falhas: {total_successful} sucessos, {total_failed} falhas em {total_time:.2f}s")
        
        return batch_result