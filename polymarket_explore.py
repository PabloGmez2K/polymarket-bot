import urllib.request
import json

# =============================================================
# polymarket_explore.py — Explorar mercados de Polymarket
# Sesión 2 del bot de Polymarket
# =============================================================
#
# Este script consulta la Gamma API de Polymarket para encontrar
# mercados meteorológicos activos usando tag_id verificados.
#
# Los tag IDs se obtuvieron con debug_tags.py y son estables.
# Si Polymarket cambia sus tags en el futuro, hay que re-verificar.
#
# Documentación: https://docs.polymarket.com/market-data/fetching-markets
# =============================================================

GAMMA_URL = "https://gamma-api.polymarket.com"

# Tags meteorológicos verificados con sus IDs reales
# Obtenidos de: GET /tags/slug/{slug}
WEATHER_TAGS = [
    {"id": "103040", "label": "Daily Temperature", "slug": "temperature"},
    {"id": "84",     "label": "Weather",           "slug": "weather"},
    {"id": "1474",   "label": "Climate & Weather",  "slug": "climate-weather"},
    {"id": "103041", "label": "Precipitation",      "slug": "precipitation"},
    {"id": "85",     "label": "Hurricanes",         "slug": "hurricanes"},
    {"id": "832",    "label": "Global Temp",         "slug": "global-temp"},
    {"id": "496",    "label": "Natural Disasters",   "slug": "natural-disasters"},
]


def api_get(endpoint):
    """
    Hace una petición GET a la Gamma API de Polymarket.
    """
    url = GAMMA_URL + endpoint
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-bot/0.1")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_markets_by_tag(tag_id, limit=10):
    """
    Obtiene mercados activos (no cerrados) para un tag específico.
    Ordenados por volumen 24h (mayor primero) para ver los más activos.
    """
    endpoint = (
        f"/events"
        f"?tag_id={tag_id}"
        f"&active=true"
        f"&closed=false"
        f"&limit={limit}"
        f"&order=volume24hr"
        f"&ascending=false"
    )
    return api_get(endpoint)


def parse_market_data(market):
    """
    Extrae los datos importantes de un mercado en un diccionario limpio.
    Esto es útil porque los datos crudos de la API vienen en formatos
    inconsistentes (strings que son JSON, números que son strings, etc.).

    Devuelve None si el mercado no tiene datos válidos.
    """
    question = market.get("question", "")
    if not question:
        return None

    # Parsear probabilidades (vienen como string JSON)
    prices_raw = market.get("outcomePrices", "[]")
    outcomes_raw = market.get("outcomes", "[]")
    try:
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
    except (json.JSONDecodeError, TypeError):
        prices, outcomes = [], []

    # Construir pares outcome:probabilidad
    probabilities = {}
    if prices and outcomes:
        for outcome, price in zip(outcomes, prices):
            probabilities[outcome] = round(float(price) * 100, 1)

    return {
        "question": question,
        "probabilities": probabilities,
        "volume": float(market.get("volume", 0)),
        "volume_24h": float(market.get("volume24hr", 0)),
        "liquidity": float(market.get("liquidity", 0)),
        "end_date": market.get("endDate", "")[:10],
        "id": market.get("id", ""),
        "slug": market.get("slug", ""),
    }


def show_markets(events, max_display=8):
    """
    Muestra los mercados encontrados.
    Devuelve la lista de mercados parseados (para uso futuro del bot).
    """
    if not events:
        print("  No se encontraron mercados.\n")
        return []

    parsed_markets = []
    count = 0

    for event in events:
        markets = event.get("markets", [])
        for market in markets:
            if count >= max_display:
                return parsed_markets

            data = parse_market_data(market)
            if not data or data["volume"] < 1:
                continue

            count += 1
            parsed_markets.append(data)

            print(f"  [{count}] {data['question']}")

            if data["probabilities"]:
                probs = [f"{k}: {v}%" for k, v in data["probabilities"].items()]
                print(f"      Probabilidades: {' | '.join(probs)}")

            print(f"      Volumen total: ${data['volume']:,.0f}", end="")
            if data["volume_24h"] > 0:
                print(f"  |  24h: ${data['volume_24h']:,.0f}", end="")
            if data["liquidity"] > 0:
                print(f"  |  Liquidez: ${data['liquidity']:,.0f}", end="")
            print()

            if data["end_date"]:
                print(f"      Cierre: {data['end_date']}")

            print()

    return parsed_markets


# =============================================================
# PROGRAMA PRINCIPAL
# =============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("  EXPLORADOR DE MERCADOS METEOROLÓGICOS — POLYMARKET")
    print("=" * 60)
    print()
    print(f"  Tags a consultar: {len(WEATHER_TAGS)}")
    for tag in WEATHER_TAGS:
        print(f"    - {tag['label']} (id: {tag['id']})")
    print()

    total_markets = 0

    for tag in WEATHER_TAGS:
        tag_id = tag["id"]
        label = tag["label"]

        print("-" * 60)
        print(f"  {label}")
        print("-" * 60)

        try:
            events = get_markets_by_tag(tag_id, limit=10)
            parsed = show_markets(events, max_display=5)
            total_markets += len(parsed)
        except Exception as e:
            print(f"  Error: {e}\n")

    print("=" * 60)
    print(f"  Total mercados mostrados: {total_markets}")
    print("=" * 60)
