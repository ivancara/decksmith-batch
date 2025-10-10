# DeckSmith Batch Processing System - Infrastructure Layer

## Componentes da Infraestrutura

Esta camada implementa os adaptadores e serviços externos que a aplicação utiliza.

### Estrutura:
- `database/` - Adaptadores PostgreSQL para repositories
- `scraper/` - Implementações de web scraping
- `ml/` - Engine de Machine Learning
- `export/` - Sistema de exportação de dados
- `config/` - Gerenciamento de configurações
- `monitoring/` - Serviços de monitoramento
- `notifications/` - Sistema de notificações

### Implementações:
1. **PostgreSQL Adapters** - Implementação dos repositories
2. **Liga Magic Scraper** - Web scraping do Liga Magic
3. **ML Engine** - Scikit-learn/TensorFlow para treinamento
4. **Parquet Exporter** - Exportação para formato Parquet
5. **Config Manager** - Configurações via environment variables
6. **Monitoring Service** - Métricas e logs
7. **Notification Service** - Alertas via email/webhook

### Dependências:
- asyncpg (PostgreSQL async)
- aiohttp (HTTP client)
- pandas (Data manipulation)
- scikit-learn (ML)
- pyarrow (Parquet)
- structlog (Logging)