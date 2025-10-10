"""
DeckSmith Batch Processing System
Infrastructure Layer - Machine Learning Engine Implementation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import json
from pathlib import Path

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from ...application.interfaces import IMLEngine
from ...application.dto import MLTrainingRequestDTO, MLTrainingResultDTO, MLPredictionRequestDTO, MLPredictionResultDTO
from ...domain.entities import MLModel, Card, Deck
from ..config import EnvironmentConfigManager


class ScikitLearnMLEngine(IMLEngine):
    """Engine de Machine Learning usando Scikit-Learn"""
    
    def __init__(self, config_manager: EnvironmentConfigManager):
        self.config = config_manager
        self.ml_config = config_manager.get_ml_config()
        
        self.logger = logging.getLogger(__name__)
        
        # Diretórios
        self.models_dir = Path(self.ml_config["models_directory"])
        self.data_dir = Path(self.ml_config["data_directory"])
        self.temp_dir = Path(self.ml_config["temp_directory"])
        
        # Criar diretórios se não existirem
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Algoritmos disponíveis
        self.algorithms = {
            "random_forest": RandomForestClassifier,
            "gradient_boosting": GradientBoostingClassifier,
            "logistic_regression": LogisticRegression,
            "svm": SVC
        }
        
        # Hiperparâmetros padrão
        self.default_hyperparameters = {
            "random_forest": {
                "n_estimators": [100, 200, 300],
                "max_depth": [10, 20, None],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4]
            },
            "gradient_boosting": {
                "n_estimators": [100, 200],
                "learning_rate": [0.05, 0.1, 0.15],
                "max_depth": [3, 5, 7]
            },
            "logistic_regression": {
                "C": [0.1, 1, 10],
                "solver": ["liblinear", "lbfgs"]
            },
            "svm": {
                "C": [0.1, 1, 10],
                "kernel": ["rbf", "linear"],
                "gamma": ["scale", "auto"]
            }
        }
        
        # Cache de modelos carregados
        self.loaded_models: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """Inicializa engine de ML"""
        try:
            self.logger.info("Machine Learning engine initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize ML engine: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Finaliza engine de ML"""
        try:
            # Limpar cache de modelos
            self.loaded_models.clear()
            
            # Limpar arquivos temporários se configurado
            if self.ml_config.get("cleanup_temp_files", True):
                await self._cleanup_temp_files()
            
            self.logger.info("Machine Learning engine cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup ML engine: {e}")
            return False
    
    async def train_model(self, request: MLTrainingRequestDTO) -> MLTrainingResultDTO:
        """Treina modelo de ML"""
        try:
            training_start = datetime.utcnow()
            
            # Preparar dados
            X, y, feature_names = await self._prepare_training_data(request)
            
            if X is None or y is None:
                return MLTrainingResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message="Failed to prepare training data",
                    training_duration=0.0,
                    training_timestamp=training_start
                )
            
            # Dividir dados
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=1 - self.ml_config["training_split"],
                random_state=42,
                stratify=y if len(np.unique(y)) > 1 else None
            )
            
            # Selecionar algoritmo
            algorithm = request.algorithm or self.ml_config["default_algorithm"]
            
            if algorithm not in self.algorithms:
                return MLTrainingResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message=f"Algorithm {algorithm} not supported",
                    training_duration=0.0,
                    training_timestamp=training_start
                )
            
            # Criar pipeline
            pipeline = await self._create_pipeline(algorithm, request.hyperparameters)
            
            # Treinar modelo
            if self.ml_config.get("hyperparameter_tuning", False):
                model = await self._train_with_hyperparameter_tuning(
                    pipeline, X_train, y_train, algorithm
                )
            else:
                model = pipeline
                model.fit(X_train, y_train)
            
            # Avaliar modelo
            metrics = await self._evaluate_model(model, X_test, y_test)
            
            # Salvar modelo
            model_path = await self._save_model(request.model_id, model, feature_names, metrics)
            
            training_end = datetime.utcnow()
            training_duration = (training_end - training_start).total_seconds()
            
            return MLTrainingResultDTO(
                model_id=request.model_id,
                success=True,
                model_path=str(model_path),
                metrics=metrics,
                training_duration=training_duration,
                training_timestamp=training_start,
                feature_names=feature_names,
                algorithm=algorithm
            )
            
        except Exception as e:
            self.logger.error(f"Error training model {request.model_id}: {e}")
            training_end = datetime.utcnow()
            training_duration = (training_end - training_start).total_seconds()
            
            return MLTrainingResultDTO(
                model_id=request.model_id,
                success=False,
                error_message=str(e),
                training_duration=training_duration,
                training_timestamp=training_start
            )
    
    async def predict(self, request: MLPredictionRequestDTO) -> MLPredictionResultDTO:
        """Faz predições usando modelo treinado"""
        try:
            # Carregar modelo
            model, feature_names = await self._load_model(request.model_id)
            
            if model is None:
                return MLPredictionResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message="Model not found or failed to load",
                    prediction_timestamp=datetime.utcnow()
                )
            
            # Preparar dados para predição
            X = await self._prepare_prediction_data(request.input_data, feature_names)
            
            if X is None:
                return MLPredictionResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message="Failed to prepare prediction data",
                    prediction_timestamp=datetime.utcnow()
                )
            
            # Fazer predições
            predictions = model.predict(X)
            
            # Obter probabilidades se disponível
            probabilities = None
            if hasattr(model, "predict_proba"):
                try:
                    probabilities = model.predict_proba(X)
                except:
                    pass
            
            # Preparar resultado
            results = []
            for i, prediction in enumerate(predictions):
                result = {"prediction": prediction}
                
                if probabilities is not None:
                    result["probabilities"] = probabilities[i].tolist()
                    result["confidence"] = float(max(probabilities[i]))
                
                results.append(result)
            
            return MLPredictionResultDTO(
                model_id=request.model_id,
                success=True,
                predictions=results,
                prediction_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error making prediction with model {request.model_id}: {e}")
            return MLPredictionResultDTO(
                model_id=request.model_id,
                success=False,
                error_message=str(e),
                prediction_timestamp=datetime.utcnow()
            )
    
    async def evaluate_model(self, model_id: str, test_data: Dict[str, Any]) -> Dict[str, float]:
        """Avalia modelo com dados de teste"""
        try:
            # Carregar modelo
            model, feature_names = await self._load_model(model_id)
            
            if model is None:
                raise ValueError("Model not found")
            
            # Preparar dados de teste
            X_test = await self._prepare_prediction_data(test_data, feature_names)
            y_test = test_data.get("target", [])
            
            if X_test is None or not y_test:
                raise ValueError("Invalid test data")
            
            # Avaliar
            return await self._evaluate_model(model, X_test, y_test)
            
        except Exception as e:
            self.logger.error(f"Error evaluating model {model_id}: {e}")
            return {}
    
    async def get_feature_importance(self, model_id: str) -> Dict[str, float]:
        """Obtém importância das features"""
        try:
            model, feature_names = await self._load_model(model_id)
            
            if model is None:
                return {}
            
            # Tentar obter feature importance
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
            elif hasattr(model, "coef_"):
                importances = np.abs(model.coef_[0])
            else:
                return {}
            
            # Criar dicionário feature -> importância
            return dict(zip(feature_names, importances.tolist()))
            
        except Exception as e:
            self.logger.error(f"Error getting feature importance for model {model_id}: {e}")
            return {}
    
    async def _prepare_training_data(self, request: MLTrainingRequestDTO) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[str]]]:
        """Prepara dados para treinamento"""
        try:
            # Converter dados para DataFrame
            df = pd.DataFrame(request.training_data)
            
            if df.empty:
                return None, None, None
            
            # Separar features e target
            target_column = request.target_column
            if target_column not in df.columns:
                raise ValueError(f"Target column {target_column} not found")
            
            y = np.array(df[target_column].values)
            X_df = df.drop(columns=[target_column])
            
            # Preparar features
            X, feature_names = await self._prepare_features(X_df)
            
            return X, y, feature_names
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return None, None, None
    
    async def _prepare_prediction_data(self, input_data: Dict[str, Any], feature_names: List[str]) -> Optional[np.ndarray]:
        """Prepara dados para predição"""
        try:
            # Converter para DataFrame
            df = pd.DataFrame([input_data])
            
            # Preparar features
            X, _ = await self._prepare_features(df, feature_names)
            
            return X
            
        except Exception as e:
            self.logger.error(f"Error preparing prediction data: {e}")
            return None
    
    async def _prepare_features(self, df: pd.DataFrame, expected_features: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """Prepara features para ML"""
        feature_columns = []
        
        # Processar cada coluna
        for column in df.columns:
            if df[column].dtype == 'object':
                # Coluna categórica/texto
                if df[column].str.len().mean() > 50:
                    # Texto longo - usar TF-IDF
                    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
                    tfidf_features = vectorizer.fit_transform(df[column].fillna(''))
                    
                    # Adicionar features TF-IDF
                    for i in range(tfidf_features.shape[1]):
                        feature_columns.append(f"{column}_tfidf_{i}")
                else:
                    # Categoria - usar Label Encoding
                    le = LabelEncoder()
                    df[f"{column}_encoded"] = le.fit_transform(df[column].fillna('unknown'))
                    feature_columns.append(f"{column}_encoded")
            else:
                # Coluna numérica
                df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0)
                feature_columns.append(column)
        
        # Selecionar features finais
        if expected_features:
            # Usar features esperadas
            available_features = [f for f in expected_features if f in df.columns]
            feature_columns = available_features
        
        # Criar matriz de features
        X = df[feature_columns].values
        
        return X, feature_columns
    
    async def _create_pipeline(self, algorithm: str, hyperparameters: Optional[Dict[str, Any]] = None) -> Pipeline:
        """Cria pipeline de ML"""
        # Selecionar algoritmo
        algorithm_class = self.algorithms[algorithm]
        
        # Usar hiperparâmetros fornecidos ou padrão
        if hyperparameters:
            params = hyperparameters
        else:
            # Usar primeiro conjunto de hiperparâmetros padrão
            default_params = self.default_hyperparameters.get(algorithm, {})
            params = {k: v[0] if isinstance(v, list) else v for k, v in default_params.items()}
        
        # Criar modelo
        model = algorithm_class(**params)
        
        # Criar pipeline com normalização
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', model)
        ])
        
        return pipeline
    
    async def _train_with_hyperparameter_tuning(self, pipeline: Pipeline, X_train: np.ndarray, 
                                               y_train: np.ndarray, algorithm: str) -> Pipeline:
        """Treina modelo com otimização de hiperparâmetros"""
        # Obter grade de hiperparâmetros
        param_grid = {}
        algorithm_params = self.default_hyperparameters.get(algorithm, {})
        
        for param, values in algorithm_params.items():
            param_grid[f"model__{param}"] = values
        
        # Grid Search
        grid_search = GridSearchCV(
            pipeline,
            param_grid,
            cv=self.ml_config["cross_validation_folds"],
            scoring='accuracy',
            n_jobs=-1,
            verbose=0
        )
        
        grid_search.fit(X_train, y_train)
        
        return grid_search.best_estimator_
    
    async def _evaluate_model(self, model: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Avalia modelo e retorna métricas"""
        # Predições
        y_pred = model.predict(X_test)
        
        # Métricas básicas
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        }
        
        # Cross-validation se configurado
        if self.ml_config.get("cross_validation_folds", 0) > 1:
            try:
                cv_scores = cross_val_score(
                    model, X_test, y_test, 
                    cv=self.ml_config["cross_validation_folds"],
                    scoring='accuracy'
                )
                metrics["cv_accuracy_mean"] = float(cv_scores.mean())
                metrics["cv_accuracy_std"] = float(cv_scores.std())
            except Exception as e:
                self.logger.warning(f"Cross-validation failed: {e}")
        
        return metrics
    
    async def _save_model(self, model_id: str, model: Any, feature_names: List[str], 
                         metrics: Dict[str, float]) -> Path:
        """Salva modelo treinado"""
        # Criar timestamp para versionamento
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Diretório do modelo
        model_dir = self.models_dir / model_id
        model_dir.mkdir(exist_ok=True)
        
        # Paths dos arquivos
        model_path = model_dir / f"model_{timestamp}.joblib"
        metadata_path = model_dir / f"metadata_{timestamp}.json"
        latest_model_path = model_dir / "latest_model.joblib"
        latest_metadata_path = model_dir / "latest_metadata.json"
        
        # Salvar modelo
        joblib.dump(model, model_path)
        joblib.dump(model, latest_model_path)
        
        # Salvar metadata
        metadata = {
            "model_id": model_id,
            "timestamp": timestamp,
            "feature_names": feature_names,
            "metrics": metrics,
            "model_path": str(model_path),
            "algorithm": type(model.named_steps['model'] if hasattr(model, 'named_steps') else model).__name__
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        with open(latest_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Backup se configurado
        if self.ml_config.get("backup_models", True):
            await self._backup_model(model_id, model_path, metadata_path)
        
        self.logger.info(f"Model {model_id} saved successfully")
        return model_path
    
    async def _load_model(self, model_id: str) -> Tuple[Optional[Any], Optional[List[str]]]:
        """Carrega modelo salvo"""
        # Verificar cache
        if model_id in self.loaded_models:
            return self.loaded_models[model_id]
        
        try:
            # Path do modelo
            model_dir = self.models_dir / model_id
            latest_model_path = model_dir / "latest_model.joblib"
            latest_metadata_path = model_dir / "latest_metadata.json"
            
            if not latest_model_path.exists() or not latest_metadata_path.exists():
                self.logger.warning(f"Model {model_id} not found")
                return None, None
            
            # Carregar modelo
            model = joblib.load(latest_model_path)
            
            # Carregar metadata
            with open(latest_metadata_path, 'r') as f:
                metadata = json.load(f)
            
            feature_names = metadata.get("feature_names", [])
            
            # Adicionar ao cache
            self.loaded_models[model_id] = (model, feature_names)
            
            self.logger.info(f"Model {model_id} loaded successfully")
            return model, feature_names
            
        except Exception as e:
            self.logger.error(f"Error loading model {model_id}: {e}")
            return None, None
    
    async def _backup_model(self, model_id: str, model_path: Path, metadata_path: Path):
        """Cria backup do modelo"""
        try:
            backup_dir = self.models_dir / "backups" / model_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copiar arquivos
            import shutil
            shutil.copy2(model_path, backup_dir)
            shutil.copy2(metadata_path, backup_dir)
            
        except Exception as e:
            self.logger.warning(f"Failed to backup model {model_id}: {e}")
    
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
    
    def get_available_algorithms(self) -> List[str]:
        """Retorna algoritmos disponíveis"""
        return list(self.algorithms.keys())
    
    def get_algorithm_info(self, algorithm: str) -> Dict[str, Any]:
        """Obtém informações sobre algoritmo"""
        if algorithm not in self.algorithms:
            return {}
        
        algorithm_class = self.algorithms[algorithm]
        hyperparameters = self.default_hyperparameters.get(algorithm, {})
        
        return {
            "name": algorithm,
            "class": algorithm_class.__name__,
            "hyperparameters": hyperparameters,
            "supports_probability": hasattr(algorithm_class(), "predict_proba"),
            "supports_feature_importance": hasattr(algorithm_class(), "feature_importances_")
        }
    
    async def get_model_list(self) -> List[Dict[str, Any]]:
        """Lista modelos disponíveis"""
        models = []
        
        try:
            for model_dir in self.models_dir.iterdir():
                if model_dir.is_dir() and model_dir.name != "backups":
                    metadata_path = model_dir / "latest_metadata.json"
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        models.append({
                            "model_id": metadata.get("model_id"),
                            "timestamp": metadata.get("timestamp"),
                            "algorithm": metadata.get("algorithm"),
                            "metrics": metadata.get("metrics", {}),
                            "feature_count": len(metadata.get("feature_names", []))
                        })
            
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
        
        return models