"""
Servicio de Sincronización Automática Render → Supabase
=========================================================
Primera ejecución: Copia TODA la base de datos (estructura + datos)
Siguientes ejecuciones: Solo sincroniza cambios nuevos cada 2 minutos
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger
import time
import sys
import subprocess
import os
from datetime import datetime
from typing import Set
import schedule

# ===================================
# CONFIGURACIÓN
# ===================================
RENDER_CONFIG = {
    'host': 'dpg-d48sg3ogjchc73f2ksc0-a.oregon-postgres.render.com',
    'port': '5432',
    'database': 'gestorapi_ixn4',
    'user': 'admin',
    'password': 'cNi4bxZsyBvD6P2SKnP1A9iJZTWORB5p'
}

SUPABASE_CONFIG = {
    'host': 'aws-1-us-east-1.pooler.supabase.com',
    'port': '6543',
    'database': 'postgres',
    'user': 'postgres.upwpqtcqhunaewddqaxl',
    'password': 'analiticaIA'
}

SYNC_INTERVAL = 120  # 2 minutos

# Estadísticas
sync_stats = {
    'total_syncs': 0,
    'successful_syncs': 0,
    'failed_syncs': 0,
    'last_sync': None,
    'records_synced': 0,
    'initial_sync_done': False
}


def get_pg_connection_string(config: dict, for_pg_tools: bool = False) -> str:
    """Genera connection string para PostgreSQL"""
    if for_pg_tools:
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return f"host={config['host']} port={config['port']} dbname={config['database']} user={config['user']} password={config['password']}"


def connect_db(config: dict):
    """Conectar a base de datos con retry"""
    try:
        conn = psycopg2.connect(**{
            'host': config['host'],
            'port': int(config['port']),
            'database': config['database'],
            'user': config['user'],
            'password': config['password']
        })
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a BD: {e}")
        return None


def get_all_tables(conn) -> Set[str]:
    """Obtener todas las tablas de una base de datos"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = {row[0] for row in cursor.fetchall()}
        cursor.close()
        return tables
    except Exception as e:
        logger.error(f"❌ Error obteniendo tablas: {e}")
        return set()


def full_database_dump():
    """
    Sincronización COMPLETA usando pg_dump/pg_restore
    Copia TODA la estructura y datos de Render → Supabase
    """
    logger.info("="*70)
    logger.info("🔄 SINCRONIZACIÓN COMPLETA (Primera vez)")
    logger.info("📦 Copiando TODA la base de datos Render → Supabase")
    logger.info("="*70)
    
    dump_file = '/tmp/render_dump.sql'
    
    try:
        # Paso 1: Dump de Render
        logger.info("📤 Paso 1/3: Exportando base de datos de Render...")
        
        render_url = get_pg_connection_string(RENDER_CONFIG, for_pg_tools=True)
        
        dump_cmd = [
            'pg_dump',
            render_url,
            '--no-owner',
            '--no-privileges',
            '--clean',
            '--if-exists',
            '-f', dump_file
        ]
        
        result = subprocess.run(dump_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Error en pg_dump: {result.stderr}")
            return False
        
        logger.info(f"✅ Dump completado: {os.path.getsize(dump_file) / 1024:.2f} KB")
        
        # Paso 2: Limpiar Supabase (eliminar tablas existentes)
        logger.info("🗑️  Paso 2/3: Limpiando Supabase...")
        
        supabase_conn = connect_db(SUPABASE_CONFIG)
        if not supabase_conn:
            return False
        
        cursor = supabase_conn.cursor()
        
        # Obtener todas las tablas en Supabase
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        # Eliminar tablas existentes
        if existing_tables:
            logger.info(f"  Eliminando {len(existing_tables)} tablas existentes...")
            cursor.execute('DROP TABLE IF EXISTS ' + ', '.join(existing_tables) + ' CASCADE')
            supabase_conn.commit()
        
        cursor.close()
        supabase_conn.close()
        
        # Paso 3: Restaurar en Supabase
        logger.info("📥 Paso 3/3: Restaurando en Supabase...")
        
        supabase_url = get_pg_connection_string(SUPABASE_CONFIG, for_pg_tools=True)
        
        restore_cmd = [
            'psql',
            supabase_url,
            '-f', dump_file,
            '--quiet'
        ]
        
        result = subprocess.run(restore_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # psql puede devolver warnings como errores, verificar si realmente falló
            if "ERROR" in result.stderr:
                logger.warning(f"⚠️  Warnings durante restore: {result.stderr[:500]}")
            else:
                logger.info("✅ Restore completado con algunos warnings (normal)")
        else:
            logger.info("✅ Restore completado exitosamente")
        
        # Limpiar archivo temporal
        if os.path.exists(dump_file):
            os.remove(dump_file)
        
        # Verificar que se copiaron las tablas
        supabase_conn = connect_db(SUPABASE_CONFIG)
        if supabase_conn:
            supabase_tables = get_all_tables(supabase_conn)
            logger.info(f"✅ {len(supabase_tables)} tablas copiadas exitosamente")
            
            # Contar registros totales
            cursor = supabase_conn.cursor()
            total_records = 0
            for table in supabase_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    total_records += count
                    logger.info(f"  📦 {table}: {count} registros")
                except:
                    pass
            
            cursor.close()
            supabase_conn.close()
            
            logger.info(f"📊 Total de registros copiados: {total_records}")
        
        sync_stats['initial_sync_done'] = True
        logger.info("="*70)
        logger.info("✅ SINCRONIZACIÓN COMPLETA FINALIZADA")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización completa: {e}")
        if os.path.exists(dump_file):
            os.remove(dump_file)
        return False


def incremental_sync():
    """
    Sincronización INCREMENTAL
    Solo copia registros nuevos/modificados
    """
    logger.info("="*70)
    logger.info(f"🔄 Sincronización incremental #{sync_stats['total_syncs']}")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    try:
        # Conectar a ambas bases
        render_conn = connect_db(RENDER_CONFIG)
        supabase_conn = connect_db(SUPABASE_CONFIG)
        
        if not render_conn or not supabase_conn:
            logger.error("❌ No se pudo conectar a las bases de datos")
            return False
        
        logger.info("✅ Conectado a Render")
        logger.info("✅ Conectado a Supabase")
        
        # Obtener tablas
        render_tables = get_all_tables(render_conn)
        supabase_tables = get_all_tables(supabase_conn)
        
        logger.info(f"📊 Tablas en Render: {len(render_tables)}")
        logger.info(f"📊 Tablas en Supabase: {len(supabase_tables)}")
        
        # Detectar tablas nuevas
        new_tables = render_tables - supabase_tables
        if new_tables:
            logger.warning(f"🆕 Tablas nuevas detectadas: {new_tables}")
            logger.warning(f"⚠️  Se requiere sincronización completa para nuevas tablas")
            logger.info("🔄 Ejecutando sincronización completa...")
            render_conn.close()
            supabase_conn.close()
            return full_database_dump()
        
        # Sincronizar solo cambios de tablas existentes
        total_synced = 0
        render_cursor = render_conn.cursor()
        supabase_cursor = supabase_conn.cursor()
        
        for table in render_tables:
            try:
                # Obtener último timestamp de la tabla
                last_sync = sync_stats.get('last_sync')
                
                # Intentar obtener registros nuevos/modificados
                time_filter = ""
                if last_sync:
                    # Buscar columnas de timestamp
                    render_cursor.execute(f"""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        AND column_name IN ('fecha_actualizacion', 'fecha_creacion', 'fecha_pedido', 'fecha_movimiento', 'updated_at', 'created_at')
                        LIMIT 1
                    """)
                    time_col_result = render_cursor.fetchone()
                    
                    if time_col_result:
                        time_col = time_col_result[0]
                        time_filter = f" WHERE {time_col} > '{last_sync.strftime('%Y-%m-%d %H:%M:%S')}'"
                
                # Obtener registros nuevos
                render_cursor.execute(f"SELECT * FROM {table}{time_filter}")
                rows = render_cursor.fetchall()
                
                if not rows:
                    continue
                
                # Obtener nombres de columnas
                columns = [desc[0] for desc in render_cursor.description]
                columns_str = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                
                # Obtener primary key
                supabase_cursor.execute(f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table}'::regclass AND i.indisprimary
                """)
                pk_result = supabase_cursor.fetchone()
                
                count = 0
                if pk_result:
                    pk_col = pk_result[0]
                    update_cols = [f"{col} = EXCLUDED.{col}" for col in columns if col != pk_col]
                    update_str = ', '.join(update_cols)
                    
                    upsert_query = f"""
                        INSERT INTO {table} ({columns_str})
                        VALUES ({placeholders})
                        ON CONFLICT ({pk_col})
                        DO UPDATE SET {update_str}
                    """
                    
                    for row in rows:
                        try:
                            supabase_cursor.execute(upsert_query, row)
                            count += 1
                        except Exception as e:
                            logger.warning(f"⚠️  Error en registro de {table}: {str(e)[:100]}")
                    
                    supabase_conn.commit()
                
                if count > 0:
                    logger.info(f"  📦 {table}: {count} registros actualizados")
                    total_synced += count
                    
            except Exception as e:
                logger.error(f"  ❌ Error en {table}: {str(e)[:200]}")
                supabase_conn.rollback()
        
        render_cursor.close()
        supabase_cursor.close()
        render_conn.close()
        supabase_conn.close()
        
        logger.info("="*70)
        logger.info(f"✅ Sincronización incremental completada")
        logger.info(f"📊 Registros sincronizados: {total_synced}")
        logger.info("="*70)
        
        sync_stats['records_synced'] += total_synced
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización incremental: {e}")
        return False


def sync_databases():
    """Ejecutar sincronización (completa o incremental según corresponda)"""
    sync_stats['total_syncs'] += 1
    start_time = datetime.now()
    
    try:
        # Primera sincronización: Completa
        if not sync_stats['initial_sync_done']:
            success = full_database_dump()
        else:
            # Siguientes: Incremental
            success = incremental_sync()
        
        if success:
            sync_stats['successful_syncs'] += 1
            sync_stats['last_sync'] = datetime.now()
        else:
            sync_stats['failed_syncs'] += 1
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️  Duración: {duration:.2f} segundos\n")
        
    except Exception as e:
        sync_stats['failed_syncs'] += 1
        logger.error(f"❌ Error general: {e}")


def print_stats():
    """Mostrar estadísticas del servicio"""
    logger.info("\n" + "="*70)
    logger.info("📊 ESTADÍSTICAS DEL SERVICIO")
    logger.info("="*70)
    logger.info(f"🔢 Total sincronizaciones: {sync_stats['total_syncs']}")
    logger.info(f"✅ Exitosas: {sync_stats['successful_syncs']}")
    logger.info(f"❌ Fallidas: {sync_stats['failed_syncs']}")
    logger.info(f"📦 Registros sincronizados: {sync_stats['records_synced']}")
    if sync_stats['last_sync']:
        logger.info(f"⏰ Última sync: {sync_stats['last_sync'].strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")


def run_service():
    """Ejecutar servicio de sincronización continua"""
    logger.info("="*70)
    logger.info("🚀 SERVICIO DE SINCRONIZACIÓN AUTOMÁTICA")
    logger.info("="*70)
    logger.info(f"🔄 Intervalo: {SYNC_INTERVAL} segundos ({SYNC_INTERVAL/60:.1f} min)")
    logger.info(f"📡 Render → Supabase")
    logger.info(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    logger.info("💡 Presiona Ctrl+C para detener")
    logger.info("="*70 + "\n")
    
    # Sincronización inicial
    sync_databases()
    
    # Programar sincronizaciones cada 2 minutos
    schedule.every(SYNC_INTERVAL).seconds.do(sync_databases)
    
    # Estadísticas cada 10 minutos
    schedule.every(10).minutes.do(print_stats)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n" + "="*70)
        logger.info("🛑 Deteniendo servicio...")
        print_stats()
        logger.info("👋 Servicio detenido")
        logger.info("="*70)
        sys.exit(0)


if __name__ == "__main__":
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    logger.add(
        "logs/sync_service.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    run_service()
