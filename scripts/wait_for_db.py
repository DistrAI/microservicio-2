"""
Script para esperar a que la base de datos esté lista y sincronizada
"""
import sys
import time
from loguru import logger
from sqlalchemy import create_engine, text
import os

# Configuración
MAX_RETRIES = 30
RETRY_INTERVAL = 2  # segundos

def wait_for_database():
    """Esperar a que la base de datos esté lista y tenga datos"""
    
    database_url = os.getenv('SUPABASE_DB_URL')
    if not database_url:
        logger.error("❌ SUPABASE_DB_URL no está configurada")
        sys.exit(1)
    
    logger.info("="*70)
    logger.info("⏳ ESPERANDO A QUE LA BASE DE DATOS ESTÉ LISTA")
    logger.info("="*70)
    
    engine = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"🔍 Intento {attempt}/{MAX_RETRIES}: Verificando conexión...")
            
            # Crear engine temporal
            if engine is None:
                engine = create_engine(database_url, pool_pre_ping=True)
            
            with engine.connect() as conn:
                # Verificar conexión
                conn.execute(text("SELECT 1"))
                logger.info("  ✅ Conexión exitosa")
                
                # Verificar que existen las tablas principales
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('productos', 'clientes', 'pedidos')
                """))
                
                table_count = result.scalar()
                logger.info(f"  📊 Tablas encontradas: {table_count}/3")
                
                if table_count >= 3:
                    logger.info("  ✅ Tablas principales existen")
                    
                    # Verificar que hay al menos algunos datos
                    result = conn.execute(text("SELECT COUNT(*) FROM productos"))
                    producto_count = result.scalar()
                    
                    result = conn.execute(text("SELECT COUNT(*) FROM clientes"))
                    cliente_count = result.scalar()
                    
                    logger.info(f"  📦 Productos: {producto_count}")
                    logger.info(f"  👥 Clientes: {cliente_count}")
                    
                    if producto_count > 0 or cliente_count > 0:
                        logger.info("\n" + "="*70)
                        logger.info("✅ BASE DE DATOS LISTA Y CON DATOS")
                        logger.info("="*70 + "\n")
                        return True
                    else:
                        logger.warning("  ⚠️  Base de datos vacía, esperando datos...")
                else:
                    logger.warning("  ⚠️  Esperando a que se creen las tablas...")
                
        except Exception as e:
            logger.warning(f"  ⏳ Base de datos no lista: {e}")
        
        if attempt < MAX_RETRIES:
            logger.info(f"⏱️  Esperando {RETRY_INTERVAL} segundos antes del siguiente intento...\n")
            time.sleep(RETRY_INTERVAL)
    
    logger.warning("\n" + "="*70)
    logger.warning("⚠️  TIMEOUT: Base de datos no está lista después de todos los intentos")
    logger.warning("🚀 Iniciando API de todas formas (modo degradado)")
    logger.warning("="*70 + "\n")
    return False


if __name__ == "__main__":
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    success = wait_for_database()
    sys.exit(0 if success else 0)  # Siempre retorna 0 para no bloquear inicio
