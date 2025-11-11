"""
Q-Learning - Optimización de Rutas de Entrega
Encuentra rutas óptimas minimizando distancia y tiempo
"""

import numpy as np
import pandas as pd
from datetime import datetime
import joblib
import os
from loguru import logger
from typing import Dict, List, Tuple, Optional
import json


class RouteOptimizer:
    """Optimizador de rutas usando Q-Learning"""
    
    def __init__(self, model_path: str = "models/route_model.pkl"):
        self.model_path = model_path
        self.q_table: Optional[np.ndarray] = None
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1  # Para exploración
        self.episodes_trained = 0
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        self.load_model()
    
    def calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calcular distancia euclidiana entre dos puntos (lat, lon)"""
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        # Fórmula de Haversine simplificada
        R = 6371  # Radio de la Tierra en km
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat / 2) ** 2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def build_distance_matrix(self, locations: List[Dict]) -> np.ndarray:
        """
        Construir matriz de distancias entre ubicaciones
        
        Args:
            locations: Lista de dict con 'lat' y 'lon'
        
        Returns:
            Matriz de distancias n x n
        """
        n = len(locations)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_matrix[i][j] = self.calculate_distance(
                        (locations[i]['lat'], locations[i]['lon']),
                        (locations[j]['lat'], locations[j]['lon'])
                    )
        
        return distance_matrix
    
    def train(self, historical_routes: List[Dict], episodes: int = 1000) -> Dict:
        """
        Entrenar el agente de Q-Learning con rutas históricas
        
        Args:
            historical_routes: Lista de rutas con formato:
                {
                    'locations': [{'id': int, 'lat': float, 'lon': float}, ...],
                    'actual_route': [0, 2, 1, 3, ...]  # Orden visitado
                }
            episodes: Número de episodios de entrenamiento
        
        Returns:
            Métricas de entrenamiento
        """
        logger.info(f"🎓 Iniciando entrenamiento Q-Learning ({episodes} episodios)...")
        
        if not historical_routes:
            logger.warning("⚠️  No hay rutas históricas, usando entrenamiento sintético")
            # Generar datos sintéticos para demostración
            historical_routes = self._generate_synthetic_routes(10)
        
        total_rewards = []
        
        # Encontrar el tamaño máximo de ubicaciones
        max_locations = max(len(route['locations']) for route in historical_routes)
        
        # Inicializar Q-table con el tamaño máximo
        if self.q_table is None:
            self.q_table = np.zeros((max_locations, max_locations))
        elif self.q_table.shape[0] < max_locations:
            # Expandir Q-table si es necesario
            old_size = self.q_table.shape[0]
            new_q_table = np.zeros((max_locations, max_locations))
            new_q_table[:old_size, :old_size] = self.q_table
            self.q_table = new_q_table
        
        for episode in range(episodes):
            # Seleccionar ruta aleatoria para entrenar
            route_data = historical_routes[episode % len(historical_routes)]
            locations = route_data['locations']
            n_locations = len(locations)
            
            # Construir matriz de distancias
            distance_matrix = self.build_distance_matrix(locations)
            
            # Simular episodio
            current_location = 0  # Siempre empezar desde la base (índice 0)
            visited = [current_location]
            total_reward = 0
            
            while len(visited) < n_locations:
                # Seleccionar siguiente acción (ubicación)
                if np.random.random() < self.epsilon:
                    # Exploración: acción aleatoria
                    unvisited = [i for i in range(n_locations) if i not in visited]
                    next_location = np.random.choice(unvisited)
                else:
                    # Explotación: mejor acción según Q-table
                    q_values = self.q_table[current_location, :n_locations].copy()
                    for v in visited:
                        if v < len(q_values):
                            q_values[v] = -np.inf  # No revisar ubicaciones ya visitadas
                    
                    # Encontrar siguiente ubicación no visitada
                    unvisited = [i for i in range(n_locations) if i not in visited]
                    if len(unvisited) > 0:
                        # Elegir la mejor entre las no visitadas
                        best_unvisited_idx = np.argmax([q_values[i] for i in unvisited])
                        next_location = unvisited[best_unvisited_idx]
                    else:
                        # Fallback: no debería pasar, pero por seguridad
                        break
                
                # Calcular recompensa (negativa de la distancia)
                reward = -distance_matrix[current_location][next_location]
                
                # Actualizar Q-table
                if len(visited) < n_locations - 1:
                    # No es el último paso
                    future_q = np.max(self.q_table[next_location, :n_locations])
                else:
                    # Último paso, volver a la base
                    future_q = -distance_matrix[next_location][0]
                
                # Asegurar que los índices estén dentro de rango
                if current_location < self.q_table.shape[0] and next_location < self.q_table.shape[1]:
                    self.q_table[current_location, next_location] = (
                        (1 - self.learning_rate) * self.q_table[current_location, next_location] +
                        self.learning_rate * (reward + self.discount_factor * future_q)
                    )
                
                total_reward += reward
                visited.append(next_location)
                current_location = next_location
            
            total_rewards.append(total_reward)
        
        self.episodes_trained += episodes
        
        # Calcular métricas
        avg_reward = np.mean(total_rewards[-100:])  # Últimos 100 episodios
        improvement = (total_rewards[-1] - total_rewards[0]) / abs(total_rewards[0]) * 100 if total_rewards[0] != 0 else 0
        
        metrics = {
            'episodes_trained': self.episodes_trained,
            'avg_reward_last_100': round(avg_reward, 2),
            'improvement_pct': round(improvement, 2),
            'final_reward': round(total_rewards[-1], 2),
            'trained_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Entrenamiento completado - Recompensa promedio: {avg_reward:.2f}")
        
        # Guardar modelo
        self.save_model()
        
        return metrics
    
    def optimize_route(self, locations: List[Dict]) -> Dict:
        """
        Optimizar ruta de entrega para un conjunto de ubicaciones
        
        Args:
            locations: Lista de ubicaciones con formato:
                [
                    {'id': 1, 'lat': -12.04, 'lon': -77.03, 'direccion': 'Calle X'},
                    {'id': 2, 'lat': -12.05, 'lon': -77.04, 'direccion': 'Calle Y'},
                    ...
                ]
        
        Returns:
            Ruta optimizada con orden de visitas y métricas
        """
        if not locations:
            return {'error': 'No hay ubicaciones para optimizar'}
        
        n_locations = len(locations)
        
        # Si el modelo no está entrenado, usar greedy algorithm
        if self.q_table is None:
            logger.warning("⚠️  Modelo no entrenado, usando algoritmo greedy")
            return self._greedy_route(locations)
        
        # Construir matriz de distancias
        distance_matrix = self.build_distance_matrix(locations)
        
        # Generar ruta usando política aprendida
        current_location = 0  # Empezar desde la base
        visited = [current_location]
        total_distance = 0
        
        while len(visited) < n_locations:
            # Seleccionar mejor siguiente ubicación según Q-table
            if current_location < self.q_table.shape[0]:
                q_values = self.q_table[current_location].copy()
                q_values[visited] = -np.inf
                next_location = np.argmax(q_values) if np.max(q_values) > -np.inf else np.random.choice([i for i in range(n_locations) if i not in visited])
            else:
                # Si la ubicación está fuera de la Q-table, usar greedy
                unvisited = [i for i in range(n_locations) if i not in visited]
                distances = [distance_matrix[current_location][i] for i in unvisited]
                next_location = unvisited[np.argmin(distances)]
            
            total_distance += distance_matrix[current_location][next_location]
            visited.append(next_location)
            current_location = next_location
        
        # Volver a la base
        total_distance += distance_matrix[current_location][0]
        
        # Calcular tiempo estimado (asumiendo velocidad promedio de 30 km/h)
        estimated_time_hours = total_distance / 30
        estimated_time_minutes = estimated_time_hours * 60
        
        # Formatear ruta
        route_order = [
            {
                'orden': i + 1,
                'ubicacion_id': locations[loc_idx]['id'],
                'direccion': locations[loc_idx].get('direccion', f'Ubicación {loc_idx}'),
                'latitud': locations[loc_idx]['lat'],
                'longitud': locations[loc_idx]['lon'],
                'distancia_desde_anterior_km': round(
                    distance_matrix[visited[i-1]][loc_idx] if i > 0 else 0, 2
                )
            }
            for i, loc_idx in enumerate(visited)
        ]
        
        return {
            'ruta_optimizada': route_order,
            'total_ubicaciones': n_locations,
            'distancia_total_km': round(total_distance, 2),
            'tiempo_estimado_minutos': round(estimated_time_minutes, 2),
            'optimizado_con': 'Q-Learning' if self.q_table is not None else 'Greedy',
            'fecha_calculo': datetime.now().isoformat()
        }
    
    def _greedy_route(self, locations: List[Dict]) -> Dict:
        """Algoritmo greedy simple como fallback"""
        distance_matrix = self.build_distance_matrix(locations)
        n_locations = len(locations)
        
        current = 0
        visited = [current]
        total_distance = 0
        
        while len(visited) < n_locations:
            unvisited = [i for i in range(n_locations) if i not in visited]
            distances = [distance_matrix[current][i] for i in unvisited]
            next_loc = unvisited[np.argmin(distances)]
            
            total_distance += distance_matrix[current][next_loc]
            visited.append(next_loc)
            current = next_loc
        
        total_distance += distance_matrix[current][0]
        
        route_order = [
            {
                'orden': i + 1,
                'ubicacion_id': locations[loc_idx]['id'],
                'direccion': locations[loc_idx].get('direccion', f'Ubicación {loc_idx}'),
                'latitud': locations[loc_idx]['lat'],
                'longitud': locations[loc_idx]['lon'],
                'distancia_desde_anterior_km': round(
                    distance_matrix[visited[i-1]][loc_idx] if i > 0 else 0, 2
                )
            }
            for i, loc_idx in enumerate(visited)
        ]
        
        return {
            'ruta_optimizada': route_order,
            'total_ubicaciones': n_locations,
            'distancia_total_km': round(total_distance, 2),
            'tiempo_estimado_minutos': round(total_distance / 30 * 60, 2),
            'optimizado_con': 'Greedy (fallback)',
            'fecha_calculo': datetime.now().isoformat()
        }
    
    def _generate_synthetic_routes(self, n_routes: int) -> List[Dict]:
        """Generar rutas sintéticas para entrenamiento de demostración"""
        routes = []
        
        for _ in range(n_routes):
            n_locations = np.random.randint(5, 10)
            
            # Generar ubicaciones aleatorias cerca de Lima, Perú
            base_lat, base_lon = -12.046374, -77.042793
            
            locations = [{'id': 0, 'lat': base_lat, 'lon': base_lon}]  # Base
            
            for i in range(1, n_locations):
                locations.append({
                    'id': i,
                    'lat': base_lat + np.random.uniform(-0.1, 0.1),
                    'lon': base_lon + np.random.uniform(-0.1, 0.1)
                })
            
            routes.append({
                'locations': locations,
                'actual_route': list(range(n_locations))
            })
        
        return routes
    
    def save_model(self):
        """Guardar modelo en disco"""
        model_data = {
            'q_table': self.q_table,
            'episodes_trained': self.episodes_trained,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'saved_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, self.model_path)
        logger.info(f"💾 Modelo de rutas guardado en {self.model_path}")
    
    def load_model(self) -> bool:
        """Cargar modelo desde disco"""
        if not os.path.exists(self.model_path):
            logger.info("📭 No hay modelo de rutas guardado")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            self.q_table = model_data['q_table']
            self.episodes_trained = model_data['episodes_trained']
            self.learning_rate = model_data.get('learning_rate', 0.1)
            self.discount_factor = model_data.get('discount_factor', 0.95)
            
            logger.info(f"✅ Modelo de rutas cargado ({self.episodes_trained} episodios)")
            return True
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            return False
