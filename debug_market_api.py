"""
debug_market_api.py — Inspecciona qué devuelve la API para traders de un mercado
=================================================================================
Ejecuta esto y pega el resultado para saber exactamente qué endpoint funciona.
"""

import urllib.request
import urllib.parse
import json

DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

def api_get(url):
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "debug/1.0")
        resp = urllib.request.urlopen(req, timeout=15)
        raw = resp.read()
        return json.loads(raw), None
    except Exception as e:
        return None, str(e)

def inspect(label, url):
    print(f"\n{'─'*60}")
    print(f"[{label}]")
    print(f"URL: {url}")
    data, err = api_get(url)
    if err:
        print(f"ERROR: {err}")
        return
    if data is None:
        print("Respuesta: None")
        return
    if isinstance(data, list):
        print(f"Tipo: lista de {len(data)} elementos")
        if data:
            print(f"Primer elemento (campos): {list(data[0].keys())}")
            print(f"Primer elemento (raw):")
            print(json.dumps(data[0], indent=2)[:600])
        else:
            print("Lista vacía []")
    elif isinstance(data, dict):
        print(f"Tipo: dict con campos: {list(data.keys())}")
        print(json.dumps(data, indent=2)[:600])
    else:
        print(f"Tipo: {type(data)} — {str(data)[:200]}")


if __name__ == "__main__":
    # ── Paso 1: obtener un mercado real con su conditionId y token ──
    print("Obteniendo mercado de temperatura real...")
    events, err = api_get(
        f"{GAMMA_API}/events"
        f"?tag_id=103040&active=true&closed=false&limit=5"
    )
    if not events or err:
        print(f"Error obteniendo eventos: {err}")
        exit(1)

    # Sacar el primer mercado que tenga conditionId
    market = None
    for event in events:
        for m in event.get("markets", []):
            cid = m.get("conditionId", "")
            clob_raw = m.get("clobTokenIds", "[]")
            try:
                clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
            except Exception:
                clob_ids = []
            if cid and clob_ids:
                market = m
                break
        if market:
            break

    if not market:
        print("No se encontró ningún mercado con conditionId")
        exit(1)

    cid      = market.get("conditionId", "")
    mkt_id   = market.get("id", "")
    question = market.get("question", "?")
    clob_raw = market.get("clobTokenIds", "[]")
    clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
    token_yes = clob_ids[0] if clob_ids else ""

    print(f"\nMercado seleccionado: {question[:70]}")
    print(f"  conditionId : {cid}")
    print(f"  market id   : {mkt_id}")
    print(f"  token YES   : {token_yes[:30]}...")

    # ── Paso 2: probar todos los endpoints posibles ──

    inspect("A — positions por conditionId",
        f"{DATA_API}/positions?market={cid}&limit=5")

    inspect("B — positions por conditionId (campo distinto)",
        f"{DATA_API}/positions?conditionId={cid}&limit=5")

    inspect("C — positions por token_id (asset_id)",
        f"{DATA_API}/positions?asset_id={token_yes}&limit=5")

    inspect("D — positions por token_id (tokenId)",
        f"{DATA_API}/positions?tokenId={token_yes}&limit=5")

    inspect("E — gamma top-holders por token",
        f"{GAMMA_API}/markets/{token_yes}/top-holders?limit=5")

    inspect("F — gamma positions por market id",
        f"{GAMMA_API}/markets/{mkt_id}/positions?limit=5")

    inspect("G — data-api trades por mercado",
        f"{DATA_API}/trades?market={cid}&limit=5")

    inspect("H — data-api trades por token",
        f"{DATA_API}/trades?asset_id={token_yes}&limit=5")

    print(f"\n{'='*60}")
    print("Pega todo este output para ver qué endpoint funciona.")
