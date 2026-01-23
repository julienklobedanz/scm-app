# Lösung: Inbound-Tabelle berücksichtigt Marketing-Szenarien

**Datum:** 2026-01-23  
**Problem:** Marketing-Szenarien haben keine Auswirkung auf Inbound-Tabelle  
**Lösung:** Hybrid-Ansatz mit automatischem Neustart der Simulation bei Szenario-Änderungen

---

## 🎯 Lösungsansatz: Hybrid-Ansatz

### **Prinzip:**

1. **Cache-Key erweitern:** Inbound-Tabelle-Cache berücksichtigt Szenarien (wie bei Supplier-Log)
2. **Szenario-Konsistenz prüfen:** Prüfe, ob Simulation mit aktuellen Szenarien konsistent ist
3. **Automatischer Neustart:** Wenn nicht konsistent → Simulation automatisch neu starten
4. **Expliziter Aufruf:** `calculate_volume_planning_demand()` wird explizit aufgerufen (wie bei Lieferant China)

---

## 📋 Konkrete Umsetzung

### **Schritt 1: Cache-Key in `get_inbound_log_dataframe()` erweitern**

**Aktuell:**
```python
# Zeilen 881-884
cache_key = tuple(sorted(saddle_shares_dict.items()))
if cache_key == self._inbound_df_cache_key and cache_key in self._inbound_df_cache:
    return self._inbound_df_cache[cache_key]
```

**Optimal:**
```python
# Erweitere Cache-Key um Szenarien und volume_planning_cache_key
try:
    import streamlit as st
    # Hole Szenario-Fingerprint (ähnlich wie bei Supplier-Log)
    scenario_manager = getattr(self, 'scenario_manager', None)
    if scenario_manager:
        # ... Szenario-Fingerprint-Berechnung (wie bei Supplier-Log) ...
        scenario_fingerprint = tuple(sorted(scenario_items))
    else:
        scenario_fingerprint = ()
    
    # Hole Cache-Key für daily_demands_actual
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    
    # Erweitere Cache-Key
    cache_key = (tuple(sorted(saddle_shares_dict.items())), scenario_fingerprint, volume_planning_cache_key)
except (ImportError, AttributeError):
    # Fallback: Einfacher Key
    cache_key = tuple(sorted(saddle_shares_dict.items()))
```

**Vorteile:**
- ✅ Cache wird invalidiert, wenn Szenarien sich ändern
- ✅ Cache wird invalidiert, wenn `daily_demands_actual` neu berechnet wird
- ✅ Konsistenz mit Supplier-Log

---

### **Schritt 2: Szenario-Konsistenz in `run_happy_path_simulation()` prüfen**

**Aktuell:**
```python
# Zeilen 79-90
if planning_year in simulation_cache:
    cached_data = simulation_cache[planning_year]
    if cached_data.get('results_df') is not None:
        # Lade aus Cache
        return  # KEINE Prüfung auf Szenarien-Konsistenz!
```

**Optimal:**
```python
# Prüfe ob Simulation für das aktuelle Jahr bereits im Cache ist
if planning_year in simulation_cache:
    cached_data = simulation_cache[planning_year]
    if cached_data.get('results_df') is not None:
        # WICHTIG: Prüfe Szenario-Konsistenz
        # Hole aktuellen Szenario-Fingerprint
        scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
        current_scenario_fingerprint = _get_scenario_fingerprint(scenario_manager)
        
        # Hole gespeicherten Szenario-Fingerprint aus Cache
        cached_scenario_fingerprint = cached_data.get('scenario_fingerprint', None)
        
        # Wenn Szenarien sich geändert haben, muss Simulation neu gestartet werden
        if cached_scenario_fingerprint != current_scenario_fingerprint:
            # Szenarien haben sich geändert → Cache invalidieren
            st.session_state.happy_path_run = False
            st.session_state.results_df = None
            # Setze Flag für Neustart
            st.session_state.simulation_needs_restart = True
            # Fahre fort mit neuer Simulation
        else:
            # Szenarien unverändert → Lade aus Cache
            st.session_state.results_df = cached_data['results_df']
            st.session_state.kpis = cached_data.get('kpis')
            st.session_state.simulator = cached_data.get('simulator')
            st.session_state.happy_path_run = True
            return
```

**Vorteile:**
- ✅ Simulation wird automatisch neu gestartet, wenn Szenarien sich ändern
- ✅ Keine manuelle Aktion nötig
- ✅ Konsistenz garantiert

---

### **Schritt 3: Szenario-Fingerprint in Simulation-Cache speichern**

**Optimal:**
```python
# Nach erfolgreicher Simulation (Zeilen 184-188)
st.session_state.simulation_cache[planning_year] = {
    'results_df': results_df,
    'kpis': kpis,
    'simulator': simulator,
    'scenario_fingerprint': current_scenario_fingerprint  # NEU: Speichere Szenario-Fingerprint
}
```

**Vorteile:**
- ✅ Kann später geprüft werden, ob Simulation konsistent ist
- ✅ Ermöglicht automatische Invalidierung

---

### **Schritt 4: Expliziter Aufruf von `calculate_volume_planning_demand()`**

**Optimal:**
```python
# In pages/4_inbound.py (wie bei Lieferant China)
from ui.volume_planning_utils import calculate_volume_planning_demand

# WICHTIG: Stelle sicher, dass daily_demands_actual aktualisiert wird
calculate_volume_planning_demand()

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
run_happy_path_simulation()
```

**Vorteile:**
- ✅ `daily_demands_actual` wird aktualisiert (mit Marketing)
- ✅ `volume_planning_cache_key` wird gesetzt
- ✅ Konsistenz mit anderen Seiten

---

## 🔄 Automatischer Neustart: Ablauf

### **Wenn Marketing-Szenario hinzugefügt wird:**

1. **Szenario wird hinzugefügt:**
   ```python
   # ui/scenario_sidebar.py
   st.session_state.scenario_manager.add_scenario(scenario)
   st.rerun()  # Seite lädt neu
   ```

2. **Seite lädt neu:**
   ```python
   # pages/4_inbound.py
   calculate_volume_planning_demand()  # daily_demands_actual wird neu berechnet (mit Marketing)
   run_happy_path_simulation()  # Prüft Szenario-Konsistenz
   ```

3. **Szenario-Konsistenz wird geprüft:**
   ```python
   # ui/utils.py
   if cached_scenario_fingerprint != current_scenario_fingerprint:
       # Szenarien haben sich geändert → Simulation muss neu gestartet werden
       st.session_state.simulation_needs_restart = True
       # Fahre fort mit neuer Simulation
   ```

4. **Simulation wird neu gestartet:**
   - Progress-Indikator wird angezeigt
   - Simulation läuft mit neuen Szenarien
   - `transport_status` wird mit neuen Bestellungen (mit Marketing) befüllt

5. **Inbound-Tabelle wird angezeigt:**
   - `get_inbound_log_dataframe()` liest aus `transport_status`
   - `transport_status` enthält jetzt neue Bestellungen (mit Marketing)
   - **Ergebnis:** Marketing hat Auswirkung!

---

## ⚠️ Performance-Überlegungen

### **Problem:**
- Simulation dauert ~60 Sekunden
- Automatischer Neustart bedeutet: Benutzer muss warten

### **Lösung:**
1. **Progress-Indikator:** Zeigt Fortschritt während Simulation läuft
2. **Hintergrund-Info:** Erkläre, warum Simulation neu gestartet wird
3. **Optional:** Warnung anzeigen, wenn Simulation neu gestartet wird

---

## 📊 Vergleich: Vorher vs. Nachher

### **Vorher:**

| Schritt | Marketing hinzugefügt | Ergebnis |
|---------|----------------------|----------|
| 1. `daily_demands_actual` | ✅ Wird neu berechnet (mit Marketing) | ✅ Korrekt |
| 2. Simulation | ❌ Wird **nicht** neu gestartet | ❌ `transport_status` bleibt alt |
| 3. Inbound-Tabelle | ❌ Liest aus `transport_status` (alt) | ❌ Marketing hat keine Auswirkung |

### **Nachher:**

| Schritt | Marketing hinzugefügt | Ergebnis |
|---------|----------------------|----------|
| 1. `daily_demands_actual` | ✅ Wird neu berechnet (mit Marketing) | ✅ Korrekt |
| 2. Szenario-Konsistenz | ✅ Wird geprüft | ✅ Erkennt Änderung |
| 3. Simulation | ✅ Wird **automatisch** neu gestartet | ✅ `transport_status` wird aktualisiert |
| 4. Inbound-Tabelle | ✅ Liest aus `transport_status` (neu) | ✅ Marketing hat Auswirkung |

---

## 🎯 Empfohlene Implementierung

### **Priorität 1: Szenario-Konsistenz-Prüfung**

**Datei:** `ui/utils.py`  
**Funktion:** `run_happy_path_simulation()`

**Änderungen:**
1. Helper-Funktion `_get_scenario_fingerprint()` erstellen (ähnlich wie in `volume_planning_utils.py`)
2. Szenario-Fingerprint in Simulation-Cache speichern
3. Szenario-Konsistenz prüfen → wenn nicht konsistent, Simulation neu starten

**Vorteile:**
- ✅ Funktioniert für **alle** Szenarien (nicht nur Marketing)
- ✅ Automatisch, keine manuelle Aktion nötig
- ✅ Konsistenz garantiert

---

### **Priorität 2: Cache-Key erweitern**

**Datei:** `simulation/china_transport.py`  
**Funktion:** `get_inbound_log_dataframe()`

**Änderungen:**
1. Cache-Key erweitern (um Szenarien und `volume_planning_cache_key`)
2. Konsistenz mit Supplier-Log

**Vorteile:**
- ✅ Cache wird korrekt invalidiert
- ✅ Konsistenz mit anderen Tabellen

---

### **Priorität 3: Expliziter Aufruf**

**Datei:** `pages/4_inbound.py`

**Änderungen:**
1. `calculate_volume_planning_demand()` explizit aufrufen (wie bei Lieferant China)

**Vorteile:**
- ✅ `daily_demands_actual` wird aktualisiert
- ✅ Konsistenz mit anderen Seiten

---

## 📋 Zusammenfassung

### **Empfohlener Ansatz:**

**Hybrid-Ansatz mit automatischem Neustart:**
1. ✅ Cache-Key erweitern (um Szenarien)
2. ✅ Szenario-Konsistenz prüfen (in `run_happy_path_simulation()`)
3. ✅ Automatischer Neustart (wenn Szenarien sich geändert haben)
4. ✅ Expliziter Aufruf von `calculate_volume_planning_demand()`

**Vorteile:**
- ✅ Funktioniert automatisch (keine manuelle Aktion nötig)
- ✅ Funktioniert für **alle** Szenarien (nicht nur Marketing)
- ✅ Konsistenz garantiert
- ✅ Benutzer wird informiert (Progress-Indikator)

**Nachteile:**
- ⚠️ Performance: Simulation dauert ~60 Sekunden
- ⚠️ Benutzer muss warten (aber mit Progress-Indikator)

---

**Die vollständige Lösungsstrategie wurde in `INBOUND_MARKETING_LOESUNG.md` gespeichert.**
