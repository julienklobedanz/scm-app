# Cache-Verfügbarkeit Analyse

## Frage: Wie realistisch ist es, dass der Cache fehlt?

## 1. Aufruf-Reihenfolge von `calculate_volume_planning_demand()`

### ✅ Garantierte Aufrufe (immer vor Verwendung):

1. **`app.py` → `run_happy_path_simulation()` (Zeile 146)**
   - Wird beim App-Start ausgeführt
   - Wird VOR der Simulation aufgerufen
   - **Garantie:** Cache ist vorhanden, bevor Simulator läuft

2. **Jede Page ruft `calculate_volume_planning_demand()` auf:**
   - `pages/2_volumenplanung.py` (Zeile 55)
   - `pages/3_lieferant_china.py` (Zeile 55)
   - `pages/4_inbound.py` (Zeile 55)
   - `pages/5_materiallager.py` (Zeile 51, 377)
   - `pages/6_produktion.py` (Zeile 50)
   - **Garantie:** Cache ist vorhanden, bevor Page-Daten verwendet werden

3. **`calculate_volume_planning_demand()` selbst prüft Cache:**
   ```python
   if st.session_state.get('volume_planning_calculated', False) and cached_key == cache_key:
       daily_demands_planned = st.session_state.get('daily_demands_planned', {})
       daily_demands_actual = st.session_state.get('daily_demands_actual', {})
       if daily_demands_planned and daily_demands_actual and len(daily_demands_planned) == 365:
           return daily_demands_planned, daily_demands_actual
   ```
   - **Garantie:** Berechnet nur neu, wenn Cache fehlt oder invalidiert wurde

---

## 2. Wann könnte der Cache fehlen?

### ❌ Unrealistische Szenarien:

1. **`day not in daily_demands_actual`**
   - **Wann:** Tag außerhalb 0-364
   - **Realität:** Simulator iteriert nur über 0-364
   - **Wahrscheinlichkeit:** ~0% (nur bei Programmierfehler)

2. **`daily_demands_actual[day]` ist leer**
   - **Wann:** Tag existiert, aber Dictionary ist leer
   - **Realität:** `calculate_volume_planning_demand()` berechnet ALLE 365 Tage
   - **Wahrscheinlichkeit:** ~0% (nur bei Programmierfehler)

3. **Streamlit nicht verfügbar**
   - **Wann:** `STREAMLIT_AVAILABLE = False`
   - **Realität:** App läuft nur in Streamlit-Umgebung
   - **Wahrscheinlichkeit:** ~0% (nur bei Unit-Tests ohne Streamlit)

4. **Exception beim Zugriff auf `session_state`**
   - **Wann:** Unerwarteter Fehler
   - **Realität:** Sollte Exception werfen, nicht Fallback verwenden
   - **Wahrscheinlichkeit:** <1% (nur bei schwerwiegenden Fehlern)

### ⚠️ Realistische Szenarien (aber selten):

1. **Session State wurde manuell gelöscht**
   - **Wann:** User löscht `st.session_state` manuell
   - **Realität:** Extrem selten, würde App-Reset erfordern
   - **Wahrscheinlichkeit:** <0.1%

2. **Cache-Invalidierung durch Szenario-Änderung**
   - **Wann:** Szenario wird geändert, Cache-Key ändert sich
   - **Realität:** `calculate_volume_planning_demand()` wird neu aufgerufen
   - **Wahrscheinlichkeit:** 0% (Cache wird automatisch neu berechnet)

3. **Jahr-Änderung**
   - **Wann:** `planning_year` ändert sich
   - **Realität:** `calculate_volume_planning_demand()` wird neu aufgerufen
   - **Wahrscheinlichkeit:** 0% (Cache wird automatisch neu berechnet)

---

## 3. Analyse der Fallback-Stellen

### 3.1 `simulation/simulator.py` (Zeile 290-314)

```python
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
if day in daily_demands_actual and daily_demands_actual[day]:
    product_demands = daily_demands_actual[day].copy()
else:
    # FALLBACK: Berechne Nachfrage selbst
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(...)
```

**Analyse:**
- ✅ `run_happy_path_simulation()` ruft `calculate_volume_planning_demand()` VOR `simulator.run()` auf
- ✅ Cache sollte IMMER vorhanden sein
- ❌ **Fallback ist überflüssig!**
- ⚠️ **Problem:** Fallback verwendet `marketing_add_ons`, die möglicherweise nicht mit Volumenplanung übereinstimmen

**Empfehlung:** Fallback entfernen, Exception werfen wenn Cache fehlt

---

### 3.2 `simulation/production_planner.py` (Zeile 100-102)

```python
product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
    day, marketing_add_ons, is_last_workday_of_year
)
```

**Analyse:**
- ❌ **Berechnet IMMER Nachfrage neu, auch wenn Cache vorhanden ist!**
- ❌ **Keine Prüfung auf Cache!**
- ❌ **Definitiv eine Redundanz!**

**Empfehlung:** Sollte `daily_demands_actual` aus `session_state` lesen, nicht neu berechnen

---

### 3.3 `pages/5_materiallager.py` (Zeile 192-231)

```python
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]
else:
    # FALLBACK: Berechne Marketing-Add-ons manuell
    # ... manuelle Berechnung ...
    product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
```

**Analyse:**
- ✅ `calculate_volume_planning_demand()` wird VORHER aufgerufen (Zeile 51)
- ✅ Cache sollte IMMER vorhanden sein
- ❌ **Fallback ist überflüssig!**
- ⚠️ **Problem:** Fallback berechnet Marketing-Add-ons manuell, möglicherweise inkonsistent

**Empfehlung:** Fallback entfernen, Exception werfen wenn Cache fehlt

---

## 4. Zusammenfassung

### ✅ Cache ist praktisch IMMER vorhanden:

1. **Garantierte Aufrufe:**
   - `run_happy_path_simulation()` ruft `calculate_volume_planning_demand()` VOR Simulation auf
   - Jede Page ruft `calculate_volume_planning_demand()` am Anfang auf
   - Funktion prüft selbst, ob Cache vorhanden ist

2. **Cache-Invalidierung:**
   - Wird automatisch erkannt (Cache-Key-Änderung)
   - Wird automatisch neu berechnet
   - Keine manuelle Intervention nötig

3. **Fehlende Cache-Szenarien:**
   - Extrem selten (<0.1%)
   - Meist durch Programmierfehler oder manuelle Session-State-Löschung

### ❌ Fallbacks sind überflüssig:

1. **`simulation/simulator.py`:**
   - Fallback wird praktisch nie erreicht
   - Fallback kann inkonsistente Werte produzieren (Marketing-Add-ons)

2. **`simulation/production_planner.py`:**
   - Berechnet IMMER neu, auch wenn Cache vorhanden ist
   - **Definitiv eine Redundanz!**

3. **`pages/5_materiallager.py`:**
   - Fallback wird praktisch nie erreicht
   - Fallback kann inkonsistente Werte produzieren (manuelle Marketing-Berechnung)

---

## 5. Empfehlungen

### 5.1 Fallbacks entfernen

**Statt Fallback:**
```python
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]
else:
    # FALLBACK: Berechne neu
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(...)
```

**Besser: Exception werfen:**
```python
if day not in daily_demands_actual:
    raise ValueError(f"daily_demands_actual fehlt für Tag {day}. "
                     f"Bitte rufen Sie calculate_volume_planning_demand() auf.")
product_demands = daily_demands_actual[day]
```

**Oder: Assertion:**
```python
assert day in daily_demands_actual, f"daily_demands_actual fehlt für Tag {day}"
product_demands = daily_demands_actual[day]
```

### 5.2 ProductionPlanner umstellen

**Aktuell:**
```python
product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
    day, marketing_add_ons, is_last_workday_of_year
)
```

**Besser: Aus Cache lesen:**
```python
try:
    import streamlit as st
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    if day in daily_demands_actual:
        product_demands = daily_demands_actual[day]
    else:
        raise ValueError(f"daily_demands_actual fehlt für Tag {day}")
except (ImportError, KeyError, ValueError):
    # Nur wenn Streamlit nicht verfügbar (z.B. Unit-Tests)
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
        day, marketing_add_ons, is_last_workday_of_year
    )
```

### 5.3 Vorteile der Änderung

1. **Konsistenz:** Alle Stellen verwenden dieselbe Quelle (SSoT)
2. **Einfachheit:** Keine redundanten Berechnungen
3. **Fehlererkennung:** Fehlende Cache wird sofort erkannt (Exception)
4. **Wartbarkeit:** Weniger Code, weniger Fehlerquellen

---

## 6. Fazit

**Antwort auf die Frage: "Wie realistisch ist es, dass der Cache fehlt?"**

**Praktisch 0%** - Der Cache ist praktisch IMMER vorhanden, weil:
- `calculate_volume_planning_demand()` wird VOR jeder Verwendung aufgerufen
- Die Funktion prüft selbst, ob Cache vorhanden ist
- Cache-Invalidierung wird automatisch erkannt und neu berechnet

**Empfehlung: Fallbacks entfernen!**

Die Fallbacks sind:
1. **Überflüssig** (Cache ist praktisch immer vorhanden)
2. **Gefährlich** (können inkonsistente Werte produzieren)
3. **Redundant** (berechnen Nachfrage neu, obwohl Cache vorhanden ist)

**Besser:** Exception werfen, wenn Cache fehlt. Das macht Fehler sofort sichtbar und zwingt zu korrekter Initialisierung.
