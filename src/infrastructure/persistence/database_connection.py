"""
Infrastructure Layer - Conexão com Banco de Dados
Implementação real com AsyncPG para PostgreSQL
"""

import asyncpg
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime
import json

from ...domain.interfaces import IConfigurationManager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Gerenciador de conexão e pool PostgreSQL com AsyncPG"""
    
    def __init__(self, config_manager: IConfigurationManager):
        self._config_manager = config_manager
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_config: Optional[Dict[str, Any]] = None
    
    async def initialize(self) -> bool:
        """Inicializa pool de conexões"""
        try:
            # Obter configurações do banco
            db_config = self._config_manager.get_database_config()
            
            # Construir DSN
            dsn = self._build_dsn(db_config)
            
            # Configurações do pool
            self._connection_config = {
                'dsn': dsn,
                'min_size': db_config.get('pool_min_size', 5),
                'max_size': db_config.get('pool_max_size', 20),
                'command_timeout': db_config.get('command_timeout', 60),
                'server_settings': {
                    'application_name': db_config.get('application_name', 'decksmith_batch'),
                    'timezone': 'UTC'
                }
            }
            
            # Criar pool
            self._pool = await asyncpg.create_pool(**self._connection_config)
            
            # Testar conexão
            async with self._pool.acquire() as conn:
                result = await conn.fetchval('SELECT version()')
                logger.info(f"Conectado ao PostgreSQL: {result}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar conexão com banco: {e}")
            return False
    
    def _build_dsn(self, config: Dict[str, Any]) -> str:
        """Constrói DSN de conexão"""
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        user = config.get('user', 'postgres')
        password = config.get('password', '')
        database = config.get('database', 'decksmith')
        ssl_mode = config.get('ssl_mode', 'prefer')
        
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"
        return dsn
    
    @asynccontextmanager
    async def acquire(self):
        """Context manager para adquirir conexão"""
        if not self._pool:
            raise RuntimeError("Pool de conexões não inicializado")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args) -> str:
        """Executa query sem retorno"""
        async with self.acquire() as conn:
            result = await conn.execute(query, *args)
            logger.debug(f"Query executada: {query[:100]}... | Resultado: {result}")
            return result
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Executa query com retorno múltiplo"""
        async with self.acquire() as conn:
            result = await conn.fetch(query, *args)
            logger.debug(f"Query executada: {query[:100]}... | Registros: {len(result)}")
            return result
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Executa query com retorno único"""
        async with self.acquire() as conn:
            result = await conn.fetchrow(query, *args)
            logger.debug(f"Query executada: {query[:100]}... | Resultado: {'Encontrado' if result else 'Não encontrado'}")
            return result
    
    async def fetchval(self, query: str, *args) -> Any:
        """Executa query retornando valor único"""
        async with self.acquire() as conn:
            result = await conn.fetchval(query, *args)
            logger.debug(f"Query executada: {query[:100]}... | Valor: {result}")
            return result
    
    async def transaction(self):
        """Retorna context manager para transação"""
        if not self._pool:
            raise RuntimeError("Pool de conexões não inicializado")
        
        return self._pool.acquire()
    
    async def close(self):
        """Fecha pool de conexões"""
        if self._pool:
            await self._pool.close()
            logger.info("Pool de conexões fechado")
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self._pool is not None and not self._pool._closed
    
    async def health_check(self) -> bool:
        """Verifica saúde da conexão"""
        try:
            if not self.is_connected():
                return False
            
            result = await self.fetchval('SELECT 1')
            return result == 1
        except Exception as e:
            logger.error(f"Health check falhou: {e}")
            return False


class PostgreSQLRepository:
    """Base repository com operações PostgreSQL comuns"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self._db = db_connection
    
    async def insert(self, table: str, data: Dict[str, Any], returning: str = "id") -> Any:
        """Insere registro e retorna campo especificado"""
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)}) 
            VALUES ({', '.join(placeholders)}) 
            RETURNING {returning}
        """
        
        result = await self._db.fetchval(query, *values)
        return result
    
    async def update(self, table: str, data: Dict[str, Any], where_clause: str, *where_args) -> str:
        """Atualiza registros"""
        set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(data.keys())]
        values = list(data.values())
        
        # Ajustar índices dos parâmetros WHERE
        where_clause_adjusted = where_clause
        for i, arg in enumerate(where_args):
            placeholder = f"${len(values) + i + 1}"
            where_clause_adjusted = where_clause_adjusted.replace(f"${i+1}", placeholder)
        
        query = f"""
            UPDATE {table} 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE {where_clause_adjusted}
        """
        
        all_values = values + list(where_args)
        result = await self._db.execute(query, *all_values)
        return result
    
    async def delete(self, table: str, where_clause: str, *where_args) -> str:
        """Deleta registros"""
        query = f"DELETE FROM {table} WHERE {where_clause}"
        result = await self._db.execute(query, *where_args)
        return result
    
    async def select(self, table: str, columns: str = "*", where_clause: Optional[str] = None, 
                    order_by: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[asyncpg.Record]:
        """Seleciona registros com filtros opcionais"""
        query = f"SELECT {columns} FROM {table}"
        
        args = []
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        if offset:
            query += f" OFFSET {offset}"
        
        return await self._db.fetch(query, *args)
    
    async def count(self, table: str, where_clause: Optional[str] = None, *where_args) -> int:
        """Conta registros"""
        query = f"SELECT COUNT(*) FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
            result = await self._db.fetchval(query, *where_args)
        else:
            result = await self._db.fetchval(query)
        
        return result or 0
    
    def record_to_dict(self, record: Optional[asyncpg.Record]) -> Optional[Dict[str, Any]]:
        """Converte Record para dict"""
        if not record:
            return None
        
        result = {}
        for key, value in record.items():
            # Converter tipos especiais para serialização
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                result[key] = value  # JSONB já vem deserializado
            else:
                result[key] = value
        
        return result
    
    def records_to_dict_list(self, records: List[asyncpg.Record]) -> List[Dict[str, Any]]:
        """Converte lista de Records para lista de dicts"""
        result = []
        for record in records:
            dict_record = self.record_to_dict(record)
            if dict_record is not None:
                result.append(dict_record)
        return result