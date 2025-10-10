"""
DeckSmith Batch Processing - Main Entry Point
============================================

Sistema de processamento em lote para MTG card data analytics.
Implementa Clean Architecture com SOLID principles.
"""

import asyncio
import logging
import sys
from typing import Dict, Any
from datetime import datetime

from src.infrastructure.config.config_manager import EnvironmentConfigManager
from src.infrastructure.config.service_container import ServiceContainer
from src.application.use_cases.scraping_use_case import ScrapingUseCase
from src.application.use_cases.ml_training_use_case import MLTrainingUseCase
from src.application.use_cases.data_export_use_case import DataExportUseCase
from src.application.use_cases.health_check_use_case import HealthCheckUseCase
from src.application.dtos.batch_request_dto import BatchRequestDTO
from src.domain.entities.scraping_session import ScrapingSessionStatus


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/decksmith-batch.log')
    ]
)

logger = logging.getLogger(__name__)


class BatchOrchestrator:
    """
    Orquestrador principal do sistema de batch processing.
    Coordena execução de scraping, treinamento ML e exportação.
    """
    
    def __init__(self, service_container: ServiceContainer):
        self.container = service_container
        self.scraping_use_case = ScrapingUseCase(
            self.container.get_scraping_session_repository(),
            self.container.get_card_repository(),
            self.container.get_deck_repository(),
            self.container.get_web_scraper()
        )
        self.ml_training_use_case = MLTrainingUseCase(
            self.container.get_ml_model_repository(),
            self.container.get_card_repository(),
            self.container.get_deck_repository(),
            self.container.get_ml_engine()
        )
        self.data_export_use_case = DataExportUseCase(
            self.container.get_card_repository(),
            self.container.get_deck_repository(),
            self.container.get_ml_model_repository(),
            self.container.get_data_exporter()
        )
        self.health_check_use_case = HealthCheckUseCase(
            self.container.get_database_connection(),
            self.container.get_web_scraper(),
            self.container.get_ml_engine()
        )
    
    async def run_batch_job(self, request: BatchRequestDTO) -> Dict[str, Any]:
        """
        Executa job de batch processing completo.
        
        Args:
            request: Configuração do job
            
        Returns:
            Relatório de execução
        """
        logger.info(f"Iniciando batch job: {request.job_type}")
        start_time = datetime.now()
        
        try:
            # Health check inicial
            health_status = await self.health_check_use_case.execute()
            if not health_status.is_healthy:
                raise Exception(f"Sistema não está saudável: {health_status.issues}")
            
            results = {}
            
            # Execução baseada no tipo de job
            if request.job_type == "scraping":
                results["scraping"] = await self._execute_scraping(request)
            
            elif request.job_type == "ml_training":
                results["ml_training"] = await self._execute_ml_training(request)
            
            elif request.job_type == "data_export":
                results["data_export"] = await self._execute_data_export(request)
            
            elif request.job_type == "full_pipeline":
                results["scraping"] = await self._execute_scraping(request)
                results["ml_training"] = await self._execute_ml_training(request)
                results["data_export"] = await self._execute_data_export(request)
            
            else:
                raise ValueError(f"Tipo de job não suportado: {request.job_type}")
            
            # Relatório final
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            report = {
                "job_type": request.job_type,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "status": "success",
                "results": results
            }
            
            logger.info(f"Batch job finalizado com sucesso em {execution_time:.2f}s")
            return report
            
        except Exception as e:
            logger.error(f"Erro no batch job: {str(e)}")
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "job_type": request.job_type,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "status": "error",
                "error": str(e)
            }
    
    async def _execute_scraping(self, request: BatchRequestDTO) -> Dict[str, Any]:
        """Executa scraping de dados."""
        logger.info("Executando scraping...")
        
        session_id = await self.scraping_use_case.start_scraping_session(
            request.source_url or "https://ligamagic.com.br",
            request.target_pages or 10
        )
        
        progress = {"processed": 0, "total": request.target_pages or 10}
        
        # Simular progresso (em implementação real, seria baseado em callbacks)
        for i in range(progress["total"]):
            await asyncio.sleep(1)  # Simular processamento
            progress["processed"] = i + 1
            logger.info(f"Scraping progress: {progress['processed']}/{progress['total']}")
        
        await self.scraping_use_case.update_session_status(
            session_id, ScrapingSessionStatus.COMPLETED
        )
        
        return {
            "session_id": str(session_id),
            "pages_processed": progress["processed"],
            "status": "completed"
        }
    
    async def _execute_ml_training(self, request: BatchRequestDTO) -> Dict[str, Any]:
        """Executa treinamento de modelo ML."""
        logger.info("Executando treinamento ML...")
        
        model_id = await self.ml_training_use_case.start_training(
            request.model_type or "random_forest",
            request.target_metric or "win_rate"
        )
        
        # Simular treinamento
        await asyncio.sleep(5)
        
        return {
            "model_id": str(model_id),
            "model_type": request.model_type or "random_forest",
            "status": "trained"
        }
    
    async def _execute_data_export(self, request: BatchRequestDTO) -> Dict[str, Any]:
        """Executa exportação de dados."""
        logger.info("Executando exportação de dados...")
        
        export_path = await self.data_export_use_case.export_dataset(
            request.export_format or "parquet",
            request.export_path or "data/exports/"
        )
        
        return {
            "export_path": export_path,
            "format": request.export_format or "parquet",
            "status": "exported"
        }


async def main():
    """Função principal do sistema."""
    logger.info("Iniciando DeckSmith Batch Processing")
    
    try:
        # Inicializar configuração e container
        config_manager = EnvironmentConfigManager()
        service_container = ServiceContainer(config_manager)
        
        # Inicializar serviços
        await service_container.initialize()
        
        # Criar orquestrador
        orchestrator = BatchOrchestrator(service_container)
        
        # Exemplo de execução
        request = BatchRequestDTO(
            job_type="full_pipeline",
            source_url="https://ligamagic.com.br",
            target_pages=5,
            model_type="random_forest",
            target_metric="win_rate",
            export_format="parquet",
            export_path="data/exports/"
        )
        
        # Executar job
        result = await orchestrator.run_batch_job(request)
        
        logger.info("Resultado do batch job:")
        logger.info(f"Status: {result['status']}")
        logger.info(f"Tempo de execução: {result.get('execution_time_seconds', 0):.2f}s")
        
        if result['status'] == 'success':
            logger.info("✅ Batch processing executado com sucesso")
        else:
            logger.error(f"❌ Erro no batch processing: {result.get('error')}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Erro crítico: {str(e)}")
        sys.exit(1)
    
    finally:
        # Cleanup
        try:
            await service_container.cleanup()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())