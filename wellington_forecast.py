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
