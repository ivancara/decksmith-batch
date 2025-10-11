"""
Infrastructure Layer - Container de Dependências
Implementação de Dependency Injection seguindo SOLID e Clean Architecture
"""

from typing import Dict, Any, Optional
import logging

from ...domain.interfaces import (
    IAdminSettingsRepository,
    IModelVersionRepository,
    IDeckRepository,
    IConfigurationManager,
    IProcessingStrategy,
    ICommand
)

from ..persistence.repositories import (
    InMemoryAdminSettingsRepository,
    InMemoryModelVersionRepository,
    InMemoryDeckRepository,
    ConfigurationManager
)

from ..services.mock_services import (
    MockDeckLoadingService,
    MockDataExportService,
    MockModelTrainingService
)

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Container de dependências para injeção de dependência"""
    
    def __init__(self):
        self._repositories: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._strategies: Dict[str, Any] = {}
        self._commands: Dict[str, Any] = {}
        self._config_manager: Optional[IConfigurationManager] = None
        
        # Inicializar container
        self._initialize_repositories()
        self._initialize_config_manager()
        self._initialize_services()
        self._initialize_factories()
    
    def _initialize_repositories(self):
        """Inicializa repositórios"""
        # Repositórios em memória para desenvolvimento/teste
        self._repositories['admin_settings'] = InMemoryAdminSettingsRepository()
        self._repositories['model_versions'] = InMemoryModelVersionRepository()
        self._repositories['decks'] = InMemoryDeckRepository()
        
        logger.info("Repositórios inicializados")
    
    def _initialize_config_manager(self):
        """Inicializa gerenciador de configuração"""
        settings_repo = self.get_repository('admin_settings')
        self._config_manager = ConfigurationManager(settings_repo)
        
        logger.info("Gerenciador de configuração inicializado")
    
    def _initialize_services(self):
        """Inicializa serviços de domínio"""
        # Serviços mock para desenvolvimento
        self._services['deck_loading'] = MockDeckLoadingService()
        self._services['data_export'] = MockDataExportService()
        self._services['model_training'] = MockModelTrainingService()
        
        logger.info("Serviços inicializados")
    
    def _initialize_factories(self):
        """Inicializa factories"""
        # Importação lazy para evitar dependências circulares
        try:
            from ...application.strategies.processing_strategies import StrategyFactory
            from ...application.commands.batch_commands import CommandFactory
            
            # Strategy Factory
            self._strategies['factory'] = StrategyFactory(
                deck_service=self._services['deck_loading'],
                export_service=self._services['data_export'],
                training_service=self._services['model_training'],
                deck_repository=self.get_repository('decks'),
                model_repository=self.get_repository('model_versions'),
                config_manager=self._config_manager
            )
            
            # Command Factory  
            self._commands['factory'] = CommandFactory(
                strategy_factory=self._strategies['factory']
            )
            
            logger.info("Factories inicializadas")
        except ImportError as e:
            logger.warning(f"Não foi possível inicializar factories: {e}")
    
    # Métodos para obter repositórios
    def get_repository(self, name: str) -> Any:
        """Obtém repositório por nome"""
        if name not in self._repositories:
            raise ValueError(f"Repositório '{name}' não encontrado")
        return self._repositories[name]
    
    def get_admin_settings_repository(self) -> IAdminSettingsRepository:
        """Obtém repositório de configurações administrativas"""
        return self.get_repository('admin_settings')
    
    def get_model_version_repository(self) -> IModelVersionRepository:
        """Obtém repositório de versões de modelos"""
        return self.get_repository('model_versions')
    
    def get_deck_repository(self) -> IDeckRepository:
        """Obtém repositório de decks"""
        return self.get_repository('decks')
    
    # Métodos para obter serviços
    def get_service(self, name: str) -> Any:
        """Obtém serviço por nome"""
        if name not in self._services:
            raise ValueError(f"Serviço '{name}' não encontrado")
        return self._services[name]
    
    def get_config_manager(self) -> IConfigurationManager:
        """Obtém gerenciador de configuração"""
        if self._config_manager is None:
            raise ValueError("Gerenciador de configuração não inicializado")
        return self._config_manager
    
    # Métodos para obter strategies
    def get_strategy_factory(self):
        """Obtém factory de strategies"""
        if 'factory' not in self._strategies:
            raise ValueError("Strategy factory não inicializada")
        return self._strategies['factory']
    
    def get_strategy(self, strategy_type: str) -> IProcessingStrategy:
        """Obtém strategy por tipo"""
        factory = self.get_strategy_factory()
        return factory.create_strategy(strategy_type)
    
    # Métodos para obter commands
    def get_command_factory(self):
        """Obtém factory de commands"""
        if 'factory' not in self._commands:
            raise ValueError("Command factory não inicializada")
        return self._commands['factory']
    
    def get_command(self, command_type: str, **kwargs) -> ICommand:
        """Obtém command por tipo"""
        factory = self.get_command_factory()
        return factory.create_command(command_type, **kwargs)
    
    # Métodos de configuração
    def configure_repository(self, name: str, repository: Any):
        """Configura repositório personalizado"""
        self._repositories[name] = repository
        logger.info(f"Repositório '{name}' configurado")
    
    def configure_service(self, name: str, service: Any):
        """Configura serviço personalizado"""
        self._services[name] = service
        logger.info(f"Serviço '{name}' configurado")
    
    # Health check
    def health_check(self) -> Dict[str, str]:
        """Verifica saúde do container"""
        status = {
            'repositories': 'OK' if self._repositories else 'ERROR',
            'config_manager': 'OK' if self._config_manager else 'ERROR',
            'strategy_factory': 'OK' if 'factory' in self._strategies else 'ERROR',
            'command_factory': 'OK' if 'factory' in self._commands else 'ERROR'
        }
        
        overall_status = 'OK' if all(s == 'OK' for s in status.values()) else 'ERROR'
        status['overall'] = overall_status
        
        return status


# Instância global do container (Singleton pattern)
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Obtém instância global do container de dependências"""
    global _container
    if _container is None:
        _container = DependencyContainer()
        logger.info("Container de dependências inicializado")
    return _container


def reset_container():
    """Reseta container (útil para testes)"""
    global _container
    _container = None
    logger.info("Container de dependências resetado")


# Funções de conveniência para acesso direto
def get_admin_settings_repository() -> IAdminSettingsRepository:
    """Acesso direto ao repositório de configurações"""
    return get_container().get_admin_settings_repository()


def get_model_version_repository() -> IModelVersionRepository:
    """Acesso direto ao repositório de versões de modelos"""
    return get_container().get_model_version_repository()


def get_deck_repository() -> IDeckRepository:
    """Acesso direto ao repositório de decks"""
    return get_container().get_deck_repository()


def get_config_manager() -> IConfigurationManager:
    """Acesso direto ao gerenciador de configuração"""
    return get_container().get_config_manager()


def get_strategy(strategy_type: str) -> IProcessingStrategy:
    """Acesso direto a strategy"""
    return get_container().get_strategy(strategy_type)


def get_command(command_type: str, **kwargs) -> ICommand:
    """Acesso direto a command"""
    return get_container().get_command(command_type, **kwargs)