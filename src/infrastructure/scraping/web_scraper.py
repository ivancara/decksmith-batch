"""
DeckSmith Batch Processing System
Infrastructure Layer - Web Scraper Implementation
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import random
import json
from bs4 import BeautifulSoup
import time

from ...application.interfaces import IWebScraper
from ...application.dto import ScrapingRequestDTO, ScrapingResultDTO
from ...domain.entities import Card, Deck
from ..config import EnvironmentConfigManager


class LigaMagicWebScraper(IWebScraper):
    """Web scraper para Liga Magic com proteção anti-detecção"""
    
    def __init__(self, config_manager: EnvironmentConfigManager):
        self.config = config_manager
        self.scraping_config = config_manager.get_scraping_config()
        self.security_config = config_manager.get_security_config()
        
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.last_request_time = 0.0
        self.request_count = 0
        self.session_start_time = time.time()
        
        # Headers pool for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
    
    async def initialize(self) -> bool:
        """Inicializa sessão de scraping"""
        try:
            connector = aiohttp.TCPConnector(
                limit=self.scraping_config["concurrent_workers"],
                limit_per_host=2,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.scraping_config["timeout"],
                connect=10,
                sock_read=30
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_base_headers()
            )
            
            self.logger.info("Web scraper initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize web scraper: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Finaliza sessão de scraping"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            self.logger.info("Web scraper cleaned up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup web scraper: {e}")
            return False
    
    async def scrape_page(self, request: ScrapingRequestDTO) -> ScrapingResultDTO:
        """Scraping de uma página específica"""
        if not self.session:
            await self.initialize()
        
        try:
            # Rate limiting
            await self._apply_rate_limit()
            
            # Preparar headers
            headers = self._get_request_headers()
            
            # Fazer requisição
            async with self.session.get(request.url, headers=headers) as response:
                # Verificar status
                if response.status != 200:
                    return ScrapingResultDTO(
                        url=request.url,
                        success=False,
                        error_message=f"HTTP {response.status}: {response.reason}",
                        scraping_timestamp=datetime.utcnow()
                    )
                
                # Obter conteúdo
                content = await response.text()
                
                # Parse específico baseado no tipo
                if request.page_type == "deck":
                    return await self._parse_deck_page(request.url, content)
                elif request.page_type == "card":
                    return await self._parse_card_page(request.url, content)
                elif request.page_type == "metagame":
                    return await self._parse_metagame_page(request.url, content)
                else:
                    return await self._parse_generic_page(request.url, content)
                    
        except asyncio.TimeoutError:
            return ScrapingResultDTO(
                url=request.url,
                success=False,
                error_message="Request timeout",
                scraping_timestamp=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error(f"Error scraping {request.url}: {e}")
            return ScrapingResultDTO(
                url=request.url,
                success=False,
                error_message=str(e),
                scraping_timestamp=datetime.utcnow()
            )
    
    async def scrape_batch(self, requests: List[ScrapingRequestDTO]) -> List[ScrapingResultDTO]:
        """Scraping em lote com controle de concorrência"""
        if not requests:
            return []
        
        # Agrupar por batches para não sobrecarregar
        batch_size = min(self.scraping_config["concurrent_workers"], len(requests))
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # Executar batch
            batch_tasks = [self.scrape_page(request) for request in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Processar resultados
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch scraping error: {result}")
                    results.append(ScrapingResultDTO(
                        url="unknown",
                        success=False,
                        error_message=str(result),
                        scraping_timestamp=datetime.utcnow()
                    ))
                else:
                    results.append(result)
            
            # Delay entre batches
            if i + batch_size < len(requests):
                delay = random.uniform(2.0, 5.0)
                await asyncio.sleep(delay)
        
        return results
    
    async def discover_deck_urls(self, format_filter: Optional[str] = None, 
                                limit: Optional[int] = None) -> List[str]:
        """Descobre URLs de decks para scraping"""
        urls = []
        
        try:
            # URL base para listas de decks
            base_url = urljoin(self.scraping_config["base_url"], "/decks/")
            
            # Parâmetros de busca
            params = {
                "ordem": "data",
                "sentido": "desc"
            }
            
            if format_filter:
                params["formato"] = format_filter
            
            # Headers
            headers = self._get_request_headers()
            
            # Fazer requisição
            async with self.session.get(base_url, params=params, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Encontrar links de decks
                    deck_links = soup.find_all('a', href=True)
                    
                    for link in deck_links:
                        href = link.get('href', '')
                        if '/deck/' in href or '/decks/' in href:
                            full_url = urljoin(self.scraping_config["base_url"], href)
                            if full_url not in urls:
                                urls.append(full_url)
                                
                                if limit and len(urls) >= limit:
                                    break
            
            self.logger.info(f"Discovered {len(urls)} deck URLs")
            return urls
            
        except Exception as e:
            self.logger.error(f"Error discovering deck URLs: {e}")
            return []
    
    async def _parse_deck_page(self, url: str, content: str) -> ScrapingResultDTO:
        """Parse página de deck"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair dados do deck
            deck_data = {
                "nome": self._extract_deck_name(soup),
                "formato": self._extract_deck_format(soup),
                "arquetipo": self._extract_deck_archetype(soup),
                "jogador": self._extract_player_name(soup),
                "data_torneio": self._extract_tournament_date(soup),
                "cartas": self._extract_deck_cards(soup),
                "sideboard": self._extract_sideboard_cards(soup)
            }
            
            # Validar dados essenciais
            if not deck_data["nome"] or not deck_data["cartas"]:
                return ScrapingResultDTO(
                    url=url,
                    success=False,
                    error_message="Essential deck data missing",
                    scraping_timestamp=datetime.utcnow()
                )
            
            return ScrapingResultDTO(
                url=url,
                success=True,
                data=deck_data,
                scraping_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ScrapingResultDTO(
                url=url,
                success=False,
                error_message=f"Deck parse error: {e}",
                scraping_timestamp=datetime.utcnow()
            )
    
    async def _parse_card_page(self, url: str, content: str) -> ScrapingResultDTO:
        """Parse página de carta"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair dados da carta
            card_data = {
                "nome": self._extract_card_name(soup),
                "custo_mana": self._extract_mana_cost(soup),
                "tipo": self._extract_card_type(soup),
                "poder": self._extract_power(soup),
                "resistencia": self._extract_toughness(soup),
                "texto": self._extract_card_text(soup),
                "raridade": self._extract_rarity(soup),
                "edicao": self._extract_set(soup),
                "numero_colecao": self._extract_collector_number(soup)
            }
            
            return ScrapingResultDTO(
                url=url,
                success=True,
                data=card_data,
                scraping_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ScrapingResultDTO(
                url=url,
                success=False,
                error_message=f"Card parse error: {e}",
                scraping_timestamp=datetime.utcnow()
            )
    
    async def _parse_metagame_page(self, url: str, content: str) -> ScrapingResultDTO:
        """Parse página de metagame"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair estatísticas de metagame
            metagame_data = {
                "formato": self._extract_format_from_url(url),
                "periodo": self._extract_time_period(soup),
                "arquetipos": self._extract_archetype_stats(soup),
                "cartas_populares": self._extract_popular_cards(soup),
                "meta_share": self._extract_meta_share(soup)
            }
            
            return ScrapingResultDTO(
                url=url,
                success=True,
                data=metagame_data,
                scraping_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ScrapingResultDTO(
                url=url,
                success=False,
                error_message=f"Metagame parse error: {e}",
                scraping_timestamp=datetime.utcnow()
            )
    
    async def _parse_generic_page(self, url: str, content: str) -> ScrapingResultDTO:
        """Parse genérico para páginas não específicas"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extrair dados básicos
            generic_data = {
                "title": soup.title.string if soup.title else "",
                "content_length": len(content),
                "links_found": len(soup.find_all('a', href=True)),
                "text_content": soup.get_text()[:1000]  # Primeiros 1000 chars
            }
            
            return ScrapingResultDTO(
                url=url,
                success=True,
                data=generic_data,
                scraping_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ScrapingResultDTO(
                url=url,
                success=False,
                error_message=f"Generic parse error: {e}",
                scraping_timestamp=datetime.utcnow()
            )
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Headers base para todas as requisições"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
    
    def _get_request_headers(self) -> Dict[str, str]:
        """Headers específicos para cada requisição"""
        headers = self._get_base_headers()
        
        if self.scraping_config["rotate_headers"]:
            headers["User-Agent"] = random.choice(self.user_agents)
        else:
            headers["User-Agent"] = self.scraping_config["user_agent"]
        
        return headers
    
    async def _apply_rate_limit(self):
        """Aplica rate limiting"""
        current_time = time.time()
        
        # Rate limiting básico
        time_since_last = current_time - self.last_request_time
        min_delay = self.scraping_config["default_delay"]
        
        if time_since_last < min_delay:
            delay = min_delay - time_since_last
            await asyncio.sleep(delay)
        
        # Rate limiting por sessão
        self.request_count += 1
        session_duration = current_time - self.session_start_time
        
        if (self.request_count > self.scraping_config["max_pages_per_session"] or 
            session_duration > 3600):  # 1 hora
            # Pausar para "rotacionar sessão"
            await asyncio.sleep(random.uniform(30, 60))
            self.request_count = 0
            self.session_start_time = current_time
        
        self.last_request_time = current_time
    
    # Métodos de extração específicos para Liga Magic
    def _extract_deck_name(self, soup: BeautifulSoup) -> str:
        """Extrai nome do deck"""
        selectors = [
            'h1.deck-title',
            'h1',
            '.deck-name',
            '[data-deck-name]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return "Deck Desconhecido"
    
    def _extract_deck_format(self, soup: BeautifulSoup) -> str:
        """Extrai formato do deck"""
        selectors = [
            '.format',
            '.deck-format',
            '[data-format]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True).lower()
                if any(fmt in text for fmt in ['standard', 'modern', 'legacy', 'commander', 'pioneer']):
                    return text.title()
        
        return "Standard"  # Default
    
    def _extract_deck_archetype(self, soup: BeautifulSoup) -> str:
        """Extrai arquétipo do deck"""
        selectors = [
            '.archetype',
            '.deck-archetype', 
            '[data-archetype]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return "Indefinido"
    
    def _extract_player_name(self, soup: BeautifulSoup) -> str:
        """Extrai nome do jogador"""
        selectors = [
            '.player-name',
            '.author',
            '[data-player]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return "Jogador Desconhecido"
    
    def _extract_tournament_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extrai data do torneio"""
        selectors = [
            '.tournament-date',
            '.date',
            '[data-date]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                # Tentar parsear diferentes formatos de data
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(date_text, fmt)
                    except ValueError:
                        continue
        
        return datetime.utcnow()  # Default para agora
    
    def _extract_deck_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai cartas do deck principal"""
        cards = []
        
        # Tentar diferentes seletores
        card_lists = soup.select('.deck-list, .mainboard, .main-deck')
        
        if not card_lists:
            card_lists = [soup]  # Usar página inteira como fallback
        
        for card_list in card_lists:
            card_items = card_list.select('.card-item, .card, .deck-card')
            
            for item in card_items:
                try:
                    # Extrair quantidade e nome
                    quantity_elem = item.select_one('.quantity, .qty, .card-qty')
                    name_elem = item.select_one('.card-name, .name')
                    
                    if quantity_elem and name_elem:
                        quantity = int(quantity_elem.get_text(strip=True))
                        name = name_elem.get_text(strip=True)
                        
                        cards.append({
                            "nome": name,
                            "quantidade": quantity,
                            "categoria": "main"
                        })
                        
                except (ValueError, AttributeError):
                    continue
        
        return cards
    
    def _extract_sideboard_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai cartas do sideboard"""
        cards = []
        
        sideboard_section = soup.select_one('.sideboard, .side-deck, .side')
        
        if sideboard_section:
            card_items = sideboard_section.select('.card-item, .card, .deck-card')
            
            for item in card_items:
                try:
                    quantity_elem = item.select_one('.quantity, .qty, .card-qty')
                    name_elem = item.select_one('.card-name, .name')
                    
                    if quantity_elem and name_elem:
                        quantity = int(quantity_elem.get_text(strip=True))
                        name = name_elem.get_text(strip=True)
                        
                        cards.append({
                            "nome": name,
                            "quantidade": quantity,
                            "categoria": "sideboard"
                        })
                        
                except (ValueError, AttributeError):
                    continue
        
        return cards
    
    def _extract_card_name(self, soup: BeautifulSoup) -> str:
        """Extrai nome da carta"""
        selectors = [
            'h1.card-title',
            'h1',
            '.card-name',
            '[data-card-name]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return "Carta Desconhecida"
    
    def _extract_mana_cost(self, soup: BeautifulSoup) -> str:
        """Extrai custo de mana"""
        selectors = [
            '.mana-cost',
            '.cost',
            '[data-cost]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return ""
    
    def _extract_card_type(self, soup: BeautifulSoup) -> str:
        """Extrai tipo da carta"""
        selectors = [
            '.card-type',
            '.type',
            '[data-type]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "Desconhecido"
    
    def _extract_power(self, soup: BeautifulSoup) -> Optional[int]:
        """Extrai poder da criatura"""
        selectors = [
            '.power',
            '.pt .power',
            '[data-power]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                try:
                    return int(element.get_text(strip=True))
                except ValueError:
                    pass
        
        return None
    
    def _extract_toughness(self, soup: BeautifulSoup) -> Optional[int]:
        """Extrai resistência da criatura"""
        selectors = [
            '.toughness',
            '.pt .toughness',
            '[data-toughness]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                try:
                    return int(element.get_text(strip=True))
                except ValueError:
                    pass
        
        return None
    
    def _extract_card_text(self, soup: BeautifulSoup) -> str:
        """Extrai texto da carta"""
        selectors = [
            '.card-text',
            '.text',
            '.oracle-text',
            '[data-text]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return ""
    
    def _extract_rarity(self, soup: BeautifulSoup) -> str:
        """Extrai raridade"""
        selectors = [
            '.rarity',
            '[data-rarity]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "Comum"
    
    def _extract_set(self, soup: BeautifulSoup) -> str:
        """Extrai edição/set"""
        selectors = [
            '.set',
            '.edition',
            '[data-set]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "Desconhecido"
    
    def _extract_collector_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai número de colecionador"""
        selectors = [
            '.collector-number',
            '.number',
            '[data-number]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _extract_format_from_url(self, url: str) -> str:
        """Extrai formato da URL"""
        url_lower = url.lower()
        
        formats = {
            'standard': 'Standard',
            'modern': 'Modern', 
            'legacy': 'Legacy',
            'commander': 'Commander',
            'pioneer': 'Pioneer',
            'pauper': 'Pauper'
        }
        
        for fmt_key, fmt_name in formats.items():
            if fmt_key in url_lower:
                return fmt_name
        
        return "Standard"
    
    def _extract_time_period(self, soup: BeautifulSoup) -> str:
        """Extrai período temporal do metagame"""
        selectors = [
            '.time-period',
            '.date-range',
            '[data-period]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "Últimos 30 dias"
    
    def _extract_archetype_stats(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai estatísticas de arquetipos"""
        stats = []
        
        archetype_rows = soup.select('.archetype-row, .meta-row, .deck-stats')
        
        for row in archetype_rows:
            try:
                name_elem = row.select_one('.archetype-name, .name')
                percentage_elem = row.select_one('.percentage, .meta-share')
                
                if name_elem and percentage_elem:
                    name = name_elem.get_text(strip=True)
                    percentage_text = percentage_elem.get_text(strip=True)
                    
                    # Extrair porcentagem
                    import re
                    percentage_match = re.search(r'(\d+\.?\d*)%?', percentage_text)
                    percentage = float(percentage_match.group(1)) if percentage_match else 0.0
                    
                    stats.append({
                        "nome": name,
                        "meta_share": percentage,
                        "categoria": "arquetipo"
                    })
                    
            except (ValueError, AttributeError):
                continue
        
        return stats
    
    def _extract_popular_cards(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai cartas populares"""
        cards = []
        
        card_rows = soup.select('.popular-card, .card-stats')
        
        for row in card_rows:
            try:
                name_elem = row.select_one('.card-name, .name')
                usage_elem = row.select_one('.usage, .percentage')
                
                if name_elem and usage_elem:
                    name = name_elem.get_text(strip=True)
                    usage_text = usage_elem.get_text(strip=True)
                    
                    # Extrair porcentagem de uso
                    import re
                    usage_match = re.search(r'(\d+\.?\d*)%?', usage_text)
                    usage = float(usage_match.group(1)) if usage_match else 0.0
                    
                    cards.append({
                        "nome": name,
                        "usage_percentage": usage,
                        "categoria": "popular"
                    })
                    
            except (ValueError, AttributeError):
                continue
        
        return cards
    
    def _extract_meta_share(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extrai distribuição do meta"""
        meta_share = {}
        
        # Implementação básica - pode ser expandida
        total_percentage = 0.0
        archetype_stats = self._extract_archetype_stats(soup)
        
        for stat in archetype_stats:
            meta_share[stat["nome"]] = stat["meta_share"]
            total_percentage += stat["meta_share"]
        
        # Adicionar "Outros" se não somar 100%
        if total_percentage < 100.0:
            meta_share["Outros"] = 100.0 - total_percentage
        
        return meta_share