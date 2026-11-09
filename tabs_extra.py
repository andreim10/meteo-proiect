"""Tab-urile noi: asistent chat, energie & smart home, astronomie, pescuit & agricultură.
Sunt într-un 'mixin' folosit de clasa App din app.py (au acces la self.data, self.extra etc.)."""

import tkinter as tk
from datetime import datetime
from tkinter import ttk

import chat
import extras
import hazards
from ui import tabel, umple

NU_AM_DATE = "Date indisponibile pentru această locație."


class ExtraTabs:
    # ================================================================ 💬 ASISTENT (chat)
    def _tab_chat(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="💬 Asistent")
        cadru = ttk.Frame(f)
        cadru.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt = tk.Text(cadru, wrap="word", state="disabled", font=("Segoe UI", 11), bg="#f7f9fc",
                           relief="flat", padx=8, pady=8)
        sb = ttk.Scrollbar(cadru, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.tag_configure("user", background="#d6e8ff", justify="right", lmargin1=200, lmargin2=200,
                               rmargin=10, spacing1=6, spacing3=6)
        self.txt.tag_configure("bot", background="#e9efe9", lmargin1=10, lmargin2=10, rmargin=120,
                               spacing1=6, spacing3=6)

        chips = ttk.Frame(f)
        chips.pack(fill="x", padx=8)
        for ex in ["O să plouă diseară?", "Când pun rufele la uscat săptămâna asta?",
                   "Ce temperatură e mâine dimineață?", "Ce să îmbrac?"]:
            ttk.Button(chips, text=ex, command=lambda t=ex: self._chat_trimite(t)).pack(side="left", padx=2, pady=4)

        rand = ttk.Frame(f)
        rand.pack(fill="x", padx=8, pady=(0, 8))
        self.e_chat = ttk.Entry(rand, font=("Segoe UI", 11))
        self.e_chat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.e_chat.bind("<Return>", lambda e: self._chat_trimite())
        ttk.Button(rand, text="Trimite", command=self._chat_trimite).pack(side="left")
        self._chat_scrie("bot", "Salut! 👋 Sunt asistentul meteo. Mă poți întreba în limbaj natural, de exemplu:\n"
                                "„O să plouă diseară când ies la alergat?” sau „La ce oră e cel mai bun moment să pun "
                                "rufele la uscat săptămâna asta?”")

    def _chat_scrie(self, cine, text):
        self.txt.config(state="normal")
        self.txt.insert("end", text + "\n", cine)
        self.txt.config(state="disabled")
        self.txt.see("end")

    def _chat_trimite(self, text=None):
        q = (text or self.e_chat.get()).strip()
        if not q:
            return
        self.e_chat.delete(0, "end")
        self._chat_scrie("user", q)
        if not self.data:
            self._chat_scrie("bot", "Încă încarc datele meteo, încearcă din nou în câteva secunde.")
            return
        try:
            self._chat_scrie("bot", chat.raspunde(q, self.data, self.air))
        except Exception as e:                              # noqa: BLE001
            self._chat_scrie("bot", f"Ups, nu am putut răspunde ({e}).")

    # ================================================================ ⚡ ENERGIE & SMART HOME
    def _tab_energie(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="⚡ Energie")
        ttk.Label(f, text="Producție fotovoltaică estimată", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        r = ttk.Frame(f)
        r.pack(fill="x", padx=10)
        ttk.Label(r, text="Putere instalată (kWp):").pack(side="left")
        self.sp_kwp = ttk.Spinbox(r, from_=1, to=50, increment=0.5, width=6)
        self.sp_kwp.set("5")
        self.sp_kwp.pack(side="left", padx=4)
        ttk.Label(r, text="Preț energie (lei/kWh):").pack(side="left", padx=(12, 0))
        self.sp_tarif = ttk.Spinbox(r, from_=0.1, to=5, increment=0.1, width=6)
        self.sp_tarif.set("1.3")
        self.sp_tarif.pack(side="left", padx=4)
        ttk.Button(r, text="Recalculează", command=self._actualizeaza_energie).pack(side="left", padx=10)
        self.l_solar = ttk.Label(f, font=("Segoe UI", 11), wraplength=940, justify="left")
        self.l_solar.pack(anchor="w", padx=10, pady=4)
        self.g_solar = tk.Canvas(f, height=120, bg="white", highlightthickness=1, highlightbackground="#ccc")
        self.g_solar.pack(fill="x", padx=10)
        self.t_solar = tabel(f, [("zi", "Zi", 110), ("rad", "Radiație (kWh/m²)", 130), ("soare", "Ore de soare", 100),
                                 ("kwh", "Producție (kWh)", 120)], inaltime=7)
        self.t_solar.pack(fill="x", padx=10, pady=6)

        ttk.Label(f, text="Consilier ventilație & climatizare (Smart Home)", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        r2 = ttk.Frame(f)
        r2.pack(fill="x", padx=10)
        ttk.Label(r2, text="Temperatura din casă (°C):").pack(side="left")
        self.sp_tin = ttk.Spinbox(r2, from_=5, to=40, width=5)
        self.sp_tin.set("22")
        self.sp_tin.pack(side="left", padx=4)
        ttk.Label(r2, text="Umiditate în casă (%):").pack(side="left", padx=(12, 0))
        self.sp_hin = ttk.Spinbox(r2, from_=10, to=95, width=5)
        self.sp_hin.set("50")
        self.sp_hin.pack(side="left", padx=4)
        ttk.Button(r2, text="Cere sfaturi", command=self._actualizeaza_smart).pack(side="left", padx=10)
        self.l_smart = ttk.Label(f, font=("Segoe UI", 10), wraplength=940, justify="left")
        self.l_smart.pack(anchor="w", padx=10, pady=4)

    def _citeste_float(self, spin, implicit):
        try:
            return float(spin.get().replace(",", "."))
        except ValueError:
            return implicit

    def _actualizeaza_energie(self):
        if not self.data:
            return
        if not self.extra:
            self.l_solar.config(text=NU_AM_DATE)
            return
        kwp = self._citeste_float(self.sp_kwp, 5)
        tarif = self._citeste_float(self.sp_tarif, 1.3)
        e = extras.energie_solara(self.extra, self.data["current"]["time"], kwp, tarif)
        self.l_solar.config(text=(f"☀️ Azi, un sistem de {kwp:g} kWp ar putea produce ≈ {e['azi']:.1f} kWh "
                                  f"(economie ≈ {e['economie']:.1f} lei). Randament sistem presupus: 75%.\n"
                                  f"Sfat: pornește mașina de spălat, boilerul sau încărcarea mașinii electrice la orele de vârf (bare mai înalte)."))
        umple(self.t_solar, [(z[8:10] + "." + z[5:7], f"{rad:.1f}", f"{e['soare'][k]:.1f} h" if k < len(e["soare"]) else "—",
                              f"{kwh:.1f}") for k, (z, rad, kwh) in enumerate(e["tabel"])])
        # grafic orar
        c = self.g_solar
        c.delete("all")
        c.update_idletasks()
        W, H = max(c.winfo_width(), 500), 120
        ore = e["ore_azi"]
        if not ore:
            return
        mx = max(v for _, v in ore) or 1
        lat = (W - 40) / 24
        for o, v in ore:
            x = 20 + o * lat
            inalt = v / mx * (H - 40)
            c.create_rectangle(x + 2, H - 20 - inalt, x + lat - 2, H - 20, fill="#f5b83d", outline="")
            if o % 3 == 0:
                c.create_text(x + lat / 2, H - 8, text=f"{o:02d}", font=("Segoe UI", 8))
        c.create_text(W - 10, 10, anchor="e", text=f"vârf ≈ {mx:.1f} kWh/oră", font=("Segoe UI", 9))

    def _actualizeaza_smart(self):
        if not self.data:
            return
        t_in = self._citeste_float(self.sp_tin, 22)
        h_in = self._citeste_float(self.sp_hin, 50)
        sfaturi, ferestre = extras.smart_home(self.data, t_in, h_in)
        txt = "\n".join(sfaturi)
        if ferestre:
            txt += "\n\n🕐 Intervale potrivite pentru aerisire (următoarele 24h): " + ", ".join(ferestre)
        self.l_smart.config(text=txt)

    # ================================================================ 🔭 ASTRO
    def _tab_astro(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🔭 Astro")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=10, pady=10)
        ttk.Label(r, text="Poluare luminoasă (Bortle 1 = cer perfect … 9 = centru de oraș):").pack(side="left")
        self.sp_bortle = ttk.Spinbox(r, from_=1, to=9, width=4)
        self.sp_bortle.set("5")
        self.sp_bortle.pack(side="left", padx=6)
        ttk.Button(r, text="Recalculează", command=self._actualizeaza_astro).pack(side="left")
        self.l_bortle = ttk.Label(f, foreground="#666")
        self.l_bortle.pack(anchor="w", padx=10)
        self.l_astro = ttk.Label(f, font=("Segoe UI", 12), wraplength=940, justify="left")
        self.l_astro.pack(anchor="w", padx=10, pady=10)

    def _seteaza_bortle_din_oras(self):
        b = extras.bortle_estimat(self.city.get("population", 0))
        self.sp_bortle.set(str(b))
        pop = self.city.get("population", 0)
        self.l_bortle.config(text=f"Estimat automat din populația localității ({pop:,} loc.) – îl poți modifica manual."
                             if pop else "Populație necunoscută – valoare implicită; poți modifica manual.")

    def _actualizeaza_astro(self):
        if not self.data:
            return
        b = int(self._citeste_float(self.sp_bortle, 5))
        b = max(1, min(9, b))
        a = extras.raport_astro(self.data, self.city.get("population", 0), b, datetime.now())
        self.l_astro.config(text=(
            f"{a['luna']}  –  iluminată {a['ilum'] * 100:.0f}%\n\n"
            f"☁️ Nori în această noapte (21:00–03:00): ~{a['nori']:.0f}%\n"
            f"💡 Poluare luminoasă: Bortle {b}\n\n"
            f"⭐ Index cer profund (galaxii, nebuloase, Calea Lactee): {a['cer_profund']}/10\n"
            f"🪐 Index planete și Lună: {a['planete']}/10\n\n"
            f"{a['calea_lactee']}\n\n{a['meteori']}\n\n"
            f"(Faza Lunii e calculată matematic; Bortle e estimat – mergi în afara orașului pentru scoruri mai bune.)"))

    # ================================================================ 🎣 PESCUIT & AGRICULTURĂ
    def _tab_pescuit(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🎣 Pescuit & Agri")
        ttk.Label(f, text="Presiune atmosferică & pescuit", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.l_presiune = ttk.Label(f, font=("Segoe UI", 11), wraplength=940, justify="left")
        self.l_presiune.pack(anchor="w", padx=10)
        self.t_solunar = tabel(f, [("tip", "Perioadă solunară", 140), ("ora", "Interval", 160)], inaltime=5)
        self.t_solunar.pack(anchor="w", padx=10, pady=6)
        ttk.Label(f, text="Agricultură & grădinărit", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.l_agri = ttk.Label(f, font=("Segoe UI", 11), wraplength=940, justify="left")
        self.l_agri.pack(anchor="w", padx=10)

    def _actualizeaza_pescuit(self):
        if not self.data:
            return
        if not self.extra:
            self.l_presiune.config(text=NU_AM_DATE)
            self.l_agri.config(text=NU_AM_DATE)
            return
        cur_time = self.data["current"]["time"]
        t = extras.tendinta_presiune(self.extra, cur_time)
        varsta = extras.luna(datetime.now())[2]
        per = extras.solunar(self.data, varsta)
        scor = extras.scor_pescuit(self.data, t, per)
        self.l_presiune.config(text=(
            f"🎣 Index pescuit: {scor}/10\n"
            f"Presiune: {t['p0']:.0f} hPa, tendință {t['tip']}\n"
            f"Variație: {t['d3']:+.1f} hPa în 3h, {t['d12']:+.1f} în 12h, {t['d24']:+.1f} în 24h\n"
            f"🤕 Risc de migrenă / sensibilitate la presiune: {t['migrena']}\n"
            f"(Regulă generală: peștii sunt activi când presiunea e stabilă sau scade lent; "
            f"după o creștere bruscă prind mai greu. Perioadele solunare sunt aproximative.)"))
        umple(self.t_solunar, [("Majoră ⭐⭐" if tip == "major" else "Minoră ⭐",
                                f"{a:%H:%M} – {b:%H:%M}") for a, b, tip in per])
        a = extras.raport_agri(self.data, self.extra, cur_time)
        um = "—" if a["um"] is None else f"{a['um'] * 100:.0f}%"
        self.l_agri.config(text=(
            f"🌱 Umiditatea solului (3–9 cm): {um} – {a['nivel']}\n"
            f"Evapotranspirație azi: {a['et0']:.1f} mm  |  Ploaie estimată în 48h: {a['ploaie48']:.1f} mm\n\n"
            + "\n".join(a["sfaturi"])))

    # ================================================================ 🚨 ALERTE DEZASTRE
    def _tab_hazard(self):
        f = ttk.Frame(self.tabs)
        self.tabs.add(f, text="🚨 Dezastre")
        r = ttk.Frame(f)
        r.pack(fill="x", padx=10, pady=8)
        ttk.Label(r, text="Alerte pentru locația curentă", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(r, text="Reîmprospătează", command=self._actualizeaza_hazard).pack(side="left", padx=10)
        self.l_hz_stare = ttk.Label(f, foreground="#666", wraplength=940)
        self.l_hz_stare.pack(anchor="w", padx=10)
        self.t_hz = tabel(f, [("niv", "Nivel", 110), ("tip", "Tip", 190), ("desc", "Detalii", 380),
                              ("dist", "Distanță", 80), ("data", "Când", 110)], inaltime=12)
        self.t_hz.column("desc", anchor="w")
        self.t_hz.pack(fill="both", expand=True, padx=10, pady=6)
        self.l_hz_info = ttk.Label(f, wraplength=940, foreground="#b03a2e")
        self.l_hz_info.pack(anchor="w", padx=10, pady=(0, 8))

    def _actualizeaza_hazard(self):
        if not self.data:
            return
        self.l_hz_stare.config(text="Se verifică sursele...")
        city, data = self.city, self.data
        self.ruleaza(lambda: hazards.colecteaza(city, data), self._arata_hazard)

    def _arata_hazard(self, rez):
        alerte, stari = rez
        rows = [(hazards.NIVEL[n], tip, desc, f"{d:.0f} km" if d else "zona ta", cand)
                for n, tip, desc, d, cand in alerte]
        umple(self.t_hz, rows or [("✅", "Nicio alertă", "Nu s-au găsit alerte în sursele verificate", "", "")])
        self.l_hz_stare.config(text="   ".join(stari))
        ro = (self.city.get("country") or "").lower() in ("românia", "romania")
        self.l_hz_info.config(text="⚠️ Informativ – nu înlocuiește alertele oficiale. "
                                   + (hazards.LINKURI_RO if ro else hazards.LINKURI_GEN))
