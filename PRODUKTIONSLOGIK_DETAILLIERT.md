# Produktionslogik - Detaillierte Analyse

## Übersicht

Dieses Dokument beschreibt die **komplette Produktionslogik** der Anwendung, zeigt den **Datenfluss anhand einer Beispielbestellung** und identifiziert **parallele Produktionslogiken**.

---

## 0. Visueller Datenfluss (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: VOLUMENPLANUNG                                     │
│                                                              │
│ calculate_volume_planning_demand()                           │
│   → daily_demands_actual[day][product]                     │
│   → Beispiel: {'MTB Allrounder': 180, ...}                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: SIMULATION (Statische Produktionslogik)            │
│                                                              │
│ simulator.run()                                              │
│   → production_planner.plan_daily_production(day)          │
│     ├─> Nachfrage: daily_demands_actual[day]               │
│     ├─> Backlog addieren                                    │
│     ├─> Kapazität berechnen (Schichtanzahl)                 │
│     ├─> Materialverfügbarkeit prüfen (Inbound-Tabelle)     │
│     ├─> Anteilige Produktion berechnen                      │
│     ├─> Rang berechnen (Priorisierung)                      │
│     ├─> "zu produzierende Mengen" berechnen (mit Rang-Logik)│
│     ├─> Material SOFORT reduzieren                          │
│     ├─> "Tatsächliche PM" = "zu produzierende Mengen"       │
│     ├─> "Fertiggestellte PM" berechnen (vom Vortag)         │
│     ├─> Backlog aktualisieren                               │
│     └─> production_logs[product].append(...)                │
│                                                              │
│   → production_logs (STATISCH)                             │
│     → Beispiel: {'MTB Allrounder': [{                       │
│         'Datum': '11.01.2027',                              │
│         'geplante PM': 180,                                 │
│         'tatsächliche PM': 230,  # Statisch                 │
│         'fertiggestellte PM': 200,                          │
│         'Backlog': 30,                                       │
│         ...                                                  │
│       }]}                                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: MATERIAL LAGER (Materialverbrauch)                │
│                                                              │
│ create_saddle_inventory_log()                                │
│   → Liest production_logs_cache (noch nicht verfügbar)     │
│   → Berechnet Materialverbrauch aus production_by_product   │
│   → material_inventory_data[date][saddle]                    │
│     → Beispiel: {date(2027,1,11): {'Spark': 500}}          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: DYNAMISCHE AKTUALISIERUNG (Für UI)                 │
│                                                              │
│ calculate_production_logs()                                  │
│   → Lade statische Logs: production_logs                    │
│   → Aktualisiere "Tatsächliche PM":                         │
│     ├─> Nachfrage: daily_demands_actual[day] (mit Marketing)│
│     ├─> Material: material_inventory_data[date][saddle]     │
│     ├─> Proportional: int(capacity * (demand / total))      │
│     └─> MIN(Proportional, Material, Nachfrage)              │
│       → Überschreibt statischen Wert!                        │
│                                                              │
│   → Aktualisiere "Fertiggestellte PM":                      │
│     └─> Aus aktualisiertem "Tatsächliche PM" vom Vortag     │
│                                                              │
│   → Aktualisiere Backlog:                                   │
│     └─> Aus aktualisierten Werten                            │
│                                                              │
│   → production_logs_cache (DYNAMISCH)                       │
│     → Beispiel: {'MTB Allrounder': DataFrame({               │
│         'Datum': '11.01.2027',                              │
│         'geplante PM': 180,                                 │
│         'tatsächliche PM': 180,  # Dynamisch aktualisiert!  │
│         'fertiggestellte PM': 200,                           │
│         'Backlog': 30,                                       │
│         ...                                                  │
│       })}                                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: UI-ANZEIGE                                          │
│                                                              │
│ pages/6_produktion.py                                        │
│   → Zeigt production_logs_cache                             │
│   → Beispiel: Tabelle mit "Tatsächliche PM" = 180           │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Inhaltliche Produktionslogik

### 1.1 Grundprinzipien

Die Produktionslogik basiert auf folgenden Prinzipien:

1. **Nachfrage-orientiert**: Produktion richtet sich nach der Nachfrage aus der Volumenplanung
2. **Material-begrenzt**: Produktion ist durch Materialverfügbarkeit (Sättel) begrenzt
3. **Kapazitäts-begrenzt**: Produktion ist durch Schichtkapazität begrenzt
4. **Priorisiert**: Produkte werden nach Rang priorisiert (Rang 1-4: Basis, Rang 5-8: Rest-Verteilung)
5. **Backlog-Tracking**: Nicht erfüllte Nachfrage wird als Backlog gespeichert
6. **Fertigstellungsverzögerung**: Produktion wird am nächsten Arbeitstag fertiggestellt

### 1.2 Produktionsbegriffe

| Begriff | Definition | Quelle |
|---------|------------|--------|
| **Geplante PM** | Tagesbedarf aus Volumenplanung (ohne Backlog) | `daily_demands_actual[day][product]` |
| **Produktionsbedarf** | Geplante PM + Backlog vom Vortag | `production_demand_by_product[product]` |
| **Anteilige Produktion** | Proportionale Verteilung der Kapazität nach Nachfrage | `proportional_production_by_product[product]` |
| **zu produzierende Mengen** | Tatsächlich geplante Produktion (nach Material- und Kapazitätsprüfung) | `scheduled_production_by_product[product]` |
| **Tatsächliche PM** | Produktion, die HEUTE geplant wird (entspricht "zu produzierende Mengen") | `production_by_product[product]` |
| **Fertiggestellte PM** | Produktion vom VORHERIGEN Arbeitstag, die HEUTE fertiggestellt wird | `finished_pm_by_product[product]` |
| **Backlog** | Nicht erfüllte Nachfrage = Geplante PM - Fertiggestellte PM + Backlog vom Vortag | `backlog[product]` |

---

## 2. Statische Produktionslogik (während Simulation)

### 2.1 Komponente: `simulation/production_planner.py`

**Aufgabe:** Plant die tägliche Produktion während der Simulation

**Methode:** `plan_daily_production(day, marketing_add_ons, scenario_manager)`

### 2.2 Schritt-für-Schritt Ablauf

#### Schritt 1: Nachfrage ermitteln
```python
# Liest aus daily_demands_actual (Single Source of Truth)
product_demands = daily_demands_actual[day].copy()
# Beispiel: {'MTB Allrounder': 150, 'E-Bike City': 200, ...}
```

#### Schritt 2: Backlog zum Bedarf addieren
```python
production_demand_by_product = {}
for product in products:
    planned_demand = product_demands[product]  # z.B. 150
    backlog = self.backlog[product]  # z.B. 50
    production_demand_by_product[product] = planned_demand + backlog  # = 200
```

#### Schritt 3: Kapazität berechnen
```python
# AGGRESSIVE BACKLOG-RECOVERY: Wenn Backlog vorhanden, IMMER 3 Schichten
if total_backlog > 0:
    shifts = 3  # Maximale Kapazität
else:
    shifts = ceil(total_demand / capacity_per_shift)  # Normal
    shifts = min(3, max(1, shifts))

daily_capacity = shifts * 8 * 130  # z.B. 3 * 8 * 130 = 3120
```

#### Schritt 4: Materialverfügbarkeit prüfen
```python
# Hole Bestand pro Sattel-Typ aus Inbound-Tabelle
stock_by_saddle_type = _get_all_stocks_from_inbound_table(day, saddle_shares)
# Beispiel: {'Fizik Tundra': 500, 'Spark': 300, ...}
```

#### Schritt 5: Anteilige Produktion berechnen
```python
proportional_production_by_product = {}
for product in products:
    demand = production_demand_by_product[product]
    proportional = floor(demand * daily_capacity / total_production_demand)
    # Beispiel: MTB Allrounder: floor(200 * 3120 / 2000) = 312
```

#### Schritt 6: Rang berechnen
```python
# Rang_Unterstützung = Anteilige_Produktion + Zeile/1000000
rank_support = (row_number / 1000000.0) + proportional
# Sortiere nach Rang (höchster Support = Rang 1)
sorted_products = sorted(products, key=lambda p: rank_support[p], reverse=True)
```

#### Schritt 7: "zu produzierende Mengen" berechnen
```python
for product in sorted_products:  # Nach Rang sortiert
    demand = production_demand_by_product[product]
    proportional = proportional_production_by_product[product]
    minimal = stock_by_saddle_type[required_saddle]  # Material-Limit
    
    if rank <= 4:
        # Rang 1-4: MIN(Bedarf, Anteilige, Minimale)
        scheduled_qty = min(demand, proportional, minimal)
    else:
        # Rang 5-8: MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung
        base_qty = min(demand, proportional, minimal)
        remaining_capacity = daily_capacity - total_scheduled_so_far
        rest_production = min(remaining_capacity, minimal, remaining_demand)
        scheduled_qty = base_qty + rest_production
    
    # KRITISCH: Reduziere Material SOFORT (dynamisch)
    stock_by_saddle_type[required_saddle] -= scheduled_qty
```

#### Schritt 8: "Tatsächliche PM" = "zu produzierende Mengen"
```python
production_by_product[product] = int(scheduled_production_by_product[product])
```

#### Schritt 9: "Fertiggestellte PM" berechnen
```python
# Fertiggestellte PM = "Tatsächliche PM" vom VORHERIGEN Arbeitstag
if day > 0:
    prev_workday = find_last_workday(day - 1)
    finished_pm_by_product[product] = production_logs[product][prev_workday]['tatsächliche PM']
```

#### Schritt 10: Backlog aktualisieren
```python
# Backlog = geplante PM - fertiggestellte PM + Backlog vom Vortag
for product in products:
    planned_pm = product_demands[product]  # Ohne Backlog!
    finished_pm = finished_pm_by_product[product]
    old_backlog = self.backlog[product]
    self.backlog[product] = max(0.0, planned_pm - finished_pm + old_backlog)
```

#### Schritt 11: Loggen für UI
```python
_log_production(
    day,
    production_by_product,  # Tatsächliche PM
    product_demands,  # Geplante PM
    production_demand_by_product,  # Produktionsbedarf
    material_availability_report,  # Materialverfügbarkeit
    rank_by_product,  # Rang
    shifts,  # Schichtanzahl
    daily_capacity,  # Tageskapazität
    stock_saddles_morning,  # Bestand morgens
    proportional_production_by_product,  # Anteilige Produktion
    scheduled_production_by_product,  # zu produzierende Mengen
    finished_pm_by_product  # Fertiggestellte PM
)
```

---

## 3. Dynamische Produktionslogik (für UI)

### 3.1 Komponente: `ui/production_calculations.py`

**Aufgabe:** Aktualisiert Produktionslogs dynamisch für UI-Anzeige (reagiert auf Marketing-Szenarien)

**Methode:** `calculate_production_logs()`

### 3.2 Schritt-für-Schritt Ablauf

#### Schritt 1: Statische Logs laden
```python
# Lade statische Logs aus ProductionPlanner
production_logs = {}
for product, logs in planner.production_logs.items():
    production_logs[product] = pd.DataFrame(logs)
```

#### Schritt 2: "Tatsächliche PM" dynamisch aktualisieren
```python
for product, df in production_logs.items():
    for idx, row in df.iterrows():
        day = (row_date - date(planning_year, 1, 1)).days
        
        # Hole Nachfrage mit Marketing (aus daily_demands_actual)
        product_demand = daily_demands_actual[day][product]
        
        # Hole Materialverfügbarkeit (aus material_inventory_data)
        saddle_available = material_inventory_data[row_date][saddle_name]
        
        # Berechne proportionale Produktion
        proportional_pm = int(daily_capacity * (product_demand / total_demand))
        
        # Tatsächliche PM = MIN(Proportional, Materialverfügbar, Nachfrage)
        dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
        
        df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)
```

#### Schritt 3: "Fertiggestellte PM" dynamisch aktualisieren
```python
# Fertiggestellte PM = "Tatsächliche PM" vom VORHERIGEN Arbeitstag
for idx, row in df_sorted.iterrows():
    prev_workday = find_previous_workday(row_date)
    if prev_workday in date_to_idx:
        prev_actual_pm = df_sorted.iloc[date_to_idx[prev_workday]]['tatsächliche PM']
        df_sorted.at[idx, 'fertiggestellte PM'] = prev_actual_pm
```

#### Schritt 4: Backlog dynamisch aktualisieren
```python
# Backlog = geplante PM (mit Marketing) - fertiggestellte PM + Backlog vom Vortag
for idx, row in df_sorted.iterrows():
    planned_pm = daily_demands_actual[day][product]  # Mit Marketing!
    finished_pm = row['fertiggestellte PM']
    prev_backlog = df_sorted.iloc[idx - 1]['Backlog']
    new_backlog = max(0.0, planned_pm - finished_pm + prev_backlog)
    df_sorted.at[idx, 'Backlog'] = int(round(new_backlog))
```

---

## 4. Parallele Produktionslogiken - Vergleich

### 4.1 Statische Logik vs. Dynamische Logik

| Aspekt | Statische Logik (`production_planner.py`) | Dynamische Logik (`production_calculations.py`) |
|--------|-------------------------------------------|--------------------------------------------------|
| **Wann** | Während Simulation (einmalig) | Bei jedem Seitenaufruf (dynamisch) |
| **Nachfrage** | Aus `daily_demands_actual` (während Simulation) | Aus `daily_demands_actual` (aktuell, mit Marketing) |
| **Materialverfügbarkeit** | Aus Inbound-Tabelle (während Simulation) | Aus `material_inventory_data` (aktuell, korrigiert) |
| **Tatsächliche PM** | "zu produzierende Mengen" (statisch) | MIN(Proportional, Material, Nachfrage) (dynamisch) |
| **Fertiggestellte PM** | Aus vorherigem Log-Eintrag | Aus aktualisiertem "tatsächliche PM" |
| **Backlog** | Berechnet während Simulation | Neu berechnet aus aktualisierten Werten |
| **Reagiert auf Marketing** | ❌ Nein (wird während Simulation berechnet) | ✅ Ja (wird dynamisch aktualisiert) |

### 4.2 Unterschiede in der Berechnung

#### "Tatsächliche PM"

**Statische Logik:**
```python
# Während Simulation
scheduled_qty = min(demand, proportional, minimal)  # Mit Rang-Logik
production_by_product[product] = int(scheduled_qty)
```

**Dynamische Logik:**
```python
# Für UI-Anzeige
proportional_pm = int(daily_capacity * (product_demand / total_demand))
dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)
```

**Unterschied:**
- Statische Logik: Berücksichtigt Rang-Logik (Rang 1-4 vs. 5-8)
- Dynamische Logik: Vereinfachte proportionale Verteilung (keine Rang-Logik)

#### Materialverfügbarkeit

**Statische Logik:**
```python
# Während Simulation
stock_by_saddle_type = _get_all_stocks_from_inbound_table(day, saddle_shares)
# Reduziert Material dynamisch während Berechnung
stock_by_saddle_type[required_saddle] -= scheduled_qty
```

**Dynamische Logik:**
```python
# Für UI-Anzeige
saddle_available = material_inventory_data[row_date][saddle_name]
# Material wird NICHT reduziert (nur für Anzeige)
```

**Unterschied:**
- Statische Logik: Material wird während Berechnung reduziert (dynamische Reduktion)
- Dynamische Logik: Material wird aus `material_inventory_data` gelesen (bereits korrigiert)

---

## 5. Datenfluss anhand einer Beispielbestellung

### 5.1 Beispiel: MTB Allrounder am 11.01.2027

**Annahme:**
- Geplante PM (ohne Marketing): 150
- Marketing-Szenario aktiv: +20% → Geplante PM (mit Marketing): 180
- Backlog vom Vortag: 50
- Materialverfügbarkeit (Spark): 500
- Tageskapazität: 3120 (3 Schichten)

### 5.2 Datenfluss Schritt für Schritt

#### Tag 0: Volumenplanung
```
[Volumenplanung]
  ↓
calculate_volume_planning_demand()
  ↓
daily_demands_actual[10] = {'MTB Allrounder': 180, ...}  # Mit Marketing
```

#### Tag 1: Simulation (11.01.2027)

**1. Simulator ruft ProductionPlanner auf:**
```
[Simulator]
  ↓
simulator.run() → Tag 10
  ↓
production_planner.plan_daily_production(day=10)
```

**2. ProductionPlanner: Schritt 1 - Nachfrage ermitteln**
```
product_demands = daily_demands_actual[10]
  → {'MTB Allrounder': 180, ...}
```

**3. ProductionPlanner: Schritt 2 - Backlog addieren**
```
production_demand_by_product['MTB Allrounder'] = 180 + 50 = 230
```

**4. ProductionPlanner: Schritt 3 - Kapazität berechnen**
```
total_backlog > 0 → shifts = 3
daily_capacity = 3 * 8 * 130 = 3120
```

**5. ProductionPlanner: Schritt 4 - Materialverfügbarkeit**
```
stock_by_saddle_type['Spark'] = _get_all_stocks_from_inbound_table(10, ...)
  → 500 (aus Inbound-Tabelle)
```

**6. ProductionPlanner: Schritt 5 - Anteilige Produktion**
```
total_production_demand = 2000 (Summe aller Produkte)
proportional = floor(230 * 3120 / 2000) = 358
```

**7. ProductionPlanner: Schritt 6 - Rang berechnen**
```
rank_support = 358 + (1 / 1000000) = 358.000001
  → Rang 1 (höchster Support)
```

**8. ProductionPlanner: Schritt 7 - "zu produzierende Mengen"**
```
scheduled_qty = min(230, 358, 500) = 230
  → Material wird reduziert: stock_by_saddle_type['Spark'] = 500 - 230 = 270
```

**9. ProductionPlanner: Schritt 8 - "Tatsächliche PM"**
```
production_by_product['MTB Allrounder'] = 230
```

**10. ProductionPlanner: Schritt 9 - "Fertiggestellte PM"**
```
prev_workday = 9 (10.01.2027)
finished_pm_by_product['MTB Allrounder'] = production_logs['MTB Allrounder'][9]['tatsächliche PM']
  → z.B. 200 (von gestern produziert)
```

**11. ProductionPlanner: Schritt 10 - Backlog aktualisieren**
```
backlog = max(0.0, 180 - 200 + 50) = 30
  → Backlog reduziert (fertiggestellte PM > geplante PM)
```

**12. ProductionPlanner: Schritt 11 - Loggen**
```
_log_production(...)
  → production_logs['MTB Allrounder'].append({
      'Datum': '11.01.2027',
      'geplante PM': 180,
      'tatsächliche PM': 230,
      'fertiggestellte PM': 200,
      'Backlog': 30,
      ...
    })
```

#### Tag 2: UI-Anzeige (11.01.2027)

**1. Seitenaufruf: `pages/6_produktion.py`**
```
get_production_logs()
  ↓
calculate_production_logs()
```

**2. Dynamische Aktualisierung: "Tatsächliche PM"**
```
# Hole aktuelle Nachfrage (mit Marketing)
product_demand = daily_demands_actual[10]['MTB Allrounder'] = 180

# Hole aktuelle Materialverfügbarkeit (aus material_inventory_data)
saddle_available = material_inventory_data[date(2027,1,11)]['Spark'] = 500

# Berechne proportionale Produktion
proportional_pm = int(3120 * (180 / 2000)) = 280

# Tatsächliche PM = MIN(280, 500, 180) = 180
df.at[idx, 'tatsächliche PM'] = 180
```

**3. Dynamische Aktualisierung: "Fertiggestellte PM"**
```
# Fertiggestellte PM = "Tatsächliche PM" vom vorherigen Arbeitstag
prev_workday = 9 (10.01.2027)
prev_actual_pm = df_sorted.iloc[date_to_idx[prev_workday]]['tatsächliche PM'] = 200
df_sorted.at[idx, 'fertiggestellte PM'] = 200
```

**4. Dynamische Aktualisierung: Backlog**
```
# Backlog = geplante PM - fertiggestellte PM + Backlog vom Vortag
planned_pm = 180
finished_pm = 200
prev_backlog = 50
new_backlog = max(0.0, 180 - 200 + 50) = 30
df_sorted.at[idx, 'Backlog'] = 30
```

---

## 6. Komponenten und ihre Aufgaben

### 6.1 `simulation/production_planner.py`

**Aufgabe:** Statische Produktionsplanung während Simulation

**Verantwortlichkeiten:**
- ✅ Nachfrage aus `daily_demands_actual` lesen
- ✅ Backlog zum Bedarf addieren
- ✅ Kapazität berechnen (Schichtanzahl)
- ✅ Materialverfügbarkeit prüfen (aus Inbound-Tabelle)
- ✅ Anteilige Produktion berechnen
- ✅ Rang berechnen (Priorisierung)
- ✅ "zu produzierende Mengen" berechnen (mit Material-Reduktion)
- ✅ "Tatsächliche PM" = "zu produzierende Mengen"
- ✅ "Fertiggestellte PM" berechnen (vom vorherigen Arbeitstag)
- ✅ Backlog aktualisieren
- ✅ Produktionslogs erstellen (statisch)

**Wird aufgerufen von:**
- `simulation/simulator.py` (während Simulation)

**Erstellt:**
- `production_logs` (statisch, während Simulation)

---

### 6.2 `ui/production_calculations.py`

**Aufgabe:** Dynamische Aktualisierung der Produktionslogs für UI

**Verantwortlichkeiten:**
- ✅ Statische Logs aus `ProductionPlanner` laden
- ✅ "Tatsächliche PM" dynamisch aktualisieren (mit Marketing, korrigierte Materialverfügbarkeit)
- ✅ "Fertiggestellte PM" dynamisch aktualisieren (aus aktualisiertem "tatsächliche PM")
- ✅ Backlog dynamisch aktualisieren (aus aktualisierten Werten)
- ✅ `production_logs_cache` erstellen (für UI-Anzeige)

**Wird aufgerufen von:**
- `ui/page_initialization.py` (beim App-Start)
- `pages/6_produktion.py` (beim Seitenaufruf)

**Erstellt:**
- `production_logs_cache` (dynamisch, für UI)

---

### 6.3 `pages/6_produktion.py`

**Aufgabe:** UI-Anzeige der Produktionsdaten

**Verantwortlichkeiten:**
- ✅ Ruft `get_production_logs()` auf (verwendet `calculate_production_logs()`)
- ✅ Zeigt Produktionstabellen für jedes Produkt
- ✅ Zeigt Auslastung, Materialverfügbarkeit, Backlog

**Verwendet:**
- `production_logs_cache` (aus `ui/production_calculations.py`)

---

### 6.4 `pages/5_materiallager.py`

**Aufgabe:** Berechnet Materialverbrauch basierend auf Produktion

**Verantwortlichkeiten:**
- ✅ Liest "tatsächliche PM" aus `production_logs_cache`
- ✅ Berechnet Materialverbrauch (`Lagerabgang`) pro Sattel-Typ
- ✅ Erstellt `material_inventory_data` (Bestand morgens pro Tag)

**Verwendet:**
- `production_logs_cache` (für Materialverbrauch)

**Erstellt:**
- `material_inventory_data` (für Produktionslogik)

---

## 7. Parallele Produktionslogiken - Detaillierter Vergleich

### 7.1 "Tatsächliche PM" - Vergleich

#### Statische Logik (`production_planner.py`)

```python
# Schritt 1: Anteilige Produktion
proportional = floor(demand * daily_capacity / total_production_demand)

# Schritt 2: Rang-basierte Berechnung
if rank <= 4:
    scheduled_qty = min(demand, proportional, minimal)
else:
    base_qty = min(demand, proportional, minimal)
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production

# Schritt 3: Material wird SOFORT reduziert
stock_by_saddle_type[required_saddle] -= scheduled_qty

# Schritt 4: Tatsächliche PM = scheduled_qty
production_by_product[product] = int(scheduled_qty)
```

**Eigenschaften:**
- ✅ Berücksichtigt Rang-Logik (Rang 1-4 vs. 5-8)
- ✅ Material wird dynamisch reduziert während Berechnung
- ✅ Rest-Verteilung für Rang 5-8
- ❌ Statisch (wird während Simulation berechnet, reagiert nicht auf Marketing-Änderungen)

#### Dynamische Logik (`production_calculations.py`)

```python
# Schritt 1: Anteilige Produktion
proportional_pm = int(daily_capacity * (product_demand / total_demand))

# Schritt 2: Materialverfügbarkeit aus material_inventory_data
saddle_available = material_inventory_data[row_date][saddle_name]

# Schritt 3: Tatsächliche PM = MIN(Proportional, Material, Nachfrage)
dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)

# Schritt 4: Überschreibe statischen Wert
df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)
```

**Eigenschaften:**
- ❌ Keine Rang-Logik (vereinfachte proportionale Verteilung)
- ✅ Verwendet korrigierte Materialverfügbarkeit (`material_inventory_data`)
- ✅ Reagiert auf Marketing-Änderungen (verwendet aktuelle `daily_demands_actual`)
- ✅ Dynamisch (wird bei jedem Seitenaufruf neu berechnet)

### 7.2 Problem: Inkonsistenz zwischen statischer und dynamischer Logik

**Problem:**
- Statische Logik verwendet Rang-Logik (Rang 1-4 vs. 5-8)
- Dynamische Logik verwendet vereinfachte proportionale Verteilung
- **Konsequenz:** Unterschiedliche Werte für "Tatsächliche PM"

**Beispiel:**
- **Statisch:** Rang 5-Produkt bekommt `base_qty + rest_production` (z.B. 100 + 50 = 150)
- **Dynamisch:** Rang 5-Produkt bekommt nur `proportional_pm` (z.B. 120)
- **Unterschied:** 30 Einheiten

### 7.3 "Fertiggestellte PM" - Vergleich

#### Statische Logik

```python
# Fertiggestellte PM = "Tatsächliche PM" vom VORHERIGEN Arbeitstag
prev_workday = find_last_workday(day - 1)
finished_pm_by_product[product] = production_logs[product][prev_workday]['tatsächliche PM']
```

**Eigenschaften:**
- ✅ Verwendet statische "Tatsächliche PM" vom vorherigen Tag
- ❌ Reagiert nicht auf dynamische Änderungen

#### Dynamische Logik

```python
# Fertiggestellte PM = aktualisierte "Tatsächliche PM" vom VORHERIGEN Arbeitstag
prev_workday = find_previous_workday(row_date)
prev_actual_pm = df_sorted.iloc[date_to_idx[prev_workday]]['tatsächliche PM']  # Dynamisch aktualisiert!
df_sorted.at[idx, 'fertiggestellte PM'] = prev_actual_pm
```

**Eigenschaften:**
- ✅ Verwendet dynamisch aktualisierte "Tatsächliche PM"
- ✅ Reagiert auf Marketing-Änderungen

### 7.4 Backlog - Vergleich

#### Statische Logik

```python
# Backlog = geplante PM (ohne Marketing) - fertiggestellte PM + Backlog vom Vortag
planned_pm = product_demands[product]  # Aus daily_demands_actual (während Simulation)
finished_pm = finished_pm_by_product[product]  # Statisch
old_backlog = self.backlog[product]
self.backlog[product] = max(0.0, planned_pm - finished_pm + old_backlog)
```

**Eigenschaften:**
- ✅ Verwendet `product_demands` (kann Marketing enthalten, wenn während Simulation aktiv)
- ❌ Reagiert nicht auf Marketing-Änderungen nach Simulation

#### Dynamische Logik

```python
# Backlog = geplante PM (mit Marketing) - fertiggestellte PM + Backlog vom Vortag
planned_pm = daily_demands_actual[day][product]  # Aktuell, mit Marketing!
finished_pm = row['fertiggestellte PM']  # Dynamisch aktualisiert
prev_backlog = df_sorted.iloc[idx - 1]['Backlog']  # Dynamisch aktualisiert
new_backlog = max(0.0, planned_pm - finished_pm + prev_backlog)
```

**Eigenschaften:**
- ✅ Verwendet aktuelle `daily_demands_actual` (mit Marketing)
- ✅ Verwendet dynamisch aktualisierte "Fertiggestellte PM"
- ✅ Reagiert auf Marketing-Änderungen

---

## 8. Beispiel-Datenfluss: Komplette Bestellung

### 8.1 Beispiel: MTB Allrounder am 11.01.2027

**Ausgangssituation:**
- Geplante PM (ohne Marketing): 150
- Marketing-Szenario aktiv: +20% → Geplante PM (mit Marketing): 180
- Backlog vom Vortag (10.01.2027): 50
- Materialverfügbarkeit (Spark) morgens: 500
- Tageskapazität: 3120 (3 Schichten, da Backlog vorhanden)

### 8.2 Datenfluss durch alle Komponenten

#### Phase 1: Volumenplanung (Tag 0)

```
[User aktiviert Marketing-Szenario]
  ↓
[pages/2_volumenplanung.py]
  ↓
calculate_volume_planning_demand()
  ↓
daily_demands_actual[10]['MTB Allrounder'] = 180  # Mit Marketing
```

#### Phase 2: Simulation (Tag 1)

```
[simulator.run() → Tag 10]
  ↓
[simulation/production_planner.py]
  ↓
plan_daily_production(day=10)
  ↓
  ├─> product_demands = daily_demands_actual[10] = {'MTB Allrounder': 180}
  ├─> production_demand_by_product = 180 + 50 = 230
  ├─> shifts = 3 (Backlog vorhanden)
  ├─> daily_capacity = 3120
  ├─> stock_by_saddle_type['Spark'] = 500
  ├─> proportional = floor(230 * 3120 / 2000) = 358
  ├─> rank = 1 (höchster Support)
  ├─> scheduled_qty = min(230, 358, 500) = 230
  ├─> stock_by_saddle_type['Spark'] = 500 - 230 = 270  # Material reduziert
  ├─> production_by_product['MTB Allrounder'] = 230  # Tatsächliche PM
  ├─> finished_pm_by_product = 200  # Von gestern
  ├─> backlog = max(0.0, 180 - 200 + 50) = 30
  └─> _log_production(...)
      └─> production_logs['MTB Allrounder'].append({
          'Datum': '11.01.2027',
          'geplante PM': 180,
          'tatsächliche PM': 230,  # Statisch
          'fertiggestellte PM': 200,
          'Backlog': 30,
          ...
        })
```

#### Phase 3: Materiallager-Berechnung (Tag 2)

```
[pages/5_materiallager.py]
  ↓
create_saddle_inventory_log()
  ↓
  ├─> Liest production_logs_cache (noch nicht verfügbar)
  ├─> Berechnet Materialverbrauch aus production_by_product_from_logs
  ├─> issue_by_saddle['Spark'] = 230  # Aus production_logs_cache
  ├─> stock_morning['Spark'] = 500
  ├─> actual_issue = min(230, 500) = 230
  ├─> stock_evening['Spark'] = 500 - 230 = 270
  └─> material_inventory_data[date(2027,1,11)]['Spark'] = 500  # Bestand morgens
```

#### Phase 4: Dynamische Produktionsaktualisierung (Tag 3)

```
[pages/6_produktion.py]
  ↓
get_production_logs()
  ↓
calculate_production_logs()
  ↓
  ├─> Lade statische Logs: production_logs['MTB Allrounder']
  ├─> Aktualisiere "Tatsächliche PM":
  │   ├─> product_demand = daily_demands_actual[10]['MTB Allrounder'] = 180
  │   ├─> saddle_available = material_inventory_data[date(2027,1,11)]['Spark'] = 500
  │   ├─> proportional_pm = int(3120 * (180 / 2000)) = 280
  │   └─> dynamic_pm = min(280, 500, 180) = 180
  │       └─> df.at[idx, 'tatsächliche PM'] = 180  # Überschreibt 230!
  │
  ├─> Aktualisiere "Fertiggestellte PM":
  │   ├─> prev_workday = 9 (10.01.2027)
  │   ├─> prev_actual_pm = df_sorted.iloc[date_to_idx[prev_workday]]['tatsächliche PM'] = 200
  │   └─> df_sorted.at[idx, 'fertiggestellte PM'] = 200
  │
  └─> Aktualisiere Backlog:
      ├─> planned_pm = 180
      ├─> finished_pm = 200
      ├─> prev_backlog = 50
      └─> new_backlog = max(0.0, 180 - 200 + 50) = 30
          └─> df_sorted.at[idx, 'Backlog'] = 30
```

#### Phase 5: UI-Anzeige

```
[pages/6_produktion.py]
  ↓
Zeige Tabelle für "MTB Allrounder"
  ↓
  ├─> Datum: 11.01.2027
  ├─> Geplante PM: 180 (mit Marketing)
  ├─> Tatsächliche PM: 180 (dynamisch aktualisiert)
  ├─> Fertiggestellte PM: 200 (von gestern)
  └─> Backlog: 30 (dynamisch aktualisiert)
```

---

## 9. Identifizierte Probleme

### 9.1 Problem 1: Inkonsistenz zwischen statischer und dynamischer "Tatsächliche PM"

**Statische Logik:** 230 (mit Rang-Logik, Material-Reduktion)
**Dynamische Logik:** 180 (vereinfachte proportionale Verteilung)

**Ursache:**
- Statische Logik verwendet Rang-Logik (Rang 1-4 vs. 5-8)
- Dynamische Logik verwendet vereinfachte proportionale Verteilung

**Konsequenz:**
- Unterschiedliche Werte für "Tatsächliche PM"
- Materialverbrauch in Materiallager basiert auf statischen Werten (230)
- UI-Anzeige zeigt dynamische Werte (180)
- **Inkonsistenz!**

### 9.2 Problem 2: Materialverbrauch basiert auf statischen Werten

**Materiallager liest:**
```python
production_by_product_from_logs = production_logs_cache['MTB Allrounder']
actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)  # = 180 (dynamisch)
```

**Aber:**
- Statische Logik hat 230 produziert (Material wurde reduziert: 500 → 270)
- Dynamische Logik zeigt 180 (Material sollte nur 180 verbrauchen)
- **Inkonsistenz!**

### 9.3 Problem 3: Rang-Logik fehlt in dynamischer Berechnung

**Statische Logik:**
- Rang 1-4: `MIN(Bedarf, Anteilige, Minimale)`
- Rang 5-8: `MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung`

**Dynamische Logik:**
- Alle Ränge: `MIN(Proportional, Material, Nachfrage)` (vereinfacht)

**Konsequenz:**
- Rang 5-8 Produkte bekommen in dynamischer Logik weniger als in statischer Logik
- **Inkonsistenz!**

---

## 10. Welches System wird in der UI angezeigt?

### 10.1 Antwort: Das dynamische System wird angezeigt

**UI-Anzeige (`pages/6_produktion.py`):**
```python
production_logs = get_production_logs()  # Ruft calculate_production_logs() auf
# Zeigt production_logs (dynamisch aktualisiert)
```

**Was passiert in `calculate_production_logs()`:**
```python
# 1. Lade statische Logs (als Basis)
production_logs = {}
for product, logs in planner.production_logs.items():
    production_logs[product] = pd.DataFrame(logs)  # STATISCH

# 2. Überschreibe "Tatsächliche PM" dynamisch
df.at[idx, 'tatsächliche PM'] = dynamic_pm  # DYNAMISCH (überschreibt statischen Wert!)

# 3. Überschreibe "Fertiggestellte PM" dynamisch
df_sorted.at[idx, 'fertiggestellte PM'] = prev_actual_pm  # DYNAMISCH

# 4. Überschreibe Backlog dynamisch
df_sorted.at[idx, 'Backlog'] = new_backlog  # DYNAMISCH

# 5. Speichere als production_logs_cache
st.session_state.production_logs_cache = production_logs  # DYNAMISCH
```

**Ergebnis:**
- ✅ **UI zeigt dynamische Werte** (aus `production_logs_cache`)
- ✅ Statische Logs werden als **Basis verwendet**, aber dann **überschrieben**
- ✅ Beide Systeme laufen parallel, aber dynamisches System **überschreibt** statische Werte

### 10.2 Heißt dies, dass eines der Systeme ruht?

**Nein!** Beide Systeme laufen parallel:

1. **Statisches System** (`production_planner.py`):
   - ✅ Wird während Simulation ausgeführt
   - ✅ Erstellt `production_logs` (statisch)
   - ✅ Wird als **Basis** für dynamisches System verwendet
   - ⚠️ **Wird überschrieben** durch dynamisches System

2. **Dynamisches System** (`production_calculations.py`):
   - ✅ Wird bei jedem Seitenaufruf ausgeführt
   - ✅ Liest statische Logs als Basis
   - ✅ **Überschreibt** "Tatsächliche PM", "Fertiggestellte PM", Backlog
   - ✅ Erstellt `production_logs_cache` (dynamisch)
   - ✅ **Wird in UI angezeigt**

**Visualisierung:**
```
Statisches System (production_planner.py)
  ↓
production_logs (statisch)
  ↓
Dynamisches System (production_calculations.py)
  ↓
  ├─> Lade statische Logs (Basis)
  ├─> Überschreibe "Tatsächliche PM" (dynamisch)
  ├─> Überschreibe "Fertiggestellte PM" (dynamisch)
  ├─> Überschreibe Backlog (dynamisch)
  └─> production_logs_cache (dynamisch)
      ↓
UI-Anzeige (pages/6_produktion.py)
```

### 10.3 Problem: Inkonsistenz zwischen Basis und Anzeige

**Beispiel: MTB Allrounder am 11.01.2027**

**Statisches System (Basis):**
- "Tatsächliche PM" = 230 (mit Rang-Logik)
- Material wurde reduziert: 500 → 270

**Dynamisches System (Anzeige):**
- "Tatsächliche PM" = 180 (vereinfachte Verteilung)
- Material wird aus `material_inventory_data` gelesen: 500

**UI zeigt:**
- "Tatsächliche PM" = **180** (dynamisch)
- Material (Spark) = **500** (aus material_inventory_data)

**Aber:**
- Materiallager berechnet Verbrauch aus `production_logs_cache`:
  - Liest "Tatsächliche PM" = 180 (dynamisch)
  - Verbraucht 180 Einheiten
  - Bestand: 500 - 180 = 320

**Problem:**
- Statisches System hat 230 produziert (Material wurde reduziert: 500 → 270)
- Dynamisches System zeigt 180 (Material sollte nur 180 verbrauchen)
- Materiallager verbraucht 180 (konsistent mit dynamischem System)
- **Aber:** Statisches System hat bereits 230 verbraucht!
- **Inkonsistenz:** Material wurde doppelt verbraucht (230 statisch + 180 dynamisch = 410, aber nur 500 vorhanden)

---

## 11. Zusammenfassung

### 11.1 Produktionslogik - Zwei parallele Systeme

1. **Statische Logik** (`production_planner.py`):
   - Wird während Simulation berechnet
   - Verwendet Rang-Logik
   - Material wird dynamisch reduziert
   - Reagiert NICHT auf Marketing-Änderungen nach Simulation
   - **Wird als Basis verwendet, aber überschrieben**

2. **Dynamische Logik** (`production_calculations.py`):
   - Wird bei jedem Seitenaufruf neu berechnet
   - Verwendet vereinfachte proportionale Verteilung
   - Material wird aus `material_inventory_data` gelesen
   - Reagiert auf Marketing-Änderungen
   - **Wird in UI angezeigt**

### 10.2 Datenfluss

```
Volumenplanung → Simulator → ProductionPlanner → Statische Logs
                                                      ↓
                                              Dynamische Aktualisierung
                                                      ↓
                                              UI-Anzeige
```

### 10.3 Hauptprobleme

1. **Inkonsistenz:** Statische und dynamische Logik produzieren unterschiedliche Werte
2. **Rang-Logik fehlt:** Dynamische Logik verwendet vereinfachte Verteilung
3. **Materialverbrauch:** Basiert auf statischen Werten, nicht auf dynamischen

### 10.4 Empfehlung

**Option 1:** Dynamische Logik sollte Rang-Logik implementieren
- Vorteil: Konsistenz mit statischer Logik
- Nachteil: Komplexere Implementierung

**Option 2:** Statische Logik sollte als "Single Source of Truth" verwendet werden
- Vorteil: Einheitliche Werte
- Nachteil: Reagiert nicht auf Marketing-Änderungen nach Simulation

**Option 3:** Hybrid-Ansatz
- Statische Logik für Basis-Berechnung
- Dynamische Logik nur für Marketing-Anpassungen (nicht für komplette Neuberechnung)
