# DeckSmith Batch Processing Service

## Heroku Deployment

### Setup Commands
```bash
# Create Heroku app
heroku create decksmith-batch

# Set Python buildpack
heroku buildpacks:set heroku/python --app decksmith-batch

# Configure environment variables
heroku config:set DATABASE_URL="your_postgres_url" --app decksmith-batch
heroku config:set REDIS_URL="your_redis_url" --app decksmith-batch
heroku config:set MTG_API_KEY="your_scryfall_api_key" --app decksmith-batch
heroku config:set ML_API_ENDPOINT="your_ml_api_endpoint" --app decksmith-batch
heroku config:set LOG_LEVEL="INFO" --app decksmith-batch

# Deploy
git subtree push --prefix=decksmith-batch heroku main

# Scale worker process
heroku ps:scale worker=1 --app decksmith-batch
```

### Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string for queues
- `MTG_API_KEY`: Scryfall API key (optional but recommended)
- `ML_API_ENDPOINT`: Machine Learning service endpoint
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Process Type
- **worker**: Runs background batch processing tasks
- No web process required (batch service only)

### Monitoring
```bash
# Check logs
heroku logs --tail --app decksmith-batch

# Check worker status
heroku ps --app decksmith-batch
```