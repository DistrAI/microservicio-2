"""
Random Forest - Predicción de Demanda
Predice cuántas unidades de un producto se venderán en el futuro
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import joblib
import os
from loguru import logger
from typing import Dict, List, Optional


class DemandPredictor:
    """Predictor de demanda usando Random Forest"""
    
    def __init__(self, model_path: str = "models/demand_model.pkl"):
        self.model_path = model_path
        self.model: Optional[RandomForestRegressor] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns = []
        
        # Crear directorio de modelos si no existe
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Cargar modelo si existe
        self.load_model()
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preparar features para el modelo"""
        
        # Crear features temporales
        df['fecha_pedido'] = pd.to_datetime(df['fecha_pedido'])
        df['mes'] = df['fecha_pedido'].dt.month
        df['dia_semana'] = df['fecha_pedido'].dt.dayofweek
        df['dia_mes'] = df['fecha_pedido'].dt.day
        df['semana_año'] = df['fecha_pedido'].dt.isocalendar().week
        
        # Features de tendencia
        df = df.sort_values('fecha_pedido')
        df['dias_desde_inicio'] = (df['fecha_pedido'] - df['fecha_pedido'].min()).dt.days
        
        # Features agregadas por producto
        df['ventas_acumuladas'] = df.groupby('producto_id')['cantidad'].cumsum()
        df['ventas_promedio_producto'] = df.groupby('producto_id')['cantidad'].transform('mean')
        
        # Features de precio
        if 'precio_unitario' in df.columns:
            df['gasto_total'] = df['cantidad'] * df['precio_unitario']
        
        return df
    
    def train(self, data: pd.DataFrame) -> Dict:
        """
        Entrenar modelo con datos históricos
        
        Args:
            data: DataFrame con columnas: producto_id, fecha_pedido, cantidad, precio_unitario
        
        Returns:
            Métricas de entrenamiento
        """
        logger.info("🎓 Iniciando entrenamiento de modelo de demanda...")
        
        # Preparar datos
        df = self.prepare_features(data.copy())
        
        # Seleccionar features
        self.feature_columns = [
            'producto_id', 'mes', 'dia_semana', 'dia_mes', 'semana_año',
            'dias_desde_inicio', 'ventas_acumuladas', 'ventas_promedio_producto'
        ]
        
        if 'precio_unitario' in df.columns:
            self.feature_columns.append('precio_unitario')
            if 'gasto_total' in df.columns:
                self.feature_columns.append('gasto_total')
        
        # Codificar variables categóricas
        if 'producto_id' in df.columns:
            self.label_encoders['producto_id'] = LabelEncoder()
            df['producto_id'] = self.label_encoders['producto_id'].fit_transform(df['producto_id'])
        
        # Preparar X e y
        X = df[self.feature_columns].fillna(0)
        y = df['cantidad']
        
        # Entrenar modelo
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X, y)
        
        # Calcular métricas
        train_score = self.model.score(X, y)
        predictions = self.model.predict(X)
        mse = np.mean((y - predictions) ** 2)
        mae = np.mean(np.abs(y - predictions))
        
        metrics = {
            'r2_score': train_score,
            'mse': mse,
            'mae': mae,
            'n_samples': len(X),
            'n_features': len(self.feature_columns),
            'trained_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Modelo entrenado - R²: {train_score:.3f}, MAE: {mae:.2f}")
        
        # Guardar modelo
        self.save_model()
        
        return metrics
    
    def predict(self, producto_id: int, periodo: str = "semana", 
                context_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Predecir demanda futura de un producto
        
        Args:
            producto_id: ID del producto
            periodo: "semana" o "mes"
            context_data: Datos históricos del producto (opcional)
        
        Returns:
            Predicción con intervalos de confianza
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train() primero.")
        
        # Crear features para predicción
        today = datetime.now()
        
        if periodo == "semana":
            fecha_prediccion = today + timedelta(days=7)
            dias_adelante = 7
        else:  # mes
            fecha_prediccion = today + timedelta(days=30)
            dias_adelante = 30
        
        # Preparar features
        features = {
            'producto_id': producto_id,
            'mes': fecha_prediccion.month,
            'dia_semana': fecha_prediccion.weekday(),
            'dia_mes': fecha_prediccion.day,
            'semana_año': fecha_prediccion.isocalendar()[1],
            'dias_desde_inicio': dias_adelante,
            'ventas_acumuladas': 0,
            'ventas_promedio_producto': 0
        }
        
        # Si hay datos de contexto, calcular features agregadas
        if context_data is not None and len(context_data) > 0:
            features['ventas_acumuladas'] = context_data['cantidad'].sum()
            features['ventas_promedio_producto'] = context_data['cantidad'].mean()
            
            if 'precio_unitario' in context_data.columns:
                features['precio_unitario'] = context_data['precio_unitario'].mean()
                features['gasto_total'] = features['ventas_promedio_producto'] * features['precio_unitario']
        
        # Codificar producto_id si es necesario
        if 'producto_id' in self.label_encoders:
            try:
                features['producto_id'] = self.label_encoders['producto_id'].transform([producto_id])[0]
            except ValueError:
                # Producto no visto en entrenamiento, usar valor por defecto
                features['producto_id'] = 0
        
        # Crear DataFrame para predicción
        X_pred = pd.DataFrame([features])[self.feature_columns].fillna(0)
        
        # Predecir
        prediction = self.model.predict(X_pred)[0]
        
        # Predecir con todos los árboles para calcular intervalo de confianza
        tree_predictions = np.array([tree.predict(X_pred)[0] for tree in self.model.estimators_])
        
        lower_bound = np.percentile(tree_predictions, 5)
        upper_bound = np.percentile(tree_predictions, 95)
        
        result = {
            'producto_id': producto_id,
            'periodo': periodo,
            'fecha_prediccion': fecha_prediccion.isoformat(),
            'cantidad_estimada': max(0, round(prediction, 2)),
            'intervalo_confianza': {
                'lower': max(0, round(lower_bound, 2)),
                'upper': round(upper_bound, 2)
            },
            'confianza': min(100, max(0, round((1 - (upper_bound - lower_bound) / max(prediction, 1)) * 100, 2)))
        }
        
        return result
    
    def predict_all_products(self, productos_ids: List[int], periodo: str = "semana") -> List[Dict]:
        """Predecir demanda para múltiples productos"""
        predictions = []
        
        for producto_id in productos_ids:
            try:
                pred = self.predict(producto_id, periodo)
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Error prediciendo producto {producto_id}: {e}")
        
        return predictions
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Obtener importancia de features"""
        if self.model is None:
            return {}
        
        importances = dict(zip(self.feature_columns, self.model.feature_importances_))
        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self):
        """Guardar modelo en disco"""
        model_data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'saved_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, self.model_path)
        logger.info(f"💾 Modelo guardado en {self.model_path}")
    
    def load_model(self) -> bool:
        """Cargar modelo desde disco"""
        if not os.path.exists(self.model_path):
            logger.info("📭 No hay modelo guardado")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.label_encoders = model_data['label_encoders']
            self.feature_columns = model_data['feature_columns']
            
            logger.info(f"✅ Modelo cargado desde {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            return False
