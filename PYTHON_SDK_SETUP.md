# Python SDK Einrichtung in PyCharm - Detaillierte Anleitung

## Übersicht
Diese Anleitung zeigt Ihnen, wie Sie ein Python SDK (Interpreter) in PyCharm für Ihr `scm-app` Projekt einrichten.

---

## Schritt 1: Python-Interpreter in PyCharm konfigurieren

### Methode A: Über Settings (Empfohlen)

1. **Einstellungen öffnen:**
   - Klicken Sie auf `File` → `Settings` (oder drücken Sie `Strg+Alt+S`)
   - **Alternative:** Rechtsklick auf das Projekt im Project Explorer → `Open Module Settings`

2. **Zum Python Interpreter navigieren:**
   - Im linken Menü: `Project: scm-app` → `Python Interpreter`
   - Oder: `Project: scm-app` → `Project Structure` → dann oben zu `Python Interpreter` wechseln

3. **Interpreter hinzufügen:**
   - Klicken Sie auf das **Zahnrad-Symbol** (⚙️) rechts neben dem Dropdown "Python Interpreter"
   - Wählen Sie `Add...` oder `Add Interpreter...`

4. **Interpreter-Typ auswählen:**
   - Wählen Sie `Add Local Interpreter...`
   - **Wichtig:** Nicht "On WSL" oder "On Docker" wählen (nur wenn Sie diese verwenden)

5. **Virtuelle Umgebung erstellen (Empfohlen):**
   - Wählen Sie `Virtualenv Environment` aus
   - Aktivieren Sie `New environment` (Radio-Button)
   - **Location:** `D:\scm-app\venv` (oder lassen Sie den Standard)
   - **Base interpreter:** Wählen Sie eine Python-Version (3.10 oder 3.11 empfohlen)
     - Falls keine angezeigt wird: Klicken Sie auf `...` und navigieren Sie zu Ihrer Python-Installation
     - Typischer Pfad: `C:\Users\[IhrName]\AppData\Local\Programs\Python\Python3XX\python.exe`
   - **Inherit global site-packages:** Optional (nicht empfohlen für saubere Umgebung)
   - **Make available to all projects:** Optional
   - Klicken Sie auf `OK`

6. **Interpreter bestätigen:**
   - Der neue Interpreter sollte jetzt im Dropdown angezeigt werden
   - Format: `Python 3.XX (scm-app)` oder `venv (scm-app)`
   - Klicken Sie auf `OK` oder `Apply`

### Methode B: Über Run Configuration (Schnell)

1. **Run Configuration öffnen:**
   - Klicken Sie auf `Run` → `Edit Configurations...`
   - Oder: Rechtsklick auf `app.py` → `Modify Run Configuration...`

2. **SDK auswählen:**
   - Im Feld "Use SDK of module" klicken Sie auf das Dropdown
   - Wählen Sie `Add Interpreter...` → `Add Local Interpreter...`
   - Folgen Sie dann den Schritten aus Methode A, Schritt 5

---

## Schritt 2: Python installieren (falls noch nicht vorhanden)

Falls Sie noch kein Python installiert haben:

1. **Python herunterladen:**
   - Offizielle Website: https://www.python.org/downloads/
   - Wählen Sie Python 3.10 oder 3.11 (Windows Installer 64-bit)

2. **Installation:**
   - **WICHTIG:** Aktivieren Sie beim Installieren: "Add Python to PATH"
   - Wählen Sie "Install Now" oder "Customize installation"
   - Nach Installation: PyCharm neu starten

3. **Installation prüfen:**
   - Öffnen Sie PowerShell oder CMD
   - Führen Sie aus: `python --version`
   - Sollte z.B. `Python 3.11.x` anzeigen

---

## Schritt 3: Abhängigkeiten installieren

### Option A: Über PyCharm Terminal (Empfohlen)

1. **Terminal öffnen:**
   - Unten in PyCharm: Klicken Sie auf den Tab `Terminal`
   - Oder: `Alt+F12` drücken
   - **Wichtig:** Stellen Sie sicher, dass die virtuelle Umgebung aktiviert ist
     - Im Terminal sollte `(venv)` am Anfang der Zeile stehen
     - Falls nicht: Aktivieren Sie manuell mit `venv\Scripts\activate` (Windows)

2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Installation prüfen:**
   ```bash
   pip list
   ```
   - Sollte `streamlit`, `pandas`, `plotly`, `numpy`, `holidays` anzeigen

### Option B: Über PyCharm Package Manager

1. **Settings öffnen:**
   - `File` → `Settings` → `Project: scm-app` → `Python Interpreter`

2. **Pakete installieren:**
   - Klicken Sie auf das `+` Symbol (oben rechts)
   - Suchen Sie nach `streamlit` und klicken Sie `Install Package`
   - Wiederholen Sie für alle Pakete aus `requirements.txt`
   - **Oder:** Klicken Sie auf `Install from requirements.txt` (falls verfügbar)

---

## Schritt 4: Run Configuration korrigieren

1. **Run Configuration öffnen:**
   - `Run` → `Edit Configurations...`
   - Oder: Rechtsklick auf `app.py` → `Modify Run Configuration...`

2. **SDK zuweisen:**
   - Im Feld **"Use SDK of module"** sollte jetzt Ihr Interpreter angezeigt werden
   - Falls nicht: Wählen Sie ihn aus dem Dropdown aus
   - Format sollte sein: `Python 3.XX (scm-app)` oder `venv (scm-app)`

3. **Script Path prüfen:**
   - **Script path:** `D:/scm-app/app.py` (sollte bereits korrekt sein)

4. **Für Streamlit-App (Alternative Konfiguration):**
   - **Script path:** `D:/scm-app/app.py`
   - **Parameters:** `run` (für `streamlit run app.py`)
   - **Oder:** Erstellen Sie eine separate Streamlit-Run-Konfiguration (siehe Schritt 5)

5. **Konfiguration speichern:**
   - Klicken Sie auf `OK` oder `Apply`
   - Der Fehler "Please select a module with a valid Python SDK" sollte verschwinden

---

## Schritt 5: Streamlit-Run-Konfiguration erstellen (Optional, aber empfohlen)

Da Ihre App eine Streamlit-App ist, ist es besser, eine spezielle Streamlit-Konfiguration zu erstellen:

1. **Run Configuration öffnen:**
   - `Run` → `Edit Configurations...`

2. **Neue Konfiguration:**
   - Klicken Sie auf `+` (oben links)
   - Wählen Sie `Python` aus

3. **Konfiguration ausfüllen:**
   - **Name:** `Streamlit App` oder `SCM App`
   - **Script path:** `D:/scm-app/app.py`
   - **Parameters:** `run` (oder leer lassen, wenn Sie `streamlit run` direkt verwenden)
   - **Use SDK of module:** Wählen Sie Ihren Interpreter aus
   - **Working directory:** `D:/scm-app`

4. **Alternative: Streamlit direkt aufrufen:**
   - **Script path:** Wählen Sie `streamlit` aus (falls im venv installiert)
   - **Parameters:** `run app.py`
   - **Working directory:** `D:/scm-app`

5. **Speichern:**
   - Klicken Sie auf `OK`

---

## Schritt 6: App testen

1. **App starten:**
   - Wählen Sie Ihre Run-Konfiguration aus dem Dropdown (oben rechts)
   - Klicken Sie auf den grünen Play-Button (▶️) oder drücken Sie `Shift+F10`

2. **Erwartetes Verhalten:**
   - Terminal zeigt: `streamlit run app.py`
   - Browser öffnet sich automatisch mit `http://localhost:8501`
   - Die SCM App sollte geladen werden

3. **Falls Fehler auftreten:**
   - Prüfen Sie die Fehlermeldung im Terminal
   - Stellen Sie sicher, dass alle Pakete installiert sind: `pip install -r requirements.txt`
   - Prüfen Sie, ob der Python-Interpreter korrekt zugewiesen ist

---

## Nützliche Links

### Offizielle PyCharm-Dokumentation:
- **Python Interpreter konfigurieren:**
  https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html

- **Virtuelle Umgebung erstellen:**
  https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html

- **Run Configurations:**
  https://www.jetbrains.com/help/pycharm/run-debug-configuration.html

- **Pakete installieren:**
  https://www.jetbrains.com/help/pycharm/installing-uninstalling-and-upgrading-packages.html

### Python-Installation:
- **Python herunterladen:**
  https://www.python.org/downloads/

- **Python auf Windows installieren:**
  https://docs.python.org/3/using/windows.html

### Streamlit:
- **Streamlit-Dokumentation:**
  https://docs.streamlit.io/

- **Streamlit in PyCharm ausführen:**
  https://docs.streamlit.io/get-started/installation

---

## Häufige Probleme und Lösungen

### Problem 1: "Please select a module with a valid Python SDK"
**Lösung:**
- Stellen Sie sicher, dass Sie einen Python-Interpreter in Schritt 1 hinzugefügt haben
- In der Run Configuration: Wählen Sie den Interpreter im Dropdown "Use SDK of module" aus

### Problem 2: "Python interpreter not found"
**Lösung:**
- Installieren Sie Python (siehe Schritt 2)
- Oder: Geben Sie den Pfad zu Python manuell an (z.B. `C:\Python311\python.exe`)

### Problem 3: "Module not found" Fehler beim Ausführen
**Lösung:**
- Installieren Sie die Abhängigkeiten: `pip install -r requirements.txt`
- Stellen Sie sicher, dass Sie die richtige virtuelle Umgebung verwenden

### Problem 4: Terminal zeigt nicht (venv)
**Lösung:**
- Aktivieren Sie die virtuelle Umgebung manuell:
  ```bash
  D:\scm-app\venv\Scripts\activate
  ```

### Problem 5: Streamlit startet nicht
**Lösung:**
- Prüfen Sie, ob Streamlit installiert ist: `pip list | findstr streamlit`
- Falls nicht: `pip install streamlit`
- Starten Sie manuell: `streamlit run app.py` im Terminal

---

## Zusammenfassung der wichtigsten Schritte

1. ✅ Python installieren (falls nicht vorhanden)
2. ✅ Virtuelle Umgebung in PyCharm erstellen
3. ✅ Abhängigkeiten installieren (`pip install -r requirements.txt`)
4. ✅ Run Configuration mit SDK verknüpfen
5. ✅ App testen

---

**Viel Erfolg!** 🚀

