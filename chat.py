"""Asistent meteo conversațional LOCAL (fără internet și fără AI extern).
Funcționează pe reguli: detectează perioada (diseară, mâine, weekend...) și intenția
(ploaie, alergat, rufe, temperatură...) din întrebare, apoi răspunde din datele API."""

import re
import unicodedata
from datetime import datetime, timedelta

import logic

ZILE_RO = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
ZILE_N = ["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _are(q, *cuvinte):
    return any(c in q for c in cuvinte)


# --------------------------------------------------------------- perioada din întrebare
def interval(q, now):
    azi = now.replace(hour=0, minute=0, second=0, microsecond=0)
    zi, eticheta = azi, "azi"
    if "poimaine" in q:
        zi, eticheta = azi + timedelta(days=2), "poimâine"
    elif "maine" in q:
        zi, eticheta = azi + timedelta(days=1), "mâine"
    else:
        for k, nm in enumerate(ZILE_N):
            if re.search(r"\b" + nm + r"\b", q):
                zi = azi + timedelta(days=(k - now.weekday()) % 7)
                eticheta = ZILE_RO[k] if zi != azi else "azi"
                break

    if _are(q, "weekend", "sfarsit de saptamana"):
        zile_pana = (5 - now.weekday()) % 7
        if now.weekday() == 6:
            start, end = azi, azi + timedelta(days=1)
        else:
            start = azi + timedelta(days=zile_pana)
            end = start + timedelta(days=2)
        eticheta = "în weekend"
    elif _are(q, "saptamana", "saptamani", "urmatoarele zile", "zilele urmatoare", "urmatoarele 7"):
        start, end, eticheta = now, now + timedelta(days=7), "în următoarele 7 zile"
    elif "diseara" in q:
        start, end, eticheta = azi + timedelta(hours=18), azi + timedelta(hours=24), "diseară"
    elif "dimineata" in q:
        start, end = zi + timedelta(hours=6), zi + timedelta(hours=12)
        eticheta += " dimineață"
    elif _are(q, "dupa amiaza", "dupa-amiaza", "amiaza"):
        start, end = zi + timedelta(hours=12), zi + timedelta(hours=18)
        eticheta += " după-amiază"
    elif "seara" in q:
        start, end = zi + timedelta(hours=18), zi + timedelta(hours=24)
        eticheta += " seara"
    elif "noapte" in q:
        start, end = zi + timedelta(hours=21), zi + timedelta(hours=24)
        eticheta += " noaptea"
    elif zi != azi:
        start, end = zi, zi + timedelta(days=1)
    elif "acum" in q:
        start, end, eticheta = now, now + timedelta(hours=3), "în următoarele 3 ore"
    else:
        start, end = now, azi + timedelta(days=1)
    return max(start, now.replace(minute=0)), end, eticheta


def _indici(data, start, end):
    t = data["hourly"]["time"]
    return [k for k, x in enumerate(t) if start <= datetime.fromisoformat(x) < end]


def _ore(h, ks):
    """'18:00–21:00' pentru indici consecutivi."""
    if not ks:
        return ""
    a = datetime.fromisoformat(h["time"][ks[0]])
    b = datetime.fromisoformat(h["time"][ks[-1]]) + timedelta(hours=1)
    if b - a >= timedelta(hours=23):
        return "pe tot parcursul zilei"
    return f"{a:%H:%M}–{b:%H:%M}"


def _ziua(dt, now):
    d = (dt.date() - now.date()).days
    return {0: "azi", 1: "mâine", 2: "poimâine"}.get(d, f"{ZILE_RO[dt.weekday()]} {dt:%d.%m}")


def _v(lista, k, impl=0):
    x = lista[k]
    return impl if x is None else x


# --------------------------------------------------------------- răspunsuri
def _ploaie(data, ks, eticheta, zapada=False):
    h = data["hourly"]
    prob = [_v(h["precipitation_probability"], k) for k in ks]
    mm = [_v(h["precipitation"], k) for k in ks]
    ud = [k for k, p, m in zip(ks, prob, mm) if p >= 40 or m >= 0.2]
    sub = "ninsoare" if zapada else "ploaie"
    if not ud:
        return f"☀️ {eticheta.capitalize()} nu pare să fie {sub} (șanse maxime {max(prob):.0f}%)."
    return (f"🌧️ Da, {eticheta} sunt șanse de {sub}, în special {_ore(h, ud)} "
            f"(probabilitate maximă {max(prob):.0f}%, în jur de {sum(mm):.1f} mm în total).")


def _alergat(data, ks, eticheta, air, activ):
    h = data["hourly"]
    prob = [_v(h["precipitation_probability"], k) for k in ks]
    temp = [_v(h["apparent_temperature"], k) for k in ks]
    gust = [_v(h["wind_gusts_10m"], k) for k in ks]
    aqi = (air or {}).get("european_aqi") or 0
    mediu_t = sum(temp) / len(temp)
    r = [_ploaie(data, ks, eticheta)]
    probleme = []
    if max(prob) >= 50: probleme.append("risc mare de ploaie")
    if mediu_t < -3: probleme.append("e foarte frig")
    if mediu_t > 30: probleme.append("e prea cald")
    if max(gust) > 45: probleme.append("rafale puternice")
    if aqi > 80: probleme.append("aerul e poluat")
    if probleme:
        r.append(f"Pentru {activ} nu e ideal ({', '.join(probleme)}).")
    else:
        r.append(f"Pentru {activ} arată bine: ~{mediu_t:.0f}°C resimțit, rafale până la {max(gust):.0f} km/h.")
    best = min(ks, key=lambda k: _v(h["precipitation_probability"], k) + abs(_v(h["apparent_temperature"], k) - 14))
    r.append(f"Cel mai bun moment din interval: {h['time'][best][11:16]} "
             f"({_v(h['apparent_temperature'], best):.0f}°C, ploaie {_v(h['precipitation_probability'], best):.0f}%).")
    return " ".join(r)


def _rufe(data, ks, eticheta):
    h = data["hourly"]
    now = datetime.fromisoformat(data["current"]["time"])

    def scor(k):
        p, hu = _v(h["precipitation_probability"], k), _v(h["relative_humidity_2m"], k, 70)
        w, t = _v(h["wind_speed_10m"], k), _v(h["temperature_2m"], k)
        return 100 - p * 1.2 - max(0, hu - 40) * 0.8 + min(w, 15) * 1.5 + min(max(t, 0), 25) * 0.5

    zi_ok = [k for k in ks if 8 <= int(h["time"][k][11:13]) <= 18]
    ferestre = []
    for k in zi_ok:
        grup = [k, k + 1, k + 2]
        if all(g in zi_ok for g in grup):
            ferestre.append((sum(scor(g) for g in grup) / 3, grup))
    if not ferestre:
        return "Nu am suficiente ore de zi în acel interval. Încearcă „mâine” sau „săptămâna asta”."
    ferestre.sort(key=lambda x: -x[0])
    sc, g = ferestre[0]
    k = g[0]
    dt = datetime.fromisoformat(h["time"][k])
    p = max(_v(h["precipitation_probability"], x) for x in g)
    hu = sum(_v(h["relative_humidity_2m"], x) for x in g) / 3
    w = sum(_v(h["wind_speed_10m"], x) for x in g) / 3
    r = (f"👕 Cel mai bun moment {eticheta}: {_ziua(dt, now)}, {_ore(h, g)} "
         f"(ploaie max {p:.0f}%, umiditate ~{hu:.0f}%, vânt ~{w:.0f} km/h).")
    if p >= 40 or hu > 85:
        r += " Atenție: nici cel mai bun interval nu e perfect – rufele se vor usca greu."
    alt = next(((s2, g2) for s2, g2 in ferestre[1:]
                if datetime.fromisoformat(h["time"][g2[0]]).date() != dt.date()), None)
    if alt:
        dt2 = datetime.fromisoformat(h["time"][alt[1][0]])
        r += f" Alternativ: {_ziua(dt2, now)}, {_ore(h, alt[1])}."
    return r


def _temperatura(data, ks, eticheta):
    h = data["hourly"]
    t = [_v(h["temperature_2m"], k) for k in ks]
    ap = [_v(h["apparent_temperature"], k) for k in ks]
    return (f"🌡️ {eticheta.capitalize()}: între {min(t):.0f}°C și {max(t):.0f}°C "
            f"(resimțit {min(ap):.0f}…{max(ap):.0f}°C).")


def _vant(data, ks, eticheta):
    h = data["hourly"]
    w = [_v(h["wind_speed_10m"], k) for k in ks]
    g = [_v(h["wind_gusts_10m"], k) for k in ks]
    cuv = "puternic" if max(g) >= 60 else "moderat" if max(g) >= 35 else "slab"
    return f"💨 {eticheta.capitalize()}: vânt {cuv}, în medie {sum(w) / len(w):.0f} km/h, rafale până la {max(g):.0f} km/h."


def _uv(data, ks, eticheta):
    h = data["hourly"]
    uv = [_v(h["uv_index"], k) for k in ks]
    m = max(uv)
    sfat = ("fără probleme" if m < 3 else "folosește SPF 30" if m < 6
            else "SPF 30–50, pălărie și ochelari" if m < 8 else "evită soarele la prânz, SPF 50+")
    return f"☀️ Index UV maxim {eticheta}: {m:.1f} – {sfat}."


def _rezumat(data):
    cur, d = data["current"], data["daily"]
    return (f"{logic.weather_text(cur['weather_code'])}, {cur['temperature_2m']:.0f}°C "
            f"(se simte {cur['apparent_temperature']:.0f}°C). Azi: {d['temperature_2m_min'][0]:.0f}°…"
            f"{d['temperature_2m_max'][0]:.0f}°C, șanse de precipitații {d['precipitation_probability_max'][0]}%.")


AJUTOR = ("Pot răspunde la întrebări precum:\n"
          "• O să plouă diseară când ies la alergat?\n"
          "• La ce oră e cel mai bun moment să pun rufele la uscat săptămâna asta?\n"
          "• Ce temperatură e mâine dimineață?\n"
          "• Bate vântul în weekend?  •  Ce index UV e azi?  •  Ce să îmbrac?  •  Merită să spăl mașina?")


def raspunde(intrebare, data, air=None):
    q = norm(intrebare)
    if not q.strip():
        return AJUTOR
    if _are(q, "ajutor", "ce poti", "ce stii", "cum functionezi"):
        return AJUTOR
    if re.fullmatch(r"(salut|buna|hei|hello|servus)\W*", q.strip()):
        return "Salut! 👋 Întreabă-mă orice despre vreme. Ex: „O să plouă diseară?”"

    now = datetime.fromisoformat(data["current"]["time"])
    start, end, eticheta = interval(q, now)
    ks = _indici(data, start, end)

    # întrebări fără interval de timp
    if _are(q, "masina", "spal auto", "spalatorie"):
        v, det = logic.car_wash(data)
        return f"🚗 {v}. {det}"
    if _are(q, "imbrac", "jacheta", "ce port", "haine", "umbrela", "pulover", "outfit") and not _are(q, "ploua", "ploaie"):
        s, extra = logic.outfit(data)
        return "👕 " + s + ". " + " ".join(extra)
    if _are(q, "polen", "alergi"):
        a = air or {}
        vals = {"mesteacăn": a.get("birch_pollen"), "iarbă": a.get("grass_pollen"), "ambrozie": a.get("ragweed_pollen")}
        if all(v is None for v in vals.values()):
            return "Nu am date despre polen pentru această zonă (sunt disponibile doar pentru Europa)."
        return "🌼 Polen acum: " + ", ".join(f"{n} {logic.pollen_level(v)}" for n, v in vals.items() if v is not None) + "."
    if _are(q, "poluare", "calitatea aerului", "aqi", "praf") :
        niv, sfat = logic.aqi_info((air or {}).get("european_aqi"))
        return f"🌫️ Calitatea aerului: {niv}. {sfat}"

    if not ks:
        return "Nu am date pentru acel interval (e în trecut sau prea departe). Încearcă „azi”, „mâine” sau „săptămâna asta”."

    if _are(q, "rufe", "uscat", "intins", "haine la uscat"):
        # pentru rufe, intervalul implicit „azi” e prea scurt: căutăm în toată săptămâna
        if eticheta == "azi" and "azi" not in q:
            ks = _indici(data, now, now + timedelta(days=7))
            eticheta = "în următoarele 7 zile"
        return _rufe(data, ks, eticheta)
    if _are(q, "alerg", "jogging", "alergare", "bicicl", "plimb", "sport", "antrenament", "ies afara", "ies la"):
        activ = "alergat" if _are(q, "alerg", "jogging") else "bicicletă" if "bicicl" in q else "activități afară"
        return _alergat(data, ks, eticheta, air, activ)
    if _are(q, "ninge", "ninsoare", "zapada", "lapovita"):
        return _ploaie(data, ks, eticheta, zapada=True)
    if _are(q, "ploua", "ploaie", "ploi", "precipit", "umbrela", "burnita", "averse", "furtuna"):
        return _ploaie(data, ks, eticheta)
    if _are(q, "vant", "rafale", "bate"):
        return _vant(data, ks, eticheta)
    if _are(q, " uv", "uv ", "bronz", "crema solara", "arsuri") or q.strip() == "uv":
        return _uv(data, ks, eticheta)
    if _are(q, "temperatur", "grade", "cald", "frig", "racoare", "canicula", "ger "):
        return _temperatura(data, ks, eticheta)
    if _are(q, "cer senin", "nori", "stele", "soare", "senin"):
        nori = [_v(data["hourly"]["cloud_cover"], k) for k in ks]
        return f"☁️ {eticheta.capitalize()}: acoperire medie cu nori ~{sum(nori) / len(nori):.0f}%."
    return "Acum: " + _rezumat(data) + "\n\nNu am înțeles exact întrebarea. " + AJUTOR
