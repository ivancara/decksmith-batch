"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Card Repository Implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...domain.entities import Card
from ...domain.repositories import ICardRepository
from . import BaseRepository, DatabaseConnection


class PostgreSQLCardRepository(BaseRepository, ICardRepository):
    """Implementação PostgreSQL do repositório de cartas"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
        self.table_name = "cartas"
    
    async def save(self, card: Card) -> Card:
        """Salva uma carta"""
        card_data = self._entity_to_dict(card)
        
        # Converter campos específicos
        card_data = self._prepare_card_data(card_data)
        
        row = await self._insert_or_update(self.table_name, card_data, "id")
        
        if row:
            self.logger.info("Card saved", card_id=card.id, name=card.nome)
            return self._row_to_card(row)
        
        raise Exception(f"Failed to save card {card.id}")
    
    async def find_by_id(self, card_id: UUID) -> Optional[Card]:
        """Busca carta por ID"""
        query = "SELECT * FROM cartas WHERE id = $1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, str(card_id))
            return self._row_to_card(dict(row)) if row else None
    
    async def find_by_name(self, nome: str) -> Optional[Card]:
        """Busca carta por nome"""
        query = "SELECT * FROM cartas WHERE nome ILIKE $1 LIMIT 1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, nome)
            return self._row_to_card(dict(row)) if row else None
    
    async def find_by_liga_magic_id(self, liga_id: str) -> Optional[Card]:
        """Busca carta por ID do Liga Magic"""
        query = "SELECT * FROM cartas WHERE liga_magic_id = $1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, liga_id)
            return self._row_to_card(dict(row)) if row else None
    
    async def save_batch(self, cards: List[Card]) -> List[Card]:
        """Salva múltiplas cartas em batch"""
        if not cards:
            return []
        
        cards_data = [self._prepare_card_data(self._entity_to_dict(card)) for card in cards]
        
        try:
            rows = await self._batch_insert(self.table_name, cards_data)
            saved_cards = [self._row_to_card(row) for row in rows]
            
            self.logger.info("Batch cards saved", count=len(saved_cards))
            return saved_cards
            
        except Exception as e:
            self.logger.error("Failed to save batch cards", error=str(e))
            # Fallback: salvar uma por uma
            saved_cards = []
            for card in cards:
                try:
                    saved_card = await self.save(card)
                    saved_cards.append(saved_card)
                except Exception as card_error:
                    self.logger.error("Failed to save individual card", 
                                    card_id=card.id, error=str(card_error))
            
            return saved_cards
    
    async def get_all_for_export(self, 
                                date_from: Optional[datetime] = None,
                                date_to: Optional[datetime] = None) -> List[Card]:
        """Busca todas as cartas para exportação"""
        base_query = "SELECT * FROM cartas"
        filters = {}
        
        if date_from:
            filters["created_at >="] = date_from
        if date_to:
            filters["created_at <="] = date_to
        
        query, values = self._apply_filters(base_query, filters)
        query += " ORDER BY created_at DESC"
        
        rows = await self.db.execute_query(query, *values)
        return [self._row_to_card(row) for row in rows]
    
    async def count_total(self) -> int:
        """Conta total de cartas"""
        query = "SELECT COUNT(*) FROM cartas"
        
        async with self.db.get_connection() as conn:
            return await conn.fetchval(query)
    
    async def search_cards(self, 
                          search_term: str,
                          cores: Optional[List[str]] = None,
                          tipos: Optional[List[str]] = None,
                          cmc_min: Optional[int] = None,
                          cmc_max: Optional[int] = None,
                          limit: int = 100) -> List[Card]:
        """Busca cartas com filtros avançados"""
        base_query = """
            SELECT * FROM cartas 
            WHERE (nome ILIKE $1 OR texto ILIKE $1)
        """
        values: List[Any] = [f"%{search_term}%"]
        param_count = 2
        
        # Filtro por cores
        if cores:
            placeholders = [f"${param_count + i}" for i in range(len(cores))]
            base_query += f" AND cores && ARRAY[{', '.join(placeholders)}]"
            values.extend(cores)
            param_count += len(cores)
        
        # Filtro por tipos
        if tipos:
            type_conditions = []
            for tipo in tipos:
                type_conditions.append(f"tipo ILIKE ${param_count}")
                values.append(f"%{tipo}%")
                param_count += 1
            base_query += f" AND ({' OR '.join(type_conditions)})"
        
        # Filtro por CMC
        if cmc_min is not None:
            base_query += f" AND cmc >= ${param_count}"
            values.append(cmc_min)
            param_count += 1
        
        if cmc_max is not None:
            base_query += f" AND cmc <= ${param_count}"
            values.append(cmc_max)
            param_count += 1
        
        base_query += f" ORDER BY nome LIMIT {limit}"
        
        rows = await self.db.execute_query(base_query, *values)
        return [self._row_to_card(row) for row in rows]
    
    async def get_cards_by_format_popularity(self, formato: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Busca cartas mais populares em um formato"""
        query = """
            SELECT c.*, COUNT(dc.carta_id) as usage_count
            FROM cartas c
            JOIN deck_cartas dc ON c.id = dc.carta_id
            JOIN decks d ON dc.deck_id = d.id
            WHERE d.formato = $1
            GROUP BY c.id
            ORDER BY usage_count DESC
            LIMIT $2
        """
        
        rows = await self.db.execute_query(query, formato, limit)
        return rows
    
    def _prepare_card_data(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados da carta para inserção no banco"""
        # Converter listas para arrays PostgreSQL
        if "cores" in card_data and isinstance(card_data["cores"], list):
            card_data["cores"] = card_data["cores"]
        
        # Garantir que campos obrigatórios existam
        card_data.setdefault("cmc", 0)
        card_data.setdefault("cores", [])
        card_data.setdefault("raridade", "common")
        card_data.setdefault("texto", "")
        card_data.setdefault("poder", None)
        card_data.setdefault("resistencia", None)
        card_data.setdefault("preco_usd", None)
        
        # Remover campos que não existem na tabela
        fields_to_remove = ["is_creature", "is_spell", "is_artifact", "is_land", "is_planeswalker"]
        for field in fields_to_remove:
            card_data.pop(field, None)
        
        return card_data
    
    def _row_to_card(self, row: Dict[str, Any]) -> Card:
        """Converte row do banco para entidade Card"""
        return Card(
            id=UUID(row["id"]),
            nome=row.get("nome", ""),
            tipo=row.get("tipo", ""),
            custo_mana=row.get("custo_mana", ""),
            cmc=row.get("cmc", 0),
            cores=row.get("cores", []),
            raridade=row.get("raridade", "common"),
            texto=row.get("texto", ""),
            poder=row.get("poder"),
            resistencia=row.get("resistencia"),
            edicao=row.get("edicao", ""),
            preco_usd=row.get("preco_usd"),
            liga_magic_id=row.get("liga_magic_id"),
            scryfall_id=row.get("scryfall_id"),
            created_at=row.get("created_at", datetime.now()),
            updated_at=row.get("updated_at", datetime.now())
        )