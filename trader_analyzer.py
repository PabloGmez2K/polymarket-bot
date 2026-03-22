"""
trader_analyzer.py — Análisis estratégico multi-trader
=======================================================

Parte del pipeline de inteligencia de mercado:

  find_traders.py → traders_db.json → trader_analyzer.py → trader_history.json

Analiza todos los traders en traders_db.json más los hardcodeados,
detecta consenso, valida edge real, y acumula histórico para
optimizar la estrategia del bot.

Uso:
    python trader_analyzer.py
"""

import urllib.request
import urllib.parse
import json
import re
import os
from datetime import datetime, timezone

# ============================================================
# TRADERS CONOCIDOS (hardcoded — siempre se analizan)
# ============================================================
TRADERS_CORE = {
    "ColdMath": "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11",
    "Trader2":  "0xd3938e1d885f7849215c49d87465709d63400744",
    "Trader3":  "0x09f4265f01d6f73d6cf3ccdb8a37e1f7bb42e9c2",
}

# Tu dirección para comparar (opcional)
MY_ADDRESS = ""

# Nuestro rango de precio operativo
MIN_PRICE = 0.08
MAX_PRICE = 0.92

# Archivos del pipeline
DB_FILE      = "traders_db.json"      # registro de traders descubiertos
HISTORY_FILE = "trader_history.json"  # histórico de análisis

DATA_API  = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


# ============================================================
# TRADERS_DB — registro persistente
# ============================================================

def load_traders_db():
    """
    Carga traders_db.json y devuelve el dict completo de traders.
    Si no existe, lo crea con los traders core.
    El archivo tiene esta estructura:
    {
      "traders": {
        "ColdMath": {
          "address": "0x...",
          "source": "manual",
          "added": "2026-03-22T...",
          "tags": ["high_bankroll", "no_strategy"],
          "notes": "Opera No a 0.99, no relevante para estrategia"
        },
        "Nuevo1": {
          "address": "0x...",
          "source": "find_traders",
          "added": "2026-03-22T...",
          "win_rate_discovery": 62.5,
          "bankroll_discovery": 45.0,
          "tags": ["our_range", "small_bankroll"]
        }
      }
    }
    """
    if not os.path.exists(DB_FILE):
        # Crear con los traders core
        db = {"traders": {}}
        for name, address in TRADERS_CORE.items():
            db["traders"][name] = {
                "address": address,
                "source": "manual",
                "added": datetime.now(timezone.utc).isoformat(),
                "tags": [],
                "notes": "",
            }
        save_traders_db(db)
        print(f"  Creado {DB_FILE} con {len(TRADERS_CORE)} traders core")
        return db

    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_traders_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def get_all_traders(db):
    """
    Devuelve dict {nombre: address} de todos los traders en la DB,
    fusionado con los core por si acaso no estaban en el archivo.
    """
    traders = dict(TRADERS_CORE)  # empieza con los core
    for name, info in db["traders"].items():
        addr = info.get("address", "")
        if addr and name not in traders:
            traders[name] = addr
    return traders


def add_trader_to_db(db, name, address, source="manual", **kwargs):
    """Añade un trader nuevo a la DB si no existe ya."""
    # Comprobar si la address ya está (aunque con otro nombre)
    existing = {
        info["address"].lower(): n
        for n, info in db["traders"].items()
    }
    if address.lower() in existing:
        print(f"  {address[:14]}... ya existe como '{existing[address.lower()]}'")
        return False

    db["traders"][name] = {
        "address": address,
        "source": source,
        "added": datetime.now(timezone.utc).isoformat(),
        "tags": kwargs.get("tags", []),
        "notes": kwargs.get("notes", ""),
        **{k: v for k, v in kwargs.items() if k not in ("tags", "notes")},
    }
    return True


def update_trader_stats(db, name, stats):
    """Actualiza las estadísticas de un trader tras el análisis."""
    if name in db["traders"]:
        db["traders"][name].update({
            "last_analyzed": datetime.now(timezone.utc).isoformat(),
            "last_win_rate": stats.get("win_rate"),
            "last_n_positions": stats.get("n_positions"),
            "last_our_range": stats.get("n_our_range"),
            "last_pnl_closed": stats.get("pnl_closed"),
        })


# ============================================================
# API
# ============================================================
def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-analyzer/2.0")
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                raise e
            import time; time.sleep(3)


def get_positions(address, limit=50):
    """Posiciones activas de un trader."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "sizeThreshold": "0.1",
            "limit": limit,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        return api_get(f"{DATA_API}/positions?{params}")
    except Exception as e:
        print(f"  Error posiciones: {e}")
        return []


def get_activity(address, limit=50):
    """Actividad reciente de un trader."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "limit": limit,
        })
        return api_get(f"{DATA_API}/activity?{params}")
    except Exception as e:
        print(f"  Error actividad: {e}")
        return []


def get_closed_positions(address, limit=100):
    """Posiciones cerradas para calcular win rate."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "sizeThreshold": "0.1",
            "limit": limit,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        return api_get(f"{DATA_API}/positions?{params}&closed=true")
    except Exception:
        return []


# ============================================================
# PARSEO
# ============================================================
def parse_city(title):
    """Extrae la ciudad de una pregunta de temperatura."""
    match = re.search(r"temperature in (.+?) (?:be |between |\d)", title, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_condition(title):
    """
    Clasifica el tipo de condición:
      exact       → "be 13°C on"
      at_or_above → "13°C or higher/above"
      at_or_below → "13°C or below"
      range       → "between 60-65°F"
    """
    t = title.lower()
    if "or higher" in t or "or above" in t:
        return "at_or_above"
    elif "or below" in t:
        return "at_or_below"
    elif "between" in t:
        return "range"
    else:
        return "exact"


def parse_temp(title):
    """Extrae temperatura y unidad."""
    match = re.search(r"(\d+)°([CF])", title)
    if match:
        return int(match.group(1)), match.group(2).upper()
    return None, None


def market_key(position):
    """
    Clave única para identificar un mercado entre traders.
    Usamos el título truncado (55 chars) como proxy —
    suficiente para detectar coincidencias.
    """
    title = position.get("title", "")
    return title[:60].strip().lower()


# ============================================================
# ANÁLISIS POR TRADER
# ============================================================
def analyze_trader(name, address):
    """Analiza un trader y devuelve un dict con todos sus datos."""
    print(f"\n  Analizando {name} ({address[:14]}...)...")

    positions = get_positions(address)
    activity = get_activity(address)
    closed = get_closed_positions(address, limit=100)

    # --- Estadísticas básicas ---
    wins = sum(1 for p in closed if float(p.get("cashPnl", 0)) > 0)
    losses = sum(1 for p in closed if float(p.get("cashPnl", 0)) < 0)
    total_pnl_closed = sum(float(p.get("cashPnl", 0)) for p in closed)
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0

    # --- Distribución de precios ---
    price_dist = {"0.00-0.10": 0, "0.10-0.50": 0, "0.50-0.90": 0, "0.90-1.00": 0}
    for p in positions:
        price = float(p.get("avgPrice", 0))
        if price < 0.10:
            price_dist["0.00-0.10"] += 1
        elif price < 0.50:
            price_dist["0.10-0.50"] += 1
        elif price < 0.90:
            price_dist["0.50-0.90"] += 1
        else:
            price_dist["0.90-1.00"] += 1

    # --- Posiciones en nuestro rango ---
    our_range = [
        p for p in positions
        if MIN_PRICE <= float(p.get("avgPrice", 0)) <= MAX_PRICE
    ]

    # --- Condiciones apostadas ---
    conditions = {}
    for p in positions:
        c = parse_condition(p.get("title", ""))
        conditions[c] = conditions.get(c, 0) + 1

    # --- Ciudades ---
    cities = {}
    for p in positions:
        city = parse_city(p.get("title", ""))
        if city:
            cities[city] = cities.get(city, 0) + 1

    # --- Timing ---
    hours = {}
    for t in activity:
        ts = t.get("timestamp", t.get("createdAt", ""))
        if ts:
            try:
                dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                h = dt.hour
                hours[h] = hours.get(h, 0) + 1
            except Exception:
                pass

    # --- Movimiento de precio (validación de edge) ---
    # Para posiciones con ganancia >20%, el precio se movió significativamente
    # después de la entrada → confirma edge real
    big_movers = []
    for p in positions:
        pct = float(p.get("percentPnl", 0))
        if abs(pct) >= 20:
            city = parse_city(p.get("title", ""))
            title_short = p.get("title", "?")[:55]
            outcome = p.get("outcome", "?")
            avg = float(p.get("avgPrice", 0))
            cur = float(p.get("curPrice", 0))
            pnl = float(p.get("cashPnl", 0))
            big_movers.append({
                "city": city,
                "title": title_short,
                "outcome": outcome,
                "avg_price": avg,
                "cur_price": cur,
                "pct_pnl": pct,
                "cash_pnl": pnl,
            })

    return {
        "name": name,
        "address": address,
        "n_positions": len(positions),
        "n_closed": len(closed),
        "win_rate": round(win_rate, 1),
        "wins": wins,
        "losses": losses,
        "pnl_closed": round(total_pnl_closed, 2),
        "price_distribution": price_dist,
        "n_our_range": len(our_range),
        "our_range_positions": [
            {
                "title": p.get("title", "?")[:60],
                "outcome": p.get("outcome", "?"),
                "avg_price": float(p.get("avgPrice", 0)),
                "cur_price": float(p.get("curPrice", 0)),
                "pct_pnl": float(p.get("percentPnl", 0)),
                "cash_pnl": float(p.get("cashPnl", 0)),
                "condition": parse_condition(p.get("title", "")),
                "city": parse_city(p.get("title", "")),
            }
            for p in our_range
        ],
        "conditions": conditions,
        "cities": cities,
        "timing_hours": hours,
        "big_movers": big_movers,
        "positions_raw_keys": [market_key(p) for p in positions],
    }


# ============================================================
# CONSENSO ENTRE TRADERS
# ============================================================
def find_consensus(trader_data_list):
    """
    Detecta mercados donde coinciden 2 o más traders DISTINTOS.
    Filtra casos donde el mismo trader aparece varias veces
    en el mismo mercado (posiciones YES y NO a la vez).
    """
    market_to_traders = {}
    for td in trader_data_list:
        for key in td["positions_raw_keys"]:
            if key not in market_to_traders:
                market_to_traders[key] = []
            # Solo añadir si este trader no está ya para este mercado
            if td["name"] not in market_to_traders[key]:
                market_to_traders[key].append(td["name"])

    # Solo mercados con 2+ traders DISTINTOS
    consensus = {
        k: v for k, v in market_to_traders.items()
        if len(v) >= 2
    }
    return consensus


# ============================================================
# MOSTRAR RESULTADOS
# ============================================================
def print_results(trader_data_list, consensus):
    print(f"\n{'='*60}")
    print("RESUMEN POR TRADER")
    print(f"{'='*60}")

    for td in trader_data_list:
        print(f"\n📊 {td['name']} ({td['address'][:14]}...)")
        print(f"  Posiciones activas: {td['n_positions']}")
        print(f"  Win rate (cerradas): {td['win_rate']:.1f}% "
              f"({td['wins']}W/{td['losses']}L, PnL: ${td['pnl_closed']:+.2f})")

        # Distribución de precios
        dist = td["price_distribution"]
        print(f"  Precios — bajo(<0.10):{dist['0.00-0.10']} "
              f"mid(0.10-0.90):{dist['0.10-0.50']+dist['0.50-0.90']} "
              f"alto(>0.90):{dist['0.90-1.00']}")

        # Horario de actividad
        if td["timing_hours"]:
            peak_hour = max(td["timing_hours"], key=td["timing_hours"].get)
            print(f"  Hora pico de actividad: {peak_hour:02d}:00 UTC "
                  f"({td['timing_hours'][peak_hour]} trades)")

        # Condiciones favoritas
        if td["conditions"]:
            top_cond = max(td["conditions"], key=td["conditions"].get)
            print(f"  Condición más usada: {top_cond} "
                  f"({td['conditions'][top_cond]} posiciones)")

    # ---- CONSENSO ----
    print(f"\n{'='*60}")
    print("🎯 CONSENSO ENTRE TRADERS (mercados compartidos)")
    print(f"{'='*60}")
    if consensus:
        for market_title, traders_in in consensus.items():
            print(f"\n  ✅ {' + '.join(traders_in)}:")
            print(f"     {market_title[:70]}")
    else:
        print("  No hay mercados compartidos en este momento.")

    # ---- POSICIONES EN NUESTRO RANGO ----
    print(f"\n{'='*60}")
    print(f"💡 POSICIONES EN NUESTRO RANGO ({MIN_PRICE}-{MAX_PRICE})")
    print(f"   → Estas son las más relevantes para nuestra estrategia")
    print(f"{'='*60}")

    found_any = False
    for td in trader_data_list:
        if td["our_range_positions"]:
            found_any = True
            print(f"\n  {td['name']} ({len(td['our_range_positions'])} posiciones):")
            for p in td["our_range_positions"]:
                icon = "🟢" if p["pct_pnl"] >= 0 else "🔴"
                move = p["cur_price"] - p["avg_price"]
                print(f"    {icon} {p['outcome']} | entrada: ${p['avg_price']:.2f} → "
                      f"ahora: ${p['cur_price']:.2f} ({move:+.2f}) | "
                      f"PnL: {p['pct_pnl']:+.1f}%")
                print(f"       {p['title'][:60]}")
                print(f"       Ciudad: {p['city']} | Condición: {p['condition']}")
    if not found_any:
        print("  Ningún trader tiene posiciones en nuestro rango ahora mismo.")

    # ---- MOVIMIENTOS DE PRECIO GRANDES ----
    print(f"\n{'='*60}")
    print("📈 VALIDACIÓN DE EDGE (movimientos >20% desde entrada)")
    print(f"   → Si subió mucho después de que entraron, el edge era real")
    print(f"{'='*60}")

    found_movers = False
    for td in trader_data_list:
        if td["big_movers"]:
            found_movers = True
            print(f"\n  {td['name']}:")
            for m in td["big_movers"][:5]:  # Top 5
                icon = "🟢" if m["pct_pnl"] >= 0 else "🔴"
                print(f"    {icon} {m['outcome']} @ ${m['avg_price']:.3f} → "
                      f"${m['cur_price']:.3f} ({m['pct_pnl']:+.0f}%) | "
                      f"${m['cash_pnl']:+.2f}")
                print(f"       {m['title'][:60]}")
    if not found_movers:
        print("  Sin movimientos grandes en este momento.")

    # ---- CIUDADES CON MAYOR ACTIVIDAD AGREGADA ----
    print(f"\n{'='*60}")
    print("🌍 CIUDADES CON MAYOR ACTIVIDAD (todos los traders)")
    print(f"{'='*60}")
    city_total = {}
    for td in trader_data_list:
        for city, count in td["cities"].items():
            city_total[city] = city_total.get(city, 0) + count

    our_cities = {
        "Seoul", "London", "Tel Aviv", "Shanghai", "Tokyo", "New York City",
        "Beijing", "Hong Kong", "Singapore", "Toronto", "Chicago", "Wellington",
        "Munich", "Warsaw", "Ankara", "Atlanta", "Shenzhen", "Paris",
        "Buenos Aires", "Miami", "Madrid", "Seattle", "Dallas", "Lucknow",
        "Sao Paulo", "Taipei", "Milan", "Chongqing", "Chengdu", "Wuhan",
    }

    for city, count in sorted(city_total.items(), key=lambda x: -x[1])[:15]:
        status = "✅" if city in our_cities else "❌ FALTA"
        print(f"  {city}: {count} posiciones totales  {status}")


# ============================================================
# GUARDAR HISTÓRICO
# ============================================================
def save_history(trader_data_list, consensus):
    """
    Guarda el análisis en trader_history.json.
    Cada ejecución añade una entrada nueva — nunca sobreescribe.
    Así puedes ver cómo evolucionan las posiciones con el tiempo.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traders": [
            {
                "name": td["name"],
                "address": td["address"],
                "n_positions": td["n_positions"],
                "win_rate": td["win_rate"],
                "pnl_closed": td["pnl_closed"],
                "our_range_count": td["n_our_range"],
                "price_distribution": td["price_distribution"],
                "conditions": td["conditions"],
                "top_cities": dict(
                    sorted(td["cities"].items(), key=lambda x: -x[1])[:10]
                ),
                "timing_hours": td["timing_hours"],
                "our_range_positions": td["our_range_positions"],
                "big_movers": td["big_movers"],
            }
            for td in trader_data_list
        ],
        "consensus_markets": list(consensus.keys()),
        "n_consensus": len(consensus),
    }

    # Cargar histórico existente
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(entry)

    # Guardar
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Análisis guardado en {HISTORY_FILE} "
          f"(total entradas: {len(history)})")


def print_history_summary():
    """Muestra tendencias del histórico si hay más de una entrada."""
    if not os.path.exists(HISTORY_FILE):
        return

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return

    if len(history) < 2:
        return

    print(f"\n{'='*60}")
    print(f"📅 TENDENCIAS HISTÓRICAS ({len(history)} análisis guardados)")
    print(f"{'='*60}")

    first = history[0]
    last = history[-1]
    print(f"  Primer análisis: {first['timestamp'][:16]} UTC")
    print(f"  Último análisis: {last['timestamp'][:16]} UTC")
    print(f"  Mercados en consenso — antes: {first['n_consensus']} | "
          f"ahora: {last['n_consensus']}")

    # Evolución del win rate por trader
    for t_now in last["traders"]:
        name = t_now["name"]
        t_first = next((t for t in first["traders"] if t["name"] == name), None)
        if t_first:
            wr_delta = t_now["win_rate"] - t_first["win_rate"]
            print(f"  {name} — win rate: {t_first['win_rate']:.1f}% → "
                  f"{t_now['win_rate']:.1f}% ({wr_delta:+.1f}pp)")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("🔍 ANALIZADOR MULTI-TRADER — Polymarket")

    # Cargar DB de traders
    print(f"\nCargando {DB_FILE}...")
    db = load_traders_db()
    all_traders = get_all_traders(db)
    print(f"  {len(all_traders)} traders a analizar: {', '.join(all_traders.keys())}")
    print(f"Buscando posiciones en rango ${MIN_PRICE}-${MAX_PRICE}...\n")

    # Analizar cada trader
    trader_data_list = []
    for name, address in all_traders.items():
        data = analyze_trader(name, address)
        trader_data_list.append(data)
        # Actualizar estadísticas en la DB
        update_trader_stats(db, name, data)

    # Guardar DB actualizada
    save_traders_db(db)

    # Detectar consenso
    consensus = find_consensus(trader_data_list)

    # Mostrar resultados en consola
    print_results(trader_data_list, consensus)

    # Mostrar tendencias históricas
    print_history_summary()

    # Guardar en histórico
    save_history(trader_data_list, consensus)

    print(f"\n✅ Análisis completado.")
    print(f"   {DB_FILE}: {len(db['traders'])} traders registrados")
    print(f"   Para añadir traders nuevos: edita {DB_FILE} o ejecuta find_traders.py")
