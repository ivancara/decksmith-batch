"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Card Repository

Implementação concreta do repositório de cartas usando PostgreSQL.
Segue padrões Repository e Single Responsibility Principle.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import asyncpg

from ...domain.entities import Card, Color, Rarity, CardType
from ...domain.repositories import ICardRepository


class PostgreSQLCardRepository(ICardRepository):
    """Implementação PostgreSQL do repositório de cartas"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
    
    async def save(self, card: Card) -> None:
        """Salva uma carta no banco"""
        query = """
            INSERT INTO cards (
                id, name, mana_cost, converted_mana_cost, type_line, oracle_text,
                power, toughness, loyalty, colors, color_identity, rarity,
                set_code, set_name, collector_number, multiverse_id, scryfall_id,
                archidekt_id, image_uri, price_usd, price_eur, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21, $22, $23
            ) ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                mana_cost = EXCLUDED.mana_cost,
                converted_mana_cost = EXCLUDED.converted_mana_cost,
                type_line = EXCLUDED.type_line,
                oracle_text = EXCLUDED.oracle_text,
                power = EXCLUDED.power,
                toughness = EXCLUDED.toughness,
                loyalty = EXCLUDED.loyalty,
                colors = EXCLUDED.colors,
                color_identity = EXCLUDED.color_identity,
                rarity = EXCLUDED.rarity,
                set_code = EXCLUDED.set_code,
                set_name = EXCLUDED.set_name,
                collector_number = EXCLUDED.collector_number,
                multiverse_id = EXCLUDED.multiverse_id,
                scryfall_id = EXCLUDED.scryfall_id,
                archidekt_id = EXCLUDED.archidekt_id,
                image_uri = EXCLUDED.image_uri,
                price_usd = EXCLUDED.price_usd,
                price_eur = EXCLUDED.price_eur,
                updated_at = NOW()
        """
        
        # Converter sets para arrays
        colors_array = [color.value for color in card.colors] if card.colors else []
        color_identity_array = [color.value for color in card.color_identity] if card.color_identity else []
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    query,
                    str(card.id), card.name, card.mana_cost, card.converted_mana_cost,
                    card.type_line, card.oracle_text, card.power, card.toughness,
                    card.loyalty, colors_array, color_identity_array,
                    card.rarity.value if card.rarity else None,
                    card.set_code, card.set_name, card.collector_number,
                    card.multiverse_id, card.scryfall_id, card.archidekt_id,
                    card.image_uri, float(card.price_usd) if card.price_usd else None,
                    float(card.price_eur) if card.price_eur else None,
                    card.created_at, card.updated_at
                )
                self.logger.debug(f"Saved card: {card.name}")
                
            except Exception as e:
                self.logger.error(f"Error saving card {card.name}: {e}")
                raise
    
    async def find_by_id(self, card_id: UUID) -> Optional[Card]:
        """Busca carta por ID"""
        query = "SELECT * FROM cards WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, str(card_id))
            if row:
                return self._row_to_card(row)
            return None
    
    async def find_by_name(self, name: str) -> Optional[Card]:
        """Busca carta por nome"""
        query = "SELECT * FROM cards WHERE LOWER(name) = LOWER($1) LIMIT 1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, name)
            if row:
                return self._row_to_card(row)
            return None
    
    async def find_by_archidekt_id(self, archidekt_id: str) -> Optional[Card]:
        """Busca carta por ID do Archidekt"""
        query = "SELECT * FROM cards WHERE archidekt_id = $1 LIMIT 1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, archidekt_id)
            if row:
                return self._row_to_card(row)
            return None
    
    async def find_by_scryfall_id(self, scryfall_id: str) -> Optional[Card]:
        """Busca carta por ID do Scryfall"""
        query = "SELECT * FROM cards WHERE scryfall_id = $1 LIMIT 1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, scryfall_id)
            if row:
                return self._row_to_card(row)
            return None
    
    async def search_by_name(self, name_pattern: str, limit: int = 50) -> List[Card]:
        """Busca cartas por padrão no nome"""
        query = """
            SELECT * FROM cards 
            WHERE name ILIKE $1 
            ORDER BY name 
            LIMIT $2
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, f"%{name_pattern}%", limit)
            return [self._row_to_card(row) for row in rows]
    
    async def find_by_set(self, set_code: str) -> List[Card]:
        """Busca cartas por código do set"""
        query = "SELECT * FROM cards WHERE set_code = $1 ORDER BY collector_number"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, set_code)
            return [self._row_to_card(row) for row in rows]
    
    async def find_by_colors(self, colors: List[str]) -> List[Card]:
        """Busca cartas por cores"""
        query = "SELECT * FROM cards WHERE colors && $1 ORDER BY name"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, colors)
            return [self._row_to_card(row) for row in rows]
    
    async def find_by_rarity(self, rarity: str) -> List[Card]:
        """Busca cartas por raridade"""
        query = "SELECT * FROM cards WHERE rarity = $1 ORDER BY name"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, rarity)
            return [self._row_to_card(row) for row in rows]
    
    async def exists_by_name(self, name: str) -> bool:
        """Verifica se carta existe por nome"""
        query = "SELECT EXISTS(SELECT 1 FROM cards WHERE LOWER(name) = LOWER($1))"
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, name)
            return bool(result)
    
    async def count_total(self) -> int:
        """Conta total de cartas"""
        query = "SELECT COUNT(*) FROM cards"
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query)
    
    async def find_recent(self, limit: int = 100) -> List[Card]:
        """Busca cartas mais recentes"""
        query = "SELECT * FROM cards ORDER BY created_at DESC LIMIT $1"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_card(row) for row in rows]
    
    async def delete(self, card_id: UUID) -> bool:
        """Remove uma carta"""
        query = "DELETE FROM cards WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, str(card_id))
            # Verifica se alguma linha foi afetada
            return result.split()[-1] == "1"
    
    def _row_to_card(self, row) -> Card:
        """Converte row do banco para entidade Card"""
        try:
            # Converter cores
            colors = set()
            if row['colors']:
                for color_value in row['colors']:
                    try:
                        colors.add(Color(color_value))
                    except ValueError:
                        pass
            
            color_identity = set()
            if row['color_identity']:
                for color_value in row['color_identity']:
                    try:
                        color_identity.add(Color(color_value))
                    except ValueError:
                        pass
            
            # Converter raridade
            rarity = None
            if row['rarity']:
                try:
                    rarity = Rarity(row['rarity'])
                except ValueError:
                    pass
            
            # Extrair tipos de carta
            card_types = Card._extract_card_types(row['type_line'] or "")
            
            return Card(
                id=UUID(row['id']),
                name=row['name'],
                mana_cost=row['mana_cost'] or "",
                converted_mana_cost=row['converted_mana_cost'] or 0,
                type_line=row['type_line'] or "",
                card_types=card_types,
                oracle_text=row['oracle_text'] or "",
                power=row['power'],
                toughness=row['toughness'],
                loyalty=row['loyalty'],
                colors=colors,
                color_identity=color_identity,
                rarity=rarity,
                set_code=row['set_code'] or "",
                set_name=row['set_name'] or "",
                collector_number=row['collector_number'] or "",
                multiverse_id=row['multiverse_id'],
                scryfall_id=row['scryfall_id'],
                archidekt_id=row['archidekt_id'],
                image_uri=row['image_uri'],
                price_usd=row['price_usd'],
                price_eur=row['price_eur'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            self.logger.error(f"Error converting row to Card: {e}")
            raise