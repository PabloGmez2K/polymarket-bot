"""
find_traders.py — Descubridor de traders de temperatura similares
=================================================================

Estrategia:
  1. Obtiene mercados de temperatura activos (tag 103040)
  2. Para cada mercado, consulta quién tiene posiciones
  3. Filtra traders con bankroll pequeño (~$5-$200) y precios medios
  4. Rankea por cuántos mercados de temperatura tienen abiertos
  5. Muestra los más relevantes para añadir al trader_analyzer.py

Esto encuentra traders que operan como nosotros, no los ballenas.

Uso:
    python find_traders.py
"""

import urllib.request
import urllib.parse
import json
import re
import os
import time
from datetime import datetime, timezone

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API  = "https://data-api.polymarket.com"

DAILY_TEMP_TAG_ID = "103040"

# ============================================================
# FILTROS — ajusta según lo que busques
# ============================================================
MIN_BANKROLL    = 5.0     # $ mínimo invertido total
MAX_BANKROLL    = 300.0   # $ máximo — excluye ballenas
MIN_PRICE       = 0.05    # precio mínimo de entrada (excluye lotería pura)
MAX_PRICE       = 0.92    # precio máximo (excluye estrategia ColdMath)
MIN_MARKETS     = 2       # mínimo de mercados donde aparecer (era 3, demasiado estricto)
MIN_WIN_RATE    = 40.0    # % win rate mínimo en posiciones cerradas

# Cuántos mercados analizar — más = más diversidad de traders encontrados
MAX_MARKETS_TO_SCAN = 40

# Traders que ya conocemos (para no repetirlos)
KNOWN_TRADERS = {
    "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11",  # ColdMath
    "0xd3938e1d885f7849215c49d87465709d63400744",  # Trader2
    "0x09f4265f01d6f73d6cf3ccdb8a37e1f7bb42e9c2",  # Trader3
    "0xbb7a6e5b0d5b...",                            # Trader4 — pon la address completa
}


# ============================================================
# API
# ============================================================
def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-finder/1.0")
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(2)
    return None


# ============================================================
# PASO 1: Obtener mercados de temperatura activos
# ============================================================
def get_temp_markets(limit=MAX_MARKETS_TO_SCAN):
    """
    Obtiene mercados de temperatura de múltiples páginas para
    conseguir diversidad de ciudades, no solo las más voluminosas.
    """
    print(f"\n[1/4] Obteniendo mercados de temperatura activos...")

    markets = []
    seen_cities = set()

    # Paginamos con offset para obtener diversidad
    for offset in range(0, 200, 50):
        data = api_get(
            f"{GAMMA_API}/events"
            f"?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=50&offset={offset}"
            f"&order=volume24hr&ascending=false"
        )
        if not data:
            break

        for event in data:
            for m in event.get("markets", []):
                try:
                    clob_raw = m.get("clobTokenIds", "[]")
                    clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
                    if not clob_ids:
                        continue
                    prices_raw = m.get("outcomePrices", "[]")
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    if not prices:
                        continue

                    question = m.get("question", "?")

                    # Extraer ciudad para garantizar diversidad
                    import re
                    city_match = re.search(r"temperature in (.+?) (?:be |between |\d)", question, re.IGNORECASE)
                    city = city_match.group(1).strip() if city_match else "unknown"

                    markets.append({
                        "question":     question,
                        "city":         city,
                        "token_yes":    clob_ids[0],
                        "token_no":     clob_ids[1] if len(clob_ids) > 1 else None,
                        "price_yes":    float(prices[0]),
                        "condition_id": m.get("conditionId", ""),
                        "market_id":    m.get("id", ""),
                    })
                    seen_cities.add(city)
                except Exception:
                    continue

        if len(markets) >= limit * 3:  # Cogemos más para tener diversidad
            break

        time.sleep(0.3)

    # Muestra qué ciudades encontramos
    print(f"  {len(markets)} mercados de {len(seen_cities)} ciudades distintas")
    print(f"  Ciudades: {', '.join(sorted(seen_cities)[:15])}{'...' if len(seen_cities) > 15 else ''}")

    # Seleccionar hasta MAX_MARKETS_TO_SCAN con diversidad de ciudades
    selected = []
    cities_included = {}
    max_per_city = 2  # máximo 2 por ciudad → más ciudades cubiertas con 40 mercados

    for m in markets:
        c = m["city"]
        if cities_included.get(c, 0) < max_per_city:
            selected.append(m)
            cities_included[c] = cities_included.get(c, 0) + 1
        if len(selected) >= limit:
            break

    print(f"  Seleccionados {len(selected)} mercados de {len(cities_included)} ciudades (max {max_per_city}/ciudad)")
    return selected


# ============================================================
# PASO 2: Para cada mercado, obtener quién tiene posiciones
# ============================================================
def get_market_traders(market):
    """
    Obtiene traders que han operado en un mercado concreto.
    Usa /trades?market=conditionId — único endpoint que funciona.
    Filtra por BUY en nuestro rango de precio.
    """
    cid = market.get("condition_id", "")
    if not cid:
        return []

    try:
        params = urllib.parse.urlencode({
            "market": cid,
            "limit": 100,
        })
        data = api_get(f"{DATA_API}/trades?{params}")
        if not data:
            return []

        result = []
        seen = set()
        for trade in data:
            # Solo BUY — los SELL son salidas, no entradas
            if trade.get("side", "").upper() != "BUY":
                continue

            addr = trade.get("proxyWallet", "")
            if not addr or addr.lower() in {k.lower() for k in KNOWN_TRADERS}:
                continue
            if addr in seen:
                continue

            price = float(trade.get("price", 0))
            if not (MIN_PRICE <= price <= MAX_PRICE):
                continue

            seen.add(addr)
            result.append({
                "address":   addr.lower(),
                "price":     price,
                "size":      float(trade.get("size", 0)),
                "timestamp": trade.get("timestamp", 0),
                "outcome":   trade.get("outcome", "?"),
            })

        return result

    except Exception as e:
        return []


# ============================================================
# PASO 3: Perfil rápido de un trader candidato
# ============================================================
def quick_profile(address):
    """
    Obtiene posiciones activas y cerradas para evaluar si un trader
    es interesante. Rápido — solo lo necesario para filtrar.
    """
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "sizeThreshold": "0.1",
            "limit": 50,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        positions = api_get(f"{DATA_API}/positions?{params}")
        if not positions:
            return None

        # Calcular bankroll aproximado
        total_invested = sum(float(p.get("initialValue", 0)) for p in positions)
        total_current  = sum(float(p.get("currentValue", 0)) for p in positions)

        # Distribución de precios de entrada
        prices = [float(p.get("avgPrice", 0)) for p in positions]
        in_our_range = sum(1 for pr in prices if MIN_PRICE <= pr <= MAX_PRICE)

        # Mercados de temperatura (detectar por título)
        temp_markets = [
            p for p in positions
            if "temperature" in p.get("title", "").lower()
        ]

        # Win rate en cerradas
        closed = api_get(
            f"{DATA_API}/positions?{urllib.parse.urlencode({'user': address.lower(), 'limit': 50, 'closed': 'true'})}"
        ) or []
        wins   = sum(1 for p in closed if float(p.get("cashPnl", 0)) > 0)
        losses = sum(1 for p in closed if float(p.get("cashPnl", 0)) < 0)
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else None

        return {
            "address":       address,
            "total_invested": total_invested,
            "total_current":  total_current,
            "n_positions":    len(positions),
            "n_temp_markets": len(temp_markets),
            "in_our_range":   in_our_range,
            "win_rate":       win_rate,
            "wins":           wins,
            "losses":         losses,
        }
    except Exception:
        return None


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("🔍 BUSCADOR DE TRADERS SIMILARES — Polymarket")
    print(f"Filtros: bankroll ${MIN_BANKROLL}-${MAX_BANKROLL} | "
          f"precio {MIN_PRICE}-{MAX_PRICE} | "
          f"mín. {MIN_MARKETS} mercados temperatura")

    # Paso 1: mercados
    markets = get_temp_markets()
    if not markets:
        print("No se pudieron obtener mercados. Inténtalo de nuevo.")
        exit(1)

    # Paso 2: recopilar traders de cada mercado
    print(f"\n[2/4] Buscando traders en {len(markets)} mercados...")
    trader_count = {}   # address → nº de mercados donde aparece
    trader_prices = {}  # address → lista de precios de entrada

    for i, mkt in enumerate(markets):
        print(f"  [{i+1}/{len(markets)}] {mkt['question'][:55]}...")
        traders = get_market_traders(mkt)
        n_found = len(traders)
        if n_found:
            print(f"             → {n_found} traders en rango")
        for t in traders:
            addr = t["address"]
            trader_count[addr] = trader_count.get(addr, 0) + 1
            if addr not in trader_prices:
                trader_prices[addr] = []
            trader_prices[addr].append(t["price"])
        time.sleep(0.3)  # respetar rate limit

    print(f"  {len(trader_count)} traders únicos encontrados en rango de precio")

    # Paso 3: filtrar por nº mínimo de mercados
    candidates = [
        addr for addr, count in trader_count.items()
        if count >= MIN_MARKETS
    ]
    candidates.sort(key=lambda a: -trader_count[a])
    print(f"\n[3/4] {len(candidates)} candidatos con ≥{MIN_MARKETS} mercados de temperatura")

    # Paso 4: perfil rápido de cada candidato
    print(f"\n[4/4] Analizando perfil de {min(len(candidates), 15)} mejores candidatos...")
    results = []
    for addr in candidates[:15]:  # Top 15 para no tardar demasiado
        print(f"  Analizando {addr[:14]}...")
        profile = quick_profile(addr)
        if not profile:
            continue
        # Filtros de bankroll y win rate
        if not (MIN_BANKROLL <= profile["total_invested"] <= MAX_BANKROLL):
            continue
        if profile["win_rate"] is not None and profile["win_rate"] < MIN_WIN_RATE:
            continue
        profile["n_temp_score"] = trader_count[addr]
        results.append(profile)
        time.sleep(0.5)

    # ============================================================
    # MOSTRAR RESULTADOS
    # ============================================================
    print(f"\n{'='*60}")
    print(f"✅ TRADERS INTERESANTES ENCONTRADOS ({len(results)})")
    print(f"   Operan en temperatura | bankroll similar | precios medios")
    print(f"{'='*60}")

    if not results:
        print("\n  Ningún trader pasó todos los filtros.")
        print("  Prueba a relajar los filtros: sube MAX_BANKROLL o baja MIN_MARKETS")
    else:
        results.sort(key=lambda x: (-x["n_temp_score"], -(x["win_rate"] or 0)))
        for i, r in enumerate(results):
            wr_str = f"{r['win_rate']:.1f}%" if r["win_rate"] is not None else "sin datos"
            print(f"\n  #{i+1} — {r['address']}")
            print(f"    Mercados temperatura: {r['n_temp_score']} | "
                  f"En nuestro rango: {r['in_our_range']}")
            print(f"    Bankroll aprox: ${r['total_invested']:.2f} invertido | "
                  f"Valor actual: ${r['total_current']:.2f}")
            print(f"    Win rate: {wr_str} ({r['wins']}W/{r['losses']}L)")

        # Sugerencia para trader_analyzer.py
        print(f"\n{'='*60}")
        print("💡 AÑADIR AL trader_analyzer.py:")
        print(f"{'='*60}")
        print('\nTRADERS = {')
        print('    "ColdMath": "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11",')
        print('    "Trader2":  "0xd3938e1d885f7849215c49d87465709d63400744",')
        print('    "Trader3":  "0x09f4265f01d6f73d6cf3ccdb8a37e1f7bb42e9c2",')
        for i, r in enumerate(results[:5]):
            print(f'    "Nuevo{i+1}":  "{r["address"]}",')
        print('}')

    # ============================================================
    # GUARDAR EN traders_db.json (alimenta trader_analyzer.py)
    # ============================================================
    DB_FILE = "traders_db.json"

    # Cargar DB existente
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"traders": {}}
        # Añadir los core si la DB es nueva
        for name, addr in [
            ("ColdMath", "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11"),
            ("Trader2",  "0xd3938e1d885f7849215c49d87465709d63400744"),
            ("Trader3",  "0x09f4265f01d6f73d6cf3ccdb8a37e1f7bb42e9c2"),
        ]:
            db["traders"][name] = {
                "address": addr, "source": "manual",
                "added": datetime.now(timezone.utc).isoformat(),
                "tags": [], "notes": "",
            }

    # Comprobar addresses ya registradas
    existing_addresses = {
        info["address"].lower()
        for info in db["traders"].values()
    }

    added = 0
    for i, r in enumerate(results):
        addr = r["address"].lower()
        if addr in existing_addresses:
            continue
        name = f"Found{len(db['traders']) - 2}"  # nombre auto
        wr_str = f"{r['win_rate']:.1f}%" if r["win_rate"] else "?"
        db["traders"][name] = {
            "address": addr,
            "source": "find_traders",
            "added": datetime.now(timezone.utc).isoformat(),
            "win_rate_discovery": r["win_rate"],
            "bankroll_discovery": r["total_invested"],
            "n_temp_markets_discovery": r["n_temp_score"],
            "tags": ["our_range", "small_bankroll", "auto_discovered"],
            "notes": f"Descubierto automáticamente. WR={wr_str}, "
                     f"bankroll=${r['total_invested']:.0f}, "
                     f"temp_markets={r['n_temp_score']}",
        }
        existing_addresses.add(addr)
        added += 1

    if added > 0:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"\n✅ {added} traders nuevos añadidos a {DB_FILE}")
        print(f"   Total en DB: {len(db['traders'])} traders")
        print(f"   Ejecuta trader_analyzer.py para analizarlos todos")
    else:
        print(f"\n  Todos los traders encontrados ya estaban en {DB_FILE}")

    # Guardar también en found_traders.json como respaldo
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": len(markets),
        "traders_found": len(results),
        "added_to_db": added,
        "results": results,
    }
    with open("found_traders.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"💾 Detalle guardado en found_traders.json")
