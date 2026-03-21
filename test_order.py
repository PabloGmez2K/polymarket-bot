import os
import json
import urllib.request
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

load_dotenv()

# --- Conexión autenticada ---
client = ClobClient(
    "https://clob.polymarket.com",
    key=os.getenv("PK"),
    chain_id=137,
    signature_type=1,
    funder=os.getenv("FUNDER")
)
client.set_api_creds(client.create_or_derive_api_creds())
print("Autenticación OK\n")

# --- Buscar un mercado activo con order book ---
print("Buscando mercado con order book activo...")
url = "https://gamma-api.polymarket.com/events?tag_id=103040&active=true&closed=false&limit=50"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req)
events = json.loads(resp.read().decode())

# Buscar el primer mercado futuro con order book
target_token = None
target_question = None

for event in events:
    if "March 21" in event.get("title", ""):
        continue  # Saltar mercados de hoy
    
    for m in event.get("markets", []):
        market = json.loads(m) if isinstance(m, str) else m
        raw_tokens = market.get("clobTokenIds", [])
        tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else raw_tokens
        
        if len(tokens) < 2:
            continue
        
        try:
            book = client.get_order_book(tokens[0])
            if len(book.bids) > 5 and len(book.asks) > 5:
                target_token = tokens[0]
                target_question = market.get("question", "???")
                
                print(f"\nMercado seleccionado: {target_question}")
                print(f"  Token YES: {target_token[:40]}...")
                print(f"  Bids: {len(book.bids)}, Asks: {len(book.asks)}")
                print(f"  Best bid: ${book.bids[0].price}")
                print(f"  Best ask: ${book.asks[0].price}")
                break
        except:
            continue
    
    if target_token:
        break

if not target_token:
    print("No se encontró un mercado con suficiente liquidez. Intenta más tarde.")
    exit()

# --- ORDEN DE PRUEBA ---
# Orden límite de compra a $0.01 (1 céntimo) por 1 share
# Precio tan bajo que NADIE va a vendernos a ese precio = no se ejecuta
# Solo queremos ver que la orden aparece y podemos cancelarla

print(f"\n{'='*50}")
print("ORDEN DE PRUEBA (no se ejecutará)")
print(f"{'='*50}")
print(f"  Mercado: {target_question}")
print(f"  Lado: BUY (comprar YES)")
print(f"  Precio: $0.01 (1 céntimo)")
print(f"  Cantidad: 10 shares")
print(f"  Coste máximo: $0.10 (10 céntimos)")
print(f"  Tipo: GTC (Good Till Cancelled)")
print(f"{'='*50}")

input("\nPulsa ENTER para colocar la orden (o Ctrl+C para cancelar)...")

try:
    # Crear la orden
    order_args = OrderArgs(
        token_id=target_token,
        price=0.01,       # $0.01 por share — no se ejecutará
        size=10.0,         # 10 shares
        side=BUY
    )
    
    signed_order = client.create_order(order_args)
    print("\nOrden firmada OK")
    
    # Enviar la orden
    resp = client.post_order(signed_order, OrderType.GTC)
    print(f"Orden enviada! Respuesta: {resp}")
    
    # Verificar que aparece
    print("\nVerificando órdenes abiertas...")
    open_orders = client.get_orders()
    print(f"Órdenes abiertas: {len(open_orders)}")
    
    for o in open_orders:
        print(f"  ID: {o.get('id', '???')}")
        print(f"  Precio: {o.get('price', '???')}")
        print(f"  Tamaño: {o.get('original_size', o.get('size', '???'))}")
        print(f"  Estado: {o.get('status', '???')}")
    
    # Cancelar la orden
    if open_orders:
        print("\nCancelando orden de prueba...")
        order_id = open_orders[0].get("id")
        if order_id:
            cancel_resp = client.cancel(order_id)
            print(f"Orden cancelada: {cancel_resp}")
    
    print("\n" + "="*50)
    print("PRIMERA ORDEN COMPLETADA CON EXITO!")
    print("Tu bot puede colocar y cancelar órdenes en Polymarket.")
    print("="*50)

except Exception as e:
    print(f"\nERROR colocando orden: {e}")
    print("\nEsto puede pasar por varias razones:")
    print("  - Los fondos aún no han llegado a tu wallet de Polymarket")
    print("  - Falta aprobar token allowances")
    print("  - La clave privada o funder no coinciden")