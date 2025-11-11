"""
Configuración de la aplicación AnaliticaIA
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración global de la aplicación"""
    
    # Aplicación
    app_name: str = "AnaliticaIA"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # Database Render (Source)
    render_db_url: str = "jdbc:postgresql://dpg-d48sg3ogjchc73f2ksc0-a.oregon-postgres.render.com:5432/gestorapi_ixn4"
    render_db_user: str = "admin"
    render_db_password: str = ""
    
    # Database Supabase (Target - Analytics)
    supabase_db_url: str = "postgresql://postgres.upwpqtcqhunaewddqaxl:analiticaIA@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
    supabase_db_user: str = "postgres.upwpqtcqhunaewddqaxl"
    supabase_db_password: str = "analiticaIA"
    supabase_db_host: str = "aws-1-us-east-1.pooler.supabase.com"
    supabase_db_port: int = 6543
    supabase_db_name: str = "postgres"
    
    # Machine Learning
    ml_model_path: str = "./models"
    ml_retrain_interval: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración singleton"""
    return Settings()
