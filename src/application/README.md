# DeckSmith Batch Processing System - Application Layer

## Casos de Uso (Use Cases)

Esta camada contém a lógica de aplicação e orquestra as operações do domínio.

### Estrutura:
- `use_cases/` - Casos de uso específicos
- `dto/` - Data Transfer Objects
- `interfaces/` - Interfaces para serviços externos
- `services/` - Serviços de aplicação

### Casos de Uso Implementados:
1. **ScrapingUseCase** - Orquestra processo de scraping
2. **MLTrainingUseCase** - Treina modelos de ML
3. **DataExportUseCase** - Exporta dados para API
4. **HealthCheckUseCase** - Monitora saúde do sistema

### DTOs:
- Request/Response objects para comunicação entre camadas
- Validação de dados de entrada
- Serialização/deserialização

### Interfaces:
- IWebScraper - Interface para scrapers
- IMLEngine - Interface para engine de ML
- IDataExporter - Interface para exportação
- INotificationService - Interface para notificações