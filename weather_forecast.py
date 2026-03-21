import urllib.request
import json

# =============================================================
# weather_forecast.py — Previsión meteorológica multi-ciudad
# Sesión 2 del bot de Polymarket
# =============================================================


def get_coordinates(city_name):
    """
    Recibe el nombre de una ciudad y devuelve sus coordenadas (lat, lon)
    y el nombre oficial que encontró la API.

    Usa la API de geocoding de Open-Meteo (gratuita, sin clave).
    'Geocoding' = convertir un nombre de lugar en coordenadas numéricas.
    """
    # Reemplazamos espacios por '+' para que la URL sea válida.
    # Ejemplo: "New York" -> "New+York"
    city_clean = city_name.strip().replace(" ", "+")

    url = (
        f"https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city_clean}&count=1&language=en"
    )

    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())

    # Si la API no encuentra la ciudad, devuelve un dict sin "results"
    if "results" not in data or len(data["results"]) == 0:
        return None  # None = "no encontré nada"

    place = data["results"][0]
    return {
        "name": place["name"],
        "country": place.get("country", ""),
        "lat": place["latitude"],
        "lon": place["longitude"],
    }


def get_forecast(lat, lon):
    """
    Recibe coordenadas y devuelve la previsión a 7 días con:
    - Temperatura máxima y mínima
    - Probabilidad de precipitación (%)
    - Precipitación total (mm)
    - Velocidad máxima del viento (km/h)

    Estas son las variables que más importan para mercados
    meteorológicos en Polymarket (¿lloverá? ¿superará X grados?
    ¿habrá viento fuerte?).
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f",precipitation_probability_max"
        f",precipitation_sum"
        f",wind_speed_10m_max"
        f"&timezone=auto"
    )

    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())

    return data["daily"]


def show_forecast(city_info, daily):
    """
    Muestra la previsión en una tabla legible en terminal.
    Recibe la info de la ciudad y los datos diarios de la API.
    """
    print()
    print(f"  Previsión 7 días — {city_info['name']}, {city_info['country']}")
    print()

    # Cabecera de la tabla
    header = (
        f"  {'Fecha':<12}"
        f"  {'Mín °C':>7}"
        f"  {'Máx °C':>7}"
        f"  {'Lluvia %':>9}"
        f"  {'Precip mm':>10}"
        f"  {'Viento km/h':>12}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    # Filas de datos
    days = daily["time"]
    t_min = daily["temperature_2m_min"]
    t_max = daily["temperature_2m_max"]
    rain_prob = daily["precipitation_probability_max"]
    rain_mm = daily["precipitation_sum"]
    wind = daily["wind_speed_10m_max"]

    for i in range(len(days)):
        row = (
            f"  {days[i]:<12}"
            f"  {t_min[i]:>7.1f}"
            f"  {t_max[i]:>7.1f}"
            f"  {rain_prob[i]:>8}%"
            f"  {rain_mm[i]:>10.1f}"
            f"  {wind[i]:>12.1f}"
        )
        print(row)

    print()


# =============================================================
# PROGRAMA PRINCIPAL
# =============================================================
# Todo lo de arriba son definiciones de funciones (recetas).
# Aquí es donde realmente se ejecuta el programa.
# =============================================================

if __name__ == "__main__":

    print()
    print("=== Previsión Meteorológica para Polymarket ===")
    print()

    # Paso 1: Pedir ciudad al usuario
    city_input = input("Ciudad (o pulsa Enter para Wellington): ").strip()

    # Si el usuario no escribe nada, usamos Wellington por defecto
    if city_input == "":
        city_input = "Wellington"

    # Paso 2: Buscar coordenadas de la ciudad
    print(f"  Buscando '{city_input}'...")
    city_info = get_coordinates(city_input)

    if city_info is None:
        print(f"  No encontré ninguna ciudad llamada '{city_input}'.")
        print("  Comprueba la ortografía e inténtalo de nuevo.")
    else:
        print(f"  Encontrada: {city_info['name']}, {city_info['country']}")
        print(f"  Coordenadas: {city_info['lat']}, {city_info['lon']}")

        # Paso 3: Obtener previsión
        print("  Descargando previsión...")
        daily = get_forecast(city_info["lat"], city_info["lon"])

        # Paso 4: Mostrar resultados
        show_forecast(city_info, daily)
