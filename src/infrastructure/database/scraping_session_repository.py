"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL Scraping Session Repository Implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...domain.entities import ScrapingSession, ScrapingStatus
from ...domain.repositories import IScrapingSessionRepository
from . import BaseRepository, DatabaseConnection


class PostgreSQLScrapingSessionRepository(BaseRepository, IScrapingSessionRepository):
    """Implementação PostgreSQL do repositório de sessões de scraping"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
        self.table_name = "scraping_sessions"
    
    async def save(self, session: ScrapingSession) -> ScrapingSession:
        """Salva sessão de scraping"""
        session_data = self._entity_to_dict(session)
        session_data = self._prepare_session_data(session_data)
        
        row = await self._insert_or_update(self.table_name, session_data, "id")
        
        if row:
            self.logger.info("Scraping session saved", session_id=session.id, status=session.status)
            return self._row_to_session(row)
        
        raise Exception(f"Failed to save scraping session {session.id}")
    
    async def find_by_id(self, session_id: UUID) -> Optional[ScrapingSession]:
        """Busca sessão por ID"""
        query = "SELECT * FROM scraping_sessions WHERE id = $1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, str(session_id))
            return self._row_to_session(dict(row)) if row else None
    
    async def find_active_sessions(self) -> List[ScrapingSession]:
        """Busca sessões ativas"""
        query = """
            SELECT * FROM scraping_sessions 
            WHERE status = $1 
            ORDER BY started_at DESC
        """
        
        rows = await self.db.execute_query(query, ScrapingStatus.RUNNING.value)
        return [self._row_to_session(row) for row in rows]
    
    async def find_recent_sessions(self, limit: int = 10) -> List[ScrapingSession]:
        """Busca sessões recentes"""
        query = """
            SELECT * FROM scraping_sessions 
            ORDER BY created_at DESC 
            LIMIT $1
        """
        
        rows = await self.db.execute_query(query, limit)
        return [self._row_to_session(row) for row in rows]
    
    async def find_last_successful_session(self) -> Optional[ScrapingSession]:
        """Busca última sessão bem-sucedida"""
        query = """
            SELECT * FROM scraping_sessions 
            WHERE status = $1 
            ORDER BY completed_at DESC 
            LIMIT 1
        """
        
        rows = await self.db.execute_query(query, ScrapingStatus.COMPLETED.value)
        return self._row_to_session(rows[0]) if rows else None
    
    async def update_progress(self, 
                            session_id: UUID,
                            current_page: int,
                            decks_found: int,
                            cards_found: int) -> None:
        """Atualiza progresso da sessão"""
        query = """
            UPDATE scraping_sessions 
            SET current_page = $1,
                decks_found = $2,
                cards_found = $3,
                updated_at = NOW()
            WHERE id = $4
        """
        
        await self.db.execute_command(query, current_page, decks_found, cards_found, str(session_id))
        
        self.logger.debug("Session progress updated", 
                         session_id=session_id, 
                         page=current_page,
                         decks=decks_found)
    
    async def find_sessions_by_status(self, status: ScrapingStatus) -> List[ScrapingSession]:
        """Busca sessões por status"""
        query = "SELECT * FROM scraping_sessions WHERE status = $1 ORDER BY created_at DESC"
        
        rows = await self.db.execute_query(query, status.value)
        return [self._row_to_session(row) for row in rows]
    
    async def find_sessions_by_date_range(self, 
                                        start_date: datetime,
                                        end_date: datetime) -> List[ScrapingSession]:
        """Busca sessões por período"""
        query = """
            SELECT * FROM scraping_sessions 
            WHERE created_at BETWEEN $1 AND $2 
            ORDER BY created_at DESC
        """
        
        rows = await self.db.execute_query(query, start_date, end_date)
        return [self._row_to_session(row) for row in rows]
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas das sessões"""
        query = """
            SELECT 
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
                SUM(decks_found) as total_decks,
                SUM(cards_found) as total_cards
            FROM scraping_sessions 
            WHERE started_at IS NOT NULL
            GROUP BY status
        """
        
        rows = await self.db.execute_query(query)
        
        stats = {}
        for row in rows:
            stats[row["status"]] = {
                "count": row["count"],
                "avg_duration_seconds": float(row["avg_duration_seconds"]) if row["avg_duration_seconds"] else 0,
                "total_decks": row["total_decks"] or 0,
                "total_cards": row["total_cards"] or 0
            }
        
        return stats
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Remove sessões antigas"""
        query = """
            DELETE FROM scraping_sessions 
            WHERE created_at < NOW() - INTERVAL '%s days'
            AND status IN ($1, $2)
        """
        
        result = await self.db.execute_command(
            query % days_old, 
            ScrapingStatus.COMPLETED.value,
            ScrapingStatus.FAILED.value
        )
        
        # Extrair número de linhas afetadas do resultado
        deleted_count = int(result.split()[-1]) if result else 0
        
        self.logger.info("Old scraping sessions cleaned up", deleted_count=deleted_count)
        return deleted_count
    
    async def get_failure_analysis(self) -> List[Dict[str, Any]]:
        """Analisa falhas das sessões"""
        query = """
            SELECT 
                error_message,
                COUNT(*) as occurrence_count,
                MAX(completed_at) as last_occurrence
            FROM scraping_sessions 
            WHERE status = $1 
            AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY occurrence_count DESC
        """
        
        return await self.db.execute_query(query, ScrapingStatus.FAILED.value)
    
    def _prepare_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados da sessão para inserção no banco"""
        # Converter enum para string
        if "status" in session_data and hasattr(session_data["status"], "value"):
            session_data["status"] = session_data["status"].value
        
        # Converter lista de logs para JSON
        if "log_entries" in session_data and isinstance(session_data["log_entries"], list):
            import json
            session_data["log_entries"] = json.dumps(session_data["log_entries"])
        
        # Garantir campos obrigatórios
        session_data.setdefault("total_pages", 0)
        session_data.setdefault("current_page", 0)
        session_data.setdefault("decks_found", 0)
        session_data.setdefault("cards_found", 0)
        session_data.setdefault("errors_count", 0)
        session_data.setdefault("delay_seconds", 1.0)
        session_data.setdefault("concurrent_workers", 4)
        
        return session_data
    
    def _row_to_session(self, row: Dict[str, Any]) -> ScrapingSession:
        """Converte row do banco para entidade ScrapingSession"""
        # Converter JSON logs de volta para lista
        log_entries = []
        if row.get("log_entries"):
            try:
                import json
                log_entries = json.loads(row["log_entries"])
            except:
                pass
        
        # Converter string status para enum
        status = ScrapingStatus.PENDING
        if row.get("status"):
            try:
                status = ScrapingStatus(row["status"])
            except ValueError:
                status = ScrapingStatus.PENDING
        
        return ScrapingSession(
            id=UUID(row["id"]),
            fonte=row.get("fonte", "ligamagic"),
            status=status,
            total_pages=row.get("total_pages", 0),
            current_page=row.get("current_page", 0),
            delay_seconds=row.get("delay_seconds", 1.0),
            concurrent_workers=row.get("concurrent_workers", 4),
            decks_found=row.get("decks_found", 0),
            decks_processed=row.get("decks_processed", 0),
            cards_found=row.get("cards_found", 0),
            cards_processed=row.get("cards_processed", 0),
            errors_count=row.get("errors_count", 0),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            estimated_completion=row.get("estimated_completion"),
            error_message=row.get("error_message"),
            log_entries=log_entries,
            created_at=row.get("created_at", datetime.now())
        )