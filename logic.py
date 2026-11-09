"""Logica aplicației: interpretarea datelor meteo, indici, recomandări.
Nu conține nimic legat de interfață sau de rețea."""

from datetime import datetime, timedelta

WMO = {
    0: "Cer senin", 1: "Predominant senin", 2: "Parțial noros", 3: "Noros",
    45: "Ceață", 48: "Ceață cu chiciură",
    51: "Burniță ușoară", 53: "Burniță", 55: "Burniță densă",
    56: "Burniță înghețată", 57: "Burniță înghețată densă",
    61: "Ploaie ușoară", 63: "Ploaie", 65: "Ploaie puternică",
    66: "Ploaie înghețată", 67: "Ploaie înghețată puternică",
    71: "Ninsoare ușoară", 73: "Ninsoare", 75: "Ninsoare puternică", 77: "Fulgi de zăpadă",
    80: "Averse ușoare", 81: "Averse", 82: "Averse violente",
    85: "Averse de ninsoare", 86: "Averse de ninsoare puternice",
    95: "Furtună", 96: "Furtună cu grindină", 99: "Furtună cu grindină puternică",
}


def emoji(cod):
    if cod == 0: return "☀️"
    if cod == 1: return "🌤️"
    if cod == 2: return "⛅"
    if cod == 3: return "☁️"
    if cod in (45, 48): return "🌫️"
    if 51 <= cod <= 57: return "🌦️"
    if 61 <= cod <= 67 or 80 <= cod <= 82: return "🌧️"
    if 71 <= cod <= 77 or cod in (85, 86): return "❄️"
    if cod >= 95: return "⛈️"
    return "🌡️"


def weather_text(cod):
    return f"{emoji(cod)} {WMO.get(cod, 'Necunoscut')}"


def is_rain(c): return 51 <= c <= 67 or 80 <= c <= 82
def is_snow(c): return 71 <= c <= 77 or c in (85, 86)
def is_storm(c): return c >= 95


def theme(cod, is_day):
    """Culorile și tipul de animație pentru fundalul dinamic."""
    if is_storm(cod):  return {"bg": "#3b4452", "fg": "white", "kind": "storm"}
    if is_rain(cod):   return {"bg": "#5b7189", "fg": "white", "kind": "rain"}
    if is_snow(cod):   return {"bg": "#d3dce6", "fg": "#1f2d3d", "kind": "snow"}
    if cod in (45, 48): return {"bg": "#aab2ba", "fg": "#1f2d3d", "kind": "fog"}
    if not is_day:     return {"bg": "#15213f", "fg": "white", "kind": "night"}
    if cod == 3:       return {"bg": "#8da2b8", "fg": "white", "kind": "cloud"}
    return {"bg": "#4aa3e8", "fg": "white", "kind": "clear"}


# ---------------------------------------------------------------- utilitare
def hour_index(data):
    """Indexul orei curente în listele 'hourly'."""
    t = data["current"]["time"][:13] + ":00"
    try:
        return data["hourly"]["time"].index(t)
    except ValueError:
        return 0


def _next(h, key, i, n):
    return [v for v in h[key][i:i + n] if v is not None]


# ---------------------------------------------------------------- avertizări
def warnings(data):
    h, d = data["hourly"], data["daily"]
    i = hour_index(data)
    out = []
    gust = max(_next(h, "wind_gusts_10m", i, 48) or [0])
    if gust >= 90:
        out.append(f"🌪️ Vânt foarte puternic: rafale de până la {gust:.0f} km/h")
    elif gust >= 60:
        out.append(f"💨 Rafale puternice de vânt: până la {gust:.0f} km/h")
    tmax = max(d["temperature_2m_max"][:3])
    tmin = min(d["temperature_2m_min"][:3])
    if tmax >= 35:
        out.append(f"🔥 Caniculă: maxime de până la {tmax:.0f}°C")
    elif tmax >= 30:
        out.append(f"🥵 Căldură: maxime de {tmax:.0f}°C")
    if tmin <= -10:
        out.append(f"🥶 Ger puternic: minime de {tmin:.0f}°C")
    elif tmin <= -2:
        out.append(f"🧊 Îngheț: minime de {tmin:.0f}°C")
    codes = d["weather_code"][:3]
    if any(is_storm(c) for c in codes):
        out.append("⛈️ Furtuni posibile în următoarele 3 zile")
    if any(is_snow(c) for c in codes):
        out.append("❄️ Ninsori posibile în următoarele 3 zile")
    if max(d["precipitation_sum"][:3]) >= 30:
        out.append("🌧️ Cantități mari de precipitații (peste 30 mm/zi)")
    if max(d["uv_index_max"][:3]) >= 8:
        out.append("☀️ Index UV foarte ridicat – protecție solară necesară")
    return out or ["✅ Nicio avertizare meteo în următoarele zile"]


# ---------------------------------------------------------------- activități casnice
def car_wash(data):
    h, i = data["hourly"], hour_index(data)
    prob = max(_next(h, "precipitation_probability", i, 48) or [0])
    mm = sum(_next(h, "precipitation", i, 48))
    if prob < 25 and mm < 0.5:
        return "✅ Da, merită", f"Șanse de ploaie în 48h: {prob:.0f}% – mașina rămâne curată."
    if prob < 50:
        return "🤔 Posibil", f"Șanse de ploaie în 48h: {prob:.0f}% – risc moderat."
    return "❌ Nu", f"Șanse mari de ploaie în 48h ({prob:.0f}%, ~{mm:.1f} mm)."


def laundry(data):
    h, i = data["hourly"], hour_index(data)
    prob = max(_next(h, "precipitation_probability", i, 24) or [0])
    hum_l = _next(h, "relative_humidity_2m", i, 24) or [70]
    hum = sum(hum_l) / len(hum_l)
    wind_l = _next(h, "wind_speed_10m", i, 24) or [0]
    wind = sum(wind_l) / len(wind_l)
    det = f"Umiditate medie {hum:.0f}%, ploaie {prob:.0f}%, vânt mediu {wind:.0f} km/h."
    if prob < 20 and hum < 70:
        return "✅ Excelent pentru uscat afară", det
    if prob < 40 and hum < 85:
        return "🤔 Acceptabil (se usucă mai greu)", det
    return "❌ Mai bine în casă", det


def _clamp(x):
    return max(0, min(10, round(x)))


def _verdict(s):
    return ("Condiții excelente" if s >= 8 else "Condiții bune" if s >= 6
            else "Acceptabil" if s >= 4 else "Nefavorabil")


def activities(data, air=None):
    """Listă de (activitate, scor 0-10, comentariu)."""
    cur, h, d = data["current"], data["hourly"], data["daily"]
    i = hour_index(data)
    t = cur["apparent_temperature"]
    w = cur["wind_speed_10m"]
    prob = max(_next(h, "precipitation_probability", i, 6) or [0])
    aqi = (air or {}).get("european_aqi") or 0

    def scor(lo, hi, wmax, aer=True):
        s = 10.0
        if t < lo: s -= (lo - t) * 0.4
        if t > hi: s -= (t - hi) * 0.5
        if w > wmax: s -= (w - wmax) * 0.15
        s -= prob * 0.08
        if aer and aqi > 60: s -= (aqi - 60) * 0.05
        return _clamp(s)

    rez = []
    for nume, args, aer in [("🏃 Alergat", (4, 18, 25), True),
                            ("🚴 Ciclism", (8, 26, 18), True),
                            ("🌱 Grădinărit", (10, 27, 30), False)]:
        s = scor(*args, aer=aer)
        rez.append((nume, s, f"{_verdict(s)} (se simte {t:.0f}°C, vânt {w:.0f} km/h, ploaie {prob:.0f}%)"))

    # Fotografie: Golden Hour
    now = datetime.fromisoformat(cur["time"])
    sr = datetime.fromisoformat(d["sunrise"][0])
    ss = datetime.fromisoformat(d["sunset"][0])
    h1 = timedelta(hours=1)
    golden = (sr <= now <= sr + h1) or (ss - h1 <= now <= ss)
    nori = cur.get("cloud_cover") or 0
    s = 6 + (2 if golden else 0) + (1 if 20 <= nori <= 70 else 0) - prob * 0.04
    txt = (f"Golden Hour: {sr:%H:%M}–{(sr + h1):%H:%M} și {(ss - h1):%H:%M}–{ss:%H:%M}"
           + (" – ACUM!" if golden else ""))
    rez.append(("📷 Fotografie", _clamp(s), txt))

    # Astronomie: acoperirea cu nori în această seară (21:00–23:00)
    seara = [c for tm, c in zip(h["time"], h["cloud_cover"])
             if c is not None and tm[:10] == cur["time"][:10] and tm[11:13] in ("21", "22", "23")]
    if seara:
        medie = sum(seara) / len(seara)
        s = 10 - medie / 10
        rez.append(("🔭 Astronomie", _clamp(s),
                    f"Nori în seara aceasta: ~{medie:.0f}% – "
                    + ("cer senin, ideal pentru stele!" if medie < 20 else "vizibilitate limitată")))
    else:
        rez.append(("🔭 Astronomie", _clamp(10 - nori / 10), f"Acoperire cu nori acum: {nori}%"))
    return rez


def outfit(data):
    cur, h = data["current"], data["hourly"]
    i = hour_index(data)
    t = cur["apparent_temperature"]
    prob = max(_next(h, "precipitation_probability", i, 12) or [0])
    uv = max(_next(h, "uv_index", i, 12) or [0])
    w = cur["wind_gusts_10m"] or 0
    if t < 0: s = "Geacă groasă de iarnă, căciulă, mănuși și fular"
    elif t < 8: s = "Geacă groasă și pulover"
    elif t < 15: s = "Jachetă sau hanorac"
    elif t < 22: s = "Bluză cu mânecă lungă sau tricou + cardigan"
    elif t < 28: s = "Tricou și haine ușoare"
    else: s = "Haine foarte ușoare și multă apă la îndemână"
    extra = []
    if prob >= 40 or is_rain(cur["weather_code"]):
        extra.append("Ia-ți o jachetă impermeabilă sau o umbrelă ☔")
    if uv >= 6:
        extra.append("Ochelari de soare și cremă cu SPF 30+ 😎")
    elif uv >= 3:
        extra.append("Ochelari de soare 😎")
    if w >= 45:
        extra.append("Alege haine rezistente la vânt 💨")
    if is_snow(cur["weather_code"]):
        extra.append("Încălțăminte impermeabilă cu talpă antiderapantă 🥾")
    return s, extra


# ---------------------------------------------------------------- sănătate
def pollen_level(v):
    if v is None: return "indisponibil"
    if v < 10: return "scăzut"
    if v < 50: return "moderat"
    if v < 200: return "ridicat"
    return "foarte ridicat"


def aqi_info(aqi):
    """Indexul european de calitate a aerului (EAQI)."""
    if aqi is None: return "indisponibil", ""
    if aqi <= 20: return "Foarte bună", "Aerul este curat – poți face orice activitate afară."
    if aqi <= 40: return "Bună", "Calitate bună a aerului, fără restricții."
    if aqi <= 60: return "Moderată", "Persoanele sensibile ar trebui să reducă efortul prelungit afară."
    if aqi <= 80: return "Slabă", "Aerul este poluat, evită activitățile fizice intense afară."
    if aqi <= 100: return "Foarte slabă", "Aer poluat: rămâi în interior, poartă mască dacă ieși."
    return "Extrem de slabă", "Pericol pentru sănătate – evită complet ieșirile."


def pm_level(v, limite):
    if v is None: return "indisponibil"
    for lim, nume in zip(limite, ("bun", "acceptabil", "ridicat")):
        if v < lim: return nume
    return "foarte ridicat"


SKIN_TYPES = {
    "Tip I – foarte deschis (se arde mereu)": 2.5,
    "Tip II – deschis (se arde ușor)": 3.0,
    "Tip III – intermediar": 4.0,
    "Tip IV – măsliniu": 5.0,
    "Tip V – brun": 8.0,
    "Tip VI – foarte închis": 13.0,
}


def uv_advice(uv, factor):
    """Timp aproximativ până la arsuri, fără protecție (minute) – formula empirică
    min = 200 * factor / (3 * UV). Valoare orientativă, nu medicală."""
    if uv is None or uv < 0.5:
        return None, "UV neglijabil – nu e nevoie de protecție."
    minute = 200 * factor / (3 * uv)
    if uv < 3: sfat = "Risc scăzut. Protecție minimă."
    elif uv < 6: sfat = "Risc moderat. Folosește SPF 30 și caută umbră la prânz."
    elif uv < 8: sfat = "Risc ridicat. SPF 30–50, pălărie și ochelari de soare."
    elif uv < 11: sfat = "Risc foarte ridicat. Evită soarele 11–16, SPF 50+."
    else: sfat = "Risc extrem. Rămâi la umbră, acoperă pielea, SPF 50+."
    return minute, sfat


# ---------------------------------------------------------------- aeroporturi
def airport_risk(data):
    """Estimează riscul de întârzieri pe baza vremii din următoarele 3 ore."""
    h, i = data["hourly"], hour_index(data)
    puncte, motive = 0, []
    vis = min(_next(h, "visibility", i, 3) or [10000])
    gust = max(_next(h, "wind_gusts_10m", i, 3) or [0])
    coduri = _next(h, "weather_code", i, 3) or [0]
    if vis < 1000: puncte += 3; motive.append(f"vizibilitate redusă ({vis:.0f} m)")
    elif vis < 5000: puncte += 1; motive.append(f"vizibilitate scăzută ({vis/1000:.1f} km)")
    if gust >= 60: puncte += 3; motive.append(f"rafale {gust:.0f} km/h")
    elif gust >= 45: puncte += 2; motive.append(f"rafale {gust:.0f} km/h")
    elif gust >= 35: puncte += 1; motive.append(f"vânt cu rafale {gust:.0f} km/h")
    if any(is_storm(c) for c in coduri): puncte += 3; motive.append("furtună")
    if any(c in (56, 57, 66, 67) for c in coduri): puncte += 3; motive.append("precipitații înghețate")
    if any(is_snow(c) for c in coduri): puncte += 2; motive.append("ninsoare")
    if any(c in (45, 48) for c in coduri): puncte += 2; motive.append("ceață")
    if any(c in (65, 82) for c in coduri): puncte += 1; motive.append("ploaie puternică")
    if puncte <= 1: nivel = "🟢 Risc scăzut"
    elif puncte <= 3: nivel = "🟡 Risc moderat – posibile întârzieri"
    else: nivel = "🔴 Risc ridicat – întârzieri/anulări probabile"
    return nivel, ", ".join(motive) or "condiții normale de zbor", vis, gust
