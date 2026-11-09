# meteo-proiect
# 🌤️ meteo-proiect

Un proiect în Python conceput pentru monitorizarea, analiza și afișarea prognozei meteorologice în timp real. Proiectul a fost realizat ca și proiect final pentru materiei PCLP 3- Proiect Python

🔗 **Acces Online (Live Demo):** [https://deft-sprinkles-d6bcac.netlify.app](https://deft-sprinkles-d6bcac.netlify.app)

---

## 🚀 Caracteristici (Features)
* 📍 **Localizare automată:** Prognoză meteo personalizată în funcție de locația curentă.
* 📊 **Prognoze detaliate:** Afișarea vremii curente, evoluția pe ore (următoarele 24h) și prognoza pe 10 zile.
* ⚖️ **Comparare orașe:** Funcție dedicată pentru a compara vremea din București, Viena, Londra sau alte locații.
* 🌍 **Date istorice:** Analiză comparativă cu aceeași zi din trecut (acum 1, 5, 10, 25 sau 50 de ani).
* ❤️ **Sănătate și Activități:** Recomandări personalizate în funcție de vreme și tipul de piele (indici UV).

---

## 🛠️ Cerințe și Instalare

Pentru a rula acest proiect local, urmează pașii de mai jos. Proiectul folosește un mediu virtual (`venv`) dedicat pentru gestionarea dependențelor.

### 1. Clonarea repository-ului
```bash
git clone https://github.com
cd meteo-proiect
```

### 2. Activarea mediului virtual (`venv`)
În funcție de sistemul tău de operare, rulează comanda potrivită în terminal:

* **Pe Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Pe Windows (Command Prompt):**
  ```cmd
  .\venv\Scripts\activate.bat
  ```
* **Pe macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Instalarea dependențelor
Instalează toate modulele necesare rulând:
```bash
pip install -r requirements.txt
```

---

## 💻 Mod de utilizare

După ce ai activat mediul virtual, poți lansa scriptul în execuție folosind comanda:

```bash
python main.py
```

*Datele meteorologice sunt furnizate cu ajutorul API-ului Open-Meteo.com.*

---

## 👤 Autor
* **Andrei Mănescu** - [@andreim10](https://github.com)
