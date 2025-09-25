# src/config/schema_config.py

"""
Archivo de configuración central para el esquema de la base de datos.
Esta es la única fuente de verdad para la estructura de las tablas,
sus claves primarias y su ubicación.
"""

# Define la clave primaria para cada tabla que la requiera.
# Esto es usado por la lógica de PUSH y UPSERT.
TABLE_PRIMARY_KEYS = {
    'egresos': 'uuid',
    'ingresos': 'uuid',
    'usuarios': 'uuid',
    'ventas': 'uuid',
    'clientes': 'uuid',
    'productos': 'uuid',
    # <-- Añade aquí cualquier nueva tabla en el futuro
}

# Define qué tablas pertenecen a las bases de datos generales de la empresa.
# Cualquier tabla no listada aquí se asumirá que pertenece a una sucursal.
TABLAS_GENERALES = {
    'usuarios',
    'clientes',
    'productos',
    # <-- Añade aquí cualquier nueva tabla general en el futuro
}
