import urllib.request
import json
import re
import math

# =============================================================
# edge_detector.py — Detector de Edge v3
# Sesión 2 del bot de Polymarket
# =============================================================
#
# MEJORA CLAVE sobre v2:
#
# Polymarket resuelve con la lectura de un termómetro en un
# aeropuerto específico. En v2 pedíamos la previsión para el
# centro de la ciudad — que puede estar a 50km del aeropuerto
# y tener 1-3°C de diferencia.
#
# En v3 usamos las COORDENADAS EXACTAS del aeropuerto.
# Open-Meteo interpola su grid al punto que le des, así que
# cuanto más cerca estemos de la estación real, mejor.
#
# También eliminamos las llamadas a la API de geocoding —
# ahora usamos coordenadas hardcodeadas (fijas en el código).
# Esto hace el bot más rápido y más fiable.
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

# Estaciones de resolución con coordenadas del aeropuerto.
# lat/lon obtenidas de datos aeronáuticos oficiales (ICAO).
#
# ¿Por qué hardcodear en vez de buscar dinámicamente?
# Porque estas coordenadas NO CAMBIAN. Un aeropuerto no se
# mueve. Y tener los datos fijos evita depender de otra API.
RESOLUTION_STATIONS = {
    "Seoul": {
        "source": "wunderground",
        "station": "RKSI",
        "name": "Incheon Intl Airport",
        "lat": 37.4602,
        "lon": 126.4407,
        "url": "https://www.wunderground.com/history/daily/kr/incheon/RKSI",
    },
    "London": {
        "source": "wunderground",
        "station": "EGLC",
        "name": "London City Airport",
        "lat": 51.5048,
        "lon": 0.0495,
        "url": "https://www.wunderground.com/history/daily/gb/london/EGLC",
    },
    "Tel Aviv": {
        "source": "NOAA",
        "station": "LLBG",
        "name": "Ben Gurion Intl Airport",
        "lat": 32.0114,
        "lon": 34.8867,
        "url": "https://www.weather.gov/wrh/timeseries?site=LLBG",
    },
    "Shanghai": {
        "source": "wunderground",
        "station": "ZSPD",
        "name": "Pudong Intl Airport",
        "lat": 31.1443,
        "lon": 121.8083,
        "url": "https://www.wunderground.com/history/daily/cn/shanghai/ZSPD",
    },
    "Tokyo": {
        "source": "wunderground",
        "station": "RJTT",
        "name": "Haneda Airport",
        "lat": 35.5494,
        "lon": 139.7798,
        "url": "https://www.wunderground.com/history/daily/jp/tokyo/RJTT",
    },
    "New York City": {
        "source": "wunderground",
        "station": "KLGA",
        "name": "LaGuardia Airport",
        "lat": 40.7772,
        "lon": -73.8726,
        "url": "https://www.wunderground.com/history/daily/us/new-york-city/KLGA",
    },
    "Beijing": {
        "source": "wunderground",
        "station": "ZBAA",
        "name": "Beijing Capital Airport",
        "lat": 40.0799,
        "lon": 116.6031,
        "url": "https://www.wunderground.com/history/daily/cn/beijing/ZBAA",
    },
    "Hong Kong": {
        "source": "wunderground",
        "station": "VHHH",
        "name": "Hong Kong Intl Airport",
        "lat": 22.3080,
        "lon": 113.9185,
        "url": "https://www.wunderground.com/history/daily/hk/hong-kong/VHHH",
    },
    "Singapore": {
        "source": "wunderground",
        "station": "WSSS",
        "name": "Changi Airport",
        "lat": 1.3502,
        "lon": 103.9940,
        "url": "https://www.wunderground.com/history/daily/sg/singapore/WSSS",
    },
    "Toronto": {
        "source": "wunderground",
        "station": "CYYZ",
        "name": "Pearson Intl Airport",
        "lat": 43.6772,
        "lon": -79.6306,
        "url": "https://www.wunderground.com/history/daily/ca/toronto/CYYZ",
    },
    "Chicago": {
        "source": "wunderground",
        "station": "KORD",
        "name": "O'Hare Intl Airport",
        "lat": 41.9742,
        "lon": -87.9073,
        "url": "https://www.wunderground.com/history/daily/us/chicago/KORD",
    },
    "Wellington": {
        "source": "wunderground",
        "station": "NZWN",
        "name": "Wellington Airport",
        "lat": -41.3272,
        "lon": 174.8053,
        "url": "https://www.wunderground.com/history/daily/nz/wellington/NZWN",
    },
    "Munich": {
        "source": "wunderground",
        "station": "EDDM",
        "name": "Munich Airport",
        "lat": 48.3538,
        "lon": 11.7861,
        "url": "https://www.wunderground.com/history/daily/de/munich/EDDM",
    },
    "Warsaw": {
        "source": "wunderground",
        "station": "EPWA",
        "name": "Warsaw Chopin Airport",
        "lat": 52.1657,
        "lon": 20.9671,
        "url": "https://www.wunderground.com/history/daily/pl/warsaw/EPWA",
    },
    "Ankara": {
        "source": "wunderground",
        "station": "LTAC",
        "name": "Esenboğa Airport",
        "lat": 40.1281,
        "lon": 32.9951,
        "url": "https://www.wunderground.com/history/daily/tr/ankara/LTAC",
    },
    "Atlanta": {
        "source": "wunderground",
        "station": "KATL",
        "name": "Hartsfield-Jackson Airport",
        "lat": 33.6407,
        "lon": -84.4277,
        "url": "https://www.wunderground.com/history/daily/us/atlanta/KATL",
    },
    "Shenzhen": {
        "source": "wunderground",
        "station": "ZGSZ",
        "name": "Shenzhen Bao'an Airport",
        "lat": 22.6393,
        "lon": 113.8107,
        "url": "https://www.wunderground.com/history/daily/cn/shenzhen/ZGSZ",
    },
    "Paris": {
        "source": "wunderground",
        "station": "LFPG",
        "name": "Charles de Gaulle Airport",
        "lat": 49.0097,
        "lon": 2.5479,
        "url": "https://www.wunderground.com/history/daily/fr/paris/LFPG",
    },
    "Buenos Aires": {
        "source": "wunderground",
        "station": "SAEZ",
        "name": "Ezeiza Airport",
        "lat": -34.8222,
        "lon": -58.5358,
        "url": "https://www.wunderground.com/history/daily/ar/buenos-aires/SAEZ",
    },
}


# =============================================================
# FUNCIONES DE API
# =============================================================

def api_get(endpoint):
    """Petición GET a la Gamma API de Polymarket."""
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.1")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_coordinates_from_geocoding(city_name):
    """
    Fallback: si una ciudad no está en RESOLUTION_STATIONS,
    usamos geocoding de Open-Meteo (centro de ciudad).
    Menos preciso, pero mejor que nada.
    """
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
    """Obtiene previsión a 7 días. Devuelve dict {fecha: datos}."""
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
        date = daily["time"][i]
        forecast_by_date[date] = {
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_prob": daily["precipitation_probability_max"][i],
            "rain_mm": daily["precipitation_sum"][i],
        }

    return forecast_by_date


# =============================================================
# PARSEO DE PREGUNTAS
# =============================================================

def parse_temperature_question(question):
    """Extrae ciudad, temperatura, condición y fecha."""
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
        match = re.search(
            r"temperature in (.+?)(?:\s+be\s+|\s+on\s+)(\d+)",
            question,
            re.IGNORECASE,
        )
        if not match:
            return None

    city = match.group(1).strip()
    temp = int(match.group(2))

    unit = "C"
    if match.lastindex >= 3 and match.group(3):
        unit = match.group(3).upper()

    condition = "exact"
    if match.lastindex >= 4 and match.group(4):
        modifier = match.group(4).lower()
        if modifier == "below":
            condition = "at_or_below"
        elif modifier in ("higher", "above"):
            condition = "at_or_above"

    date_str = None
    if match.lastindex >= 5 and match.group(5):
        date_str = match.group(5)

    return {
        "city": city,
        "temp_threshold": temp,
        "condition": condition,
        "date_str": date_str,
        "unit": unit,
    }


def date_text_to_iso(date_text, year=2026):
    """Convierte 'March 22' a '2026-03-22'."""
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
# MODELO DE PROBABILIDAD v2
# =============================================================

def normal_cdf(x, mu, sigma):
    """P(X <= x) donde X ~ Normal(mu, sigma)."""
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def get_forecast_uncertainty(days_ahead):
    """Incertidumbre de la previsión según días."""
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


def calculate_edge(parsed_question, forecast_for_date, days_ahead):
    """Modelo de probabilidad con distribución normal + redondeo."""
    threshold = parsed_question["temp_threshold"]
    condition = parsed_question["condition"]
    forecast_max = forecast_for_date["temp_max"]

    if parsed_question["unit"] == "F":
        threshold_c = (threshold - 32) * 5 / 9
    else:
        threshold_c = float(threshold)

    sigma = get_forecast_uncertainty(days_ahead)
    mu = forecast_max

    if condition == "exact":
        lower = threshold_c - 0.5
        upper = threshold_c + 0.5
        prob_yes = normal_cdf(upper, mu, sigma) - normal_cdf(lower, mu, sigma)

    elif condition == "at_or_below":
        upper = threshold_c + 0.5
        prob_yes = normal_cdf(upper, mu, sigma)

    elif condition == "at_or_above":
        lower = threshold_c - 0.5
        prob_yes = 1.0 - normal_cdf(lower, mu, sigma)

    else:
        prob_yes = 0.5

    prob_yes = max(0.01, min(0.99, prob_yes))

    return {
        "forecast_max_c": forecast_max,
        "threshold_c": threshold_c,
        "sigma": sigma,
        "days_ahead": days_ahead,
        "estimated_prob_yes": round(prob_yes * 100, 1),
        "estimated_prob_no": round((1 - prob_yes) * 100, 1),
    }


# =============================================================
# PROGRAMA PRINCIPAL
# =============================================================

if __name__ == "__main__":

    from datetime import date

    today = date.today().isoformat()

    print()
    print("=" * 65)
    print("  DETECTOR DE EDGE v3 — Coordenadas de Aeropuerto")
    print(f"  Fecha: {today}")
    print("=" * 65)
    print()

    # ---- PASO 1: Obtener mercados ----
    print("  [1/4] Obteniendo mercados de Daily Temperature...")
    try:
        events = api_get(
            f"/events"
            f"?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true"
            f"&closed=false"
            f"&limit=30"
            f"&order=volume24hr"
            f"&ascending=false"
        )
    except Exception as e:
        print(f"  Error conectando con Polymarket: {e}")
        events = []

    all_markets = []
    for event in events:
        for market in event.get("markets", []):
            all_markets.append(market)

    print(f"        Mercados encontrados: {len(all_markets)}")

    # ---- PASO 2: Parsear preguntas ----
    print("  [2/4] Analizando preguntas...")

    parsed_markets = []
    skipped_parse = 0
    skipped_resolved = 0

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)

        if not parsed or not parsed["date_str"]:
            skipped_parse += 1
            continue

        prices_raw = market.get("outcomePrices", "[]")
        outcomes_raw = market.get("outcomes", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except (json.JSONDecodeError, TypeError):
            prices, outcomes = [], []

        market_prob_yes = 0
        if prices:
            market_prob_yes = round(float(prices[0]) * 100, 1)

        if market_prob_yes >= 98.0 or market_prob_yes <= 2.0:
            skipped_resolved += 1
            continue

        parsed["question"] = question
        parsed["market_prob_yes"] = market_prob_yes
        parsed["market_prob_no"] = round(100 - market_prob_yes, 1)
        parsed["volume"] = float(market.get("volume", 0))
        parsed["volume_24h"] = float(market.get("volume24hr", 0))
        parsed["liquidity"] = float(market.get("liquidity", 0))
        parsed_markets.append(parsed)

    print(f"        Parseadas OK: {len(parsed_markets)}")
    print(f"        Descartadas (no parseables): {skipped_parse}")
    print(f"        Descartadas (ya resueltas): {skipped_resolved}")

    # ---- PASO 3: Obtener previsiones usando coords de aeropuerto ----
    print("  [3/4] Consultando previsiones (coords de aeropuerto)...")

    cities_needed = set()
    for pm in parsed_markets:
        cities_needed.add(pm["city"])

    forecast_cache = {}

    for city in sorted(cities_needed):
        station = RESOLUTION_STATIONS.get(city)

        if station:
            lat = station["lat"]
            lon = station["lon"]
            name = station["name"]
            source_type = "AEROPUERTO"
        else:
            # Fallback a geocoding si no conocemos el aeropuerto
            coords = get_coordinates_from_geocoding(city)
            if coords:
                lat, lon = coords
                name = "centro de ciudad (fallback)"
                source_type = "CENTRO CIUDAD"
            else:
                print(f"        {city}: NO ENCONTRADA")
                continue

        forecast = get_forecast(lat, lon)
        forecast_cache[city] = forecast
        print(f"        {city}: OK via {source_type} — {name} ({lat:.2f}, {lon:.2f})")

    # ---- PASO 4: Comparar y detectar edge ----
    print("  [4/4] Comparando previsiones con mercados...\n")

    opportunities = []

    for pm in parsed_markets:
        city = pm["city"]
        date_iso = date_text_to_iso(pm["date_str"])

        if not date_iso or city not in forecast_cache:
            continue
        if date_iso not in forecast_cache[city]:
            continue

        try:
            market_date = date.fromisoformat(date_iso)
            today_date = date.today()
            days_ahead = (market_date - today_date).days
        except ValueError:
            continue

        forecast_day = forecast_cache[city][date_iso]
        edge_data = calculate_edge(pm, forecast_day, days_ahead)

        edge_yes = edge_data["estimated_prob_yes"] - pm["market_prob_yes"]
        edge_no = edge_data["estimated_prob_no"] - pm["market_prob_no"]

        best_edge = max(abs(edge_yes), abs(edge_no))
        if best_edge < 8:
            continue

        if edge_yes > edge_no:
            recommendation = f"Comprar YES (edge: +{edge_yes:.1f}%)"
            edge_side = "YES"
        else:
            recommendation = f"Comprar NO (edge: +{edge_no:.1f}%)"
            edge_side = "NO"

        station_info = RESOLUTION_STATIONS.get(city, {})

        opportunity = {
            "question": pm["question"],
            "city": city,
            "date": date_iso,
            "days_ahead": days_ahead,
            "forecast_max": edge_data["forecast_max_c"],
            "threshold": pm["temp_threshold"],
            "unit": pm["unit"],
            "condition": pm["condition"],
            "sigma": edge_data["sigma"],
            "market_yes": pm["market_prob_yes"],
            "market_no": pm["market_prob_no"],
            "estimated_yes": edge_data["estimated_prob_yes"],
            "estimated_no": edge_data["estimated_prob_no"],
            "edge": best_edge,
            "edge_side": edge_side,
            "recommendation": recommendation,
            "volume_24h": pm["volume_24h"],
            "liquidity": pm["liquidity"],
            "station": station_info.get("name", "desconocida"),
            "station_url": station_info.get("url", ""),
        }
        opportunities.append(opportunity)

    opportunities.sort(key=lambda x: x["edge"], reverse=True)

    # ---- MOSTRAR RESULTADOS ----
    print("=" * 65)
    print("  OPORTUNIDADES DETECTADAS")
    print("=" * 65)

    if not opportunities:
        print()
        print("  No se encontraron oportunidades con edge > 8%.")
        print()
    else:
        print()
        for i, opp in enumerate(opportunities[:20]):
            unit = "°" + opp["unit"]
            confidence = "ALTA" if opp["days_ahead"] <= 1 else "MEDIA" if opp["days_ahead"] <= 3 else "BAJA"

            print(f"  --- #{i + 1}  |  Edge: {opp['edge']:.1f}%  |  Confianza: {confidence}  |  {opp['edge_side']} ---")
            print(f"  Pregunta:     {opp['question']}")
            print(f"  Previsión:    {opp['forecast_max']:.1f}°C (±{opp['sigma']:.1f}°C) en {opp['city']}")
            print(f"  Umbral:       {opp['threshold']}{unit} ({opp['condition']})")
            print(f"  Polymarket:   Yes {opp['market_yes']}%  |  No {opp['market_no']}%")
            print(f"  Mi estimación: Yes {opp['estimated_yes']}%  |  No {opp['estimated_no']}%")
            print(f"  Días hasta:   {opp['days_ahead']}  |  Estación: {opp['station']}")
            if opp["station_url"]:
                print(f"  Verificar:    {opp['station_url']}")
            print(f"  Volumen 24h:  ${opp['volume_24h']:,.0f}  |  Liquidez: ${opp['liquidity']:,.0f}")
            print(f"  >>> {opp['recommendation']}")
            print()

    # ---- RESUMEN ----
    print("=" * 65)
    print(f"  Oportunidades: {len(opportunities)}  (mostrando top {min(20, len(opportunities))})")
    if opportunities:
        high_conf = sum(1 for o in opportunities if o["days_ahead"] <= 1)
        med_conf = sum(1 for o in opportunities if 1 < o["days_ahead"] <= 3)
        low_conf = sum(1 for o in opportunities if o["days_ahead"] > 3)
        print(f"  Confianza ALTA (hoy/mañana): {high_conf}")
        print(f"  Confianza MEDIA (2-3 días):  {med_conf}")
        print(f"  Confianza BAJA (4+ días):    {low_conf}")
    print()
    print("  IMPORTANTE: Antes de operar, verifica la previsión en la")
    print("  URL de la estación. Open-Meteo es una aproximación — la")
    print("  lectura real de Wunderground/NOAA es lo que resuelve.")
    print("=" * 65)
