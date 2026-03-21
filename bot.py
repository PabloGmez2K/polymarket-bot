import urllib.request
import json
import re
import math
import os
import logging
from datetime import date, datetime

# Dependencias externas (pip install python-dotenv py-clob-client)
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

# =============================================================
# bot.py — Bot de Polymarket v2 (Con Ejecución Real)
# Sesión 4: Primera orden real + integración completa
# =============================================================
#
# Novedades respecto a v1:
#   - Autenticación con Polymarket (Magic wallet)
#   - Ejecución real de órdenes (con flag DRY_RUN)
#   - Logging a archivo trades.log
#   - Fix bug clobTokenIds (json.loads si viene como string)
#   - Filtro: se excluyen mercados que resuelven HOY (sin order book)
#   - Fix bug SELL: comprar NO usa BUY + token_id_no, no SELL
#
# Flujo:
#   1. Configuración (bankroll, límites, DRY_RUN)
#   2. Autenticación con Polymarket
#   3. Leer mercados de Polymarket
#   4. Parsear preguntas + extraer token IDs
#   5. Obtener previsiones (coords de aeropuerto)
#   6. Calcular edge
#   7. Calcular tamaño de apuesta (Kelly)
#   8. Mostrar plan de operaciones
#   9. Ejecutar órdenes (si DRY_RUN = False)
# =============================================================


# =============================================================
# CONFIGURACIÓN DEL USUARIO
# =============================================================

DRY_RUN = False          # True = solo planifica, no ejecuta.
                         # Cambia a False para órdenes reales.

BANKROLL = 15.00         # Bankroll real actual en USDC
MIN_EDGE = 10.0          # Edge mínimo (%) para considerar operar
MIN_BET = 1.00           # Apuesta mínima en USD (límite real de Polymarket)
MAX_BET_PCT = 0.05       # Máximo 5% del bankroll por operación
MAX_EXPOSURE_PCT = 0.30  # Máximo 30% del bankroll expuesto EN TOTAL
MIN_LIQUIDITY = 100      # Liquidez mínima del mercado en USD
MAX_DAYS_AHEAD = 3       # Solo mercados que resuelven en los próximos N días
MIN_DAYS_AHEAD = 1       # Excluir mercados que resuelven HOY (sin order book)


# =============================================================
# LOGGING — Guarda un registro de todo en trades.log
# =============================================================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("trades.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


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
# AUTENTICACIÓN
# =============================================================

def setup_client():
    load_dotenv()
    pk = os.getenv("PK")
    funder = os.getenv("FUNDER")

    if not pk or not funder:
        log.error("No se encontraron PK o FUNDER en .env")
        return None

    try:
        client = ClobClient(
            "https://clob.polymarket.com",
            key=pk,
            chain_id=137,
            signature_type=1,
            funder=funder,
        )
        client.set_api_creds(client.create_or_derive_api_creds())
        log.info("Autenticación con Polymarket: OK")
        return client
    except Exception as e:
        log.error(f"Error en autenticación: {e}")
        return None


# =============================================================
# FUNCIONES: API
# =============================================================

def api_get(endpoint):
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.2")
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

    # Polymarket exige mínimo 5 shares por orden.
    # Con precios altos (ej: NO a $0.60) o apuestas pequeñas,
    # el cálculo puede dar menos de 5 shares y la orden es rechazada.
    # En ese caso escalamos el importe para llegar a 5 shares exactas,
    # respetando siempre el tope MAX_BET_PCT.
    if shares < 5.0:
        amount_for_5_shares = round(5.0 * market_price, 2)
        if amount_for_5_shares > bankroll * MAX_BET_PCT:
            return None   # No se puede llegar a 5 shares sin superar el tope
        if amount_for_5_shares < MIN_BET:
            return None
        amount = amount_for_5_shares
        shares = 5.0

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
# FUNCIONES: EJECUCIÓN DE ÓRDENES
# =============================================================

def execute_trade(client, trade, dry_run=True):
    """
    Ejecuta una orden en Polymarket.

    Por qué siempre BUY:
        En Polymarket, para apostar a que algo NO ocurre, no se
        hace SELL. Se compra el token "NO" directamente con BUY.
        El token_id ya apunta al outcome correcto (YES o NO).
        SELL significaría vender tokens que ya tienes, no comprar.

    Por qué órdenes límite (GTC):
        Tú fijas el precio máximo. Si el mercado sube, no te llena.
        GTC = Good Till Cancelled → activa hasta llenar o cancelar.
    """
    token_id = trade["token_id"]
    price = trade["mkt_price"] / 100.0
    size = trade["position"]["shares"]

    price = round(price, 2)
    size = round(size, 2)

    side = BUY   # Siempre BUY — el token_id ya determina si es YES o NO

    log.info(
        f"{'[DRY RUN] ' if dry_run else ''}Orden: "
        f"{trade['side']} {size} shares × ${price:.2f} "
        f"| {trade['city']} {trade['date']} "
        f"| token {token_id[:12]}..."
    )

    if dry_run:
        return {"ok": True, "order_id": "DRY_RUN", "msg": "Simulado (DRY_RUN=True)"}

    try:
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.GTC)

        order_id = resp.get("orderID", resp.get("id", "desconocido"))
        status = resp.get("status", "?")

        log.info(f"Orden enviada: ID={order_id} | Status={status}")
        return {"ok": True, "order_id": order_id, "msg": f"Status: {status}"}

    except Exception as e:
        log.error(f"Error al ejecutar orden: {e}")
        return {"ok": False, "order_id": None, "msg": str(e)}


# =============================================================
# PROGRAMA PRINCIPAL
# =============================================================

if __name__ == "__main__":

    today_str = date.today().isoformat()
    mode_label = "DRY RUN (sin órdenes reales)" if DRY_RUN else "⚠️  MODO REAL — ÓRDENES ACTIVAS"

    log.info("=" * 65)
    log.info(f"POLYMARKET WEATHER BOT v2  |  {today_str}")
    log.info(f"Modo: {mode_label}")
    log.info(f"Bankroll: ${BANKROLL:.2f}  |  Edge mín: {MIN_EDGE}%")
    log.info("=" * 65)

    # ---- AUTENTICACIÓN ----
    client = setup_client()
    if client is None:
        log.error("No se pudo autenticar. Verifica tu .env. Saliendo.")
        exit(1)

    # ---- PASO 1: Mercados ----
    log.info("[1/5] Obteniendo mercados...")
    try:
        events = api_get(
            f"/events?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=30&order=volume24hr&ascending=false"
        )
    except Exception as e:
        log.error(f"Error al obtener mercados: {e}")
        events = []

    all_markets = []
    for event in events:
        for m in event.get("markets", []):
            all_markets.append(m)
    log.info(f"       {len(all_markets)} mercados encontrados")

    # ---- PASO 2: Parsear + extraer token IDs ----
    log.info("[2/5] Parseando preguntas...")
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

        if days_ahead < MIN_DAYS_AHEAD or days_ahead > MAX_DAYS_AHEAD:
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

        clob_ids_raw = market.get("clobTokenIds", "[]")
        try:
            clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        except (json.JSONDecodeError, TypeError):
            clob_ids = []

        if not clob_ids or len(clob_ids) < 2:
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
        parsed["token_id_yes"] = clob_ids[0]
        parsed["token_id_no"] = clob_ids[1]
        candidates.append(parsed)

    log.info(f"       {len(candidates)} candidatos (con filtros de calidad)")

    # ---- PASO 3: Previsiones ----
    log.info("[3/5] Obteniendo previsiones...")
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
                log.warning(f"No se encontraron coordenadas para {city}")
                continue

        forecast_cache[city] = get_forecast(lat, lon)
        label = station["name"] if station else "fallback"
        log.info(f"       {city} ({label}): OK")

    # ---- PASO 4: Calcular edge ----
    log.info("[4/5] Calculando edge...")
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

        edge_yes = our_prob_yes - c["mkt_prob_yes"]
        edge_no = our_prob_no - c["mkt_prob_no"]

        if edge_yes > edge_no and edge_yes > 0:
            side = "YES"
            our_prob = our_prob_yes
            mkt_price = c["mkt_prob_yes"]
            edge = edge_yes
            token_id = c["token_id_yes"]
        elif edge_no > 0:
            side = "NO"
            our_prob = our_prob_no
            mkt_price = c["mkt_prob_no"]
            edge = edge_no
            token_id = c["token_id_no"]
        else:
            continue

        edge_pct = edge * 100
        if edge_pct < MIN_EDGE:
            continue

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
            "token_id": token_id,
        })

    trades.sort(key=lambda x: x["position"]["expected_value"], reverse=True)

    # ---- PASO 5: Presupuesto global + plan ----
    max_budget = BANKROLL * MAX_EXPOSURE_PCT
    budget_remaining = max_budget
    selected_trades = []

    for t in trades:
        pos = t["position"]
        if pos["amount"] <= budget_remaining:
            budget_remaining -= pos["amount"]
            t["selected"] = True
            selected_trades.append(t)
        else:
            if budget_remaining >= MIN_BET:
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

    log.info("[5/5] Generando plan de operaciones...")
    log.info(f"       {len(trades)} oportunidades detectadas")
    log.info(f"       {len(selected_trades)} seleccionadas (presupuesto: ${max_budget:.2f})")
    log.info(f"       {len(trades) - len(selected_trades)} descartadas (sin presupuesto)")

    # ---- IMPRIMIR PLAN ----
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
            print(f"  │ Token ID:  {t['token_id'][:16]}...")
            print(f"  └────────────────────────────────────────────")
            print()

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
        print(f"  Modo: {mode_label}")
        print("=" * 65)

    # ---- PASO 6: EJECUCIÓN ----
    if not selected_trades:
        log.info("Sin operaciones que ejecutar.")
    else:
        print()
        if DRY_RUN:
            print("  [DRY RUN] Las siguientes órdenes se SIMULARÍAN:")
        else:
            print("  ⚠️  EJECUTANDO ÓRDENES REALES...")
        print()

        results = []
        for i, trade in enumerate(selected_trades):
            result = execute_trade(client, trade, dry_run=DRY_RUN)
            results.append(result)

            status_icon = "✓" if result["ok"] else "✗"
            print(
                f"  {status_icon} #{i+1} {trade['city']} {trade['side']} "
                f"${trade['position']['amount']:.2f} → {result['msg']}"
            )

            log.info(
                f"Trade #{i+1}: {trade['city']} | {trade['side']} | "
                f"${trade['position']['amount']:.2f} | edge={trade['edge_pct']}% | "
                f"order_id={result['order_id']} | ok={result['ok']}"
            )

        ok_count = sum(1 for r in results if r["ok"])
        print()
        print(f"  Resultado: {ok_count}/{len(results)} órdenes OK")
        print()

    log.info("Bot finalizado.")
