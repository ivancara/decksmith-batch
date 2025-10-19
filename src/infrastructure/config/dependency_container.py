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
    PostgreSQLAdminSettingsRepository,
    PostgreSQLModelVersionRepository,
    PostgreSQLDeckRepository
)

from ..persistence.database_connection import DatabaseConnection

# Mock services removidos na implementação E4 - usando apenas serviços reais

from ..services.web_scraping_service import WebScrapingService
from ..services.data_export_service import ParquetDataExportService
from ..services.ml_training_service import TensorFlowMLService

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Container de dependências para injeção de dependência"""
    
    def __init__(self, use_real_services: bool = True):
        self._repositories: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._strategies: Dict[str, Any] = {}
        self._commands: Dict[str, Any] = {}
        self._config_manager: Optional[IConfigurationManager] = None
        self._database_connection: Optional[DatabaseConnection] = None
        self._use_real_services = use_real_services
        
        # Inicializar container
        self._initialize_config_manager()
        self._initialize_database_connection()
        self._initialize_repositories()
        self._initialize_services()
        self._initialize_factories()
    
    def _initialize_database_connection(self):
        """Inicializa conexão com banco de dados"""
        if not self._use_real_services:
            return
            
        try:
            if self._config_manager:
                self._database_connection = DatabaseConnection(self._config_manager)
                logger.info("Conexão com banco de dados inicializada")
            else:
                logger.warning("Config manager não disponível para conexão DB")
        except Exception as e:
            logger.error(f"Erro ao inicializar conexão DB: {e}")
            self._database_connection = None

    def _initialize_repositories(self):
        """Inicializa repositórios"""
        if self._use_real_services and self._database_connection:
            # Usar repositórios PostgreSQL em produção
            try:
                self._repositories['admin_settings'] = PostgreSQLAdminSettingsRepository(
                    self._database_connection
                )
                self._repositories['model_versions'] = PostgreSQLModelVersionRepository(
                    self._database_connection
                )
                self._repositories['decks'] = PostgreSQLDeckRepository(
                    self._database_connection
                )
                logger.info("Repositórios PostgreSQL inicializados")
            except Exception as e:
                logger.error(f"Erro ao inicializar repositórios PostgreSQL: {e}")
                # Fallback para repositórios em memória
                self._initialize_memory_repositories()
        else:
            # Usar repositórios em memória para desenvolvimento/teste
            self._initialize_memory_repositories()
    
    def _initialize_memory_repositories(self):
        """Inicializa repositórios em memória"""
        self._repositories['admin_settings'] = InMemoryAdminSettingsRepository()
        self._repositories['model_versions'] = InMemoryModelVersionRepository()
        self._repositories['decks'] = InMemoryDeckRepository()
        logger.info("Repositórios em memória inicializados")
    
    def _initialize_config_manager(self):
        """Inicializa gerenciador de configuração"""
        from .config_manager import EnvironmentConfigManager
        self._config_manager = EnvironmentConfigManager()
        
        # Carregar configurações do admin_settings se disponível
        try:
            settings_repo = self.get_repository('admin_settings')
            if hasattr(self._config_manager, 'load_admin_settings'):
                import asyncio
                asyncio.create_task(self._config_manager.load_admin_settings(settings_repo))
        except Exception as e:
            logger.warning(f"Não foi possível carregar admin_settings: {e}")
        
        logger.info("Gerenciador de configuração inicializado")
    
    def _initialize_services(self):
        """Inicializa serviços de domínio"""
        if self._use_real_services:
            # Usar serviços reais em produção
            try:
                # Configurações para scraping service
                scraping_config = None
                if self._config_manager:
                    scraping_config = self._config_manager.get_scraping_config()
                
                self._services['deck_loading'] = WebScrapingService(scraping_config)
                
                # Configurações para export service
                export_config = None
                ml_config = None
                
                if self._config_manager:
                    import asyncio
                    loop = None
                    try:
                        # Criar um loop se não existir
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Executar as funções async
                        export_config = loop.run_until_complete(
                            self._config_manager.get_export_config()
                        )
                        ml_config = loop.run_until_complete(
                            self._config_manager.get_ml_models_config()
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao obter configurações: {e}")
                
                self._services['data_export'] = ParquetDataExportService(export_config)
                self._services['model_training'] = TensorFlowMLService(ml_config)
                
                logger.info("Serviços reais inicializados")
            except Exception as e:
                logger.error(f"Erro ao inicializar serviços reais: {e}")
                # E4: Fallback para mock removido - sistema requer serviços reais
                raise RuntimeError(f"E4: Falha crítica - serviços reais obrigatórios: {e}")
        else:
            # E4: Modo de desenvolvimento também usa serviços reais
            logger.info("E4: Modo desenvolvimento com serviços reais (mocks removidos)")
            self._initialize_mock_services()  # Tentará usar implementação real
    
    def _initialize_mock_services(self):
        """REMOVIDO E4: Serviços mock substituídos por implementações reais"""
        # E4: Fallback removido - sempre usar serviços reais
        logger.error("Serviços mock removidos na implementação E4")
        logger.info("Tentando reinicializar serviços reais...")
        
        # Forçar inicialização de serviços reais
        try:
            scraping_config = None
            if self._config_manager:
                scraping_config = self._config_manager.get_scraping_config()
            
            self._services['deck_loading'] = WebScrapingService(scraping_config)
            
            # Configurações básicas se config manager falhar
            export_config = {'output_directory': './results'}
            ml_config = {'model_directory': './models'}
            
            self._services['data_export'] = ParquetDataExportService(export_config)
            self._services['model_training'] = TensorFlowMLService(ml_config)
            
            logger.info("Serviços reais inicializados como fallback")
        except Exception as e:
            logger.critical(f"ERRO CRÍTICO E4: Não foi possível inicializar serviços reais: {e}")
            raise RuntimeError("E4: Sistema requer serviços reais - mocks removidos")
    
    def _initialize_factories(self):
        """Inicializa factories"""
        if self._config_manager is None:
            logger.error("Config manager não inicializado")
            return
            
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
    
    def get_database_connection(self) -> Optional[DatabaseConnection]:
        """Obtém conexão com banco de dados"""
        return self._database_connection
    
    def use_real_services(self) -> bool:
        """Verifica se está usando serviços reais"""
        return self._use_real_services
    
    def switch_to_mock_services(self):
        """E4: REMOVIDO - Serviços mock não disponíveis na implementação E4"""
        logger.error("E4: Tentativa de usar serviços mock - funcionalidade removida")
        raise NotImplementedError("E4: Serviços mock removidos - apenas serviços reais disponíveis")
    
    def switch_to_real_services(self):
        """Alterna para serviços reais"""
        self._use_real_services = True
        self._initialize_database_connection()
        self._initialize_repositories()
        self._initialize_services()
        logger.info("Alternado para serviços reais")
    
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


def get_container(use_real_services: bool = True) -> DependencyContainer:
    """Obtém instância global do container de dependências"""
    global _container
    if _container is None:
        _container = DependencyContainer(use_real_services=use_real_services)
        logger.info(f"Container de dependências inicializado (real_services={use_real_services})")
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