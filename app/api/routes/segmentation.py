"""
Router de Segmentación de Clientes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from loguru import logger
import pandas as pd

from app.api.schemas import CustomerSegmentationRequest, CustomerSegmentationResponse, CustomerSegment
from app.database.connection import get_db
from app.database.models import Cliente, Pedido
from app.ml.customer_segmentation import CustomerSegmentation

router = APIRouter()

# Instancia global del segmentador
segmenter = CustomerSegmentation()


@router.post("/segment/customers", response_model=CustomerSegmentationResponse)
async def segment_customers(
    request: CustomerSegmentationRequest,
    db: Session = Depends(get_db)
):
    """
    Segmenta clientes usando K-Means clustering
    
    Analiza:
    - Frecuencia de compra
    - Valor monetario
    - Recencia
    - Comportamiento de compra
    
    Retorna grupos de clientes con características similares.
    """
    try:
        logger.info(f"Segmentando clientes en {request.num_clusters} grupos")
        
        # Obtener datos de pedidos para segmentación
        from sqlalchemy import text
        
        query_str = """
            SELECT id, cliente_id, total, fecha_pedido
            FROM pedidos
            WHERE activo = true
        """
        
        pedidos_data = pd.read_sql(text(query_str), db.bind)
        
        if len(pedidos_data) < 10:
            raise HTTPException(
                status_code=400,
                detail="Datos insuficientes para segmentación. Se requieren al menos 10 pedidos."
            )
        
        # Entrenar/actualizar modelo
        metrics = segmenter.train(pedidos_data, n_clusters=request.num_clusters)
        
        # Formatear segmentos para respuesta
        segmentos = []
        for segment in metrics['segments']:
            segmentos.append(
                CustomerSegment(
                    segmento_id=segment['cluster_id'],
                    segmento_nombre=segment['label'],
                    descripcion=f"{segment['size']} clientes ({segment['percentage']}%)",
                    clientes_count=segment['size'],
                    valor_promedio=segment['avg_spend']
                )
            )
        
        response = CustomerSegmentationResponse(
            total_clientes=metrics['n_customers'],
            num_segmentos=request.num_clusters,
            segmentos=segmentos,
            fecha_analisis=datetime.utcnow()
        )
        
        logger.info(f"Segmentación completada: {len(response.segmentos)} segmentos")
        return response
        
    except Exception as e:
        logger.error(f"Error en segmentación: {e}")
        raise HTTPException(status_code=500, detail=f"Error en segmentación: {str(e)}")


@router.get("/segment/customer/{customer_id}")
async def get_customer_segment(customer_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el segmento de un cliente específico
    """
    try:
        # Verificar que el cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # Obtener pedidos del cliente
        from sqlalchemy import text
        
        query_str = """
            SELECT id, cliente_id, total, fecha_pedido
            FROM pedidos
            WHERE cliente_id = :cliente_id AND activo = true
        """
        
        pedidos_data = pd.read_sql(
            text(query_str),
            db.bind,
            params={'cliente_id': customer_id}
        )
        
        if len(pedidos_data) == 0:
            return {
                "cliente_id": customer_id,
                "nombre": cliente.nombre,
                "segmento": "Sin datos",
                "segmento_id": -1,
                "mensaje": "El cliente no tiene pedidos registrados"
            }
        
        # Predecir segmento
        predictions = segmenter.predict(pedidos_data)
        
        if predictions and len(predictions) > 0:
            pred = predictions[0]
            
            # Generar recomendaciones según segmento
            recomendaciones = []
            if "Champions" in pred['segment_label'] or "Premium" in pred['segment_label']:
                recomendaciones = [
                    "Ofrecer beneficios VIP exclusivos",
                    "Programa de referidos con incentivos",
                    "Acceso anticipado a nuevos productos"
                ]
            elif "Riesgo" in pred['segment_label']:
                recomendaciones = [
                    "Enviar oferta de reactivación",
                    "Descuento especial personalizado",
                    "Encuesta de satisfacción"
                ]
            else:
                recomendaciones = [
                    "Ofrecer programa de lealtad",
                    "Enviar promociones personalizadas",
                    "Newsletter con productos relevantes"
                ]
            
            return {
                "cliente_id": customer_id,
                "nombre": cliente.nombre,
                "segmento": pred['segment_label'],
                "segmento_id": pred['cluster_id'],
                "num_pedidos": pred['num_pedidos'],
                "gasto_total": pred['gasto_total'],
                "gasto_promedio": pred['gasto_promedio'],
                "dias_desde_ultima_compra": pred['dias_desde_ultima_compra'],
                "rfm_score": pred['rfm_score'],
                "recomendaciones": recomendaciones
            }
        else:
            return {
                "cliente_id": customer_id,
                "nombre": cliente.nombre,
                "error": "No se pudo clasificar al cliente"
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo segmento de cliente {customer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
