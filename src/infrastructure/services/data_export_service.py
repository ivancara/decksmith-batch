"""
Infrastructure Layer - Exportação de Dados Real
Implementação com PyArrow para Parquet, CSV e outros formatos
"""

import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import csv

from ...domain.interfaces import IDataExportService

logger = logging.getLogger(__name__)


class ParquetDataExportService(IDataExportService):
    """Serviço de exportação usando PyArrow e Pandas"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.compression_methods = {
            'snappy': 'snappy',
            'gzip': 'gzip', 
            'brotli': 'brotli',
            'lz4': 'lz4',
            'none': None
        }
    
    async def export_to_parquet(
        self, 
        data: List[Dict[str, Any]], 
        output_path: str,
        compression: str = "snappy"
    ) -> str:
        """Exporta dados para formato Parquet com otimizações"""
        try:
            logger.info(f"Iniciando exportação Parquet: {len(data)} registros para {output_path}")
            
            if not data:
                raise ValueError("Nenhum dado fornecido para exportação")
            
            # Criar diretório se não existir
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar dados para Pandas
            df = self._prepare_dataframe(data)
            
            # Configurar compressão
            compression_method = self.compression_methods.get(compression.lower(), 'snappy')
            
            # Configurações de escrita otimizadas
            write_options = {
                'compression': compression_method,
                'use_dictionary': True,  # Compressão de strings repetidas
                'row_group_size': 50000,  # Tamanho otimizado dos grupos
                'data_page_size': 1024 * 1024,  # 1MB por página
                'write_statistics': True,  # Estatísticas para filtragem
                'use_deprecated_int96_timestamps': False
            }
            
            # Escrever arquivo Parquet
            df.to_parquet(
                output_path,
                engine='pyarrow',
                index=False,
                **write_options
            )
            
            # Verificar arquivo criado
            file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            
            # Criar metadados
            await self._create_metadata_file(output_path, {
                'format': 'parquet',
                'compression': compression,
                'records_count': len(data),
                'columns_count': len(df.columns),
                'file_size_mb': round(file_size_mb, 2),
                'created_at': datetime.now().isoformat(),
                'schema': self._get_parquet_schema_info(df)
            })
            
            logger.info(f"Exportação Parquet concluída: {output_path} ({file_size_mb:.2f} MB)")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação Parquet: {e}")
            raise
    
    async def export_to_csv(
        self, 
        data: List[Dict[str, Any]], 
        output_path: str,
        delimiter: str = ",",
        encoding: str = "utf-8"
    ) -> str:
        """Exporta dados para formato CSV"""
        try:
            logger.info(f"Iniciando exportação CSV: {len(data)} registros para {output_path}")
            
            if not data:
                raise ValueError("Nenhum dado fornecido para exportação")
            
            # Criar diretório se não existir
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar dados para Pandas
            df = self._prepare_dataframe(data)
            
            # Configurações de escrita CSV
            csv_options = {
                'sep': delimiter,
                'encoding': encoding,
                'index': False,
                'quoting': csv.QUOTE_NONNUMERIC,
                'escapechar': '\\',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
            
            # Escrever arquivo CSV
            df.to_csv(output_path, **csv_options)
            
            # Verificar arquivo criado
            file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            
            # Criar metadados
            await self._create_metadata_file(output_path, {
                'format': 'csv',
                'delimiter': delimiter,
                'encoding': encoding,
                'records_count': len(data),
                'columns_count': len(df.columns),
                'file_size_mb': round(file_size_mb, 2),
                'created_at': datetime.now().isoformat()
            })
            
            logger.info(f"Exportação CSV concluída: {output_path} ({file_size_mb:.2f} MB)")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação CSV: {e}")
            raise
    
    async def export_to_json(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        indent: int = 2,
        encoding: str = "utf-8"
    ) -> str:
        """Exporta dados para formato JSON"""
        try:
            logger.info(f"Iniciando exportação JSON: {len(data)} registros para {output_path}")
            
            if not data:
                raise ValueError("Nenhum dado fornecido para exportação")
            
            # Criar diretório se não existir
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar dados (converter tipos especiais)
            cleaned_data = self._clean_data_for_json(data)
            
            # Escrever arquivo JSON
            with open(output_path, 'w', encoding=encoding) as f:
                json.dump(cleaned_data, f, indent=indent, ensure_ascii=False, default=str)
            
            # Verificar arquivo criado
            file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            
            # Criar metadados
            await self._create_metadata_file(output_path, {
                'format': 'json',
                'indent': indent,
                'encoding': encoding,
                'records_count': len(data),
                'file_size_mb': round(file_size_mb, 2),
                'created_at': datetime.now().isoformat()
            })
            
            logger.info(f"Exportação JSON concluída: {output_path} ({file_size_mb:.2f} MB)")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na exportação JSON: {e}")
            raise
    
    def _prepare_dataframe(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepara DataFrame otimizado para exportação"""
        # Converter para DataFrame
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        # Otimizar tipos de dados
        df = self._optimize_dtypes(df)
        
        # Processar colunas especiais
        df = self._process_special_columns(df)
        
        return df
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Otimiza tipos de dados para reduzir tamanho"""
        for column in df.columns:
            col_type = df[column].dtype
            
            # Otimizar inteiros
            if pd.api.types.is_integer_dtype(col_type):
                df[column] = pd.to_numeric(df[column], downcast='integer')
            
            # Otimizar floats
            elif pd.api.types.is_float_dtype(col_type):
                df[column] = pd.to_numeric(df[column], downcast='float')
            
            # Otimizar strings/objects
            elif pd.api.types.is_object_dtype(col_type):
                # Verificar se pode ser categorical (muitos valores repetidos)
                unique_ratio = df[column].nunique() / len(df[column])
                if unique_ratio < 0.5 and df[column].nunique() < 1000:
                    df[column] = df[column].astype('category')
        
        return df
    
    def _process_special_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa colunas com tipos especiais"""
        for column in df.columns:
            # Converter listas/arrays para strings
            if column in ['colors', 'color_identity', 'tags', 'cards']:
                df[column] = df[column].apply(
                    lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x)
                )
            
            # Processar datas
            elif 'date' in column.lower() or column.endswith('_at'):
                try:
                    df[column] = pd.to_datetime(df[column], errors='coerce')
                except:
                    pass  # Manter original se conversão falhar
            
            # Processar valores monetários
            elif 'price' in column.lower() or 'cost' in column.lower():
                df[column] = pd.to_numeric(df[column], errors='coerce')
        
        return df
    
    def _clean_data_for_json(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limpa dados para serialização JSON"""
        cleaned = []
        
        for record in data:
            clean_record = {}
            for key, value in record.items():
                # Converter datetime para string
                if isinstance(value, datetime):
                    clean_record[key] = value.isoformat()
                # Converter outros tipos não serializáveis
                elif hasattr(value, '__dict__'):
                    clean_record[key] = str(value)
                else:
                    clean_record[key] = value
            
            cleaned.append(clean_record)
        
        return cleaned
    
    def _get_parquet_schema_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Obtém informações do schema Parquet"""
        schema_info = {
            'columns': {},
            'total_columns': len(df.columns),
            'total_rows': len(df)
        }
        
        for column in df.columns:
            col_info = {
                'dtype': str(df[column].dtype),
                'null_count': int(df[column].isnull().sum()),
                'null_percentage': round(df[column].isnull().mean() * 100, 2)
            }
            
            # Estatísticas específicas por tipo
            if pd.api.types.is_numeric_dtype(df[column]):
                col_info.update({
                    'min': float(df[column].min()) if not df[column].empty else None,
                    'max': float(df[column].max()) if not df[column].empty else None,
                    'mean': float(df[column].mean()) if not df[column].empty else None
                })
            elif pd.api.types.is_string_dtype(df[column]) or pd.api.types.is_object_dtype(df[column]):
                col_info.update({
                    'unique_count': int(df[column].nunique()),
                    'max_length': int(df[column].astype(str).str.len().max()) if not df[column].empty else None
                })
            
            schema_info['columns'][column] = col_info
        
        return schema_info
    
    async def _create_metadata_file(self, data_file_path: str, metadata: Dict[str, Any]):
        """Cria arquivo de metadados junto com o arquivo de dados"""
        try:
            metadata_path = data_file_path + '.metadata.json'
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"Metadados salvos: {metadata_path}")
            
        except Exception as e:
            logger.warning(f"Erro ao criar arquivo de metadados: {e}")
    
    async def validate_export(self, file_path: str) -> Dict[str, Any]:
        """Valida arquivo exportado"""
        try:
            file_info = {
                'file_path': file_path,
                'exists': Path(file_path).exists(),
                'size_bytes': 0,
                'size_mb': 0,
                'is_readable': False,
                'record_count': 0,
                'validation_errors': []
            }
            
            if not file_info['exists']:
                file_info['validation_errors'].append('Arquivo não existe')
                return file_info
            
            # Informações básicas do arquivo
            file_stats = Path(file_path).stat()
            file_info['size_bytes'] = file_stats.st_size
            file_info['size_mb'] = round(file_stats.st_size / (1024 * 1024), 2)
            
            # Validação específica por formato
            if file_path.endswith('.parquet'):
                try:
                    table = pq.read_table(file_path)
                    file_info['record_count'] = table.num_rows
                    file_info['is_readable'] = True
                except Exception as e:
                    file_info['validation_errors'].append(f'Erro ao ler Parquet: {e}')
            
            elif file_path.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path, nrows=1000)  # Ler apenas amostra
                    file_info['record_count'] = len(df)
                    file_info['is_readable'] = True
                except Exception as e:
                    file_info['validation_errors'].append(f'Erro ao ler CSV: {e}')
            
            elif file_path.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            file_info['record_count'] = len(data)
                        file_info['is_readable'] = True
                except Exception as e:
                    file_info['validation_errors'].append(f'Erro ao ler JSON: {e}')
            
            # Validações gerais
            if file_info['size_bytes'] == 0:
                file_info['validation_errors'].append('Arquivo vazio')
            
            if file_info['record_count'] == 0:
                file_info['validation_errors'].append('Nenhum registro encontrado')
            
            file_info['is_valid'] = len(file_info['validation_errors']) == 0
            
            return file_info
            
        except Exception as e:
            return {
                'file_path': file_path,
                'exists': False,
                'is_valid': False,
                'validation_errors': [f'Erro na validação: {e}']
            }
    
    async def export_data(
        self, 
        data: List[Dict[str, Any]], 
        filename: str, 
        format: str = 'parquet',
        **kwargs
    ) -> Dict[str, Any]:
        """Exporta dados arbitrários (interface genérica)"""
        try:
            start_time = datetime.now()
            
            # Configurar formato baseado no parâmetro
            if format.lower() == 'parquet':
                output_path = await self.export_to_parquet(data, filename, **kwargs)
            elif format.lower() == 'csv':
                output_path = await self.export_to_csv(data, filename, **kwargs)
            elif format.lower() == 'json':
                output_path = await self.export_to_json(data, filename, **kwargs)
            else:
                raise ValueError(f"Formato não suportado: {format}")
            
            # Calcular estatísticas
            execution_time = (datetime.now() - start_time).total_seconds()
            file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            file_size_mb = file_size / (1024 * 1024)
            
            # Calcular compressão aproximada (assumindo que JSON seria ~3x maior)
            estimated_json_size = len(str(data)) * 1.5
            compression_ratio = estimated_json_size / file_size if file_size > 0 else 1.0
            
            result = {
                'success': True,
                'file_path': output_path,
                'format': format,
                'records_exported': len(data),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size_mb, 2),
                'compression_ratio': round(compression_ratio, 2),
                'execution_time_seconds': round(execution_time, 2),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Export genérico concluído: {len(data)} registros em {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erro no export genérico: {e}")
            return {
                'success': False,
                'errors': [str(e)],
                'file_path': '',
                'records_exported': 0
            }