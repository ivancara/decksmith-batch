"""
DeckSmith Batch Processing System
Infrastructure Layer - PostgreSQL ML Model Repository Implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...domain.entities import MLModel, MLModelStatus
from ...domain.repositories import IMLModelRepository
from . import BaseRepository, DatabaseConnection


class PostgreSQLMLModelRepository(BaseRepository, IMLModelRepository):
    """Implementação PostgreSQL do repositório de modelos ML"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
        self.table_name = "ml_models"
    
    async def save(self, model: MLModel) -> MLModel:
        """Salva modelo ML"""
        model_data = self._entity_to_dict(model)
        model_data = self._prepare_model_data(model_data)
        
        row = await self._insert_or_update(self.table_name, model_data, "id")
        
        if row:
            self.logger.info("ML Model saved", model_id=model.id, name=model.nome, status=model.status)
            return self._row_to_model(row)
        
        raise Exception(f"Failed to save ML model {model.id}")
    
    async def find_by_id(self, model_id: UUID) -> Optional[MLModel]:
        """Busca modelo por ID"""
        query = "SELECT * FROM ml_models WHERE id = $1"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, str(model_id))
            return self._row_to_model(dict(row)) if row else None
    
    async def find_by_name_version(self, nome: str, versao: str) -> Optional[MLModel]:
        """Busca modelo por nome e versão"""
        query = "SELECT * FROM ml_models WHERE nome = $1 AND versao = $2"
        
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, nome, versao)
            return self._row_to_model(dict(row)) if row else None
    
    async def find_active_models(self) -> List[MLModel]:
        """Busca modelos ativos"""
        query = """
            SELECT * FROM ml_models 
            WHERE is_active = true AND status = $1
            ORDER BY created_at DESC
        """
        
        rows = await self.db.execute_query(query, MLModelStatus.ACTIVE.value)
        return [self._row_to_model(row) for row in rows]
    
    async def find_latest_by_algorithm(self, algoritmo: str) -> Optional[MLModel]:
        """Busca modelo mais recente por algoritmo"""
        query = """
            SELECT * FROM ml_models 
            WHERE algoritmo = $1 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        rows = await self.db.execute_query(query, algoritmo)
        return self._row_to_model(rows[0]) if rows else None
    
    async def deactivate_all(self) -> None:
        """Desativa todos os modelos"""
        query = """
            UPDATE ml_models 
            SET is_active = false,
                updated_at = NOW()
            WHERE is_active = true
        """
        
        await self.db.execute_command(query)
        self.logger.info("All ML models deactivated")
    
    async def get_model_performance_history(self, 
                                          algoritmo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca histórico de performance dos modelos"""
        base_query = """
            SELECT 
                id, nome, versao, algoritmo, 
                accuracy, precision, recall, f1_score,
                training_duration_seconds, created_at,
                status, is_active
            FROM ml_models 
        """
        
        if algoritmo:
            query = base_query + "WHERE algoritmo = $1 ORDER BY created_at DESC"
            rows = await self.db.execute_query(query, algoritmo)
        else:
            query = base_query + "ORDER BY created_at DESC"
            rows = await self.db.execute_query(query)
        
        return rows
    
    async def find_best_model_by_algorithm(self, algoritmo: str) -> Optional[MLModel]:
        """Busca melhor modelo por algoritmo (baseado em F1-score)"""
        query = """
            SELECT * FROM ml_models 
            WHERE algoritmo = $1 
            AND status = $2
            AND f1_score IS NOT NULL
            ORDER BY f1_score DESC, accuracy DESC
            LIMIT 1
        """
        
        rows = await self.db.execute_query(query, algoritmo, MLModelStatus.COMPLETED.value)
        return self._row_to_model(rows[0]) if rows else None
    
    async def find_models_by_status(self, status: MLModelStatus) -> List[MLModel]:
        """Busca modelos por status"""
        query = "SELECT * FROM ml_models WHERE status = $1 ORDER BY created_at DESC"
        
        rows = await self.db.execute_query(query, status.value)
        return [self._row_to_model(row) for row in rows]
    
    async def get_algorithm_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Obtém estatísticas por algoritmo"""
        query = """
            SELECT 
                algoritmo,
                COUNT(*) as total_models,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_models,
                COUNT(CASE WHEN is_active = true THEN 1 END) as active_models,
                AVG(accuracy) as avg_accuracy,
                MAX(accuracy) as best_accuracy,
                AVG(f1_score) as avg_f1_score,
                MAX(f1_score) as best_f1_score,
                AVG(training_duration_seconds) as avg_training_time
            FROM ml_models 
            GROUP BY algoritmo
            ORDER BY total_models DESC
        """
        
        rows = await self.db.execute_query(query)
        
        stats = {}
        for row in rows:
            stats[row["algoritmo"]] = {
                "total_models": row["total_models"],
                "completed_models": row["completed_models"],
                "active_models": row["active_models"],
                "avg_accuracy": float(row["avg_accuracy"]) if row["avg_accuracy"] else 0,
                "best_accuracy": float(row["best_accuracy"]) if row["best_accuracy"] else 0,
                "avg_f1_score": float(row["avg_f1_score"]) if row["avg_f1_score"] else 0,
                "best_f1_score": float(row["best_f1_score"]) if row["best_f1_score"] else 0,
                "avg_training_time_hours": (float(row["avg_training_time"]) / 3600) if row["avg_training_time"] else 0
            }
        
        return stats
    
    async def cleanup_failed_models(self, days_old: int = 7) -> int:
        """Remove modelos falhados antigos"""
        query = """
            DELETE FROM ml_models 
            WHERE status = $1 
            AND created_at < NOW() - INTERVAL '%s days'
        """
        
        result = await self.db.execute_command(query % days_old, MLModelStatus.FAILED.value)
        deleted_count = int(result.split()[-1]) if result else 0
        
        self.logger.info("Failed ML models cleaned up", deleted_count=deleted_count)
        return deleted_count
    
    async def update_model_metrics(self, 
                                 model_id: UUID,
                                 accuracy: Optional[float] = None,
                                 precision: Optional[float] = None,
                                 recall: Optional[float] = None,
                                 f1_score: Optional[float] = None) -> bool:
        """Atualiza métricas de um modelo"""
        updates = []
        values = []
        param_count = 1
        
        if accuracy is not None:
            updates.append(f"accuracy = ${param_count}")
            values.append(accuracy)
            param_count += 1
        
        if precision is not None:
            updates.append(f"precision = ${param_count}")
            values.append(precision)
            param_count += 1
        
        if recall is not None:
            updates.append(f"recall = ${param_count}")
            values.append(recall)
            param_count += 1
        
        if f1_score is not None:
            updates.append(f"f1_score = ${param_count}")
            values.append(f1_score)
            param_count += 1
        
        if not updates:
            return False
        
        updates.append(f"updated_at = NOW()")
        values.append(str(model_id))
        
        query = f"""
            UPDATE ml_models 
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """
        
        await self.db.execute_command(query, *values)
        
        self.logger.info("Model metrics updated", model_id=model_id)
        return True
    
    async def set_model_active(self, model_id: UUID) -> bool:
        """Define modelo como ativo (desativa outros)"""
        async with self.db.get_transaction() as conn:
            # Primeiro desativar todos os modelos
            await conn.execute("UPDATE ml_models SET is_active = false")
            
            # Ativar o modelo específico
            result = await conn.execute(
                "UPDATE ml_models SET is_active = true, status = $1 WHERE id = $2",
                MLModelStatus.ACTIVE.value, str(model_id)
            )
            
            # Verificar se foi atualizado
            updated = int(result.split()[-1]) if result else 0
            
            if updated > 0:
                self.logger.info("Model activated", model_id=model_id)
                return True
            else:
                self.logger.warning("Failed to activate model", model_id=model_id)
                return False
    
    def _prepare_model_data(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados do modelo para inserção no banco"""
        # Converter enum para string
        if "status" in model_data and hasattr(model_data["status"], "value"):
            model_data["status"] = model_data["status"].value
        
        # Converter dicionários para JSON
        if "hiperparametros" in model_data and isinstance(model_data["hiperparametros"], dict):
            import json
            model_data["hiperparametros"] = json.dumps(model_data["hiperparametros"])
        
        if "dataset_info" in model_data and isinstance(model_data["dataset_info"], dict):
            import json
            model_data["dataset_info"] = json.dumps(model_data["dataset_info"])
        
        # Garantir campos obrigatórios
        model_data.setdefault("versao", "1.0.0")
        model_data.setdefault("algoritmo", "unknown")
        model_data.setdefault("is_active", False)
        model_data.setdefault("created_by", "batch_system")
        
        return model_data
    
    def _row_to_model(self, row: Dict[str, Any]) -> MLModel:
        """Converte row do banco para entidade MLModel"""
        # Converter JSON de volta para dicts
        hiperparametros = {}
        dataset_info = {}
        
        if row.get("hiperparametros"):
            try:
                import json
                hiperparametros = json.loads(row["hiperparametros"])
            except:
                pass
        
        if row.get("dataset_info"):
            try:
                import json
                dataset_info = json.loads(row["dataset_info"])
            except:
                pass
        
        # Converter string status para enum
        status = MLModelStatus.TRAINING
        if row.get("status"):
            try:
                status = MLModelStatus(row["status"])
            except ValueError:
                status = MLModelStatus.TRAINING
        
        return MLModel(
            id=UUID(row["id"]),
            nome=row.get("nome", ""),
            versao=row.get("versao", "1.0.0"),
            algoritmo=row.get("algoritmo", "unknown"),
            status=status,
            hiperparametros=hiperparametros,
            dataset_info=dataset_info,
            accuracy=row.get("accuracy"),
            precision=row.get("precision"),
            recall=row.get("recall"),
            f1_score=row.get("f1_score"),
            loss=row.get("loss"),
            model_file_path=row.get("model_file_path"),
            preprocessor_path=row.get("preprocessor_path"),
            metadata_path=row.get("metadata_path"),
            training_started_at=row.get("training_started_at"),
            training_completed_at=row.get("training_completed_at"),
            training_duration_seconds=row.get("training_duration_seconds"),
            created_by=row.get("created_by", "batch_system"),
            is_active=row.get("is_active", False),
            created_at=row.get("created_at", datetime.now())
        )