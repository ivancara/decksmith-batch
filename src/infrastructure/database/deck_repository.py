"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Deck Repository Implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...domain.entities import Deck
from ...domain.repositories import IDeckRepository
from . import BaseRepository, DatabaseConnection


class PostgreSQLDeckRepository(BaseRepository, IDeckRepository):
    """Implementação PostgreSQL do repositório de decks"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
        self.table_name = "decks"
    
    async def save(self, deck: Deck) -> Deck:
        """Salva um deck"""
        deck_data = self._entity_to_dict(deck)
        deck_data = self._prepare_deck_data(deck_data)
        
        # Usar transação para salvar deck e cartas
        async with self.db.get_transaction() as conn:
            # Salvar dados básicos do deck
            basic_data = {k: v for k, v in deck_data.items() if k != "cartas"}
            row = await self._insert_or_update_with_conn(conn, self.table_name, basic_data, "id")
            
            if not row:
                raise Exception(f"Failed to save deck {deck.id}")
            
            # Salvar cartas do deck
            if deck.cartas:
                await self._save_deck_cards(conn, str(deck.id), deck.cartas)
            
            self.logger.info("Deck saved", deck_id=deck.id, name=deck.nome)
            saved_deck = await self._load_deck_with_cards(conn, str(deck.id))
            if not saved_deck:
                raise Exception(f"Failed to load saved deck {deck.id}")
            return saved_deck
    
    async def find_by_id(self, deck_id: UUID) -> Optional[Deck]:
        """Busca deck por ID"""
        async with self.db.get_connection() as conn:
            return await self._load_deck_with_cards(conn, str(deck_id))
    
    async def find_by_name_and_format(self, nome: str, formato: str) -> Optional[Deck]:
        """Busca deck por nome e formato"""
        query = "SELECT * FROM decks WHERE nome ILIKE $1 AND formato = $2 LIMIT 1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, nome, formato)
            if row:
                return await self._load_deck_with_cards(conn, row["id"])
            return None
    
    async def find_by_liga_magic_id(self, liga_id: str) -> Optional[Deck]:
        """Busca deck por ID do Liga Magic"""
        query = "SELECT * FROM decks WHERE liga_magic_id = $1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, liga_id)
            if row:
                return await self._load_deck_with_cards(conn, row["id"])
            return None
    
    async def get_all_for_ml_training(
        self,
        formatos: Optional[List[str]] = None,
        competitive_only: bool = False,
        min_cards: int = 60
    ) -> List[Deck]:
        """Busca decks para treinamento ML"""
        base_query = "SELECT * FROM decks WHERE total_cartas >= $1"
        values: List[Any] = [min_cards]
        param_count = 2
        
        if formatos:
            placeholders = [f"${param_count + i}" for i in range(len(formatos))]
            base_query += f" AND formato = ANY(ARRAY[{', '.join(placeholders)}])"
            values.extend(formatos)
            param_count += len(formatos)
        
        if competitive_only:
            base_query += " AND is_competitive = true"
        
        base_query += " ORDER BY created_at DESC"
        
        rows = await self.db.execute_query(base_query, *values)
        
        # Carregar decks com cartas (pode ser otimizado com JOIN)
        decks = []
        async with self.db.get_connection() as conn:
            for row in rows:
                deck = await self._load_deck_with_cards(conn, row["id"])
                if deck:
                    decks.append(deck)
        
        return decks
    
    async def get_deck_with_cards(self, deck_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca deck com suas cartas"""
        async with self.db.get_connection() as conn:
            # Buscar dados do deck
            deck_query = "SELECT * FROM decks WHERE id = $1"
            deck_row = await conn.fetchrow(deck_query, str(deck_id))
            
            if not deck_row:
                return None
            
            # Buscar cartas do deck
            cards_query = """
                SELECT c.*, dc.quantidade
                FROM cartas c
                JOIN deck_cartas dc ON c.id = dc.carta_id
                WHERE dc.deck_id = $1
                ORDER BY dc.quantidade DESC, c.nome
            """
            
            card_rows = await conn.fetch(cards_query, str(deck_id))
            
            return {
                "id": deck_row["id"],
                "nome": deck_row["nome"],
                "formato": deck_row["formato"],
                "comandante": deck_row.get("comandante"),
                "cores": deck_row.get("cores", []),
                "total_cartas": deck_row.get("total_cartas", 0),
                "is_competitive": deck_row.get("is_competitive", False),
                "cards": [dict(row) for row in card_rows]
            }
    
    async def get_all_for_export(self,
                                formatos: Optional[List[str]] = None,
                                date_from: Optional[datetime] = None,
                                date_to: Optional[datetime] = None) -> List[Deck]:
        """Busca decks para exportação"""
        base_query = "SELECT * FROM decks"
        filters = {}
        
        if formatos:
            filters["formato"] = formatos
        if date_from:
            filters["created_at >="] = date_from
        if date_to:
            filters["created_at <="] = date_to
        
        query, values = self._apply_filters(base_query, filters)
        query += " ORDER BY created_at DESC"
        
        rows = await self.db.execute_query(query, *values)
        
        # Carregar decks básicos (sem cartas para performance)
        return [self._row_to_deck(row) for row in rows]
    
    async def save_batch(self, decks: List[Deck]) -> List[Deck]:
        """Salva múltiplos decks em batch"""
        if not decks:
            return []
        
        saved_decks = []
        
        # Para decks, é mais complexo fazer batch devido às cartas
        # Por agora, salvar um por um
        for deck in decks:
            try:
                saved_deck = await self.save(deck)
                saved_decks.append(saved_deck)
            except Exception as e:
                self.logger.error("Failed to save deck in batch", 
                                deck_id=deck.id, error=str(e))
        
        self.logger.info("Batch decks saved", count=len(saved_decks))
        return saved_decks
    
    async def count_by_format(self) -> Dict[str, int]:
        """Conta decks por formato"""
        query = """
            SELECT formato, COUNT(*) as count
            FROM decks
            GROUP BY formato
            ORDER BY count DESC
        """
        
        rows = await self.db.execute_query(query)
        return {row["formato"]: row["count"] for row in rows}
    
    async def get_popular_commanders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca comandantes mais populares"""
        query = """
            SELECT comandante, COUNT(*) as usage_count
            FROM decks
            WHERE comandante IS NOT NULL AND formato = 'Commander'
            GROUP BY comandante
            ORDER BY usage_count DESC
            LIMIT $1
        """
        
        return await self.db.execute_query(query, limit)
    
    async def get_format_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Obtém estatísticas por formato"""
        query = """
            SELECT 
                formato,
                COUNT(*) as total_decks,
                AVG(total_cartas) as avg_cards,
                AVG(custo_medio_mana) as avg_cmc,
                COUNT(CASE WHEN is_competitive THEN 1 END) as competitive_count
            FROM decks
            GROUP BY formato
            ORDER BY total_decks DESC
        """
        
        rows = await self.db.execute_query(query)
        
        stats = {}
        for row in rows:
            stats[row["formato"]] = {
                "total_decks": row["total_decks"],
                "avg_cards": float(row["avg_cards"]) if row["avg_cards"] else 0,
                "avg_cmc": float(row["avg_cmc"]) if row["avg_cmc"] else 0,
                "competitive_count": row["competitive_count"],
                "competitive_percentage": (row["competitive_count"] / row["total_decks"]) * 100 if row["total_decks"] > 0 else 0
            }
        
        return stats
    
    async def _save_deck_cards(self, conn, deck_id: str, cartas: List[Dict[str, Any]]):
        """Salva cartas do deck"""
        # Primeiro, remove cartas existentes
        await conn.execute("DELETE FROM deck_cartas WHERE deck_id = $1", deck_id)
        
        # Inserir novas cartas
        if cartas:
            values = []
            for carta in cartas:
                values.append((deck_id, str(carta["carta_id"]), carta["quantidade"]))
            
            await conn.executemany(
                "INSERT INTO deck_cartas (deck_id, carta_id, quantidade) VALUES ($1, $2, $3)",
                values
            )
    
    async def _load_deck_with_cards(self, conn, deck_id: str) -> Optional[Deck]:
        """Carrega deck com suas cartas"""
        # Buscar dados básicos do deck
        deck_row = await conn.fetchrow("SELECT * FROM decks WHERE id = $1", deck_id)
        
        if not deck_row:
            return None
        
        # Buscar cartas do deck
        cards_query = """
            SELECT carta_id, quantidade
            FROM deck_cartas
            WHERE deck_id = $1
            ORDER BY quantidade DESC
        """
        
        card_rows = await conn.fetch(cards_query, deck_id)
        
        # Converter para formato da entidade
        cartas = [
            {
                "carta_id": UUID(row["carta_id"]),
                "quantidade": row["quantidade"]
            }
            for row in card_rows
        ]
        
        # Criar entidade Deck
        deck_data = dict(deck_row)
        deck_data["cartas"] = cartas
        
        return self._row_to_deck(deck_data)
    
    async def _insert_or_update_with_conn(self, conn, table: str, data: Dict[str, Any], id_field: str = "id"):
        """Insert ou update usando conexão específica"""
        id_value = data.get(id_field)
        
        if id_value:
            # Verificar se existe
            exists = await conn.fetchval(f"SELECT 1 FROM {table} WHERE {id_field} = $1", id_value)
            
            if exists:
                # UPDATE
                query, values = self._build_update_query(table, data, id_field)
            else:
                # INSERT
                query, values = self._build_insert_query(table, data)
        else:
            # INSERT
            query, values = self._build_insert_query(table, data)
        
        row = await conn.fetchrow(query, *values)
        return dict(row) if row else None
    
    def _prepare_deck_data(self, deck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados do deck para inserção no banco"""
        # Converter arrays
        if "cores" in deck_data and isinstance(deck_data["cores"], list):
            deck_data["cores"] = deck_data["cores"]
        
        if "tags" in deck_data and isinstance(deck_data["tags"], list):
            deck_data["tags"] = deck_data["tags"]
        
        # Garantir campos obrigatórios
        deck_data.setdefault("total_cartas", 0)
        deck_data.setdefault("custo_medio_mana", 0.0)
        deck_data.setdefault("cores", [])
        deck_data.setdefault("is_competitive", False)
        deck_data.setdefault("tags", [])
        
        # Converter dicionários para JSON
        if "curva_mana" in deck_data and isinstance(deck_data["curva_mana"], dict):
            import json
            deck_data["curva_mana"] = json.dumps(deck_data["curva_mana"])
        
        if "distribuicao_tipos" in deck_data and isinstance(deck_data["distribuicao_tipos"], dict):
            import json
            deck_data["distribuicao_tipos"] = json.dumps(deck_data["distribuicao_tipos"])
        
        return deck_data
    
    def _row_to_deck(self, row: Dict[str, Any]) -> Deck:
        """Converte row do banco para entidade Deck"""
        # Converter JSON strings de volta para dicts
        curva_mana = {}
        distribuicao_tipos = {}
        
        if row.get("curva_mana"):
            try:
                import json
                curva_mana = json.loads(row["curva_mana"])
            except:
                pass
        
        if row.get("distribuicao_tipos"):
            try:
                import json
                distribuicao_tipos = json.loads(row["distribuicao_tipos"])
            except:
                pass
        
        return Deck(
            id=UUID(row["id"]),
            nome=row.get("nome", ""),
            formato=row.get("formato", "Commander"),
            comandante=row.get("comandante"),
            cores=row.get("cores", []),
            cartas=row.get("cartas", []),
            dono=row.get("dono", ""),
            total_cartas=row.get("total_cartas", 0),
            custo_medio_mana=row.get("custo_medio_mana", 0.0),
            curva_mana=curva_mana,
            distribuicao_tipos=distribuicao_tipos,
            liga_magic_id=row.get("liga_magic_id"),
            is_competitive=row.get("is_competitive", False),
            tags=row.get("tags", []),
            created_at=row.get("created_at", datetime.now()),
            updated_at=row.get("updated_at", datetime.now())
        )