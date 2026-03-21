import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Cargar claves desde .env
load_dotenv()

pk = os.getenv("PK")
funder = os.getenv("FUNDER")

# Verificar que las claves se cargaron
print("Clave privada cargada:", "SI" if pk else "NO")
print("Funder address cargada:", "SI" if funder else "NO")
print(f"Funder: {funder[:6]}...{funder[-4:]}" if funder else "")

# Crear cliente autenticado
# signature_type=1 = Magic wallet (cuenta creada con email)
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon

client = ClobClient(
    HOST,
    key=pk,
    chain_id=CHAIN_ID,
    signature_type=1,  # Magic wallet
    funder=funder
)

# Generar credenciales API (L2)
# Esto firma un mensaje con tu clave privada para demostrar que eres tú
print("\nGenerando credenciales API...")
try:
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)
    print("Credenciales API generadas OK!")
    print(f"  API Key: {creds.api_key[:10]}...")
    print(f"  Secret:  {creds.api_secret[:10]}...")
except Exception as e:
    print(f"ERROR generando credenciales: {e}")
    exit()

# Test: operaciones que requieren autenticación
print("\n--- Tests autenticados ---")

try:
    trades = client.get_trades()
    print(f"Historial de trades: {len(trades)} operaciones")
except Exception as e:
    print(f"get_trades: {e}")

try:
    orders = client.get_orders()
    print(f"Órdenes abiertas: {len(orders)} órdenes")
except Exception as e:
    print(f"get_orders: {e}")

print("\n--- Autenticación completada ---")
print("Tu bot puede leer Y escribir en Polymarket!")