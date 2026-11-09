"""Alerte pentru dezastre naturale în locația curentă.
Surse gratuite, fără cheie API:
  - USGS            -> cutremure (ultimele 7 zile, rază 300 km)
  - NASA EONET      -> incendii, vulcani, furtuni, inundații etc. (evenimente deschise, ±3° ≈ 300 km)
  - Open-Meteo Flood-> estimare debit râuri (risc de inundații)
  - Prognoza meteo  -> ploi torențiale, vânt, caniculă, ger, furtuni, risc de incendii de vegetație
Niveluri: 1 = informativ, 2 = atenție, 3 = pericol.  NU înlocuiește alertele oficiale (112, RO-ALERT)."""

import math
from datetime import datetime, timedelta, timezone

import api

USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
EONET = "https://eonet.gsfc.nasa.gov/api/v3/events"
FLOOD = "https://flood-api.open-meteo.com/v1/flood"
NIVEL = {1: "🟢 informativ", 2: "🟠 atenție", 3: "🔴 pericol"}
EMOJI_EONET = {"Wildfires": "🔥", "Volcanoes": "🌋", "Severe Storms": "⛈️", "Floods": "🌊",
               "Landslides": "⛰️", "Drought": "🏜️", "Sea and Lake Ice": "🧊", "Snow": "❄️",
               "Dust and Haze": "🌫️", "Earthquakes": "🌍", "Temperature Extremes": "🌡️"}
LINKURI_RO = ("Surse oficiale România: meteoromania.ro (avertizări meteo), hidro.ro (hidrologie / inundații), "
              "infp.ro (cutremure), dsu.mai.gov.ro (situații de urgență). Urgențe: 112 · mesaje RO-ALERT.")
LINKURI_GEN = ("Surse oficiale: serviciul meteo național, meteoalarm.org (Europa), gdacs.org (dezastre globale), "
               "earthquake.usgs.gov. Număr de urgență în UE: 112.")


def km(lat1, lon1, lat2, lon2):
    r = math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def cutremure(lat, lon):
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    j = api._get(USGS, {"format": "geojson", "latitude": lat, "longitude": lon, "maxradiuskm": 300,
                        "minmagnitude": 2.5, "orderby": "time", "starttime": start})
    out = []
    for f in j["features"]:
        p = f["properties"]
        mag = p.get("mag") or 0
        lo, la = f["geometry"]["coordinates"][:2]
        out.append((3 if mag >= 5 else 2 if mag >= 4 else 1, "🌍 Cutremur", f"M{mag:.1f} – {p.get('place', '')}",
                    km(lat, lon, la, lo), datetime.fromtimestamp(p["time"] / 1000, timezone.utc).strftime("%d.%m %H:%M UTC")))
    return out


def evenimente(lat, lon, delta=3):
    j = api._get(EONET, {"status": "open", "days": 14,
                         "bbox": f"{lon - delta},{lat + delta},{lon + delta},{lat - delta}"})
    out = []
    for e in j["events"]:
        g = e["geometry"][-1]
        c = g["coordinates"]
        while isinstance(c[0], list):
            c = c[0]
        d = km(lat, lon, c[1], c[0])
        cat = e["categories"][0]["title"]
        out.append((2 if d < 100 else 1, f"{EMOJI_EONET.get(cat, '⚠️')} {cat}", e["title"], d, g["date"][:10]))
    return out


def inundatii(lat, lon):
    j = api._get(FLOOD, {"latitude": lat, "longitude": lon, "daily": "river_discharge",
                         "past_days": 30, "forecast_days": 7})
    t, v = j["daily"]["time"], j["daily"]["river_discharge"]
    azi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trecut = sorted(x for z, x in zip(t, v) if z < azi and x is not None)
    viitor = [x for z, x in zip(t, v) if z >= azi and x is not None]
    if not trecut or not viitor or trecut[len(trecut) // 2] <= 0:
        return []
    raport = max(viitor) / trecut[len(trecut) // 2]
    if raport >= 3:
        return [(3, "🌊 Inundații", f"Debit foarte mare prevăzut la râul din apropiere (~{raport:.1f}× față de normal)", 0, "7 zile")]
    if raport >= 2:
        return [(2, "🌊 Inundații", f"Debit în creștere la râul din apropiere (~{raport:.1f}× față de normal)", 0, "7 zile")]
    return []


def din_meteo(data):
    d, h = data["daily"], data["hourly"]
    out = []
    pm = max(d["precipitation_sum"][:3])
    g = max(v for v in h["wind_gusts_10m"][:72] if v is not None)
    tx, tn = max(d["temperature_2m_max"][:3]), min(d["temperature_2m_min"][:3])
    if pm >= 50: out.append((3, "🌧️ Ploi torențiale", f"până la {pm:.0f} mm într-o zi", 0, "3 zile"))
    elif pm >= 30: out.append((2, "🌧️ Ploi abundente", f"până la {pm:.0f} mm într-o zi", 0, "3 zile"))
    if g >= 90: out.append((3, "🌪️ Vânt violent", f"rafale până la {g:.0f} km/h", 0, "3 zile"))
    elif g >= 60: out.append((2, "💨 Vânt puternic", f"rafale până la {g:.0f} km/h", 0, "3 zile"))
    if tx >= 38: out.append((3, "🔥 Caniculă extremă", f"maxime de {tx:.0f}°C", 0, "3 zile"))
    elif tx >= 35: out.append((2, "🔥 Caniculă", f"maxime de {tx:.0f}°C", 0, "3 zile"))
    if tn <= -15: out.append((3, "🥶 Ger extrem", f"minime de {tn:.0f}°C", 0, "3 zile"))
    elif tn <= -10: out.append((2, "🥶 Ger puternic", f"minime de {tn:.0f}°C", 0, "3 zile"))
    if any(c >= 95 for c in d["weather_code"][:3]): out.append((2, "⛈️ Furtuni", "furtuni (posibil grindină) în următoarele 3 zile", 0, "3 zile"))
    if any(c in (75, 86) for c in d["weather_code"][:3]): out.append((2, "❄️ Ninsoare abundentă", "ninsori puternice prevăzute", 0, "3 zile"))
    hum = [v for v in h["relative_humidity_2m"][:48] if v is not None]
    if hum and sum(hum) / len(hum) < 35 and tx >= 28 and g >= 25 and sum(d["precipitation_sum"][:7]) < 5:
        out.append((2, "🔥 Risc de incendii de vegetație", "aer uscat, cald, vânt și fără ploaie", 0, "48 ore"))
    return out


def colecteaza(city, data):
    """Returnează (alerte sortate, stări surse). Fiecare sursă e independentă: dacă una cade, restul merg."""
    lat, lon = city["lat"], city["lon"]
    alerte, stari = din_meteo(data), []
    for nume, f in [("Cutremure (USGS)", lambda: cutremure(lat, lon)),
                    ("Evenimente naturale (NASA EONET)", lambda: evenimente(lat, lon)),
                    ("Inundații (Open-Meteo Flood)", lambda: inundatii(lat, lon))]:
        try:
            alerte += f()
            stari.append(f"✔ {nume}")
        except Exception:
            stari.append(f"✘ {nume} – indisponibil acum")
    alerte.sort(key=lambda a: (-a[0], a[3]))
    return alerte, stari
