"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Batch Metrics Repository Implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from ...domain.repositories import IBatchMetricsRepository
from . import BaseRepository, DatabaseConnection


class PostgreSQLBatchMetricsRepository(BaseRepository, IBatchMetricsRepository):
    """Implementação PostgreSQL do repositório de métricas batch"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
    
    async def record_scraping_metrics(self, session_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de scraping"""
        await self._record_metric("scraping", str(session_id), metrics)
    
    async def record_ml_training_metrics(self, model_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de treinamento ML"""
        await self._record_metric("ml_training", str(model_id), metrics)
    
    async def record_export_metrics(self, job_id: UUID, metrics: Dict[str, Any]) -> None:
        """Registra métricas de exportação"""
        await self._record_metric("export", str(job_id), metrics)
    
    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """Obtém métricas de saúde do sistema"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        
        # Métricas de scraping
        scraping_metrics = await self._get_scraping_metrics(last_24h, now)
        
        # Métricas de ML
        ml_metrics = await self._get_ml_metrics(last_week, now)
        
        # Métricas de exportação
        export_metrics = await self._get_export_metrics(last_week, now)
        
        # Métricas de sistema
        system_metrics = await self._get_system_metrics()
        
        return {
            "timestamp": now,
            "scraping": scraping_metrics,
            "ml": ml_metrics,
            "export": export_metrics,
            "system": system_metrics
        }
    
    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Busca tendências de performance"""
        start_time = datetime.now() - timedelta(days=days)
        
        # Tendências de scraping
        scraping_trends = await self._get_scraping_trends(start_time)
        
        # Tendências de ML
        ml_trends = await self._get_ml_trends(start_time)
        
        # Tendências de exportação
        export_trends = await self._get_export_trends(start_time)
        
        return {
            "period_days": days,
            "start_date": start_time,
            "scraping": scraping_trends,
            "ml": ml_trends,
            "export": export_trends
        }
    
    async def _record_metric(self, metric_type: str, entity_id: str, metrics: Dict[str, Any]) -> None:
        """Registra métrica genérica"""
        import json
        
        # Simples implementação usando log - pode ser expandida com tabela específica
        self.logger.info("Metric recorded", 
                        metric_type=metric_type, 
                        entity_id=entity_id, 
                        metrics=metrics)
    
    async def _get_scraping_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Obtém métricas de scraping"""
        # Última execução
        last_session_query = """
            SELECT * FROM scraping_sessions 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        try:
            last_session_rows = await self.db.execute_query(last_session_query)
            last_run = last_session_rows[0]["completed_at"] if last_session_rows else None
        except Exception:
            last_run = None
        
        # Taxa de sucesso nas últimas 24h
        success_rate_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful
            FROM scraping_sessions 
            WHERE created_at BETWEEN $1 AND $2
        """
        
        try:
            success_rows = await self.db.execute_query(success_rate_query, start_time, end_time)
            success_data = success_rows[0] if success_rows else {"total": 0, "successful": 0}
        except Exception:
            success_data = {"total": 0, "successful": 0}
        
        success_rate = 0
        if success_data["total"] > 0:
            success_rate = success_data["successful"] / success_data["total"]
        
        return {
            "last_run": last_run,
            "success_rate": success_rate,
            "total_sessions_24h": success_data["total"],
            "successful_sessions_24h": success_data["successful"]
        }
    
    async def _get_ml_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Obtém métricas de ML"""
        try:
            # Modelos ativos
            active_models_query = "SELECT COUNT(*) as count FROM ml_models WHERE is_active = true"
            active_rows = await self.db.execute_query(active_models_query)
            active_models = active_rows[0]["count"] if active_rows else 0
            
            # Último treinamento
            last_training_query = """
                SELECT training_completed_at 
                FROM ml_models 
                WHERE training_completed_at IS NOT NULL
                ORDER BY training_completed_at DESC 
                LIMIT 1
            """
            
            training_rows = await self.db.execute_query(last_training_query)
            last_training = training_rows[0]["training_completed_at"] if training_rows else None
            
        except Exception:
            active_models = 0
            last_training = None
        
        return {
            "active_models": active_models,
            "last_training": last_training
        }
    
    async def _get_export_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Obtém métricas de exportação"""
        # Placeholder - implementar quando tabela de export jobs existir
        return {
            "last_export": None,
            "failed_jobs": 0,
            "total_jobs_week": 0,
            "successful_jobs_week": 0
        }
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Obtém métricas gerais do sistema"""
        try:
            # Contadores básicos
            cards_count_query = "SELECT COUNT(*) as count FROM cartas"
            decks_count_query = "SELECT COUNT(*) as count FROM decks"
            
            cards_rows = await self.db.execute_query(cards_count_query)
            decks_rows = await self.db.execute_query(decks_count_query)
            
            total_cards = cards_rows[0]["count"] if cards_rows else 0
            total_decks = decks_rows[0]["count"] if decks_rows else 0
            
            # Saúde do banco de dados
            db_health = await self.db.health_check()
            
        except Exception:
            total_cards = 0
            total_decks = 0
            db_health = False
        
        return {
            "total_cards": total_cards,
            "total_decks": total_decks,
            "database_healthy": db_health,
            "timestamp": datetime.now()
        }
    
    async def _get_scraping_trends(self, start_time: datetime) -> Dict[str, Any]:
        """Obtém tendências de scraping"""
        try:
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as sessions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    COALESCE(SUM(decks_found), 0) as total_decks
                FROM scraping_sessions
                WHERE created_at >= $1
                GROUP BY DATE(created_at)
                ORDER BY date
            """
            
            rows = await self.db.execute_query(query, start_time)
            
            return {
                "daily_stats": rows,
                "total_sessions": sum(row["sessions"] for row in rows),
                "total_successful": sum(row["successful"] for row in rows),
                "total_decks_scraped": sum(row["total_decks"] or 0 for row in rows)
            }
        except Exception:
            return {
                "daily_stats": [],
                "total_sessions": 0,
                "total_successful": 0,
                "total_decks_scraped": 0
            }
    
    async def _get_ml_trends(self, start_time: datetime) -> Dict[str, Any]:
        """Obtém tendências de ML"""
        try:
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as models_created,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    AVG(accuracy) as avg_accuracy
                FROM ml_models
                WHERE created_at >= $1
                GROUP BY DATE(created_at)
                ORDER BY date
            """
            
            rows = await self.db.execute_query(query, start_time)
            
            return {
                "daily_stats": rows,
                "total_models": sum(row["models_created"] for row in rows),
                "successful_models": sum(row["successful"] for row in rows)
            }
        except Exception:
            return {
                "daily_stats": [],
                "total_models": 0,
                "successful_models": 0
            }
    
    async def _get_export_trends(self, start_time: datetime) -> Dict[str, Any]:
        """Obtém tendências de exportação"""
        # Placeholder - implementar quando necessário
        return {
            "daily_stats": [],
            "total_exports": 0,
            "successful_exports": 0
        }