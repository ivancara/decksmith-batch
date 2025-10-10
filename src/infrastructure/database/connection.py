"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Database Connection
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection

from ...application.interfaces import IConfigManager


class DatabaseConnection:
    """Gerenciador de conexão com PostgreSQL"""
    
    def __init__(self, config_manager: IConfigManager):
        self.config_manager = config_manager
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Inicializa pool de conexões"""
        if self.pool:
            return
        
        db_config = self.config_manager.get_database_config()
        
        try:
            self.pool = await asyncpg.create_pool(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 5432),
                user=db_config.get("user", "postgres"),
                password=db_config.get("password", ""),
                database=db_config.get("database", "decksmith"),
                min_size=db_config.get("pool_min_size", 5),
                max_size=db_config.get("pool_max_size", 20),
                command_timeout=60,
                server_settings={
                    'application_name': 'decksmith_batch'
                }
            )
            
            self.logger.info("Database pool initialized", 
                           extra={"host": db_config.get("host"), "database": db_config.get("database")})
            
        except Exception as e:
            self.logger.error("Failed to initialize database pool", extra={"error": str(e)})
            raise
    
    async def close(self) -> None:
        """Fecha pool de conexões"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager para obter conexão do pool"""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    @asynccontextmanager
    async def get_transaction(self):
        """Context manager para transação"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Executa query e retorna resultados"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Executa comando e retorna status"""
        async with self.get_connection() as conn:
            return await conn.execute(command, *args)
    
    async def health_check(self) -> bool:
        """Verifica se conexão está saudável"""
        try:
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            self.logger.error("Database health check failed", extra={"error": str(e)})
            return False