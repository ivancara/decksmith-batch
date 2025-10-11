"""
DeckSmith Batch Processing System
Infrastructure Layer - Deep Learning Engine Implementation
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import joblib

# TensorFlow imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers, callbacks
    from tensorflow.keras.utils import plot_model
    TENSORFLOW_AVAILABLE = True
except ImportError:
    tf = None
    keras = None
    layers = None
    models = None
    optimizers = None
    callbacks = None
    TENSORFLOW_AVAILABLE = False

# Scikit-learn para preprocessing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from ...application.interfaces import IMLEngine
from ...application.dto import MLTrainingRequestDTO, MLTrainingResultDTO, MLPredictionRequestDTO, MLPredictionResultDTO, MLFeatureVectorDTO, DeckDataDTO, CardDataDTO, MLTrainingResponseDTO
from ...domain.entities import MLModel, Card, Deck
from ..config.environment_config import EnvironmentAwareConfigManager


class TensorFlowDeepLearningEngine(IMLEngine):
    """Engine de Deep Learning usando TensorFlow/Keras"""
    
    def __init__(self, config_manager: EnvironmentAwareConfigManager):
        self.config = config_manager
        self.ml_config = config_manager.get_ml_config_typed()
        
        self.logger = logging.getLogger(__name__)
        
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is not available. Please install tensorflow>=2.13.0")
        
        # Configurar TensorFlow
        self._configure_tensorflow()
        
        # Diretórios
        self.models_dir = Path(self.ml_config.models_directory)
        self.data_dir = Path(self.ml_config.data_directory)
        self.temp_dir = Path(self.ml_config.temp_directory)
        
        # Criar diretórios se não existirem
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquiteturas disponíveis
        self.architectures = {
            "card_recommendation": self._create_card_recommendation_model,
            "deck_similarity": self._create_deck_similarity_model,
            "card_embedding": self._create_card_embedding_model,
            "meta_predictor": self._create_meta_predictor_model,
            "price_predictor": self._create_price_predictor_model,
            "synergy_detector": self._create_synergy_detector_model
        }
        
        # Cache de modelos carregados
        self.loaded_models: Dict[str, tf.keras.Model] = {}
        self.preprocessors: Dict[str, Any] = {}
    
    def _configure_tensorflow(self):
        """Configura TensorFlow baseado no ambiente"""
        tf_config = self.ml_config.tensorflow_config
        
        # Configurar GPU se disponível
        if tf_config.get("use_gpu", False) and tf.config.list_physical_devices('GPU'):
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                try:
                    # Permitir crescimento de memória GPU
                    if tf_config.get("memory_growth", True):
                        for gpu in gpus:
                            tf.config.experimental.set_memory_growth(gpu, True)
                    
                    # Mixed precision para performance
                    if tf_config.get("mixed_precision", True):
                        tf.keras.mixed_precision.set_global_policy('mixed_float16')
                    
                    self.logger.info(f"TensorFlow configured with {len(gpus)} GPU(s)")
                except RuntimeError as e:
                    self.logger.warning(f"GPU configuration failed: {e}")
        else:
            # Forçar CPU
            tf.config.set_visible_devices([], 'GPU')
            self.logger.info("TensorFlow configured for CPU only")
        
        # Configurar threading
        tf.config.threading.set_intra_op_parallelism_threads(0)
        tf.config.threading.set_inter_op_parallelism_threads(0)
    
    async def initialize(self) -> bool:
        """Inicializa engine de Deep Learning"""
        try:
            self.logger.info(f"TensorFlow version: {tf.__version__}")
            self.logger.info("Deep Learning engine initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Deep Learning engine: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Finaliza engine de Deep Learning"""
        try:
            # Limpar modelos da memória
            for model in self.loaded_models.values():
                del model
            self.loaded_models.clear()
            self.preprocessors.clear()
            
            # Limpar cache do TensorFlow
            tf.keras.backend.clear_session()
            
            # Limpar arquivos temporários
            if self.ml_config.temp_directory:
                await self._cleanup_temp_files()
            
            self.logger.info("Deep Learning engine cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup Deep Learning engine: {e}")
            return False
    
    async def train_model(self, request: MLTrainingRequestDTO) -> MLTrainingResultDTO:
        """Treina modelo de Deep Learning"""
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
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42,
                stratify=y if len(np.unique(y)) > 1 else None
            )
            
            # Criar modelo
            architecture = request.algorithm or "card_recommendation"
            model = await self._create_model(architecture, X_train.shape, len(np.unique(y_train)))
            
            if model is None:
                return MLTrainingResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message=f"Failed to create model architecture: {architecture}",
                    training_duration=0.0,
                    training_timestamp=training_start
                )
            
            # Configurar callbacks
            callbacks_list = self._create_callbacks(request.model_id)
            
            # Treinar modelo
            history = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=self.ml_config.epochs,
                batch_size=self.ml_config.batch_size,
                callbacks=callbacks_list,
                verbose=1 if self.config.is_development() else 0
            )
            
            # Avaliar modelo
            metrics = await self._evaluate_model(model, X_val, y_val, history)
            
            # Salvar modelo
            model_path = await self._save_model(request.model_id, model, feature_names, metrics, history)
            
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
                algorithm=architecture,
                training_history=self._history_to_dict(history)
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
        """Faz predições usando modelo de Deep Learning"""
        try:
            prediction_start = datetime.utcnow()
            
            # Carregar modelo
            model, feature_names = await self._load_model(request.model_id)
            
            if model is None:
                return MLPredictionResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message="Model not found or failed to load",
                    prediction_timestamp=prediction_start
                )
            
            # Preparar dados para predição
            X = await self._prepare_prediction_data(request.input_data, feature_names)
            
            if X is None:
                return MLPredictionResultDTO(
                    model_id=request.model_id,
                    success=False,
                    error_message="Failed to prepare prediction data",
                    prediction_timestamp=prediction_start
                )
            
            # Fazer predições
            prediction_probs = model.predict(X, verbose=0)
            predictions = np.argmax(prediction_probs, axis=1) if prediction_probs.shape[1] > 1 else (prediction_probs > 0.5).astype(int)
            
            # Preparar resultado
            results = []
            for i, (prediction, probs) in enumerate(zip(predictions, prediction_probs)):
                result = {
                    "prediction": int(prediction) if prediction_probs.shape[1] > 1 else float(prediction),
                    "probabilities": probs.tolist(),
                    "confidence": float(np.max(probs))
                }
                results.append(result)
            
            prediction_end = datetime.utcnow()
            inference_time = (prediction_end - prediction_start).total_seconds() * 1000  # ms
            
            return MLPredictionResultDTO(
                model_id=request.model_id,
                success=True,
                predictions=results,
                prediction_timestamp=prediction_start,
                inference_time_ms=int(inference_time)
            )
            
        except Exception as e:
            self.logger.error(f"Error making prediction with model {request.model_id}: {e}")
            return MLPredictionResultDTO(
                model_id=request.model_id,
                success=False,
                error_message=str(e),
                prediction_timestamp=datetime.utcnow()
            )
    
    async def generate_embeddings(self, model_id: str, data: List[Dict[str, Any]]) -> Optional[np.ndarray]:
        """Gera embeddings usando modelo treinado"""
        try:
            model, feature_names = await self._load_model(model_id)
            
            if model is None:
                return None
            
            # Preparar dados
            X = await self._prepare_prediction_data({"features": data}, feature_names)
            
            if X is None:
                return None
            
            # Obter embeddings da camada intermediária
            if hasattr(model, 'get_layer'):
                try:
                    # Tentar obter embeddings da camada de embedding
                    embedding_layer = model.get_layer('embedding_layer')
                    embedding_model = tf.keras.Model(inputs=model.input, outputs=embedding_layer.output)
                    embeddings = embedding_model.predict(X, verbose=0)
                    return embeddings
                except:
                    # Fallback: usar saída da penúltima camada
                    feature_model = tf.keras.Model(inputs=model.input, outputs=model.layers[-2].output)
                    embeddings = feature_model.predict(X, verbose=0)
                    return embeddings
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings with model {model_id}: {e}")
            return None
    
    async def _create_model(self, architecture: str, input_shape: tuple, num_classes: int) -> Optional[tf.keras.Model]:
        """Cria modelo baseado na arquitetura especificada"""
        if architecture not in self.architectures:
            self.logger.error(f"Unknown architecture: {architecture}")
            return None
        
        try:
            return self.architectures[architecture](input_shape, num_classes)
        except Exception as e:
            self.logger.error(f"Error creating model {architecture}: {e}")
            return None
    
    def _create_card_recommendation_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para recomendação de cartas"""
        model = models.Sequential([
            layers.Input(shape=input_shape[1:]),
            
            # Camadas de embedding e feature extraction
            layers.Dense(512, activation='relu', name='feature_layer_1'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(256, activation='relu', name='feature_layer_2'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(128, activation='relu', name='embedding_layer'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Camadas de classificação
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(num_classes, activation='softmax' if num_classes > 2 else 'sigmoid')
        ])
        
        optimizer = optimizers.Adam(learning_rate=self.ml_config.learning_rate)
        loss = 'sparse_categorical_crossentropy' if num_classes > 2 else 'binary_crossentropy'
        
        model.compile(
            optimizer=optimizer,
            loss=loss,
            metrics=['accuracy', 'precision', 'recall']
        )
        
        return model
    
    def _create_deck_similarity_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para similaridade entre decks"""
        input_layer = layers.Input(shape=input_shape[1:])
        
        # Encoder para deck embeddings
        x = layers.Dense(256, activation='relu')(input_layer)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        
        x = layers.Dense(128, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        
        # Embedding layer
        embedding = layers.Dense(64, activation='tanh', name='deck_embedding')(x)
        
        # Similarity prediction
        x = layers.Dense(32, activation='relu')(embedding)
        x = layers.Dropout(0.2)(x)
        output = layers.Dense(1, activation='sigmoid', name='similarity_score')(x)
        
        model = models.Model(inputs=input_layer, outputs=output)
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.ml_config.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy', 'mse']
        )
        
        return model
    
    def _create_card_embedding_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para embeddings de cartas (autoencoder)"""
        # Encoder
        input_layer = layers.Input(shape=input_shape[1:])
        
        # Encoder layers
        x = layers.Dense(512, activation='relu')(input_layer)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)
        
        x = layers.Dense(256, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)
        
        # Bottleneck (embedding layer)
        embedding = layers.Dense(128, activation='tanh', name='card_embedding')(x)
        
        # Decoder layers
        x = layers.Dense(256, activation='relu')(embedding)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)
        
        x = layers.Dense(512, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        
        # Output layer (reconstruction)
        output = layers.Dense(input_shape[1], activation='linear')(x)
        
        # Autoencoder model
        autoencoder = models.Model(inputs=input_layer, outputs=output)
        
        autoencoder.compile(
            optimizer=optimizers.Adam(learning_rate=self.ml_config.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        return autoencoder
    
    def _create_meta_predictor_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para predição de meta-game"""
        model = models.Sequential([
            layers.Input(shape=input_shape[1:]),
            
            # Feature extraction
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            # LSTM para análise temporal
            layers.Reshape((128, 1)),
            layers.LSTM(64, return_sequences=True),
            layers.LSTM(32),
            layers.Dropout(0.2),
            
            # Output layer
            layers.Dense(num_classes, activation='softmax' if num_classes > 2 else 'sigmoid')
        ])
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.ml_config.learning_rate),
            loss='sparse_categorical_crossentropy' if num_classes > 2 else 'binary_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _create_price_predictor_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para predição de preços"""
        model = models.Sequential([
            layers.Input(shape=input_shape[1:]),
            
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='linear')  # Regressão para preço
        ])
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.ml_config.learning_rate),
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        return model
    
    def _create_synergy_detector_model(self, input_shape: tuple, num_classes: int) -> tf.keras.Model:
        """Cria modelo para detecção de sinergias entre cartas"""
        # Input para duas cartas
        card_a_input = layers.Input(shape=(input_shape[1]//2,), name='card_a')
        card_b_input = layers.Input(shape=(input_shape[1]//2,), name='card_b')
        
        # Processamento individual de cada carta
        def process_card(card_input):
            x = layers.Dense(128, activation='relu')(card_input)
            x = layers.BatchNormalization()(x)
            x = layers.Dropout(0.2)(x)
            return layers.Dense(64, activation='relu')(x)
        
        card_a_features = process_card(card_a_input)
        card_b_features = process_card(card_b_input)
        
        # Combinar features das cartas
        combined = layers.Concatenate()([card_a_features, card_b_features])
        
        # Interaction layers
        x = layers.Dense(128, activation='relu')(combined)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(0.2)(x)
        
        # Output: sinergia score
        output = layers.Dense(1, activation='sigmoid', name='synergy_score')(x)
        
        model = models.Model(inputs=[card_a_input, card_b_input], outputs=output)
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.ml_config.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy', 'mse']
        )
        
        return model
    
    def _create_callbacks(self, model_id: str) -> List[tf.keras.callbacks.Callback]:
        """Cria callbacks para treinamento"""
        callbacks_list = []
        
        # Early stopping
        callbacks_list.append(
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=1 if self.config.is_development() else 0
            )
        )
        
        # Reduce learning rate on plateau
        callbacks_list.append(
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1 if self.config.is_development() else 0
            )
        )
        
        # Model checkpoint
        checkpoint_path = self.models_dir / model_id / "checkpoints"
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        callbacks_list.append(
            callbacks.ModelCheckpoint(
                filepath=str(checkpoint_path / "best_model.h5"),
                monitor='val_loss',
                save_best_only=True,
                save_weights_only=False,
                verbose=1 if self.config.is_development() else 0
            )
        )
        
        # CSV Logger para histórico
        callbacks_list.append(
            callbacks.CSVLogger(
                filename=str(self.models_dir / model_id / "training_log.csv"),
                append=True
            )
        )
        
        return callbacks_list
    
    async def _prepare_training_data(self, request: MLTrainingRequestDTO) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[str]]]:
        """Prepara dados para treinamento de Deep Learning"""
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
            
            # Preprocessamento específico para Deep Learning
            X, feature_names = await self._preprocess_features_for_dl(X_df, request.model_id)
            
            return X, y, feature_names
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return None, None, None
    
    async def _preprocess_features_for_dl(self, df: pd.DataFrame, model_id: str) -> Tuple[np.ndarray, List[str]]:
        """Preprocessamento específico para Deep Learning"""
        feature_columns = []
        processed_features = []
        
        # Salvar preprocessors para uso futuro
        if model_id not in self.preprocessors:
            self.preprocessors[model_id] = {}
        
        for column in df.columns:
            if df[column].dtype == 'object':
                # Coluna categórica
                if df[column].nunique() > 50:
                    # Muitas categorias - usar embedding
                    le = LabelEncoder()
                    encoded = le.fit_transform(df[column].fillna('unknown'))
                    
                    # Salvar encoder
                    self.preprocessors[model_id][f"{column}_encoder"] = le
                    
                    processed_features.append(encoded.reshape(-1, 1))
                    feature_columns.append(f"{column}_encoded")
                else:
                    # Poucas categorias - usar one-hot
                    ohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                    encoded = ohe.fit_transform(df[column].fillna('unknown').values.reshape(-1, 1))
                    
                    # Salvar encoder
                    self.preprocessors[model_id][f"{column}_onehot"] = ohe
                    
                    processed_features.append(encoded)
                    feature_columns.extend([f"{column}_ohe_{i}" for i in range(encoded.shape[1])])
            else:
                # Coluna numérica
                values = pd.to_numeric(df[column], errors='coerce').fillna(0).values
                
                # Normalizar
                scaler = StandardScaler()
                normalized = scaler.fit_transform(values.reshape(-1, 1))
                
                # Salvar scaler
                self.preprocessors[model_id][f"{column}_scaler"] = scaler
                
                processed_features.append(normalized)
                feature_columns.append(f"{column}_normalized")
        
        # Concatenar todas as features
        if processed_features:
            X = np.concatenate(processed_features, axis=1)
        else:
            X = np.array([]).reshape(len(df), 0)
        
        return X, feature_columns
    
    async def _prepare_prediction_data(self, input_data: Dict[str, Any], feature_names: List[str]) -> Optional[np.ndarray]:
        """Prepara dados para predição"""
        try:
            # Implementar preprocessamento usando preprocessors salvos
            # Esta é uma versão simplificada - seria expandida para usar os preprocessors salvos
            
            if isinstance(input_data, dict) and 'features' in input_data:
                df = pd.DataFrame(input_data['features'])
            else:
                df = pd.DataFrame([input_data])
            
            # Aplicar mesmo preprocessamento do treinamento
            # (implementação seria mais complexa na versão real)
            X = df.select_dtypes(include=[np.number]).fillna(0).values
            
            return X
            
        except Exception as e:
            self.logger.error(f"Error preparing prediction data: {e}")
            return None
    
    async def _evaluate_model(self, model: tf.keras.Model, X_test: np.ndarray, 
                             y_test: np.ndarray, history: tf.keras.callbacks.History) -> Dict[str, float]:
        """Avalia modelo de Deep Learning"""
        # Predições
        y_pred_probs = model.predict(X_test, verbose=0)
        
        if y_pred_probs.shape[1] > 1:
            # Classificação multi-classe
            y_pred = np.argmax(y_pred_probs, axis=1)
        else:
            # Classificação binária ou regressão
            y_pred = (y_pred_probs > 0.5).astype(int).flatten() if y_pred_probs.shape[1] == 1 else y_pred_probs.flatten()
        
        # Métricas básicas
        metrics = {}
        
        try:
            if len(np.unique(y_test)) > 1:  # Classificação
                metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
                metrics["precision"] = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
                metrics["recall"] = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
                metrics["f1_score"] = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
                
                # AUC para classificação binária
                if len(np.unique(y_test)) == 2:
                    try:
                        auc = roc_auc_score(y_test, y_pred_probs[:, 1] if y_pred_probs.shape[1] > 1 else y_pred_probs.flatten())
                        metrics["auc"] = float(auc)
                    except:
                        pass
            else:  # Regressão
                from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
                metrics["mse"] = float(mean_squared_error(y_test, y_pred))
                metrics["mae"] = float(mean_absolute_error(y_test, y_pred))
                metrics["r2"] = float(r2_score(y_test, y_pred))
        except Exception as e:
            self.logger.warning(f"Error calculating metrics: {e}")
        
        # Métricas do histórico de treinamento
        if history and history.history:
            final_epoch = len(history.history['loss']) - 1
            metrics["final_loss"] = float(history.history['loss'][final_epoch])
            metrics["final_val_loss"] = float(history.history['val_loss'][final_epoch])
            
            if 'accuracy' in history.history:
                metrics["final_accuracy"] = float(history.history['accuracy'][final_epoch])
                metrics["final_val_accuracy"] = float(history.history['val_accuracy'][final_epoch])
        
        return metrics
    
    async def _save_model(self, model_id: str, model: tf.keras.Model, feature_names: List[str], 
                         metrics: Dict[str, float], history: tf.keras.callbacks.History) -> Path:
        """Salva modelo de Deep Learning"""
        # Criar timestamp para versionamento
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Diretório do modelo
        model_dir = self.models_dir / model_id
        model_dir.mkdir(exist_ok=True)
        
        # Paths dos arquivos
        model_path = model_dir / f"model_{timestamp}.h5"
        weights_path = model_dir / f"weights_{timestamp}.h5"
        metadata_path = model_dir / f"metadata_{timestamp}.json"
        history_path = model_dir / f"history_{timestamp}.json"
        
        latest_model_path = model_dir / "latest_model.h5"
        latest_metadata_path = model_dir / "latest_metadata.json"
        
        # Salvar modelo completo
        model.save(model_path)
        model.save(latest_model_path)
        
        # Salvar apenas pesos
        model.save_weights(weights_path)
        
        # Salvar preprocessors
        preprocessors_path = model_dir / f"preprocessors_{timestamp}.joblib"
        if model_id in self.preprocessors:
            joblib.dump(self.preprocessors[model_id], preprocessors_path)
        
        # Salvar metadata
        metadata = {
            "model_id": model_id,
            "timestamp": timestamp,
            "feature_names": feature_names,
            "metrics": metrics,
            "model_path": str(model_path),
            "weights_path": str(weights_path),
            "preprocessors_path": str(preprocessors_path),
            "architecture": model.name,
            "total_params": model.count_params(),
            "trainable_params": sum([tf.keras.backend.count_params(w) for w in model.trainable_weights]),
            "model_summary": self._get_model_summary(model),
            "tensorflow_version": tf.__version__,
            "training_config": {
                "epochs": self.ml_config.epochs,
                "batch_size": self.ml_config.batch_size,
                "learning_rate": self.ml_config.learning_rate,
            }
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        with open(latest_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Salvar histórico de treinamento
        if history and history.history:
            history_dict = {k: [float(v) for v in values] for k, values in history.history.items()}
            
            with open(history_path, 'w') as f:
                json.dump(history_dict, f, indent=2)
        
        self.logger.info(f"Deep Learning model {model_id} saved successfully")
        return model_path
    
    async def _load_model(self, model_id: str) -> Tuple[Optional[tf.keras.Model], Optional[List[str]]]:
        """Carrega modelo de Deep Learning"""
        # Verificar cache
        if model_id in self.loaded_models:
            # Carregar metadata para feature names
            metadata_path = self.models_dir / model_id / "latest_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                return self.loaded_models[model_id], metadata.get("feature_names", [])
        
        try:
            # Path do modelo
            model_dir = self.models_dir / model_id
            latest_model_path = model_dir / "latest_model.h5"
            latest_metadata_path = model_dir / "latest_metadata.json"
            
            if not latest_model_path.exists() or not latest_metadata_path.exists():
                self.logger.warning(f"Model {model_id} not found")
                return None, None
            
            # Carregar modelo
            model = tf.keras.models.load_model(latest_model_path)
            
            # Carregar metadata
            with open(latest_metadata_path, 'r') as f:
                metadata = json.load(f)
            
            feature_names = metadata.get("feature_names", [])
            
            # Carregar preprocessors
            preprocessors_path = model_dir / "preprocessors_latest.joblib"
            if preprocessors_path.exists():
                self.preprocessors[model_id] = joblib.load(preprocessors_path)
            
            # Adicionar ao cache
            self.loaded_models[model_id] = model
            
            self.logger.info(f"Deep Learning model {model_id} loaded successfully")
            return model, feature_names
            
        except Exception as e:
            self.logger.error(f"Error loading model {model_id}: {e}")
            return None, None
    
    def _get_model_summary(self, model: tf.keras.Model) -> str:
        """Obtém resumo do modelo como string"""
        try:
            import io
            import sys
            
            # Capturar output do summary
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            
            model.summary()
            
            sys.stdout = old_stdout
            return buffer.getvalue()
        except:
            return "Model summary not available"
    
    def _history_to_dict(self, history: tf.keras.callbacks.History) -> Dict[str, List[float]]:
        """Converte histórico de treinamento para dict"""
        if not history or not history.history:
            return {}
        
        return {k: [float(v) for v in values] for k, values in history.history.items()}
    
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
    
    async def prepare_dataset(
        self,
        deck_data: List[DeckDataDTO],
        target_variable: str
    ) -> List[MLFeatureVectorDTO]:
        """Prepara dataset para treinamento"""
        try:
            features = []
            for deck in deck_data:
                # Criar vetor de features a partir dos dados do deck
                feature_vector = MLFeatureVectorDTO(
                    deck_id=deck.nome,  # Usar nome como ID
                    numeric_features={
                        "total_cartas": float(deck.total_cartas),
                        "custo_medio_mana": deck.custo_medio_mana or 0.0,
                        "cores_count": float(len(deck.cores))
                    },
                    categorical_features={
                        "formato": deck.formato,
                        "comandante": deck.comandante or "none"
                    },
                    boolean_features={
                        "tem_comandante": deck.comandante is not None
                    },
                    array_features={
                        "cores": [str(c) for c in deck.cores],  # Converter para string
                        "curva_mana": [float(deck.curva_mana.get(i, 0)) for i in range(10)]
                    },
                    target=getattr(deck, target_variable, 0) if hasattr(deck, target_variable) else 0
                )
                features.append(feature_vector)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error preparing dataset: {e}")
            return []
    
    async def save_model(self, model_id: str, file_path: str) -> bool:
        """Salva modelo treinado em arquivo"""
        try:
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                model.save(file_path)
                self.logger.info(f"Model {model_id} saved to {file_path}")
                return True
            else:
                self.logger.error(f"Model {model_id} not found")
                return False
        except Exception as e:
            self.logger.error(f"Error saving model {model_id}: {e}")
            return False
    
    async def load_model(self, file_path: str) -> str:
        """Carrega modelo de arquivo"""
        try:
            if not TENSORFLOW_AVAILABLE:
                self.logger.error("TensorFlow not available")
                return ""
            
            model = tf.keras.models.load_model(file_path)
            model_id = f"loaded_{int(datetime.utcnow().timestamp())}"
            
            self.loaded_models[model_id] = model
            
            self.logger.info(f"Model loaded from {file_path} as {model_id}")
            return model_id
            
        except Exception as e:
            self.logger.error(f"Error loading model from {file_path}: {e}")
            return ""
    
    def get_available_architectures(self) -> List[str]:
        """Retorna arquiteturas disponíveis"""
        return list(self.architectures.keys())
    
    def get_architecture_info(self, architecture: str) -> Dict[str, Any]:
        """Obtém informações sobre arquitetura"""
        if architecture not in self.architectures:
            return {}
        
        return {
            "name": architecture,
            "type": "deep_learning",
            "framework": "tensorflow",
            "supports_gpu": True,
            "supports_embeddings": True,
            "supports_attention": architecture in ["meta_predictor"],
            "supports_sequences": architecture in ["meta_predictor"]
        }
    
    async def get_model_list(self) -> List[Dict[str, Any]]:
        """Lista modelos de Deep Learning disponíveis"""
        models = []
        
        try:
            for model_dir in self.models_dir.iterdir():
                if model_dir.is_dir():
                    metadata_path = model_dir / "latest_metadata.json"
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        models.append({
                            "model_id": metadata.get("model_id"),
                            "timestamp": metadata.get("timestamp"),
                            "architecture": metadata.get("architecture"),
                            "total_params": metadata.get("total_params"),
                            "trainable_params": metadata.get("trainable_params"),
                            "metrics": metadata.get("metrics", {}),
                            "feature_count": len(metadata.get("feature_names", [])),
                            "tensorflow_version": metadata.get("tensorflow_version"),
                            "model_type": "deep_learning"
                        })
            
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
        
        return models