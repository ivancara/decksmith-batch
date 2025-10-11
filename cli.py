"""
CLI Integrado com Sistema de Dependências
Versão final com todos os comandos integrados às implementações reais
"""

import click
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Imports do sistema
from src.infrastructure.config.dependency_container import get_container
from src.domain.interfaces import ModelType, ModelStatus

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIContext:
    """Contexto compartilhado do CLI"""
    
    def __init__(self):
        self.container = get_container()
        self.start_time = datetime.now()
    
    def log_operation(self, operation: str, details: Dict[str, Any]):
        """Log padronizado de operações"""
        logger.info(f"Operação: {operation} | Detalhes: {details}")


# Context global
cli_context = CLIContext()


def handle_async(func):
    """Decorator para lidar com funções async no Click"""
    def wrapper(*args, **kwargs):
        try:
            result = asyncio.run(func(*args, **kwargs))
            return result
        except Exception as e:
            click.echo(f"❌ Erro: {str(e)}", err=True)
            logger.error(f"Erro na operação: {e}", exc_info=True)
            raise click.ClickException(str(e))
    return wrapper


def format_table(data: List[Dict[str, Any]], headers: List[str]) -> str:
    """Formata dados em tabela"""
    if not data:
        return "Nenhum dado para exibir."
    
    # Calcular larguras das colunas
    widths = {}
    for header in headers:
        widths[header] = max(len(header), max(len(str(row.get(header, ''))) for row in data))
    
    # Criar linhas
    lines = []
    
    # Cabeçalho
    header_line = "│ " + " │ ".join(h.ljust(widths[h]) for h in headers) + " │"
    separator = "├" + "┼".join("─" * (widths[h] + 2) for h in headers) + "┤"
    top_border = "┌" + "┬".join("─" * (widths[h] + 2) for h in headers) + "┐"
    bottom_border = "└" + "┴".join("─" * (widths[h] + 2) for h in headers) + "┘"
    
    lines.append(top_border)
    lines.append(header_line)
    lines.append(separator)
    
    # Dados
    for row in data:
        data_line = "│ " + " │ ".join(str(row.get(h, '')).ljust(widths[h]) for h in headers) + " │"
        lines.append(data_line)
    
    lines.append(bottom_border)
    
    return "\n".join(lines)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
def cli(verbose):
    """
    🎯 DeckSmith Batch Processing System
    
    Sistema profissional de processamento em lote para Magic: The Gathering.
    Aplica Clean Architecture, SOLID e Strategy Pattern para máxima qualidade.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        click.echo("🔧 Modo verboso ativado")
    
    # Verificar saúde do sistema
    health = cli_context.container.health_check()
    if health['overall'] != 'OK':
        click.echo("⚠️  Aviso: Alguns componentes podem não estar funcionando corretamente")
        if verbose:
            for component, status in health.items():
                click.echo(f"   {component}: {status}")


@cli.command('load-decks')
@click.option('--source', '-s', default='archidekt', 
              type=click.Choice(['archidekt', 'moxfield', 'edhrec']),
              help='Fonte dos decks para carregar')
@click.option('--limit', '-l', type=int, help='Limite de decks para carregar')
@click.option('--batch-size', '-b', type=int, default=100,
              help='Tamanho do lote para processamento')
@click.option('--dry-run', is_flag=True, help='Execução de teste (não salva dados)')
@handle_async
async def load_decks(source: str, limit: Optional[int], batch_size: int, dry_run: bool):
    """
    📥 Carrega decks de uma fonte específica
    
    Executa scraping de decks e armazena no banco de dados usando
    o padrão Strategy para diferentes fontes.
    """
    click.echo(f"🚀 Iniciando carga de decks da fonte: {source.upper()}")
    
    if dry_run:
        click.echo("🧪 Modo DRY-RUN ativado - nenhum dado será salvo")
    
    # Obter command via dependency injection
    command = cli_context.container.get_command(
        'load_decks',
        source=source,
        limit=limit,
        batch_size=batch_size,
        dry_run=dry_run
    )
    
    # Executar comando
    start_time = datetime.now()
    result = await command.execute()
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Exibir resultados
    click.echo(f"\n✅ Carga concluída em {duration:.2f}s")
    click.echo(f"📊 Decks processados: {result.items_processed}")
    click.echo(f"✔️  Sucessos: {result.success_count}")
    click.echo(f"❌ Erros: {result.error_count}")
    
    if result.errors:
        click.echo("\n📝 Erros encontrados:")
        for error in result.errors[:5]:  # Mostrar apenas os primeiros 5
            click.echo(f"   • {error}")
        if len(result.errors) > 5:
            click.echo(f"   ... e mais {len(result.errors) - 5} erros")
    
    cli_context.log_operation('load_decks', {
        'source': source,
        'processed': result.items_processed,
        'success': result.success_count,
        'errors': result.error_count,
        'duration': duration
    })


@cli.command('generate-parquet')
@click.option('--output-path', '-o', type=click.Path(), 
              help='Caminho para salvar o arquivo parquet')
@click.option('--limit', '-l', type=int, help='Limite de registros para exportar')
@click.option('--format', '-f', default='parquet',
              type=click.Choice(['parquet', 'csv', 'json']),
              help='Formato de saída dos dados')
@click.option('--compression', '-c', default='snappy',
              type=click.Choice(['snappy', 'gzip', 'brotli', 'none']),
              help='Tipo de compressão para parquet')
@handle_async
async def generate_parquet(output_path: Optional[str], limit: Optional[int], 
                          format: str, compression: str):
    """
    📤 Gera arquivo de exportação dos dados
    
    Exporta dados dos decks em formato otimizado para análise,
    usando configurações personalizáveis de compressão e formato.
    """
    click.echo(f"📊 Iniciando geração de arquivo {format.upper()}")
    
    if output_path:
        click.echo(f"📁 Arquivo será salvo em: {output_path}")
    
    # Obter command via dependency injection
    command = cli_context.container.get_command(
        'generate_parquet',
        output_path=output_path,
        limit=limit,
        format=format,
        compression=compression
    )
    
    # Executar comando
    start_time = datetime.now()
    result = await command.execute()
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Exibir resultados
    click.echo(f"\n✅ Exportação concluída em {duration:.2f}s")
    click.echo(f"📊 Registros exportados: {result.items_processed}")
    click.echo(f"📁 Arquivo gerado: {result.output_file}")
    click.echo(f"💾 Tamanho: {result.file_size_mb:.2f} MB")
    
    if result.metadata:
        click.echo(f"📈 Compressão: {result.metadata.get('compression_ratio', 'N/A')}")
    
    cli_context.log_operation('generate_parquet', {
        'format': format,
        'records': result.items_processed,
        'file_size_mb': result.file_size_mb,
        'duration': duration,
        'output_file': result.output_file
    })


@cli.command('train-model')
@click.option('--type', '-t', 'model_type', required=True,
              type=click.Choice(['card_recommendation', 'win_rate_predictor', 'deck_analyzer']),
              help='Tipo de modelo para treinar')
@click.option('--epochs', '-e', type=int, default=10,
              help='Número de épocas para treinamento')
@click.option('--batch-size', '-b', type=int, default=32,
              help='Tamanho do batch para treinamento')
@click.option('--learning-rate', '-lr', type=float, default=0.001,
              help='Taxa de aprendizado')
@click.option('--validation-split', '-vs', type=float, default=0.2,
              help='Proporção dos dados para validação')
@click.option('--auto-activate', is_flag=True,
              help='Ativa automaticamente o modelo após treinamento')
@click.option('--description', '-d', type=str,
              help='Descrição do modelo')
@click.option('--tags', type=str, help='Tags separadas por vírgula')
@handle_async
async def train_model(model_type: str, epochs: int, batch_size: int, 
                     learning_rate: float, validation_split: float,
                     auto_activate: bool, description: Optional[str], 
                     tags: Optional[str]):
    """
    🤖 Treina modelo de machine learning
    
    Executa treinamento de modelos usando dados dos decks,
    com arquitetura otimizada e versionamento automático.
    """
    click.echo(f"🧠 Iniciando treinamento do modelo: {model_type.upper()}")
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
    
    # Exibir configurações
    config_table = [
        {"Parâmetro": "Épocas", "Valor": str(epochs)},
        {"Parâmetro": "Batch Size", "Valor": str(batch_size)},
        {"Parâmetro": "Learning Rate", "Valor": str(learning_rate)},
        {"Parâmetro": "Validação Split", "Valor": f"{validation_split:.1%}"},
        {"Parâmetro": "Auto-ativar", "Valor": "Sim" if auto_activate else "Não"}
    ]
    
    click.echo("\n📋 Configurações do Treinamento:")
    click.echo(format_table(config_table, ["Parâmetro", "Valor"]))
    
    # Obter command via dependency injection
    command = cli_context.container.get_command(
        'train_model',
        model_type=model_type,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        validation_split=validation_split,
        auto_activate=auto_activate,
        description=description,
        tags=tag_list
    )
    
    # Executar comando
    start_time = datetime.now()
    click.echo(f"\n🚀 Iniciando treinamento às {start_time.strftime('%H:%M:%S')}")
    
    result = await command.execute()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Exibir resultados
    click.echo(f"\n✅ Treinamento concluído em {duration:.2f}s")
    
    if result.metadata:
        metadata = result.metadata
        click.echo(f"🎯 Modelo: {metadata.get('model_type', 'N/A')}")
        click.echo(f"📊 Versão: {metadata.get('model_version', 'N/A')}")
        click.echo(f"💾 Arquivo: {metadata.get('file_path', 'N/A')}")
        click.echo(f"📏 Tamanho: {metadata.get('file_size_mb', 0):.2f} MB")
        
        if 'performance_metrics' in metadata:
            metrics = metadata['performance_metrics']
            click.echo(f"\n📈 Métricas de Performance:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    click.echo(f"   {metric}: {value:.4f}")
                else:
                    click.echo(f"   {metric}: {value}")
        
        if auto_activate and metadata.get('auto_activated'):
            click.echo(f"\n✨ Modelo ativado automaticamente!")
    
    cli_context.log_operation('train_model', {
        'model_type': model_type,
        'duration': duration,
        'auto_activated': auto_activate,
        'successful': result.successful > 0
    })


@cli.command('list-models')
@click.option('--type', '-t', 'model_type',
              type=click.Choice(['all', 'card_recommendation', 'win_rate_predictor', 'deck_analyzer']),
              default='all', help='Filtrar por tipo de modelo')
@click.option('--status', '-s', 
              type=click.Choice(['all', 'active', 'trained', 'deprecated']),
              default='all', help='Filtrar por status')
@click.option('--limit', '-l', type=int, default=10, help='Número máximo de modelos')
@click.option('--verbose', '-v', is_flag=True, help='Exibir informações detalhadas')
@handle_async
async def list_models(model_type: str, status: str, limit: int, verbose: bool):
    """
    📋 Lista modelos de ML disponíveis
    
    Exibe informações sobre modelos treinados, incluindo performance,
    status e configurações de treinamento.
    """
    click.echo(f"📊 Listando modelos")
    
    if model_type != 'all':
        click.echo(f"🔍 Filtro de tipo: {model_type}")
    if status != 'all':
        click.echo(f"🔍 Filtro de status: {status}")
    
    # Obter repositório via dependency injection
    model_repo = cli_context.container.get_model_version_repository()
    
    # Buscar modelos
    if model_type == 'all':
        # Buscar todos os tipos de modelos
        from src.domain.interfaces import ModelType
        all_models = []
        for mtype in ModelType:
            models_of_type = await model_repo.get_all_versions(mtype)
            all_models.extend(models_of_type)
        models = all_models
    else:
        # Buscar tipo específico
        from src.domain.interfaces import ModelType
        try:
            mtype = ModelType(model_type)
            models = await model_repo.get_all_versions(mtype)
        except ValueError:
            click.echo(f"❌ Tipo de modelo inválido: {model_type}")
            return
    
    # Filtrar por status se necessário
    if status != 'all':
        from src.domain.interfaces import ModelStatus
        try:
            status_enum = ModelStatus(status)
            models = [m for m in models if m.status == status_enum]
        except ValueError:
            click.echo(f"❌ Status inválido: {status}")
            return
    
    # Aplicar limite
    if limit and limit > 0:
        models = models[:limit]
    
    # Ordenar por data de criação (mais recente primeiro)
    models.sort(key=lambda x: x.created_at if x.created_at else datetime.min, reverse=True)
    
    if not models:
        click.echo("\n❌ Nenhum modelo encontrado com os filtros especificados")
        return
    
    # Preparar dados para tabela
    if verbose:
        table_data = []
        for model in models:
            # Extrair métricas principais
            metrics = model.performance_metrics or {}
            main_metric = ""
            if model.model_type == ModelType.CARD_RECOMMENDATION:
                main_metric = f"Acc: {metrics.get('accuracy', 'N/A')}"
            elif model.model_type == ModelType.WIN_RATE_PREDICTOR:
                main_metric = f"MAE: {metrics.get('mae', 'N/A')}"
            
            table_data.append({
                "ID": str(model.id),
                "Nome": model.model_name[:25] + "..." if len(model.model_name) > 25 else model.model_name,
                "Tipo": model.model_type.value,
                "Versão": model.version,
                "Status": model.status.value,
                "Ativo": "✓" if model.is_active else "✗",
                "Tamanho (MB)": f"{model.file_size_bytes / (1024*1024):.1f}" if model.file_size_bytes else "N/A",
                "Métrica": main_metric,
                "Criado": model.created_at.strftime('%d/%m %H:%M') if model.created_at else "N/A"
            })
        
        headers = ["ID", "Nome", "Tipo", "Versão", "Status", "Ativo", "Tamanho (MB)", "Métrica", "Criado"]
    else:
        table_data = []
        for model in models:
            table_data.append({
                "ID": str(model.id),
                "Nome": model.model_name[:30] + "..." if len(model.model_name) > 30 else model.model_name,
                "Tipo": model.model_type.value,
                "Status": model.status.value,
                "Ativo": "✓" if model.is_active else "✗",
                "Criado": model.created_at.strftime('%d/%m/%y') if model.created_at else "N/A"
            })
        
        headers = ["ID", "Nome", "Tipo", "Status", "Ativo", "Criado"]
    
    click.echo(f"\n📋 Encontrados {len(models)} modelos:")
    click.echo(format_table(table_data, headers))
    
    # Estatísticas adicionais
    if verbose:
        stats = {
            'total': len(models),
            'active': sum(1 for m in models if m.is_active),
            'types': len(set(m.model_type for m in models))
        }
        
        click.echo(f"\n📊 Estatísticas:")
        click.echo(f"   Total: {stats['total']} modelos")
        click.echo(f"   Ativos: {stats['active']} modelos")
        click.echo(f"   Tipos diferentes: {stats['types']}")


@cli.command('activate-model')
@click.argument('model_type', type=click.Choice(['card_recommendation', 'win_rate_predictor', 'deck_analyzer']))
@click.argument('version')
@click.option('--force', is_flag=True, help='Força ativação mesmo se houver avisos')
@handle_async
async def activate_model(model_type: str, version: str, force: bool):
    """
    ✨ Ativa uma versão específica de modelo
    
    Define qual versão do modelo será usada em produção,
    desativando automaticamente a versão anterior.
    """
    click.echo(f"🔄 Ativando modelo {model_type} versão {version}")
    
    # Obter repositório via dependency injection
    model_repo = cli_context.container.get_model_version_repository()
    
    # Verificar se modelo existe
    model = await model_repo.get_model_by_version(ModelType(model_type), version)
    if not model:
        click.echo(f"❌ Modelo {model_type} versão {version} não encontrado")
        return
    
    # Verificar se já está ativo
    if model.is_active:
        click.echo(f"ℹ️  Modelo {model_type} versão {version} já está ativo")
        return
    
    # Verificar status
    if model.status == ModelStatus.DEPRECATED and not force:
        click.echo(f"⚠️  Atenção: Modelo está marcado como DEPRECATED")
        click.echo("   Use --force para ativar mesmo assim")
        return
    
    # Exibir informações do modelo
    click.echo(f"\n📋 Informações do Modelo:")
    click.echo(f"   Nome: {model.model_name}")
    click.echo(f"   Tipo: {model.model_type.value}")
    click.echo(f"   Status atual: {model.status.value}")
    click.echo(f"   Criado em: {model.created_at.strftime('%d/%m/%Y %H:%M') if model.created_at else 'N/A'}")
    
    if model.description:
        click.echo(f"   Descrição: {model.description}")
    
    # Confirmar ativação
    if not force:
        if not click.confirm("\n🤔 Deseja ativar este modelo?"):
            click.echo("❌ Operação cancelada")
            return
    
    # Ativar modelo
    success = await model_repo.activate_model_version(ModelType(model_type), version)
    
    if success:
        click.echo(f"\n✅ Modelo {model_type} versão {version} ativado com sucesso!")
        click.echo(f"🎯 Agora é o modelo ativo para {model_type}")
        
        cli_context.log_operation('activate_model', {
            'model_type': model_type,
            'version': version,
            'model_name': model.model_name
        })
    else:
        click.echo(f"\n❌ Falha ao ativar modelo {model_type} versão {version}")


@cli.command('health-check')
def health_check():
    """
    🏥 Verifica saúde do sistema
    
    Executa diagnóstico completo dos componentes do sistema,
    incluindo dependências, configurações e conectividade.
    """
    click.echo("🏥 Executando diagnóstico do sistema...")
    
    # Health check do container
    health = cli_context.container.health_check()
    
    # Formatar resultados
    table_data = []
    for component, status in health.items():
        icon = "✅" if status == "OK" else "❌"
        table_data.append({
            "Componente": component.replace('_', ' ').title(),
            "Status": f"{icon} {status}"
        })
    
    click.echo("\n📊 Status dos Componentes:")
    click.echo(format_table(table_data, ["Componente", "Status"]))
    
    # Status geral
    overall_icon = "✅" if health['overall'] == "OK" else "❌"
    click.echo(f"\n🎯 Status Geral: {overall_icon} {health['overall']}")
    
    # Informações adicionais
    uptime = datetime.now() - cli_context.start_time
    click.echo(f"⏱️  Uptime: {uptime}")
    
    # Log da operação
    cli_context.log_operation('health_check', {
        'overall_status': health['overall'],
        'uptime_seconds': uptime.total_seconds()
    })


if __name__ == '__main__':
    cli()