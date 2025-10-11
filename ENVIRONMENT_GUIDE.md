# DeckSmith Batch Processing System - Environment Configuration Guide

## 📋 Visão Geral

O sistema DeckSmith foi completamente modernizado com configurações específicas por ambiente, Deep Learning com TensorFlow, e pipeline CI/CD completo. O sistema detecta automaticamente o ambiente baseado no branch Git e ajusta todas as configurações correspondentes.

## 🔄 Ambientes e Branches

### Estrutura de Branches
- **`develop`** → Ambiente de **Desenvolvimento** (`development`)
- **`release/vX.Y.Z`** → Ambiente de **Homologação** (`homologation`)
- **`main`** → Ambiente de **Produção** (`production`)

### Detecção Automática de Ambiente
O sistema utiliza as seguintes regras de detecção:

1. **Git Branch Detection**: Verifica o branch atual
2. **Environment Variable**: `DECKSMITH_ENV` (override manual)
3. **Heroku Detection**: Detecta se está rodando no Heroku
4. **Default Fallback**: Development se não conseguir detectar

## 🌍 Configurações por Ambiente

### Development Environment
```yaml
Environment: development
Database:
  host: localhost
  port: 5432
  pool_size: 5-10
API:
  timeout: 30s
  rate_limit: 1s
  max_requests_per_hour: 500
ML:
  enable_deep_learning: true
  batch_size: 32
  model_architecture: simple_neural_network
  epochs: 10
Monitoring:
  log_level: DEBUG
  metrics_retention: 7 days
```

### Homologation Environment  
```yaml
Environment: homologation
Database:
  host: heroku-postgres
  pool_size: 10-20
API:
  timeout: 60s
  rate_limit: 0.5s
  max_requests_per_hour: 1000
ML:
  enable_deep_learning: true
  batch_size: 64
  model_architecture: convolutional_neural_network
  epochs: 50
Monitoring:
  log_level: INFO
  metrics_retention: 30 days
```

### Production Environment
```yaml
Environment: production
Database:
  host: heroku-postgres
  pool_size: 20-50
API:
  timeout: 120s
  rate_limit: 0.2s
  max_requests_per_hour: 2000
ML:
  enable_deep_learning: true
  batch_size: 128
  model_architecture: lstm_transformer
  epochs: 100
Monitoring:
  log_level: WARNING
  metrics_retention: 90 days
```
- **`main`** → Ambiente de **Produção** (`production`)

### Detecção Automática de Ambiente
O sistema detecta automaticamente o ambiente baseado em:
1. Variável de ambiente `DECKSMITH_ENVIRONMENT`
2. Branch Git atual
3. Nome do app Heroku (`HEROKU_APP_NAME`)
4. Padrão: `development`

## 🗃️ Configurações por Ambiente

### Development (develop branch)
```json
{
  "database": "Local PostgreSQL - decksmith_dev",
  "ml_config": {
    "deep_learning": true,
    "gpu": false,
    "batch_size": 32,
    "epochs": 10
  },
  "monitoring": "Debug level, local only",
  "security": "Relaxed for development",
  "notifications": "Disabled"
}
```

### Homologation (release/* branches)
```json
{
  "database": "Heroku Postgres - decksmith_hom",
  "ml_config": {
    "deep_learning": true,
    "gpu": false,
    "batch_size": 64,
    "epochs": 20
  },
  "monitoring": "Info level, Sentry enabled",
  "security": "Moderate security",
  "notifications": "Enabled for errors"
}
```

### Production (main branch)
```json
{
  "database": "Heroku Postgres Premium - decksmith_prod",
  "ml_config": {
    "deep_learning": true,
    "gpu": true,
    "batch_size": 128,
    "epochs": 50
  },
  "monitoring": "Warning level, full monitoring",
  "security": "Maximum security",
  "notifications": "Full notifications"
}
```

## 🤖 Deep Learning Implementation

### Novas Funcionalidades
- **TensorFlow/Keras** para Deep Learning
- **Múltiplas arquiteturas**: Card recommendation, deck similarity, embeddings
- **GPU Support** em produção
- **Model versioning** e tracking
- **Performance monitoring**

### Modelos Disponíveis
1. **Card Recommendation** - Recomendação de cartas para decks
2. **Deck Similarity** - Similaridade entre decks
3. **Card Embeddings** - Embeddings de cartas (autoencoder)
4. **Meta Predictor** - Predição de meta-game
5. **Price Predictor** - Predição de preços
6. **Synergy Detector** - Detecção de sinergias

### Schema do Banco Atualizado
- **ml_models** - Modelos com métricas de Deep Learning
- **ml_training_history** - Histórico época por época
- **ml_datasets** - Datasets para treinamento
- **card_embeddings** - Embeddings de cartas
- **deck_embeddings** - Embeddings de decks
- **meta_analysis** - Análise de meta-game

## 🚀 CI/CD Pipeline

### Workflow Development
**Trigger**: Push para `develop`
- ✅ Testes unitários
- ✅ Linting e code quality
- ✅ Security scan
- 🚀 Deploy automático para Heroku dev
- 📊 Health check

### Workflow Homologation
**Trigger**: Push para `release/*`
- ✅ Validação de versão
- ✅ Testes abrangentes + integração
- ✅ Security audit completo
- ✅ Build e teste Docker
- 🚀 Deploy para Heroku homologation
- 📋 Smoke tests
- 🏷️ Criação de release tag

### Workflow Production
**Trigger**: Push para `main` (com tag) ou manual
- ✅ Validação de produção
- ✅ Verificação de homologação
- ✅ Aprovação manual obrigatória
- ✅ Security audit crítico
- ✅ Testes finais
- 🛡️ Backup antes do deploy
- 🚀 Deploy para produção
- 🔄 Rollback automático em falha

## 📦 Configuração do Projeto

### 1. Variáveis de Ambiente
Copie `.env.template` para `.env` e configure:

```bash
# Ambiente
DECKSMITH_ENVIRONMENT=development

# Database
DATABASE_HOST=localhost
DATABASE_NAME=decksmith_dev
DATABASE_USER=decksmith_user
DATABASE_PASSWORD=your_password

# ML
ML_ENABLE_DEEP_LEARNING=true
ML_USE_GPU=false
ML_BATCH_SIZE=32

# Monitoring
MONITORING_ENABLED=true
MONITORING_LOG_LEVEL=DEBUG
```

### 2. Configuração do Heroku

#### Apps Necessários
```bash
# Desenvolvimento
heroku apps:create decksmith-batch-dev

# Homologação
heroku apps:create decksmith-batch-hom

# Produção
heroku apps:create decksmith-batch-prod
```

#### Add-ons Heroku
```bash
# PostgreSQL
heroku addons:create heroku-postgresql:mini --app decksmith-batch-dev
heroku addons:create heroku-postgresql:basic --app decksmith-batch-hom
heroku addons:create heroku-postgresql:standard-0 --app decksmith-batch-prod

# Redis (se necessário)
heroku addons:create heroku-redis:mini --app decksmith-batch-dev
```

### 3. Secrets do GitHub
Configure no GitHub Settings > Secrets:

```
# Heroku
HEROKU_API_KEY=your_heroku_api_key
HEROKU_EMAIL=your_heroku_email
HEROKU_API_KEY_PROD=your_heroku_api_key_prod
HEROKU_EMAIL_PROD=your_heroku_email_prod

# Slack
SLACK_WEBHOOK_DEV=dev_webhook_url
SLACK_WEBHOOK_HOM=hom_webhook_url
SLACK_WEBHOOK_PROD=prod_webhook_url

# Sentry
SENTRY_DSN_DEV=dev_sentry_dsn
SENTRY_DSN_HOM=hom_sentry_dsn
SENTRY_DSN_PROD=prod_sentry_dsn
```

## 🔧 Desenvolvimento Local

### Configuração Inicial
```bash
# 1. Clone o repositório
git clone https://github.com/ivancara/decksmith-batch.git
cd decksmith-batch

# 2. Configure ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure banco local
createdb decksmith_dev
psql -d decksmith_dev -f database_schema.sql

# 5. Configure variáveis de ambiente
cp .env.template .env
# Edite .env com suas configurações

# 6. Execute o sistema
python main.py
```

### Testando Deep Learning
```python
from src.infrastructure.ml.deep_learning_engine import TensorFlowDeepLearningEngine
from src.infrastructure.config.environment_config import EnvironmentAwareConfigManager

# Inicializar
config = EnvironmentAwareConfigManager()
ml_engine = TensorFlowDeepLearningEngine(config)

# Verificar arquiteturas disponíveis
print(ml_engine.get_available_architectures())
```

## 🔄 Fluxo de Deploy

### 1. Desenvolvimento
```bash
# Trabalhe na branch develop
git checkout develop
git pull origin develop

# Faça suas alterações
git add .
git commit -m "feat: nova funcionalidade"
git push origin develop

# Deploy automático para dev acontece via CI/CD
```

### 2. Homologação
```bash
# Crie branch de release
git checkout -b release/v1.2.0
git push origin release/v1.2.0

# Deploy automático para homologação acontece via CI/CD
# Testes são executados automaticamente
```

### 3. Produção
```bash
# Merge da release para main
git checkout main
git merge release/v1.2.0
git tag v1.2.0
git push origin main --tags

# Deploy para produção (com aprovação manual)
```

## 📊 Monitoramento

### Métricas por Ambiente
- **Development**: Logs debug, métricas básicas
- **Homologation**: Logs info, Sentry, métricas completas
- **Production**: Logs warning+, Sentry, alertas, métricas detalhadas

### URLs de Monitoramento
- Dev: https://decksmith-batch-dev.herokuapp.com/health
- Hom: https://decksmith-batch-hom.herokuapp.com/health
- Prod: https://decksmith-batch-prod.herokuapp.com/health

## 🛡️ Segurança

### Por Ambiente
- **Development**: Segurança relaxada, sem rate limiting
- **Homologation**: Rate limiting moderado, verificações básicas
- **Production**: Segurança máxima, rate limiting rigoroso, verificações completas

### Security Checks
- Dependency vulnerabilities (Safety)
- Code security issues (Bandit)
- Static analysis (Semgrep)
- Docker security scanning

## 📝 Logs e Debugging

### Níveis de Log por Ambiente
- **Development**: DEBUG - todos os detalhes
- **Homologation**: INFO - informações importantes
- **Production**: WARNING - apenas problemas importantes

### Acessando Logs
```bash
# Heroku logs
heroku logs --tail --app decksmith-batch-dev
heroku logs --tail --app decksmith-batch-hom
heroku logs --tail --app decksmith-batch-prod

# Logs específicos do ML
heroku logs --tail --source app --app decksmith-batch-prod | grep "ML"
```

## 🆘 Troubleshooting

### Problemas Comuns

#### 1. Falha no Deploy
```bash
# Verificar logs do CI/CD
# Checar GitHub Actions logs

# Verificar configurações do Heroku
heroku config --app decksmith-batch-dev
```

#### 2. Erro de Configuração
```bash
# Verificar ambiente detectado
python -c "from src.infrastructure.config.environment_config import EnvironmentAwareConfigManager; print(EnvironmentAwareConfigManager().get_environment_info())"
```

#### 3. Problema de ML/TensorFlow
```bash
# Verificar TensorFlow
python -c "import tensorflow as tf; print(tf.__version__); print(tf.config.list_physical_devices())"

# Verificar configuração ML
python -c "from src.infrastructure.config.environment_config import EnvironmentAwareConfigManager; print(EnvironmentAwareConfigManager().get_ml_config_typed())"
```

#### 4. Rollback de Produção
```bash
# Rollback manual
heroku rollback --app decksmith-batch-prod

# Verificar health
curl https://decksmith-batch-prod.herokuapp.com/health
```

## 📚 Documentação Adicional

- [Database Schema](database_schema.sql) - Schema completo do banco
- [Requirements](requirements.txt) - Dependências Python
- [Dockerfile](Dockerfile) - Configuração Docker
- [CI/CD Workflows](.github/workflows/) - Pipelines GitHub Actions

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Add nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request para `develop`

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.