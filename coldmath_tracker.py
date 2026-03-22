"""
coldmath_tracker.py — Seguidor de actividad de traders en Polymarket
=====================================================================

Uso:
    1. Pon la wallet address de ColdMath en COLDMATH_ADDRESS
    2. python coldmath_tracker.py

Cómo obtener la wallet address:
    - Ve a polymarket.com/@ColdMath
    - F12 → Network → Recarga → filtra por "profile" o "ColdMath"
    - Busca la llamada a gamma-api o data-api
    - El campo "address" o "proxyWallet" es el que necesitas (0x...)

Qué muestra:
    - Posiciones activas del trader
    - Trades recientes (actividad)
    - Comparación con nuestras posiciones
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

# ============================================================
# CONFIGURACIÓN — pon aquí la address real de ColdMath
# ============================================================
COLDMATH_ADDRESS = "0x594edb9112f526fa6a80b8f858a6379c8a2c1c11"

# Nuestra dirección (para comparar posiciones)
MY_ADDRESS = ""  # ← opcional: pon tu FUNDER address para comparar

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-tracker/1.0")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


# ============================================================
# 1. PERFIL PÚBLICO
# ============================================================
def get_profile(address):
    """Datos básicos del trader: nombre, ganancias, número de trades."""
    try:
        data = api_get(f"{GAMMA_API}/profiles?id={address}")
        if data:
            p = data[0] if isinstance(data, list) else data
            print(f"\n{'='*50}")
            print(f"PERFIL: {p.get('name', '?')} (@{p.get('slug', '?')})")
            print(f"  Trades totales: {p.get('tradesCount', '?')}")
            print(f"  PnL total:      ${p.get('profit', 0):.2f}")
            print(f"  Miembro desde:  {p.get('joinedAt', '?')[:10]}")
            print(f"{'='*50}")
            return p
    except Exception as e:
        print(f"Error perfil: {e}")
    return {}


# ============================================================
# 2. POSICIONES ACTIVAS
# ============================================================
def get_positions(address, label=""):
    """Qué mercados tiene abiertos ahora mismo."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "sizeThreshold": "0.1",
            "limit": "50",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        positions = api_get(f"{DATA_API}/positions?{params}")

        print(f"\n📊 POSICIONES ACTIVAS {label}({len(positions)} totales)")
        print("-" * 50)

        for i, pos in enumerate(positions[:20]):  # Mostrar top 20
            title = pos.get("title", "?")[:60]
            outcome = pos.get("outcome", "?")
            size = float(pos.get("size", 0))
            avg_price = float(pos.get("avgPrice", 0))
            cur_price = float(pos.get("curPrice", 0))
            pnl = float(pos.get("cashPnl", 0))
            pct_pnl = float(pos.get("percentPnl", 0))

            icon = "🟢" if pnl >= 0 else "🔴"
            print(f"{i+1:2}. {icon} {outcome} @ ${avg_price:.2f} → ${cur_price:.2f}")
            print(f"    {title}")
            print(f"    {size:.1f} shares | PnL: ${pnl:+.2f} ({pct_pnl:+.1f}%)")

        return positions
    except Exception as e:
        print(f"Error posiciones: {e}")
        return []


# ============================================================
# 3. ACTIVIDAD RECIENTE (trades)
# ============================================================
def get_activity(address, limit=20):
    """Últimos trades ejecutados."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "limit": limit,
        })
        # Endpoint de trades
        trades = api_get(f"{DATA_API}/activity?{params}")

        print(f"\n⚡ ACTIVIDAD RECIENTE (últimos {limit} trades)")
        print("-" * 50)

        for t in trades[:limit]:
            # Los campos exactos dependen de la API — explorar con print(t)
            side = t.get("side", t.get("type", "?"))
            outcome = t.get("outcome", "?")
            price = float(t.get("price", t.get("usdcSize", 0) or 0))
            size = float(t.get("size", t.get("shares", 0) or 0))
            title = (t.get("title", t.get("market", {}).get("question", "?")))[:55]
            ts = t.get("timestamp", t.get("createdAt", ""))
            if ts:
                try:
                    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                    ts_str = dt.strftime("%m-%d %H:%M UTC")
                except Exception:
                    ts_str = str(ts)[:16]
            else:
                ts_str = "?"

            print(f"  [{ts_str}] {side} {outcome} @ ${price:.3f} ({size:.1f}sh)")
            print(f"    {title}")

        return trades
    except Exception as e:
        print(f"Error actividad: {e}")
        # Mostrar los campos disponibles para debug
        try:
            raw = api_get(f"{DATA_API}/activity?user={address.lower()}&limit=1")
            print(f"  Campos disponibles: {list(raw[0].keys()) if raw else 'vacío'}")
        except Exception:
            pass
        return []


# ============================================================
# 4. COMPARAR POSICIONES (ColdMath vs nosotros)
# ============================================================
def compare_positions(their_positions, my_positions):
    """¿En qué mercados coincidimos? ¿Dónde van en dirección opuesta?"""
    if not my_positions:
        return

    their_markets = {}
    for p in their_positions:
        cid = p.get("conditionId", p.get("market", {}).get("conditionId", ""))
        if cid:
            their_markets[cid] = p

    my_markets = {}
    for p in my_positions:
        cid = p.get("conditionId", p.get("market", {}).get("conditionId", ""))
        if cid:
            my_markets[cid] = p

    same = set(their_markets) & set(my_markets)
    only_them = set(their_markets) - set(my_markets)

    print(f"\n🔍 COMPARACIÓN DE POSICIONES")
    print("-" * 50)
    print(f"  ColdMath tiene: {len(their_markets)} mercados")
    print(f"  Nosotros tenemos: {len(my_markets)} mercados")
    print(f"  En común: {len(same)}")

    if same:
        print("\n  COINCIDENCIAS:")
        for cid in same:
            t = their_markets[cid]
            m = my_markets[cid]
            t_out = t.get("outcome", "?")
            m_out = m.get("outcome", "?")
            title = t.get("title", "?")[:50]
            align = "✅ MISMA dirección" if t_out == m_out else "⚠️ OPUESTA"
            print(f"    {align}: {title}")
            print(f"      ColdMath: {t_out} @ ${float(t.get('avgPrice',0)):.2f}")
            print(f"      Nosotros: {m_out} @ ${float(m.get('avgPrice',0)):.2f}")

    if only_them:
        print(f"\n  SOLO COLDMATH ({len(only_them)} mercados — posibles ideas):")
        for cid in list(only_them)[:5]:
            p = their_markets[cid]
            title = p.get("title", "?")[:55]
            outcome = p.get("outcome", "?")
            price = float(p.get("avgPrice", 0))
            cur = float(p.get("curPrice", 0))
            pnl = float(p.get("cashPnl", 0))
            print(f"    {outcome} @ ${price:.2f} (ahora ${cur:.2f}, PnL ${pnl:+.2f})")
            print(f"    {title}")


# ============================================================
# MAIN
# ============================================================
def get_closed_positions(address, limit=50):
    """Posiciones ya cerradas — para medir win rate real."""
    try:
        params = urllib.parse.urlencode({
            "user": address.lower(),
            "sizeThreshold": "0.1",
            "limit": limit,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        })
        positions = api_get(f"{DATA_API}/positions?{params}&closed=true")
        return positions
    except Exception as e:
        # Algunos endpoints usan parámetro distinto
        try:
            params2 = urllib.parse.urlencode({
                "user": address.lower(),
                "limit": limit,
                "redeemed": "true",
            })
            positions = api_get(f"{DATA_API}/positions?{params2}")
            return positions
        except Exception as e2:
            print(f"Error posiciones cerradas: {e2}")
            return []


def extract_cities(positions):
    """Extrae todas las ciudades de las posiciones."""
    import re
    cities = {}
    pattern = re.compile(
        r"temperature in (.+?) (?:be |between |\d)",
        re.IGNORECASE
    )
    for pos in positions:
        title = pos.get("title", "")
        match = pattern.search(title)
        if match:
            city = match.group(1).strip()
            if city not in cities:
                cities[city] = 0
            cities[city] += 1
    return cities


def analyze_timing(activity):
    """¿A qué horas opera ColdMath?"""
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
    return hours


def analyze_strategy(positions, activity):
    """
    ¿Qué patrón de precios usa ColdMath?
    Clasifica sus posiciones en rangos de precio.
    """
    price_ranges = {
        "0.00-0.10 (very low — lotería)": 0,
        "0.10-0.50 (mid-low)":            0,
        "0.50-0.90 (mid)":                0,
        "0.90-0.95 (high)":               0,
        "0.95-1.00 (very high — seguro)": 0,
    }

    for pos in positions:
        price = float(pos.get("avgPrice", 0))
        if price < 0.10:
            price_ranges["0.00-0.10 (very low — lotería)"] += 1
        elif price < 0.50:
            price_ranges["0.10-0.50 (mid-low)"] += 1
        elif price < 0.90:
            price_ranges["0.50-0.90 (mid)"] += 1
        elif price < 0.95:
            price_ranges["0.90-0.95 (high)"] += 1
        else:
            price_ranges["0.95-1.00 (very high — seguro)"] += 1

    return price_ranges


if __name__ == "__main__":
    print(f"🔍 Analizando trader: {COLDMATH_ADDRESS[:14]}...")

    # 1. Perfil
    profile = get_profile(COLDMATH_ADDRESS)

    # 2. Posiciones activas (todas, no solo 20)
    their_positions = get_positions(COLDMATH_ADDRESS, label="(ColdMath) ")

    # 3. Actividad reciente (más datos para análisis de timing)
    activity = get_activity(COLDMATH_ADDRESS, limit=50)

    # 4. Comparar con nuestras posiciones
    if MY_ADDRESS:
        my_positions = get_positions(MY_ADDRESS, label="(nosotros) ")
        compare_positions(their_positions, my_positions)

    # ============================================================
    # ANÁLISIS ESTRATÉGICO
    # ============================================================

    print(f"\n{'='*50}")
    print("🧠 ANÁLISIS ESTRATÉGICO")
    print(f"{'='*50}")

    # Ciudades que cubre
    cities = extract_cities(their_positions)
    our_cities = {
        "Seoul", "London", "Tel Aviv", "Shanghai", "Tokyo",
        "New York City", "Beijing", "Hong Kong", "Singapore",
        "Toronto", "Chicago", "Wellington", "Munich", "Warsaw",
        "Ankara", "Atlanta", "Shenzhen", "Paris", "Buenos Aires",
    }

    print(f"\n🌍 CIUDADES DE COLDMATH ({len(cities)} detectadas):")
    missing = []
    for city, count in sorted(cities.items(), key=lambda x: -x[1]):
        in_ours = "✅" if city in our_cities else "❌ FALTA EN NUESTRO BOT"
        print(f"  {city}: {count} posiciones  {in_ours}")
        if city not in our_cities:
            missing.append(city)

    if missing:
        print(f"\n⚠️  Ciudades que ColdMath cubre y nosotros no ({len(missing)}):")
        for c in missing:
            print(f"    → {c}")

    # Distribución de precios
    price_dist = analyze_strategy(their_positions, activity)
    print(f"\n💰 DISTRIBUCIÓN DE PRECIOS (posiciones activas):")
    for rng, count in price_dist.items():
        bar = "█" * count
        print(f"  {rng}: {count}  {bar}")

    # Timing
    timing = analyze_timing(activity)
    if timing:
        print(f"\n⏰ HORAS DE ACTIVIDAD (UTC):")
        for h in sorted(timing.keys()):
            bar = "█" * timing[h]
            print(f"  {h:02d}:00  {bar} ({timing[h]} trades)")

    # Posiciones cerradas (win rate)
    print(f"\n📈 POSICIONES CERRADAS (win rate):")
    closed = get_closed_positions(COLDMATH_ADDRESS, limit=50)
    if closed:
        wins = sum(1 for p in closed if float(p.get("cashPnl", 0)) > 0)
        losses = sum(1 for p in closed if float(p.get("cashPnl", 0)) < 0)
        total_pnl = sum(float(p.get("cashPnl", 0)) for p in closed)
        print(f"  Cerradas analizadas: {len(closed)}")
        print(f"  Ganadoras: {wins} | Perdedoras: {losses}")
        if wins + losses > 0:
            print(f"  Win rate: {wins/(wins+losses)*100:.1f}%")
        print(f"  PnL total muestra: ${total_pnl:+.2f}")
    else:
        print("  No se pudieron obtener (endpoint distinto)")

    print(f"\n✅ Análisis completado.")
