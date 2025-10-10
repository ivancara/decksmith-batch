"""
Pytest configuration for DeckSmith Batch testing
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.database.connection import Base
from src.domain.entities import Deck, Card, AnalysisResult
from src.infrastructure.ml.ml_engine import MLEngine
from src.infrastructure.scraping.web_scraper import WebScraper

# Test database
TEST_DATABASE_URL = "sqlite:///test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)
    # Clean up test database file
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    return mock_redis

@pytest.fixture
def sample_deck_data():
    """Sample deck data for testing"""
    return {
        "name": "Test Aggro Deck",
        "format": "Standard",
        "cards": [
            {"name": "Lightning Bolt", "quantity": 4},
            {"name": "Shock", "quantity": 4},
            {"name": "Mountain", "quantity": 20}
        ],
        "archetype": "Aggro",
        "colors": ["R"],
        "mana_curve": [0, 8, 0, 0, 0, 0, 0, 0]
    }

@pytest.fixture
def sample_card_data():
    """Sample card data for testing"""
    return {
        "name": "Lightning Bolt",
        "mana_cost": "R",
        "cmc": 1,
        "type_line": "Instant",
        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
        "colors": ["R"],
        "rarity": "common",
        "set_code": "M21"
    }

@pytest.fixture
def mock_ml_engine():
    """Mock ML engine"""
    mock_engine = Mock(spec=MLEngine)
    mock_engine.analyze_deck = Mock(return_value={
        "win_rate_prediction": 0.72,
        "strengths": ["Fast aggro", "Consistent"],
        "weaknesses": ["Weak to board wipes"],
        "recommendations": ["Add more removal"]
    })
    mock_engine.train_model = Mock(return_value=True)
    mock_engine.predict_meta_shifts = Mock(return_value={
        "emerging_decks": ["New Aggro"],
        "declining_decks": ["Old Control"]
    })
    return mock_engine

@pytest.fixture
def mock_web_scraper():
    """Mock web scraper"""
    mock_scraper = Mock(spec=WebScraper)
    mock_scraper.scrape_tournament_data = AsyncMock(return_value=[
        {
            "tournament_name": "Test Tournament",
            "date": "2024-01-01",
            "format": "Standard",
            "decks": [{"name": "Aggro Deck", "placement": 1}]
        }
    ])
    mock_scraper.scrape_deck_data = AsyncMock(return_value={
        "name": "Scraped Deck",
        "cards": [{"name": "Lightning Bolt", "quantity": 4}]
    })
    return mock_scraper

@pytest.fixture
def temp_directory():
    """Create temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing"""
    return {
        "deck_id": 1,
        "analysis_type": "win_rate_prediction",
        "result": {
            "predicted_win_rate": 0.68,
            "confidence": 0.85,
            "factors": ["mana_curve", "card_synergy"]
        },
        "created_at": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_external_api():
    """Mock external API responses"""
    mock_api = Mock()
    mock_api.get_card_data = AsyncMock(return_value={
        "name": "Lightning Bolt",
        "oracle_text": "Lightning Bolt deals 3 damage to any target."
    })
    mock_api.get_tournament_results = AsyncMock(return_value=[
        {"tournament": "Test", "winner": "Player A"}
    ])
    return mock_api

@pytest.fixture
def batch_job_config():
    """Configuration for batch job testing"""
    return {
        "batch_size": 10,
        "max_retries": 3,
        "timeout": 30,
        "parallel_workers": 2
    }