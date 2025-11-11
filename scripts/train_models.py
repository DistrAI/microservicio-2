"""
Pipeline de Entrenamiento Automático de Modelos ML
Entrena todos los modelos con datos de Supabase
"""

import sys
import os

# Agregar path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger
from datetime import datetime
from app.ml.demand_predictor import DemandPredictor
from app.ml.customer_segmentation import CustomerSegmentation
from app.ml.route_optimizer import RouteOptimizer

# Configuración de Supabase
SUPABASE_URL = "postgresql://postgres.upwpqtcqhunaewddqaxl:analiticaIA@aws-1-us-east-1.pooler.supabase.com:6543/postgres"


def get_training_data():
    """Obtener datos de entrenamiento desde Supabase"""
    logger.info("📥 Obteniendo datos de Supabase...")
    
    engine = create_engine(SUPABASE_URL)
    
    with engine.connect() as conn:
        # Datos para predicción de demanda
        demand_query = """
            SELECT 
                p.id as producto_id,
                p.nombre as producto_nombre,
                ip.cantidad,
                ip.precio_unitario,
                ped.fecha_pedido
            FROM items_pedido ip
            JOIN productos p ON ip.producto_id = p.id
            JOIN pedidos ped ON ip.pedido_id = ped.id
            WHERE ped.activo = true
            ORDER BY ped.fecha_pedido
        """
        
        demand_data = pd.read_sql(text(demand_query), conn)
        logger.info(f"  ✅ Datos de demanda: {len(demand_data)} registros")
        
        # Datos para segmentación de clientes
        segmentation_query = """
            SELECT 
                ped.id,
                ped.cliente_id,
                ped.total,
                ped.fecha_pedido
            FROM pedidos ped
            WHERE ped.activo = true
            ORDER BY ped.fecha_pedido
        """
        
        segmentation_data = pd.read_sql(text(segmentation_query), conn)
        logger.info(f"  ✅ Datos de segmentación: {len(segmentation_data)} pedidos")
        
        # Datos para optimización de rutas
        routes_query = """
            SELECT 
                re.id as ruta_id,
                c.id as cliente_id,
                c.latitud_cliente as lat,
                c.longitud_cliente as lon,
                c.direccion
            FROM rutas_entrega re
            JOIN ruta_pedidos rp ON re.id = rp.ruta_id
            JOIN pedidos ped ON rp.pedido_id = ped.id
            JOIN clientes c ON ped.cliente_id = c.id
            WHERE re.activo = true
            AND c.latitud_cliente IS NOT NULL
            AND c.longitud_cliente IS NOT NULL
        """
        
        routes_data = pd.read_sql(text(routes_query), conn)
        logger.info(f"  ✅ Datos de rutas: {len(routes_data)} ubicaciones")
    
    engine.dispose()
    
    return {
        'demand': demand_data,
        'segmentation': segmentation_data,
        'routes': routes_data
    }


def train_demand_model(data: pd.DataFrame) -> dict:
    """Entrenar modelo de predicción de demanda"""
    logger.info("\n" + "="*70)
    logger.info("🎯 ENTRENANDO MODELO DE PREDICCIÓN DE DEMANDA")
    logger.info("="*70)
    
    predictor = DemandPredictor()
    
    if len(data) < 10:
        logger.warning("⚠️  Pocos datos para entrenamiento, generando datos sintéticos...")
        data = generate_synthetic_demand_data()
    
    metrics = predictor.train(data)
    
    logger.info("\n📊 Métricas del modelo:")
    logger.info(f"  R² Score: {metrics['r2_score']:.3f}")
    logger.info(f"  MAE: {metrics['mae']:.2f}")
    logger.info(f"  Muestras: {metrics['n_samples']}")
    logger.info(f"  Features: {metrics['n_features']}")
    
    return metrics


def train_segmentation_model(data: pd.DataFrame) -> dict:
    """Entrenar modelo de segmentación de clientes"""
    logger.info("\n" + "="*70)
    logger.info("👥 ENTRENANDO MODELO DE SEGMENTACIÓN DE CLIENTES")
    logger.info("="*70)
    
    segmenter = CustomerSegmentation()
    
    if len(data) < 10:
        logger.warning("⚠️  Pocos datos para entrenamiento, generando datos sintéticos...")
        data = generate_synthetic_segmentation_data()
    
    metrics = segmenter.train(data, n_clusters=4)
    
    logger.info("\n📊 Segmentos encontrados:")
    for segment in metrics['segments']:
        logger.info(f"  {segment['label']}: {segment['size']} clientes ({segment['percentage']}%)")
        logger.info(f"    - Pedidos promedio: {segment['avg_orders']}")
        logger.info(f"    - Gasto promedio: ${segment['avg_spend']:.2f}")
    
    return metrics


def train_route_model(data: pd.DataFrame) -> dict:
    """Entrenar modelo de optimización de rutas"""
    logger.info("\n" + "="*70)
    logger.info("🚚 ENTRENANDO MODELO DE OPTIMIZACIÓN DE RUTAS")
    logger.info("="*70)
    
    optimizer = RouteOptimizer()
    
    # Preparar rutas históricas
    if len(data) > 0:
        historical_routes = prepare_historical_routes(data)
    else:
        logger.warning("⚠️  Sin datos de rutas, usando datos sintéticos...")
        historical_routes = []
    
    metrics = optimizer.train(historical_routes, episodes=1000)
    
    logger.info("\n📊 Métricas del modelo:")
    logger.info(f"  Episodios: {metrics['episodes_trained']}")
    logger.info(f"  Recompensa promedio: {metrics['avg_reward_last_100']:.2f}")
    logger.info(f"  Mejora: {metrics['improvement_pct']:.2f}%")
    
    return metrics


def prepare_historical_routes(data: pd.DataFrame) -> list:
    """Preparar rutas históricas desde datos"""
    routes = []
    
    for ruta_id in data['ruta_id'].unique():
        route_data = data[data['ruta_id'] == ruta_id]
        
        locations = [
            {
                'id': row['cliente_id'],
                'lat': row['lat'],
                'lon': row['lon'],
                'direccion': row['direccion']
            }
            for _, row in route_data.iterrows()
        ]
        
        if len(locations) > 1:
            routes.append({
                'locations': locations,
                'actual_route': list(range(len(locations)))
            })
    
    return routes


def generate_synthetic_demand_data() -> pd.DataFrame:
    """Generar datos sintéticos de demanda para demostración"""
    import numpy as np
    from datetime import timedelta
    
    n_records = 500
    n_products = 10
    
    start_date = datetime.now() - timedelta(days=365)
    
    data = {
        'producto_id': np.random.randint(1, n_products + 1, n_records),
        'producto_nombre': [f'Producto {i}' for i in np.random.randint(1, n_products + 1, n_records)],
        'cantidad': np.random.randint(1, 20, n_records),
        'precio_unitario': np.random.uniform(10, 100, n_records),
        'fecha_pedido': [start_date + timedelta(days=int(x)) for x in np.random.uniform(0, 365, n_records)]
    }
    
    return pd.DataFrame(data)


def generate_synthetic_segmentation_data() -> pd.DataFrame:
    """Generar datos sintéticos de clientes para demostración"""
    import numpy as np
    from datetime import timedelta
    
    n_customers = 50
    n_orders = 200
    
    start_date = datetime.now() - timedelta(days=365)
    
    data = {
        'id': np.random.randint(1, 10000, n_orders),
        'cliente_id': np.random.randint(1, n_customers + 1, n_orders),
        'total': np.random.uniform(20, 500, n_orders),
        'fecha_pedido': [start_date + timedelta(days=int(x)) for x in np.random.uniform(0, 365, n_orders)]
    }
    
    return pd.DataFrame(data)


def main():
    """Ejecutar pipeline completo de entrenamiento"""
    logger.info("="*70)
    logger.info("🚀 INICIANDO PIPELINE DE ENTRENAMIENTO DE MODELOS ML")
    logger.info("="*70)
    logger.info(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Obtener datos
        data = get_training_data()
        
        # Entrenar modelos
        results = {
            'demand': train_demand_model(data['demand']),
            'segmentation': train_segmentation_model(data['segmentation']),
            'routes': train_route_model(data['routes'])
        }
        
        # Resumen final
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "="*70)
        logger.info("✅ ENTRENAMIENTO COMPLETADO")
        logger.info("="*70)
        logger.info(f"⏱️  Duración total: {duration:.2f} segundos")
        logger.info("\n📊 Modelos entrenados:")
        logger.info(f"  ✅ Predicción de Demanda - R²: {results['demand']['r2_score']:.3f}")
        logger.info(f"  ✅ Segmentación - {len(results['segmentation']['segments'])} segmentos")
        logger.info(f"  ✅ Rutas - {results['routes']['episodes_trained']} episodios")
        logger.info("="*70)
        logger.info("\n💾 Modelos guardados en /app/models/")
        logger.info("🎉 ¡Listo para usar en la API!")
        
    except Exception as e:
        logger.error(f"\n❌ Error en entrenamiento: {e}")
        raise


if __name__ == "__main__":
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    os.makedirs('logs', exist_ok=True)
    logger.add(
        "logs/training.log",
        rotation="10 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    main()
