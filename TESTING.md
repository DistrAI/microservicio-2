# 🧪 Guía de Testing - AnaliticaIA

Documentación completa para ejecutar tests automatizados del microservicio.

---

## 📋 Tests Implementados

### **Suite Completa: 15 Tests**

#### **Tests Básicos (3)**
- ✅ Health Check
- ✅ Root Endpoint  
- ✅ API Documentation (Swagger)

#### **Tests de Predicción de Demanda (4)**
- ✅ Predicción producto específico (semana)
- ✅ Predicción producto específico (mes)
- ✅ Predicción todos los productos
- ❌ Producto inexistente (debe fallar)

#### **Tests de Segmentación (4)**
- ✅ Segmentación 3 clusters
- ✅ Segmentación 4 clusters
- ✅ Segmento cliente específico
- ❌ Cliente inexistente (debe fallar)

#### **Tests de Optimización de Rutas (4)**
- ✅ Optimización 1 vehículo
- ✅ Optimización 2 vehículos
- ✅ Rutas históricas
- ❌ Pedido inexistente (debe fallar)

---

## 🚀 Cómo Ejecutar los Tests

### **Opción 1: Todo-en-Uno (Recomendada)** ⭐

Entrena los modelos Y ejecuta los tests automáticamente:

```bash
# Dentro del contenedor Docker
docker-compose exec analiticaia-api python scripts/test_all.py

# O ejecutar como comando único
docker-compose run --rm analiticaia-api python scripts/test_all.py
```

**Qué hace:**
1. 🎓 Entrena los 3 modelos ML
2. ⏳ Espera 5 segundos
3. 🧪 Ejecuta los 15 tests
4. 📊 Muestra resumen

**Duración:** ~2-3 minutos

---

### **Opción 2: Solo Tests**

Si ya entrenaste los modelos:

```bash
# Dentro del contenedor
docker-compose exec analiticaia-api python scripts/test_api.py

# O desde fuera (si API está en localhost:8000)
python scripts/test_api.py
```

---

### **Opción 3: Test Manual con Curl**

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Predicción de Demanda
```bash
curl -X POST http://localhost:8000/api/v1/predict/demand \
  -H "Content-Type: application/json" \
  -d '{"producto_id": 1, "periodo": "semana"}'
```

#### Segmentación
```bash
curl -X POST http://localhost:8000/api/v1/segment/customers \
  -H "Content-Type: application/json" \
  -d '{"num_clusters": 3}'
```

#### Optimización de Rutas
```bash
curl -X POST http://localhost:8000/api/v1/optimize/routes \
  -H "Content-Type: application/json" \
  -d '{"pedidos": [1, 2, 3], "vehiculos": 1}'
```

---

## 📊 Salida Esperada

### **Test Exitoso**
```
🧪 Test: Predicción de Demanda - Producto 1
======================================================================
📡 POST http://localhost:8000/api/v1/predict/demand
📤 Request: {
  "producto_id": 1,
  "periodo": "semana"
}
📥 Status: 200
✅ Status correcto: 200
📦 Response:
{
  "producto_id": 1,
  "periodo": "semana",
  "cantidad_estimada": 150.5,
  "intervalo_confianza": {
    "lower": 120.4,
    "upper": 180.6
  },
  "confianza": 85.5
}
✅ TEST PASADO: Predicción de Demanda - Producto 1
```

### **Resumen Final**
```
======================================================================
📊 RESUMEN DE TESTS
======================================================================
✅ Pasados: 15
❌ Fallados: 0
📈 Total: 15
🎯 Tasa de éxito: 100.00%
======================================================================

🎉 ¡TODOS LOS TESTS PASARON!
```

---

## 🐛 Troubleshooting

### Error: "Connection refused"
**Causa:** La API no está corriendo  
**Solución:**
```bash
docker-compose ps  # Verificar estado
docker-compose up  # Iniciar si está detenida
```

### Error: "Modelo no entrenado"
**Causa:** No se han entrenado los modelos ML  
**Solución:**
```bash
docker-compose run --rm analiticaia-api python scripts/train_models.py
```

### Error: "Producto/Cliente/Pedido no encontrado"
**Causa:** Los IDs en los tests no existen en tu BD  
**Solución:**
1. Verificar datos: `docker-compose logs analiticaia-sync`
2. Modificar IDs en `scripts/test_api.py` según tus datos
3. O agregar datos de prueba manualmente

### Error: "Bin labels must be one fewer than..."
**Causa:** Bug en segmentación (YA ARREGLADO)  
**Solución:** Pull el código actualizado

### Tests lentos
**Causa:** Modelos grandes o DB lenta  
**Optimización:**
- Usa menos datos de entrenamiento
- Reduce `n_clusters` en segmentación
- Verifica conexión a Supabase

---

## 📝 Modificar Tests

### Agregar un Nuevo Test

Edita `scripts/test_api.py`:

```python
# Test 16: Mi nuevo test
tester.test(
    name="Mi Nuevo Test",
    method="POST",  # GET o POST
    url=f"{API_V1}/mi-endpoint",
    data={"param": "valor"},  # Solo para POST
    expected_status=200
)
```

### Cambiar IDs de Prueba

```python
# Usar IDs que existan en tu BD
data={
    "producto_id": 1,    # Cambiar por ID existente
    "periodo": "semana"
}
```

### Agregar Validaciones Personalizadas

```python
def test_custom(self, name, url, validator_func):
    response = requests.get(url)
    if validator_func(response.json()):
        self.passed += 1
    else:
        self.failed += 1
```

---

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and Start Services
        run: docker-compose up -d
      
      - name: Wait for API
        run: sleep 30
      
      - name: Run Tests
        run: docker-compose exec -T analiticaia-api python scripts/test_all.py
      
      - name: Cleanup
        run: docker-compose down
```

---

## 📈 Métricas de Cobertura

| Módulo | Endpoints | Tests | Cobertura |
|--------|-----------|-------|-----------|
| Health | 1 | 1 | 100% |
| Demanda | 2 | 4 | 100% |
| Segmentación | 2 | 4 | 100% |
| Rutas | 2 | 4 | 100% |
| **TOTAL** | **7** | **15** | **100%** |

---

## 🎯 Mejores Prácticas

### Antes de Cada Test
1. ✅ Entrenar modelos
2. ✅ Verificar que la API está corriendo
3. ✅ Confirmar que hay datos en Supabase
4. ✅ Revisar logs si algo falla

### Después de Cambios
1. ✅ Ejecutar `test_all.py`
2. ✅ Verificar que todos los tests pasan
3. ✅ Revisar logs de errores
4. ✅ Actualizar tests si cambiaste endpoints

### Tests en Producción
⚠️ **NO ejecutes tests destructivos en producción**
- Usa datos de prueba
- Ambiente separado
- Endpoints de solo lectura

---

## 🛠️ Herramientas Adicionales

### Postman Collection

Importa esta colección para tests manuales:

```json
{
  "info": {
    "name": "AnaliticaIA Tests",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "http://localhost:8000/health"
      }
    },
    {
      "name": "Predict Demand",
      "request": {
        "method": "POST",
        "url": "http://localhost:8000/api/v1/predict/demand",
        "body": {
          "mode": "raw",
          "raw": "{\"producto_id\": 1, \"periodo\": \"semana\"}"
        }
      }
    }
  ]
}
```

### Swagger UI (Recomendado)

Mejor herramienta para tests manuales:
```
http://localhost:8000/docs
```

**Ventajas:**
- ✅ Interfaz visual
- ✅ Tests interactivos
- ✅ Documentación integrada
- ✅ Validación automática

---

## 📚 Logs de Tests

Los logs se guardan en:
- `logs/test_api.log` - Tests individuales
- `logs/test_all.log` - Pipeline completo

Ver logs en tiempo real:
```bash
tail -f logs/test_api.log
```

---

## ✅ Checklist Pre-Deploy

Antes de deployar a producción:

- [ ] ✅ Todos los tests pasan
- [ ] ✅ Modelos entrenados con datos reales
- [ ] ✅ Sincronización funcionando
- [ ] ✅ Health check retorna 200
- [ ] ✅ Swagger UI accesible
- [ ] ✅ Logs sin errores críticos
- [ ] ✅ Base de datos con datos de producción
- [ ] ✅ Variables de entorno configuradas

---

**¿Preguntas?** Revisa los logs o ejecuta con `--verbose` para más detalles 🚀
