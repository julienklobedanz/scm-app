# Anleitung: Änderungen seit letztem Merge prüfen

## 📋 Übersicht

Diese Anleitung hilft Ihnen, die Änderungen seit dem letzten Merge zu verstehen und mögliche Probleme zu identifizieren.

---

## 🔍 Schritt 1: Git-Historie prüfen

### 1.1 Letzte Commits anzeigen
```bash
cd d:\scm-app
git log --oneline -10
```

**Was Sie sehen sollten:**
- `13d7e09 Wasserschaden Szenario Anpassung und Szenario UI` (neuester Commit)
- `9906843 Dark mode entfernt` (vorheriger Commit)

### 1.2 Änderungen im letzten Commit anzeigen
```bash
git diff HEAD~1 HEAD --stat
```

**Was Sie sehen sollten:**
- 6 Dateien geändert
- Hauptsächlich: `scenario_sidebar.py`, `material_calculations.py`, `production_calculations.py`

---

## 📁 Schritt 2: Geänderte Dateien prüfen

### 2.1 Detaillierte Änderungen anzeigen
```bash
git diff HEAD~1 HEAD
```

**Wichtigste Änderungen:**

#### `models/scenarios.py`
- **Was:** `WaterDamageScenario` erweitert um `affected_saddles` Feld
- **Warum:** Ermöglicht selektive Anwendung auf bestimmte Satteltypen
- **Auswirkung:** Neue Szenarien können jetzt spezifische Satteltypen auswählen

#### `ui/scenario_sidebar.py`
- **Was:** UI für Wasserschaden-Szenarien erweitert
- **Neue Features:**
  - Multi-Select für betroffene Satteltypen
  - Funktion `_format_scenario_details()` für bessere Anzeige
  - Funktion `_day_index_to_date()` für Datumskonvertierung
- **Auswirkung:** Bessere UX beim Erstellen von Wasserschaden-Szenarien

#### `ui/material_calculations.py`
- **Was:** Wasserschaden-Verarbeitung angepasst
- **Änderung:** Unterstützt jetzt mehrere Szenarien parallel und `affected_saddles`
- **Auswirkung:** Mehrere Wasserschaden-Szenarien können gleichzeitig aktiv sein

#### `ui/production_calculations.py`
- **Was:** Wasserschaden-Verarbeitung angepasst
- **Änderung:** Unterstützt jetzt `affected_saddles` für selektive Anwendung
- **Auswirkung:** Wasserschaden wird nur auf ausgewählte Satteltypen angewendet

#### `simulation/china_transport.py`
- **Was:** Cache-Keys erweitert um `WaterDamageScenario` zu berücksichtigen
- **Auswirkung:** Bessere Cache-Invalidierung bei Szenario-Änderungen

---

## 🔧 Schritt 3: Mögliche Probleme identifizieren

### 3.1 Cache-Invalidierung prüfen

**Problem:** Wenn ein Szenario hinzugefügt wird, werden ALLE Caches invalidiert:
- `volume_planning_cache_key`
- `production_logs_cache`
- `material_inventory_data`
- `_supplier_log_cache` (im ChinaTransportManager)
- `_inbound_df_cache` (im ChinaTransportManager)

**Wo prüfen:**
```bash
# Zeige Cache-Invalidierung in scenario_sidebar.py
grep -n "Invalidiere" ui/scenario_sidebar.py
```

**Zeilen:** 350-368 (Wasserschaden hinzufügen), 562-586 (Szenario entfernen)

### 3.2 st.rerun() Aufrufe prüfen

**Problem:** `st.rerun()` wird nach Cache-Invalidierung aufgerufen, was zu Neuberechnungen führt.

**Wo prüfen:**
```bash
# Zeige alle st.rerun() Aufrufe
grep -n "st.rerun()" ui/scenario_sidebar.py
```

**Zeilen:** 279, 371, 403, 484, 538, 588, 604

**Mögliche Auswirkung:**
- Wenn Simulation läuft → `st.rerun()` könnte zu Problemen führen
- Cache-Invalidierung → teure Neuberechnungen → UI blockiert

### 3.3 Performance-kritische Funktionen prüfen

**Wo prüfen:**
```bash
# Zeige get_inbound_log_dataframe() Aufrufe
grep -rn "get_inbound_log_dataframe" . --include="*.py"
```

**Bekannte Probleme:**
- `get_inbound_log_dataframe()` kann 90-180 Sekunden dauern beim ersten Aufruf
- Wird aufgerufen wenn Caches invalidiert werden

---

## 🐛 Schritt 4: Problem-Diagnose

### 4.1 Prüfen ob Simulation hängt

**Symptome:**
- UI reagiert nicht mehr
- Keine Klicks möglich
- Progress-Bar zeigt keine Änderung

**Wo prüfen:**
1. Browser-Konsole öffnen (F12)
2. Nach Fehlermeldungen suchen
3. Network-Tab prüfen (laufende Requests?)

### 4.2 Prüfen ob Cache-Invalidierung das Problem ist

**Test:**
1. Öffnen Sie die App
2. Warten Sie bis Simulation fertig ist
3. Fügen Sie ein Wasserschaden-Szenario hinzu
4. Beobachten Sie ob UI hängt

**Erwartetes Verhalten:**
- Cache wird invalidiert
- `st.rerun()` wird aufgerufen
- Berechnungen werden neu gestartet
- UI sollte währenddessen reagieren (Progress-Bar)

**Tatsächliches Verhalten (wenn Problem vorhanden):**
- UI hängt komplett
- Keine Progress-Bar
- Keine Reaktion auf Klicks

### 4.3 Prüfen ob st.rerun() während Simulation

**Test:**
1. Starten Sie Simulation
2. Während Simulation läuft: Fügen Sie ein Szenario hinzu
3. Beobachten Sie Verhalten

**Erwartetes Verhalten:**
- Szenario wird gespeichert
- `st.rerun()` wird aufgerufen
- Simulation läuft weiter oder wird neu gestartet

**Tatsächliches Verhalten (wenn Problem vorhanden):**
- UI hängt
- Simulation läuft nicht weiter
- Keine Reaktion

---

## 🔍 Schritt 5: Code-Stellen prüfen (Reihenfolge)

### 5.1 Szenario hinzufügen (Wasserschaden)
**Datei:** `ui/scenario_sidebar.py`
**Zeilen:** 338-371

**Was passiert:**
1. Szenario wird erstellt
2. Szenario wird zu `scenario_manager` hinzugefügt
3. **ALLE Caches werden invalidiert** (Zeile 350-368)
4. `st.rerun()` wird aufgerufen (Zeile 371)

**Problem:** Cache-Invalidierung + `st.rerun()` könnte während laufender Simulation problematisch sein

### 5.2 Cache-Invalidierung
**Datei:** `ui/scenario_sidebar.py`
**Zeilen:** 350-368

**Was wird invalidiert:**
- `volume_planning_calculated` → False
- `volume_planning_cache_key` → None
- `saddle_logs_cache` → gelöscht
- `material_inventory_data` → gelöscht
- `material_inventory_cache_key` → gelöscht
- `production_logs_cache` → gelöscht
- `production_logs_cache_key` → gelöscht
- `_supplier_log_cache` → {} (leer)
- `_inbound_df_cache` → {} (leer)
- `_inbound_df_cache_key` → None

**Auswirkung:** Alle Berechnungen müssen neu durchgeführt werden

### 5.3 Simulation starten
**Datei:** `ui/utils.py`
**Zeilen:** 114-137

**Was passiert:**
1. Prüft ob Simulation läuft
2. Wenn ja: Zeigt Progress + `st.stop()`
3. Wenn nein: Startet Simulation

**Problem:** Wenn `st.rerun()` während Simulation aufgerufen wird, könnte das zu Problemen führen

### 5.4 Berechnungen nach Cache-Invalidierung
**Datei:** `ui/page_initialization.py`
**Zeilen:** 14-54

**Was passiert:**
1. Parameter-Validierung
2. `calculate_volume_planning_demand()`
3. `run_happy_path_simulation()`
4. Iterative Berechnung (Production + Material)

**Problem:** Diese Berechnungen können sehr lange dauern (30-60 Sekunden)

---

## ✅ Schritt 6: Lösung prüfen

### 6.1 Prüfen ob Fix implementiert wurde

**Gesuchte Änderungen:**
1. `st.rerun()` sollte NICHT während laufender Simulation aufgerufen werden
2. Cache-Invalidierung sollte nur bei Bedarf erfolgen
3. Progress-Indikator sollte während Neuberechnungen angezeigt werden

**Wo prüfen:**
```bash
# Prüfe ob st.rerun() nach Simulation-Check kommt
grep -A 5 -B 5 "simulation_running" ui/scenario_sidebar.py
```

### 6.2 Empfohlene Fixes

**Fix 1: Prüfe Simulation-Status vor st.rerun()**
```python
# Vor st.rerun() prüfen:
if not st.session_state.get('simulation_running', False):
    st.rerun()
else:
    # Zeige Info statt rerun
    st.info("Simulation läuft. Änderungen werden nach Abschluss übernommen.")
```

**Fix 2: Defer Cache-Invalidierung**
```python
# Statt sofortiger Invalidierung:
# Markiere für Invalidierung nach Simulation
st.session_state.pending_cache_invalidation = True
```

**Fix 3: Progress-Indikator während Neuberechnung**
```python
# Zeige Progress während Neuberechnung
with st.spinner("Neuberechnung läuft..."):
    # Berechnungen
```

---

## 📊 Schritt 7: Zusammenfassung

### Was wurde geändert:
1. ✅ Wasserschaden-Szenarien unterstützen jetzt `affected_saddles`
2. ✅ UI für Wasserschaden-Szenarien verbessert
3. ✅ Cache-Keys erweitert um Szenarien zu berücksichtigen

### Mögliche Probleme:
1. ⚠️ Cache-Invalidierung führt zu teuren Neuberechnungen
2. ⚠️ `st.rerun()` könnte während laufender Simulation aufgerufen werden
3. ⚠️ UI könnte während Neuberechnungen hängen

### Nächste Schritte:
1. Prüfen Sie ob Problem reproduzierbar ist
2. Prüfen Sie Browser-Konsole auf Fehler
3. Prüfen Sie ob Simulation läuft wenn Problem auftritt
4. Implementieren Sie Fixes falls nötig
