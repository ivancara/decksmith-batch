"""
DeckSmith Batch Processing System
Infrastructure Layer - Data Exporter Implementation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json

# Parquet support
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    pa = None
    pq = None

from ...application.interfaces import IDataExporter
from ...application.dto import DataExportRequestDTO, DataExportResultDTO
from ...domain.entities import Card, Deck, DataExportJob
from ..config import EnvironmentConfigManager


class ParquetDataExporter(IDataExporter):
    """Exportador de dados para formato Parquet"""
    
    def __init__(self, config_manager: EnvironmentConfigManager):
        self.config = config_manager
        self.export_config = config_manager.get_export_config()
        
        self.logger = logging.getLogger(__name__)
        
        # Diretórios
        self.output_dir = Path(self.export_config["output_directory"])
        self.temp_dir = Path(self.export_config["temp_directory"])
        
        # Criar diretórios se não existirem
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Verificar disponibilidade do Parquet
        if not PARQUET_AVAILABLE:
            self.logger.warning("PyArrow not available, Parquet export will not work")
    
    async def initialize(self) -> bool:
        """Inicializa exportador"""
        try:
            if not PARQUET_AVAILABLE:
                self.logger.error("PyArrow required for Parquet export")
                return False
            
            self.logger.info("Data exporter initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize data exporter: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Finaliza exportador"""
        try:
            # Limpar arquivos temporários se configurado
            if self.export_config.get("cleanup_temp_files", True):
                await self._cleanup_temp_files()
            
            self.logger.info("Data exporter cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup data exporter: {e}")
            return False
    
    async def export_data(self, request: DataExportRequestDTO) -> DataExportResultDTO:
        """Exporta dados para arquivo"""
        try:
            export_start = datetime.utcnow()
            
            # Preparar dados
            df = await self._prepare_dataframe(request.data, request.data_type)
            
            if df is None or df.empty:
                return DataExportResultDTO(
                    export_id=request.export_id,
                    success=False,
                    error_message="No data to export or data preparation failed",
                    export_duration=0.0,
                    export_timestamp=export_start
                )
            
            # Aplicar filtros se especificados
            if request.filters:
                df = await self._apply_filters(df, request.filters)
            
            # Gerar nome do arquivo
            filename = await self._generate_filename(request)
            output_path = self.output_dir / filename
            
            # Exportar baseado no formato
            export_format = request.format or self.export_config["default_format"]
            
            if export_format.lower() == "parquet":
                await self._export_parquet(df, output_path, request)
            elif export_format.lower() == "csv":
                await self._export_csv(df, output_path, request)
            elif export_format.lower() == "json":
                await self._export_json(df, output_path, request)
            else:
                raise ValueError(f"Export format {export_format} not supported")
            
            # Verificar exportação se configurado
            if self.export_config.get("verify_export", True):
                verification_result = await self._verify_export(output_path, df)
                if not verification_result:
                    return DataExportResultDTO(
                        export_id=request.export_id,
                        success=False,
                        error_message="Export verification failed",
                        export_duration=0.0,
                        export_timestamp=export_start
                    )
            
            # Criar backup se configurado
            if self.export_config.get("backup_exports", False):
                await self._backup_export(output_path)
            
            # Calcular métricas
            file_size = output_path.stat().st_size
            export_end = datetime.utcnow()
            export_duration = (export_end - export_start).total_seconds()
            
            # Salvar metadata
            metadata = await self._save_export_metadata(request, output_path, df, export_duration)
            
            return DataExportResultDTO(
                export_id=request.export_id,
                success=True,
                output_path=str(output_path),
                file_size=file_size,
                rows_exported=len(df),
                export_format=export_format,
                export_duration=export_duration,
                export_timestamp=export_start,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error exporting data {request.export_id}: {e}")
            export_start = datetime.utcnow()  # Initialize for error case
            export_end = datetime.utcnow()
            export_duration = (export_end - export_start).total_seconds()
            
            return DataExportResultDTO(
                export_id=request.export_id,
                success=False,
                error_message=str(e),
                export_duration=export_duration,
                export_timestamp=export_start
            )
    
    async def export_batch(self, requests: List[DataExportRequestDTO]) -> List[DataExportResultDTO]:
        """Exporta múltiplos conjuntos de dados"""
        results = []
        
        for request in requests:
            result = await self.export_data(request)
            results.append(result)
            
            # Delay entre exportações para não sobrecarregar
            if len(requests) > 1:
                await asyncio.sleep(0.1)
        
        return results
    
    async def get_export_status(self, export_id: str) -> Dict[str, Any]:
        """Obtém status de exportação"""
        try:
            # Procurar arquivo de metadata
            metadata_files = list(self.output_dir.glob(f"*{export_id}*.metadata.json"))
            
            if not metadata_files:
                return {"status": "not_found", "export_id": export_id}
            
            # Ler metadata mais recente
            latest_metadata = max(metadata_files, key=lambda p: p.stat().st_mtime)
            
            with open(latest_metadata, 'r') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting export status for {export_id}: {e}")
            return {"status": "error", "error": str(e), "export_id": export_id}
    
    async def cleanup_old_exports(self, max_age_days: Optional[int] = None) -> int:
        """Remove exportações antigas"""
        retention_days = max_age_days or self.export_config.get("retention_days", 30)
        cutoff_date = datetime.utcnow().timestamp() - (retention_days * 24 * 3600)
        
        removed_count = 0
        
        try:
            for file_path in self.output_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            self.logger.info(f"Cleaned up {removed_count} old export files")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old exports: {e}")
            return 0
    
    async def _prepare_dataframe(self, data: List[Dict[str, Any]], data_type: str) -> Optional[pd.DataFrame]:
        """Prepara DataFrame para exportação"""
        try:
            if not data:
                return None
            
            # Converter para DataFrame
            df = pd.DataFrame(data)
            
            # Processamento específico por tipo
            if data_type == "cards":
                df = await self._process_cards_dataframe(df)
            elif data_type == "decks":
                df = await self._process_decks_dataframe(df)
            elif data_type == "scraping_sessions":
                df = await self._process_sessions_dataframe(df)
            elif data_type == "ml_models":
                df = await self._process_models_dataframe(df)
            
            # Limpeza geral
            df = await self._clean_dataframe(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error preparing dataframe: {e}")
            return None
    
    async def _process_cards_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa DataFrame de cartas"""
        # Conversões de tipo
        if 'poder' in df.columns:
            df['poder'] = pd.to_numeric(df['poder'], errors='coerce')
        
        if 'resistencia' in df.columns:
            df['resistencia'] = pd.to_numeric(df['resistencia'], errors='coerce')
        
        if 'cmc' in df.columns:
            df['cmc'] = pd.to_numeric(df['cmc'], errors='coerce')
        
        # Tratar campos de data
        date_columns = ['data_criacao', 'data_atualizacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    async def _process_decks_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa DataFrame de decks"""
        # Conversões de tipo
        if 'total_cartas' in df.columns:
            df['total_cartas'] = pd.to_numeric(df['total_cartas'], errors='coerce')
        
        if 'sideboard_size' in df.columns:
            df['sideboard_size'] = pd.to_numeric(df['sideboard_size'], errors='coerce')
        
        # Tratar campos de data
        date_columns = ['data_criacao', 'data_torneio', 'data_atualizacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    async def _process_sessions_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa DataFrame de sessões de scraping"""
        # Conversões de tipo
        numeric_columns = ['total_pages', 'successful_pages', 'failed_pages', 'duration_seconds']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Tratar campos de data
        date_columns = ['start_time', 'end_time', 'data_criacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    async def _process_models_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa DataFrame de modelos ML"""
        # Conversões de tipo
        if 'training_duration' in df.columns:
            df['training_duration'] = pd.to_numeric(df['training_duration'], errors='coerce')
        
        # Tratar campos de data
        date_columns = ['training_timestamp', 'data_criacao']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    async def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpeza geral do DataFrame"""
        # Remover colunas completamente vazias
        df = df.dropna(axis=1, how='all')
        
        # Converter colunas de texto para string
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).replace('nan', '')
        
        # Ordenar por data de criação se disponível
        if 'data_criacao' in df.columns:
            df = df.sort_values('data_criacao', ascending=False)
        
        return df
    
    async def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Aplica filtros ao DataFrame"""
        try:
            for column, filter_value in filters.items():
                if column not in df.columns:
                    continue
                
                if isinstance(filter_value, dict):
                    # Filtro complexo
                    if 'min' in filter_value:
                        df = df[df[column] >= filter_value['min']]
                    if 'max' in filter_value:
                        df = df[df[column] <= filter_value['max']]
                    if 'in' in filter_value:
                        df = df[df[column].isin(filter_value['in'])]
                    if 'not_in' in filter_value:
                        df = df[~df[column].isin(filter_value['not_in'])]
                else:
                    # Filtro simples
                    df = df[df[column] == filter_value]
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Error applying filters: {e}")
            return df
    
    async def _generate_filename(self, request: DataExportRequestDTO) -> str:
        """Gera nome do arquivo de exportação"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_format = request.format or self.export_config["default_format"]
        
        # Nome base
        base_name = f"{request.data_type}_{request.export_id}_{timestamp}"
        
        # Adicionar filtros ao nome se especificados
        if request.filters:
            filter_suffix = "_".join([f"{k}{v}" for k, v in request.filters.items() if isinstance(v, (str, int, float))])
            if filter_suffix:
                base_name += f"_{filter_suffix}"
        
        return f"{base_name}.{export_format.lower()}"
    
    async def _export_parquet(self, df: pd.DataFrame, output_path: Path, request: DataExportRequestDTO):
        """Exporta para formato Parquet"""
        if not PARQUET_AVAILABLE:
            raise ValueError("PyArrow not available for Parquet export")
        
        # Configurações do Parquet
        compression = self.export_config.get("compression", "snappy")
        
        # Verificar se precisa particionar
        partition_by = self.export_config.get("partition_by")
        
        if partition_by and partition_by in df.columns and len(df[partition_by].unique()) > 1:
            # Exportação particionada
            if pa is not None and pq is not None:
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(
                    table,
                    root_path=str(output_path.parent / output_path.stem),
                    partition_cols=[partition_by],
                    compression=compression
                )
            else:
                raise ValueError("PyArrow not available for partitioned export")
        else:
            # Exportação simples
            df.to_parquet(
                output_path,
                compression=compression,
                index=False
            )
    
    async def _export_csv(self, df: pd.DataFrame, output_path: Path, request: DataExportRequestDTO):
        """Exporta para formato CSV"""
        df.to_csv(
            output_path,
            index=False,
            encoding='utf-8'
        )
    
    async def _export_json(self, df: pd.DataFrame, output_path: Path, request: DataExportRequestDTO):
        """Exporta para formato JSON"""
        # Converter DataFrame para dicionários
        data = df.to_dict('records')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    async def _verify_export(self, output_path: Path, original_df: pd.DataFrame) -> bool:
        """Verifica se exportação foi bem-sucedida"""
        try:
            if not output_path.exists():
                return False
            
            # Verificar se arquivo não está vazio
            if output_path.stat().st_size == 0:
                return False
            
            # Verificação específica por formato
            if output_path.suffix.lower() == '.parquet':
                # Ler arquivo Parquet e verificar número de linhas
                df_read = pd.read_parquet(output_path)
                return len(df_read) == len(original_df)
            
            elif output_path.suffix.lower() == '.csv':
                # Ler arquivo CSV e verificar número de linhas
                df_read = pd.read_csv(output_path)
                return len(df_read) == len(original_df)
            
            elif output_path.suffix.lower() == '.json':
                # Verificar se JSON é válido
                with open(output_path, 'r') as f:
                    data = json.load(f)
                return len(data) == len(original_df)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying export: {e}")
            return False
    
    async def _backup_export(self, output_path: Path):
        """Cria backup da exportação"""
        try:
            backup_dir = self.output_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / output_path.name
            
            import shutil
            shutil.copy2(output_path, backup_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to backup export: {e}")
    
    async def _save_export_metadata(self, request: DataExportRequestDTO, output_path: Path, 
                                   df: pd.DataFrame, export_duration: float) -> Dict[str, Any]:
        """Salva metadata da exportação"""
        metadata = {
            "export_id": request.export_id,
            "data_type": request.data_type,
            "export_format": request.format or self.export_config["default_format"],
            "output_path": str(output_path),
            "file_size": output_path.stat().st_size,
            "rows_exported": len(df),
            "columns_exported": len(df.columns),
            "column_names": list(df.columns),
            "export_duration": export_duration,
            "export_timestamp": datetime.utcnow().isoformat(),
            "filters_applied": request.filters or {},
            "compression": self.export_config.get("compression"),
            "partitioned": self.export_config.get("partition_by") is not None
        }
        
        # Adicionar metadata do DataFrame
        if self.export_config.get("include_metadata", True):
            metadata["dataframe_info"] = {
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_usage": df.memory_usage(deep=True).sum(),
                "null_counts": df.isnull().sum().to_dict()
            }
        
        # Salvar arquivo de metadata
        metadata_path = output_path.parent / f"{output_path.stem}.metadata.json"
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return metadata
    
    async def _cleanup_temp_files(self):
        """Limpa arquivos temporários"""
        try:
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
                elif temp_file.is_dir():
                    import shutil
                    shutil.rmtree(temp_file)
            
            self.logger.info("Temporary files cleaned up")
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp files: {e}")
    
    def get_supported_formats(self) -> List[str]:
        """Retorna formatos suportados"""
        formats = ["csv", "json"]
        if PARQUET_AVAILABLE:
            formats.append("parquet")
        return formats
    
    async def get_export_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de exportações"""
        try:
            export_files = list(self.output_dir.glob("*"))
            export_files = [f for f in export_files if f.is_file() and not f.name.endswith('.metadata.json')]
            
            total_size = sum(f.stat().st_size for f in export_files)
            
            # Agrupar por formato
            format_stats = {}
            for file_path in export_files:
                ext = file_path.suffix.lower().lstrip('.')
                if ext not in format_stats:
                    format_stats[ext] = {"count": 0, "total_size": 0}
                
                format_stats[ext]["count"] += 1
                format_stats[ext]["total_size"] += file_path.stat().st_size
            
            return {
                "total_exports": len(export_files),
                "total_size_bytes": total_size,
                "format_breakdown": format_stats,
                "output_directory": str(self.output_dir),
                "available_space": self._get_available_space()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting export statistics: {e}")
            return {}
    
    def _get_available_space(self) -> Optional[int]:
        """Obtém espaço disponível em disco"""
        try:
            import shutil
            return shutil.disk_usage(self.output_dir).free
        except:
            return None