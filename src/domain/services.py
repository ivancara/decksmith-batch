"""
DeckSmith Batch Processing System
Domain Layer - Domain Services
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .entities import (
    Card, Deck, ScrapingSession, MLModel, DataExportJob,
    ScrapingStatus, MLModelStatus
)
from .repositories import (
    ICardRepository, IDeckRepository, IMLModelRepository,
    IScrapingSessionRepository, IBatchMetricsRepository
)


class DeckAnalysisService:
    """Serviço para análise de decks e extração de features"""
    
    def __init__(self, card_repository: ICardRepository):
        self.card_repository = card_repository
        self.logger = logging.getLogger(__name__)
    
    async def analyze_deck_synergies(self, deck: Deck) -> Dict[str, Any]:
        """Analisa sinergias entre cartas do deck"""
        synergies = {
            "color_synergy": self._calculate_color_synergy(deck),
            "mana_curve_quality": self._analyze_mana_curve(deck),
            "type_distribution": self._analyze_type_distribution(deck),
            "competitive_score": self._calculate_competitive_score(deck)
        }
        
        return synergies
    
    def _calculate_color_synergy(self, deck: Deck) -> float:
        """Calcula sinergia de cores (0-1)"""
        if not deck.cores:
            return 0.0
        
        # Lógica simplificada - pode ser expandida
        if len(deck.cores) <= 2:
            return 0.9  # Decks bi-color ou mono-color são mais sinérgicos
        elif len(deck.cores) == 3:
            return 0.7
        else:
            return 0.5  # Decks 4-5 cores são menos sinérgicos
    
    def _analyze_mana_curve(self, deck: Deck) -> Dict[str, Any]:
        """Analisa curva de mana do deck"""
        if not deck.curva_mana:
            return {"quality_score": 0.0, "issues": ["Curva de mana não calculada"]}
        
        # Análise da distribuição de CMC
        total_cards = sum(deck.curva_mana.values())
        if total_cards == 0:
            return {"quality_score": 0.0, "issues": ["Deck vazio"]}
        
        # Curva ideal varia por formato
        ideal_curve = self._get_ideal_curve_for_format(deck.formato)
        
        quality_score = self._compare_curves(deck.curva_mana, ideal_curve, total_cards)
        
        return {
            "quality_score": quality_score,
            "distribution": deck.curva_mana,
            "total_cards": total_cards,
            "avg_cmc": deck.custo_medio_mana
        }
    
    def _get_ideal_curve_for_format(self, formato: str) -> Dict[int, float]:
        """Retorna curva ideal por formato (porcentagens)"""
        if formato.lower() == "commander":
            return {1: 0.10, 2: 0.15, 3: 0.20, 4: 0.20, 5: 0.15, 6: 0.10, 7: 0.10}
        elif formato.lower() == "standard":
            return {1: 0.20, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10, 6: 0.05, 7: 0.05}
        else:
            # Padrão genérico
            return {1: 0.15, 2: 0.20, 3: 0.20, 4: 0.15, 5: 0.15, 6: 0.10, 7: 0.05}
    
    def _compare_curves(self, actual: Dict[int, int], ideal: Dict[int, float], total: int) -> float:
        """Compara curva atual com ideal (0-1)"""
        if total == 0:
            return 0.0
        
        score = 1.0
        for cmc, ideal_pct in ideal.items():
            actual_pct = actual.get(cmc, 0) / total
            difference = abs(actual_pct - ideal_pct)
            score -= difference * 0.5  # Penaliza diferenças
        
        return max(0.0, score)
    
    def _analyze_type_distribution(self, deck: Deck) -> Dict[str, Any]:
        """Analisa distribuição de tipos de cartas"""
        if not deck.distribuicao_tipos:
            return {"balance_score": 0.0, "issues": ["Distribuição não calculada"]}
        
        total = sum(deck.distribuicao_tipos.values())
        if total == 0:
            return {"balance_score": 0.0, "issues": ["Deck vazio"]}
        
        # Calcular porcentagens
        percentages = {
            tipo: (count / total) * 100 
            for tipo, count in deck.distribuicao_tipos.items()
        }
        
        balance_score = self._calculate_type_balance_score(percentages, deck.formato)
        
        return {
            "balance_score": balance_score,
            "distribution": percentages,
            "total_nonland": total
        }
    
    def _calculate_type_balance_score(self, percentages: Dict[str, float], formato: str) -> float:
        """Calcula score de balanceamento de tipos"""
        # Lógica simplificada - pode ser expandida com regras específicas por formato
        creature_pct = percentages.get("Creature", 0)
        spell_pct = percentages.get("Instant", 0) + percentages.get("Sorcery", 0)
        
        if formato.lower() == "commander":
            # Commander geralmente tem mais variedade
            if 20 <= creature_pct <= 40 and spell_pct >= 20:
                return 0.8
        
        return 0.5  # Score padrão
    
    def _calculate_competitive_score(self, deck: Deck) -> float:
        """Calcula score competitivo do deck (0-1)"""
        score = 0.0
        
        # Fatores que aumentam competitividade
        if deck.total_cartas >= 60:  # Tamanho mínimo
            score += 0.2
        
        if deck.custo_medio_mana <= 3.5:  # Curva baixa
            score += 0.3
        
        if len(deck.cores) <= 2:  # Consistência de cores
            score += 0.2
        
        if deck.formato.lower() in ["standard", "modern", "legacy"]:
            score += 0.3  # Formatos competitivos
        
        return min(1.0, score)


class MLDataPreparationService:
    """Serviço para preparação de dados para ML"""
    
    def __init__(self, deck_repository: IDeckRepository, card_repository: ICardRepository):
        self.deck_repository = deck_repository
        self.card_repository = card_repository
        self.logger = logging.getLogger(__name__)
    
    async def prepare_deck_dataset(self, formatos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Prepara dataset de decks para treinamento"""
        self.logger.info("Iniciando preparação do dataset de decks")
        
        # Buscar decks para treinamento
        decks = await self.deck_repository.get_all_for_ml_training(
            formatos=formatos,
            competitive_only=True,
            min_cards=60
        )
        
        dataset = []
        for deck in decks:
            # Buscar cartas do deck
            deck_data = await self.deck_repository.get_deck_with_cards(deck.id)
            if deck_data:
                features = await self._extract_deck_features(deck_data)
                dataset.append(features)
        
        self.logger.info(f"Dataset preparado com {len(dataset)} decks")
        return dataset
    
    async def _extract_deck_features(self, deck_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai features de um deck para ML"""
        cards = deck_data.get("cards", [])
        
        # Features básicas
        features = {
            "deck_id": deck_data["id"],
            "formato": deck_data["formato"],
            "total_cartas": len(cards),
            "cores": deck_data.get("cores", []),
            "commander": deck_data.get("comandante")
        }
        
        # Features de cartas
        card_features = await self._extract_card_features(cards)
        features.update(card_features)
        
        # Features de sinergia
        synergy_features = self._calculate_synergy_features(cards)
        features.update(synergy_features)
        
        return features
    
    async def _extract_card_features(self, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extrai features das cartas do deck"""
        if not cards:
            return {}
        
        total_cmc = sum(card.get("cmc", 0) for card in cards)
        avg_cmc = total_cmc / len(cards) if cards else 0
        
        # Distribuição por tipos
        type_counts = {}
        color_counts = {}
        rarity_counts = {}
        
        for card in cards:
            # Tipos
            card_type = card.get("tipo", "").lower()
            if "creature" in card_type:
                type_counts["creatures"] = type_counts.get("creatures", 0) + 1
            elif "instant" in card_type or "sorcery" in card_type:
                type_counts["spells"] = type_counts.get("spells", 0) + 1
            elif "land" in card_type:
                type_counts["lands"] = type_counts.get("lands", 0) + 1
            else:
                type_counts["others"] = type_counts.get("others", 0) + 1
            
            # Cores
            for cor in card.get("cores", []):
                color_counts[cor] = color_counts.get(cor, 0) + 1
            
            # Raridade
            rarity = card.get("raridade", "common").lower()
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        return {
            "avg_cmc": avg_cmc,
            "creature_count": type_counts.get("creatures", 0),
            "spell_count": type_counts.get("spells", 0),
            "land_count": type_counts.get("lands", 0),
            "other_count": type_counts.get("others", 0),
            "color_diversity": len(color_counts),
            "rare_count": rarity_counts.get("rare", 0) + rarity_counts.get("mythic", 0)
        }
    
    def _calculate_synergy_features(self, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula features de sinergia entre cartas"""
        # Implementação simplificada
        return {
            "tribal_synergy": self._detect_tribal_synergy(cards),
            "keyword_synergy": self._detect_keyword_synergy(cards),
            "combo_potential": self._detect_combo_potential(cards)
        }
    
    def _detect_tribal_synergy(self, cards: List[Dict[str, Any]]) -> float:
        """Detecta sinergias tribais (0-1)"""
        # Contar subtipos de criaturas
        subtypes = {}
        for card in cards:
            if "creature" in card.get("tipo", "").lower():
                # Extrair subtipos (simplificado)
                tipo = card.get("tipo", "")
                # Lógica para extrair subtipos seria implementada aqui
        
        # Retorna score baseado na concentração de tipos
        if not subtypes:
            return 0.0
        
        max_count = max(subtypes.values())
        total_creatures = sum(subtypes.values())
        
        return (max_count / total_creatures) if total_creatures > 0 else 0.0
    
    def _detect_keyword_synergy(self, cards: List[Dict[str, Any]]) -> float:
        """Detecta sinergias de palavras-chave"""
        # Implementação simplificada
        return 0.5  # Placeholder
    
    def _detect_combo_potential(self, cards: List[Dict[str, Any]]) -> float:
        """Detecta potencial de combos"""
        # Implementação simplificada
        return 0.5  # Placeholder


class ModelValidationService:
    """Serviço para validação de modelos ML"""
    
    def __init__(self, model_repository: IMLModelRepository):
        self.model_repository = model_repository
        self.logger = logging.getLogger(__name__)
    
    async def validate_model_performance(self, model: MLModel) -> Dict[str, Any]:
        """Valida performance de um modelo"""
        validation_result = {
            "is_valid": False,
            "issues": [],
            "recommendations": [],
            "quality_score": 0.0
        }
        
        # Validar métricas básicas
        if model.accuracy is None:
            validation_result["issues"].append("Accuracy não calculada")
        elif model.accuracy < 0.7:
            validation_result["issues"].append(f"Accuracy baixa: {model.accuracy:.3f}")
        
        if model.f1_score is None:
            validation_result["issues"].append("F1-score não calculado")
        elif model.f1_score < 0.7:
            validation_result["issues"].append(f"F1-score baixo: {model.f1_score:.3f}")
        
        # Comparar com modelos anteriores
        previous_models = await self.model_repository.find_latest_by_algorithm(model.algoritmo)
        if previous_models and model.accuracy and previous_models.accuracy:
            if model.accuracy < previous_models.accuracy * 0.95:  # 5% de tolerância
                validation_result["issues"].append("Performance pior que modelo anterior")
        
        # Calcular score de qualidade
        quality_score = self._calculate_quality_score(model)
        validation_result["quality_score"] = quality_score
        
        # Determinar se é válido
        validation_result["is_valid"] = (
            len(validation_result["issues"]) == 0 and 
            quality_score >= 0.7
        )
        
        # Gerar recomendações
        if not validation_result["is_valid"]:
            validation_result["recommendations"] = self._generate_recommendations(model, validation_result["issues"])
        
        return validation_result
    
    def _calculate_quality_score(self, model: MLModel) -> float:
        """Calcula score de qualidade do modelo (0-1)"""
        score = 0.0
        weights = {
            "accuracy": 0.3,
            "precision": 0.2,
            "recall": 0.2,
            "f1_score": 0.3
        }
        
        if model.accuracy:
            score += model.accuracy * weights["accuracy"]
        if model.precision:
            score += model.precision * weights["precision"]
        if model.recall:
            score += model.recall * weights["recall"]
        if model.f1_score:
            score += model.f1_score * weights["f1_score"]
        
        return score
    
    def _generate_recommendations(self, model: MLModel, issues: List[str]) -> List[str]:
        """Gera recomendações para melhorar o modelo"""
        recommendations = []
        
        if model.accuracy and model.accuracy < 0.7:
            recommendations.append("Considere aumentar o dataset de treinamento")
            recommendations.append("Experimente diferentes hiperparâmetros")
        
        if model.training_duration_seconds and model.training_duration_seconds < 300:  # 5 minutos
            recommendations.append("Treinamento muito rápido - considere mais épocas")
        
        if "F1-score baixo" in str(issues):
            recommendations.append("Verifique balanceamento das classes no dataset")
        
        return recommendations


class BatchHealthService:
    """Serviço para monitoramento de saúde do sistema batch"""
    
    def __init__(self, metrics_repository: IBatchMetricsRepository):
        self.metrics_repository = metrics_repository
        self.logger = logging.getLogger(__name__)
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Verifica saúde geral do sistema"""
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Verificar métricas do sistema
        metrics = await self.metrics_repository.get_system_health_metrics()
        
        # Verificar componentes
        health_status["components"]["scraping"] = await self._check_scraping_health(metrics)
        health_status["components"]["ml_training"] = await self._check_ml_health(metrics)
        health_status["components"]["data_export"] = await self._check_export_health(metrics)
        
        # Determinar status geral
        component_statuses = [comp["status"] for comp in health_status["components"].values()]
        if "critical" in component_statuses:
            health_status["overall_status"] = "critical"
        elif "warning" in component_statuses:
            health_status["overall_status"] = "warning"
        
        return health_status
    
    async def _check_scraping_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica saúde do sistema de scraping"""
        status = {
            "status": "healthy",
            "last_run": metrics.get("scraping", {}).get("last_run"),
            "success_rate": metrics.get("scraping", {}).get("success_rate", 0),
            "issues": []
        }
        
        # Verificar se scraping rodou recentemente
        last_run = status["last_run"]
        if last_run:
            hours_since_last = (datetime.now() - last_run).total_seconds() / 3600
            if hours_since_last > 24:
                status["status"] = "warning"
                status["issues"].append("Scraping não executado nas últimas 24h")
        
        # Verificar taxa de sucesso
        if status["success_rate"] < 0.8:
            status["status"] = "warning"
            status["issues"].append(f"Taxa de sucesso baixa: {status['success_rate']:.1%}")
        
        return status
    
    async def _check_ml_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica saúde do sistema de ML"""
        status = {
            "status": "healthy",
            "active_models": metrics.get("ml", {}).get("active_models", 0),
            "last_training": metrics.get("ml", {}).get("last_training"),
            "issues": []
        }
        
        # Verificar se há modelos ativos
        if status["active_models"] == 0:
            status["status"] = "critical"
            status["issues"].append("Nenhum modelo ativo encontrado")
        
        return status
    
    async def _check_export_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica saúde do sistema de exportação"""
        status = {
            "status": "healthy",
            "last_export": metrics.get("export", {}).get("last_export"),
            "failed_jobs": metrics.get("export", {}).get("failed_jobs", 0),
            "issues": []
        }
        
        # Verificar jobs falhados
        if status["failed_jobs"] > 0:
            status["status"] = "warning"
            status["issues"].append(f"{status['failed_jobs']} jobs de export falharam")
        
        return status