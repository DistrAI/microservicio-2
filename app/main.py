"""
AnaliticaIA - Microservicio de Inteligencia de Datos
Estratega Predictivo para DistribuyoIA
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.api.routes import demand, segmentation, routes, health

# Configuración
settings = get_settings()

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    description="Microservicio de análisis predictivo y segmentación para PYMES",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health.router, tags=["Health"])
app.include_router(demand.router, prefix="/api/v1", tags=["Predicción de Demanda"])
app.include_router(segmentation.router, prefix="/api/v1", tags=["Segmentación"])
app.include_router(routes.router, prefix="/api/v1", tags=["Optimización de Rutas"])


@app.on_event("startup")
async def startup_event():
    """Ejecutar al iniciar la aplicación"""
    logger.info(f"🚀 Iniciando {settings.app_name} v{settings.app_version}")
    logger.info(f"📊 Modo Debug: {settings.debug}")
    logger.info(f"🗄️  Base de datos: Supabase PostgreSQL")
    

@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutar al cerrar la aplicación"""
    logger.info(f"👋 Cerrando {settings.app_name}")


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
