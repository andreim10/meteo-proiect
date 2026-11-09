"""Funcții avansate: energie solară, smart home, astronomie, pescuit, agricultură, briefing.
Doar calcule – fără interfață și fără rețea."""

import math
import re
from datetime import date, datetime, timedelta

import logic

SYNODIC = 29.530588853                 # durata unei luni sinodice (zile)
REF_LUNA_NOUA = datetime(2000, 1, 6, 18, 14)


def idx_ora(times, cur_time):
    t = cur_time[:13] + ":00"
    return times.index(t) if t in times else 0


def _intervale(ore_iso):
    """Grupează ore consecutive în intervale: ['08:00–11:00', ...]"""
    if not ore_iso:
        return []
    ore = sorted(datetime.fromisoformat(o) for o in ore_iso)
    grupuri, start, prev = [], ore[0], ore[0]
    for o in ore[1:]:
        if o - prev > timedelta(hours=1):
            grupuri.append((start, prev))
            start = o
        prev = o
    grupuri.append((start, prev))
    return [f"{a:%H:%M}–{(b + timedelta(hours=1)):%H:%M}" for a, b in grupuri]


# ======================================================================= ENERGIE SOLARĂ
def energie_solara(extra, cur_time, kwp, tarif, pr=0.75):
    """Estimare producție fotovoltaică.
    kWh = kWp × (radiația zilnică în kWh/m²) × PR   (PR ≈ 0,75 = pierderi invertor, cabluri, temperatură)"""
    h = extra["hourly"]
    zile = {}
    for t, g in zip(h["time"], h["shortwave_radiation"]):
        if g is not None:
            zile.setdefault(t[:10], []).append((int(t[11:13]), g))
    tabel = []
    for z, ore in zile.items():
        kwh_m2 = sum(g for _, g in ore) / 1000
        tabel.append((z, kwh_m2, kwh_m2 * kwp * pr))
    azi = cur_time[:10]
    ore_azi = [(o, g / 1000 * kwp * pr) for o, g in zile.get(azi, [])]
    soare = [s / 3600 if s is not None else 0 for s in extra["daily"]["sunshine_duration"]]
    prod_azi = next((p for z, _, p in tabel if z == azi), 0)
    return {"tabel": tabel, "ore_azi": ore_azi, "soare": soare,
            "azi": prod_azi, "economie": prod_azi * tarif}


# ======================================================================= SMART HOME
def umiditate_absoluta(t, rh):
    """g/m³ de vapori de apă în aer."""
    return 6.112 * math.exp(17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)


def smart_home(data, t_in, rh_in):
    cur, h, d = data["current"], data["hourly"], data["daily"]
    i = logic.hour_index(data)
    t_out, rh_out = cur["temperature_2m"], cur["relative_humidity_2m"]
    ah_in, ah_out = umiditate_absoluta(t_in, rh_in), umiditate_absoluta(t_out, rh_out)
    sfaturi = []

    if t_in >= 24:
        if t_out <= t_in - 2:
            sfaturi.append(f"🪟 Afară sunt {t_out:.0f}°C, iar în casă {t_in:.0f}°C: deschide geamurile "
                           f"pentru a răcori locuința în loc să pornești aerul condiționat.")
        else:
            sfaturi.append(f"🌞 Afară sunt {t_out:.0f}°C: ține geamurile și jaluzelele închise peste zi. "
                           f"Dacă pornești AC-ul, setează 25–26°C – fiecare grad în plus reduce consumul.")
    elif t_in < 19:
        sfaturi.append("🔥 În casă e răcoare: aerisește scurt (5–10 min, geamuri larg deschise), apoi închide, "
                       "ca să nu pierzi căldura.")
        if cur["is_day"] and (cur.get("cloud_cover") or 0) < 40:
            sfaturi.append("☀️ E senin: deschide perdelele pe partea însorită – soarele încălzește gratuit.")
    else:
        sfaturi.append(f"👍 Temperatura din casă ({t_in:.0f}°C) e confortabilă. Nu e nevoie de încălzire sau AC.")

    if rh_in > 60:
        if ah_out < ah_in - 1.5:
            sfaturi.append("💧 Umiditate mare în casă, iar aerul de afară e mai uscat: aerisește 10 minute.")
        else:
            sfaturi.append("💧 Umiditate mare în casă, dar și afară aerul e umed: folosește un dezumidificator "
                           "sau hota la gătit, nu aerisirea.")
    elif rh_in < 30:
        sfaturi.append("🏜️ Aer prea uscat în casă: evită ventilația prelungită și folosește un umidificator.")

    if d["temperature_2m_max"][1] >= 30:
        sfaturi.append(f"🔥 Mâine se anunță {d['temperature_2m_max'][1]:.0f}°C: aerisește dimineața devreme "
                       f"și închide geamurile și jaluzelele înainte să se încălzească afară.")

    # Ferestre bune pentru ventilație în următoarele 24h
    ore = []
    for k in range(i, min(i + 24, len(h["time"]))):
        to, ro = h["temperature_2m"][k], h["relative_humidity_2m"][k]
        if to is None or ro is None:
            continue
        racire = t_in >= 24 and t_in - 8 <= to <= t_in - 2
        uscare = rh_in > 60 and to >= 5 and umiditate_absoluta(to, ro) < ah_in - 1.5
        incalzire_ok = t_in < 24 and 15 <= to <= 24 and rh_in <= 60 and 8 <= int(h["time"][k][11:13]) <= 20
        if racire or uscare or incalzire_ok:
            ore.append(h["time"][k])
    return sfaturi, _intervale(ore)


# ======================================================================= ASTRONOMIE
def luna(dt):
    """Faza Lunii calculată matematic (fără API). Returnează (nume, iluminare 0-1, vârsta în zile)."""
    varsta = ((dt - REF_LUNA_NOUA).total_seconds() / 86400) % SYNODIC
    ilum = (1 - math.cos(2 * math.pi * varsta / SYNODIC)) / 2
    for lim, nume in [(1.85, "🌑 Lună nouă"), (5.54, "🌒 Semilună crescătoare"), (9.22, "🌓 Primul pătrar"),
                      (12.91, "🌔 Lună gibboasă crescătoare"), (16.61, "🌕 Lună plină"),
                      (20.30, "🌖 Lună gibboasă descrescătoare"), (23.99, "🌗 Ultimul pătrar"),
                      (27.68, "🌘 Semilună descrescătoare")]:
        if varsta < lim:
            return nume, ilum, varsta
    return "🌑 Lună nouă", ilum, varsta


def bortle_estimat(populatie):
    """Poluarea luminoasă (scara Bortle 1=cer perfect ... 9=centru de oraș mare),
    estimată din populația localității. Valoare orientativă – o poți modifica manual."""
    if not populatie: return 4
    if populatie >= 1_000_000: return 8
    if populatie >= 300_000: return 7
    if populatie >= 100_000: return 6
    if populatie >= 30_000: return 5
    if populatie >= 5_000: return 4
    return 3


PLOI_METEORI = [("Quadrantidele", 1, 3, 80), ("Lyridele", 4, 22, 18), ("Eta Aquaridele", 5, 6, 50),
                ("Perseidele", 8, 12, 100), ("Orionidele", 10, 21, 20), ("Leonidele", 11, 17, 15),
                ("Geminidele", 12, 14, 150), ("Ursidele", 12, 22, 10)]


def ploaie_meteori(azi):
    best = None
    for nume, m, z, zhr in PLOI_METEORI:
        for an in (azi.year, azi.year + 1):
            peak = date(an, m, z)
            delta = (peak - azi).days
            if delta >= -3 and (best is None or delta < best[3]):
                best = (nume, peak, zhr, delta)
    nume, peak, zhr, delta = best
    if abs(delta) <= 3:
        return f"☄️ {nume} sunt ACTIVE (maxim {peak:%d.%m}, până la ~{zhr} meteori/oră în condiții ideale)"
    return f"☄️ Următoarea ploaie de meteori: {nume}, maxim pe {peak:%d.%m} (peste {delta} zile, ~{zhr} meteori/oră)"


def cai_lactee(luna_m, ilum, bortle, nori):
    if luna_m in (11, 12, 1, 2):
        return "🌌 Nucleul Căii Lactee nu se vede iarna; brațul de iarnă e slab și greu de observat."
    if luna_m in (3, 10):
        sezon = "nucleul apare doar spre dimineață, jos pe orizont"
    elif luna_m in (6, 7, 8):
        sezon = "sezon excelent, nucleul urcă sus pe cer"
    else:
        sezon = "sezon bun, nucleul se vede seara spre sud"
    if bortle > 4:
        return f"🌌 Calea Lactee: {sezon}, dar poluarea luminoasă (Bortle {bortle}) o ascunde – mergi în afara orașului."
    if ilum > 0.4 or nori > 30:
        return f"🌌 Calea Lactee: {sezon}, dar Luna sau norii o fac greu vizibilă azi."
    return f"🌌 Calea Lactee: {sezon}. Condiții bune în noaptea aceasta!"


def raport_astro(data, populatie, bortle, acum):
    h = data["hourly"]
    azi = data["current"]["time"][:10]
    maine = (datetime.fromisoformat(azi) + timedelta(days=1)).strftime("%Y-%m-%d")
    nori = [c for t, c in zip(h["time"], h["cloud_cover"]) if c is not None and
            ((t[:10] == azi and int(t[11:13]) >= 21) or (t[:10] == maine and int(t[11:13]) <= 3))]
    nori_med = sum(nori) / len(nori) if nori else (data["current"].get("cloud_cover") or 0)
    nume, ilum, varsta = luna(acum)
    cer_profund = 10 - nori_med * 0.08 - ilum * 3 - (bortle - 1) * 0.6
    planete = 10 - nori_med * 0.09 - (bortle - 1) * 0.15
    cl = lambda x: max(0, min(10, round(x)))
    return {"luna": nume, "ilum": ilum, "nori": nori_med, "cer_profund": cl(cer_profund), "planete": cl(planete),
            "calea_lactee": cai_lactee(acum.month, ilum, bortle, nori_med),
            "meteori": ploaie_meteori(acum.date()), "varsta": varsta}


# ======================================================================= PESCUIT
def tendinta_presiune(extra, cur_time):
    h = extra["hourly"]
    i = idx_ora(h["time"], cur_time)
    p = h["surface_pressure"]
    val = lambda k: p[min(i + k, len(p) - 1)]
    p0, d3, d12, d24 = val(0), val(3) - val(0), val(12) - val(0), val(24) - val(0)
    if d3 <= -3: tip = "în scădere RAPIDĂ (se apropie un front de vreme rea)"
    elif d24 <= -2: tip = "în scădere lentă"
    elif d3 >= 3: tip = "în creștere rapidă"
    elif d24 >= 2: tip = "în creștere lentă"
    else: tip = "stabilă"
    if abs(d24) >= 6 or abs(d3) >= 3: migrena = "🔴 ridicat"
    elif abs(d24) >= 3: migrena = "🟡 moderat"
    else: migrena = "🟢 scăzut"
    return {"p0": p0, "d3": d3, "d12": d12, "d24": d24, "tip": tip, "migrena": migrena}


def solunar(data, varsta):
    """Perioade solunare APROXIMATIVE: trecerea Lunii la meridian ≈ amiaza solară + vârsta·0,84 h.
    Majore = ±1h în jurul trecerii (sus/jos), minore = ±30 min la răsărit/apus de Lună."""
    d, cur = data["daily"], data["current"]
    zi0 = datetime.fromisoformat(cur["time"][:10])
    sr, ss = datetime.fromisoformat(d["sunrise"][0]), datetime.fromisoformat(d["sunset"][0])
    amiaza = sr + (ss - sr) / 2
    tranzit = amiaza + timedelta(hours=varsta / SYNODIC * 24.84)
    zi_luna = timedelta(hours=24.84)
    while tranzit < zi0: tranzit += zi_luna
    while tranzit >= zi0 + timedelta(days=1): tranzit -= zi_luna
    jum = timedelta(hours=12.42)
    perioade = []
    for c, tip, w in [(tranzit, "major", 1), (tranzit - jum, "major", 1), (tranzit + jum, "major", 1),
                      (tranzit - jum / 2, "minor", 0.5), (tranzit + jum / 2, "minor", 0.5)]:
        a, b = c - timedelta(hours=w), c + timedelta(hours=w)
        if a.date() == zi0.date() or b.date() == zi0.date():
            perioade.append((a, b, tip))
    return sorted(perioade, key=lambda x: x[0])


def scor_pescuit(data, tendinta, perioade):
    cur = data["current"]
    now = datetime.fromisoformat(cur["time"])
    s = 5
    if tendinta["tip"] == "stabilă": s += 2
    elif "scădere lentă" in tendinta["tip"]: s += 3
    elif "scădere RAPIDĂ" in tendinta["tip"]: s += 1
    elif "creștere lentă" in tendinta["tip"]: s += 1
    else: s -= 2
    w = cur["wind_speed_10m"]
    if w > 25: s -= 2
    elif 5 <= w <= 15: s += 1
    if 40 <= (cur.get("cloud_cover") or 0) <= 80: s += 1
    for a, b, tip in perioade:
        if a <= now <= b:
            s += 2 if tip == "major" else 1
    t = cur["temperature_2m"]
    if t < 0 or t > 32: s -= 1
    return max(0, min(10, s))


# ======================================================================= AGRICULTURĂ
def raport_agri(data, extra, cur_time):
    h, d = extra["hourly"], extra["daily"]
    i = idx_ora(h["time"], cur_time)
    um = h["soil_moisture_3_to_9cm"][i]
    ts = h["soil_temperature_6cm"][i]
    et0 = d["et0_fao_evapotranspiration"][0]
    mh, ii = data["hourly"], logic.hour_index(data)
    ploaie48 = sum(v for v in mh["precipitation"][ii:ii + 48] if v is not None)
    rez = {"um": um, "ts": ts, "et0": et0, "ploaie48": ploaie48, "sfaturi": []}

    if um is None: nivel = "indisponibil"
    elif um < 0.12: nivel = "foarte uscat"
    elif um < 0.20: nivel = "uscat"
    elif um <= 0.35: nivel = "optim"
    else: nivel = "foarte umed"
    rez["nivel"] = nivel

    s = rez["sfaturi"]
    if nivel in ("uscat", "foarte uscat"):
        if ploaie48 < 3:
            s.append(f"💦 Solul e uscat și nu vine ploaie (≈{ploaie48:.1f} mm în 48h): udă plantele, "
                     f"de preferat dimineața devreme sau seara. Pierderea de apă azi ≈ {et0:.1f} mm.")
        else:
            s.append(f"🌧️ Solul e uscat, dar vin ≈{ploaie48:.1f} mm de ploaie în 48h – poți amâna udatul.")
    elif nivel == "foarte umed":
        s.append("🚫 Sol foarte umed: nu uda și evită lucrările pe teren (tasare, risc de boli fungice).")
    elif nivel == "optim":
        s.append("✅ Umiditatea solului e bună – nu e nevoie de udat acum.")

    if ts is not None:
        if ts < 5: s.append(f"🥶 Sol la {ts:.0f}°C: prea rece pentru semănat.")
        elif ts < 10: s.append(f"🌱 Sol la {ts:.0f}°C: doar culturi rezistente (mazăre, spanac, salată).")
        elif ts < 16: s.append(f"🌱 Sol la {ts:.0f}°C: potrivit pentru cartofi, morcovi, ceapă.")
        else: s.append(f"🌽 Sol la {ts:.0f}°C: bun pentru porumb, fasole, castraveți, roșii.")
    if min(data["daily"]["temperature_2m_min"][:3]) <= 0:
        s.append("❄️ Risc de îngheț în următoarele 3 zile: protejează plantele sensibile.")
    return rez


# ======================================================================= BRIEFING VOCAL
def curata_pt_voce(text):
    text = re.sub(r"[\U0001F000-\U0001FFFF\u2190-\u27BF\uFE0F•]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def briefing(data, city_name):
    cur, h, d = data["current"], data["hourly"], data["daily"]
    i = logic.hour_index(data)
    azi = cur["time"][:10]
    desc = logic.WMO.get(cur["weather_code"], "").lower()
    p = [f"Bună dimineața! În {city_name} sunt acum {cur['temperature_2m']:.0f} grade, {desc}.",
         f"Maxima de astăzi va fi de {d['temperature_2m_max'][0]:.0f} grade, iar minima de "
         f"{d['temperature_2m_min'][0]:.0f} grade."]
    ploaie = [t for t, pr in zip(h["time"][i:i + 24], h["precipitation_probability"][i:i + 24])
              if t[:10] == azi and (pr or 0) >= 50]
    if ploaie:
        p.append(f"Atenție, la ora {int(ploaie[0][11:13])} sunt șanse mari de ploaie.")
    else:
        p.append("Nu sunt șanse mari de ploaie astăzi.")
    haine, extra = logic.outfit(data)
    p.append("Îți recomand: " + haine.lower() + ". " + " ".join(x.rstrip(".") + "." for x in extra))
    av = [a for a in logic.warnings(data) if not a.startswith("✅")]
    if av:
        p.append("Avertizări: " + ". ".join(av) + ".")
    p.append("Zi frumoasă!")
    return curata_pt_voce(" ".join(p))
