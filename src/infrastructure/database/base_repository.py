"""
DeckSmith Batch Processing System
Infrastructure Layer - Base Repository Implementation
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from dataclasses import asdict

from .connection import DatabaseConnection


class BaseRepository:
    """Classe base para repositories PostgreSQL"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _entity_to_dict(self, entity) -> Dict[str, Any]:
        """Converte entidade para dicionário, removendo campos complexos"""
        if hasattr(entity, '__dataclass_fields__'):
            data = asdict(entity)
        else:
            data = entity.__dict__.copy()
        
        # Converter UUID para string
        for key, value in data.items():
            if hasattr(value, 'hex'):  # UUID
                data[key] = str(value)
            elif isinstance(value, list) and value and hasattr(value[0], 'hex'):
                data[key] = [str(v) for v in value]
        
        return data
    
    def _build_insert_query(self, table: str, data: Dict[str, Any]) -> tuple[str, list]:
        """Constrói query INSERT"""
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        return query, values
    
    def _build_update_query(self, table: str, data: Dict[str, Any], where_field: str) -> tuple[str, list]:
        """Constrói query UPDATE"""
        # Remover campo de WHERE dos dados
        update_data = {k: v for k, v in data.items() if k != where_field}
        where_value = data[where_field]
        
        set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(update_data.keys())]
        values = list(update_data.values()) + [where_value]
        
        query = f"""
            UPDATE {table}
            SET {', '.join(set_clauses)}
            WHERE {where_field} = ${len(values)}
            RETURNING *
        """
        
        return query, values
    
    async def _exists(self, table: str, field: str, value: Any) -> bool:
        """Verifica se registro existe"""
        query = f"SELECT 1 FROM {table} WHERE {field} = $1 LIMIT 1"
        async with self.db.get_connection() as conn:
            result = await conn.fetchval(query, value)
            return result is not None
    
    async def _insert_or_update(self, table: str, data: Dict[str, Any], id_field: str = "id"):
        """Insert ou update baseado na existência do ID"""
        id_value = data.get(id_field)
        
        if id_value and await self._exists(table, id_field, id_value):
            # UPDATE
            query, values = self._build_update_query(table, data, id_field)
        else:
            # INSERT
            query, values = self._build_insert_query(table, data)
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def _batch_insert(self, table: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Inserção em lote"""
        if not records:
            return []
        
        # Usar o primeiro registro para determinar colunas
        columns = list(records[0].keys())
        
        # Preparar dados para COPY
        async with self.db.get_transaction() as conn:
            # Criar tabela temporária
            temp_table = f"temp_{table}_{asyncio.get_event_loop().time():.0f}"
            
            # Obter schema da tabela original
            schema_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """
            
            schema_rows = await conn.fetch(schema_query)
            
            # Criar tabela temporária com mesmo schema
            create_temp = f"CREATE TEMP TABLE {temp_table} (LIKE {table} INCLUDING ALL)"
            await conn.execute(create_temp)
            
            # COPY dados para tabela temporária
            copy_stmt = f"COPY {temp_table} ({', '.join(columns)}) FROM STDIN WITH CSV"
            
            # Preparar dados CSV
            import io
            import csv
            
            csv_data = io.StringIO()
            writer = csv.DictWriter(csv_data, fieldnames=columns)
            writer.writerows(records)
            csv_data.seek(0)
            
            await conn.copy_from_table(temp_table, source=csv_data, columns=columns, format='csv')
            
            # INSERT dados da temp para tabela principal
            insert_query = f"""
                INSERT INTO {table} ({', '.join(columns)})
                SELECT {', '.join(columns)} FROM {temp_table}
                ON CONFLICT DO NOTHING
                RETURNING *
            """
            
            result_rows = await conn.fetch(insert_query)
            return [dict(row) for row in result_rows]
    
    def _apply_pagination(self, query: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
        """Aplica paginação à query"""
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        return query
    
    def _apply_filters(self, base_query: str, filters: Dict[str, Any]) -> tuple[str, list]:
        """Aplica filtros à query"""
        if not filters:
            return base_query, []
        
        where_clauses = []
        values = []
        param_count = 1
        
        for field, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    placeholders = [f"${param_count + i}" for i in range(len(value))]
                    where_clauses.append(f"{field} = ANY(ARRAY[{', '.join(placeholders)}])")
                    values.extend(value)
                    param_count += len(value)
                else:
                    where_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
        
        if where_clauses:
            if "WHERE" in base_query.upper():
                query = f"{base_query} AND {' AND '.join(where_clauses)}"
            else:
                query = f"{base_query} WHERE {' AND '.join(where_clauses)}"
        else:
            query = base_query
        
        return query, values