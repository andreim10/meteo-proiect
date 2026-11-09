"""Modul pentru apelurile către API-uri (Open-Meteo, OSRM, RainViewer).
Toate API-urile folosite sunt gratuite și NU necesită cheie."""

import math

import requests

TIMEOUT = 20
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
RAINVIEWER_URL = "https://api.rainviewer.com/public/weather-maps.json"

# Aeroporturi: cod -> (nume, lat, lon)
AIRPORTS = {
    "OTP": ("București – Henri Coandă", 44.5711, 26.0850),
    "CLJ": ("Cluj-Napoca – Avram Iancu", 46.7852, 23.6862),
    "TSR": ("Timișoara – Traian Vuia", 45.8099, 21.3379),
    "SUJ": ("Satu Mare", 47.7033, 22.8857),
    "IAS": ("Iași", 47.1785, 27.6206),
    "SBZ": ("Sibiu", 45.7856, 24.0913),
    "LHR": ("Londra – Heathrow", 51.4700, -0.4543),
    "CDG": ("Paris – Charles de Gaulle", 49.0097, 2.5479),
    "FRA": ("Frankfurt", 50.0379, 8.5622),
    "VIE": ("Viena", 48.1103, 16.5697),
    "BUD": ("Budapesta – Ferenc Liszt", 47.4369, 19.2556),
}


def _get(url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT,
                     headers={"User-Agent": "proiect-scolar-meteo"})
    r.raise_for_status()
    return r.json()


def geocode(nume):
    j = _get(GEO_URL, {"name": nume, "count": 1, "language": "ro", "format": "json"})
    rez = j.get("results")
    if not rez:
        raise ValueError(f"Orașul „{nume}” nu a fost găsit.")
    o = rez[0]
    return {"name": o["name"], "country": o.get("country", ""),
            "lat": o["latitude"], "lon": o["longitude"],
            "population": o.get("population") or 0}


def suggest(nume, n=8):
    """Sugestii de orașe pentru autocomplete (în timp ce scrii)."""
    j = _get(GEO_URL, {"name": nume, "count": n, "language": "ro", "format": "json"})
    return [{"name": o["name"], "country": o.get("country", ""), "admin1": o.get("admin1", ""),
             "lat": o["latitude"], "lon": o["longitude"], "population": o.get("population") or 0}
            for o in j.get("results", [])]


def forecast(lat, lon, days=10):
    """Vremea curentă + date pe ore + prognoză zilnică."""
    return _get(FORECAST_URL, {
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": days,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
                   "weather_code,cloud_cover,surface_pressure,wind_speed_10m,"
                   "wind_gusts_10m,is_day",
        "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                  "precipitation_probability,precipitation,weather_code,cloud_cover,"
                  "visibility,wind_speed_10m,wind_gusts_10m,uv_index",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "apparent_temperature_max,apparent_temperature_min,precipitation_sum,"
                 "precipitation_probability_max,wind_gusts_10m_max,uv_index_max,"
                 "sunrise,sunset",
    })


def forecast_extra(lat, lon, days=7):
    """Date suplimentare: radiație solară (panouri), presiune (pescuit/migrene),
    umiditatea și temperatura solului (agricultură). Separat, ca să nu strice restul."""
    return _get(FORECAST_URL, {
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": days,
        "hourly": "surface_pressure,shortwave_radiation,soil_moisture_3_to_9cm,soil_temperature_6cm",
        "daily": "sunshine_duration,et0_fao_evapotranspiration",
    })


def air_quality(lat, lon):
    """AQI, PM2.5, PM10, CO2 și polen (polenul există doar pentru Europa)."""
    j = _get(AIR_URL, {
        "latitude": lat, "longitude": lon, "timezone": "auto",
        "current": "european_aqi,pm10,pm2_5,carbon_dioxide,alder_pollen,birch_pollen,"
                   "grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen",
    })
    return j["current"]


def historical(lat, lon, zi, ani_in_urma):
    """Vremea din aceeași zi, cu N ani în urmă (arhiva ERA5 – din 1940)."""
    try:
        d = zi.replace(year=zi.year - ani_in_urma)
    except ValueError:            # 29 februarie
        d = zi.replace(year=zi.year - ani_in_urma, day=28)
    j = _get(ARCHIVE_URL, {
        "latitude": lat, "longitude": lon, "timezone": "auto",
        "start_date": d.isoformat(), "end_date": d.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
    })["daily"]
    return {"an": d.year, "tmax": j["temperature_2m_max"][0],
            "tmin": j["temperature_2m_min"][0], "precip": j["precipitation_sum"][0]}


def _haversine(a, b):
    """Distanța în km între două puncte (lon, lat)."""
    R = 6371
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dla = la2 - la1
    dlo = math.radians(b[0] - a[0])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def route(a, b, n_puncte=6):
    """Traseu auto A -> B. Returnează (puncte_cheie, durata_s, distanta_km).
    Fiecare punct: {lat, lon, km, frac} unde frac = cât din drum s-a parcurs (0..1)."""
    url = f"{OSRM_URL}/{a['lon']},{a['lat']};{b['lon']},{b['lat']}"
    j = _get(url, {"overview": "full", "geometries": "geojson"})
    if j.get("code") != "Ok":
        raise ValueError("Nu s-a putut calcula un traseu auto între cele două locuri.")
    r = j["routes"][0]
    coords = r["geometry"]["coordinates"]
    cum = [0.0]
    for i in range(1, len(coords)):
        cum.append(cum[-1] + _haversine(coords[i - 1], coords[i]))
    total = cum[-1] or 1
    puncte = []
    for k in range(n_puncte):
        tinta = total * k / (n_puncte - 1)
        idx = min(range(len(cum)), key=lambda i: abs(cum[i] - tinta))
        lon, lat = coords[idx]
        puncte.append({"lat": lat, "lon": lon, "km": cum[idx] * r["distance"] / 1000 / total,
                       "frac": cum[idx] / total})
    return puncte, r["duration"], r["distance"] / 1000


def rainviewer():
    """Dalele de radar / satelit pentru hartă."""
    return _get(RAINVIEWER_URL)
