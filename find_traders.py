"""
find_traders.py v2 — Descubrimiento inteligente de traders
============================================================

Cambio fundamental respecto a v1:
  v1: escaneaba 40 mercados → perfilaba cada trader con llamadas extra
  v2: escanea TODOS los mercados → construye perfiles desde los trades mismos

Flujo:
  1. Obtener todos los mercados de temperatura activos (paginación completa)
  2. Seleccionar ~120 con diversidad de ciudades
  3. Para cada mercado, GET /trades?market=conditionId (endpoint confirmado)
  4. De cada trade BUY: dirección, precio, tamaño, ciudad, pseudonym
  5. Acumular por trader → perfil completo sin llamadas extra
  6. Clasificar: lottery / mid_range / high_confidence
  7. Filtrar mid_range con 3+ mercados → relevantes
  8. Guardar en traders_db.json

Uso:
    python find_traders.py              # ejecución normal
    python find_traders.py --quick      # solo 40 mercados (rápido)
"""

import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API  = "https://data-api.polymarket.com"

DAILY_TEMP_TAG_ID = "103040"

# Cuántos mercados escanear (más = mejor mapa del ecosistema)
MAX_MARKETS_SCAN = 120       # normal
MAX_MARKETS_QUICK = 40       # --quick
MAX_PER_CITY = 5             # diversidad de ciudades

# Filtros para clasificar traders
LOTTERY_PRICE_CEIL = 0.06    # precio medio < 6¢ = lotería
HIGH_CONF_PRICE_FLOOR = 0.90 # precio medio > 90¢ = high-confidence (estilo ColdMath)
MID_RANGE_MIN = 0.06         # nuestro rango operativo: 6¢-90¢
MID_RANGE_MAX = 0.90

# Filtros para seleccionar traders relevantes
MIN_MARKETS = 3              # aparecer en 3+ mercados distintos
MIN_TOTAL_SIZE = 5.0         # $5+ invertido en total (excluir dust)
MAX_TOTAL_SIZE = 5000.0      # $5000 tope (excluir ballenas enormes)

# Traders que ya conocemos manualmente (no los descubrimos, pero los incluimos en DB)
CORE_TRADERS = {
    "ColdMath": {
        "address": "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11",
        "notes": "Ballena $70K, opera No a $0.95-0.99. Referencia, no imitar.",
        "tags": ["high_confidence", "whale", "reference"],
    },
    "Trader2": {
        "address": "0xd3938e1d885f7849215c49d87465709d63400744",
        "notes": "Lotería masiva, Yes a $0.003. WR bajo. No imitar.",
        "tags": ["lottery", "reference"],
    },
}

DB_FILE = "traders_db.json"


# ============================================================
# API
# ============================================================

def api_get(url, retries=3, delay=3):
    """GET con reintentos. Devuelve None si falla."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-finder/2.0")
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(delay)
    return None


# ============================================================
# PASO 1: Obtener mercados de temperatura
# ============================================================

def get_all_temp_markets():
    """
    Pagina por TODOS los mercados de temperatura activos.
    Devuelve lista de dicts con lo mínimo necesario.
    """
    print(f"\n[1/5] Obteniendo mercados de temperatura activos...")

    markets = []
    seen_ids = set()

    for offset in range(0, 1000, 50):
        data = api_get(
            f"{GAMMA_API}/events"
            f"?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=50&offset={offset}"
            f"&order=volume24hr&ascending=false"
        )
        if not data or len(data) == 0:
            break

        for event in data:
            for m in event.get("markets", []):
                mid = m.get("id", "")
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)

                condition_id = m.get("conditionId", "")
                if not condition_id:
                    continue

                question = m.get("question", "")

                # Extraer ciudad
                city_match = re.search(
                    r"temperature in (.+?) (?:be |between |\d)",
                    question, re.IGNORECASE
                )
                city = city_match.group(1).strip() if city_match else "unknown"

                markets.append({
                    "condition_id": condition_id,
                    "question": question,
                    "city": city,
                    "volume_24h": float(m.get("volume24hr", 0)),
                })

        time.sleep(0.3)

    print(f"  Total mercados encontrados: {len(markets)}")

    # Contar ciudades
    cities = {}
    for m in markets:
        cities[m["city"]] = cities.get(m["city"], 0) + 1

    print(f"  Ciudades únicas: {len(cities)}")
    top_5 = sorted(cities.items(), key=lambda x: -x[1])[:5]
    for c, n in top_5:
        print(f"    {c}: {n} mercados")

    return markets


def select_diverse_markets(markets, max_markets):
    """
    Selecciona hasta max_markets mercados con diversidad de ciudades.
    Prioriza ciudades con más mercados (más actividad = más traders).
    """
    # Agrupar por ciudad
    by_city = {}
    for m in markets:
        c = m["city"]
        if c not in by_city:
            by_city[c] = []
        by_city[c].append(m)

    # Selección round-robin: 1 por ciudad, luego 2, etc.
    selected = []
    round_num = 0

    while len(selected) < max_markets and round_num < MAX_PER_CITY:
        added_this_round = 0
        # Ciudades ordenadas por nº de mercados (más mercados primero)
        for city in sorted(by_city.keys(), key=lambda c: -len(by_city[c])):
            city_markets = by_city[city]
            if round_num < len(city_markets):
                selected.append(city_markets[round_num])
                added_this_round += 1
                if len(selected) >= max_markets:
                    break
        if added_this_round == 0:
            break
        round_num += 1

    cities_included = set(m["city"] for m in selected)
    print(f"\n[2/5] Seleccionados {len(selected)} mercados de {len(cities_included)} ciudades")
    return selected


# ============================================================
# PASO 2: Escanear trades de cada mercado
# ============================================================

def scan_market_trades(market):
    """
    Obtiene los trades de un mercado.
    Devuelve lista de trades BUY relevantes.
    """
    cid = market["condition_id"]
    params = urllib.parse.urlencode({
        "market": cid,
        "limit": 200,  # más trades = más traders descubiertos
    })
    data = api_get(f"{DATA_API}/trades?{params}")
    if not data:
        return []

    result = []
    for trade in data:
        # Solo BUY — nos interesa quién compra, no quién vende
        if trade.get("side", "").upper() != "BUY":
            continue

        addr = trade.get("proxyWallet", "").lower()
        if not addr:
            continue

        price = float(trade.get("price", 0))
        size = float(trade.get("size", 0))

        # Ignorar trades insignificantes
        if size < 0.1:
            continue

        result.append({
            "address": addr,
            "price": price,
            "size": size,
            "pseudonym": trade.get("pseudonym", ""),
            "outcome": trade.get("outcome", ""),
            "city": market["city"],
            "question": market["question"],
        })

    return result


# ============================================================
# PASO 3: Acumular perfiles de trader
# ============================================================

def build_trader_profiles(all_trades):
    """
    Desde la lista de todos los trades, construye un perfil
    por dirección. Esto es lo clave de v2: el perfil se construye
    gratis a partir de datos que ya tenemos.
    """
    profiles = {}  # address → perfil

    for trade in all_trades:
        addr = trade["address"]

        if addr not in profiles:
            profiles[addr] = {
                "address": addr,
                "pseudonym": "",
                "prices": [],           # todos los precios de entrada
                "sizes": [],            # todos los tamaños
                "markets": set(),       # condition_ids únicos (via question)
                "cities": {},           # ciudad → nº de trades
                "total_size": 0.0,      # $ total invertido
                "n_trades": 0,
            }

        p = profiles[addr]
        p["prices"].append(trade["price"])
        p["sizes"].append(trade["size"])
        p["total_size"] += trade["size"] * trade["price"]  # coste real
        p["n_trades"] += 1
        p["markets"].add(trade["question"][:80])  # proxy de mercado único

        # Pseudonym: guardar el primero no vacío
        if trade["pseudonym"] and not p["pseudonym"]:
            p["pseudonym"] = trade["pseudonym"]

        city = trade["city"]
        p["cities"][city] = p["cities"].get(city, 0) + 1

    # Convertir sets a conteos y calcular estadísticas
    for addr, p in profiles.items():
        p["n_markets"] = len(p["markets"])
        del p["markets"]  # no serializable

        # Precio medio de entrada
        if p["prices"]:
            p["avg_price"] = sum(p["prices"]) / len(p["prices"])
            p["min_price"] = min(p["prices"])
            p["max_price"] = max(p["prices"])
            p["median_price"] = sorted(p["prices"])[len(p["prices"]) // 2]
        else:
            p["avg_price"] = 0
            p["min_price"] = 0
            p["max_price"] = 0
            p["median_price"] = 0

        # Distribución de precios (para clasificación)
        low = sum(1 for pr in p["prices"] if pr < 0.06)
        mid = sum(1 for pr in p["prices"] if 0.06 <= pr <= 0.90)
        high = sum(1 for pr in p["prices"] if pr > 0.90)
        p["price_dist"] = {"low": low, "mid": mid, "high": high}

        # Limpiar listas grandes (no las guardamos en JSON)
        del p["prices"]
        del p["sizes"]

    return profiles


# ============================================================
# PASO 4: Clasificar y filtrar
# ============================================================

def classify_trader(profile):
    """
    Clasifica un trader por su estrategia basándose en la
    distribución de precios de sus trades.
    
    lottery       → mayoría de compras < 6¢ (apuesta a imposibles)
    mid_range     → mayoría entre 6¢-90¢ (nuestro estilo)
    high_confidence → mayoría > 90¢ (estilo ColdMath, No a 99¢)
    mixed         → sin patrón claro
    """
    dist = profile["price_dist"]
    total = dist["low"] + dist["mid"] + dist["high"]
    if total == 0:
        return "unknown"

    pct_low = dist["low"] / total
    pct_mid = dist["mid"] / total
    pct_high = dist["high"] / total

    # Clasificación por dominancia (>50% de trades en una categoría)
    if pct_low > 0.50:
        return "lottery"
    elif pct_high > 0.50:
        return "high_confidence"
    elif pct_mid > 0.50:
        return "mid_range"
    else:
        return "mixed"


def filter_and_rank(profiles):
    """
    Filtra traders relevantes y los rankea por calidad.
    Solo pasan los mid_range con suficientes mercados e inversión.
    """
    results = []

    for addr, p in profiles.items():
        strategy = classify_trader(p)
        p["strategy"] = strategy

        # Solo nos interesan mid_range (y mixed con suficiente mid)
        if strategy not in ("mid_range", "mixed"):
            continue

        # Para mixed, exigir al menos 30% en mid range
        if strategy == "mixed" and p["price_dist"]["mid"] / max(p["n_trades"], 1) < 0.30:
            continue

        # Filtros de volumen
        if p["n_markets"] < MIN_MARKETS:
            continue
        if p["total_size"] < MIN_TOTAL_SIZE:
            continue
        if p["total_size"] > MAX_TOTAL_SIZE:
            continue

        # Score: combina diversidad de mercados + volumen
        # Más mercados = más consistencia, más volumen = más convicción
        score = p["n_markets"] * 2 + min(p["total_size"] / 10, 20)
        p["relevance_score"] = round(score, 1)

        results.append(p)

    # Rankear por score
    results.sort(key=lambda x: -x["relevance_score"])
    return results


# ============================================================
# PASO 5: Guardar en traders_db.json
# ============================================================

def load_db():
    """Carga o crea traders_db.json."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    # DB nueva: empezar con los traders core
    db = {"traders": {}, "meta": {}}
    for name, info in CORE_TRADERS.items():
        db["traders"][name] = {
            "address": info["address"],
            "source": "manual",
            "added": datetime.now(timezone.utc).isoformat(),
            "tags": info.get("tags", []),
            "notes": info.get("notes", ""),
            "strategy": "reference",
        }
    return db


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def update_db_with_results(db, ranked_traders, scan_stats):
    """
    Añade traders nuevos a la DB y actualiza los existentes.
    Devuelve cuántos se añadieron.
    """
    # Addresses ya en DB
    existing = {
        info["address"].lower(): name
        for name, info in db["traders"].items()
    }

    added = 0
    updated = 0

    for p in ranked_traders:
        addr = p["address"].lower()

        if addr in existing:
            # Ya existe → actualizar stats de descubrimiento
            name = existing[addr]
            db["traders"][name]["last_discovery"] = datetime.now(timezone.utc).isoformat()
            db["traders"][name]["discovery_n_markets"] = p["n_markets"]
            db["traders"][name]["discovery_total_size"] = round(p["total_size"], 2)
            db["traders"][name]["discovery_avg_price"] = round(p["avg_price"], 3)
            db["traders"][name]["discovery_score"] = p["relevance_score"]
            db["traders"][name]["strategy"] = p["strategy"]
            updated += 1
        else:
            # Nuevo trader → añadir
            # Generar nombre: usar pseudonym si existe, sino auto
            if p["pseudonym"]:
                name = p["pseudonym"][:20]
                # Evitar colisión de nombres
                if name in db["traders"]:
                    name = f"{name}_{addr[:6]}"
            else:
                # Auto-nombre basado en orden de descubrimiento
                idx = sum(1 for info in db["traders"].values()
                          if info.get("source") == "auto_discovery") + 1
                name = f"Auto_{idx:03d}"

            # Top 3 ciudades
            top_cities = sorted(p["cities"].items(), key=lambda x: -x[1])[:3]
            cities_str = ", ".join(f"{c}({n})" for c, n in top_cities)

            db["traders"][name] = {
                "address": addr,
                "source": "auto_discovery",
                "added": datetime.now(timezone.utc).isoformat(),
                "pseudonym": p.get("pseudonym", ""),
                "tags": [p["strategy"], "auto_discovered"],
                "notes": f"Score={p['relevance_score']}, {p['n_markets']} mercados, "
                         f"${p['total_size']:.0f} invertido, ciudades: {cities_str}",
                "strategy": p["strategy"],
                "discovery_n_markets": p["n_markets"],
                "discovery_total_size": round(p["total_size"], 2),
                "discovery_avg_price": round(p["avg_price"], 3),
                "discovery_score": p["relevance_score"],
                "top_cities": dict(top_cities),
            }
            existing[addr] = name
            added += 1

    # Metadata del último scan
    db["meta"] = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": scan_stats["markets_scanned"],
        "total_trades_seen": scan_stats["total_trades"],
        "unique_traders_seen": scan_stats["unique_traders"],
        "traders_passed_filter": len(ranked_traders),
        "new_added": added,
        "existing_updated": updated,
    }

    return added, updated


# ============================================================
# MAIN
# ============================================================

def main(quick=False):
    max_markets = MAX_MARKETS_QUICK if quick else MAX_MARKETS_SCAN
    mode = "RÁPIDO" if quick else "COMPLETO"

    print("=" * 60)
    print(f"🔍 FIND_TRADERS v2 — Descubrimiento inteligente ({mode})")
    print(f"   Escaneando hasta {max_markets} mercados de temperatura")
    print(f"   Buscando traders mid_range con {MIN_MARKETS}+ mercados")
    print("=" * 60)

    # Paso 1: obtener todos los mercados
    all_markets = get_all_temp_markets()
    if not all_markets:
        print("❌ No se pudieron obtener mercados.")
        return

    # Paso 2: seleccionar con diversidad
    selected = select_diverse_markets(all_markets, max_markets)

    # Paso 3: escanear trades
    print(f"\n[3/5] Escaneando trades de {len(selected)} mercados...")
    all_trades = []
    for i, mkt in enumerate(selected):
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  [{i+1}/{len(selected)}] {mkt['city']}...")
        trades = scan_market_trades(mkt)
        all_trades.extend(trades)
        time.sleep(0.3)  # rate limit

    unique_addrs = set(t["address"] for t in all_trades)
    print(f"  Total trades BUY: {len(all_trades)}")
    print(f"  Traders únicos: {len(unique_addrs)}")

    # Paso 4: construir perfiles
    print(f"\n[4/5] Construyendo perfiles de {len(unique_addrs)} traders...")
    profiles = build_trader_profiles(all_trades)

    # Clasificar todos
    strategy_counts = {"lottery": 0, "mid_range": 0, "high_confidence": 0, "mixed": 0, "unknown": 0}
    for addr, p in profiles.items():
        s = classify_trader(p)
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    print(f"  Clasificación del ecosistema:")
    for s, n in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        if n > 0:
            print(f"    {s}: {n} traders")

    # Filtrar y rankear
    ranked = filter_and_rank(profiles)
    print(f"\n[5/5] {len(ranked)} traders pasan filtro mid_range + {MIN_MARKETS}+ mercados")

    # Mostrar resultados
    print(f"\n{'='*60}")
    print(f"✅ TOP TRADERS RELEVANTES")
    print(f"{'='*60}")

    if not ranked:
        print("\n  Ningún trader pasó todos los filtros.")
        print(f"  Prueba con --quick o revisa los umbrales.")
    else:
        for i, p in enumerate(ranked[:15]):
            pseudo = f" ({p['pseudonym']})" if p.get("pseudonym") else ""
            top_cities = sorted(p["cities"].items(), key=lambda x: -x[1])[:3]
            cities_str = ", ".join(f"{c}" for c, _ in top_cities)

            print(f"\n  #{i+1} {p['address'][:14]}...{pseudo}")
            print(f"    Score: {p['relevance_score']} | "
                  f"Mercados: {p['n_markets']} | "
                  f"Invertido: ${p['total_size']:.0f}")
            print(f"    Precio medio: ${p['avg_price']:.3f} | "
                  f"Rango: ${p['min_price']:.2f}-${p['max_price']:.2f}")
            print(f"    Distribución: low={p['price_dist']['low']} "
                  f"mid={p['price_dist']['mid']} "
                  f"high={p['price_dist']['high']} → {p['strategy']}")
            print(f"    Ciudades: {cities_str}")

    # Guardar en DB
    print(f"\n{'='*60}")
    print(f"💾 Actualizando {DB_FILE}...")
    db = load_db()

    scan_stats = {
        "markets_scanned": len(selected),
        "total_trades": len(all_trades),
        "unique_traders": len(unique_addrs),
    }
    added, updated = update_db_with_results(db, ranked, scan_stats)
    save_db(db)

    print(f"  Traders nuevos añadidos: {added}")
    print(f"  Traders existentes actualizados: {updated}")
    print(f"  Total en DB: {len(db['traders'])}")
    print(f"\n✅ Listo. Ejecuta trader_analyzer.py para análisis profundo.")

    return {
        "added": added,
        "updated": updated,
        "total_found": len(ranked),
        "scan_stats": scan_stats,
    }


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    main(quick=quick)
