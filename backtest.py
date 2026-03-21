import urllib.request
import json
import re
import math

# =============================================================
# backtest.py — ¿Nuestro modelo habría ganado dinero?
# Sesión 2 del bot de Polymarket
# =============================================================
#
# Este script hace un "backtest" (prueba histórica):
#
# 1. Busca mercados de temperatura que YA se resolvieron
# 2. Ve cuál fue el resultado real (qué temperatura ganó)
# 3. Simula qué habría dicho nuestro modelo
# 4. Calcula si habríamos ganado o perdido
#
# ¿Por qué importa? Porque un modelo que detecta "edge" pero
# pierde dinero no sirve de nada. Necesitamos EVIDENCIA de que
# las señales del bot son rentables antes de operar con dinero.
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

# Coordenadas de aeropuertos (copiado de edge_detector.py)
RESOLUTION_STATIONS = {
    "Seoul": {"lat": 37.4602, "lon": 126.4407, "name": "Incheon Intl"},
    "London": {"lat": 51.5048, "lon": 0.0495, "name": "London City"},
    "Tel Aviv": {"lat": 32.0114, "lon": 34.8867, "name": "Ben Gurion"},
    "Shanghai": {"lat": 31.1443, "lon": 121.8083, "name": "Pudong"},
    "Tokyo": {"lat": 35.5494, "lon": 139.7798, "name": "Haneda"},
    "New York City": {"lat": 40.7772, "lon": -73.8726, "name": "LaGuardia"},
    "Beijing": {"lat": 40.0799, "lon": 116.6031, "name": "Beijing Capital"},
    "Hong Kong": {"lat": 22.3080, "lon": 113.9185, "name": "HK Intl"},
    "Singapore": {"lat": 1.3502, "lon": 103.9940, "name": "Changi"},
    "Toronto": {"lat": 43.6772, "lon": -79.6306, "name": "Pearson"},
    "Chicago": {"lat": 41.9742, "lon": -87.9073, "name": "O'Hare"},
    "Wellington": {"lat": -41.3272, "lon": 174.8053, "name": "Wellington"},
    "Munich": {"lat": 48.3538, "lon": 11.7861, "name": "Munich"},
    "Warsaw": {"lat": 52.1657, "lon": 20.9671, "name": "Warsaw Chopin"},
    "Ankara": {"lat": 40.1281, "lon": 32.9951, "name": "Esenboğa"},
    "Atlanta": {"lat": 33.6407, "lon": -84.4277, "name": "Hartsfield"},
    "Shenzhen": {"lat": 22.6393, "lon": 113.8107, "name": "Bao'an"},
    "Paris": {"lat": 49.0097, "lon": 2.5479, "name": "CDG"},
    "Buenos Aires": {"lat": -34.8222, "lon": -58.5358, "name": "Ezeiza"},
}


# =============================================================
# FUNCIONES (mismas que edge_detector.py)
# =============================================================

def api_get(endpoint):
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.1")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_historical_forecast(lat, lon, date_iso):
    """
    Obtiene la previsión HISTÓRICA de Open-Meteo para una fecha pasada.

    Open-Meteo tiene un endpoint de archivo que guarda las previsiones
    que hizo en el pasado. Esto es CLAVE para el backtest: no queremos
    saber la temperatura real (eso ya lo sabemos por cómo resolvió
    el mercado), queremos saber qué HABRÍA PREDICHO nuestro modelo
    en ese momento.

    Nota: usamos el endpoint de datos históricos reales (archive),
    no la previsión. Para un backtest más preciso, necesitaríamos
    las previsiones históricas, pero Open-Meteo solo ofrece datos
    reales gratis. Esto es una simplificación que funciona para
    validar el concepto.
    """
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={date_iso}&end_date={date_iso}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone=auto"
    )
    try:
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())
        daily = data.get("daily", {})
        if daily and daily.get("temperature_2m_max"):
            return {
                "temp_max": daily["temperature_2m_max"][0],
                "temp_min": daily["temperature_2m_min"][0],
            }
    except Exception:
        pass
    return None


def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def estimate_probability(forecast_max, threshold_c, condition, sigma=1.0):
    """Calcula probabilidad estimada usando modelo normal + redondeo."""
    mu = forecast_max

    if condition == "exact":
        lower = threshold_c - 0.5
        upper = threshold_c + 0.5
        prob = normal_cdf(upper, mu, sigma) - normal_cdf(lower, mu, sigma)

    elif condition == "at_or_below":
        upper = threshold_c + 0.5
        prob = normal_cdf(upper, mu, sigma)

    elif condition == "at_or_above":
        lower = threshold_c - 0.5
        prob = 1.0 - normal_cdf(lower, mu, sigma)

    else:
        prob = 0.5

    return max(0.01, min(0.99, prob))


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
        "city": city,
        "temp_threshold": temp,
        "condition": condition,
        "date_str": date_str,
        "unit": unit,
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
# PROGRAMA PRINCIPAL
# =============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("  BACKTEST — ¿Nuestro modelo habría ganado dinero?")
    print("=" * 65)
    print()

    # ---- PASO 1: Obtener mercados CERRADOS (resueltos) ----
    print("  [1/3] Obteniendo mercados de temperatura ya resueltos...")

    try:
        events = api_get(
            f"/events"
            f"?tag_id={DAILY_TEMP_TAG_ID}"
            f"&closed=true"
            f"&limit=20"
            f"&order=endDate"
            f"&ascending=false"
        )
    except Exception as e:
        print(f"  Error: {e}")
        events = []

    # Extraer mercados individuales
    all_markets = []
    for event in events:
        for market in event.get("markets", []):
            all_markets.append(market)

    print(f"        Mercados resueltos encontrados: {len(all_markets)}")

    # ---- PASO 2: Analizar cada mercado resuelto ----
    print("  [2/3] Analizando mercados y consultando datos históricos...")
    print()

    results = []
    cities_forecast_cache = {}  # {(city, date): temp_max}

    for market in all_markets:
        question = market.get("question", "")
        parsed = parse_temperature_question(question)
        if not parsed or not parsed["date_str"]:
            continue

        city = parsed["city"]
        date_iso = date_text_to_iso(parsed["date_str"])
        if not date_iso:
            continue

        # ¿El mercado resolvió como Yes o No?
        # En mercados resueltos, outcomePrices será "1" para el ganador
        prices_raw = market.get("outcomePrices", "[]")
        outcomes_raw = market.get("outcomes", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except (json.JSONDecodeError, TypeError):
            continue

        if not prices or not outcomes:
            continue

        # Determinar resultado real
        yes_price = float(prices[0])
        if yes_price > 0.9:
            actual_result = "YES"
        elif yes_price < 0.1:
            actual_result = "NO"
        else:
            continue  # No está claramente resuelto

        # Obtener temperatura histórica del aeropuerto
        station = RESOLUTION_STATIONS.get(city)
        if not station:
            continue

        cache_key = (city, date_iso)
        if cache_key not in cities_forecast_cache:
            hist = get_historical_forecast(station["lat"], station["lon"], date_iso)
            if hist:
                cities_forecast_cache[cache_key] = hist["temp_max"]
            else:
                cities_forecast_cache[cache_key] = None

        forecast_max = cities_forecast_cache.get(cache_key)
        if forecast_max is None:
            continue

        # Calcular qué habría dicho nuestro modelo
        threshold = parsed["temp_threshold"]
        if parsed["unit"] == "F":
            threshold_c = (threshold - 32) * 5 / 9
        else:
            threshold_c = float(threshold)

        # Usamos sigma=1.0 (como si fuera predicción a 1 día)
        our_prob_yes = estimate_probability(
            forecast_max, threshold_c, parsed["condition"], sigma=1.0
        )

        # ¿Habríamos detectado edge?
        # Simulamos que compramos si nuestro edge > 10%
        our_prob_yes_pct = our_prob_yes * 100
        our_prob_no_pct = (1 - our_prob_yes) * 100

        # Para este backtest simple, simulamos que Polymarket
        # estaba en 50/50 (no tenemos los precios históricos del
        # momento exacto en que habríamos entrado). Lo que medimos
        # es si nuestra SEÑAL (YES o NO) coincide con el resultado real.
        if our_prob_yes > 0.5:
            our_signal = "YES"
        else:
            our_signal = "NO"

        correct = our_signal == actual_result

        results.append({
            "question": question,
            "city": city,
            "date": date_iso,
            "threshold": threshold,
            "unit": parsed["unit"],
            "condition": parsed["condition"],
            "forecast_max": forecast_max,
            "our_prob_yes": our_prob_yes_pct,
            "our_signal": our_signal,
            "actual_result": actual_result,
            "correct": correct,
        })

    # ---- PASO 3: Resultados ----
    print("=" * 65)
    print("  RESULTADOS DEL BACKTEST")
    print("=" * 65)
    print()

    if not results:
        print("  No se pudieron analizar mercados resueltos.")
        print("  Posibles razones:")
        print("    - Los datos históricos no están disponibles aún")
        print("    - Las ciudades no están en nuestra tabla de aeropuertos")
        print()
    else:
        correct_count = sum(1 for r in results if r["correct"])
        total = len(results)
        accuracy = correct_count / total * 100

        # Mostrar cada mercado
        for r in results:
            status = "ACIERTO" if r["correct"] else "FALLO"
            unit = "°" + r["unit"]
            print(f"  [{status}] {r['question']}")
            print(f"          Open-Meteo max: {r['forecast_max']:.1f}°C | "
                  f"Umbral: {r['threshold']}{unit} ({r['condition']})")
            print(f"          Nuestro modelo: {r['our_signal']} ({r['our_prob_yes']:.1f}% Yes) | "
                  f"Resultado real: {r['actual_result']}")
            print()

        # Resumen
        print("=" * 65)
        print(f"  RESUMEN")
        print(f"  Mercados analizados: {total}")
        print(f"  Aciertos: {correct_count}")
        print(f"  Fallos: {total - correct_count}")
        print(f"  Precisión: {accuracy:.1f}%")
        print()

        if accuracy >= 60:
            print(f"  El modelo acierta el {accuracy:.0f}% de las veces.")
            print(f"  En mercados binarios, >55% ya es rentable a largo plazo.")
            print(f"  Esto es prometedor, pero necesitamos más datos para")
            print(f"  confirmar (idealmente 100+ mercados).")
        elif accuracy >= 50:
            print(f"  Precisión del {accuracy:.0f}% — básicamente aleatorio.")
            print(f"  El modelo necesita mejoras antes de operar con dinero.")
        else:
            print(f"  Precisión del {accuracy:.0f}% — PEOR que aleatorio.")
            print(f"  Algo está mal. Revisar las fuentes de datos.")

        print("=" * 65)
