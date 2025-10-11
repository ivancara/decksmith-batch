"""
DeckSmith Batch Processing System
Infrastructure Layer - Environment-Specific Configuration
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .config_manager import EnvironmentConfigManager


class Environment(Enum):
    """Enum dos ambientes disponíveis"""
    DEVELOPMENT = "development"
    HOMOLOGATION = "homologation"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Configuração do banco de dados"""
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str
    pool_min_size: int
    pool_max_size: int
    command_timeout: int


@dataclass
class MLConfig:
    """Configuração de Machine Learning"""
    models_directory: str
    data_directory: str
    temp_directory: str
    default_algorithm: str
    enable_deep_learning: bool
    tensorflow_config: Dict[str, Any]
    batch_size: int
    epochs: int
    learning_rate: float
    use_gpu: bool


@dataclass
class APIConfig:
    """Configuração da API"""
    base_url: str
    timeout: int
    max_retries: int
    rate_limit: int
    api_keys: Dict[str, str]


@dataclass
class MonitoringConfig:
    """Configuração de monitoramento"""
    enabled: bool
    sentry_dsn: str
    metrics_retention_days: int
    alert_webhooks: Dict[str, str]
    log_level: str


class EnvironmentAwareConfigManager(EnvironmentConfigManager):
    """Gerenciador de configurações com suporte a ambientes específicos"""
    
    def __init__(self, environment: Optional[str] = None):
        super().__init__()
        
        # Determinar ambiente
        self.environment = Environment(environment or self._detect_environment())
        
        # Carregar configurações específicas do ambiente
        self._load_environment_specific_config()
    
    def _detect_environment(self) -> str:
        """Detecta o ambiente baseado na branch Git ou variáveis de ambiente"""
        # 1. Verificar variável de ambiente explícita
        env_var = os.getenv("DECKSMITH_ENVIRONMENT", "").lower()
        if env_var in [e.value for e in Environment]:
            return env_var
        
        # 2. Detectar pela branch Git
        try:
            git_branch = self._get_current_git_branch()
            if git_branch:
                if git_branch == "main":
                    return Environment.PRODUCTION.value
                elif git_branch.startswith("release/") or git_branch == "homologation":
                    return Environment.HOMOLOGATION.value
                elif git_branch == "develop" or git_branch.startswith("feature/"):
                    return Environment.DEVELOPMENT.value
        except Exception:
            pass
        
        # 3. Detectar pelo Heroku
        if os.getenv("HEROKU_APP_NAME"):
            app_name = os.getenv("HEROKU_APP_NAME", "").lower()
            if "prod" in app_name:
                return Environment.PRODUCTION.value
            elif "hom" in app_name or "staging" in app_name:
                return Environment.HOMOLOGATION.value
            else:
                return Environment.DEVELOPMENT.value
        
        # 4. Padrão: desenvolvimento
        return Environment.DEVELOPMENT.value
    
    def _get_current_git_branch(self) -> Optional[str]:
        """Obtém a branch Git atual"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _load_environment_specific_config(self):
        """Carrega configurações específicas do ambiente"""
        # Carregar arquivo de configuração do ambiente
        config_file = Path(f"config/{self.environment.value}.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    env_config = json.load(f)
                
                # Adicionar configurações ao cache
                for key, value in env_config.items():
                    self._config_cache[key] = value
                    
            except Exception as e:
                print(f"Warning: Could not load environment config {config_file}: {e}")
        
        # Carregar configurações padrão baseadas no ambiente
        self._set_environment_defaults()
    
    def _set_environment_defaults(self):
        """Define configurações padrão baseadas no ambiente"""
        if self.environment == Environment.DEVELOPMENT:
            self._set_development_defaults()
        elif self.environment == Environment.HOMOLOGATION:
            self._set_homologation_defaults()
        elif self.environment == Environment.PRODUCTION:
            self._set_production_defaults()
    
    def _set_development_defaults(self):
        """Configurações padrão para desenvolvimento"""
        defaults = {
            # Database
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": 5432,
            "DATABASE_NAME": "decksmith_dev",
            "DATABASE_USER": "decksmith_user",
            "DATABASE_SSL_MODE": "disable",
            "DATABASE_POOL_MIN_SIZE": 2,
            "DATABASE_POOL_MAX_SIZE": 10,
            
            # ML
            "ML_ENABLE_DEEP_LEARNING": True,
            "ML_USE_GPU": False,
            "ML_BATCH_SIZE": 32,
            "ML_EPOCHS": 10,
            "ML_LEARNING_RATE": 0.001,
            "ML_MODELS_DIR": "./models_dev",
            "ML_DATA_DIR": "./data_dev",
            
            # API
            "API_TIMEOUT": 30,
            "API_MAX_RETRIES": 3,
            "API_RATE_LIMIT": 100,
            
            # Monitoring
            "MONITORING_ENABLED": True,
            "MONITORING_LOG_LEVEL": "DEBUG",
            "MONITORING_METRICS_RETENTION_DAYS": 7,
            
            # Scraping
            "SCRAPING_CONCURRENT_WORKERS": 2,
            "SCRAPING_DEFAULT_DELAY": 2.0,
            "SCRAPING_STEALTH_MODE": False,
            
            # Notifications
            "NOTIFICATIONS_ENABLED": False,
        }
        
        # Aplicar apenas se não estiver já definido
        for key, value in defaults.items():
            if key not in self._config_cache:
                self._config_cache[key] = value
    
    def _set_homologation_defaults(self):
        """Configurações padrão para homologação"""
        defaults = {
            # Database
            "DATABASE_HOST": os.getenv("DATABASE_URL_HOM", "").split("@")[-1].split("/")[0] if os.getenv("DATABASE_URL_HOM") else "",
            "DATABASE_NAME": "decksmith_hom",
            "DATABASE_SSL_MODE": "require",
            "DATABASE_POOL_MIN_SIZE": 5,
            "DATABASE_POOL_MAX_SIZE": 15,
            
            # ML
            "ML_ENABLE_DEEP_LEARNING": True,
            "ML_USE_GPU": False,
            "ML_BATCH_SIZE": 64,
            "ML_EPOCHS": 20,
            "ML_LEARNING_RATE": 0.0005,
            "ML_MODELS_DIR": "/app/models",
            "ML_DATA_DIR": "/app/data",
            
            # API
            "API_TIMEOUT": 45,
            "API_MAX_RETRIES": 5,
            "API_RATE_LIMIT": 200,
            
            # Monitoring
            "MONITORING_ENABLED": True,
            "MONITORING_LOG_LEVEL": "INFO",
            "MONITORING_METRICS_RETENTION_DAYS": 30,
            
            # Scraping
            "SCRAPING_CONCURRENT_WORKERS": 4,
            "SCRAPING_DEFAULT_DELAY": 1.5,
            "SCRAPING_STEALTH_MODE": True,
            
            # Notifications
            "NOTIFICATIONS_ENABLED": True,
            "NOTIFICATIONS_ON_ERROR": True,
        }
        
        for key, value in defaults.items():
            if key not in self._config_cache and value:
                self._config_cache[key] = value
    
    def _set_production_defaults(self):
        """Configurações padrão para produção"""
        defaults = {
            # Database
            "DATABASE_SSL_MODE": "require",
            "DATABASE_POOL_MIN_SIZE": 10,
            "DATABASE_POOL_MAX_SIZE": 30,
            "DATABASE_COMMAND_TIMEOUT": 120,
            
            # ML
            "ML_ENABLE_DEEP_LEARNING": True,
            "ML_USE_GPU": True,
            "ML_BATCH_SIZE": 128,
            "ML_EPOCHS": 50,
            "ML_LEARNING_RATE": 0.0001,
            "ML_MODELS_DIR": "/app/models",
            "ML_DATA_DIR": "/app/data",
            
            # API
            "API_TIMEOUT": 60,
            "API_MAX_RETRIES": 10,
            "API_RATE_LIMIT": 1000,
            
            # Monitoring
            "MONITORING_ENABLED": True,
            "MONITORING_LOG_LEVEL": "WARNING",
            "MONITORING_METRICS_RETENTION_DAYS": 90,
            
            # Scraping
            "SCRAPING_CONCURRENT_WORKERS": 8,
            "SCRAPING_DEFAULT_DELAY": 1.0,
            "SCRAPING_STEALTH_MODE": True,
            "SCRAPING_USE_PROXY": True,
            
            # Notifications
            "NOTIFICATIONS_ENABLED": True,
            "NOTIFICATIONS_ON_ERROR": True,
            "NOTIFICATIONS_ON_SUCCESS": False,
            "NOTIFICATIONS_ON_COMPLETION": True,
            
            # Security
            "SECURITY_RATE_LIMIT_ENABLED": True,
            "SECURITY_IP_WHITELIST": [],
        }
        
        for key, value in defaults.items():
            if key not in self._config_cache:
                self._config_cache[key] = value
    
    def get_database_config_typed(self) -> DatabaseConfig:
        """Obtém configuração do banco específica do ambiente"""
        # Parse Heroku DATABASE_URL se disponível
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return self._parse_database_url(database_url)
        
        return DatabaseConfig(
            host=self.get_config("DATABASE_HOST", "localhost"),
            port=self.get_config("DATABASE_PORT", 5432),
            database=self.get_config("DATABASE_NAME", f"decksmith_{self.environment.value}"),
            user=self.get_config("DATABASE_USER", "decksmith_user"),
            password=self.get_config("DATABASE_PASSWORD", ""),
            ssl_mode=self.get_config("DATABASE_SSL_MODE", "prefer"),
            pool_min_size=self.get_config("DATABASE_POOL_MIN_SIZE", 5),
            pool_max_size=self.get_config("DATABASE_POOL_MAX_SIZE", 20),
            command_timeout=self.get_config("DATABASE_COMMAND_TIMEOUT", 60)
        )
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtém configuração do banco como dict (compatibilidade)"""
        config = self.get_database_config_typed()
        return {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "user": config.user,
            "password": config.password,
            "ssl_mode": config.ssl_mode,
            "pool_min_size": config.pool_min_size,
            "pool_max_size": config.pool_max_size,
            "command_timeout": config.command_timeout
        }
    
    def _parse_database_url(self, database_url: str) -> DatabaseConfig:
        """Parse da URL do banco do Heroku"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            
            return DatabaseConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=parsed.path[1:] if parsed.path else "decksmith",
                user=parsed.username or "decksmith_user",
                password=parsed.password or "",
                ssl_mode="require" if self.environment != Environment.DEVELOPMENT else "prefer",
                pool_min_size=self.get_config("DATABASE_POOL_MIN_SIZE", 5),
                pool_max_size=self.get_config("DATABASE_POOL_MAX_SIZE", 20),
                command_timeout=self.get_config("DATABASE_COMMAND_TIMEOUT", 60)
            )
        except Exception:
            # Fallback para configuração padrão
            return self.get_database_config_typed()
    
    def get_ml_config_typed(self) -> MLConfig:
        """Obtém configuração de ML específica do ambiente"""
        return MLConfig(
            models_directory=self.get_config("ML_MODELS_DIR", "./models"),
            data_directory=self.get_config("ML_DATA_DIR", "./data"),
            temp_directory=self.get_config("ML_TEMP_DIR", "./temp"),
            default_algorithm=self.get_config("ML_DEFAULT_ALGORITHM", "deep_learning"),
            enable_deep_learning=self.get_config("ML_ENABLE_DEEP_LEARNING", True),
            tensorflow_config={
                "use_gpu": self.get_config("ML_USE_GPU", False),
                "memory_growth": self.get_config("ML_GPU_MEMORY_GROWTH", True),
                "mixed_precision": self.get_config("ML_MIXED_PRECISION", True),
            },
            batch_size=self.get_config("ML_BATCH_SIZE", 32),
            epochs=self.get_config("ML_EPOCHS", 10),
            learning_rate=self.get_config("ML_LEARNING_RATE", 0.001),
            use_gpu=self.get_config("ML_USE_GPU", False)
        )
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Obtém configuração de ML como dict (compatibilidade)"""
        config = self.get_ml_config_typed()
        return {
            "models_directory": config.models_directory,
            "data_directory": config.data_directory,
            "temp_directory": config.temp_directory,
            "default_algorithm": config.default_algorithm,
            "enable_deep_learning": config.enable_deep_learning,
            "tensorflow_config": config.tensorflow_config,
            "batch_size": config.batch_size,
            "epochs": config.epochs,
            "learning_rate": config.learning_rate,
            "use_gpu": config.use_gpu
        }
    
    def get_api_config(self) -> APIConfig:
        """Obtém configuração da API específica do ambiente"""
        # APIs diferentes por ambiente
        api_keys = {}
        
        if self.environment == Environment.DEVELOPMENT:
            api_keys = {
                "scryfall": self.get_config("SCRYFALL_API_KEY_DEV", ""),
                "edhrec": self.get_config("EDHREC_API_KEY_DEV", ""),
                "mtgjson": self.get_config("MTGJSON_API_KEY_DEV", ""),
            }
        elif self.environment == Environment.HOMOLOGATION:
            api_keys = {
                "scryfall": self.get_config("SCRYFALL_API_KEY_HOM", ""),
                "edhrec": self.get_config("EDHREC_API_KEY_HOM", ""),
                "mtgjson": self.get_config("MTGJSON_API_KEY_HOM", ""),
            }
        else:  # Production
            api_keys = {
                "scryfall": self.get_config("SCRYFALL_API_KEY_PROD", ""),
                "edhrec": self.get_config("EDHREC_API_KEY_PROD", ""),
                "mtgjson": self.get_config("MTGJSON_API_KEY_PROD", ""),
            }
        
        return APIConfig(
            base_url=self.get_config("API_BASE_URL", "https://api.decksmith.com"),
            timeout=self.get_config("API_TIMEOUT", 30),
            max_retries=self.get_config("API_MAX_RETRIES", 3),
            rate_limit=self.get_config("API_RATE_LIMIT", 100),
            api_keys=api_keys
        )
    
    def get_monitoring_config_typed(self) -> MonitoringConfig:
        """Obtém configuração de monitoramento específica do ambiente"""
        # Sentry DSN específico do ambiente
        sentry_dsn = ""
        if self.environment == Environment.DEVELOPMENT:
            sentry_dsn = self.get_config("SENTRY_DSN_DEV", "")
        elif self.environment == Environment.HOMOLOGATION:
            sentry_dsn = self.get_config("SENTRY_DSN_HOM", "")
        else:  # Production
            sentry_dsn = self.get_config("SENTRY_DSN_PROD", "")
        
        # Webhooks específicos do ambiente
        webhooks = {}
        if self.environment == Environment.DEVELOPMENT:
            webhooks = {
                "slack": self.get_config("SLACK_WEBHOOK_DEV", ""),
                "teams": self.get_config("TEAMS_WEBHOOK_DEV", ""),
            }
        elif self.environment == Environment.HOMOLOGATION:
            webhooks = {
                "slack": self.get_config("SLACK_WEBHOOK_HOM", ""),
                "teams": self.get_config("TEAMS_WEBHOOK_HOM", ""),
            }
        else:  # Production
            webhooks = {
                "slack": self.get_config("SLACK_WEBHOOK_PROD", ""),
                "teams": self.get_config("TEAMS_WEBHOOK_PROD", ""),
            }
        
        return MonitoringConfig(
            enabled=self.get_config("MONITORING_ENABLED", True),
            sentry_dsn=sentry_dsn,
            metrics_retention_days=self.get_config("MONITORING_METRICS_RETENTION_DAYS", 30),
            alert_webhooks=webhooks,
            log_level=self.get_config("MONITORING_LOG_LEVEL", "INFO")
        )
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Obtém configuração de monitoramento como dict (compatibilidade)"""
        config = self.get_monitoring_config_typed()
        return {
            "enabled": config.enabled,
            "sentry_dsn": config.sentry_dsn,
            "metrics_retention_days": config.metrics_retention_days,
            "alert_webhooks": config.alert_webhooks,
            "log_level": config.log_level
        }
    
    def get_environment_enum(self) -> Environment:
        """Retorna o ambiente atual como enum"""
        return self.environment
    
    def get_environment(self) -> str:
        """Retorna o ambiente atual como string (compatibilidade)"""
        return self.environment.value
    
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento"""
        return self.environment == Environment.DEVELOPMENT
    
    def is_homologation(self) -> bool:
        """Verifica se está em homologação"""
        return self.environment == Environment.HOMOLOGATION
    
    def is_production(self) -> bool:
        """Verifica se está em produção"""
        return self.environment == Environment.PRODUCTION
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Obtém informações detalhadas do ambiente"""
        db_config = self.get_database_config_typed()
        ml_config = self.get_ml_config_typed()
        monitoring_config = self.get_monitoring_config_typed()
        
        return {
            "environment": self.environment.value,
            "git_branch": self._get_current_git_branch(),
            "heroku_app": os.getenv("HEROKU_APP_NAME"),
            "database_name": db_config.database,
            "ml_config": {
                "enable_deep_learning": ml_config.enable_deep_learning,
                "use_gpu": ml_config.use_gpu,
                "batch_size": ml_config.batch_size,
            },
            "monitoring": {
                "enabled": monitoring_config.enabled,
                "log_level": monitoring_config.log_level,
            }
        }