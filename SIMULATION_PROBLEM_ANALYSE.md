# Analyse: Warum die Simulation hängt

## Problembeschreibung
Alle Seiten zeigen "🔄 Happy Path Simulation wird ausgeführt..." an, aber die Simulation scheint nicht abzuschließen.

## Identifizierte Probleme

### 1. **Rechenintensive Initialisierung**

Die Simulation führt beim Initialisieren sehr rechenintensive Operationen aus:

**Datei:** `simulation/simulator.py`

**Problemstelle 1:** `_initialize_stock_from_inbound()` (Zeile 76-125)
- Wird im `__init__` aufgerufen (Zeile 74)
- Ruft `get_inbound_log_dataframe()` auf (Zeile 93)
- Diese Methode iteriert über **426 Tage** (01.11.2025 bis 31.12.2026)
- Für jeden Tag werden komplexe Berechnungen durchgeführt

**Problemstelle 2:** `get_inbound_log_dataframe()` in `simulation/china_transport.py` (Zeile 650-839)
- Iteriert über 426 Tage
- Für jeden Tag:
  - Berechnet Produktion für alle Sattel-Typen
  - Simuliert Hafen-Buckets (Eimer-Logik)
  - Führt Versand-Berechnungen durch
  - Erstellt DataFrame-Zeilen

**Problemstelle 3:** `get_daily_arrival_qty()` ruft `get_inbound_log_dataframe()` auf (Zeile 864)
- Wird während der Simulation **365 Mal** aufgerufen (einmal pro Tag)
- Jeder Aufruf berechnet die gesamte Inbound-Tabelle neu
- **Performance-Problem:** O(n²) Komplexität

### 2. **Fehlende Fehlerbehandlung**

**Datei:** `ui/utils.py`, Zeile 56-69

```python
def run_happy_path_simulation():
    if not st.session_state.happy_path_run and st.session_state.results_df is None:
        try:
            with st.spinner("🔄 Happy Path Simulation wird ausgeführt..."):
                simulator = create_simulator()  # <-- Hier könnte es hängen
                results_df, kpis = simulator.run()  # <-- Oder hier
                # ...
```

**Problem:**
- Wenn `create_simulator()` hängt (z.B. bei `_initialize_stock_from_inbound()`), wird kein Fehler angezeigt
- Der Spinner bleibt für immer sichtbar
- Keine Timeout-Mechanismus

### 3. **Potenzielle Endlosschleife**

**Datei:** `simulation/china_transport.py`, Zeile 370-389

```python
def _get_next_workday(self, start_day: int, use_chinese_holidays: bool = True) -> int:
    current_day = start_day + 1
    while True:  # <-- Potenzielle Endlosschleife
        current_date = self.workday_calculator.get_date_from_day(current_day)
        # ...
```

**Problem:**
- Wenn `get_date_from_day()` einen Fehler wirft oder ungültige Werte zurückgibt, könnte die Schleife endlos laufen
- Keine Maximalanzahl von Iterationen

### 4. **Cache-Invalidierung während der Initialisierung**

**Datei:** `simulation/china_transport.py`

**Problem:**
- `_initialize_stock_from_inbound()` ruft `get_inbound_log_dataframe()` auf
- Diese Methode verwendet einen Cache (Zeile 660-662)
- Aber während der Initialisierung werden noch keine Bestellungen platziert (`transport_status` ist leer)
- Die Methode könnte versuchen, auf leere Daten zuzugreifen

### 5. **Fehlende Validierung**

**Datei:** `simulation/simulator.py`, Zeile 92-96

```python
try:
    inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
except Exception:
    # Bei Fehler: behalte stock_saddles = 0.0
    return
```

**Problem:**
- Exceptions werden stillschweigend ignoriert
- Keine Logging-Ausgabe
- Keine Möglichkeit, das Problem zu diagnostizieren

## Wahrscheinlichste Ursache

**Die Simulation hängt wahrscheinlich bei der Initialisierung:**

1. `create_simulator()` wird aufgerufen
2. `Simulator.__init__()` wird ausgeführt
3. `_place_initial_orders()` wird aufgerufen (Zeile 65)
4. `_warmup_logistics()` wird aufgerufen (Zeile 69)
5. `_initialize_stock_from_inbound()` wird aufgerufen (Zeile 74)
6. **HIER HÄNGT ES:** `get_inbound_log_dataframe()` benötigt sehr lange (426 Tage × komplexe Berechnungen)
7. Der Spinner bleibt sichtbar, weil die Funktion noch läuft

## Empfohlene Diagnose-Schritte

### 1. Prüfen Sie die Konsole/Terminal
- Öffnen Sie das Terminal, in dem `streamlit run app.py` läuft
- Prüfen Sie auf Fehlermeldungen oder Stack-Traces
- Prüfen Sie, ob die CPU-Auslastung hoch ist (läuft die Simulation noch?)

### 2. Prüfen Sie den Browser-Console
- Öffnen Sie die Browser-Entwicklertools (F12)
- Prüfen Sie die Console auf JavaScript-Fehler
- Prüfen Sie das Network-Tab auf hängende Requests

### 3. Fügen Sie Debug-Ausgaben hinzu
- In `simulation/simulator.py`, Zeile 76, fügen Sie hinzu:
  ```python
  print("DEBUG: Start _initialize_stock_from_inbound")
  ```
- In `simulation/china_transport.py`, Zeile 650, fügen Sie hinzu:
  ```python
  print(f"DEBUG: get_inbound_log_dataframe called, transport_status length: {len(self.transport_status)}")
  ```

### 4. Prüfen Sie die Daten
- Ist `transport_status` leer beim ersten Aufruf von `get_inbound_log_dataframe()`?
- Werden die initialen Bestellungen korrekt platziert?

## Mögliche Lösungen (ohne Code-Änderungen)

### Lösung 1: Warten Sie länger
- Die Simulation könnte einfach sehr lange dauern (mehrere Minuten)
- Lassen Sie die App 5-10 Minuten laufen
- Prüfen Sie die CPU-Auslastung im Task Manager

### Lösung 2: Prüfen Sie die Streamlit-Logs
- Streamlit schreibt Logs in die Konsole
- Prüfen Sie auf Fehlermeldungen oder Warnings

### Lösung 3: Reduzieren Sie den Zeitraum
- Temporär: Ändern Sie `days = 365` auf `days = 10` in `simulator.py` Zeile 171
- Das reduziert die Simulationszeit erheblich

## Nächste Schritte

1. **Sofort:** Prüfen Sie das Terminal auf Fehlermeldungen
2. **Sofort:** Prüfen Sie die CPU-Auslastung (Task Manager)
3. **Wenn keine Fehler:** Warten Sie 5-10 Minuten
4. **Wenn es immer noch hängt:** Fügen Sie Debug-Ausgaben hinzu (siehe oben)

