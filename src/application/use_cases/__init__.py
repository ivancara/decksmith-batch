"""
DeckSmith Batch Processing System
Application Layer - Use Cases (Casos de Uso)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from ..dto import (
    ScrapingRequestDTO, ScrapingResponseDTO,
    MLTrainingRequestDTO, MLTrainingResponseDTO,
    DataExportRequestDTO, DataExportResponseDTO,
    HealthCheckRequestDTO, HealthCheckResponseDTO,
    BatchJobStatusDTO
)
from ..interfaces import (
    IWebScraper, IMLEngine, IDataExporter, INotificationService,
    IJobQueue, ICacheService, IMonitoringService
)
from ...domain.entities import ScrapingSession, MLModel, DataExportJob
from ...domain.repositories import (
    ICardRepository, IDeckRepository, IMLModelRepository,
    IScrapingSessionRepository, IBatchMetricsRepository
)
from ...domain.services import (
    DeckAnalysisService, MLDataPreparationService, 
    ModelValidationService, BatchHealthService
)


class ScrapingUseCase:
    """Caso de uso para coordenar operações de scraping"""
    
    def __init__(
        self,
        web_scraper: IWebScraper,
        card_repository: ICardRepository,
        deck_repository: IDeckRepository,
        session_repository: IScrapingSessionRepository,
        notification_service: INotificationService,
        monitoring_service: IMonitoringService,
        cache_service: ICacheService
    ):
        self.web_scraper = web_scraper
        self.card_repository = card_repository
        self.deck_repository = deck_repository
        self.session_repository = session_repository
        self.notification_service = notification_service
        self.monitoring_service = monitoring_service
        self.cache_service = cache_service
        self.deck_analysis_service = DeckAnalysisService(card_repository)
        self.logger = logging.getLogger(__name__)
    
    async def execute_scraping(self, request: ScrapingRequestDTO) -> ScrapingResponseDTO:
        """Executa processo completo de scraping"""
        timer_id = await self.monitoring_service.start_timer("scraping_session")
        
        # Criar sessão de scraping
        session = ScrapingSession.create_new(
            request_type=request.request_type.value,
            target_formats=request.target_formats or [],
            max_pages=request.max_pages,
            configuration={
                "delay_seconds": request.delay_seconds,
                "use_stealth": request.use_stealth,
                "priority": request.priority
            }
        )
        
        # Salvar sessão
        await self.session_repository.save(session)
        
        response = ScrapingResponseDTO(
            session_id=session.id,
            status="started",
            total_pages_scraped=0,
            total_decks_found=0,
            total_cards_found=0,
            start_time=session.start_time
        )
        
        try:
            # Configurar scraper
            self.web_scraper.configure_stealth_mode(request.use_stealth)
            self.web_scraper.configure_delays(
                request.delay_seconds or 1.0,
                (request.delay_seconds or 1.0) * 2
            )
            
            if request.proxy_config:
                self.web_scraper.set_proxy_config(request.proxy_config)
            
            # Executar scraping baseado no tipo
            if request.request_type.value == "full_sync":
                await self._execute_full_sync(session, request, response)
            elif request.request_type.value == "incremental":
                await self._execute_incremental_sync(session, request, response)
            elif request.request_type.value == "specific_deck":
                await self._execute_specific_deck(session, request, response)
            elif request.request_type.value == "format_sync":
                await self._execute_format_sync(session, request, response)
            
            # Finalizar sessão com sucesso
            session.complete_successfully(
                total_pages=response.total_pages_scraped,
                total_decks=response.total_decks_found,
                total_cards=response.total_cards_found
            )
            response.status = "completed"
            response.end_time = session.end_time
            response.duration_seconds = session.duration_seconds
            
        except Exception as e:
            self.logger.error(f"Erro durante scraping: {str(e)}")
            session.mark_as_failed(str(e))
            response.status = "failed"
            response.errors.append(str(e))
            
            # Enviar alerta
            await self.notification_service.send_system_alert(
                severity="error",
                message=f"Falha no scraping da sessão {session.id}",
                details={"error": str(e), "session_id": session.id}
            )
        
        finally:
            # Salvar sessão atualizada
            await self.session_repository.save(session)
            
            # Parar timer e registrar métricas
            duration = await self.monitoring_service.stop_timer(timer_id)
            await self.monitoring_service.record_metric("scraping_duration", duration)
            await self.monitoring_service.record_metric("decks_scraped", response.total_decks_found)
            
            # Notificar conclusão
            await self.notification_service.send_scraping_completed(session.id, response)
        
        return response
    
    async def _execute_full_sync(
        self, 
        session: ScrapingSession, 
        request: ScrapingRequestDTO, 
        response: ScrapingResponseDTO
    ):
        """Executa sincronização completa"""
        formats = request.target_formats or await self.web_scraper.get_available_formats()
        
        for formato in formats:
            self.logger.info(f"Iniciando scraping do formato: {formato}")
            await self._scrape_format(formato, session, request, response)
    
    async def _execute_incremental_sync(
        self,
        session: ScrapingSession,
        request: ScrapingRequestDTO,
        response: ScrapingResponseDTO
    ):
        """Executa sincronização incremental"""
        # Obter última execução bem-sucedida
        last_session = await self.session_repository.find_last_successful_session()
        
        if not last_session:
            self.logger.warning("Nenhuma sessão anterior encontrada, executando sync completo")
            await self._execute_full_sync(session, request, response)
            return
        
        # Determinar o que atualizar baseado no tempo
        formats = request.target_formats or await self.web_scraper.get_available_formats()
        
        for formato in formats:
            # Scraping limitado baseado na última execução
            max_pages = min(request.max_pages or 10, 10)  # Limitar incremental
            await self._scrape_format(formato, session, request, response, max_pages)
    
    async def _execute_specific_deck(
        self,
        session: ScrapingSession,
        request: ScrapingRequestDTO,
        response: ScrapingResponseDTO
    ):
        """Executa scraping de deck específico"""
        if not request.specific_deck_id:
            raise ValueError("specific_deck_id é obrigatório para scraping específico")
        
        deck_data = await self.web_scraper.scrape_deck_details(request.specific_deck_id)
        
        if deck_data:
            deck_entity = await self._process_deck_data(deck_data)
            if deck_entity:
                response.total_decks_found = 1
                response.total_cards_found = deck_entity.total_cartas
    
    async def _execute_format_sync(
        self,
        session: ScrapingSession,
        request: ScrapingRequestDTO,
        response: ScrapingResponseDTO
    ):
        """Executa sincronização por formato específico"""
        if not request.target_formats:
            raise ValueError("target_formats é obrigatório para format_sync")
        
        for formato in request.target_formats:
            await self._scrape_format(formato, session, request, response)
    
    async def _scrape_format(
        self,
        formato: str,
        session: ScrapingSession,
        request: ScrapingRequestDTO,
        response: ScrapingResponseDTO,
        max_pages: Optional[int] = None
    ):
        """Scraping de um formato específico"""
        max_pages = max_pages or request.max_pages
        page_count = 0
        
        deck_iterator = await self.web_scraper.scrape_deck_list(formato, max_pages)
        async for deck_info in deck_iterator:
            page_count += 1
            response.total_pages_scraped = page_count
            
            # Processar deck
            deck_url = deck_info.get("url")
            if deck_url:
                deck_data = await self.web_scraper.scrape_deck_details(deck_url)
                if deck_data:
                    deck_entity = await self._process_deck_data(deck_data)
                    if deck_entity:
                        response.total_decks_found += 1
                        response.total_cards_found += deck_entity.total_cartas
            
            # Atualizar progresso
            await self.monitoring_service.increment_counter("pages_scraped")
    
    async def _process_deck_data(self, deck_data) -> Optional[Any]:
        """Processa dados de um deck"""
        try:
            # Verificar se deck já existe
            existing_deck = await self.deck_repository.find_by_name_and_format(
                deck_data.nome, deck_data.formato
            )
            
            if existing_deck:
                # Atualizar deck existente se necessário
                self.logger.debug(f"Deck já existe: {deck_data.nome}")
                return existing_deck
            
            # Processar cartas do deck
            processed_cards = []
            for card_info in deck_data.cartas:
                card = await self._process_card_data(card_info)
                if card:
                    processed_cards.append(card)
            
            # Criar entidade de deck
            from ...domain.entities import Deck
            deck = Deck.create_from_scraping(
                nome=deck_data.nome,
                formato=deck_data.formato,
                cartas_data=processed_cards,
                comandante=deck_data.comandante,
                source_url=deck_data.source_url
            )
            
            # Analisar deck
            analysis = await self.deck_analysis_service.analyze_deck_synergies(deck)
            deck.add_analysis_data(analysis)
            
            # Salvar deck
            await self.deck_repository.save(deck)
            
            return deck
            
        except Exception as e:
            self.logger.error(f"Erro ao processar deck {deck_data.nome}: {str(e)}")
            return None
    
    async def _process_card_data(self, card_info) -> Optional[Any]:
        """Processa dados de uma carta"""
        try:
            # Verificar se carta já existe
            existing_card = await self.card_repository.find_by_name(card_info.get("name"))
            
            if existing_card:
                return existing_card
            
            # Buscar detalhes da carta se necessário
            card_details = await self.web_scraper.scrape_card_details(card_info.get("name"))
            
            if card_details:
                # Criar entidade de carta
                from ...domain.entities import Card
                card = Card.create_from_scraping(
                    nome=card_details.nome,
                    custo_mana=card_details.custo_mana,
                    tipo=card_details.tipo,
                    texto=card_details.texto,
                    cores=card_details.cores,
                    raridade=card_details.raridade
                )
                
                # Salvar carta
                await self.card_repository.save(card)
                
                return card
            
        except Exception as e:
            self.logger.error(f"Erro ao processar carta {card_info.get('name')}: {str(e)}")
        
        return None


class MLTrainingUseCase:
    """Caso de uso para treinamento de modelos ML"""
    
    def __init__(
        self,
        ml_engine: IMLEngine,
        model_repository: IMLModelRepository,
        deck_repository: IDeckRepository,
        card_repository: ICardRepository,
        notification_service: INotificationService,
        monitoring_service: IMonitoringService
    ):
        self.ml_engine = ml_engine
        self.model_repository = model_repository
        self.deck_repository = deck_repository
        self.card_repository = card_repository
        self.notification_service = notification_service
        self.monitoring_service = monitoring_service
        self.data_preparation_service = MLDataPreparationService(deck_repository, card_repository)
        self.validation_service = ModelValidationService(model_repository)
        self.logger = logging.getLogger(__name__)
    
    async def execute_training(self, request: MLTrainingRequestDTO) -> MLTrainingResponseDTO:
        """Executa treinamento completo de modelo ML"""
        timer_id = await self.monitoring_service.start_timer("ml_training")
        
        # Criar modelo
        model = MLModel.create_new(
            algorithm=request.algorithm,
            hyperparameters=request.hyperparameters,
            target_formats=request.target_formats
        )
        
        response = MLTrainingResponseDTO(
            model_id=str(model.id),
            algorithm=request.algorithm,
            status="started"
        )
        
        try:
            # Preparar dataset
            self.logger.info("Preparando dataset para treinamento")
            dataset = await self.data_preparation_service.prepare_deck_dataset(
                formatos=request.target_formats
            )
            
            if len(dataset) < 100:  # Mínimo de amostras
                raise ValueError(f"Dataset muito pequeno: {len(dataset)} amostras")
            
            response.total_samples = len(dataset)
            
            # Dividir dataset
            train_size = int(len(dataset) * request.training_size)
            training_data = dataset[:train_size]
            validation_data = dataset[train_size:]
            
            response.training_samples = len(training_data)
            response.validation_samples = len(validation_data)
            
            # Preparar features
            from ..dto import MLFeatureVectorDTO
            feature_vectors = [
                MLFeatureVectorDTO(
                    deck_id=data["deck_id"],
                    numeric_features=data,
                    target=data.get("competitive_score", 0)
                )
                for data in training_data
            ]
            
            # Treinar modelo
            self.logger.info("Iniciando treinamento do modelo")
            model.start_training()
            await self.model_repository.save(model)
            
            training_result = await self.ml_engine.train_model(
                algorithm=request.algorithm,
                features=feature_vectors,
                hyperparameters=request.hyperparameters
            )
            
            # Atualizar modelo com resultados
            model.complete_training(
                accuracy=training_result.accuracy,
                precision=training_result.precision,
                recall=training_result.recall,
                f1_score=training_result.f1_score
            )
            
            # Validar modelo
            validation_result = await self.validation_service.validate_model_performance(model)
            
            if validation_result["is_valid"]:
                model.mark_as_production_ready()
                response.is_production_ready = True
            else:
                response.validation_errors = validation_result["issues"]
                response.deployment_recommendations = validation_result["recommendations"]
            
            # Atualizar response
            response.status = "completed"
            response.accuracy = model.accuracy
            response.precision = model.precision
            response.recall = model.recall
            response.f1_score = model.f1_score
            response.training_duration_seconds = model.training_duration_seconds
            
        except Exception as e:
            self.logger.error(f"Erro durante treinamento: {str(e)}")
            model.mark_as_failed(str(e))
            response.status = "failed"
            
            await self.notification_service.send_system_alert(
                severity="error",
                message=f"Falha no treinamento do modelo {model.id}",
                details={"error": str(e), "model_id": model.id}
            )
        
        finally:
            # Salvar modelo
            await self.model_repository.save(model)
            
            # Registrar métricas
            duration = await self.monitoring_service.stop_timer(timer_id)
            await self.monitoring_service.record_metric("training_duration", duration)
            
            if response.accuracy:
                await self.monitoring_service.record_metric("model_accuracy", response.accuracy)
            
            # Notificar conclusão
            await self.notification_service.send_training_completed(str(model.id), response)
        
        return response


class DataExportUseCase:
    """Caso de uso para exportação de dados"""
    
    def __init__(
        self,
        data_exporter: IDataExporter,
        export_repository: Any,  # Repository para jobs de export
        notification_service: INotificationService,
        monitoring_service: IMonitoringService
    ):
        self.data_exporter = data_exporter
        self.export_repository = export_repository
        self.notification_service = notification_service
        self.monitoring_service = monitoring_service
        self.logger = logging.getLogger(__name__)
    
    async def execute_export(self, request: DataExportRequestDTO) -> DataExportResponseDTO:
        """Executa exportação de dados"""
        timer_id = await self.monitoring_service.start_timer("data_export")
        
        # Criar job de exportação
        export_job = DataExportJob.create_new(
            export_type=request.export_type.value,
            export_format=request.export_format.value,
            destination_path=request.destination_path,
            filters=request.format_specific_config
        )
        
        try:
            # Validar caminho
            if not await self.data_exporter.validate_export_path(request.destination_path):
                raise ValueError(f"Caminho inválido: {request.destination_path}")
            
            # Executar exportação baseada no tipo
            if request.export_type.value == "cards_only":
                result = await self.data_exporter.export_cards(
                    request.export_format.value,
                    request.destination_path,
                    filters=request.format_specific_config
                )
            elif request.export_type.value == "decks_only":
                result = await self.data_exporter.export_decks(
                    request.export_format.value,
                    request.destination_path,
                    filters=request.format_specific_config
                )
            elif request.export_type.value == "ml_features":
                result = await self.data_exporter.export_ml_features(
                    request.export_format.value,
                    request.destination_path
                )
            else:  # full_dataset
                result = await self.data_exporter.export_full_dataset(
                    request.export_format.value,
                    request.destination_path,
                    include_metadata=request.include_metadata
                )
            
            # Atualizar job
            export_job.complete_successfully(
                file_size_mb=result.file_size_mb,
                total_records=result.total_records
            )
            
            # Notificar conclusão
            await self.notification_service.send_export_completed(str(export_job.id), result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante exportação: {str(e)}")
            export_job.mark_as_failed(str(e))
            
            response = DataExportResponseDTO(
                export_id=str(export_job.id),
                status="failed",
                file_path=request.destination_path,
                errors=[str(e)]
            )
            
            return response
        
        finally:
            # Salvar job
            if hasattr(self.export_repository, 'save'):
                await self.export_repository.save(export_job)
            
            # Registrar métricas
            duration = await self.monitoring_service.stop_timer(timer_id)
            await self.monitoring_service.record_metric("export_duration", duration)


class HealthCheckUseCase:
    """Caso de uso para verificação de saúde do sistema"""
    
    def __init__(
        self,
        metrics_repository: IBatchMetricsRepository,
        monitoring_service: IMonitoringService
    ):
        self.metrics_repository = metrics_repository
        self.monitoring_service = monitoring_service
        self.health_service = BatchHealthService(metrics_repository)
        self.logger = logging.getLogger(__name__)
    
    async def execute_health_check(self, request: HealthCheckRequestDTO) -> HealthCheckResponseDTO:
        """Executa verificação completa de saúde"""
        # Obter status do sistema
        health_status = await self.health_service.check_system_health()
        
        # Obter métricas adicionais se solicitado
        system_metrics = {}
        if request.include_metrics:
            system_metrics = await self.monitoring_service.get_system_health()
        
        response = HealthCheckResponseDTO(
            overall_status=health_status["overall_status"],
            check_timestamp=datetime.now(),
            component_health=health_status["components"],
            system_metrics=system_metrics
        )
        
        # Adicionar alertas se houver problemas
        for component, status in health_status["components"].items():
            if status["status"] != "healthy":
                response.active_alerts.append({
                    "component": component,
                    "severity": status["status"],
                    "issues": status["issues"]
                })
        
        # Gerar recomendações se solicitado
        if request.include_recommendations:
            response.recommendations = health_status.get("recommendations", [])
        
        return response