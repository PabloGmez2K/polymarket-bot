# CONTEXTO SESIÓN 1 — Bot Polymarket

**Fecha:** 21 de marzo de 2026

---

## Qué hemos construido

Un script Python (`wellington_forecast.py`) que hace una llamada GET a la API gratuita de Open-Meteo y muestra en terminal la previsión de temperatura máxima y mínima de Wellington (Nueva Zelanda) para los próximos 7 días. No usa librerías externas — solo `urllib` y `json` de la librería estándar de Python.

---

## Qué he aprendido

- **Abrir y usar la terminal de Windows (cmd):** navegar carpetas con `cd`, comprobar la versión de Python con `python --version`, ejecutar scripts con `python nombre.py`.
- **Cómo funciona una llamada a una API:** se construye una URL con parámetros (latitud, longitud, datos que pides), se envía una petición HTTP GET, y la API devuelve datos en formato JSON.
- **Que Open-Meteo es gratuita y no necesita clave de API**, lo que la hace perfecta para prototipar.
- **Por qué no hacer doble clic en un .py:** la ventana se cierra al terminar. Hay que ejecutarlo desde la terminal para ver el resultado.

---

## Estado actual del código

```python
import urllib.request
import json

# Wellington, New Zealand
LAT = -41.2866
LON = 174.7756

url = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&daily=temperature_2m_max,temperature_2m_min"
    f"&timezone=Pacific%2FAuckland"
)

resp = urllib.request.urlopen(url)
data = json.loads(resp.read())

print("🌡️  Previsión de temperatura — Wellington, NZ\n")
print(f"{'Fecha':<14} {'Mín (°C)':>10} {'Máx (°C)':>10}")
print("-" * 36)

days  = data["daily"]["time"]
t_min = data["daily"]["temperature_2m_min"]
t_max = data["daily"]["temperature_2m_max"]

for d, lo, hi in zip(days, t_min, t_max):
    print(f"{d:<14} {lo:>10.1f} {hi:>10.1f}")
```

**Ubicación del archivo:** `Downloads/wellington_forecast.py`  
**Ejecución:** `python wellington_forecast.py` desde cmd en la carpeta Downloads.

---

## Siguiente paso hacia el objetivo final

**Sesión 2 — Ampliar el script para que sea útil como fuente de datos del bot:**

1. Permitir elegir cualquier ciudad desde la terminal (input del usuario o argumento).
2. Añadir más variables meteorológicas relevantes para Polymarket (precipitación, viento, etc.).
3. Empezar a organizar el código en funciones reutilizables — preparando la estructura para cuando el bot necesite consultar previsiones automáticamente.

**Camino hacia el bot completo (vista general):**
- ~~Sesión 1: Primera llamada a API meteorológica~~ ✅
- Sesión 2: Script flexible con múltiples ciudades y variables
- Sesión 3: Conectar con la API de Polymarket (leer mercados meteorológicos)
- Sesión 4: Comparar previsión real vs. probabilidades de Polymarket (detectar edge)
- Sesión 5+: Ejecución automática de órdenes, alertas, despliegue en Railway

---

## Mi nivel técnico actual

- **Programación:** Principiante total. Primer proyecto real con Python. Sabe ejecutar scripts desde terminal pero aún no ha escrito código propio.
- **Terminal:** Sabe abrir cmd, navegar con `cd`, ejecutar `python archivo.py`.
- **Python:** Versión 3.14.3 instalada en Windows. No ha usado VS Code ni Git todavía.
- **Conceptos adquiridos:** Qué es una API REST, qué es JSON, cómo se construye una URL con parámetros.
- **Herramientas pendientes:** VS Code, Git/GitHub, pip (instalar librerías), Railway.
