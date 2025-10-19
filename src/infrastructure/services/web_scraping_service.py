"""
Infrastructure Layer - Web Scraping Real
Implementação de scraping para Liga Magic e outras fontes
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import random
import re
from urllib.parse import urljoin, urlparse
import json

from ...domain.interfaces import IDeckLoadingService, BatchResult

logger = logging.getLogger(__name__)


class LigaMagicScraper:
    """Scraper especializado para Liga Magic"""
    
    def __init__(self, base_url: str = "https://ligamagic.com.br"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers rotativos para evitar detecção
        self.headers_pool = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-br',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            },
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30, connect=10),
            connector=aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_random_headers(self) -> Dict[str, str]:
        """Retorna headers aleatórios"""
        return random.choice(self.headers_pool).copy()
    
    async def _smart_delay(self):
        """Delay inteligente para evitar rate limiting"""
        delay = random.uniform(1.0, 3.0)  # Entre 1-3 segundos
        await asyncio.sleep(delay)
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Faz requisição para uma página com retry e tratamento de erros"""
        if not self.session:
            raise RuntimeError("Session não inicializada. Use async with.")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = self._get_random_headers()
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text(encoding='utf-8')
                        logger.debug(f"Página carregada com sucesso: {url}")
                        return content
                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt  # Backoff exponencial
                        logger.warning(f"Rate limit detectado. Aguardando {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 404:
                        logger.warning(f"Página não encontrada: {url}")
                        return None
                    else:
                        logger.warning(f"Status HTTP {response.status} para {url}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Erro de cliente na tentativa {attempt + 1}: {e}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout na tentativa {attempt + 1} para {url}")
            except Exception as e:
                logger.error(f"Erro inesperado na tentativa {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                await self._smart_delay()
        
        logger.error(f"Falha ao carregar página após {max_retries} tentativas: {url}")
        return None
    
    async def search_decks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Busca decks no Liga Magic"""
        decks = []
        
        try:
            # URL de busca de decks (ajustar conforme estrutura real do site)
            search_url = f"{self.base_url}/deck/busca/"
            
            # Buscar página de listagem
            content = await self._fetch_page(search_url)
            if not content:
                return decks
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair links de decks (ajustar seletores conforme estrutura real)
            deck_links = self._extract_deck_links(soup)
            
            logger.info(f"Encontrados {len(deck_links)} links de decks")
            
            # Processar cada deck (limitado)
            processed = 0
            for deck_url in deck_links[:limit]:
                if processed >= limit:
                    break
                
                try:
                    deck_data = await self.scrape_single_deck(deck_url)
                    if deck_data:
                        decks.append(deck_data)
                        processed += 1
                        logger.debug(f"Deck processado: {deck_data.get('name', 'Sem nome')} ({processed}/{limit})")
                    
                    # Delay entre requisições
                    await self._smart_delay()
                    
                except Exception as e:
                    logger.error(f"Erro ao processar deck {deck_url}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Erro na busca de decks: {e}")
        
        return decks
    
    def _extract_deck_links(self, soup: BeautifulSoup) -> List[str]:
        """Extrai links de decks da página de busca"""
        links = []
        
        # Buscar links que parecem ser de decks (ajustar conforme estrutura real)
        # Exemplos de padrões comuns:
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/deck/' in href and '/view/' in href:
                full_url = urljoin(self.base_url, href)
                links.append(full_url)
        
        # Remover duplicatas
        return list(set(links))
    
    async def scrape_single_deck(self, deck_url: str) -> Optional[Dict[str, Any]]:
        """Scrape um deck específico"""
        try:
            content = await self._fetch_page(deck_url)
            if not content:
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair informações do deck
            deck_data = {
                'name': self._extract_deck_name(soup),
                'description': self._extract_deck_description(soup),
                'colors': self._extract_deck_colors(soup),
                'format': self._extract_deck_format(soup),
                'cards': self._extract_deck_cards(soup),
                'source_url': deck_url,
                'scraped_at': datetime.now().isoformat(),
                'source': 'liga_magic'
            }
            
            # Validar dados mínimos
            if not deck_data['name'] or not deck_data['cards']:
                logger.warning(f"Deck com dados insuficientes: {deck_url}")
                return None
            
            deck_data['card_count'] = len(deck_data['cards'])
            
            return deck_data
            
        except Exception as e:
            logger.error(f"Erro ao fazer scraping do deck {deck_url}: {e}")
            return None
    
    def _extract_deck_name(self, soup: BeautifulSoup) -> str:
        """Extrai nome do deck"""
        # Tentar diferentes seletores comuns
        selectors = [
            'h1.deck-title',
            'h1',
            '.deck-name',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                # Limpar nome se necessário
                name = re.sub(r'Liga Magic.*', '', name).strip()
                if name and len(name) > 3:
                    return name
        
        return "Deck Importado"
    
    def _extract_deck_description(self, soup: BeautifulSoup) -> str:
        """Extrai descrição do deck"""
        selectors = [
            '.deck-description',
            '.description',
            'meta[name="description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '')
                else:
                    return element.get_text(strip=True)
        
        return ""
    
    def _extract_deck_colors(self, soup: BeautifulSoup) -> List[str]:
        """Extrai cores do deck"""
        colors = []
        
        # Buscar por imagens ou classes de cores
        color_elements = soup.find_all(['img', 'span', 'div'], class_=re.compile(r'color|mana'))
        
        color_mapping = {
            'white': 'W',
            'blue': 'U', 
            'black': 'B',
            'red': 'R',
            'green': 'G',
            'branco': 'W',
            'azul': 'U',
            'preto': 'B',
            'vermelho': 'R',
            'verde': 'G'
        }
        
        for element in color_elements:
            classes = element.get('class', [])
            src = element.get('src', '') if element.name == 'img' else ''
            
            for color_name, color_code in color_mapping.items():
                if any(color_name in str(cls).lower() for cls in classes) or color_name in src.lower():
                    if color_code not in colors:
                        colors.append(color_code)
        
        return colors
    
    def _extract_deck_format(self, soup: BeautifulSoup) -> str:
        """Extrai formato do deck"""
        # Buscar por texto que mencione formato
        format_text = soup.get_text().lower()
        
        formats = {
            'commander': 'Commander',
            'standard': 'Standard',
            'modern': 'Modern',
            'legacy': 'Legacy',
            'vintage': 'Vintage',
            'pioneer': 'Pioneer',
            'pauper': 'Pauper'
        }
        
        for format_key, format_name in formats.items():
            if format_key in format_text:
                return format_name
        
        return 'Commander'  # Default
    
    def _extract_deck_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai cartas do deck"""
        cards = []
        
        # Buscar por diferentes estruturas de listas de cartas
        card_selectors = [
            '.card-list .card-item',
            '.decklist .card',
            'tr.card-row',
            '.carta'
        ]
        
        for selector in card_selectors:
            card_elements = soup.select(selector)
            if card_elements:
                for element in card_elements:
                    card = self._parse_card_element(element)
                    if card:
                        cards.append(card)
                break  # Usar apenas o primeiro seletor que funcionou
        
        return cards
    
    def _parse_card_element(self, element) -> Optional[Dict[str, Any]]:
        """Parse elemento de carta individual"""
        try:
            # Extrair quantidade (normalmente no início)
            quantity_text = element.get_text()
            quantity_match = re.search(r'^(\d+)x?\s+', quantity_text)
            quantity = int(quantity_match.group(1)) if quantity_match else 1
            
            # Extrair nome da carta
            name_element = element.find(['a', 'span'], class_=re.compile(r'card-name|name'))
            if name_element:
                name = name_element.get_text(strip=True)
            else:
                # Fallback: usar todo o texto e tentar extrair nome
                full_text = element.get_text(strip=True)
                name_match = re.search(r'^\d*x?\s*(.+)', full_text)
                name = name_match.group(1) if name_match else full_text
            
            # Limpar nome
            name = re.sub(r'\s+', ' ', name).strip()
            
            if name and len(name) > 1:
                return {
                    'name': name,
                    'quantity': quantity,
                    'is_commander': False  # Será determinado por outras regras
                }
            
        except Exception as e:
            logger.debug(f"Erro ao processar elemento de carta: {e}")
        
        return None


class WebScrapingService(IDeckLoadingService):
    """Serviço principal de scraping integrando múltiplas fontes"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.scrapers = {
            'liga_magic': LigaMagicScraper,
            # Adicionar outros scrapers aqui no futuro
        }
    
    async def load_decks(self, count: int, source: str = "liga_magic") -> BatchResult:
        """Carrega decks de uma fonte específica"""
        start_time = datetime.now()
        
        try:
            if source not in self.scrapers:
                available = list(self.scrapers.keys())
                raise ValueError(f"Fonte '{source}' não suportada. Disponíveis: {available}")
            
            scraper_class = self.scrapers[source]
            
            logger.info(f"Iniciando scraping de {count} decks da fonte {source}")
            
            async with scraper_class() as scraper:
                decks = await scraper.search_decks(limit=count)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Calcular estatísticas
            successful = len(decks)
            failed = max(0, count - successful)
            
            # Validar qualidade dos dados
            quality_errors = self._validate_deck_quality(decks)
            
            logger.info(f"Scraping concluído: {successful}/{count} decks em {execution_time:.2f}s")
            
            return BatchResult(
                operation_type="web_scraping",
                total_processed=count,
                successful=successful,
                failed=failed,
                errors=quality_errors,
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={
                    "source": source,
                    "decks_per_second": successful / execution_time if execution_time > 0 else 0,
                    "average_cards_per_deck": sum(len(d.get('cards', [])) for d in decks) / len(decks) if decks else 0,
                    "scraped_decks": decks  # Dados para processamento posterior
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Erro no scraping de {source}: {e}")
            
            return BatchResult(
                operation_type="web_scraping",
                total_processed=count,
                successful=0,
                failed=count,
                errors=[str(e)],
                execution_time_seconds=execution_time,
                output_files=[],
                metadata={"source": source, "error": str(e)}
            )
    
    def _validate_deck_quality(self, decks: List[Dict[str, Any]]) -> List[str]:
        """Valida qualidade dos dados coletados"""
        errors = []
        
        for i, deck in enumerate(decks):
            deck_id = f"deck_{i+1}"
            
            # Validar campos obrigatórios
            if not deck.get('name'):
                errors.append(f"{deck_id}: Nome do deck ausente")
            
            if not deck.get('cards'):
                errors.append(f"{deck_id}: Lista de cartas vazia")
            elif len(deck['cards']) < 10:
                errors.append(f"{deck_id}: Muito poucas cartas ({len(deck['cards'])})")
            
            # Validar qualidade das cartas
            invalid_cards = 0
            for card in deck.get('cards', []):
                if not card.get('name') or len(card['name'].strip()) < 2:
                    invalid_cards += 1
            
            if invalid_cards > 0:
                errors.append(f"{deck_id}: {invalid_cards} cartas com nomes inválidos")
        
        return errors[:10]  # Limitar a 10 erros para não poluir logs