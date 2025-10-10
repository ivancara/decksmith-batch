# DeckSmith Batch Processing System

## Visão Geral

Sistema completo de processamento em lote para coleta, análise e processamento de dados de Magic: The Gathering com arquitetura limpa e padrões SOLID.

## Arquitetura

### Clean Architecture - 4 Camadas

```
src/
├── domain/              # Camada de Domínio
├── application/         # Camada de Aplicação  
├── infrastructure/      # Camada de Infraestrutura
└── presentation/        # Camada de Apresentação (futura)
```

## Camadas Implementadas

### 🎯 Domain Layer (Entidades de Negócio)

**Localização:** `src/domain/entities/`

- **Card**: Entidade de carta MTG com métodos de negócio
- **Deck**: Entidade de deck com análise de composição
- **ScrapingSession**: Gestão de sessões de scraping
- **MLModel**: Modelos de Machine Learning
- **DataExportJob**: Jobs de exportação de dados

**Interfaces de Repositório:** `src/domain/repositories/`
- ICardRepository, IDeckRepository, IScrapingSessionRepository, etc.

### 🔧 Application Layer (Casos de Uso)

**DTOs:** `src/application/dto/`
- ScrapingRequestDTO/ResultDTO
- MLTrainingRequestDTO/ResultDTO  
- DataExportRequestDTO/ResultDTO
- BatchJobStatusDTO

**Use Cases:** `src/application/use_cases/`
- ScrapingUseCase
- MLTrainingUseCase
- DataExportUseCase
- HealthCheckUseCase

**Interfaces:** `src/application/interfaces/`
- IWebScraper, IMLEngine, IDataExporter, IConfigManager

### 🏗️ Infrastructure Layer (Implementações)

#### Database (PostgreSQL)
**Localização:** `src/infrastructure/database/`

- **DatabaseConnection**: Gerenciamento de pool de conexões
- **BaseRepository**: Classe base com operações CRUD
- **Repositórios Específicos**:
  - CardRepository
  - DeckRepository  
  - ScrapingSessionRepository
  - MLModelRepository
  - BatchMetricsRepository

#### Configuration Management
**Localização:** `src/infrastructure/config/`

- **EnvironmentConfigManager**: Configurações por ambiente
- **ServiceContainer**: Container de injeção de dependência
- **Dependency Injection**: Decorators e lifecycle management

#### Web Scraping
**Localização:** `src/infrastructure/scraping/`

- **LigaMagicWebScraper**: Scraper anti-detecção para Liga Magic
- Rate limiting e session management
- Parsing específico por tipo de página

#### Machine Learning
**Localização:** `src/infrastructure/ml/`

- **ScikitLearnMLEngine**: Engine ML com scikit-learn
- Algoritmos: Random Forest, Gradient Boosting, Logistic Regression, SVM
- Feature engineering automático
- Hyperparameter tuning

#### Data Export
**Localização:** `src/infrastructure/export/`

- **ParquetDataExporter**: Exportação para Parquet, CSV, JSON
- Compressão e particionamento
- Validação de exportação

## Funcionalidades Principais

### 🔍 Web Scraping Avançado
- **Anti-detecção**: Headers rotativos, delays inteligentes
- **Robustez**: Retry automático, gestão de erros
- **Performance**: Scraping concorrente com rate limiting
- **Flexibilidade**: Suporte a múltiplos tipos de página

### 🤖 Machine Learning Pipeline
- **Algoritmos Múltiplos**: RF, GB, LR, SVM
- **Feature Engineering**: Automático com TF-IDF para texto
- **Validação**: Cross-validation e métricas completas
- **Lifecycle**: Versionamento e backup de modelos

### 📊 Exportação de Dados
- **Formatos**: Parquet (com particionamento), CSV, JSON
- **Performance**: Exportação em lote otimizada
- **Qualidade**: Validação e limpeza automática
- **Metadata**: Informações detalhadas de exportação

### ⚙️ Configuração e DI
- **Environment-based**: Configurações por ambiente
- **Dependency Injection**: Container completo com lifecycles
- **Type Safety**: Interfaces bem definidas
- **Flexibilidade**: Factory patterns e decorators

## Padrões de Design Implementados

### SOLID Principles
- **S**: Responsabilidade única por classe/módulo
- **O**: Extensão sem modificação (interfaces)
- **L**: Substituição de Liskov (implementações intercambiáveis)
- **I**: Segregação de interface (interfaces específicas)
- **D**: Inversão de dependência (DI container)

### Design Patterns
- **Repository Pattern**: Abstração de acesso a dados
- **Factory Pattern**: Criação de entidades
- **Strategy Pattern**: Algoritmos intercambiáveis
- **Command Pattern**: Operações como objetos
- **Observer Pattern**: Notificações de eventos

## Configuração

### Variáveis de Ambiente

```bash
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=sua_senha
DATABASE_NAME=decksmith

# Scraping
SCRAPING_BASE_URL=https://ligamagic.com.br
SCRAPING_DEFAULT_DELAY=1.0
SCRAPING_CONCURRENT_WORKERS=4

# Machine Learning
ML_MODELS_DIR=./models
ML_DEFAULT_ALGORITHM=random_forest

# Export
EXPORT_OUTPUT_DIR=./exports
EXPORT_DEFAULT_FORMAT=parquet
```

## Próximos Passos

### 1. DeckSmith-API (REST Service)
- Endpoints para consulta de modelos ML
- Autenticação JWT
- Cache Redis
- Documentação OpenAPI

### 2. DeckSmith-Frontend (Interface Web)
- Dashboard React/Vue
- Visualizações interativas
- Gerenciamento de jobs
- Monitoramento em tempo real

### 3. Deploy Heroku
- Configuração Docker
- CI/CD pipelines
- Monitoramento e logs
- Escalabilidade automática

## Performance e Escalabilidade

### Database
- **Connection Pooling**: 5-20 conexões simultâneas
- **Batch Operations**: Inserções em lote otimizadas
- **Indexação**: Índices automáticos por queries

### Scraping
- **Concorrência**: 4 workers simultâneos
- **Rate Limiting**: 1-5s entre requisições
- **Memory**: Gestão eficiente de sessões

### Machine Learning
- **Pipeline**: Processing paralelo de features
- **Memory**: Batch processing para grandes datasets
- **Storage**: Compressão e backup automático

### Export
- **Streaming**: Exportação incremental
- **Compression**: Snappy/GZIP automático
- **Validation**: Verificação de integridade

## Monitoramento

### Logs Estruturados
- Níveis configuráveis (DEBUG, INFO, WARN, ERROR)
- Contexto detalhado por operação
- Integração com sistemas externos

### Métricas
- Performance de scraping
- Acurácia de modelos ML
- Status de exportações
- Health checks automáticos

### Alertas
- Falhas de scraping
- Degradação de modelos
- Problemas de infraestrutura
- Capacidade do sistema

## Desenvolvimento

### Setup Local
```bash
# 1. Clonar repositório
git clone <repo>

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env

# 4. Executar migrations
python scripts/migrate.py

# 5. Iniciar sistema
python main.py
```

### Testes
- Unit tests para cada camada
- Integration tests para APIs
- End-to-end tests para workflows
- Performance tests para bottlenecks

### Qualidade de Código
- Type hints em 100% do código
- Docstrings detalhadas
- Linting com pylint/black
- Coverage mínimo de 90%

## Arquitetura Técnica

### Stack Principal
- **Python 3.11+**: Linguagem principal
- **PostgreSQL**: Banco de dados principal
- **AsyncPG**: Driver assíncrono PostgreSQL
- **Scikit-learn**: Machine Learning
- **PyArrow**: Processamento Parquet
- **aiohttp**: HTTP client assíncrono
- **BeautifulSoup**: HTML parsing

### DevOps
- **Docker**: Containerização
- **Heroku**: Cloud deployment
- **GitHub Actions**: CI/CD
- **Monitoring**: Logs + métricas

O sistema está completamente funcional e pronto para deploy e extensão com os demais microserviços!