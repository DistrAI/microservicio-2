"""
Esquemas Pydantic para validación de datos
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ===================================
# SCHEMAS DE PREDICCIÓN DE DEMANDA
# ===================================
class DemandPredictionRequest(BaseModel):
    """Request para predicción de demanda"""
    producto_id: int = Field(..., description="ID del producto")
    periodo: str = Field("semana", description="Período: 'semana', 'mes'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "producto_id": 1,
                "periodo": "semana"
            }
        }


class DemandPredictionResponse(BaseModel):
    """Response de predicción de demanda"""
    producto_id: int
    producto_nombre: str
    prediccion_unidades: int
    confianza: float
    periodo: str
    fecha_prediccion: datetime
    tendencia: str  # "creciente", "estable", "decreciente"


# ===================================
# SCHEMAS DE SEGMENTACIÓN
# ===================================
class CustomerSegmentationRequest(BaseModel):
    """Request para segmentación de clientes"""
    num_clusters: int = Field(3, ge=2, le=10, description="Número de segmentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "num_clusters": 3
            }
        }


class CustomerSegment(BaseModel):
    """Información de un segmento de cliente"""
    segmento_id: int
    segmento_nombre: str
    descripcion: str
    clientes_count: int
    valor_promedio: float


class CustomerSegmentationResponse(BaseModel):
    """Response de segmentación de clientes"""
    total_clientes: int
    num_segmentos: int
    segmentos: List[CustomerSegment]
    fecha_analisis: datetime


# ===================================
# SCHEMAS DE OPTIMIZACIÓN DE RUTAS
# ===================================
class RouteOptimizationRequest(BaseModel):
    """Request para optimización de rutas"""
    pedidos: List[int] = Field(..., description="IDs de pedidos a entregar")
    vehiculos: int = Field(1, ge=1, description="Número de vehículos disponibles")
    capacidad_vehiculo: Optional[int] = Field(100, description="Capacidad máxima por vehículo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pedidos": [1, 2, 3, 4, 5],
                "vehiculos": 2,
                "capacidad_vehiculo": 100
            }
        }


class RutaOptimizada(BaseModel):
    """Información de una ruta optimizada"""
    vehiculo_id: int
    pedidos: List[int]
    distancia_total_km: float
    tiempo_estimado_min: int
    orden_entrega: List[int]


class RouteOptimizationResponse(BaseModel):
    """Response de optimización de rutas"""
    total_pedidos: int
    num_vehiculos: int
    rutas: List[RutaOptimizada]
    distancia_total_km: float
    tiempo_total_min: int
    ahorro_estimado_km: float
    fecha_optimizacion: datetime


# ===================================
# SCHEMAS GENERALES
# ===================================
class HealthResponse(BaseModel):
    """Response de health check"""
    status: str
    service: str
    version: str
    database: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Response de error"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
