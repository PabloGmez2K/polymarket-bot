import urllib.request
import json
import re
import math
from datetime import date

# =============================================================
# bot.py — Bot de Polymarket v1 (Sistema Completo)
# Sesión 2 del bot de Polymarket
# =============================================================
#
# Este es el script principal del bot. Combina:
# - Edge detection (de edge_detector.py)
# - Bankroll management (de bankroll.py)
# - Coordenadas de aeropuerto verificadas
# - Modelo de probabilidad con distribución normal
#
# Flujo:
#   1. Configuración (bankroll, límites de riesgo)
#   2. Leer mercados de Polymarket
#   3. Parsear preguntas
#   4. Obtener previsiones (coords de aeropuerto)
#   5. Calcular edge
#   6. Calcular tamaño de apuesta (Kelly)
#   7. Mostrar plan de operaciones concreto
#
# IMPORTANTE: Este bot NO ejecuta órdenes todavía.
# Solo muestra recomendaciones. La ejecución automática
# requiere autenticación con Polymarket (futuras sesiones).
# =============================================================


# =============================================================
# CONFIGURACIÓN DEL USUARIO
# =============================================================

BANKROLL = 100.00        # Capital total en USD
MIN_EDGE = 10.0          # Edge mínimo (%) para considerar operar
MIN_BET = 0.50           # Apuesta mínima en USD
MAX_BET_PCT = 0.05       # Máximo 5% del bankroll por operación
MAX_EXPOSURE_PCT = 0.30  # Máximo 30% del bankroll expuesto EN TOTAL
MIN_LIQUIDITY = 100      # Liquidez mínima del mercado en USD
MAX_DAYS_AHEAD = 3       # Solo mercados que resuelven en 3 días o menos


# =============================================================
# DATOS DE REFERENCIA
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

RESOLUTION_STATIONS = {
    "Seoul":          {"lat": 37.4602, "lon": 126.4407, "name": "Incheon Intl"},
    "London":         {"lat": 51.5048, "lon": 0.0495,   "name": "London City"},
    "Tel Aviv":       {"lat": 32.0114, "lon": 34.8867,  "name": "Ben Gurion"},
    "Shanghai":       {"lat": 31.1443, "lon": 121.8083, "name": "Pudong"},
    "Tokyo":          {"lat": 35.5494, "lon": 139.7798, "name": "Haneda"},
    "New York City":  {"lat": 40.7772, "lon": -73.8726, "name": "LaGuardia"},
    "Beijing":        {"lat": 40.0799, "lon": 116.6031, "name": "Beijing Capital"},
    "Hong Kong":      {"lat": 22.3080, "lon": 113.9185, "name": "HK Intl"},
    "Singapore":      {"lat": 1.3502,  "lon": 103.9940, "name": "Changi"},
    "Toronto":        {"lat": 43.6772, "lon": -79.6306, "name": "Pearson"},
    "Chicago":        {"lat": 41.9742, "lon": -87.9073, "name": "O'Hare"},
    "Wellington":     {"lat": -41.3272, "lon": 174.8053, "name": "Wellington"},
    "Munich":         {"lat": 48.3538, "lon": 11.7861,  "name": "Munich"},
    "Warsaw":         {"lat": 52.1657, "lon": 20.9671,  "name": "Warsaw Chopin"},
    "Ankara":         {"lat": 40.1281, "lon": 32.9951,  "name": "Esenboğa"},
    "Atlanta":        {"lat": 33.6407, "lon": -84.4277, "name": "Hartsfield"},
    "Shenzhen":       {"lat": 22.6393, "lon": 113.8107, "name": "Bao'an"},
    "Paris":          {"lat": 49.0097, "lon": 2.5479,   "name": "CDG"},
    "Buenos Aires":   {"lat": -34.8222, "lon": -58.5358, "name": "Ezeiza"},
}


# =============================================================
# FUNCIONES: API
# =============================================================

def api_get(endpoint):
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.1")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_coordinates_fallback(city_name):
    city_clean = city_name.strip().replace(" ", "+")
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city_clean}&count=1&language=en"
    )
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    if "results" not in data or len(data["results"]) == 0:
        return None
    place = data["results"][0]
    return place["latitude"], place["longitude"]


def get_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f",precipitation_probability_max"
        f",precipitation_sum"
        f"&timezone=auto"
    )
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    daily = data["daily"]
    forecast_by_date = {}
    for i in range(len(daily["time"])):
        d = daily["time"][i]
        forecast_by_date[d] = {
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_prob": daily["precipitation_probability_max"][i],
            "rain_mm": daily["precipitation_sum"][i],
        }
    return forecast_by_date


# =============================================================
# FUNCIONES: PARSEO
# =============================================================

def parse_temperature_question(question):
    match = re.search(
        r"temperature in (.+?) (?:be |on )"
        r"(\d+)°([CF])"
        r"(?: or (below|higher|above))?"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)"
        r"\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if not match:
        return None

    city = match.group(1).strip()
    temp = int(match.group(2))
    unit = match.group(3).upper() if match.group(3) else "C"

    condition = "exact"
    if match.lastindex >= 4 and match.group(4):
        modifier = match.group(4).lower()
        if modifier == "below":
            condition = "at_or_below"
        elif modifier in ("higher", "above"):
            condition = "at_or_above"

    date_str = match.group(5) if match.lastindex >= 5 else None

    return {
        "city": city, "temp_threshold": temp,
        "condition": condition, "date_str": date_str, "unit": unit,
    }


def date_text_to_iso(date_text, year=2026):
    if not date_text:
        return None
    months = {
        "january": "01", "february": "02", "march": "03",
        "april": "04", "may": "05", "june": "06",
        "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12",
    }
    parts = date_text.strip().split()
    if len(parts) != 2:
        return None
    month_name = parts[0].lower()
    day = parts[1]
    if month_name not in months:
        return None
    return f"{year}-{months[month_name]}-{day.zfill(2)}"


# =============================================================
# FUNCIONES: MODELO DE PROBABILIDAD
# =============================================================

def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def get_uncertainty(days_ahead):
    if days_ahead <= 0:
        return 0.8
    elif days_ahead == 1:
        return 1.0
    elif days_ahead == 2:
        return 1.4
    elif days_ahead == 3:
        return 1.8
    elif days_ahead <= 5:
        return 2.5
    else:
        return 3.0


def estimate_prob(forecast_max, threshold_c, condition, days_ahead):
    sigma = get_uncertainty(days_ahead)
    mu = forecast_max

    if condition == "exact":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma) - normal_cdf(threshold_c - 0.5, mu, sigma)
    elif condition == "at_or_below":
        prob = normal_cdf(threshold_c + 0.5, mu, sigma)
    elif condition == "at_or_above":
        prob = 1.0 - normal_cdf(threshold_c - 0.5, mu, sigma)
    else:
        prob = 0.5

    return max(0.01, min(0.99, prob))


# =============================================================
# FUNCIONES: BANKROLL / KELLY
# =============================================================

def kelly_fraction(estimated_prob, market_price):
    if market_price <= 0.01 or market_price >= 0.99:
        return 0.0
    if estimated_prob <= 0.01 or estimated_prob >= 0.99:
        return 0.0

    b = (1.0 - market_price) / market_price
    p = estimated_prob
    q = 1.0 - p

    kelly = (p * b - q) / b
    if kelly <= 0:
        return 0.0

    half_kelly = kelly / 2.0
    return min(half_kelly, MAX_BET_PCT)


def calculate_position(bankroll, estimated_prob, market_price):
    fraction = kelly_fraction(estimated_prob, market_price)

    if fraction <= 0:
        return None

    amount = round(bankroll * fraction, 2)
    if amount < MIN_BET:
        return None

    shares = amount / market_price
    profit = round(shares * (1.0 - market_price), 2)
    loss = round(amount, 2)
    ev = round(estimated_prob * profit - (1 - estimated_prob) * loss, 2)

    return {
        "fraction_pct": round(fraction * 100, 2),
        "amount": amount,
        "shares": round(shares, 2),
        "profit_if_win": profit,
        "loss_if_lose": loss,
        "expected_value": ev,
    }


# =============================================================
# PROGRAMA PRINCIPAL
# =============================================================

if __name__ == "__main__":

    today_str = date.today().isoformat()

    print()
    print("=" * 65)
    print("  POLYMARKET WEATHER BOT v1")
    print(f"  Fecha: {today_str}  |  Bankroll: ${BANKROLL:.2f}")
    print("=" * 65)
    print()

    # ---- PASO 1: Mercados ----
    print("  [1/5] Obteniendo mercados...")
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=30&order=volume24hr&ascending=false"
        )
    except Exception as e:
        print(f"  Error: {e}")
        events = []

    all_markets = []
    for event in events:
        for m in event.get("markets", []):
            all_markets.append(m)
    print(f"        {len(all_markets)} mercados encontrados")

    # ---- PASO 2: Parsear ----
    print("  [2/5] Parseando preguntas...")
    candidates = []

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)
        if not parsed or not parsed["date_str"]:
            continue

        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            continue

        try:
            market_date = date.fromisoformat(date_iso)
            days_ahead = (market_date - date.today()).days
        except ValueError:
            continue

        if days_ahead < 0 or days_ahead > MAX_DAYS_AHEAD:
            continue

        prices_raw = market.get("outcomePrices", "[]")
        outcomes_raw = market.get("outcomes", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except (json.JSONDecodeError, TypeError):
            continue

        if not prices:
            continue

        mkt_prob_yes = float(prices[0])
        if mkt_prob_yes >= 0.98 or mkt_prob_yes <= 0.02:
            continue

        liquidity = float(market.get("liquidity", 0))
        if liquidity < MIN_LIQUIDITY:
            continue

        parsed["question"] = question
        parsed["date_iso"] = date_iso
        parsed["days_ahead"] = days_ahead
        parsed["mkt_prob_yes"] = mkt_prob_yes
        parsed["mkt_prob_no"] = 1.0 - mkt_prob_yes
        parsed["volume_24h"] = float(market.get("volume24hr", 0))
        parsed["liquidity"] = liquidity
        candidates.append(parsed)

    print(f"        {len(candidates)} candidatos (con filtros de calidad)")

    # ---- PASO 3: Previsiones ----
    print("  [3/5] Obteniendo previsiones...")
    cities_needed = set(c["city"] for c in candidates)
    forecast_cache = {}

    for city in sorted(cities_needed):
        station = RESOLUTION_STATIONS.get(city)
        if station:
            lat, lon = station["lat"], station["lon"]
        else:
            coords = get_coordinates_fallback(city)
            if coords:
                lat, lon = coords
            else:
                continue

        forecast_cache[city] = get_forecast(lat, lon)
        label = station["name"] if station else "fallback"
        print(f"        {city} ({label}): OK")

    # ---- PASO 4: Calcular edge ----
    print("  [4/5] Calculando edge...")
    trades = []

    for c in candidates:
        city = c["city"]
        if city not in forecast_cache:
            continue
        if c["date_iso"] not in forecast_cache[city]:
            continue

        forecast_day = forecast_cache[city][c["date_iso"]]
        forecast_max = forecast_day["temp_max"]

        threshold = c["temp_threshold"]
        if c["unit"] == "F":
            threshold_c = (threshold - 32) * 5 / 9
        else:
            threshold_c = float(threshold)

        our_prob_yes = estimate_prob(
            forecast_max, threshold_c, c["condition"], c["days_ahead"]
        )
        our_prob_no = 1.0 - our_prob_yes

        # Determinar dirección de la operación
        # ¿Compramos YES o NO?
        edge_yes = our_prob_yes - c["mkt_prob_yes"]
        edge_no = our_prob_no - c["mkt_prob_no"]

        if edge_yes > edge_no and edge_yes > 0:
            side = "YES"
            our_prob = our_prob_yes
            mkt_price = c["mkt_prob_yes"]
            edge = edge_yes
        elif edge_no > 0:
            side = "NO"
            our_prob = our_prob_no
            mkt_price = c["mkt_prob_no"]
            edge = edge_no
        else:
            continue

        edge_pct = edge * 100
        if edge_pct < MIN_EDGE:
            continue

        # Calcular posición
        position = calculate_position(BANKROLL, our_prob, mkt_price)
        if not position:
            continue

        trades.append({
            "question": c["question"],
            "city": city,
            "date": c["date_iso"],
            "days_ahead": c["days_ahead"],
            "forecast_max": forecast_max,
            "threshold": threshold,
            "unit": c["unit"],
            "condition": c["condition"],
            "side": side,
            "our_prob": round(our_prob * 100, 1),
            "mkt_price": round(mkt_price * 100, 1),
            "edge_pct": round(edge_pct, 1),
            "position": position,
            "volume_24h": c["volume_24h"],
            "liquidity": c["liquidity"],
            "station": RESOLUTION_STATIONS.get(city, {}).get("name", "?"),
        })

    trades.sort(key=lambda x: x["position"]["expected_value"], reverse=True)

    # ---- PASO 5: Aplicar presupuesto global y mostrar plan ----
    #
    # Problema: Kelly calcula cada trade de forma independiente.
    # Con 23 trades a 5% cada uno = 115% del bankroll. Imposible.
    #
    # Solución: presupuesto global. Recorremos los trades ordenados
    # por EV (mejores primero) y asignamos capital hasta llegar al
    # tope de MAX_EXPOSURE_PCT. Los que no caben, se descartan.
    #
    # Esto es como un carrito de la compra con presupuesto: metes
    # los productos más valiosos primero y cuando se acaba el dinero,
    # dejas el resto en la estantería.

    max_budget = BANKROLL * MAX_EXPOSURE_PCT
    budget_remaining = max_budget
    selected_trades = []

    for t in trades:
        pos = t["position"]
        if pos["amount"] <= budget_remaining:
            # Cabe en el presupuesto → la incluimos
            budget_remaining -= pos["amount"]
            t["selected"] = True
            selected_trades.append(t)
        else:
            # No cabe el tamaño completo.
            # ¿Cabe algo? Solo si lo que queda supera el mínimo.
            if budget_remaining >= MIN_BET:
                # Recalcular con lo que queda
                reduced_amount = round(budget_remaining, 2)
                mkt_price_decimal = t["mkt_price"] / 100
                shares = reduced_amount / mkt_price_decimal
                profit = round(shares * (1.0 - mkt_price_decimal), 2)
                loss = round(reduced_amount, 2)
                our_prob_decimal = t["our_prob"] / 100
                ev = round(our_prob_decimal * profit - (1 - our_prob_decimal) * loss, 2)

                t["position"] = {
                    "fraction_pct": round(reduced_amount / BANKROLL * 100, 2),
                    "amount": reduced_amount,
                    "shares": round(shares, 2),
                    "profit_if_win": profit,
                    "loss_if_lose": loss,
                    "expected_value": ev,
                }
                budget_remaining = 0
                selected_trades.append(t)
            # Si no cabe ni el mínimo, saltamos este trade

    print(f"  [5/5] Generando plan de operaciones...\n")
    print(f"        {len(trades)} oportunidades detectadas")
    print(f"        {len(selected_trades)} seleccionadas (presupuesto: ${max_budget:.2f})")
    print(f"        {len(trades) - len(selected_trades)} descartadas (sin presupuesto)")
    print()

    print("=" * 65)
    print("  PLAN DE OPERACIONES")
    print("=" * 65)

    if not selected_trades:
        print()
        print("  No hay operaciones recomendadas ahora.")
        print()
    else:
        total_exposure = 0
        total_ev = 0

        print()
        for i, t in enumerate(selected_trades):
            pos = t["position"]
            total_exposure += pos["amount"]
            total_ev += pos["expected_value"]
            confidence = "ALTA" if t["days_ahead"] <= 1 else "MEDIA"
            unit = "°" + t["unit"]

            print(f"  ┌─ Operación #{i + 1} ──────────────────────────────")
            print(f"  │ {t['question']}")
            print(f"  │")
            print(f"  │ Acción:    COMPRAR {t['side']} a ${t['mkt_price']/100:.2f}")
            print(f"  │ Cantidad:  ${pos['amount']:.2f} ({pos['fraction_pct']}% del bankroll)")
            print(f"  │ Shares:    {pos['shares']:.1f}")
            print(f"  │")
            print(f"  │ Edge:      {t['edge_pct']:.1f}% | Confianza: {confidence}")
            print(f"  │ Previsión: {t['forecast_max']:.1f}°C  |  Umbral: {t['threshold']}{unit}")
            print(f"  │ Nuestro:   {t['our_prob']}%  |  Mercado: {t['mkt_price']}%")
            print(f"  │")
            print(f"  │ Si ganas:  +${pos['profit_if_win']:.2f}")
            print(f"  │ Si pierdes: -${pos['loss_if_lose']:.2f}")
            print(f"  │ EV:        ${pos['expected_value']:+.2f}")
            print(f"  │")
            print(f"  │ Liquidez: ${t['liquidity']:,.0f} | Vol 24h: ${t['volume_24h']:,.0f}")
            print(f"  │ Estación: {t['station']} | Fecha: {t['date']}")
            print(f"  └────────────────────────────────────────────")
            print()

        # Resumen
        print("=" * 65)
        print("  RESUMEN DEL PLAN")
        print("=" * 65)
        print(f"  Operaciones:      {len(selected_trades)} de {len(trades)} oportunidades")
        print(f"  Bankroll:         ${BANKROLL:.2f}")
        print(f"  Presupuesto:      ${max_budget:.2f} ({MAX_EXPOSURE_PCT*100:.0f}% del bankroll)")
        print(f"  Exposición total: ${total_exposure:.2f} ({total_exposure/BANKROLL*100:.1f}%)")
        print(f"  Capital libre:    ${BANKROLL - total_exposure:.2f}")
        print(f"  EV total:         ${total_ev:+.2f}")
        print()
        print("  RECORDATORIO: Este plan es una RECOMENDACIÓN.")
        print("  Verifica las previsiones en Wunderground antes de operar.")
        print("  El bot NO ejecuta órdenes — eso requiere autenticación.")
    print("=" * 65)
