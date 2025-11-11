"""
Servicio de Re-entrenamiento Automático de Modelos
Ejecuta re-entrenamiento periódico y monitorea métricas
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import schedule
import time
from datetime import datetime
from loguru import logger
from train_models import main as train_all_models

# Configuración
RETRAIN_INTERVAL_DAYS = 7  # Re-entrenar cada 7 días
CHECK_INTERVAL_HOURS = 24   # Verificar cada 24 horas


def should_retrain() -> bool:
    """Verificar si es necesario re-entrenar"""
    # Verificar si los modelos existen
    models_dir = "models"
    required_models = [
        "demand_model.pkl",
        "segmentation_model.pkl",
        "route_model.pkl"
    ]
    
    models_exist = all(
        os.path.exists(os.path.join(models_dir, model))
        for model in required_models
    )
    
    if not models_exist:
        logger.warning("⚠️  Modelos no encontrados, re-entrenamiento necesario")
        return True
    
    # Verificar antigüedad de los modelos
    oldest_model_time = min(
        os.path.getmtime(os.path.join(models_dir, model))
        for model in required_models
        if os.path.exists(os.path.join(models_dir, model))
    )
    
    days_old = (time.time() - oldest_model_time) / (24 * 3600)
    
    if days_old >= RETRAIN_INTERVAL_DAYS:
        logger.info(f"📅 Modelos tienen {days_old:.1f} días, re-entrenando...")
        return True
    
    logger.info(f"✅ Modelos actualizados ({days_old:.1f} días de antigüedad)")
    return False


def retrain_models():
    """Ejecutar re-entrenamiento de todos los modelos"""
    logger.info("="*70)
    logger.info("🔄 INICIANDO RE-ENTRENAMIENTO AUTOMÁTICO")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    try:
        if should_retrain():
            # Ejecutar entrenamiento
            train_all_models()
            
            logger.info("\n" + "="*70)
            logger.info("✅ RE-ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
            logger.info(f"⏰ Siguiente re-entrenamiento en {RETRAIN_INTERVAL_DAYS} días")
            logger.info("="*70 + "\n")
        else:
            logger.info("⏭️  Re-entrenamiento no necesario aún\n")
    
    except Exception as e:
        logger.error(f"❌ Error en re-entrenamiento automático: {e}")


def monitor_model_performance():
    """Monitorear rendimiento de modelos (placeholder)"""
    logger.info("📊 Monitoreando rendimiento de modelos...")
    
    # TODO: Implementar métricas de producción
    # - Comparar predicciones vs resultados reales
    # - Alertar si métricas degradan
    # - Trigger re-entrenamiento si es necesario
    
    logger.info("✅ Monitoreo completado")


def run_auto_retrain_service():
    """Ejecutar servicio de re-entrenamiento automático"""
    logger.info("="*70)
    logger.info("🤖 SERVICIO DE RE-ENTRENAMIENTO AUTOMÁTICO")
    logger.info("="*70)
    logger.info(f"🔄 Re-entrenamiento cada: {RETRAIN_INTERVAL_DAYS} días")
    logger.info(f"🔍 Verificación cada: {CHECK_INTERVAL_HOURS} horas")
    logger.info(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    logger.info("💡 Presiona Ctrl+C para detener")
    logger.info("="*70 + "\n")
    
    # Re-entrenamiento inicial si es necesario
    retrain_models()
    
    # Programar tareas
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(retrain_models)
    schedule.every(24).hours.do(monitor_model_performance)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    except KeyboardInterrupt:
        logger.info("\n" + "="*70)
        logger.info("🛑 Deteniendo servicio de re-entrenamiento...")
        logger.info("👋 Servicio detenido")
        logger.info("="*70)
        sys.exit(0)


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
        "logs/auto_retrain.log",
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    run_auto_retrain_service()
