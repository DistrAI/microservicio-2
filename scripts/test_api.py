"""
Script de tests automatizados para AnaliticaIA
Verifica que todos los endpoints funcionen correctamente
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from loguru import logger
from typing import Dict, List

# Configuración
API_URL = "http://localhost:8000"
API_V1 = f"{API_URL}/api/v1"


class APITester:
    """Clase para ejecutar tests de la API"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def test(self, name: str, method: str, url: str, data: Dict = None, expected_status: int = 200):
        """Ejecutar un test individual"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 Test: {name}")
        logger.info(f"{'='*70}")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            logger.info(f"📡 {method} {url}")
            if data:
                logger.info(f"📤 Request: {json.dumps(data, indent=2)}")
            
            logger.info(f"📥 Status: {response.status_code}")
            
            # Verificar status code
            if response.status_code == expected_status:
                logger.info(f"✅ Status correcto: {response.status_code}")
                status_ok = True
            else:
                logger.error(f"❌ Status incorrecto. Esperado: {expected_status}, Recibido: {response.status_code}")
                status_ok = False
            
            # Mostrar respuesta
            try:
                response_data = response.json()
                logger.info(f"📦 Response:")
                logger.info(json.dumps(response_data, indent=2, ensure_ascii=False)[:500])
                
                if "detail" in response_data and not status_ok:
                    logger.error(f"💥 Error: {response_data['detail']}")
            except:
                logger.info(f"📦 Response (text): {response.text[:200]}")
            
            # Resultado
            if status_ok:
                logger.info(f"✅ TEST PASADO: {name}")
                self.passed += 1
                self.results.append({"name": name, "status": "PASSED"})
                return True
            else:
                logger.error(f"❌ TEST FALLADO: {name}")
                self.failed += 1
                self.results.append({"name": name, "status": "FAILED", "error": response.text[:200]})
                return False
                
        except Exception as e:
            logger.error(f"❌ TEST FALLADO: {name}")
            logger.error(f"💥 Excepción: {e}")
            self.failed += 1
            self.results.append({"name": name, "status": "FAILED", "error": str(e)})
            return False
    
    def summary(self):
        """Mostrar resumen de tests"""
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 RESUMEN DE TESTS")
        logger.info(f"{'='*70}")
        logger.info(f"✅ Pasados: {self.passed}")
        logger.info(f"❌ Fallados: {self.failed}")
        logger.info(f"📈 Total: {self.passed + self.failed}")
        logger.info(f"🎯 Tasa de éxito: {(self.passed / (self.passed + self.failed) * 100):.2f}%")
        logger.info(f"{'='*70}\n")
        
        if self.failed > 0:
            logger.warning("⚠️  Algunos tests fallaron. Revisa los logs arriba.")
        else:
            logger.info("🎉 ¡TODOS LOS TESTS PASARON!")


def main():
    """Ejecutar suite de tests"""
    logger.info("="*70)
    logger.info("🚀 INICIANDO SUITE DE TESTS - ANALITICAIA")
    logger.info("="*70)
    logger.info(f"🌐 API URL: {API_URL}")
    logger.info("="*70 + "\n")
    
    tester = APITester()
    
    # ====================
    # TESTS BÁSICOS
    # ====================
    
    # Test 1: Health Check
    tester.test(
        name="Health Check",
        method="GET",
        url=f"{API_URL}/health",
        expected_status=200
    )
    
    # Test 2: Root
    tester.test(
        name="Root Endpoint",
        method="GET",
        url=API_URL,
        expected_status=200
    )
    
    # Test 3: Docs
    tester.test(
        name="API Documentation",
        method="GET",
        url=f"{API_URL}/docs",
        expected_status=200
    )
    
    # ====================
    # TESTS DE PREDICCIÓN DE DEMANDA
    # ====================
    
    # Test 4: Predicción de demanda (producto específico)
    tester.test(
        name="Predicción de Demanda - Producto 1",
        method="POST",
        url=f"{API_V1}/predict/demand",
        data={
            "producto_id": 1,
            "periodo": "semana"
        },
        expected_status=200
    )
    
    # Test 5: Predicción de demanda (mes)
    tester.test(
        name="Predicción de Demanda - Mes",
        method="POST",
        url=f"{API_V1}/predict/demand",
        data={
            "producto_id": 1,
            "periodo": "mes"
        },
        expected_status=200
    )
    
    # Test 6: Predicción todos los productos
    tester.test(
        name="Predicción Todos los Productos",
        method="GET",
        url=f"{API_V1}/predict/all-products?periodo=semana",
        expected_status=200
    )
    
    # Test 7: Producto inexistente (debe fallar)
    tester.test(
        name="Predicción Producto Inexistente",
        method="POST",
        url=f"{API_V1}/predict/demand",
        data={
            "producto_id": 99999,
            "periodo": "semana"
        },
        expected_status=500  # Esperamos error
    )
    
    # ====================
    # TESTS DE SEGMENTACIÓN
    # ====================
    
    # Test 8: Segmentación de clientes (3 clusters)
    tester.test(
        name="Segmentación de Clientes - 3 clusters",
        method="POST",
        url=f"{API_V1}/segment/customers",
        data={
            "num_clusters": 3
        },
        expected_status=200
    )
    
    # Test 9: Segmentación de clientes (4 clusters)
    tester.test(
        name="Segmentación de Clientes - 4 clusters",
        method="POST",
        url=f"{API_V1}/segment/customers",
        data={
            "num_clusters": 4
        },
        expected_status=200
    )
    
    # Test 10: Segmento de cliente específico
    tester.test(
        name="Segmento de Cliente ID 1",
        method="GET",
        url=f"{API_V1}/segment/customer/1",
        expected_status=200
    )
    
    # Test 11: Cliente inexistente
    tester.test(
        name="Segmento Cliente Inexistente",
        method="GET",
        url=f"{API_V1}/segment/customer/99999",
        expected_status=404  # Esperamos not found
    )
    
    # ====================
    # TESTS DE OPTIMIZACIÓN DE RUTAS
    # ====================
    
    # Test 12: Optimización de rutas (1 vehículo)
    tester.test(
        name="Optimización de Rutas - 1 vehículo",
        method="POST",
        url=f"{API_V1}/optimize/routes",
        data={
            "pedidos": [1, 2, 3],
            "vehiculos": 1
        },
        expected_status=200
    )
    
    # Test 13: Optimización de rutas (2 vehículos)
    tester.test(
        name="Optimización de Rutas - 2 vehículos",
        method="POST",
        url=f"{API_V1}/optimize/routes",
        data={
            "pedidos": [1, 2, 3, 4, 5, 6],
            "vehiculos": 2
        },
        expected_status=200
    )
    
    # Test 14: Rutas históricas
    tester.test(
        name="Rutas Históricas",
        method="GET",
        url=f"{API_V1}/optimize/routes/historical",
        expected_status=200
    )
    
    # Test 15: Pedido inexistente
    tester.test(
        name="Optimización con Pedido Inexistente",
        method="POST",
        url=f"{API_V1}/optimize/routes",
        data={
            "pedidos": [99999],
            "vehiculos": 1
        },
        expected_status=404  # Esperamos not found
    )
    
    # ====================
    # RESUMEN
    # ====================
    
    tester.summary()
    
    # Exit code según resultado
    sys.exit(0 if tester.failed == 0 else 1)


if __name__ == "__main__":
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    os.makedirs('logs', exist_ok=True)
    logger.add(
        "logs/test_api.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    main()
