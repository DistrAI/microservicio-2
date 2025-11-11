"""
Router de Predicción de Demanda
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import pandas as pd
from loguru import logger

from app.api.schemas import (
    DemandPredictionRequest,
    DemandPredictionResponse,
    ErrorResponse
)
from app.database.connection import get_db
from app.database.models import Producto, ItemPedido, Pedido
from app.ml.demand_predictor import DemandPredictor

router = APIRouter()

# Instancia global del predictor de demanda
predictor = DemandPredictor()


@router.post("/predict/demand", response_model=DemandPredictionResponse)
async def predict_demand(
    request: DemandPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Predice la demanda futura de un producto usando Random Forest
    
    Este endpoint analiza:
    """
    try:
        # Obtener datos históricos del producto para contexto
        from sqlalchemy import text
        
        query_str = """
            SELECT ip.cantidad, ip.precio_unitario, p.fecha_pedido
            FROM items_pedido ip
            JOIN pedidos p ON ip.pedido_id = p.id
            WHERE ip.producto_id = :producto_id AND p.activo = true
        """
        
        historical_data = pd.read_sql(
            text(query_str),
            db.bind,
            params={'producto_id': request.producto_id}
        )
        
        # Predecir demanda
        prediction = predictor.predict(
            producto_id=request.producto_id,
            periodo=request.periodo,
            context_data=historical_data if len(historical_data) > 0 else None
        )
        
        return DemandPredictionResponse(
            producto_id=prediction['producto_id'],
            periodo=prediction['periodo'],
            cantidad_estimada=prediction['cantidad_estimada'],
            intervalo_confianza=prediction['intervalo_confianza'],
            confianza=prediction['confianza'],
            fecha_prediccion=datetime.fromisoformat(prediction['fecha_prediccion'])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")


@router.get("/predict/all-products", response_model=List[DemandPredictionResponse])
async def predict_all_products(periodo: str = "semana", db: Session = Depends(get_db)):
    """
    Predice la demanda para todos los productos activos
    """
    try:
        # Obtener todos los productos activos
        from sqlalchemy import text
        
        result = db.execute(text("SELECT id FROM productos WHERE activo = true"))
        producto_ids = [row[0] for row in result]
        
        if not producto_ids:
            return []
        
        # Predecir para todos
        predictions = predictor.predict_all_products(producto_ids, periodo)
        
        results = []
        for pred in predictions:
            results.append(
                DemandPredictionResponse(
                    producto_id=pred['producto_id'],
                    periodo=pred['periodo'],
                    cantidad_estimada=pred['cantidad_estimada'],
                    intervalo_confianza=pred['intervalo_confianza'],
                    confianza=pred['confianza'],
                    fecha_prediccion=datetime.fromisoformat(pred['fecha_prediccion'])
                )
            )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción múltiple: {str(e)}")
