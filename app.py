"""
Aplicație meteo – interfață grafică (Tkinter)
Rulare:  python app.py
Cerințe: pip install requests tkintermapview
"""

import json
import math
import os
import queue
import random
import threading
import tkinter as tk
from datetime import date, datetime, timedelta, timezone
from tkinter import messagebox, ttk

import requests

import api
import extras
import logic
import sound
import voice
from tabs_extra import ExtraTabs
from ui import tabel, umple

try:
    import tkintermapview
except ImportError:
    tkintermapview = None

ZILE = ["Lun", "Mar", "Mie", "Joi", "Vin", "Sâm", "Dum"]
ORAS_IMPLICIT = "Satu Mare"


SETARI = os.path.join(os.path.expanduser("~"), ".meteo_proiect.json")


class App(ExtraTabs, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Meteo – proiect Python")
        self.geometry("1100x780")
        self.minsize(900, 700)

        self.q = queue.Queue()          # rezultatele thread-urilor ajung aici
        self.city = self.data = self.air = self.extra = None
        self.setari = self._citeste_setari()
        self.tema = logic.theme(0, 1)
        self.sunet_pornit = False
        self.particule = [[random.random(), random.random() * 170,
                           random.uniform(12, 22), random.uniform(8, 16)] for _ in range(90)]

        self._bara_sus()
        self._banner()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self._tab_acasa()
        self._tab_comparare()
        self._tab_aeroporturi()
        self._tab_casa()
        self._tab_sanatate()
        self._tab_radar()
        self._tab_traseu()
        self._tab_clima()
        self._tab_chat()
        self._tab_energie()
        self._tab_astro()
        self._tab_pescuit()
        self._tab_hazard()

        self.protocol("WM_DELETE_WINDOW", self._inchide)
        self.after(100, self._poll)
        self.after(40, self._animatie)
        self.cauta_oras(ORAS_IMPLICIT)

    # ================================================================ infrastructură
    def ruleaza(self, functie, la_succes):
        """Rulează 'functie' într-un thread; rezultatul e livrat în firul principal."""
        def lucru():
            try:
                self.q.put((la_succes, functie()))
            except Exception as e:                      # noqa: BLE001
                self.q.put((self._eroare, e))
        threading.Thread(target=lucru, daemon=True).start()

    def _poll(self):
        try:
            while True:
                cb, arg = self.q.get_nowait()
                cb(arg)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _eroare(self, e):
        self.stare.config(text="")
        if isinstance(e, requests.exceptions.RequestException):
            msg = "Eroare de rețea. Verifică conexiunea la internet."
        else:
            msg = str(e)
        messagebox.showerror("Eroare", msg)

    def _inchide(self):
        sound.opreste()
        self.destroy()

    # ================================================================ bara de sus + banner
    def _bara_sus(self):
        f = ttk.Frame(self)
        f.pack(fill="x", padx=8, pady=6)
        ttk.Label(f, text="Oraș central:").pack(side="left")
        self.e_oras = ttk.Entry(f, width=28)
        self.e_oras.insert(0, ORAS_IMPLICIT)
        self.e_oras.pack(side="left", padx=6)
        self.sug_places, self._sug_job = [], None
        self.e_oras.bind("<Return>", self._enter_oras)
        self.e_oras.bind("<KeyRelease>", self._tasta_oras)
        self.e_oras.bind("<Down>", self._spre_lista)
        self.e_oras.bind("<Escape>", lambda e: self.lb.place_forget())
        self.lb = tk.Listbox(self, height=7, activestyle="dotbox", font=("Segoe UI", 10))
        self.lb.bind("<Return>", self._alege_sugestie)
        self.lb.bind("<ButtonRelease-1>", self._alege_sugestie)
        self.lb.bind("<Escape>", lambda e: (self.lb.place_forget(), self.e_oras.focus_set()))
        ttk.Button(f, text="Caută", command=lambda: self.cauta_oras(self.e_oras.get())).pack(side="left")
        self.stare = ttk.Label(f, text="")
        self.stare.pack(side="left", padx=12)
        ttk.Button(f, text="🗣️ Briefing vocal", command=self._briefing).pack(side="right", padx=4)
        self.v_auto = tk.BooleanVar(value=self.setari.get("briefing_auto", False))
        ttk.Checkbutton(f, text="Automat dimineața", variable=self.v_auto,
                        command=self._salveaza_setari).pack(side="right")
        self.v_sunet = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="🔊 Sunet de ploaie", variable=self.v_sunet,
                        command=self._comuta_sunet).pack(side="right")

    def _banner(self):
        c = self.banner = tk.Canvas(self, height=170, highlightthickness=0, bg="#4aa3e8")
        c.pack(fill="x", padx=8)
        self.t_oras = c.create_text(20, 28, anchor="w", font=("Segoe UI", 18, "bold"), text="", tags="txt")
        self.t_temp = c.create_text(20, 85, anchor="w", font=("Segoe UI", 44, "bold"), text="", tags="txt")
        self.t_desc = c.create_text(20, 140, anchor="w", font=("Segoe UI", 14), text="", tags="txt")
        self.t_det = c.create_text(900, 85, anchor="e", font=("Segoe UI", 12), text="", tags="txt", justify="right")
        c.bind("<Configure>", lambda e: c.coords(self.t_det, e.width - 20, 85))

    # ---- autocomplete pentru oraș (scrii, apar sugestii; ↓ intri în listă, Enter alegi)
    def _tasta_oras(self, e):
        if e.keysym in ("Return", "Down", "Up", "Escape", "Tab", "Left", "Right", "Shift_L", "Shift_R"):
            return
        text = self.e_oras.get().strip()
        if self._sug_job:
            self.after_cancel(self._sug_job)
        if len(text) < 2:
            self.lb.place_forget()
            return

        def lucru():
            try:
                return api.suggest(text)
            except Exception:           # fără erori pop-up la fiecare tastă
                return []
        self._sug_job = self.after(300, lambda: self.ruleaza(lucru, self._arata_sugestii))

    def _arata_sugestii(self, places):
        self.sug_places = places
        self.lb.delete(0, "end")
        if not places or not self.e_oras.get().strip():
            self.lb.place_forget()
            return
        for p in places:
            self.lb.insert("end", ", ".join(x for x in (p["name"], p["admin1"], p["country"]) if x))
        x = self.e_oras.winfo_rootx() - self.winfo_rootx()
        y = self.e_oras.winfo_rooty() - self.winfo_rooty() + self.e_oras.winfo_height()
        self.lb.place(x=x, y=y, width=self.e_oras.winfo_width() + 120)
        self.lb.lift()

    def _spre_lista(self, e=None):
        if self.sug_places and self.lb.winfo_ismapped():
            self.lb.focus_set()
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(0)
            self.lb.activate(0)
            return "break"

    def _alege_sugestie(self, e=None):
        sel = self.lb.curselection()
        if not self.sug_places:
            return
        place = self.sug_places[sel[0] if sel else 0]
        self.lb.place_forget()
        self.e_oras.delete(0, "end")
        self.e_oras.insert(0, place["name"])
        self.e_oras.focus_set()
        self.cauta_oras(place["name"], place)

    def _enter_oras(self, e=None):
        if self.sug_places and self.lb.winfo_ismapped():
            self._alege_sugestie()
        else:
            self.cauta_oras(self.e_oras.get())

    def _comuta_sunet(self):
        if self.v_sunet.get():
            if not sound.porneste():
                self.v_sunet.set(False)
                messagebox.showinfo("Sunet", "Pe acest sistem instalează pygame:  pip install pygame")
        else:
            sound.opreste()

    def _animatie(self):
        c = self.banner
        c.delete("fx")
        kind = self.tema["kind"]
        W, H = max(c.winfo_width(), 300), max(c.winfo_height(), 100)
        if kind in ("rain", "storm"):
            for p in self.particule:
                p[1] += p[2]
                if p[1] > H:
                    p[0], p[1] = random.random(), -10
                x = p[0] * W
                c.create_line(x, p[1], x - 3, p[1] + p[3], fill="#c4dbf2", tags="fx")
            if kind == "storm" and random.random() < 0.02:
                c.create_rectangle(0, 0, W, H, fill="#e8eefc", stipple="gray25", outline="", tags="fx")
        elif kind == "snow":
            for p in self.particule:
                p[1] += p[2] * 0.25
                if p[1] > H:
                    p[0], p[1] = random.random(), -5
                x = p[0] * W + math.sin(p[1] / 18 + p[0] * 10) * 8
                r = p[3] / 5
                c.create_oval(x, p[1], x + r, p[1] + r, fill="white", outline="", tags="fx")
        c.tag_raise("txt")
        self.after(40, self._animatie)

    # ================================================================ căutare oraș principal
    def cauta_oras(self, nume, place=None):
        nume = nume.strip()
        if not nume:
            return
        self.stare.config(text="Se încarcă...")

        def lucru():
            city = place or api.geocode(nume)
            data = api.forecast(city["lat"], city["lon"])
            try:
                air = api.air_quality(city["lat"], city["lon"])
            except Exception:           # calitatea aerului nu e vitală
                air = None
            try:
                extra = api.forecast_extra(city["lat"], city["lon"])
            except Exception:           # date suplimentare (solar, sol, presiune)
                extra = None
            return city, data, air, extra
        self.ruleaza(lucru, self._la_oras)

    def _la_oras(self, rez):
        self.city, self.data, self.air, self.extra = rez
        self.stare.config(text=f"Actualizat la {datetime.now():%H:%M}")
        self._actualizeaza_banner()
        self._actualizeaza_acasa()
        self._actualizeaza_casa()
        self._actualizeaza_sanatate()
        self._seteaza_bortle_din_oras()
        self._actualizeaza_energie()
        self._actualizeaza_smart()
        self._actualizeaza_astro()
        self._actualizeaza_pescuit()
        self._actualizeaza_hazard()
        self._briefing_automat()
        if self.map_widget:
            self.map_widget.set_position(self.city["lat"], self.city["lon"])
            self.map_widget.set_zoom(7)

    def _actualizeaza_banner(self):
        cur = self.data["current"]
        self.tema = logic.theme(cur["weather_code"], cur["is_day"])
        t, c = self.tema, self.banner
        c.config(bg=t["bg"])
        for item in (self.t_oras, self.t_temp, self.t_desc, self.t_det):
            c.itemconfig(item, fill=t["fg"])
        c.itemconfig(self.t_oras, text=f"{self.city['name']}, {self.city['country']}")
        c.itemconfig(self.t_temp, text=f"{cur['temperature_2m']:.0f}°C")
        c.itemconfig(self.t_desc, text=logic.weather_text(cur["weather_code"]))
        c.itemconfig(self.t_det, text=(
            f"Se simte ca {cur['apparent_temperature']:.0f}°C\n"
            f"Umiditate {cur['relative_humidity_2m']}%\n"
            f"Vânt {cur['wind_speed_10m']:.0f} km/h"))

    # ================================================================ briefing vocal & setări
    def _citeste_setari(self):
        try:
            with open(SETARI, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _salveaza_setari(self):
        self.setari["briefing_auto"] = self.v_auto.get()
        try:
            with open(SETARI, "w", encoding="utf-8") as f:
                json.dump(self.setari, f)
        except OSError:
            pass

    def _briefing(self):
        """Citește cu voce tare rezumatul zilei (pyttsx3)."""
        if not self.data:
            return
        text = extras.briefing(self.data, self.city["name"])
        if not voice.spune(text):
            messagebox.showinfo("Briefing (pyttsx3 nu e instalat: pip install pyttsx3)", text)

    def _briefing_automat(self):
        """La prima deschidere de dimineață (05:00–11:59) a zilei, citește briefingul."""
        acum = datetime.now()
        azi = acum.strftime("%Y-%m-%d")
        if self.v_auto.get() and 5 <= acum.hour < 12 and self.setari.get("ultimul_briefing") != azi:
            self.setari["ultimul_briefing"] = azi
            self._salveaza_setari()
            self._briefing()

    # ================================================================ TAB: Acasă
    def _tab_acasa(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🏠 Acasă")
        self.l_avert = ttk.Label(f, text="", wraplength=940, foreground="#b03a2e", font=("Segoe UI", 10, "bold"))
        self.l_avert.pack(anchor="w", padx=8, pady=(8, 2))
        self.l_detalii = ttk.Label(f, text="", font=("Segoe UI", 10))
        self.l_detalii.pack(anchor="w", padx=8)

        ttk.Label(f, text="Estimări pe ore – următoarele 24h (linie = temperatură, bare = șanse de precipitații)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(10, 0))
        self.grafic = tk.Canvas(f, height=190, bg="white", highlightthickness=1, highlightbackground="#ccc")
        self.grafic.pack(fill="x", padx=8, pady=4)

        ttk.Label(f, text="Prognoză 10 zile", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8)
        self.t_zile = tabel(f, [("zi", "Zi", 80), ("vreme", "Vreme", 170), ("min", "Min", 60), ("max", "Max", 60),
                                ("res", "Resimțită", 100), ("prec", "Precip. (mm)", 90),
                                ("prob", "Șanse %", 70), ("uv", "UV max", 60)], inaltime=10)
        self.t_zile.pack(fill="both", expand=True, padx=8, pady=4)

    def _actualizeaza_acasa(self):
        data, cur = self.data, self.data["current"]
        self.l_avert.config(text="\n".join(logic.warnings(data)))
        h, i = data["hourly"], logic.hour_index(data)
        self.l_detalii.config(text=(
            f"Temperatură resimțită: {cur['apparent_temperature']:.1f}°C   |   Umiditate: {cur['relative_humidity_2m']}%   |   "
            f"Precipitații acum: {cur['precipitation']} mm   |   Rafale: {cur['wind_gusts_10m']:.0f} km/h   |   "
            f"Presiune: {cur['surface_pressure']:.0f} hPa"))
        self._deseneaza_grafic(h, i)
        d = data["daily"]
        rand = []
        for k, zi in enumerate(d["time"]):
            dt = datetime.strptime(zi, "%Y-%m-%d")
            rand.append((f"{ZILE[dt.weekday()]} {dt:%d.%m}", logic.weather_text(d["weather_code"][k]),
                         f"{d['temperature_2m_min'][k]:.0f}°", f"{d['temperature_2m_max'][k]:.0f}°",
                         f"{d['apparent_temperature_min'][k]:.0f}° / {d['apparent_temperature_max'][k]:.0f}°",
                         d["precipitation_sum"][k], d["precipitation_probability_max"][k],
                         d["uv_index_max"][k]))
        umple(self.t_zile, rand)

    def _deseneaza_grafic(self, h, i):
        c = self.grafic
        c.delete("all")
        c.update_idletasks()
        W, H = max(c.winfo_width(), 600), 190
        ore = h["time"][i:i + 24]
        temp = h["temperature_2m"][i:i + 24]
        prob = h["precipitation_probability"][i:i + 24]
        if not ore:
            return
        st, dr, sus, jos = 40, W - 20, 30, H - 40
        tmin, tmax = min(temp) - 1, max(temp) + 1
        dx = (dr - st) / (len(ore) - 1)
        pts = []
        for k, (tm, tp, pr) in enumerate(zip(ore, temp, prob)):
            x = st + k * dx
            y = jos - (tp - tmin) / (tmax - tmin) * (jos - sus)
            pts.append((x, y))
            if pr:                                        # bara de precipitații
                c.create_rectangle(x - 5, jos - pr / 100 * 40, x + 5, jos, fill="#9fc5f0", outline="")
            if k % 3 == 0:
                c.create_text(x, H - 22, text=tm[11:16], font=("Segoe UI", 8))
                c.create_text(x, y - 12, text=f"{tp:.0f}°", font=("Segoe UI", 9, "bold"), fill="#c0392b")
        for a, b in zip(pts, pts[1:]):
            c.create_line(*a, *b, fill="#e74c3c", width=2)
        for x, y in pts:
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#e74c3c", outline="")

    # ================================================================ TAB: Comparare orașe
    def _tab_comparare(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="⚖️ Comparare")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=8, pady=8)
        ttk.Label(r, text="Orașe de comparat (separate prin virgulă):").pack(side="left")
        self.e_comp = ttk.Entry(r, width=45)
        self.e_comp.insert(0, "București, Cluj-Napoca, Viena, Londra")
        self.e_comp.pack(side="left", padx=6)
        ttk.Button(r, text="Compară", command=self._compara).pack(side="left")
        self.t_comp = tabel(f, [("oras", "Oraș", 160), ("vreme", "Vreme", 170), ("t", "Temp.", 70),
                                ("res", "Resimțită", 80), ("um", "Umiditate", 80),
                                ("vant", "Vânt km/h", 80), ("prec", "Precip. mm", 80)], inaltime=12)
        self.t_comp.pack(fill="both", expand=True, padx=8)

    def _compara(self):
        nume = [n.strip() for n in self.e_comp.get().split(",") if n.strip()][:8]
        if self.city:
            nume.insert(0, self.city["name"])
        self.stare.config(text="Se compară...")

        def lucru():
            randuri = []
            for n in nume:
                try:
                    c = api.geocode(n)
                    cur = api.forecast(c["lat"], c["lon"], days=1)["current"]
                    randuri.append((c["name"], logic.weather_text(cur["weather_code"]),
                                    f"{cur['temperature_2m']:.0f}°C", f"{cur['apparent_temperature']:.0f}°C",
                                    f"{cur['relative_humidity_2m']}%", f"{cur['wind_speed_10m']:.0f}",
                                    cur["precipitation"]))
                except ValueError:
                    randuri.append((n, "negăsit", "", "", "", "", ""))
            return randuri
        self.ruleaza(lucru, lambda r: (umple(self.t_comp, r), self.stare.config(text="")))

    # ================================================================ TAB: Aeroporturi
    def _tab_aeroporturi(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="✈️ Aeroporturi")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=8, pady=8)
        ttk.Label(r, text="Aeroport:").pack(side="left")
        self.cb_aero = ttk.Combobox(r, state="readonly", width=40,
                                    values=[f"{k} – {v[0]}" for k, v in api.AIRPORTS.items()])
        self.cb_aero.current(0)
        self.cb_aero.pack(side="left", padx=6)
        ttk.Button(r, text="Verifică", command=lambda: self._aeroporturi(False)).pack(side="left")
        ttk.Button(r, text="Toate aeroporturile", command=lambda: self._aeroporturi(True)).pack(side="left", padx=6)
        self.t_aero = tabel(f, [("cod", "Cod", 50), ("nume", "Aeroport", 190), ("vreme", "Vreme", 140),
                                ("vant", "Rafale", 70), ("vis", "Vizib.", 70),
                                ("risc", "Risc întârzieri", 250), ("motiv", "Motiv", 180)], inaltime=14)
        self.t_aero.pack(fill="both", expand=True, padx=8)
        ttk.Label(f, text="Estimarea riscului e orientativă: se bazează doar pe vizibilitate, vânt și fenomene "
                          "meteo din următoarele 3 ore (nu pe datele reale ale companiilor aeriene).",
                  wraplength=900, foreground="#666").pack(anchor="w", padx=8, pady=6)

    def _aeroporturi(self, toate):
        coduri = list(api.AIRPORTS) if toate else [self.cb_aero.get().split(" – ")[0]]
        self.stare.config(text="Se verifică aeroporturile...")

        def lucru():
            rez = []
            for cod in coduri:
                nume, lat, lon = api.AIRPORTS[cod]
                d = api.forecast(lat, lon, days=2)
                nivel, motiv, vis, gust = logic.airport_risk(d)
                cur = d["current"]
                rez.append((cod, nume, logic.weather_text(cur["weather_code"]), f"{gust:.0f} km/h",
                            f"{vis / 1000:.1f} km", nivel, motiv))
            return rez
        self.ruleaza(lucru, lambda r: (umple(self.t_aero, r), self.stare.config(text="")))

    # ================================================================ TAB: Casă & activități
    def _tab_casa(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🧺 Casă & Activități")
        self.l_auto = ttk.Label(f, font=("Segoe UI", 11), wraplength=940)
        self.l_rufe = ttk.Label(f, font=("Segoe UI", 11), wraplength=940)
        self.l_auto.pack(anchor="w", padx=10, pady=(12, 2))
        self.l_rufe.pack(anchor="w", padx=10, pady=2)
        ttk.Label(f, text="Outfit Planner", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(14, 2))
        self.l_outfit = ttk.Label(f, font=("Segoe UI", 11), wraplength=940, justify="left")
        self.l_outfit.pack(anchor="w", padx=10)
        ttk.Label(f, text="Index de activități (0–10)", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(14, 2))
        self.t_act = tabel(f, [("act", "Activitate", 140), ("scor", "Scor", 60), ("com", "Detalii", 700)], inaltime=6)
        self.t_act.column("com", anchor="w")
        self.t_act.pack(fill="x", padx=10)

    def _actualizeaza_casa(self):
        v, d = logic.car_wash(self.data)
        self.l_auto.config(text=f"🚗 Spălare auto: {v}  –  {d}")
        v, d = logic.laundry(self.data)
        self.l_rufe.config(text=f"👕 Uscat rufe afară: {v}  –  {d}")
        s, extra = logic.outfit(self.data)
        self.l_outfit.config(text="• " + s + "".join("\n• " + e for e in extra))
        umple(self.t_act, [(n, f"{s}/10", c) for n, s, c in logic.activities(self.data, self.air)])

    # ================================================================ TAB: Sănătate
    def _tab_sanatate(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="❤️ Sănătate")
        ttk.Label(f, text="Alergeni – polen (grăunțe/m³)", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.t_polen = tabel(f, [("tip", "Tip", 160), ("val", "Valoare", 100), ("niv", "Nivel", 140)], inaltime=6)
        self.t_polen.pack(fill="x", padx=10)
        ttk.Label(f, text="Calitatea aerului", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.t_aer = tabel(f, [("ind", "Indicator", 160), ("val", "Valoare", 100), ("niv", "Nivel", 140)], inaltime=4)
        self.t_aer.pack(fill="x", padx=10)
        self.l_aer = ttk.Label(f, font=("Segoe UI", 10, "bold"), wraplength=940)
        self.l_aer.pack(anchor="w", padx=10, pady=3)

        ttk.Label(f, text="Index UV & protecție solară", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        r = ttk.Frame(f)
        r.pack(fill="x", padx=10)
        ttk.Label(r, text="Tipul tău de piele:").pack(side="left")
        self.cb_piele = ttk.Combobox(r, state="readonly", width=42, values=list(logic.SKIN_TYPES))
        self.cb_piele.current(2)
        self.cb_piele.pack(side="left", padx=6)
        self.cb_piele.bind("<<ComboboxSelected>>", lambda e: self._actualizeaza_uv())
        self.l_uv = ttk.Label(f, font=("Segoe UI", 10), wraplength=940, justify="left")
        self.l_uv.pack(anchor="w", padx=10, pady=4)

    def _actualizeaza_sanatate(self):
        a = self.air or {}
        nume = [("Mesteacăn", "birch_pollen"), ("Arin", "alder_pollen"), ("Iarbă", "grass_pollen"),
                ("Ambrozie", "ragweed_pollen"), ("Pelin", "mugwort_pollen"), ("Măslin", "olive_pollen")]
        umple(self.t_polen, [(n, "—" if a.get(k) is None else f"{a[k]:.0f}", logic.pollen_level(a.get(k)))
                             for n, k in nume])
        niv, sfat = logic.aqi_info(a.get("european_aqi"))
        pm25, pm10, co2 = a.get("pm2_5"), a.get("pm10"), a.get("carbon_dioxide")
        fmt = lambda v: "—" if v is None else f"{v:.0f}"
        umple(self.t_aer, [
            ("AQI european", fmt(a.get("european_aqi")), niv),
            ("PM2.5 (µg/m³)", fmt(pm25), logic.pm_level(pm25, (10, 25, 50))),
            ("PM10 (µg/m³)", fmt(pm10), logic.pm_level(pm10, (20, 50, 100))),
            ("CO₂ (ppm)", fmt(co2), "fond atmosferic ≈ 420"),
        ])
        self.l_aer.config(text=("🌫️ " + sfat) if sfat else "Date indisponibile pentru această zonă.")
        self._actualizeaza_uv()

    def _actualizeaza_uv(self):
        if not self.data:
            return
        i = logic.hour_index(self.data)
        uv_acum = self.data["hourly"]["uv_index"][i] or 0
        uv_max = self.data["daily"]["uv_index_max"][0] or 0
        factor = logic.SKIN_TYPES[self.cb_piele.get()]
        minute, sfat = logic.uv_advice(uv_max, factor)
        txt = f"Index UV acum: {uv_acum:.1f}   |   maxim azi: {uv_max:.1f}\n"
        if minute:
            txt += f"Timp orientativ până la arsuri la UV maxim, fără protecție: ~{minute:.0f} minute\n"
        txt += sfat + "\n(Valori orientative, nu înlocuiesc sfatul medicului.)"
        self.l_uv.config(text="☀️ " + txt)

    # ================================================================ TAB: Radar
    def _tab_radar(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🗺️ Radar")
        self.map_widget = None
        if tkintermapview is None:
            ttk.Label(f, text="Instalează biblioteca pentru hartă:\n\n    pip install tkintermapview",
                      font=("Segoe UI", 12)).pack(pady=40)
            return
        r = ttk.Frame(f)
        r.pack(fill="x", padx=8, pady=6)
        for text, tip in [("🌧️ Radar precipitații", "radar"), ("☁️ Nori (satelit IR)", "nori"),
                          ("🗺️ Doar harta", "nimic")]:
            ttk.Button(r, text=text, command=lambda t=tip: self._strat(t)).pack(side="left", padx=3)
        self.l_radar = ttk.Label(r, text="")
        self.l_radar.pack(side="left", padx=10)
        self.map_widget = tkintermapview.TkinterMapView(f, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.map_widget.set_position(47.8, 22.9)
        self.map_widget.set_zoom(6)

    def _strat(self, tip):
        if tip == "nimic":
            self.map_widget.set_overlay_tile_server(None) if hasattr(self.map_widget, "set_overlay_tile_server") else None
            self.l_radar.config(text="")
            return
        self.l_radar.config(text="Se încarcă stratul...")

        def lucru():
            j = api.rainviewer()
            host = j["host"]
            if tip == "radar":
                return f"{host}{j['radar']['past'][-1]['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
            return f"{host}{j['satellite']['infrared'][-1]['path']}/256/{{z}}/{{x}}/{{y}}/0/0_0.png"

        def gata(url):
            if not hasattr(self.map_widget, "set_overlay_tile_server"):
                messagebox.showinfo("Hartă", "Actualizează biblioteca:  pip install -U tkintermapview")
                return
            self.map_widget.set_overlay_tile_server(url)
            self.l_radar.config(text="Strat activ (date RainViewer)")
        self.ruleaza(lucru, gata)

    # ================================================================ TAB: Meteo pe traseu
    def _tab_traseu(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🚗 Pe traseu")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=8, pady=8)
        ttk.Label(r, text="Plecare:").pack(side="left")
        self.e_a = ttk.Entry(r, width=20)
        self.e_a.insert(0, "București")
        self.e_a.pack(side="left", padx=4)
        ttk.Label(r, text="Destinație:").pack(side="left")
        self.e_b = ttk.Entry(r, width=20)
        self.e_b.insert(0, "Brașov")
        self.e_b.pack(side="left", padx=4)
        ttk.Button(r, text="Calculează (plecare acum)", command=self._traseu).pack(side="left", padx=6)
        self.l_traseu = ttk.Label(f, text="", font=("Segoe UI", 10, "bold"))
        self.l_traseu.pack(anchor="w", padx=8)
        self.t_traseu = tabel(f, [("km", "Km", 60), ("poz", "Poziție", 130), ("ora", "Sosire (ora locală)", 120),
                                  ("vreme", "Vreme", 170), ("t", "Temp.", 60), ("prob", "Ploaie %", 70),
                                  ("vant", "Rafale", 80), ("av", "Atenție", 220)], inaltime=12)
        self.t_traseu.pack(fill="both", expand=True, padx=8, pady=6)

    def _traseu(self):
        a, b = self.e_a.get().strip(), self.e_b.get().strip()
        if not a or not b:
            return
        self.stare.config(text="Se calculează traseul...")

        def lucru():
            ca, cb = api.geocode(a), api.geocode(b)
            puncte, durata, km = api.route(ca, cb)
            start = datetime.now(timezone.utc)
            rez = []
            for p in puncte:
                d = api.forecast(p["lat"], p["lon"], days=3)
                eta_local = start + timedelta(seconds=durata * p["frac"]) + timedelta(seconds=d["utc_offset_seconds"])
                cheie = (eta_local + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:00")
                ore = d["hourly"]["time"]
                k = ore.index(cheie) if cheie in ore else len(ore) - 1
                h = d["hourly"]
                cod, gust, prob = h["weather_code"][k], h["wind_gusts_10m"][k] or 0, h["precipitation_probability"][k] or 0
                av = []
                if logic.is_storm(cod): av.append("furtună")
                if logic.is_snow(cod): av.append("ninsoare/polei")
                if cod in (45, 48): av.append("ceață")
                if logic.is_rain(cod) and prob >= 60: av.append("carosabil ud")
                if gust >= 60: av.append("vânt puternic")
                if h["temperature_2m"][k] <= 1 and prob >= 30: av.append("risc de polei")
                rez.append((f"{p['km']:.0f}", f"{p['lat']:.2f}, {p['lon']:.2f}", f"{eta_local:%d.%m %H:%M}",
                            logic.weather_text(cod), f"{h['temperature_2m'][k]:.0f}°C", f"{prob:.0f}%",
                            f"{gust:.0f} km/h", ", ".join(av) or "—"))
            return rez, durata, km, ca["name"], cb["name"]

        def gata(r):
            rez, durata, km, na, nb = r
            umple(self.t_traseu, rez)
            self.l_traseu.config(text=f"{na} → {nb}:  {km:.0f} km,  ~{int(durata // 3600)} h {int(durata % 3600 // 60)} min")
            self.stare.config(text="")
        self.ruleaza(lucru, gata)

    # ================================================================ TAB: Schimbări climatice
    def _tab_clima(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🌍 Clima în timp")
        ttk.Label(f, text="Cum era vremea în aceeași zi, în orașul selectat, acum 1, 5, 10, 25 și 50 de ani?",
                  font=("Segoe UI", 11)).pack(anchor="w", padx=10, pady=10)
        ttk.Button(f, text="Compară cu trecutul", command=self._clima).pack(anchor="w", padx=10)
        self.t_clima = tabel(f, [("an", "An", 80), ("max", "Max", 90), ("min", "Min", 90),
                                 ("prec", "Precip. (mm)", 100), ("dif", "Față de azi (max)", 160)], inaltime=6)
        self.t_clima.pack(fill="x", padx=10, pady=10)
        self.l_clima = ttk.Label(f, wraplength=940, font=("Segoe UI", 11), justify="left")
        self.l_clima.pack(anchor="w", padx=10)

    def _clima(self):
        if not self.city:
            return
        azi = date.today()
        tmax_azi = self.data["daily"]["temperature_2m_max"][0]
        self.stare.config(text="Se încarcă arhiva climatică...")

        def lucru():
            return [api.historical(self.city["lat"], self.city["lon"], azi, n) for n in (1, 5, 10, 25, 50)]

        def gata(rez):
            randuri, difs = [], []
            for r in rez:
                if r["tmax"] is None:
                    continue
                dif = tmax_azi - r["tmax"]
                difs.append((r["an"], dif))
                randuri.append((r["an"], f"{r['tmax']:.1f}°C", f"{r['tmin']:.1f}°C",
                                r["precip"], f"{dif:+.1f}°C"))
            randuri.append((f"{azi.year} (azi)", f"{tmax_azi:.1f}°C",
                            f"{self.data['daily']['temperature_2m_min'][0]:.1f}°C",
                            self.data["daily"]["precipitation_sum"][0], "—"))
            umple(self.t_clima, randuri)
            if difs:
                medie = sum(d for _, d in difs) / len(difs)
                cuvant = "mai cald" if medie > 0 else "mai rece"
                self.l_clima.config(text=(
                    f"În {self.city['name']}, temperatura maximă prevăzută azi este în medie cu {abs(medie):.1f}°C "
                    f"{cuvant} decât în aceeași zi din anii comparați.\n\nAtenție: o singură zi nu demonstrează un "
                    f"trend – vremea variază mult de la an la an. Schimbările climatice se văd în medii pe zeci "
                    f"de ani, nu în zile izolate."))
            self.stare.config(text="")
        self.ruleaza(lucru, gata)


if __name__ == "__main__":
    App().mainloop()
