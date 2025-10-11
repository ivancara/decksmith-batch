"""
Infrastructure Layer - Configuration Manager Implementation
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from ...domain.interfaces import IConfigurationManager


class EnvironmentConfigManager(IConfigurationManager):
    """Gerenciador de configurações baseado em variáveis de ambiente e admin_settings"""
    
    def __init__(self):
        self._config_cache: Dict[str, Any] = {}
        self._admin_settings_cache: Dict[str, Any] = {}
        self._load_environment_variables()
    
    def _load_environment_variables(self):
        """Carrega variáveis de ambiente para cache"""
        # Carregar arquivo .env se existir
        env_file = Path(".env")
        if env_file.exists():
            self._load_env_file(env_file)
        
        # Sobrescrever com variáveis de ambiente do sistema
        self._load_system_env()
    
    def _load_env_file(self, env_file: Path):
        """Carrega variáveis do arquivo .env"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        self._config_cache[key] = value
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")
    
    def _load_system_env(self):
        """Carrega variáveis de ambiente do sistema"""
        for key, value in os.environ.items():
            if key.startswith(('DECKSMITH_', 'DATABASE_', 'ML_', 'SCRAPING_', 'EXPORT_')):
                self._config_cache[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Obtém configuração (prioridade: admin_settings > env > default)"""
        # Tentar buscar do admin_settings primeiro
        admin_value = self._admin_settings_cache.get(key)
        if admin_value is not None:
            return self._convert_value(admin_value)
        
        # Fallback para variáveis de ambiente
        value = self._config_cache.get(key, default)
        return self._convert_value(value)
    
    def _convert_value(self, value: Any) -> Any:
        """Converte valor para tipo apropriado"""
        if isinstance(value, str):
            # Booleanos
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            
            # Números inteiros
            if value.isdigit():
                return int(value)
            
            # Números decimais
            try:
                if '.' in value:
                    return float(value)
            except ValueError:
                pass
            
            # JSON
            if value.startswith(('{', '[')):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
        
        return value
    
    def set_config(self, key: str, value: Any) -> bool:
        """Define configuração"""
        try:
            self._config_cache[key] = value
            return True
        except Exception:
            return False
    
    async def load_admin_settings(self, repository=None) -> bool:
        """Carrega configurações da tabela admin_settings"""
        if repository is None:
            return False
        
        try:
            # Buscar todas as configurações ativas
            settings = await repository.get_all_settings()
            
            # Atualizar cache
            self._admin_settings_cache.clear()
            for setting in settings:
                key = setting['setting_key']
                value = setting['setting_value']
                # Se for JSONB, já vem como valor deserializado
                if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]  # Remove aspas duplas para strings
                self._admin_settings_cache[key] = value
            
            return True
        except Exception as e:
            print(f"Warning: Could not load admin settings: {e}")
            return False
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtém configurações do banco"""
        return {
            "host": self.get_config("DATABASE_HOST", "localhost"),
            "port": self.get_config("DATABASE_PORT", 5432),
            "user": self.get_config("DATABASE_USER", "postgres"),
            "password": self.get_config("DATABASE_PASSWORD", ""),
            "database": self.get_config("DATABASE_NAME", "decksmith"),
            "pool_min_size": self.get_config("DATABASE_POOL_MIN_SIZE", 5),
            "pool_max_size": self.get_config("DATABASE_POOL_MAX_SIZE", 20),
            "command_timeout": self.get_config("DATABASE_COMMAND_TIMEOUT", 60),
            "ssl_mode": self.get_config("DATABASE_SSL_MODE", "prefer"),
            "application_name": self.get_config("DATABASE_APP_NAME", "decksmith_batch")
        }
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Obtém configurações de scraping"""
        return {
            "base_url": self.get_config("SCRAPING_BASE_URL", "https://ligamagic.com.br"),
            "user_agent": self.get_config("SCRAPING_USER_AGENT", "DeckSmith Bot 1.0"),
            "default_delay": self.get_config("SCRAPING_DEFAULT_DELAY", 1.0),
            "max_delay": self.get_config("SCRAPING_MAX_DELAY", 5.0),
            "timeout": self.get_config("SCRAPING_TIMEOUT", 30),
            "max_retries": self.get_config("SCRAPING_MAX_RETRIES", 3),
            "concurrent_workers": self.get_config("SCRAPING_CONCURRENT_WORKERS", 4),
            "use_proxy": self.get_config("SCRAPING_USE_PROXY", False),
            "proxy_list": self._parse_list(self.get_config("SCRAPING_PROXY_LIST", "")),
            "stealth_mode": self.get_config("SCRAPING_STEALTH_MODE", True),
            "rotate_headers": self.get_config("SCRAPING_ROTATE_HEADERS", True),
            "max_pages_per_session": self.get_config("SCRAPING_MAX_PAGES_PER_SESSION", 1000)
        }
    
    async def get_ml_models_config(self) -> Dict[str, Any]:
        """Obtém configurações de ML"""
        return {
            "models_directory": self.get_config("ml_models_base_path", "./models"),
            "max_versions": self.get_config("ml_models_max_versions_per_type", 10),
            "auto_cleanup": self.get_config("ml_models_auto_cleanup", True),
            "backup_enabled": self.get_config("ml_models_backup_enabled", True),
            "default_batch_size": self.get_config("ml_models_default_batch_size", 32),
            "inference_timeout": self.get_config("ml_models_inference_timeout", 30),
            "data_directory": self.get_config("ML_DATA_DIR", "./data"),
            "temp_directory": self.get_config("ML_TEMP_DIR", "./temp"),
            "default_algorithm": self.get_config("ML_DEFAULT_ALGORITHM", "deep_learning"),
            "training_split": self.get_config("ML_TRAINING_SPLIT", 0.8),
            "validation_split": self.get_config("ML_VALIDATION_SPLIT", 0.2),
            "cross_validation_folds": self.get_config("ML_CV_FOLDS", 5),
            "max_training_time_minutes": self.get_config("ML_MAX_TRAINING_TIME", 120),
            "early_stopping": self.get_config("ML_EARLY_STOPPING", True),
            "feature_selection": self.get_config("ML_FEATURE_SELECTION", True),
            "hyperparameter_tuning": self.get_config("ML_HYPERPARAMETER_TUNING", False),
            "model_versioning": self.get_config("ML_MODEL_VERSIONING", True),
            "metrics_tracking": self.get_config("ML_METRICS_TRACKING", True)
        }
    
    async def get_export_config(self) -> Dict[str, Any]:
        """Obtém configurações de exportação"""
        return {
            "output_directory": self.get_config("data_export_base_path", "./exports"),
            "default_format": self.get_config("data_export_format", "parquet"),
            "compression": self.get_config("data_export_compression", "snappy"),
            "max_file_size_mb": self.get_config("data_export_max_file_size_mb", 100),
            "include_metadata": self.get_config("data_export_include_metadata", True),
            "temp_directory": self.get_config("EXPORT_TEMP_DIR", "./temp"),
            "batch_size": self.get_config("EXPORT_BATCH_SIZE", 10000),
            "partition_by": self.get_config("EXPORT_PARTITION_BY", "formato"),
            "cleanup_temp_files": self.get_config("EXPORT_CLEANUP_TEMP", True),
            "verify_export": self.get_config("EXPORT_VERIFY", True),
            "backup_exports": self.get_config("EXPORT_BACKUP", False),
            "retention_days": self.get_config("EXPORT_RETENTION_DAYS", 30)
        }
    
    async def get_batch_processing_config(self) -> Dict[str, Any]:
        """Obtém configurações de processamento em lote"""
        return {
            "chunk_size": self.get_config("batch_processing_chunk_size", 1000),
            "max_parallel": self.get_config("batch_processing_max_parallel", 4),
            "timeout_minutes": self.get_config("batch_processing_timeout_minutes", 30),
            "memory_limit_gb": self.get_config("batch_processing_memory_limit_gb", 8)
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Obtém configurações de monitoramento"""
        return {
            "enabled": self.get_config("MONITORING_ENABLED", True),
            "metrics_retention_days": self.get_config("MONITORING_METRICS_RETENTION_DAYS", 30),
            "health_check_interval": self.get_config("MONITORING_HEALTH_CHECK_INTERVAL", 300),
            "alert_email": self.get_config("MONITORING_ALERT_EMAIL", ""),
            "webhook_url": self.get_config("MONITORING_WEBHOOK_URL", ""),
            "log_level": self.get_config("logging_level", "INFO"),
            "performance_tracking": self.get_config("MONITORING_PERFORMANCE_TRACKING", True),
            "error_tracking": self.get_config("MONITORING_ERROR_TRACKING", True),
            "sentry_dsn": self.get_config("MONITORING_SENTRY_DSN", "")
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Obtém configurações de segurança"""
        return {
            "api_key": self.get_config("DECKSMITH_API_KEY", ""),
            "secret_key": self.get_config("DECKSMITH_SECRET_KEY", ""),
            "jwt_secret": self.get_config("DECKSMITH_JWT_SECRET", ""),
            "encryption_key": self.get_config("DECKSMITH_ENCRYPTION_KEY", ""),
            "jwt_expiration_hours": self.get_config("security_jwt_expiration_hours", 24),
            "max_login_attempts": self.get_config("security_max_login_attempts", 5),
            "password_min_length": self.get_config("security_password_min_length", 8),
            "enable_2fa": self.get_config("security_enable_2fa", False),
            "rate_limit_enabled": self.get_config("SECURITY_RATE_LIMIT_ENABLED", True),
            "rate_limit_requests": self.get_config("api_rate_limit_per_minute", 60),
            "rate_limit_window": self.get_config("SECURITY_RATE_LIMIT_WINDOW", 3600),
            "ip_whitelist": self._parse_list(self.get_config("SECURITY_IP_WHITELIST", "")),
            "user_agent_verification": self.get_config("SECURITY_USER_AGENT_VERIFICATION", False)
        }
    
    def get_general_config(self) -> Dict[str, Any]:
        """Obtém configurações gerais"""
        return {
            "environment": self.get_config("system_environment", "development"),
            "max_concurrent_users": self.get_config("max_concurrent_users", 100),
            "feature_flags": self.get_config("feature_flags", {
                "model_versioning": True,
                "auto_export": True,
                "batch_metrics": True
            })
        }
    
    def reload_config(self) -> bool:
        """Recarrega configurações"""
        try:
            self._config_cache.clear()
            self._load_environment_variables()
            return True
        except Exception:
            return False
    
    def _parse_list(self, value: str, separator: str = ",") -> list:
        """Parse string separada por vírgulas em lista"""
        if not value:
            return []
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def get_environment(self) -> str:
        """Obtém ambiente atual"""
        return self.get_config("system_environment", "development")
    
    def is_production(self) -> bool:
        """Verifica se está em produção"""
        return self.get_environment().lower() == "production"
    
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento"""
        return self.get_environment().lower() == "development"
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obtém todas as configurações (para debug)"""
        # Retorna cópia sem dados sensíveis
        safe_config = {}
        sensitive_keys = ['password', 'secret', 'key', 'token', 'webhook']
        
        for key, value in {**self._config_cache, **self._admin_settings_cache}.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_config[key] = "***HIDDEN***"
            else:
                safe_config[key] = value
        
        return safe_config