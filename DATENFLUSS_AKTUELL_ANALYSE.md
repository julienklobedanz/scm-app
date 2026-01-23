# Aktueller Datenfluss - Vollständige Analyse

## Übersicht

Dieses Dokument beschreibt den **kompletten Datenfluss** der Anwendung nach allen bisherigen Änderungen, identifiziert **doppelte Berechnungen**, **parallele Aktivitäten** und **potenzielle Inkonsistenzen**.

---

## 1. Datenfluss-Übersicht (High-Level)

```
[User Input / Szenarien]
         ↓
[Volumenplanung] ← Single Source of Truth für Nachfrage
         ↓
[Simulator] ← Verwendet daily_demands_actual
         ↓
[ProductionPlanner] ← Plant Produktion (statisch)
         ↓
[ChinaTransportManager] ← Berechnet Bestellungen & Transport
         ↓
[Pages] ← Dynamische Updates für UI
```

---

## 2. Detaillierter Datenfluss

### 2.1 Nachfrageberechnung (REDUNDANZ!)

#### ✅ Single Source of Truth: `calculate_volume_planning_demand()`
- **Datei:** `ui/volume_planning_utils.py`
- **Aufruf:** 
  - `app.py` (beim Start)
  - `pages/2_volumenplanung.py` (Zeile 55)
  - `pages/3_lieferant_china.py` (Zeile 55)
  - `pages/4_inbound.py` (Zeile 55)
  - `pages/5_materiallager.py` (Zeile 51, 377)
  - `pages/6_produktion.py` (Zeile 50)
- **Output:** 
  - `st.session_state.daily_demands_planned` (ohne Marketing)
  - `st.session_state.daily_demands_actual` (mit Marketing)
- **Cache-Key:** `(planning_year, yearly_volume, scenario_fingerprint)`

#### ⚠️ PROBLEM: Parallele Berechnungen

**1. In `simulation/simulator.py` (Zeile 290-314):**
```python
# Versuche Nachfrage aus Volumenplanung zu holen
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day].copy()
else:
    # FALLBACK: Berechne Nachfrage selbst
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(...)
```
- **Problem:** Fallback berechnet Nachfrage NEU, wenn Cache fehlt
- **Konsequenz:** Inkonsistente Werte, wenn Volumenplanung nicht geladen wurde

**2. In `simulation/production_planner.py` (Zeile 100-102):**
```python
product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
    day, marketing_add_ons, is_last_workday_of_year
)
```
- **Problem:** Berechnet Nachfrage NEU, statt aus `daily_demands_actual` zu lesen
- **Konsequenz:** Mögliche Inkonsistenz mit Volumenplanung

**3. In `pages/5_materiallager.py` (Zeile 192-231):**
```python
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]
else:
    # FALLBACK: Berechne Marketing-Add-ons manuell
    marketing_add_ons = {}
    # ... manuelle Berechnung ...
    product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
```
- **Problem:** Fallback berechnet Nachfrage NEU mit manueller Marketing-Berechnung
- **Konsequenz:** Inkonsistenz, wenn Marketing-Szenarien aktiv sind

**4. In `pages/2_volumenplanung.py` (Zeile 99-154):**
```python
def calculate_product_demand(day: int, product: str, include_marketing: bool = True) -> float:
    # Berechnet Nachfrage für UI-Anzeige
```
- **Problem:** Berechnet Nachfrage NEU für UI, statt aus Cache zu lesen
- **Konsequenz:** Redundanz, aber konsistent (verwendet `calculate_volume_planning_demand()`)

---

### 2.2 Produktionsberechnung (MEHRFACHE REDUNDANZ!)

#### ✅ Statische Quelle: `ProductionPlanner.plan_daily_production()`
- **Datei:** `simulation/production_planner.py`
- **Wann:** Während Simulation (`simulator.run()`)
- **Output:** 
  - `production_by_product` (Dict[product -> quantity])
  - `production_logs` (Dict[product -> List[Dict]]) - statische Logs

#### ⚠️ PROBLEM: Drei parallele Berechnungen der Produktion

**1. In `pages/5_materiallager.py` (Zeile 181-262):**
```python
production_by_product = {}
if 0 <= day < len(results_df):
    actual_build = results_df.iloc[day]['Actual_Build']  # Statisch!
    
    # Berechne Produktionsmengen pro Produkt dynamisch (mit Marketing)
    product_demands = daily_demands_actual[day]  # Aus Volumenplanung
    # ... proportionale Verteilung basierend auf actual_build ...
    production_by_product[product] = allocated
```
- **Problem:** Berechnet Produktion NEU aus `actual_build` (statisch) und `product_demands`
- **Konsequenz:** Kann von statischen `production_logs` abweichen

**2. In `pages/6_produktion.py` (Zeile 132-196):**
```python
# Dynamische Berechnung der "tatsächlichen PM"
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]
    product_demand = product_demands.get(product, 0)
    
    # Berechne "tatsächliche PM" dynamisch:
    # 1. Anteilige Produktion basierend auf Nachfrage
    proportional_pm = int(daily_capacity * proportional_share)
    # 2. Begrenze durch Materialverfügbarkeit
    dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
    df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)
```
- **Problem:** Berechnet "tatsächliche PM" NEU, basierend auf:
  - `daily_demands_actual` (korrekt)
  - `saddle_stock_morning` aus statischen Logs (kann veraltet sein!)
- **Konsequenz:** Inkonsistenz, wenn Materialverfügbarkeit sich geändert hat

**3. In `simulation/production_planner.py` (Zeile 53-330):**
```python
def plan_daily_production(self, day, ...):
    # Berechnet Produktion während Simulation
    # Verwendet: product_demands, Materialverfügbarkeit, Kapazität
    # Output: production_by_product (statisch)
```
- **Problem:** Wird nur einmal während Simulation berechnet
- **Konsequenz:** Kann nicht auf Änderungen in Materialverfügbarkeit reagieren

---

### 2.3 Materialverbrauch (ZIRKULÄRE ABHÄNGIGKEIT!)

#### ⚠️ KRITISCHES PROBLEM: Zirkuläre Abhängigkeit

**1. In `pages/5_materiallager.py` (Zeile 268-293):**
```python
production_by_product_from_logs = {}
if 'production_logs_cache' in st.session_state:
    # Lese "tatsächliche PM" aus production_logs_cache
    actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)
    production_by_product_from_logs[product_name] = int(actual_pm)
else:
    # Fallback: Verwende production_by_product (berechnet aus actual_build)
    production_by_product_from_logs = production_by_product
```
- **Benötigt:** `production_logs_cache` (wird in `pages/6_produktion.py` erstellt)

**2. In `pages/6_produktion.py` (Zeile 130):**
```python
material_inventory_data = st.session_state.get('material_inventory_data', {})
# Wird verwendet für: Sattel-Bestand in dynamischer Berechnung
```
- **Benötigt:** `material_inventory_data` (wird in `pages/5_materiallager.py` erstellt)

**3. Zirkuläre Abhängigkeit:**
```
pages/5_materiallager.py (create_saddle_inventory_log)
    → benötigt production_logs_cache
        → wird in pages/6_produktion.py (get_production_logs) erstellt
            → benötigt material_inventory_data
                → wird in pages/5_materiallager.py (create_saddle_inventory_log) erstellt
                    → ZIRKEL!
```

---

### 2.4 Bestelleingang (REDUNDANZ!)

#### ✅ Quelle: `ChinaTransportManager._calculate_order_quantity_from_volume_planning()`
- **Datei:** `simulation/china_transport.py`
- **Methode:** `get_supplier_log_dataframe()`
- **Berechnung:** Summiert `daily_demands_actual` für alle Produkte mit spezifischem Sattel

#### ⚠️ PROBLEM: Cache-Key-Abhängigkeit
- **Cache-Key:** `_supplier_log_cache` (Zeile ~500)
- **Erweitert um:** `volume_planning_cache_key` (für Szenario-Invalidierung)
- **Problem:** Wenn Cache nicht invalidiert wird, zeigt Tabelle veraltete Werte

---

### 2.5 Inbound (REDUNDANZ!)

#### ✅ Quelle: `ChinaTransportManager.get_inbound_log_dataframe()`
- **Datei:** `simulation/china_transport.py`
- **Berechnung:** 
  - **ALT:** Eigene Berechnung basierend auf `transport_status`
  - **NEU:** Leitet Produktionsmengen dynamisch aus `get_supplier_log_dataframe()` ab

#### ⚠️ PROBLEM: Doppelte Berechnung
- **In `pages/4_inbound.py`:** Ruft `get_inbound_log_dataframe()` auf
- **In `simulation/china_transport.py`:** Berechnet Inbound-Logik
- **In `pages/5_materiallager.py`:** Ruft `get_inbound_log_dataframe()` erneut auf (Zeile 110)
- **Konsequenz:** Mehrfache Berechnung derselben Daten

---

### 2.6 Backlog (REDUNDANZ!)

#### ✅ Quelle: `ProductionPlanner.backlog`
- **Datei:** `simulation/production_planner.py`
- **Berechnung:** `Backlog = geplante PM - fertiggestellte PM + Backlog_vortag` (Zeile 363)

#### ⚠️ PROBLEM: Dynamische Überschreibung
- **In `pages/6_produktion.py` (Zeile 213-282):**
  - Überschreibt Backlog dynamisch basierend auf aktualisierten "fertiggestellten PM"
- **Problem:** Backlog wird ZWEIMAL berechnet:
  1. Statisch in `ProductionPlanner.plan_daily_production()` (während Simulation)
  2. Dynamisch in `pages/6_produktion.py` (für UI)
- **Konsequenz:** Inkonsistenz zwischen statischen und dynamischen Werten

---

## 3. Identifizierte Redundanzen

### 3.1 Nachfrageberechnung (4x)

| Stelle | Methode | Wann | Problem |
|--------|---------|------|---------|
| `ui/volume_planning_utils.py` | `calculate_volume_planning_demand()` | ✅ SSoT | - |
| `simulation/simulator.py` | `demand_calculator.calculate_daily_demand_per_product_dict()` | Fallback | ❌ Inkonsistent |
| `simulation/production_planner.py` | `demand_calculator.calculate_daily_demand_per_product_dict()` | Immer | ❌ Inkonsistent |
| `pages/5_materiallager.py` | `demand_calc.calculate_daily_demand_per_product_dict()` | Fallback | ❌ Inkonsistent |

### 3.2 Produktionsberechnung (3x)

| Stelle | Methode | Wann | Problem |
|--------|---------|------|---------|
| `simulation/production_planner.py` | `plan_daily_production()` | Während Simulation | ✅ Statisch, korrekt |
| `pages/5_materiallager.py` | `production_by_product` (Zeile 181-262) | Für Materialverbrauch | ❌ Abweichung von statischen Logs |
| `pages/6_produktion.py` | Dynamische Berechnung (Zeile 132-196) | Für UI-Anzeige | ❌ Verwendet veraltete Materialbestände |

### 3.3 Materialverbrauch (2x)

| Stelle | Methode | Wann | Problem |
|--------|---------|------|---------|
| `simulation/production_planner.py` | `consume_components()` | Während Simulation | ✅ Statisch, korrekt |
| `pages/5_materiallager.py` | `create_saddle_inventory_log()` | Für UI-Anzeige | ❌ Zirkuläre Abhängigkeit |

### 3.4 Backlog (2x)

| Stelle | Methode | Wann | Problem |
|--------|---------|------|---------|
| `simulation/production_planner.py` | `plan_daily_production()` (Zeile 363) | Während Simulation | ✅ Statisch |
| `pages/6_produktion.py` | Dynamische Berechnung (Zeile 213-282) | Für UI-Anzeige | ❌ Überschreibt statische Werte |

---

## 4. Parallele Aktivitäten

### 4.1 Marketing-Add-on Berechnung

**1. In `ui/volume_planning_utils.py` (Zeile 115-130):**
```python
marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
if marketing_scenarios:
    base_daily_floats = demand_calculator_actual._calculate_monthly_base_daily_float(month)
    for scenario in marketing_scenarios:
        factor = scenario.demand_increase_factor
        add_on = base_float * (factor - 1.0)
```

**2. In `pages/5_materiallager.py` (Zeile 198-216):**
```python
marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
if marketing_scenarios:
    base_daily_floats = demand_calc._calculate_monthly_base_daily_float(month)
    # ... identische Logik ...
```

**3. In `simulation/simulator.py` (Zeile ~270):**
```python
# Berechnet Marketing-Add-ons für Simulation
```

**Problem:** Marketing-Add-ons werden an 3 Stellen berechnet, statt einmal in `calculate_volume_planning_demand()`

---

### 4.2 Produktionsverteilung (proportional)

**1. In `simulation/production_planner.py` (Zeile 165-238):**
```python
# Berechnet proportionale Produktion basierend auf Nachfrage
proportional_share = product_demand / total_demand
proportional_pm = int(daily_capacity * proportional_share)
```

**2. In `pages/5_materiallager.py` (Zeile 242-259):**
```python
# Verteile die tatsächliche Produktion proportional zur Nachfrage
share = product_demands[product] / total_demand
allocated = int(actual_build * share)
production_by_product[product] = allocated
```

**3. In `pages/6_produktion.py` (Zeile 168-170):**
```python
# Berechne "tatsächliche PM" dynamisch:
proportional_share = product_demand / total_demand
proportional_pm = int(daily_capacity * proportional_share)
```

**Problem:** Proportionale Verteilung wird an 3 Stellen berechnet, mit unterschiedlichen Basiswerten (`daily_capacity` vs. `actual_build`)

---

## 5. Potenzielle Inkonsistenzen

### 5.1 Materialverfügbarkeit

**Problem:** Materialbestand wird an verschiedenen Stellen unterschiedlich berechnet:

1. **In `simulation/production_planner.py`:**
   - Verwendet `_get_all_stocks_from_inbound_table()` (Zeile 374)
   - Berechnet Bestand aus Inbound-Tabelle

2. **In `pages/6_produktion.py`:**
   - Verwendet `saddle_stock_morning` aus statischen Logs (Zeile 155)
   - **Problem:** Diese Werte wurden während Simulation berechnet, als Material fehlte
   - **Konsequenz:** Zeigt 0, obwohl jetzt Material da ist

3. **In `pages/5_materiallager.py`:**
   - Berechnet Bestand aus `receipt_by_saddle` und `issue_by_saddle` (Zeile 307)
   - **Problem:** Verwendet `production_by_product_from_logs`, das aus Cache kommt
   - **Konsequenz:** Zirkuläre Abhängigkeit

---

### 5.2 "Tatsächliche PM" vs. "Fertiggestellte PM"

**Problem:** Inkonsistenz zwischen dynamisch aktualisierten Werten:

1. **"Tatsächliche PM":**
   - Wird dynamisch in `pages/6_produktion.py` berechnet (Zeile 196)
   - Basierend auf: `daily_demands_actual`, `daily_capacity`, `saddle_available` (aus statischen Logs)

2. **"Fertiggestellte PM":**
   - Wird dynamisch in `pages/6_produktion.py` berechnet (Zeile 213-282)
   - Basierend auf: "tatsächliche PM" vom vorherigen Arbeitstag

3. **Problem:** Wenn "tatsächliche PM" basierend auf veralteten Materialbeständen berechnet wird, ist auch "fertiggestellte PM" falsch

---

### 5.3 Backlog-Konsistenz

**Problem:** Backlog wird zweimal berechnet:

1. **Statisch (während Simulation):**
   - `ProductionPlanner.backlog` (Zeile 363)
   - `Backlog = geplante PM - fertiggestellte PM + Backlog_vortag`
   - Verwendet: Statische "fertiggestellte PM" aus vorherigem Tag

2. **Dynamisch (für UI):**
   - `pages/6_produktion.py` (Zeile 213-282)
   - `Backlog = geplante PM - fertiggestellte PM + Backlog_vortag`
   - Verwendet: Dynamisch aktualisierte "fertiggestellte PM"

3. **Konsequenz:** Unterschiedliche Werte, wenn Materialverfügbarkeit sich geändert hat

---

## 6. Zirkuläre Abhängigkeiten

### 6.1 Materiallager ↔ Produktion

```
create_saddle_inventory_log() (pages/5_materiallager.py)
    → benötigt production_logs_cache
        → wird in get_production_logs() (pages/6_produktion.py) erstellt
            → benötigt material_inventory_data
                → wird in create_saddle_inventory_log() erstellt
                    → ZIRKEL!
```

**Lösung:** Iterative Berechnung oder Trennung der Abhängigkeiten

---

## 7. Zusammenfassung der Probleme

### 7.1 Kritische Probleme

1. **Zirkuläre Abhängigkeit:** Materiallager ↔ Produktion
2. **Veraltete Materialbestände:** `pages/6_produktion.py` verwendet statische Logs
3. **Mehrfache Nachfrageberechnung:** 4 verschiedene Stellen
4. **Mehrfache Produktionsberechnung:** 3 verschiedene Stellen

### 7.2 Redundanzen

1. **Marketing-Add-ons:** 3x berechnet
2. **Proportionale Verteilung:** 3x berechnet
3. **Inbound-Berechnung:** Mehrfach aufgerufen
4. **Backlog:** 2x berechnet (statisch + dynamisch)

### 7.3 Inkonsistenzen

1. **Materialverfügbarkeit:** Unterschiedliche Quellen
2. **"Tatsächliche PM":** Statische vs. dynamische Werte
3. **Backlog:** Statische vs. dynamische Werte
4. **Materialverbrauch:** Abweichung zwischen statischen und dynamischen Werten

---

## 8. Empfohlene Optimierungen

### 8.1 Single Source of Truth etablieren

1. **Nachfrage:** ✅ Bereits SSoT (`calculate_volume_planning_demand()`)
   - ❌ Problem: Fallbacks berechnen Nachfrage neu
   - ✅ Lösung: Alle Stellen müssen aus Cache lesen, keine Fallbacks

2. **Produktion:** ❌ Keine SSoT
   - ❌ Problem: 3 verschiedene Berechnungen
   - ✅ Lösung: Eine zentrale Funktion, die von allen verwendet wird

3. **Materialverfügbarkeit:** ❌ Keine SSoT
   - ❌ Problem: Unterschiedliche Quellen
   - ✅ Lösung: `material_inventory_data` als SSoT, alle lesen daraus

### 8.2 Zirkuläre Abhängigkeit auflösen

**Option 1: Iterative Berechnung**
- Erste Iteration: Verwende statische Werte
- Zweite Iteration: Verwende korrigierte Werte
- Dritte Iteration: Finale Werte

**Option 2: Trennung der Abhängigkeiten**
- Materiallager berechnet Bestand unabhängig von Produktion
- Produktion verwendet Materiallager-Bestand für Berechnung
- Keine zirkuläre Abhängigkeit

### 8.3 Redundanzen eliminieren

1. **Marketing-Add-ons:** Nur in `calculate_volume_planning_demand()` berechnen
2. **Proportionale Verteilung:** Zentrale Funktion erstellen
3. **Inbound:** Nur einmal berechnen, dann cachen
4. **Backlog:** Nur einmal berechnen (dynamisch), statische Berechnung entfernen

---

## 9. Datenfluss-Diagramm (Aktuell)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VOLUMENPLANUNG (SSoT)                                    │
│    calculate_volume_planning_demand()                       │
│    → daily_demands_planned (ohne Marketing)                │
│    → daily_demands_actual (mit Marketing)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SIMULATOR                                                 │
│    simulator.run()                                           │
│    → Liest daily_demands_actual (✅)                        │
│    → FALLBACK: Berechnet Nachfrage neu (❌)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PRODUCTION PLANNER (Statisch)                             │
│    plan_daily_production()                                   │
│    → Berechnet Nachfrage NEU (❌)                           │
│    → production_by_product (statisch)                       │
│    → production_logs (statisch)                             │
│    → backlog (statisch)                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. CHINA TRANSPORT MANAGER                                   │
│    get_supplier_log_dataframe()                             │
│    → Berechnet Bestelleingang aus daily_demands_actual (✅) │
│    get_inbound_log_dataframe()                              │
│    → Leitet Produktion aus get_supplier_log_dataframe() (✅)│
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. PAGES - Dynamische Updates                                │
│                                                              │
│ 5.1 pages/6_produktion.py                                   │
│     get_production_logs()                                    │
│     → Überschreibt "tatsächliche PM" dynamisch (❌)        │
│        (verwendet veraltete Materialbestände)               │
│     → Überschreibt "fertiggestellte PM" dynamisch           │
│     → Überschreibt Backlog dynamisch                        │
│     → Erstellt production_logs_cache                        │
│                                                              │
│ 5.2 pages/5_materiallager.py                               │
│     create_saddle_inventory_log()                           │
│     → Benötigt production_logs_cache (ZIRKEL!)            │
│     → Berechnet production_by_product NEU (❌)             │
│     → Berechnet Materialverbrauch                           │
│     → Erstellt material_inventory_data                      │
│                                                              │
│ 5.3 pages/3_lieferant_china.py                              │
│     → Ruft get_supplier_log_dataframe() auf                │
│                                                              │
│ 5.4 pages/4_inbound.py                                      │
│     → Ruft get_inbound_log_dataframe() auf                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Kritische Probleme im Detail

### Problem 1: Materialverbrauch zu hoch (1152 statt 273)

**Ursache:**
- `pages/5_materiallager.py` liest `production_logs_cache`
- `production_logs_cache` enthält möglicherweise veraltete Werte (aus statischen Logs)
- Oder: Fallback auf `production_by_product` greift, der falsche Werte enthält

**Lösung:**
- Sicherstellen, dass `production_logs_cache` korrekte Werte enthält
- Oder: Direkt aus statischen `production_logs` lesen (aber dann keine dynamischen Updates)

### Problem 2: Keine Produktion trotz Material

**Ursache:**
- `pages/6_produktion.py` verwendet `saddle_stock_morning` aus statischen Logs (Zeile 155)
- Diese Werte wurden während Simulation berechnet, als Material fehlte
- Dynamische Berechnung verwendet veraltete Werte

**Lösung:**
- Materialbestand aus `material_inventory_data` holen (korrigierter Bestand)
- ABER: Zirkuläre Abhängigkeit muss aufgelöst werden

---

## 11. Empfohlene Architektur (Ziel)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VOLUMENPLANUNG (SSoT)                                    │
│    → daily_demands_actual                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SIMULATOR                                                 │
│    → Verwendet daily_demands_actual (KEIN Fallback!)        │
│    → ProductionPlanner verwendet daily_demands_actual        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. MATERIAL LAGER (SSoT für Bestände)                        │
│    → Berechnet Bestand unabhängig von Produktion             │
│    → material_inventory_data (korrigierte Bestände)          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PRODUKTION (Dynamisch)                                    │
│    → Verwendet material_inventory_data für Bestände          │
│    → Berechnet "tatsächliche PM" dynamisch                   │
│    → production_logs_cache (korrigierte Werte)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. MATERIAL LAGER (Verbrauch)                                │
│    → Verwendet production_logs_cache für Verbrauch           │
│    → Aktualisiert material_inventory_data                    │
└─────────────────────────────────────────────────────────────┘
```

**Wichtig:** Iterative Berechnung oder Trennung der Abhängigkeiten!
