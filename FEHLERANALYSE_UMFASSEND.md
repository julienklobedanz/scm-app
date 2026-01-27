# Umfassende Fehleranalyse - SCM App

**Datum:** 27.01.2026  
**Analysemethode:** Von hinten nach vorne, systematische Code-Analyse  
**Ziel:** Identifikation aller Fehler, Inkonsistenzen und Edge Cases

---

## Inhaltsverzeichnis

1. [Kritische Parameter-Inkonsistenzen](#1-kritische-parameter-inkonsistenzen)
2. [Cache-Invalidierungsprobleme](#2-cache-invalidierungsprobleme)
3. [Zirkuläre Abhängigkeiten](#3-zirkuläre-abhängigkeiten)
4. [Fehlerbehandlung und Edge Cases](#4-fehlerbehandlung-und-edge-cases)
5. [Datenkonsistenz-Probleme](#5-datenkonsistenz-probleme)
6. [Performance und Race Conditions](#6-performance-und-race-conditions)
7. [Validierungsprobleme](#7-validierungsprobleme)
8. [Testfälle](#8-testfälle)

---

## 1. Kritische Parameter-Inkonsistenzen

### 1.1 `yearly_volume` vs `total_volume` Inkonsistenz

**Problem:** Zwei verschiedene Parameter für dasselbe Konzept

**Betroffene Stellen:**
- `st.session_state.yearly_volume` (Standard: 370000) - wird verwendet für:
  - `DemandCalculator.__init__()`
  - `Simulator.__init__()`
  - `calculate_volume_planning_demand()`
  - Cache-Key-Generierung

- `MasterData.GLOBAL_CONFIG['total_volume']` (Standard: 370000) - wird verwendet für:
  - `ProductionPlanner.plan_daily_production()` (Fallback, Zeile 124)
  - `pages/8_stammdaten.py` (editierbar)

- `st.session_state.editable_global_config['total_volume']` - wird NICHT synchronisiert mit `yearly_volume`

**Fehler:**
1. Wenn `editable_global_config['total_volume']` geändert wird, wird `yearly_volume` NICHT aktualisiert
2. `ProductionPlanner` verwendet `GLOBAL_CONFIG.get('total_volume', 370000)` als Fallback, aber sollte `yearly_volume` verwenden
3. Cache wird nicht invalidiert wenn `editable_global_config['total_volume']` geändert wird

**Auswirkung:**
- Inkonsistente Berechnungen zwischen Volumenplanung und Produktion
- Cache zeigt veraltete Werte
- Unterschiedliche Ergebnisse je nachdem welche Quelle verwendet wird

**Schweregrad:** 🔴 KRITISCH

---

### 1.2 `GLOBAL_CONFIG` wird nicht aktualisiert wenn `editable_global_config` geändert wird

**Problem:** 
- `pages/8_stammdaten.py` Zeile 38: `editable_global_config = MasterData.GLOBAL_CONFIG.copy()`
- Änderungen werden nur in `st.session_state.editable_global_config` gespeichert
- `MasterData.GLOBAL_CONFIG` bleibt unverändert
- Code verwendet `MasterData.GLOBAL_CONFIG` direkt (z.B. `production_planner.py` Zeile 137-138)

**Betroffene Parameter:**
- `capacity_per_hour` (Standard: 130)
- `working_hours_per_shift` (Standard: 8)
- `assembly_lines` (Standard: 1)
- `min_shifts_per_day` / `max_shifts_per_day` (Standard: 1/3)
- `batch_size` (Standard: 1)

**Fehler:**
- Änderungen in Stammdaten-Seite haben keine Auswirkung auf Berechnungen
- Code liest immer aus `MasterData.GLOBAL_CONFIG`, nicht aus `editable_global_config`

**Auswirkung:**
- Benutzer ändert Parameter → keine Auswirkung
- Inkonsistente Werte zwischen UI und Berechnung

**Schweregrad:** 🔴 KRITISCH

---

### 1.3 `PRODUCT_SALES_SHARES` Inkonsistenz

**Problem:**
- `MasterData.PRODUCT_SALES_SHARES` wird direkt verwendet
- `st.session_state.editable_product_sales_shares` wird in `pages/8_stammdaten.py` erstellt
- Änderungen werden NICHT zurück in `MasterData.PRODUCT_SALES_SHARES` geschrieben
- Code verwendet `MasterData.PRODUCT_SALES_SHARES` direkt

**Betroffene Stellen:**
- `DemandCalculator` verwendet `MasterData.PRODUCT_SALES_SHARES`
- `calculate_saddle_shares()` verwendet `MasterData.PRODUCT_SALES_SHARES`
- Alle Berechnungen verwenden statische Werte

**Fehler:**
- Änderungen in Stammdaten haben keine Auswirkung
- Summe der Shares könnte != 1.0 sein (keine Validierung)

**Auswirkung:**
- Inkonsistente Nachfrage-Berechnungen
- Falsche Sattel-Anteile

**Schweregrad:** 🔴 KRITISCH

---

### 1.4 `DAILY_WORKLOAD` Inkonsistenz

**Problem:**
- `MasterData.DAILY_WORKLOAD` wird direkt verwendet
- `st.session_state.editable_daily_workload` wird erstellt
- Änderungen werden NICHT zurückgeschrieben
- Code verwendet `MasterData.DAILY_WORKLOAD` direkt (`workday_calculator.py` Zeile 83)

**Fehler:**
- Änderungen haben keine Auswirkung
- Keine Validierung dass Summe = 1.0

**Schweregrad:** 🟡 MITTEL

---

### 1.5 `BOM` Inkonsistenz

**Problem:**
- `MasterData.BOM` wird direkt verwendet
- `st.session_state.editable_bom` wird erstellt
- Änderungen werden NICHT zurückgeschrieben
- Code verwendet `MasterData.BOM` direkt überall

**Fehler:**
- Änderungen haben keine Auswirkung
- Keine Validierung dass alle Komponenten existieren

**Schweregrad:** 🟡 MITTEL

---

## 2. Cache-Invalidierungsprobleme

### 2.1 Cache wird nicht invalidiert bei Parameteränderungen

**Problem:**
- Wenn `yearly_volume` geändert wird, wird Cache nicht invalidiert
- Wenn `editable_global_config` geändert wird, wird Cache nicht invalidiert
- Wenn `editable_product_sales_shares` geändert wird, wird Cache nicht invalidiert

**Betroffene Caches:**
- `volume_planning_cache_key` - sollte invalidiert werden
- `production_logs_cache` - sollte invalidiert werden
- `material_inventory_data` - sollte invalidiert werden
- `simulation_cache` - sollte invalidiert werden

**Fehler:**
- Alte Werte werden weiterhin verwendet
- Inkonsistente Berechnungen

**Schweregrad:** 🔴 KRITISCH

---

### 2.2 `simulation_cache` ist nicht abhängig von Parametern

**Problem:**
- `simulation_cache` wird nur nach Jahr unterschieden
- Änderungen von `yearly_volume`, `GLOBAL_CONFIG`, etc. werden nicht berücksichtigt
- Cache wird nicht invalidiert wenn Parameter geändert werden

**Fehler:**
- Falsche Simulationsergebnisse bei Parameteränderungen
- Cache zeigt veraltete Werte

**Schweregrad:** 🔴 KRITISCH

---

### 2.3 Cache-Invalidierung während Iteration

**Problem:**
- `calculate_production_logs()` löscht `material_inventory_data` nach Berechnung (Zeile 658)
- Aber Iteration läuft noch → Race Condition möglich
- Cache könnte während Berechnung gelöscht werden

**Schweregrad:** 🟡 MITTEL

---

## 3. Zirkuläre Abhängigkeiten

### 3.1 Production ↔ Material Zirkelbezug ohne Konvergenz-Check

**Problem:**
- Genau 2 Iterationen werden durchgeführt (`page_initialization.py` Zeile 39-63)
- Kein Check ob Werte konvergiert sind
- Werte könnten oszillieren

**Fehler:**
- Nicht-deterministische Ergebnisse
- Unterschiedliche Werte bei Neuladen (z.B. 1799 vs 1760 für Extreme)

**Schweregrad:** 🔴 KRITISCH

---

### 3.2 Nicht-deterministische Produktreihenfolge

**Problem:**
- `MasterData.BOM.keys()` wird verwendet ohne Sortierung
- Python-Dict-Reihenfolge ist zwar stabil (ab 3.7), aber nicht garantiert deterministisch
- Rang-Berechnung hängt von Reihenfolge ab

**Betroffene Stellen:**
- `ui/production_calculations.py` Zeile 118: `products_list = list(MasterData.BOM.keys())`
- `ui/production_calculations.py` Zeile 358, 409, 492, 516: `for product in MasterData.BOM.keys():`
- `simulation/production_planner.py` verwendet auch `BOM.keys()`

**Fehler:**
- Unterschiedliche Rang-Berechnungen bei unterschiedlicher Reihenfolge
- Nicht-deterministische Produktionsmengen

**Schweregrad:** 🔴 KRITISCH

---

### 3.3 Backlog-Berechnung hängt von bereits berechneten Werten ab

**Problem:**
- Backlog wird basierend auf vorherigen Tagen berechnet
- Wenn Reihenfolge variiert, können unterschiedliche Backlogs entstehen
- `calculated_backlogs` Dictionary könnte inkonsistent sein

**Schweregrad:** 🟡 MITTEL

---

## 4. Fehlerbehandlung und Edge Cases

### 4.1 Division durch Null

**Potentielle Stellen:**

1. **`demand_calculator.py` Zeile 70:**
   ```python
   base_daily_float[product] = monthly_target_product / num_workdays
   ```
   - `num_workdays` könnte 0 sein (Zeile 54-56: Fallback auf 1, aber unsicher)

2. **`production_calculations.py` Zeile 116:**
   ```python
   total_production_demand = sum(production_demand_by_product.values())
   proportional = math.floor(demand * daily_capacity / total_production_demand)
   ```
   - `total_production_demand` könnte 0 sein → Division durch Null

3. **`production_calculations.py` Zeile 122:**
   ```python
   if total_production_demand > 0:
       proportional = math.floor(demand * daily_capacity / total_production_demand)
   ```
   - Prüfung vorhanden, aber `daily_capacity` könnte 0 sein

4. **`volume_planning_utils.py` Zeile 186:**
   ```python
   target_sum = int(yearly_volume * sales_share)
   ```
   - `yearly_volume` könnte 0 sein (keine Prüfung)

5. **`material_calculations.py`:**
   - Verschiedene Divisionen ohne Prüfung auf 0

**Schweregrad:** 🔴 KRITISCH

---

### 4.2 Index Out of Bounds

**Potentielle Stellen:**

1. **`production_calculations.py` Zeile 256:**
   ```python
   if logs and day < len(logs):
       log_entry = logs[day]
   ```
   - Prüfung vorhanden, aber `logs[day]` könnte fehlschlagen wenn `logs` nicht sequenziell ist

2. **`china_transport.py`:**
   - Zugriff auf `transport_status` ohne Prüfung ob Key existiert
   - Zugriff auf DataFrame-Indizes ohne Prüfung

3. **`workday_calculator.py` Zeile 36:**
   ```python
   return start_date + timedelta(days=day)
   ```
   - `day` könnte negativ sein oder > 365 (wird nicht geprüft)

**Schweregrad:** 🟡 MITTEL

---

### 4.3 None-Checks fehlen

**Potentielle Stellen:**

1. **`simulator.py`:**
   - `daily_demands_actual` könnte None sein (Zeile 159)
   - Prüfung vorhanden, aber nicht überall konsistent

2. **`china_transport.py`:**
   - Viele `Optional` Typen, aber nicht alle None-Checks vorhanden
   - `scenario_manager` könnte None sein

3. **`production_calculations.py`:**
   - `material_inventory_data` könnte None sein
   - `production_logs_cache` könnte None sein

**Schweregrad:** 🟡 MITTEL

---

### 4.4 Leere Collections

**Potentielle Stellen:**

1. **`production_calculations.py`:**
   - `production_logs` könnte leer sein
   - `days_to_update` könnte leer sein
   - Prüfungen vorhanden, aber nicht überall

2. **`material_calculations.py`:**
   - `inbound_df` könnte leer sein
   - `production_logs_cache` könnte leer sein

**Schweregrad:** 🟢 NIEDRIG

---

## 5. Datenkonsistenz-Probleme

### 5.1 `yearly_volume` wird nicht aus `editable_global_config` synchronisiert

**Problem:**
- `pages/8_stammdaten.py` erlaubt Änderung von `total_volume`
- Aber `yearly_volume` wird nicht aktualisiert
- Cache wird nicht invalidiert

**Fehler:**
- Inkonsistente Werte
- Falsche Berechnungen

**Schweregrad:** 🔴 KRITISCH

---

### 5.2 Materialverbrauch vs Produktionsmenge Inkonsistenz

**Problem:**
- `material_verbrauch` wird in `production_logs_cache` gespeichert
- Aber könnte von `tatsächliche PM` abweichen
- Materiallager verwendet `material_verbrauch`, aber Produktion könnte anders sein

**Schweregrad:** 🟡 MITTEL

---

### 5.3 Inbound-Tabelle vs Simulation Inkonsistenz

**Problem:**
- `get_inbound_log_dataframe()` berechnet Daten dynamisch
- `simulator.run()` verwendet `get_daily_arrival_qty()`
- Könnten unterschiedliche Werte liefern

**Schweregrad:** 🟡 MITTEL

---

## 6. Performance und Race Conditions

### 6.1 Nicht-deterministische Dictionary-Iteration

**Problem:**
- `MasterData.BOM.keys()` ohne Sortierung
- `MasterData.PRODUCT_SALES_SHARES.keys()` ohne Sortierung
- Könnte zu unterschiedlichen Ergebnissen führen

**Schweregrad:** 🔴 KRITISCH

---

### 6.2 Cache wird während Berechnung gelöscht

**Problem:**
- `calculate_production_logs()` löscht `material_inventory_data` während Iteration
- Könnte zu Race Conditions führen

**Schweregrad:** 🟡 MITTEL

---

### 6.3 Exception-Handling zu breit

**Problem:**
- `page_initialization.py` Zeile 42, 49, 62: `except Exception: pass`
- Fehler werden stillschweigend ignoriert
- Schwer zu debuggen

**Schweregrad:** 🟡 MITTEL

---

## 7. Validierungsprobleme

### 7.1 Keine Validierung für `PRODUCT_SALES_SHARES` Summe

**Problem:**
- Summe sollte = 1.0 sein
- Keine Prüfung vorhanden
- Falsche Berechnungen wenn Summe != 1.0

**Schweregrad:** 🟡 MITTEL

---

### 7.2 Keine Validierung für `DAILY_WORKLOAD` Summe

**Problem:**
- Summe sollte = 1.0 sein (für Mo-Fr)
- Keine Prüfung vorhanden

**Schweregrad:** 🟢 NIEDRIG

---

### 7.3 Keine Validierung für `SEASONALITY` Summe

**Problem:**
- Summe sollte = 1.0 sein
- Keine Prüfung vorhanden

**Schweregrad:** 🟡 MITTEL

---

### 7.4 Keine Validierung für Parameter-Bereiche

**Problem:**
- `yearly_volume` könnte negativ sein
- `capacity_per_hour` könnte 0 sein
- `max_shifts_per_day` könnte < `min_shifts_per_day` sein
- Keine Validierung vorhanden

**Schweregrad:** 🟡 MITTEL

---

## 8. Testfälle

### 8.1 Parameter-Konsistenz Tests

```python
def test_yearly_volume_sync():
    """Test: yearly_volume sollte mit total_volume synchronisiert sein"""
    # Ändere total_volume in editable_global_config
    # Prüfe ob yearly_volume aktualisiert wird
    # Prüfe ob Cache invalidiert wird
    pass

def test_parameter_change_invalidates_cache():
    """Test: Parameteränderungen sollten Cache invalidierten"""
    # Ändere yearly_volume
    # Prüfe ob alle relevanten Caches gelöscht werden
    pass

def test_global_config_usage():
    """Test: Code sollte editable_global_config verwenden, nicht GLOBAL_CONFIG"""
    # Ändere editable_global_config
    # Prüfe ob Berechnungen neue Werte verwenden
    pass
```

---

### 8.2 Zirkuläre Abhängigkeit Tests

```python
def test_production_material_convergence():
    """Test: Production und Material sollten konvergieren"""
    # Führe mehrere Iterationen durch
    # Prüfe ob Werte stabil werden
    # Prüfe ob Konvergenz erreicht wird
    pass

def test_deterministic_calculation():
    """Test: Berechnungen sollten deterministisch sein"""
    # Führe Berechnung 10x durch
    # Prüfe ob alle Ergebnisse identisch sind
    pass

def test_product_order_stability():
    """Test: Produktreihenfolge sollte stabil sein"""
    # Prüfe ob sorted() verwendet wird
    # Prüfe ob Rang-Berechnung konsistent ist
    pass
```

---

### 8.3 Edge Case Tests

```python
def test_zero_yearly_volume():
    """Test: yearly_volume = 0 sollte nicht zu Division durch Null führen"""
    pass

def test_zero_capacity():
    """Test: capacity_per_hour = 0 sollte behandelt werden"""
    pass

def test_empty_production_logs():
    """Test: Leere production_logs sollten nicht zu Fehlern führen"""
    pass

def test_negative_days():
    """Test: Negative Tage sollten behandelt werden"""
    pass

def test_year_boundary():
    """Test: Tage > 365 sollten behandelt werden"""
    pass
```

---

### 8.4 Robustheit Tests

```python
def test_extreme_parameter_values():
    """Test: Extreme Parameterwerte sollten funktionieren"""
    # yearly_volume = 1000000
    # capacity_per_hour = 500
    # Prüfe ob System stabil bleibt
    pass

def test_multiple_scenario_combinations():
    """Test: Mehrere Szenarien gleichzeitig"""
    # Marketing + Wasserschaden + Verspätung
    # Prüfe ob alle korrekt angewendet werden
    pass

def test_cache_resilience():
    """Test: Cache sollte bei Fehlern resilient sein"""
    # Simuliere Cache-Korruption
    # Prüfe ob System sich erholt
    pass
```

---

## Zusammenfassung: Kritische Fehler

### 🔴 KRITISCH (Sofort beheben)

1. **Parameter-Inkonsistenz:** `yearly_volume` vs `total_volume` nicht synchronisiert
2. **Cache-Invalidierung:** Parameteränderungen invalidierten Cache nicht
3. **Zirkuläre Abhängigkeit:** Kein Konvergenz-Check, nicht-deterministisch
4. **Produktreihenfolge:** Nicht stabilisiert, führt zu unterschiedlichen Ergebnissen
5. **Division durch Null:** Mehrere Stellen ohne Prüfung

### 🟡 MITTEL (Bald beheben)

1. **GLOBAL_CONFIG:** Wird nicht aus editable_global_config aktualisiert
2. **Exception-Handling:** Zu breit, Fehler werden ignoriert
3. **Validierung:** Fehlt für viele Parameter
4. **None-Checks:** Nicht überall vorhanden

### 🟢 NIEDRIG (Verbesserung)

1. **Code-Duplikation:** Ähnliche Logik mehrfach vorhanden
2. **Dokumentation:** Fehlt an einigen Stellen
3. **Performance:** Könnte optimiert werden

---

## Nächste Schritte

1. **Sofort:** Parameter-Synchronisation implementieren
2. **Sofort:** Cache-Invalidierung bei Parameteränderungen
3. **Sofort:** Konvergenz-Check für iterative Berechnung
4. **Sofort:** Produktreihenfolge stabilisieren
5. **Bald:** Division-durch-Null-Prüfungen hinzufügen
6. **Bald:** Validierung für alle Parameter
7. **Später:** Exception-Handling verbessern
