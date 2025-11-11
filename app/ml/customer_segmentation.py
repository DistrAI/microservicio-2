"""
K-Means - Segmentación de Clientes
Agrupa clientes en segmentos basados en comportamiento de compra
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import joblib
import os
from loguru import logger
from typing import Dict, List, Optional


class CustomerSegmentation:
    """Segmentación de clientes usando K-Means"""
    
    def __init__(self, model_path: str = "models/segmentation_model.pkl"):
        self.model_path = model_path
        self.model: Optional[KMeans] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_columns = []
        self.segment_labels = {}
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        self.load_model()
    
    def prepare_customer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preparar features de clientes para segmentación
        
        Input: DataFrame con pedidos (cliente_id, fecha_pedido, total, etc.)
        Output: DataFrame con features agregadas por cliente
        """
        
        # Agregar por cliente
        customer_features = df.groupby('cliente_id').agg({
            'id': 'count',  # Número de pedidos
            'total': ['sum', 'mean', 'std'],  # Gastos
            'fecha_pedido': ['min', 'max']  # Fechas
        }).reset_index()
        
        # Aplanar nombres de columnas
        customer_features.columns = ['cliente_id', 'num_pedidos', 'gasto_total', 
                                     'gasto_promedio', 'gasto_std', 'primera_compra', 'ultima_compra']
        
        # Features temporales
        customer_features['primera_compra'] = pd.to_datetime(customer_features['primera_compra'])
        customer_features['ultima_compra'] = pd.to_datetime(customer_features['ultima_compra'])
        
        hoy = datetime.now()
        customer_features['dias_desde_primera_compra'] = (hoy - customer_features['primera_compra']).dt.days
        customer_features['dias_desde_ultima_compra'] = (hoy - customer_features['ultima_compra']).dt.days
        customer_features['dias_cliente_activo'] = (customer_features['ultima_compra'] - customer_features['primera_compra']).dt.days
        
        # Frecuencia de compra
        customer_features['frecuencia_compra'] = customer_features['num_pedidos'] / (customer_features['dias_cliente_activo'] + 1)
        
        # Rellenar NaN
        customer_features['gasto_std'] = customer_features['gasto_std'].fillna(0)
        customer_features['frecuencia_compra'] = customer_features['frecuencia_compra'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # RFM: Recency, Frequency, Monetary (usando rank para evitar problemas con duplicados)
        try:
            # Recency: menor es mejor (invertir escala)
            customer_features['recency_score'] = 6 - pd.qcut(customer_features['dias_desde_ultima_compra'], 
                                                              q=5, labels=False, duplicates='drop')
        except ValueError:
            # Si falla qcut (muy pocos valores únicos), usar rank
            customer_features['recency_score'] = customer_features['dias_desde_ultima_compra'].rank(method='dense', ascending=True)
            customer_features['recency_score'] = (customer_features['recency_score'] / customer_features['recency_score'].max() * 5).round()
        
        try:
            # Frequency: mayor es mejor
            customer_features['frequency_score'] = pd.qcut(customer_features['num_pedidos'], 
                                                            q=5, labels=False, duplicates='drop') + 1
        except ValueError:
            customer_features['frequency_score'] = customer_features['num_pedidos'].rank(method='dense', ascending=False)
            customer_features['frequency_score'] = (customer_features['frequency_score'] / customer_features['frequency_score'].max() * 5).round()
        
        try:
            # Monetary: mayor es mejor
            customer_features['monetary_score'] = pd.qcut(customer_features['gasto_total'], 
                                                           q=5, labels=False, duplicates='drop') + 1
        except ValueError:
            customer_features['monetary_score'] = customer_features['gasto_total'].rank(method='dense', ascending=False)
            customer_features['monetary_score'] = (customer_features['monetary_score'] / customer_features['monetary_score'].max() * 5).round()
        
        # Asegurar que los scores estén en rango 1-5
        customer_features['recency_score'] = customer_features['recency_score'].clip(1, 5).fillna(3)
        customer_features['frequency_score'] = customer_features['frequency_score'].clip(1, 5).fillna(3)
        customer_features['monetary_score'] = customer_features['monetary_score'].clip(1, 5).fillna(3)
        
        customer_features['rfm_score'] = (customer_features['recency_score'] + 
                                          customer_features['frequency_score'] + 
                                          customer_features['monetary_score'])
        
        return customer_features
    
    def train(self, data: pd.DataFrame, n_clusters: int = 4) -> Dict:
        """
        Entrenar modelo de segmentación
        
        Args:
            data: DataFrame con pedidos
            n_clusters: Número de segmentos a crear
        
        Returns:
            Métricas y características de cada segmento
        """
        logger.info(f"🎓 Iniciando segmentación con {n_clusters} clusters...")
        
        # Preparar features
        customer_df = self.prepare_customer_features(data.copy())
        
        # Seleccionar features para clustering
        self.feature_columns = [
            'num_pedidos', 'gasto_total', 'gasto_promedio',
            'dias_desde_ultima_compra', 'frecuencia_compra',
            'recency_score', 'frequency_score', 'monetary_score', 'rfm_score'
        ]
        
        X = customer_df[self.feature_columns].fillna(0)
        
        # Escalar features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Entrenar K-Means
        self.model = KMeans(
            n_clusters=n_clusters,
            init='k-means++',
            n_init=10,
            max_iter=300,
            random_state=42
        )
        
        customer_df['cluster'] = self.model.fit_predict(X_scaled)
        
        # Analizar cada cluster y asignar etiquetas
        self.segment_labels = self._label_segments(customer_df)
        
        # Calcular métricas
        inertia = self.model.inertia_
        silhouette = self._calculate_silhouette_simple(X_scaled, customer_df['cluster'])
        
        # Estadísticas por segmento
        segment_stats = []
        for cluster_id in range(n_clusters):
            cluster_data = customer_df[customer_df['cluster'] == cluster_id]
            
            stats = {
                'cluster_id': int(cluster_id),
                'label': self.segment_labels.get(cluster_id, f'Segmento {cluster_id}'),
                'size': len(cluster_data),
                'percentage': round(len(cluster_data) / len(customer_df) * 100, 2),
                'avg_orders': round(cluster_data['num_pedidos'].mean(), 2),
                'avg_spend': round(cluster_data['gasto_total'].mean(), 2),
                'avg_frequency': round(cluster_data['frecuencia_compra'].mean(), 4),
                'avg_recency_days': round(cluster_data['dias_desde_ultima_compra'].mean(), 2)
            }
            segment_stats.append(stats)
        
        metrics = {
            'n_clusters': n_clusters,
            'n_customers': len(customer_df),
            'inertia': inertia,
            'silhouette_score': silhouette,
            'segments': segment_stats,
            'trained_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Segmentación completada - {n_clusters} segmentos, Silhouette: {silhouette:.3f}")
        
        # Guardar modelo
        self.save_model()
        
        return metrics
    
    def _label_segments(self, customer_df: pd.DataFrame) -> Dict[int, str]:
        """Asignar etiquetas descriptivas a cada segmento"""
        labels = {}
        
        for cluster_id in customer_df['cluster'].unique():
            cluster_data = customer_df[customer_df['cluster'] == cluster_id]
            
            avg_recency = cluster_data['dias_desde_ultima_compra'].mean()
            avg_frequency = cluster_data['num_pedidos'].mean()
            avg_monetary = cluster_data['gasto_total'].mean()
            avg_rfm = cluster_data['rfm_score'].mean()
            
            # Lógica de etiquetado
            if avg_rfm >= 12:
                labels[cluster_id] = "Champions (Mejores Clientes)"
            elif avg_rfm >= 9 and avg_recency < 60:
                labels[cluster_id] = "Clientes Leales"
            elif avg_frequency >= 5 and avg_recency > 90:
                labels[cluster_id] = "En Riesgo de Abandono"
            elif avg_recency < 30:
                labels[cluster_id] = "Clientes Recientes"
            elif avg_frequency <= 2:
                labels[cluster_id] = "Clientes Ocasionales"
            else:
                labels[cluster_id] = f"Segmento {cluster_id}"
        
        return labels
    
    def _calculate_silhouette_simple(self, X, labels) -> float:
        """Cálculo simplificado del coeficiente de silueta"""
        try:
            from sklearn.metrics import silhouette_score
            return silhouette_score(X, labels)
        except:
            # Si falla, retornar valor aproximado
            return 0.5
    
    def predict(self, customer_data: pd.DataFrame) -> List[Dict]:
        """
        Asignar clientes a segmentos
        
        Args:
            customer_data: DataFrame con datos de clientes (mismo formato que train)
        
        Returns:
            Lista de clientes con su segmento asignado
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado. Ejecuta train() primero.")
        
        # Preparar features
        customer_df = self.prepare_customer_features(customer_data.copy())
        
        X = customer_df[self.feature_columns].fillna(0)
        X_scaled = self.scaler.transform(X)
        
        # Predecir clusters
        clusters = self.model.predict(X_scaled)
        customer_df['cluster'] = clusters
        
        # Formatear resultados
        results = []
        for _, row in customer_df.iterrows():
            cluster_id = int(row['cluster'])
            results.append({
                'cliente_id': int(row['cliente_id']),
                'cluster_id': cluster_id,
                'segment_label': self.segment_labels.get(cluster_id, f'Segmento {cluster_id}'),
                'num_pedidos': int(row['num_pedidos']),
                'gasto_total': round(row['gasto_total'], 2),
                'gasto_promedio': round(row['gasto_promedio'], 2),
                'dias_desde_ultima_compra': int(row['dias_desde_ultima_compra']),
                'rfm_score': round(row['rfm_score'], 2)
            })
        
        return results
    
    def get_segment_details(self, cluster_id: int, customer_data: pd.DataFrame) -> Dict:
        """Obtener detalles de un segmento específico"""
        predictions = self.predict(customer_data)
        segment_customers = [p for p in predictions if p['cluster_id'] == cluster_id]
        
        if not segment_customers:
            return {'error': 'Segmento no encontrado'}
        
        return {
            'cluster_id': cluster_id,
            'label': self.segment_labels.get(cluster_id, f'Segmento {cluster_id}'),
            'size': len(segment_customers),
            'customers': segment_customers[:10],  # Primeros 10
            'avg_metrics': {
                'avg_orders': round(np.mean([c['num_pedidos'] for c in segment_customers]), 2),
                'avg_spend': round(np.mean([c['gasto_total'] for c in segment_customers]), 2),
                'avg_recency_days': round(np.mean([c['dias_desde_ultima_compra'] for c in segment_customers]), 2)
            }
        }
    
    def save_model(self):
        """Guardar modelo en disco"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'segment_labels': self.segment_labels,
            'saved_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, self.model_path)
        logger.info(f"💾 Modelo de segmentación guardado en {self.model_path}")
    
    def load_model(self) -> bool:
        """Cargar modelo desde disco"""
        if not os.path.exists(self.model_path):
            logger.info("📭 No hay modelo de segmentación guardado")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.segment_labels = model_data['segment_labels']
            
            logger.info(f"✅ Modelo de segmentación cargado desde {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            return False
