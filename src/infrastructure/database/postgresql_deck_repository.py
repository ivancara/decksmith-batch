"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Deck Repository

Implementação concreta do repositório de decks usando PostgreSQL.
Gerencia decks e relacionamentos com cartas.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import asyncpg

from ...domain.entities import Deck, DeckCard, DeckFormat, Color
from ...domain.repositories import IDeckRepository


class PostgreSQLDeckRepository(IDeckRepository):
    """Implementação PostgreSQL do repositório de decks"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
    
    async def save(self, deck: Deck) -> None:
        """Salva um deck no banco com suas cartas"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Salvar deck principal
                    await self._save_deck_main(conn, deck)
                    
                    # Limpar cartas existentes
                    await conn.execute("DELETE FROM deck_cards WHERE deck_id = $1", str(deck.id))
                    
                    # Salvar cartas do deck
                    if deck.cards:
                        await self._save_deck_cards(conn, deck)
                    
                    self.logger.debug(f"Saved deck: {deck.name} with {len(deck.cards)} cards")
                    
                except Exception as e:
                    self.logger.error(f"Error saving deck {deck.name}: {e}")
                    raise
    
    async def _save_deck_main(self, conn: asyncpg.Connection, deck: Deck) -> None:
        """Salva dados principais do deck"""
        query = """
            INSERT INTO decks (
                id, name, description, format, archidekt_id, archidekt_url,
                owner_name, tags, is_public, is_featured, view_count, like_count,
                total_cards, main_deck_size, sideboard_size, average_cmc,
                estimated_price_usd, color_identity, created_at, updated_at, scraped_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21
            ) ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                format = EXCLUDED.format,
                archidekt_id = EXCLUDED.archidekt_id,
                archidekt_url = EXCLUDED.archidekt_url,
                owner_name = EXCLUDED.owner_name,
                tags = EXCLUDED.tags,
                is_public = EXCLUDED.is_public,
                is_featured = EXCLUDED.is_featured,
                view_count = EXCLUDED.view_count,
                like_count = EXCLUDED.like_count,
                total_cards = EXCLUDED.total_cards,
                main_deck_size = EXCLUDED.main_deck_size,
                sideboard_size = EXCLUDED.sideboard_size,
                average_cmc = EXCLUDED.average_cmc,
                estimated_price_usd = EXCLUDED.estimated_price_usd,
                color_identity = EXCLUDED.color_identity,
                updated_at = NOW(),
                scraped_at = EXCLUDED.scraped_at
        """
        
        # Converter dados
        tags_array = list(deck.tags) if deck.tags else []
        color_identity_array = [color.value for color in deck.color_identity] if deck.color_identity else []
        
        await conn.execute(
            query,
            str(deck.id), deck.name, deck.description,
            deck.format.value if deck.format else None,
            deck.archidekt_id, deck.archidekt_url, deck.owner_name,
            tags_array, deck.is_public, deck.is_featured,
            deck.view_count, deck.like_count, deck.total_cards,
            deck.main_deck_size, deck.sideboard_size,
            float(deck.average_cmc) if deck.average_cmc else None,
            float(deck.estimated_price_usd) if deck.estimated_price_usd else None,
            color_identity_array, deck.created_at, deck.updated_at, deck.scraped_at
        )
    
    async def _save_deck_cards(self, conn: asyncpg.Connection, deck: Deck) -> None:
        """Salva cartas do deck"""
        if not deck.cards:
            return
        
        # Preparar dados para inserção em lote
        card_data = []
        for deck_card in deck.cards:
            card_data.append((
                str(deck.id),
                str(deck_card.card_id),
                deck_card.quantity,
                deck_card.category
            ))
        
        # Inserção em lote
        await conn.executemany(
            """
            INSERT INTO deck_cards (deck_id, card_id, quantity, category)
            VALUES ($1, $2, $3, $4)
            """,
            card_data
        )
    
    async def find_by_id(self, deck_id: UUID) -> Optional[Deck]:
        """Busca deck por ID"""
        query = "SELECT * FROM decks WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, str(deck_id))
            if row:
                deck = self._row_to_deck(row)
                # Carregar cartas
                await self._load_deck_cards(conn, deck)
                return deck
            return None
    
    async def find_by_archidekt_id(self, archidekt_id: str) -> Optional[Deck]:
        """Busca deck por ID do Archidekt"""
        query = "SELECT * FROM decks WHERE archidekt_id = $1 LIMIT 1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, archidekt_id)
            if row:
                deck = self._row_to_deck(row)
                await self._load_deck_cards(conn, deck)
                return deck
            return None
    
    async def find_by_name(self, name: str) -> List[Deck]:
        """Busca decks por nome"""
        query = "SELECT * FROM decks WHERE name ILIKE $1 ORDER BY name"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, f"%{name}%")
            decks = []
            for row in rows:
                deck = self._row_to_deck(row)
                await self._load_deck_cards(conn, deck)
                decks.append(deck)
            return decks
    
    async def find_by_format(self, format: str) -> List[Deck]:
        """Busca decks por formato"""
        query = "SELECT * FROM decks WHERE format = $1 ORDER BY updated_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, format)
            decks = []
            for row in rows:
                deck = self._row_to_deck(row)
                await self._load_deck_cards(conn, deck)
                decks.append(deck)
            return decks
    
    async def find_by_owner(self, owner_name: str) -> List[Deck]:
        """Busca decks por proprietário"""
        query = "SELECT * FROM decks WHERE owner_name = $1 ORDER BY updated_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, owner_name)
            decks = []
            for row in rows:
                deck = self._row_to_deck(row)
                await self._load_deck_cards(conn, deck)
                decks.append(deck)
            return decks
    
    async def find_by_colors(self, colors: List[str]) -> List[Deck]:
        """Busca decks por identidade de cor"""
        query = "SELECT * FROM decks WHERE color_identity && $1 ORDER BY updated_at DESC"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, colors)
            decks = []
            for row in rows:
                deck = self._row_to_deck(row)
                await self._load_deck_cards(conn, deck)
                decks.append(deck)
            return decks
    
    async def find_public_decks(self, limit: int = 100) -> List[Deck]:
        """Busca decks públicos"""
        query = "SELECT * FROM decks WHERE is_public = true ORDER BY updated_at DESC LIMIT $1"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_deck(row) for row in rows]
    
    async def find_featured_decks(self, limit: int = 50) -> List[Deck]:
        """Busca decks em destaque"""
        query = "SELECT * FROM decks WHERE is_featured = true ORDER BY updated_at DESC LIMIT $1"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_deck(row) for row in rows]
    
    async def find_popular_decks(self, limit: int = 100) -> List[Deck]:
        """Busca decks populares (ordenados por views/likes)"""
        query = """
            SELECT * FROM decks 
            WHERE is_public = true 
            ORDER BY (view_count + like_count * 2) DESC 
            LIMIT $1
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_deck(row) for row in rows]
    
    async def find_recent(self, limit: int = 100) -> List[Deck]:
        """Busca decks mais recentes"""
        query = "SELECT * FROM decks ORDER BY created_at DESC LIMIT $1"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_deck(row) for row in rows]
    
    async def exists_by_archidekt_id(self, archidekt_id: str) -> bool:
        """Verifica se deck existe por ID do Archidekt"""
        query = "SELECT EXISTS(SELECT 1 FROM decks WHERE archidekt_id = $1)"
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, archidekt_id)
            return bool(result)
    
    async def count_total(self) -> int:
        """Conta total de decks"""
        query = "SELECT COUNT(*) FROM decks"
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query)
    
    async def count_by_format(self, format: str) -> int:
        """Conta decks por formato"""
        query = "SELECT COUNT(*) FROM decks WHERE format = $1"
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, format)
    
    async def find_decks_with_card(self, card_id: UUID) -> List[Deck]:
        """Busca decks que contêm uma carta específica"""
        query = """
            SELECT DISTINCT d.* FROM decks d
            JOIN deck_cards dc ON d.id = dc.deck_id
            WHERE dc.card_id = $1
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, str(card_id))
            return [self._row_to_deck(row) for row in rows]
    
    async def get_deck_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais dos decks"""
        async with self.pool.acquire() as conn:
            stats_query = """
                SELECT 
                    COUNT(*) as total_decks,
                    COUNT(*) FILTER (WHERE is_public = true) as public_decks,
                    COUNT(*) FILTER (WHERE is_featured = true) as featured_decks,
                    AVG(total_cards) as avg_deck_size,
                    AVG(view_count) as avg_views,
                    AVG(like_count) as avg_likes
                FROM decks
            """
            
            formats_query = """
                SELECT format, COUNT(*) as count
                FROM decks
                WHERE format IS NOT NULL
                GROUP BY format
                ORDER BY count DESC
            """
            
            stats = await conn.fetchrow(stats_query)
            formats = await conn.fetch(formats_query)
            
            return {
                "total_decks": stats['total_decks'],
                "public_decks": stats['public_decks'],
                "featured_decks": stats['featured_decks'],
                "average_deck_size": float(stats['avg_deck_size']) if stats['avg_deck_size'] else 0,
                "average_views": float(stats['avg_views']) if stats['avg_views'] else 0,
                "average_likes": float(stats['avg_likes']) if stats['avg_likes'] else 0,
                "formats": {row['format']: row['count'] for row in formats}
            }
    
    async def delete(self, deck_id: UUID) -> bool:
        """Remove um deck"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Remover cartas do deck primeiro
                await conn.execute("DELETE FROM deck_cards WHERE deck_id = $1", str(deck_id))
                
                # Remover deck
                result = await conn.execute("DELETE FROM decks WHERE id = $1", str(deck_id))
                return result.split()[-1] == "1"
    
    async def _load_deck_cards(self, conn: asyncpg.Connection, deck: Deck) -> None:
        """Carrega cartas do deck"""
        query = """
            SELECT card_id, quantity, category
            FROM deck_cards
            WHERE deck_id = $1
        """
        
        rows = await conn.fetch(query, str(deck.id))
        deck.cards = []
        
        for row in rows:
            deck_card = DeckCard(
                card_id=UUID(row['card_id']),
                quantity=row['quantity'],
                category=row['category']
            )
            deck.cards.append(deck_card)
    
    def _row_to_deck(self, row) -> Deck:
        """Converte row do banco para entidade Deck"""
        try:
            # Converter formato
            format_enum = None
            if row['format']:
                try:
                    format_enum = DeckFormat(row['format'])
                except ValueError:
                    pass
            
            # Converter tags
            tags = set(row['tags']) if row['tags'] else set()
            
            # Converter identidade de cor
            color_identity = set()
            if row['color_identity']:
                for color_value in row['color_identity']:
                    try:
                        color_identity.add(Color(color_value))
                    except ValueError:
                        pass
            
            return Deck(
                id=UUID(row['id']),
                name=row['name'],
                description=row['description'] or "",
                format=format_enum,
                archidekt_id=row['archidekt_id'],
                archidekt_url=row['archidekt_url'],
                owner_name=row['owner_name'],
                cards=[],  # Será carregado separadamente
                tags=tags,
                is_public=row['is_public'],
                is_featured=row['is_featured'],
                view_count=row['view_count'],
                like_count=row['like_count'],
                total_cards=row['total_cards'],
                main_deck_size=row['main_deck_size'],
                sideboard_size=row['sideboard_size'],
                average_cmc=row['average_cmc'],
                estimated_price_usd=row['estimated_price_usd'],
                color_identity=color_identity,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                scraped_at=row['scraped_at']
            )
            
        except Exception as e:
            self.logger.error(f"Error converting row to Deck: {e}")
            raise