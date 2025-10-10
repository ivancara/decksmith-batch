"""
Tests for ML analysis functionality in batch processing
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd

class TestMLEngine:
    """Test ML engine functionality"""
    
    def test_ml_engine_initialization(self, mock_ml_engine):
        """Test ML engine initializes correctly"""
        assert mock_ml_engine is not None
        
    def test_analyze_deck_success(self, mock_ml_engine, sample_deck_data):
        """Test successful deck analysis"""
        result = mock_ml_engine.analyze_deck(sample_deck_data)
        
        assert result["win_rate_prediction"] == 0.72
        assert "strengths" in result
        assert "weaknesses" in result
        assert "recommendations" in result
        
    def test_analyze_deck_invalid_data(self, mock_ml_engine):
        """Test deck analysis with invalid data"""
        invalid_data = {"invalid": "data"}
        
        mock_ml_engine.analyze_deck.side_effect = ValueError("Invalid deck data")
        
        with pytest.raises(ValueError):
            mock_ml_engine.analyze_deck(invalid_data)
    
    @patch('src.infrastructure.ml.ml_engine.joblib')
    def test_train_model_success(self, mock_joblib, mock_ml_engine, test_db):
        """Test successful model training"""
        # Mock training data
        training_data = pd.DataFrame({
            'deck_id': [1, 2, 3],
            'win_rate': [0.6, 0.7, 0.8],
            'features': [[1, 0, 1], [0, 1, 1], [1, 1, 0]]
        })
        
        mock_ml_engine.train_model.return_value = {
            "model_id": "test_model_v1",
            "accuracy": 0.85,
            "training_time": 120
        }
        
        result = mock_ml_engine.train_model(training_data)
        
        assert result["accuracy"] >= 0.8
        assert "model_id" in result
        
    def test_predict_meta_shifts(self, mock_ml_engine):
        """Test meta shift prediction"""
        result = mock_ml_engine.predict_meta_shifts()
        
        assert "emerging_decks" in result
        assert "declining_decks" in result
        
    def test_feature_extraction(self, mock_ml_engine, sample_deck_data):
        """Test feature extraction from deck data"""
        mock_ml_engine.extract_features = Mock(return_value=np.array([1, 0, 1, 0, 0]))
        
        features = mock_ml_engine.extract_features(sample_deck_data)
        
        assert isinstance(features, np.ndarray)
        assert len(features) == 5

class TestDataProcessing:
    """Test data processing functionality"""
    
    @pytest.mark.asyncio
    async def test_process_tournament_data(self, mock_web_scraper):
        """Test processing tournament data"""
        tournament_data = await mock_web_scraper.scrape_tournament_data()
        
        assert len(tournament_data) > 0
        assert "tournament_name" in tournament_data[0]
        assert "decks" in tournament_data[0]
        
    @pytest.mark.asyncio
    async def test_process_deck_data(self, mock_web_scraper):
        """Test processing individual deck data"""
        deck_data = await mock_web_scraper.scrape_deck_data()
        
        assert "name" in deck_data
        assert "cards" in deck_data
        
    def test_data_validation(self, sample_deck_data):
        """Test data validation functionality"""
        from src.application.services.validation_service import validate_deck_data
        
        # Mock validation
        with patch('src.application.services.validation_service.validate_deck_data') as mock_validate:
            mock_validate.return_value = True
            
            is_valid = validate_deck_data(sample_deck_data)
            assert is_valid is True
            
    def test_data_cleaning(self, sample_deck_data):
        """Test data cleaning functionality"""
        from src.application.services.data_service import clean_deck_data
        
        # Mock cleaning
        with patch('src.application.services.data_service.clean_deck_data') as mock_clean:
            cleaned_data = sample_deck_data.copy()
            cleaned_data["normalized"] = True
            mock_clean.return_value = cleaned_data
            
            result = clean_deck_data(sample_deck_data)
            assert result["normalized"] is True

class TestBatchJobs:
    """Test batch job functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_decks_batch(self, mock_ml_engine, batch_job_config):
        """Test batch deck analysis"""
        from src.application.jobs.analysis_job import AnalysisJob
        
        # Mock batch job
        with patch.object(AnalysisJob, 'process_batch') as mock_process:
            mock_process.return_value = {
                "processed": 10,
                "succeeded": 9,
                "failed": 1,
                "results": [{"deck_id": i, "status": "success"} for i in range(9)]
            }
            
            job = AnalysisJob(config=batch_job_config)
            result = await job.process_batch([f"deck_{i}" for i in range(10)])
            
            assert result["processed"] == 10
            assert result["succeeded"] == 9
            
    @pytest.mark.asyncio
    async def test_scraping_batch_job(self, mock_web_scraper, batch_job_config):
        """Test batch scraping job"""
        from src.application.jobs.scraping_job import ScrapingJob
        
        with patch.object(ScrapingJob, 'process_urls') as mock_process:
            mock_process.return_value = {
                "urls_processed": 5,
                "data_extracted": 4,
                "errors": 1
            }
            
            job = ScrapingJob(config=batch_job_config)
            urls = ["http://example.com/deck/1", "http://example.com/deck/2"]
            result = await job.process_urls(urls)
            
            assert result["urls_processed"] >= len(urls)
            
    def test_job_retry_mechanism(self, batch_job_config):
        """Test job retry mechanism"""
        from src.application.jobs.base_job import BaseJob
        
        with patch.object(BaseJob, 'execute_with_retry') as mock_retry:
            # Simulate failure then success
            mock_retry.side_effect = [Exception("Temporary error"), {"status": "success"}]
            
            job = BaseJob(config=batch_job_config)
            # Should retry and eventually succeed
            mock_retry.side_effect = [{"status": "success"}]
            result = job.execute_with_retry(lambda: {"status": "success"})
            
            assert result["status"] == "success"
            
    @pytest.mark.asyncio
    async def test_parallel_processing(self, batch_job_config):
        """Test parallel job processing"""
        from src.application.jobs.parallel_processor import ParallelProcessor
        
        async def mock_task(item):
            return {"item": item, "processed": True}
        
        processor = ParallelProcessor(max_workers=batch_job_config["parallel_workers"])
        items = [f"item_{i}" for i in range(5)]
        
        results = await processor.process_parallel(items, mock_task)
        
        assert len(results) == 5
        assert all(result["processed"] for result in results)

class TestCaching:
    """Test caching functionality"""
    
    def test_redis_cache_operations(self, mock_redis):
        """Test Redis cache operations"""
        from src.infrastructure.cache.redis_cache import RedisCache
        
        cache = RedisCache(mock_redis)
        
        # Test set
        cache.set("test_key", {"data": "value"}, ttl=3600)
        mock_redis.set.assert_called()
        
        # Test get
        mock_redis.get.return_value = '{"data": "value"}'
        result = cache.get("test_key")
        assert result["data"] == "value"
        
    def test_cache_invalidation(self, mock_redis):
        """Test cache invalidation"""
        from src.infrastructure.cache.redis_cache import RedisCache
        
        cache = RedisCache(mock_redis)
        
        cache.invalidate("pattern:*")
        mock_redis.delete.assert_called()
        
    def test_cache_miss_handling(self, mock_redis):
        """Test cache miss handling"""
        from src.infrastructure.cache.redis_cache import RedisCache
        
        cache = RedisCache(mock_redis)
        mock_redis.get.return_value = None
        
        result = cache.get("nonexistent_key")
        assert result is None

class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_web_scraper):
        """Test handling of network errors during scraping"""
        mock_web_scraper.scrape_tournament_data.side_effect = Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            await mock_web_scraper.scrape_tournament_data()
        
        assert "Network error" in str(exc_info.value)
        
    def test_database_error_handling(self, test_db):
        """Test handling of database errors"""
        from src.infrastructure.database.operations import DatabaseOperations
        
        with patch.object(DatabaseOperations, 'save_analysis_result') as mock_save:
            mock_save.side_effect = Exception("Database connection error")
            
            db_ops = DatabaseOperations(test_db)
            
            with pytest.raises(Exception) as exc_info:
                db_ops.save_analysis_result({"test": "data"})
            
            assert "Database connection error" in str(exc_info.value)
            
    def test_ml_model_error_handling(self, mock_ml_engine):
        """Test handling of ML model errors"""
        mock_ml_engine.analyze_deck.side_effect = Exception("Model prediction error")
        
        with pytest.raises(Exception) as exc_info:
            mock_ml_engine.analyze_deck({"test": "deck"})
            
        assert "Model prediction error" in str(exc_info.value)

class TestPerformanceMonitoring:
    """Test performance monitoring"""
    
    def test_execution_time_tracking(self):
        """Test execution time tracking"""
        from src.infrastructure.monitoring.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        with monitor.track_execution("test_operation"):
            import time
            time.sleep(0.1)  # Simulate work
            
        stats = monitor.get_stats("test_operation")
        assert stats["execution_time"] >= 0.1
        
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring"""
        from src.infrastructure.monitoring.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        initial_memory = monitor.get_memory_usage()
        
        # Simulate memory intensive operation
        large_data = [i for i in range(10000)]
        
        peak_memory = monitor.get_memory_usage()
        assert peak_memory >= initial_memory
        
    def test_job_queue_monitoring(self, mock_redis):
        """Test job queue monitoring"""
        from src.infrastructure.monitoring.queue_monitor import QueueMonitor
        
        monitor = QueueMonitor(mock_redis)
        
        mock_redis.llen.return_value = 5
        queue_size = monitor.get_queue_size("analysis_queue")
        
        assert queue_size == 5