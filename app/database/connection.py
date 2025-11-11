"""
Gestión de conexiones a base de datos
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger

from app.config import get_settings

settings = get_settings()

# Motor de base de datos Supabase
SUPABASE_DATABASE_URL = settings.supabase_db_url

# Crear engine
engine = create_engine(
    SUPABASE_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.debug
)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """Dependency para obtener sesión de BD"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializar base de datos (crear tablas)"""
    logger.info("🗄️  Inicializando base de datos...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Base de datos inicializada")


def test_connection():
    """Probar conexión a la base de datos"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Conexión a Supabase exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión a Supabase: {e}")
        return False
