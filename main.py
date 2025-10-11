"""
DeckSmith Batch Processing - Main Entry Point
============================================

Sistema de processamento em lote para MTG card data analytics.
Implementa Clean Architecture com SOLID principles.
Versão com integração completa do Archidekt scraping.
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
    Coordena todas as operações de batch processing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.card_repository: Optional[ICardRepository] = None
        self.deck_repository: Optional[IDeckRepository] = None
        self.session_repository: Optional[IScrapingSessionRepository] = None
        self.scraping_service: Optional[ArchidektScrapingService] = None
        self.scraping_use_case: Optional[ArchidektScrapingUseCase] = None
    
    async def initialize(self):
        """Inicializa todos os componentes do sistema"""
        self.logger.info("🚀 Initializing DeckSmith Batch Processor...")
        
        # Configurar banco de dados
        await self._setup_database()
        
        # Configurar repositórios
        self._setup_repositories()
        
        # Configurar serviços
        self._setup_services()
        
        # Configurar use cases
        self._setup_use_cases()
        
        self.logger.info("✅ System initialized successfully")
    
    async def _setup_database(self):
        """Configura conexão com banco de dados"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # URL padrão para desenvolvimento
            database_url = "postgresql://postgres:postgres@localhost:5432/decksmith"
            self.logger.warning("Using default database URL for development")
        
        # Modo de teste - sem banco de dados
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            self.logger.info("Running in TEST MODE - skipping database connection")
            return
        
        try:
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            self.logger.info("Database connection pool created")
            
            # Testar conexão
            async with self.db_pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                self.logger.info(f"Connected to PostgreSQL: {version[:50]}...")
                
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
        """Configura serviços de infraestrutura"""
        delay = float(os.getenv('SCRAPING_DELAY', '1.0'))
        self.scraping_service = ArchidektScrapingService(
            delay_between_requests=delay,
            max_retries=3,
            timeout=30
        )
        self.logger.info("Services configured")
    
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
            "components": {}
        }
        
        # Verificar banco de dados
        try:
            assert self.db_pool is not None, "Database pool not initialized"
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database error: {e}"
            }
            health_status["status"] = "unhealthy"
        
        # Verificar repositórios
        try:
            assert self.card_repository is not None
            assert self.deck_repository is not None
            card_count = await self.card_repository.count_total()
            deck_count = await self.deck_repository.count_total()
            health_status["components"]["repositories"] = {
                "status": "healthy",
                "message": f"Cards: {card_count}, Decks: {deck_count}"
            }
        except Exception as e:
            health_status["components"]["repositories"] = {
                "status": "unhealthy",
                "message": f"Repository error: {e}"
            }
            health_status["status"] = "unhealthy"
        
        # Verificar variáveis de ambiente
        required_vars = ["DATABASE_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
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
                "status": "success",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "session_id": str(session_id),
                "results": session_status
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
        if self.scraping_service and self.scraping_service.session:
            await self.scraping_service.close()
        
        if self.db_pool:
            await self.db_pool.close()
        
        self.logger.info("System cleanup completed")


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
        
        if operation == "scraping":
            # Executar scraping do Archidekt
            result = await processor.run_archidekt_scraping(max_pages=max_pages)
            
            # Mostrar estatísticas finais
            stats = await processor.get_system_statistics()
            logger.info(f"📈 Final Statistics: {stats.get('total_cards', 0)} cards, {stats.get('total_decks', 0)} decks")
            
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