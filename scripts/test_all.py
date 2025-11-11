"""
Script completo: Entrenar modelos + Ejecutar tests
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import subprocess
from loguru import logger
import time

def run_training():
    """Ejecutar entrenamiento de modelos"""
    logger.info("="*70)
    logger.info("🎓 PASO 1: ENTRENANDO MODELOS ML")
    logger.info("="*70 + "\n")
    
    try:
        # Importar y ejecutar train_models
        from train_models import main as train_main
        train_main()
        logger.info("\n✅ Entrenamiento completado\n")
        return True
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {e}")
        return False


def run_tests():
    """Ejecutar suite de tests"""
    logger.info("="*70)
    logger.info("🧪 PASO 2: EJECUTANDO TESTS DE API")
    logger.info("="*70 + "\n")
    
    # Esperar un poco para que la API esté lista
    logger.info("⏳ Esperando 5 segundos para que la API esté lista...")
    time.sleep(5)
    
    try:
        # Importar y ejecutar test_api
        from test_api import main as test_main
        test_main()
        return True
    except SystemExit as e:
        # test_api hace sys.exit con código de error
        return e.code == 0
    except Exception as e:
        logger.error(f"❌ Error ejecutando tests: {e}")
        return False


def main():
    """Ejecutar pipeline completo"""
    logger.info("\n" + "="*70)
    logger.info("🚀 PIPELINE COMPLETO: ENTRENAMIENTO + TESTS")
    logger.info("="*70 + "\n")
    
    start_time = time.time()
    
    # Paso 1: Entrenar modelos
    training_success = run_training()
    
    if not training_success:
        logger.error("\n❌ Entrenamiento falló. No se ejecutarán los tests.")
        sys.exit(1)
    
    # Paso 2: Ejecutar tests
    tests_success = run_tests()
    
    # Resumen final
    duration = time.time() - start_time
    
    logger.info("\n" + "="*70)
    logger.info("📊 RESUMEN FINAL")
    logger.info("="*70)
    logger.info(f"🎓 Entrenamiento: {'✅ OK' if training_success else '❌ FALLÓ'}")
    logger.info(f"🧪 Tests: {'✅ OK' if tests_success else '❌ FALLARON'}")
    logger.info(f"⏱️  Duración total: {duration:.2f} segundos")
    logger.info("="*70 + "\n")
    
    if training_success and tests_success:
        logger.info("🎉 ¡TODO COMPLETADO EXITOSAMENTE!")
        sys.exit(0)
    else:
        logger.error("❌ Algunos pasos fallaron")
        sys.exit(1)


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
        "logs/test_all.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    main()
