"""
DeckSmith Batch Processing System
Infrastructure Layer - Configuration Manager Implementation
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from ...application.interfaces import IConfigManager


class EnvironmentConfigManager(IConfigManager):
    """Gerenciador de configurações baseado em variáveis de ambiente"""
    
    def __init__(self):
        self._config_cache: Dict[str, Any] = {}
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
        """Obtém configuração"""
        value = self._config_cache.get(key, default)
        
        # Tentar converter tipos básicos
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
        
        return value
    
    def set_config(self, key: str, value: Any) -> bool:
        """Define configuração"""
        try:
            self._config_cache[key] = value
            return True
        except Exception:
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
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Obtém configurações de ML"""
        return {
            "models_directory": self.get_config("ML_MODELS_DIR", "./models"),
            "data_directory": self.get_config("ML_DATA_DIR", "./data"),
            "temp_directory": self.get_config("ML_TEMP_DIR", "./temp"),
            "default_algorithm": self.get_config("ML_DEFAULT_ALGORITHM", "random_forest"),
            "training_split": self.get_config("ML_TRAINING_SPLIT", 0.8),
            "validation_split": self.get_config("ML_VALIDATION_SPLIT", 0.2),
            "cross_validation_folds": self.get_config("ML_CV_FOLDS", 5),
            "max_training_time_minutes": self.get_config("ML_MAX_TRAINING_TIME", 120),
            "early_stopping": self.get_config("ML_EARLY_STOPPING", True),
            "feature_selection": self.get_config("ML_FEATURE_SELECTION", True),
            "hyperparameter_tuning": self.get_config("ML_HYPERPARAMETER_TUNING", False),
            "model_versioning": self.get_config("ML_MODEL_VERSIONING", True),
            "backup_models": self.get_config("ML_BACKUP_MODELS", True),
            "metrics_tracking": self.get_config("ML_METRICS_TRACKING", True)
        }
    
    def get_export_config(self) -> Dict[str, Any]:
        """Obtém configurações de exportação"""
        return {
            "output_directory": self.get_config("EXPORT_OUTPUT_DIR", "./exports"),
            "temp_directory": self.get_config("EXPORT_TEMP_DIR", "./temp"),
            "default_format": self.get_config("EXPORT_DEFAULT_FORMAT", "parquet"),
            "compression": self.get_config("EXPORT_COMPRESSION", "snappy"),
            "batch_size": self.get_config("EXPORT_BATCH_SIZE", 10000),
            "max_file_size_mb": self.get_config("EXPORT_MAX_FILE_SIZE_MB", 500),
            "include_metadata": self.get_config("EXPORT_INCLUDE_METADATA", True),
            "partition_by": self.get_config("EXPORT_PARTITION_BY", "formato"),
            "cleanup_temp_files": self.get_config("EXPORT_CLEANUP_TEMP", True),
            "verify_export": self.get_config("EXPORT_VERIFY", True),
            "backup_exports": self.get_config("EXPORT_BACKUP", False),
            "retention_days": self.get_config("EXPORT_RETENTION_DAYS", 30)
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Obtém configurações de monitoramento"""
        return {
            "enabled": self.get_config("MONITORING_ENABLED", True),
            "metrics_retention_days": self.get_config("MONITORING_METRICS_RETENTION_DAYS", 30),
            "health_check_interval": self.get_config("MONITORING_HEALTH_CHECK_INTERVAL", 300),
            "alert_email": self.get_config("MONITORING_ALERT_EMAIL", ""),
            "webhook_url": self.get_config("MONITORING_WEBHOOK_URL", ""),
            "log_level": self.get_config("MONITORING_LOG_LEVEL", "INFO"),
            "performance_tracking": self.get_config("MONITORING_PERFORMANCE_TRACKING", True),
            "error_tracking": self.get_config("MONITORING_ERROR_TRACKING", True),
            "sentry_dsn": self.get_config("MONITORING_SENTRY_DSN", "")
        }
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Obtém configurações de notificações"""
        return {
            "enabled": self.get_config("NOTIFICATIONS_ENABLED", True),
            "email_enabled": self.get_config("NOTIFICATIONS_EMAIL_ENABLED", False),
            "webhook_enabled": self.get_config("NOTIFICATIONS_WEBHOOK_ENABLED", False),
            "slack_enabled": self.get_config("NOTIFICATIONS_SLACK_ENABLED", False),
            
            # Email settings
            "smtp_server": self.get_config("NOTIFICATIONS_SMTP_SERVER", ""),
            "smtp_port": self.get_config("NOTIFICATIONS_SMTP_PORT", 587),
            "smtp_username": self.get_config("NOTIFICATIONS_SMTP_USERNAME", ""),
            "smtp_password": self.get_config("NOTIFICATIONS_SMTP_PASSWORD", ""),
            "email_from": self.get_config("NOTIFICATIONS_EMAIL_FROM", ""),
            "email_to": self._parse_list(self.get_config("NOTIFICATIONS_EMAIL_TO", "")),
            
            # Webhook settings
            "webhook_url": self.get_config("NOTIFICATIONS_WEBHOOK_URL", ""),
            "webhook_secret": self.get_config("NOTIFICATIONS_WEBHOOK_SECRET", ""),
            
            # Slack settings
            "slack_webhook": self.get_config("NOTIFICATIONS_SLACK_WEBHOOK", ""),
            "slack_channel": self.get_config("NOTIFICATIONS_SLACK_CHANNEL", "#decksmith"),
            
            # Notification levels
            "notify_on_success": self.get_config("NOTIFICATIONS_ON_SUCCESS", True),
            "notify_on_error": self.get_config("NOTIFICATIONS_ON_ERROR", True),
            "notify_on_warning": self.get_config("NOTIFICATIONS_ON_WARNING", False),
            "notify_on_completion": self.get_config("NOTIFICATIONS_ON_COMPLETION", True)
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Obtém configurações de segurança"""
        return {
            "api_key": self.get_config("DECKSMITH_API_KEY", ""),
            "secret_key": self.get_config("DECKSMITH_SECRET_KEY", ""),
            "jwt_secret": self.get_config("DECKSMITH_JWT_SECRET", ""),
            "encryption_key": self.get_config("DECKSMITH_ENCRYPTION_KEY", ""),
            "rate_limit_enabled": self.get_config("SECURITY_RATE_LIMIT_ENABLED", True),
            "rate_limit_requests": self.get_config("SECURITY_RATE_LIMIT_REQUESTS", 100),
            "rate_limit_window": self.get_config("SECURITY_RATE_LIMIT_WINDOW", 3600),
            "ip_whitelist": self._parse_list(self.get_config("SECURITY_IP_WHITELIST", "")),
            "user_agent_verification": self.get_config("SECURITY_USER_AGENT_VERIFICATION", False)
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
        return self.get_config("ENVIRONMENT", "development")
    
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
        
        for key, value in self._config_cache.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_config[key] = "***HIDDEN***"
            else:
                safe_config[key] = value
        
        return safe_config