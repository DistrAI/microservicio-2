# 🧠 Guía de Machine Learning - AnaliticaIA

Guía completa para entrenar y usar los 3 modelos de ML del microservicio.

---

## 📋 Modelos Implementados

### 1. **Random Forest** - Predicción de Demanda
- **Objetivo:** Predecir cuántas unidades de un producto se venderán
- **Algoritmo:** Ensamble de árboles de decisión
- **Features:** Temporalidad, tendencias, ventas históricas
- **Endpoint:** `POST /api/v1/predict/demand`

### 2. **K-Means** - Segmentación de Clientes  
- **Objetivo:** Agrupar clientes según comportamiento de compra
- **Algoritmo:** Clustering no supervisado
- **Features:** RFM (Recency, Frequency, Monetary)
- **Endpoint:** `POST /api/v1/segment/customers`

### 3. **Q-Learning** - Optimización de Rutas
- **Objetivo:** Encontrar rutas óptimas de entrega
- **Algoritmo:** Aprendizaje por Refuerzo
- **Recompensa:** Minimizar distancia total
- **Endpoint:** `POST /api/v1/optimize/routes`

---

## 🎓 Entrenamiento de Modelos

### Opción 1: Entrenar Todos los Modelos (Recomendado)

```bash
# Con Docker
docker-compose run --rm analiticaia-api python scripts/train_models.py

# Sin Docker (local)
python scripts/train_models.py
```

**Salida esperada:**
```
🚀 INICIANDO PIPELINE DE ENTRENAMIENTO DE MODELOS ML
📥 Obteniendo datos de Supabase...
  ✅ Datos de demanda: 500 registros
  ✅ Datos de segmentación: 200 pedidos
  ✅ Datos de rutas: 150 ubicaciones

🎯 ENTRENANDO MODELO DE PREDICCIÓN DE DEMANDA
✅ Modelo entrenado - R²: 0.856, MAE: 12.45

👥 ENTRENANDO MODELO DE SEGMENTACIÓN DE CLIENTES
✅ Segmentos encontrados:
  Champions (Mejores Clientes): 25 clientes (20%)
  Clientes Leales: 80 clientes (50%)
  En Riesgo de Abandono: 45 clientes (30%)

🚚 ENTRENANDO MODELO DE OPTIMIZACIÓN DE RUTAS
✅ Modelo entrenado
  Episodios: 1000
  Recompensa promedio: -45.23
  Mejora: 35.67%

✅ ENTRENAMIENTO COMPLETADO
💾 Modelos guardados en /app/models/
🎉 ¡Listo para usar en la API!
```

### Opción 2: Entrenar Modelos Individualmente

#### Entrenar Predicción de Demanda

```python
from app.ml.demand_predictor import DemandPredictor
import pandas as pd

# Preparar datos
data = pd.DataFrame({
    'producto_id': [1, 1, 2, 2, 3],
    'cantidad': [10, 15, 8, 12, 20],
    'precio_unitario': [50, 50, 30, 30, 100],
    'fecha_pedido': ['2024-01-01', '2024-02-01', '2024-01-15', '2024-02-15', '2024-01-20']
})

# Entrenar
predictor = DemandPredictor()
metrics = predictor.train(data)

print(f"R² Score: {metrics['r2_score']}")
print(f"MAE: {metrics['mae']}")
```

#### Entrenar Segmentación

```python
from app.ml.customer_segmentation import CustomerSegmentation
import pandas as pd

# Preparar datos (pedidos)
data = pd.DataFrame({
    'id': [1, 2, 3, 4, 5],
    'cliente_id': [1, 1, 2, 2, 3],
    'total': [100, 150, 50, 75, 300],
    'fecha_pedido': ['2024-01-01', '2024-02-01', '2024-01-15', '2024-02-15', '2024-01-20']
})

# Entrenar
segmenter = CustomerSegmentation()
metrics = segmenter.train(data, n_clusters=3)

for segment in metrics['segments']:
    print(f"{segment['label']}: {segment['size']} clientes")
```

#### Entrenar Optimización de Rutas

```python
from app.ml.route_optimizer import RouteOptimizer

# Entrenar
optimizer = RouteOptimizer()

# Con datos históricos (opcional)
historical_routes = [
    {
        'locations': [
            {'id': 0, 'lat': -12.04, 'lon': -77.03},
            {'id': 1, 'lat': -12.05, 'lon': -77.04},
            {'id': 2, 'lat': -12.06, 'lon': -77.05}
        ],
        'actual_route': [0, 1, 2]
    }
]

metrics = optimizer.train(historical_routes, episodes=1000)
print(f"Mejora: {metrics['improvement_pct']}%")
```

---

## 🚀 Uso de los Modelos (API)

### 1. Predicción de Demanda

#### Predecir un producto específico

```bash
curl -X POST "http://localhost:8000/api/v1/predict/demand" \
  -H "Content-Type: application/json" \
  -d '{
    "producto_id": 1,
    "periodo": "semana"
  }'
```

**Respuesta:**
```json
{
  "producto_id": 1,
  "periodo": "semana",
  "cantidad_estimada": 150.5,
  "intervalo_confianza": {
    "lower": 120.4,
    "upper": 180.6
  },
  "confianza": 85.5,
  "fecha_prediccion": "2025-11-17T00:00:00"
}
```

#### Predecir todos los productos

```bash
curl "http://localhost:8000/api/v1/predict/all-products?periodo=mes"
```

### 2. Segmentación de Clientes

#### Segmentar todos los clientes

```bash
curl -X POST "http://localhost:8000/api/v1/segment/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "num_clusters": 4
  }'
```

**Respuesta:**
```json
{
  "total_clientes": 150,
  "num_segmentos": 4,
  "segmentos": [
    {
      "segmento_id": 0,
      "segmento_nombre": "Champions (Mejores Clientes)",
      "descripcion": "30 clientes (20%)",
      "clientes_count": 30,
      "valor_promedio": 850.5
    },
    {
      "segmento_id": 1,
      "segmento_nombre": "Clientes Leales",
      "descripcion": "60 clientes (40%)",
      "clientes_count": 60,
      "valor_promedio": 350.0
    }
  ],
  "fecha_analisis": "2025-11-10T20:00:00"
}
```

#### Obtener segmento de un cliente

```bash
curl "http://localhost:8000/api/v1/segment/customer/1"
```

**Respuesta:**
```json
{
  "cliente_id": 1,
  "nombre": "Juan Pérez",
  "segmento": "Champions (Mejores Clientes)",
  "segmento_id": 0,
  "num_pedidos": 15,
  "gasto_total": 2500.0,
  "gasto_promedio": 166.67,
  "dias_desde_ultima_compra": 5,
  "rfm_score": 13.5,
  "recomendaciones": [
    "Ofrecer beneficios VIP exclusivos",
    "Programa de referidos con incentivos",
    "Acceso anticipado a nuevos productos"
  ]
}
```

### 3. Optimización de Rutas

#### Optimizar ruta de entrega

```bash
curl -X POST "http://localhost:8000/api/v1/optimize/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "pedidos": [1, 2, 3, 4, 5, 6],
    "vehiculos": 2
  }'
```

**Respuesta:**
```json
{
  "total_pedidos": 6,
  "num_vehiculos": 2,
  "rutas": [
    {
      "vehiculo_id": 1,
      "pedidos": [1, 3, 5],
      "distancia_total_km": 12.5,
      "tiempo_estimado_min": 25.0,
      "orden_entrega": [1, 3, 5]
    },
    {
      "vehiculo_id": 2,
      "pedidos": [2, 4, 6],
      "distancia_total_km": 15.3,
      "tiempo_estimado_min": 30.6,
      "orden_entrega": [2, 4, 6]
    }
  ],
  "distancia_total_km": 27.8,
  "tiempo_total_min": 55.6,
  "ahorro_estimado_km": 5.56,
  "fecha_optimizacion": "2025-11-10T20:00:00"
}
```

#### Ver estadísticas de rutas históricas

```bash
curl "http://localhost:8000/api/v1/optimize/routes/historical"
```

---

## 📊 Métricas de los Modelos

### Random Forest (Demanda)
- **R² Score:** Mide qué tan bien el modelo predice (0-1, mayor es mejor)
- **MAE:** Error absoluto promedio en unidades
- **Features importantes:** Temporalidad, historial de ventas

### K-Means (Segmentación)
- **Silhouette Score:** Calidad de los clusters (-1 a 1, mayor es mejor)
- **Inertia:** Distancia promedio dentro de clusters (menor es mejor)
- **Segmentos típicos:** 3-5 grupos según tamaño de negocio

### Q-Learning (Rutas)
- **Recompensa:** Distancia negativa (maximizar = minimizar distancia)
- **Mejora:** % de reducción vs rutas no optimizadas
- **Convergencia:** Mejora debe ser positiva tras entrenamiento

---

## 🔄 Re-entrenamiento

### Cuándo re-entrenar:

**Predicción de Demanda:**
- ✅ Cada mes (datos nuevos de ventas)
- ✅ Cuando cambian patrones de compra
- ✅ Al agregar nuevos productos

**Segmentación:**
- ✅ Cada 2-3 meses
- ✅ Cuando crece significativamente la base de clientes
- ✅ Cambios en comportamiento de compra

**Optimización de Rutas:**
- ✅ Cada semana (nuevos datos de tráfico)
- ✅ Al cambiar zonas de entrega
- ✅ Agregar nuevos puntos de entrega

### Comando automático:

```bash
# Programar con cron (Linux)
0 2 * * 0 cd /app && python scripts/train_models.py

# O crear un servicio que ejecute cada X tiempo
```

---

## 🐛 Troubleshooting

### Error: "Modelo no entrenado"
**Solución:** Ejecutar `python scripts/train_models.py`

### Error: "Datos insuficientes"
**Causa:** Menos de 10 registros en la BD
**Solución:** 
1. Agregar más datos manualmente
2. El script usará datos sintéticos automáticamente

### Predicciones no son precisas
**Solución:**
1. Re-entrenar con más datos
2. Verificar calidad de los datos (fechas, cantidades)
3. Revisar métricas de entrenamiento

### Segmentación da siempre los mismos grupos
**Solución:**
1. Ajustar `num_clusters`
2. Verificar variabilidad en datos de clientes
3. Re-entrenar con datos más recientes

### Rutas optimizadas son ilógicas
**Solución:**
1. Verificar coordenadas GPS de clientes
2. Re-entrenar el modelo Q-Learning con más episodios
3. Revisar que el algoritmo greedy funciona como fallback

---

## 📈 Mejores Prácticas

1. **Entrenar con datos reales:** Usar `train_models.py` con datos de Supabase
2. **Monitorear métricas:** Guardar historial de R², MAE, Silhouette
3. **Validar predicciones:** Comparar predicciones vs ventas reales
4. **A/B Testing:** Comparar rutas optimizadas vs rutas manuales
5. **Feedback loop:** Usar resultados para mejorar modelos

---

## 🎯 Próximos Pasos

- [ ] Implementar validación cruzada en entrenamiento
- [ ] Agregar más features (clima, promociones, eventos)
- [ ] Hyperparameter tuning automático
- [ ] Deploy de modelos a GCP AI Platform
- [ ] Dashboard de métricas de modelos
- [ ] API de re-entrenamiento automático
- [ ] Versionado de modelos (MLflow)

---

**¿Preguntas?** Revisa la documentación en http://localhost:8000/docs 🚀
