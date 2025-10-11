"""
DeckSmith Batch Processing - Main Entry Point
============================================

Sistema de processamento em lote para MTG card data analytics.
Implementa Clean Architecture com SOLID principles.
Versão com configuração por ambiente e Deep Learning integrado.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncpg

from src.domain.entities import Card, Deck, ScrapingSession
from src.domain.repositories import ICardRepository, IDeckRepository, IScrapingSessionRepository
from src.infrastructure.database.postgresql_card_repository import PostgreSQLCardRepository
from src.infrastructure.database.postgresql_deck_repository import PostgreSQLDeckRepository
from src.infrastructure.scraping.archidekt_scraping_service import ArchidektScrapingService
from src.application.use_cases.archidekt_scraping_use_case import ArchidektScrapingUseCase
from src.infrastructure.config.environment_config import EnvironmentAwareConfigManager
# from src.infrastructure.ml.deep_learning_engine import TensorFlowDeepLearningEngine  # Temporariamente desabilitado


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class PostgreSQLScrapingSessionRepository(IScrapingSessionRepository):
    """Implementação simples do repositório de sessões"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
    
    async def save(self, session: ScrapingSession) -> None:
        """Salva sessão no banco"""
        query = """
            INSERT INTO scraping_sessions (
                id, source, start_time, end_time, status, pages_scraped,
                decks_found, decks_saved, cards_found, cards_saved, errors, configuration
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO UPDATE SET
                end_time = EXCLUDED.end_time,
                status = EXCLUDED.status,
                pages_scraped = EXCLUDED.pages_scraped,
                decks_found = EXCLUDED.decks_found,
                decks_saved = EXCLUDED.decks_saved,
                cards_found = EXCLUDED.cards_found,
                cards_saved = EXCLUDED.cards_saved,
                errors = EXCLUDED.errors
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                str(session.id), session.source, session.start_time, session.end_time,
                session.status.value, session.pages_scraped, session.decks_found,
                session.decks_saved, session.cards_found, session.cards_saved,
                session.errors, session.configuration
            )
    
    async def find_by_id(self, session_id) -> Optional[ScrapingSession]:
        """Busca sessão por ID (implementação básica)"""
        # Implementação simplificada
        return None
    
    async def find_recent_sessions(self, limit: int = 10) -> List[ScrapingSession]:
        """Busca sessões recentes (implementação básica)"""
        return []
    
    # Implementações básicas para outros métodos da interface
    async def find_active_sessions(self) -> List[ScrapingSession]:
        return []
    
    async def find_completed_sessions(self, limit: int = 50) -> List[ScrapingSession]:
        return []
    
    async def find_failed_sessions(self, limit: int = 50) -> List[ScrapingSession]:
        return []
    
    async def find_by_source(self, source: str) -> List[ScrapingSession]:
        return []
    
    async def find_by_date_range(self, start_date, end_date) -> List[ScrapingSession]:
        return []
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        return {}
    
    async def count_total(self) -> int:
        return 0
    
    async def delete_old_sessions(self, days_old: int = 30) -> int:
        return 0


class DeckSmithBatchProcessor:
    """
    Processador principal do sistema DeckSmith.
    Coordena todas as operações de batch processing com configuração por ambiente.
    """
    
    def __init__(self):
        # Inicializar configuração baseada no ambiente
        self.config = EnvironmentAwareConfigManager()
        
        # Configurar logging baseado no ambiente
        log_level = getattr(logging, self.config.get_monitoring_config_typed().log_level)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Log informações do ambiente
        env_info = self.config.get_environment_info()
        self.logger.info(f"🌍 Environment: {env_info['environment']}")
        self.logger.info(f"🔧 Git Branch: {env_info.get('git_branch', 'unknown')}")
        self.logger.info(f"☁️ Heroku App: {env_info.get('heroku_app', 'local')}")
        
        # Componentes do sistema
        self.db_pool: Optional[asyncpg.Pool] = None
        self.card_repository: Optional[ICardRepository] = None
        self.deck_repository: Optional[IDeckRepository] = None
        self.session_repository: Optional[IScrapingSessionRepository] = None
        self.scraping_service: Optional[ArchidektScrapingService] = None
        self.scraping_use_case: Optional[ArchidektScrapingUseCase] = None
        self.ml_engine: Optional[Any] = None  # TensorFlowDeepLearningEngine temporariamente desabilitado
    
    async def initialize(self):
        """Inicializa todos os componentes do sistema baseado no ambiente"""
        self.logger.info("🚀 Initializing DeckSmith Batch Processor...")
        
        # Mostrar configurações por ambiente
        self._log_environment_config()
        
        # Configurar banco de dados
        await self._setup_database()
        
        # Configurar repositórios
        self._setup_repositories()
        
        # Configurar serviços
        self._setup_services()
        
        # Configurar use cases
        self._setup_use_cases()
        
        # Configurar ML Engine (se habilitado)
        await self._setup_ml_engine()
        
        self.logger.info("✅ System initialized successfully")
    
    def _log_environment_config(self):
        """Log das configurações por ambiente"""
        self.logger.info("📋 Environment Configuration:")
        
        # Database config
        db_config = self.config.get_database_config_typed()
        self.logger.info(f"  🗄️ Database: {db_config.database} @ {db_config.host}:{db_config.port}")
        self.logger.info(f"  🔒 SSL Mode: {db_config.ssl_mode}")
        self.logger.info(f"  🏊 Pool: {db_config.pool_min_size}-{db_config.pool_max_size}")
        
        # ML config
        ml_config = self.config.get_ml_config_typed()
        self.logger.info(f"  🤖 Deep Learning: {'✅' if ml_config.enable_deep_learning else '❌'}")
        self.logger.info(f"  🚀 GPU Support: {'✅' if ml_config.use_gpu else '❌'}")
        self.logger.info(f"  📊 Batch Size: {ml_config.batch_size}, Epochs: {ml_config.epochs}")
        
        # Monitoring config
        monitoring_config = self.config.get_monitoring_config_typed()
        self.logger.info(f"  📈 Monitoring: {'✅' if monitoring_config.enabled else '❌'}")
        self.logger.info(f"  📋 Log Level: {monitoring_config.log_level}")
        
        # API config
        api_config = self.config.get_api_config()
        self.logger.info(f"  🌐 API Base: {api_config.base_url}")
        self.logger.info(f"  ⏱️ Timeout: {api_config.timeout}s, Retries: {api_config.max_retries}")
    
    async def _setup_ml_engine(self):
        """Configura ML Engine baseado no ambiente"""
        ml_config = self.config.get_ml_config()
        
        if not ml_config.get("enable_deep_learning", False):
            self.logger.info("🤖 Deep Learning disabled in this environment")
            return
        
        try:
            # Por enquanto, vamos usar uma versão mock em caso de problemas com TensorFlow
            self.logger.info("🤖 ML Engine setup deferred (TensorFlow configuration issues)")
            self.ml_engine = None
                
        except Exception as e:
            self.logger.error(f"🤖 Error initializing ML engine: {e}")
            self.ml_engine = None
    
    async def _setup_database(self):
        """Configura conexão com banco baseada no ambiente"""
        db_config = self.config.get_database_config_typed()
        
        # Modo de teste - sem banco de dados
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            self.logger.info("Running in TEST MODE - skipping database connection")
            return
        
        # Usar DATABASE_URL do Heroku se disponível, senão construir URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            database_url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
            if self.config.is_development():
                self.logger.warning("Using constructed database URL for development")
        
        try:
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=db_config.pool_min_size,
                max_size=db_config.pool_max_size,
                command_timeout=db_config.command_timeout,
                ssl=db_config.ssl_mode if db_config.ssl_mode != 'disable' else None
            )
            self.logger.info(f"Database connection pool created (size: {db_config.pool_min_size}-{db_config.pool_max_size})")
            
            # Testar conexão
            async with self.db_pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                self.logger.info(f"Connected to PostgreSQL: {version[:50]}...")
                
                # Verificar se as tabelas existem (apenas log, não criação)
                tables_query = """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name IN ('cards', 'decks', 'ml_models')
                """
                existing_tables = await conn.fetch(tables_query)
                table_names = [row['table_name'] for row in existing_tables]
                self.logger.info(f"Found tables: {', '.join(table_names) if table_names else 'none'}")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            if not test_mode:
                raise
    
    def _setup_repositories(self):
        """Configura repositórios"""
        assert self.db_pool is not None, "Database pool must be initialized"
        self.card_repository = PostgreSQLCardRepository(self.db_pool)
        self.deck_repository = PostgreSQLDeckRepository(self.db_pool)
        self.session_repository = PostgreSQLScrapingSessionRepository(self.db_pool)
        self.logger.info("Repositories configured")
    
    def _setup_services(self):
        """Configura serviços baseados no ambiente"""
        scraping_config = self.config.get_scraping_config()
        
        self.scraping_service = ArchidektScrapingService(
            delay_between_requests=scraping_config["default_delay"],
            max_retries=scraping_config["max_retries"],
            timeout=scraping_config["timeout"]
        )
        
        self.logger.info(f"Scraping service configured (delay: {scraping_config['default_delay']}s, workers: {scraping_config['concurrent_workers']})")
    
    def _setup_use_cases(self):
        """Configura use cases de aplicação"""
        assert self.card_repository is not None
        assert self.deck_repository is not None
        assert self.session_repository is not None
        assert self.scraping_service is not None
        
        self.scraping_use_case = ArchidektScrapingUseCase(
            card_repository=self.card_repository,
            deck_repository=self.deck_repository,
            session_repository=self.session_repository,
            scraping_service=self.scraping_service
        )
        self.logger.info("Use cases configured")
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Executa verificação de saúde do sistema"""
        self.logger.info("🔍 Running health check...")
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": self.config.get_environment(),
            "version": os.getenv("DECKSMITH_VERSION", "unknown"),
            "components": {}
        }
        
        # Verificar configuração
        try:
            env_info = self.config.get_environment_info()
            health_status["components"]["configuration"] = {
                "status": "healthy",
                "message": f"Environment: {env_info['environment']}",
                "details": env_info
            }
        except Exception as e:
            health_status["components"]["configuration"] = {
                "status": "unhealthy",
                "message": f"Configuration error: {e}"
            }
            health_status["status"] = "unhealthy"
        
        # Verificar banco de dados
        try:
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                    
                    # Verificar tabelas importantes
                    tables_query = """
                        SELECT COUNT(*) as table_count FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name IN ('cards', 'decks', 'ml_models')
                    """
                    table_count = await conn.fetchval(tables_query)
                    
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "message": f"Database connection successful, {table_count}/3 core tables found",
                    "pool_size": f"{self.db_pool.get_size()}/{self.db_pool.get_max_size()}"
                }
            else:
                health_status["components"]["database"] = {
                    "status": "warning",
                    "message": "Database pool not initialized (test mode?)"
                }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {e}"
            }
            health_status["status"] = "unhealthy"
        
        # Verificar repositórios
        try:
            if self.card_repository and self.deck_repository:
                card_count = await self.card_repository.count_total()
                deck_count = await self.deck_repository.count_total()
                health_status["components"]["repositories"] = {
                    "status": "healthy",
                    "message": f"Cards: {card_count}, Decks: {deck_count}"
                }
            else:
                health_status["components"]["repositories"] = {
                    "status": "warning",
                    "message": "Repositories not initialized"
                }
        except Exception as e:
            health_status["components"]["repositories"] = {
                "status": "unhealthy",
                "message": f"Repository error: {e}"
            }
            health_status["status"] = "unhealthy"
        
        # Verificar ML Engine
        try:
            if self.ml_engine:
                models = await self.ml_engine.get_model_list()
                architectures = self.ml_engine.get_available_architectures()
                health_status["components"]["ml_engine"] = {
                    "status": "healthy",
                    "message": f"ML Engine active, {len(models)} models, {len(architectures)} architectures",
                    "details": {
                        "models_count": len(models),
                        "architectures": architectures
                    }
                }
            else:
                ml_config = self.config.get_ml_config_typed()
                if ml_config.enable_deep_learning:
                    health_status["components"]["ml_engine"] = {
                        "status": "warning",
                        "message": "ML Engine enabled but not initialized"
                    }
                else:
                    health_status["components"]["ml_engine"] = {
                        "status": "disabled",
                        "message": "ML Engine disabled in this environment"
                    }
        except Exception as e:
            health_status["components"]["ml_engine"] = {
                "status": "unhealthy",
                "message": f"ML Engine error: {e}"
            }
        
        # Verificar variáveis de ambiente críticas
        try:
            required_vars = []
            missing_vars = []
            
            # Variáveis obrigatórias por ambiente
            if not self.config.is_development():
                required_vars.extend(["DATABASE_URL"])
            
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                health_status["components"]["environment"] = {
                    "status": "warning",
                    "message": f"Missing env vars: {', '.join(missing_vars)}"
                }
            else:
                health_status["components"]["environment"] = {
                    "status": "healthy",
                    "message": "All required environment variables present"
                }
        except Exception as e:
            health_status["components"]["environment"] = {
                "status": "unhealthy",
                "message": f"Environment check error: {e}"
            }
        
        return health_status
    
    async def run_archidekt_scraping(self, max_pages: int = 100) -> Dict[str, Any]:
        """
        Executa scraping completo do Archidekt.
        
        Args:
            max_pages: Número máximo de páginas para processar
            
        Returns:
            Relatório da execução
        """
        start_time = datetime.now()
        self.logger.info(f"🕷️ Starting Archidekt scraping with max_pages={max_pages}")
        
        try:
            # Verificar configuração de scraping
            api_config = self.config.get_api_config()
            
            # Configurações de scraping baseadas no ambiente
            enable_scraping = True  # Por padrão habilitado
            max_requests_per_hour = 1000 if self.config.is_production() else 500
            batch_size = 50 if self.config.is_production() else 20
            
            if not enable_scraping:
                self.logger.warning("Scraping is disabled in this environment")
                return {
                    "operation": "archidekt_scraping",
                    "status": "skipped",
                    "message": "Scraping disabled for this environment",
                    "environment": self.config.get_environment(),
                    "timestamp": start_time.isoformat()
                }
            
            # Ajustar max_pages baseado no ambiente
            env_max_pages = min(max_pages, max_requests_per_hour // 10)  # Conservador
            if env_max_pages != max_pages:
                self.logger.info(f"Adjusted max_pages from {max_pages} to {env_max_pages} for environment {self.config.get_environment()}")
                max_pages = env_max_pages
            
            # Executar scraping
            assert self.scraping_use_case is not None, "Scraping use case not initialized"
            session_id = await self.scraping_use_case.execute_scraping_session(
                max_pages=max_pages,
                format_filter=None,  # Todos os formatos
                featured_only=False,
                update_existing=False
            )
            
            # Obter status da sessão
            session_status = await self.scraping_use_case.get_session_status(session_id)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            report = {
                "operation": "archidekt_scraping",
                "environment": self.config.get_environment(),
                "session_id": str(session_id),
                "status": session_status.get("status", "unknown") if session_status else "unknown",
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "max_pages_requested": max_pages,
                "results": session_status.get("stats", {}) if session_status else {},
                "config_used": {
                    "rate_limit": api_config.rate_limit,
                    "batch_size": batch_size,
                    "max_requests_per_hour": max_requests_per_hour
                }
            }
            
            self.logger.info(f"✅ Scraping completed successfully in {duration:.2f}s")
            if session_status:
                self.logger.info(f"📊 Results: {session_status.get('decks_saved', 0)} decks, {session_status.get('cards_saved', 0)} cards")
            
            return report
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_report = {
                "operation": "archidekt_scraping",
                "status": "error",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e)
            }
            
            self.logger.error(f"❌ Scraping failed after {duration:.2f}s: {e}")
            return error_report
    
    async def run_ml_analysis(self, model_name: str = "default", operation: str = "train") -> Dict[str, Any]:
        """
        Executa análise de Machine Learning.
        
        Args:
            model_name: Nome do modelo para usar/treinar
            operation: Operação a executar ('train', 'predict', 'evaluate')
            
        Returns:
            Relatório da execução
        """
        start_time = datetime.now()
        self.logger.info(f"🤖 Starting ML analysis: {operation} on model '{model_name}'")
        
        try:
            # Verificar configuração de ML
            ml_config = self.config.get_ml_config()
            if not ml_config.get("enable_deep_learning", False):
                self.logger.warning("Deep Learning is disabled in this environment")
                return {
                    "operation": f"ml_{operation}",
                    "status": "skipped",
                    "message": "Deep Learning disabled for this environment",
                    "environment": self.config.get_environment(),
                    "timestamp": start_time.isoformat()
                }
            
            # Verificar se ML engine está disponível
            if not self.ml_engine:
                self.logger.error("ML Engine not initialized")
                return {
                    "operation": f"ml_{operation}",
                    "status": "error",
                    "message": "ML Engine not available",
                    "environment": self.config.get_environment(),
                    "timestamp": start_time.isoformat()
                }
            
            # Executar operação baseada no tipo
            result = {}
            if operation == "train":
                # Simular treinamento (implementação real dependeria dos dados disponíveis)
                result = await self._simulate_training(model_name)
            elif operation == "predict":
                result = await self._simulate_prediction(model_name)
            elif operation == "evaluate":
                result = await self._simulate_evaluation(model_name)
            else:
                raise ValueError(f"Unknown ML operation: {operation}")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            report = {
                "operation": f"ml_{operation}",
                "environment": self.config.get_environment(),
                "model_name": model_name,
                "status": "success",
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "results": result,
                "ml_config": {
                    "enable_deep_learning": ml_config.get("enable_deep_learning", False),
                    "model_architecture": ml_config.get("model_architecture", "neural_network"),
                    "batch_size": ml_config.get("batch_size", 32)
                }
            }
            
            self.logger.info(f"✅ ML analysis completed successfully in {duration:.2f}s")
            return report
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_report = {
                "operation": f"ml_{operation}",
                "environment": self.config.get_environment(),
                "model_name": model_name,
                "status": "error",
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "error": str(e)
            }
            
            self.logger.error(f"❌ ML analysis failed after {duration:.2f}s: {e}")
            return error_report
    
    async def _simulate_training(self, model_name: str) -> Dict[str, Any]:
        """Simula treinamento de modelo"""
        if self.ml_engine:
            architectures = self.ml_engine.get_available_architectures()
            selected_arch = architectures[0] if architectures else "neural_network"
        else:
            selected_arch = "neural_network"
        
        return {
            "model_saved": True,
            "architecture": selected_arch,
            "training_samples": 1000,
            "validation_accuracy": 0.85,
            "epochs": 10
        }
    
    async def _simulate_prediction(self, model_name: str) -> Dict[str, Any]:
        """Simula predição de modelo"""
        return {
            "predictions_made": 100,
            "confidence_avg": 0.75,
            "processing_time_ms": 150
        }
    
    async def _simulate_evaluation(self, model_name: str) -> Dict[str, Any]:
        """Simula avaliação de modelo"""
        return {
            "test_accuracy": 0.82,
            "precision": 0.78,
            "recall": 0.81,
            "f1_score": 0.79,
            "test_samples": 500
        }
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema"""
        try:
            assert self.card_repository is not None
            assert self.deck_repository is not None
            
            card_count = await self.card_repository.count_total()
            deck_count = await self.deck_repository.count_total()
            deck_stats = await self.deck_repository.get_deck_statistics()
            
            return {
                "total_cards": card_count,
                "total_decks": deck_count,
                "deck_statistics": deck_stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Limpa recursos do sistema"""
        self.logger.info("🧹 Starting system cleanup...")
        
        # Cleanup ML Engine
        if self.ml_engine:
            try:
                await self.ml_engine.cleanup()
                self.logger.info("🤖 ML Engine cleaned up")
            except Exception as e:
                self.logger.warning(f"🤖 Error cleaning up ML Engine: {e}")
        
        # Cleanup Scraping Service
        if self.scraping_service and self.scraping_service.session:
            try:
                await self.scraping_service.close()
                self.logger.info("🕷️ Scraping service closed")
            except Exception as e:
                self.logger.warning(f"🕷️ Error closing scraping service: {e}")
        
        # Cleanup Database Pool
        if self.db_pool:
            try:
                await self.db_pool.close()
                self.logger.info("🗄️ Database pool closed")
            except Exception as e:
                self.logger.warning(f"🗄️ Error closing database pool: {e}")
        
        self.logger.info("✅ System cleanup completed")


async def main():
    """Função principal do sistema"""
    logger.info("🚀 Starting DeckSmith Batch Processing System")
    
    processor = DeckSmithBatchProcessor()
    
    try:
        # Inicializar sistema
        await processor.initialize()
        
        # Health check
        health_result = await processor.run_health_check()
        logger.info("Health Check Results:")
        for component, status in health_result["components"].items():
            status_icon = "✅" if status["status"] == "healthy" else "⚠️" if status["status"] == "warning" else "❌"
            logger.info(f"  {status_icon} {component}: {status['message']}")
        
        if health_result["status"] != "healthy":
            logger.warning("System health check failed, continuing anyway...")
        
        # Determinar operação baseada em variáveis de ambiente
        operation = os.getenv("BATCH_OPERATION", "scraping")
        max_pages = int(os.getenv("MAX_PAGES", "100"))
        ml_model = os.getenv("ML_MODEL", "default")
        ml_operation = os.getenv("ML_OPERATION", "train")
        
        if operation == "scraping":
            # Executar scraping do Archidekt
            result = await processor.run_archidekt_scraping(max_pages=max_pages)
            
            # Mostrar estatísticas finais
            stats = await processor.get_system_statistics()
            logger.info(f"📈 Final Statistics: {stats.get('total_cards', 0)} cards, {stats.get('total_decks', 0)} decks")
            
        elif operation == "ml":
            # Executar análise de ML
            result = await processor.run_ml_analysis(model_name=ml_model, operation=ml_operation)
            
            # Mostrar estatísticas do sistema
            stats = await processor.get_system_statistics()
            logger.info(f"📈 System Statistics: {stats.get('total_cards', 0)} cards, {stats.get('total_decks', 0)} decks")
            
        elif operation == "stats":
            # Apenas mostrar estatísticas
            stats = await processor.get_system_statistics()
            logger.info(f"📊 System Statistics: {stats}")
            result = {"operation": "stats", "status": "success", "data": stats}
            
        else:
            logger.warning(f"Unknown operation '{operation}', defaulting to health check")
            result = {"operation": "health_check", "status": "success", "data": health_result}
        
        # Log resultado final
        logger.info("Final Result:")
        logger.info(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            logger.info("✅ Batch processing completed successfully")
            return 0
        else:
            logger.error(f"❌ Batch processing failed: {result.get('error', 'Unknown error')}")
            return 1
        
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        return 1
    
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)