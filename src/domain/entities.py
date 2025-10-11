"""
DeckSmith Batch Processing System
Domain Layer - Core Entities

Implementação seguindo Domain Driven Design (DDD), SOLID principles e Clean Code.
Entidades ricas com comportamentos e invariantes bem definidos.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from enum import Enum
import logging


class CardType(Enum):
    """Tipos de cartas MTG"""
    CREATURE = "Creature"
    INSTANT = "Instant"
    SORCERY = "Sorcery"
    ENCHANTMENT = "Enchantment"
    ARTIFACT = "Artifact"
    PLANESWALKER = "Planeswalker"
    LAND = "Land"
    TRIBAL = "Tribal"


class Rarity(Enum):
    """Raridades das cartas"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    MYTHIC = "mythic"
    SPECIAL = "special"


class Color(Enum):
    """Cores do MTG"""
    WHITE = "W"
    BLUE = "U"
    BLACK = "B"
    RED = "R"
    GREEN = "G"
    COLORLESS = ""


class DeckFormat(Enum):
    """Formatos de deck"""
    STANDARD = "Standard"
    MODERN = "Modern"
    LEGACY = "Legacy"
    VINTAGE = "Vintage"
    COMMANDER = "Commander"
    PIONEER = "Pioneer"
    HISTORIC = "Historic"
    ALCHEMY = "Alchemy"
    PAUPER = "Pauper"
    BRAWL = "Brawl"


class ScrapingStatus(Enum):
    """Status do processo de scraping"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Card:
    """
    Entidade Card representa uma carta individual do MTG.
    Seguindo princípios DDD com invariantes e regras de negócio.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = field(default="")
    mana_cost: str = field(default="")
    converted_mana_cost: int = field(default=0)
    type_line: str = field(default="")
    card_types: Set[CardType] = field(default_factory=set)
    oracle_text: str = field(default="")
    power: Optional[str] = field(default=None)
    toughness: Optional[str] = field(default=None)
    loyalty: Optional[str] = field(default=None)
    colors: Set[Color] = field(default_factory=set)
    color_identity: Set[Color] = field(default_factory=set)
    rarity: Optional[Rarity] = field(default=None)
    set_code: str = field(default="")
    set_name: str = field(default="")
    collector_number: str = field(default="")
    multiverse_id: Optional[int] = field(default=None)
    scryfall_id: Optional[str] = field(default=None)
    archidekt_id: Optional[str] = field(default=None)
    image_uri: Optional[str] = field(default=None)
    price_usd: Optional[Decimal] = field(default=None)
    price_eur: Optional[Decimal] = field(default=None)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validações após inicialização"""
        self._validate_invariants()
    
    def _validate_invariants(self):
        """Valida invariantes da entidade"""
        if not self.name or not self.name.strip():
            raise ValueError("Card name cannot be empty")
        
        if self.converted_mana_cost < 0:
            raise ValueError("Converted mana cost cannot be negative")
        
        # Normalizar nome
        self.name = self.name.strip()
    
    @classmethod
    def create_from_archidekt(
        cls,
        name: str,
        mana_cost: str = "",
        type_line: str = "",
        oracle_text: str = "",
        power: Optional[str] = None,
        toughness: Optional[str] = None,
        colors: Optional[List[str]] = None,
        rarity: Optional[str] = None,
        set_code: str = "",
        archidekt_id: Optional[str] = None,
        **kwargs
    ) -> 'Card':
        """Factory method para criar carta a partir de dados do Archidekt"""
        
        # Converter cores
        color_set = set()
        if colors:
            for color in colors:
                try:
                    color_set.add(Color(color.upper()))
                except ValueError:
                    pass  # Ignorar cores inválidas
        
        # Converter raridade
        rarity_enum = None
        if rarity:
            try:
                rarity_enum = Rarity(rarity.lower())
            except ValueError:
                pass
        
        # Calcular CMC a partir do mana cost
        cmc = cls._calculate_cmc(mana_cost)
        
        # Extrair tipos de carta
        card_types = cls._extract_card_types(type_line)
        
        return cls(
            name=name,
            mana_cost=mana_cost,
            converted_mana_cost=cmc,
            type_line=type_line,
            card_types=card_types,
            oracle_text=oracle_text,
            power=power,
            toughness=toughness,
            colors=color_set,
            color_identity=color_set,  # Simplificação
            rarity=rarity_enum,
            set_code=set_code,
            archidekt_id=archidekt_id,
            **kwargs
        )
    
    @staticmethod
    def _calculate_cmc(mana_cost: str) -> int:
        """Calcula Converted Mana Cost a partir do mana cost"""
        if not mana_cost:
            return 0
        
        import re
        # Extrair números do mana cost
        numbers = re.findall(r'\d+', mana_cost)
        total = sum(int(num) for num in numbers)
        
        # Contar símbolos de mana (não números)
        symbols = re.findall(r'\{[WUBRG]\}', mana_cost)
        total += len(symbols)
        
        return total
    
    @staticmethod
    def _extract_card_types(type_line: str) -> Set[CardType]:
        """Extrai tipos de carta da type line"""
        types = set()
        if not type_line:
            return types
        
        type_line_upper = type_line.upper()
        for card_type in CardType:
            if card_type.value.upper() in type_line_upper:
                types.add(card_type)
        
        return types
    
    def is_creature(self) -> bool:
        """Verifica se é criatura"""
        return CardType.CREATURE in self.card_types
    
    def is_spell(self) -> bool:
        """Verifica se é mágica"""
        return any(t in self.card_types for t in [
            CardType.INSTANT, CardType.SORCERY
        ])
    
    def is_permanent(self) -> bool:
        """Verifica se é permanente"""
        return any(t in self.card_types for t in [
            CardType.CREATURE, CardType.ENCHANTMENT, CardType.ARTIFACT,
            CardType.PLANESWALKER, CardType.LAND
        ])
    
    def get_color_identity_string(self) -> str:
        """Retorna identidade de cor como string"""
        return "".join(sorted(color.value for color in self.color_identity))
    
    def update_price(self, price_usd: Optional[Decimal] = None, price_eur: Optional[Decimal] = None):
        """Atualiza preços da carta"""
        if price_usd is not None:
            self.price_usd = price_usd
        if price_eur is not None:
            self.price_eur = price_eur
        self.updated_at = datetime.now()


@dataclass
class DeckCard:
    """
    Representa uma carta em um deck com quantidade e categoria.
    Value Object para o relacionamento Deck-Card.
    """
    card_id: UUID
    quantity: int
    category: str = "main"  # main, sideboard, commander, companion
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Card quantity must be positive")
        
        if self.category not in ["main", "sideboard", "commander", "companion"]:
            raise ValueError(f"Invalid category: {self.category}")


@dataclass
class Deck:
    """
    Entidade Deck representa um deck completo de MTG.
    Agregado root que gerencia cartas e suas quantidades.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = field(default="")
    description: str = field(default="")
    format: Optional[DeckFormat] = field(default=None)
    archidekt_id: Optional[str] = field(default=None)
    archidekt_url: Optional[str] = field(default=None)
    owner_name: Optional[str] = field(default=None)
    cards: List[DeckCard] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    is_public: bool = field(default=True)
    is_featured: bool = field(default=False)
    view_count: int = field(default=0)
    like_count: int = field(default=0)
    total_cards: int = field(default=0)
    main_deck_size: int = field(default=0)
    sideboard_size: int = field(default=0)
    average_cmc: Optional[Decimal] = field(default=None)
    estimated_price_usd: Optional[Decimal] = field(default=None)
    color_identity: Set[Color] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validações após inicialização"""
        self._validate_invariants()
    
    def _validate_invariants(self):
        """Valida invariantes da entidade"""
        if not self.name or not self.name.strip():
            raise ValueError("Deck name cannot be empty")
        
        self.name = self.name.strip()
    
    @classmethod
    def create_from_archidekt(
        cls,
        name: str,
        archidekt_id: str,
        archidekt_url: str,
        format: Optional[str] = None,
        description: str = "",
        owner_name: Optional[str] = None,
        is_public: bool = True,
        **kwargs
    ) -> 'Deck':
        """Factory method para criar deck a partir de dados do Archidekt"""
        
        # Converter formato
        format_enum = None
        if format:
            try:
                format_enum = DeckFormat(format)
            except ValueError:
                # Tentar encontrar formato similar
                format_upper = format.upper()
                for deck_format in DeckFormat:
                    if deck_format.value.upper() == format_upper:
                        format_enum = deck_format
                        break
        
        return cls(
            name=name,
            archidekt_id=archidekt_id,
            archidekt_url=archidekt_url,
            format=format_enum,
            description=description,
            owner_name=owner_name,
            is_public=is_public,
            **kwargs
        )
    
    def add_card(self, card_id: UUID, quantity: int, category: str = "main"):
        """Adiciona carta ao deck"""
        # Verificar se carta já existe
        for existing_card in self.cards:
            if existing_card.card_id == card_id and existing_card.category == category:
                existing_card.quantity += quantity
                self._update_statistics()
                return
        
        # Adicionar nova carta
        deck_card = DeckCard(card_id=card_id, quantity=quantity, category=category)
        self.cards.append(deck_card)
        self._update_statistics()
    
    def remove_card(self, card_id: UUID, category: str = "main"):
        """Remove carta do deck"""
        self.cards = [
            card for card in self.cards 
            if not (card.card_id == card_id and card.category == category)
        ]
        self._update_statistics()
    
    def update_card_quantity(self, card_id: UUID, new_quantity: int, category: str = "main"):
        """Atualiza quantidade de uma carta"""
        for card in self.cards:
            if card.card_id == card_id and card.category == category:
                if new_quantity <= 0:
                    self.remove_card(card_id, category)
                else:
                    card.quantity = new_quantity
                    self._update_statistics()
                return
        
        # Se não encontrou, adicionar
        if new_quantity > 0:
            self.add_card(card_id, new_quantity, category)
    
    def get_main_deck_cards(self) -> List[DeckCard]:
        """Retorna cartas do deck principal"""
        return [card for card in self.cards if card.category == "main"]
    
    def get_sideboard_cards(self) -> List[DeckCard]:
        """Retorna cartas do sideboard"""
        return [card for card in self.cards if card.category == "sideboard"]
    
    def get_commander_cards(self) -> List[DeckCard]:
        """Retorna comandantes"""
        return [card for card in self.cards if card.category == "commander"]
    
    def _update_statistics(self):
        """Atualiza estatísticas do deck"""
        main_cards = self.get_main_deck_cards()
        sideboard_cards = self.get_sideboard_cards()
        
        self.main_deck_size = sum(card.quantity for card in main_cards)
        self.sideboard_size = sum(card.quantity for card in sideboard_cards)
        self.total_cards = self.main_deck_size + self.sideboard_size
        
        self.updated_at = datetime.now()
    
    def is_legal_in_format(self) -> bool:
        """Verifica se o deck é legal no formato especificado"""
        if not self.format:
            return True
        
        # Implementar regras específicas de formato
        if self.format == DeckFormat.COMMANDER:
            return self.main_deck_size == 100 and len(self.get_commander_cards()) == 1
        elif self.format in [DeckFormat.STANDARD, DeckFormat.MODERN, DeckFormat.PIONEER]:
            return 60 <= self.main_deck_size <= 100 and self.sideboard_size <= 15
        
        return True
    
    def add_tag(self, tag: str):
        """Adiciona tag ao deck"""
        if tag and tag.strip():
            self.tags.add(tag.strip().lower())
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """Remove tag do deck"""
        self.tags.discard(tag.lower())
        self.updated_at = datetime.now()


@dataclass
class ScrapingSession:
    """
    Entidade para rastrear sessões de scraping.
    """
    id: UUID = field(default_factory=uuid4)
    source: str = field(default="archidekt")
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = field(default=None)
    status: ScrapingStatus = field(default=ScrapingStatus.PENDING)
    pages_scraped: int = field(default=0)
    decks_found: int = field(default=0)
    decks_saved: int = field(default=0)
    cards_found: int = field(default=0)
    cards_saved: int = field(default=0)
    errors: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    def start(self):
        """Inicia a sessão"""
        self.status = ScrapingStatus.RUNNING
        self.start_time = datetime.now()
    
    def mark_completed(self):
        """Marca sessão como concluída"""
        self.status = ScrapingStatus.COMPLETED
        self.end_time = datetime.now()
    
    def mark_failed(self, error_message: str):
        """Marca sessão como falha"""
        self.status = ScrapingStatus.FAILED
        self.end_time = datetime.now()
        self.errors.append(error_message)
    
    def add_error(self, error_message: str):
        """Adiciona erro à sessão"""
        self.errors.append(error_message)
        logging.getLogger(__name__).error(f"Scraping error: {error_message}")
    
    def get_duration_seconds(self) -> Optional[float]:
        """Retorna duração da sessão em segundos"""
        if not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    def update_progress(self, pages_scraped: int, decks_found: int, cards_found: int):
        """Atualiza progresso da sessão"""
        self.pages_scraped = pages_scraped
        self.decks_found = decks_found
        self.cards_found = cards_found