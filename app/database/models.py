"""
Modelos de base de datos SQLAlchemy
Réplica de las tablas del microservicio GestorAPI
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Date, Text, Table, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.connection import Base


# Tabla intermedia para relación muchos a muchos
ruta_pedidos = Table(
    'ruta_pedidos',
    Base.metadata,
    Column('ruta_id', Integer, ForeignKey('rutas_entrega.id')),
    Column('pedido_id', Integer, ForeignKey('pedidos.id'))
)


class Cliente(Base):
    """Modelo de Cliente"""
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    telefono = Column(String(20))
    direccion = Column(String(500))
    latitud_cliente = Column(Float)
    longitud_cliente = Column(Float)
    referencia_direccion = Column(String(300))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    pedidos = relationship("Pedido", back_populates="cliente")


class Producto(Base):
    """Modelo de Producto"""
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False, index=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    descripcion = Column(String(255))
    precio = Column(Numeric(12, 2), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    items_pedido = relationship("ItemPedido", back_populates="producto")
    inventarios = relationship("Inventario", back_populates="producto")


class Usuario(Base):
    """Modelo de Usuario"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)  # ADMIN, REPARTIDOR
    telefono = Column(String(20))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    rutas = relationship("RutaEntrega", back_populates="repartidor")


class Pedido(Base):
    """Modelo de Pedido"""
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    direccion_entrega = Column(String(255), nullable=False)
    observaciones = Column(String(500))
    fecha_entrega = Column(DateTime)
    activo = Column(Boolean, default=True)
    fecha_pedido = Column(DateTime, default=datetime.utcnow, index=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    rutas = relationship("RutaEntrega", secondary=ruta_pedidos, back_populates="pedidos")


class ItemPedido(Base):
    """Modelo de Item de Pedido"""
    __tablename__ = "items_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items_pedido")


class RutaEntrega(Base):
    """Modelo de Ruta de Entrega"""
    __tablename__ = "rutas_entrega"
    
    id = Column(Integer, primary_key=True, index=True)
    repartidor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="PLANIFICADA", index=True)
    fecha_ruta = Column(Date, nullable=False, index=True)
    distancia_total_km = Column(Float)
    tiempo_estimado_min = Column(Integer)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    repartidor = relationship("Usuario", back_populates="rutas")
    pedidos = relationship("Pedido", secondary=ruta_pedidos, back_populates="rutas")


class Inventario(Base):
    """Modelo de Inventario"""
    __tablename__ = "inventarios"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, unique=True, index=True)
    cantidad_actual = Column(Integer, nullable=False, default=0)
    cantidad_minima = Column(Integer, nullable=False, default=0)
    cantidad_maxima = Column(Integer, nullable=False, default=0)
    ubicacion_almacen = Column(String(100))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    producto = relationship("Producto", back_populates="inventarios")
    movimientos = relationship("MovimientoInventario", back_populates="inventario")


class MovimientoInventario(Base):
    """Modelo de Movimiento de Inventario"""
    __tablename__ = "movimientos_inventario"
    
    id = Column(Integer, primary_key=True, index=True)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # ENTRADA, SALIDA, AJUSTE
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(255))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_movimiento = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    inventario = relationship("Inventario", back_populates="movimientos")
