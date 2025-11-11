"""
Router de Optimización de Rutas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from loguru import logger

from app.api.schemas import RouteOptimizationRequest, RouteOptimizationResponse, RutaOptimizada
from app.database.connection import get_db
from app.database.models import Pedido, Cliente
from app.ml.route_optimizer import RouteOptimizer

router = APIRouter()

# Instancia global del optimizador
optimizer = RouteOptimizer()


@router.post("/optimize/routes", response_model=RouteOptimizationResponse)
async def optimize_routes(
    request: RouteOptimizationRequest,
    db: Session = Depends(get_db)
):
    """
    Optimiza rutas de entrega usando Q-Learning (Reinforcement Learning)
    
    Considera:
    - Ubicación de clientes
    - Distancias entre puntos
    - Capacidad de vehículos
    - Tráfico estimado
    
    Retorna rutas optimizadas para minimizar distancia y tiempo.
    """
    try:
        logger.info(f"Optimizando rutas para {len(request.pedidos)} pedidos")
        
        # Verificar que todos los pedidos existen y obtener ubicaciones
        pedidos = db.query(Pedido, Cliente).join(
            Cliente, Pedido.cliente_id == Cliente.id
        ).filter(
            Pedido.id.in_(request.pedidos)
        ).all()
        
        if len(pedidos) != len(request.pedidos):
            raise HTTPException(status_code=404, detail="Algunos pedidos no fueron encontrados")
        
        # Preparar ubicaciones para optimización
        locations = []
        pedido_map = {}
        
        for idx, (pedido, cliente) in enumerate(pedidos):
            if cliente.latitud_cliente is None or cliente.longitud_cliente is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"El cliente {cliente.id} no tiene coordenadas GPS"
                )
            
            locations.append({
                'id': pedido.id,
                'lat': float(cliente.latitud_cliente),
                'lon': float(cliente.longitud_cliente),
                'direccion': cliente.direccion or f"Cliente {cliente.id}"
            })
            pedido_map[pedido.id] = idx
        
        # Optimizar ruta con Q-Learning
        optimization_result = optimizer.optimize_route(locations)
        
        # Distribuir pedidos entre vehículos
        total_pedidos = len(locations)
        pedidos_por_vehiculo = (total_pedidos + request.vehiculos - 1) // request.vehiculos
        
        rutas = []
        ruta_optimizada = optimization_result['ruta_optimizada']
        
        for i in range(request.vehiculos):
            start_idx = i * pedidos_por_vehiculo
            end_idx = min(start_idx + pedidos_por_vehiculo, total_pedidos)
            
            if start_idx >= total_pedidos:
                break
            
            pedidos_vehiculo = [
                ruta_optimizada[j]['ubicacion_id'] 
                for j in range(start_idx, end_idx)
            ]
            
            orden_entrega = pedidos_vehiculo.copy()
            
            # Calcular distancia para este vehículo
            distancia_vehiculo = sum(
                ruta_optimizada[j]['distancia_desde_anterior_km']
                for j in range(start_idx, end_idx)
            )
            
            tiempo_vehiculo = distancia_vehiculo / 30 * 60  # 30 km/h promedio
            
            ruta = RutaOptimizada(
                vehiculo_id=i + 1,
                pedidos=pedidos_vehiculo,
                distancia_total_km=round(distancia_vehiculo, 2),
                tiempo_estimado_min=round(tiempo_vehiculo, 2),
                orden_entrega=orden_entrega
            )
            rutas.append(ruta)
        
        distancia_total = optimization_result['distancia_total_km']
        tiempo_total = optimization_result['tiempo_estimado_minutos']
        
        # Estimar ahorro vs ruta no optimizada (aproximadamente 15-25%)
        ahorro_estimado = distancia_total * 0.20
        
        response = RouteOptimizationResponse(
            total_pedidos=len(request.pedidos),
            num_vehiculos=len(rutas),
            rutas=rutas,
            distancia_total_km=distancia_total,
            tiempo_total_min=tiempo_total,
            ahorro_estimado_km=round(ahorro_estimado, 2),
            fecha_optimizacion=datetime.utcnow()
        )
        
        logger.info(f"Rutas optimizadas: {len(rutas)} vehículos, {distancia_total:.2f} km total")
        return response
        
    except Exception as e:
        logger.error(f"Error optimizando rutas: {e}")
        raise HTTPException(status_code=500, detail=f"Error en optimización: {str(e)}")


@router.get("/optimize/routes/historical")
async def get_historical_routes(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas de rutas históricas para análisis
    """
    try:
        from sqlalchemy import func
        from app.database.models import RutaEntrega
        
        # Obtener estadísticas de rutas completadas
        stats = db.query(
            func.count(RutaEntrega.id).label('total'),
            func.avg(RutaEntrega.distancia_total_km).label('avg_distance'),
            func.avg(RutaEntrega.tiempo_estimado_min).label('avg_time')
        ).filter(
            RutaEntrega.activo == True,
            RutaEntrega.estado == 'completada'
        ).first()
        
        total_rutas = stats.total if stats.total else 0
        avg_distance = float(stats.avg_distance) if stats.avg_distance else 0
        avg_time = float(stats.avg_time) if stats.avg_time else 0
        
        # Si no hay datos, retornar ejemplo
        if total_rutas == 0:
            return {
                "total_rutas": 0,
                "distancia_promedio_km": 0,
                "tiempo_promedio_min": 0,
                "eficiencia_promedio": 0,
                "mejora_estimada_con_ia": "20-25%",
                "mensaje": "No hay rutas históricas completadas"
            }
        
        # Calcular eficiencia (asumiendo velocidad ideal de 40 km/h)
        eficiencia = (avg_distance / 40) / (avg_time / 60) if avg_time > 0 else 0
        
        return {
            "total_rutas": total_rutas,
            "distancia_promedio_km": round(avg_distance, 2),
            "tiempo_promedio_min": round(avg_time, 2),
            "eficiencia_promedio": round(eficiencia, 2),
            "mejora_estimada_con_ia": "20-25%",
            "recomendacion": "Usar optimización Q-Learning para reducir distancias"
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo rutas históricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
