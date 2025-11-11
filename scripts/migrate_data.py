"""
Script de migración de datos de Render a Supabase
Migra todas las tablas del microservicio GestorAPI
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger
import sys
from datetime import datetime

# Configuración de bases de datos
RENDER_CONFIG = {
    'host': 'dpg-d48sg3ogjchc73f2ksc0-a.oregon-postgres.render.com',
    'port': 5432,
    'database': 'gestorapi_ixn4',
    'user': 'admin',
    'password': 'cNi4bxZsyBvD6P2SKnP1A9iJZTWORB5p'
}

SUPABASE_CONFIG = {
    'host': 'aws-1-us-east-1.pooler.supabase.com',
    'port': 6543,
    'database': 'postgres',
    'user': 'postgres.upwpqtcqhunaewddqaxl',
    'password': 'analiticaIA'
}

# Orden de migración (respetando foreign keys)
TABLES_ORDER = [
    'usuarios',
    'clientes',
    'productos',
    'inventarios',
    'movimientos_inventario',
    'pedidos',
    'items_pedido',
    'rutas_entrega',
    'ruta_pedidos'
]


def connect_database(config, db_name):
    """Conectar a base de datos"""
    try:
        conn = psycopg2.connect(**config)
        logger.info(f"✅ Conectado a {db_name}")
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a {db_name}: {e}")
        sys.exit(1)


def get_table_columns(cursor, table_name):
    """Obtener columnas de una tabla"""
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    return [row[0] for row in cursor.fetchall()]


def create_tables_in_supabase(supabase_conn):
    """Crear tablas en Supabase si no existen"""
    logger.info("📋 Creando tablas en Supabase...")
    
    cursor = supabase_conn.cursor()
    
    # Crear tablas con el schema correcto
    tables_sql = [
        # Usuarios
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            rol VARCHAR(20) NOT NULL,
            telefono VARCHAR(20),
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Clientes
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            telefono VARCHAR(20),
            direccion VARCHAR(500),
            latitud_cliente DOUBLE PRECISION,
            longitud_cliente DOUBLE PRECISION,
            referencia_direccion VARCHAR(300),
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Productos
        """
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            sku VARCHAR(64) UNIQUE NOT NULL,
            descripcion VARCHAR(255),
            precio NUMERIC(12,2) NOT NULL,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Inventarios
        """
        CREATE TABLE IF NOT EXISTS inventarios (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER UNIQUE REFERENCES productos(id),
            cantidad_actual INTEGER DEFAULT 0,
            cantidad_minima INTEGER DEFAULT 0,
            cantidad_maxima INTEGER DEFAULT 0,
            ubicacion_almacen VARCHAR(100),
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Movimientos Inventario
        """
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id SERIAL PRIMARY KEY,
            inventario_id INTEGER REFERENCES inventarios(id),
            tipo VARCHAR(20) NOT NULL,
            cantidad INTEGER NOT NULL,
            motivo VARCHAR(255),
            usuario_id INTEGER REFERENCES usuarios(id),
            fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Pedidos
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER REFERENCES clientes(id),
            estado VARCHAR(20) DEFAULT 'PENDIENTE',
            total NUMERIC(12,2) DEFAULT 0,
            direccion_entrega VARCHAR(255) NOT NULL,
            observaciones VARCHAR(500),
            fecha_entrega TIMESTAMP,
            activo BOOLEAN DEFAULT TRUE,
            fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Items Pedido
        """
        CREATE TABLE IF NOT EXISTS items_pedido (
            id SERIAL PRIMARY KEY,
            pedido_id INTEGER REFERENCES pedidos(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL,
            precio_unitario NUMERIC(12,2) NOT NULL,
            subtotal NUMERIC(12,2) NOT NULL
        )
        """,
        
        # Rutas Entrega
        """
        CREATE TABLE IF NOT EXISTS rutas_entrega (
            id SERIAL PRIMARY KEY,
            repartidor_id INTEGER REFERENCES usuarios(id),
            estado VARCHAR(20) DEFAULT 'PLANIFICADA',
            fecha_ruta DATE NOT NULL,
            distancia_total_km DOUBLE PRECISION,
            tiempo_estimado_min INTEGER,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Ruta Pedidos (tabla intermedia)
        """
        CREATE TABLE IF NOT EXISTS ruta_pedidos (
            ruta_id INTEGER REFERENCES rutas_entrega(id),
            pedido_id INTEGER REFERENCES pedidos(id),
            PRIMARY KEY (ruta_id, pedido_id)
        )
        """
    ]
    
    for sql in tables_sql:
        try:
            cursor.execute(sql)
        except Exception as e:
            logger.warning(f"⚠️  Tabla ya existe o error: {e}")
    
    supabase_conn.commit()
    logger.info("✅ Tablas creadas/verificadas en Supabase")


def migrate_table(render_conn, supabase_conn, table_name):
    """Migrar una tabla específica"""
    logger.info(f"🔄 Migrando tabla: {table_name}")
    
    render_cursor = render_conn.cursor(cursor_factory=RealDictCursor)
    supabase_cursor = supabase_conn.cursor()
    
    try:
        # Obtener datos de Render
        render_cursor.execute(f"SELECT * FROM {table_name}")
        rows = render_cursor.fetchall()
        
        if not rows:
            logger.info(f"⚠️  Tabla {table_name} está vacía")
            return 0
        
        # Obtener columnas
        columns = list(rows[0].keys())
        
        # Limpiar tabla en Supabase (opcional)
        supabase_cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        
        # Insertar datos
        migrated_count = 0
        for row in rows:
            values = [row[col] for col in columns]
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            try:
                supabase_cursor.execute(insert_sql, values)
                migrated_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Error insertando fila en {table_name}: {e}")
        
        supabase_conn.commit()
        logger.info(f"✅ Migrados {migrated_count} registros de {table_name}")
        return migrated_count
        
    except Exception as e:
        logger.error(f"❌ Error migrando {table_name}: {e}")
        supabase_conn.rollback()
        return 0


def reset_sequences(supabase_conn):
    """Resetear secuencias de IDs después de la migración"""
    logger.info("🔄 Reseteando secuencias de IDs...")
    
    cursor = supabase_conn.cursor()
    
    for table in TABLES_ORDER:
        if table != 'ruta_pedidos':  # Esta tabla no tiene secuencia
            try:
                cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1),
                        true
                    )
                """)
            except Exception as e:
                logger.warning(f"⚠️  No se pudo resetear secuencia de {table}: {e}")
    
    supabase_conn.commit()
    logger.info("✅ Secuencias reseteadas")


def main():
    """Función principal de migración"""
    logger.info("="*60)
    logger.info("🚀 Iniciando migración de datos Render → Supabase")
    logger.info("="*60)
    
    start_time = datetime.now()
    
    # Conectar a ambas bases de datos
    render_conn = connect_database(RENDER_CONFIG, "Render")
    supabase_conn = connect_database(SUPABASE_CONFIG, "Supabase")
    
    # Crear tablas en Supabase
    create_tables_in_supabase(supabase_conn)
    
    # Migrar cada tabla
    total_migrated = 0
    for table in TABLES_ORDER:
        count = migrate_table(render_conn, supabase_conn, table)
        total_migrated += count
    
    # Resetear secuencias
    reset_sequences(supabase_conn)
    
    # Cerrar conexiones
    render_conn.close()
    supabase_conn.close()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("="*60)
    logger.info(f"✅ Migración completada exitosamente")
    logger.info(f"📊 Total de registros migrados: {total_migrated}")
    logger.info(f"⏱️  Tiempo total: {duration:.2f} segundos")
    logger.info("="*60)


if __name__ == "__main__":
    main()
