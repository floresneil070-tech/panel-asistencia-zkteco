from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Ajusta aquí tus credenciales exactas
cadena_conexion = 'mysql+pymysql://root:sqlproneil23>@localhost/recursos_humanos'

print("Intentando conectar a MySQL...")

try:
    engine = create_engine(cadena_conexion)
    # Intentamos abrir una conexión rápida
    with engine.connect() as conexion:
        print("¡Conexión exitosa! Python ya puede hablar con tu base de datos MySQL.")
except OperationalError as e:
    print("\nError de conexión. Revisa los datos o asegúrate de que el servidor esté encendido.")
    print(f"Detalle: {e}")