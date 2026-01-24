# Option 3: Hybrid-Ansatz - Detaillierte Analyse

## Übersicht

**Option 3: Hybrid-Ansatz** bedeutet:
- **Statische Produktionslogik bleibt die Basis** (Rang-Logik, Material-Reduktion, etc.)
- **Dynamische Logik macht nur Marketing-Anpassungen** (aktualisierte Nachfrage, korrigierte Materialverfügbarkeit)
- **Rang-Logik wird IMMER verwendet** (sowohl statisch als auch dynamisch)

---

## 1. Was bedeutet Option 3 konkret?

### 1.1 Aktueller Zustand (Problem)

**Statische Logik:**
```python
# Während Simulation
product_demands = daily_demands_actual[day]  # Mit Marketing (wenn während Simulation aktiv)
# ... Rang-Logik ...
scheduled_qty = min(demand, proportional, minimal)  # Mit Rang-Logik
production_by_product[product] = int(scheduled_qty)  # z.B. 230
```

**Dynamische Logik (aktuell - FALSCH):**
```python
# Für UI-Anzeige
proportional_pm = int(daily_capacity * (product_demand / total_demand))  # Vereinfacht!
dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)  # KEINE Rang-Logik!
df.at[idx, 'tatsächliche PM'] = dynamic_pm  # z.B. 180 (überschreibt 230!)
```

**Problem:**
- Dynamische Logik überschreibt statische Werte
- Rang-Logik fehlt in dynamischer Berechnung
- Inkonsistenz zwischen statischen und dynamischen Werten

### 1.2 Option 3: Hybrid-Ansatz (Lösung)

**Prinzip:**
- Statische Logik wird als **Basis verwendet**
- Dynamische Logik macht nur **Input-Anpassungen** (Nachfrage mit Marketing, korrigierte Materialverfügbarkeit)
- **Rang-Logik wird vollständig repliziert** in dynamischer Berechnung

**Konkrete Umsetzung:**
```python
# Dynamische Logik (Option 3)
# 1. Hole statische Werte als Basis
base_tatsaechliche_pm = row.get('tatsächliche PM', 0)  # Statisch: z.B. 230

# 2. Hole aktualisierte Inputs
product_demand_new = daily_demands_actual[day][product]  # Mit Marketing: z.B. 180 statt 150
saddle_available_new = material_inventory_data[row_date][saddle_name]  # Korrigiert: z.B. 500

# 3. WENN sich Inputs geändert haben (Marketing aktiviert):
if product_demand_new != base_geplante_pm or saddle_available_new != base_saddle_stock:
    # 4. Repliziere KOMPLETTE statische Logik mit neuen Inputs
    #    (inkl. Rang-Logik, Material-Reduktion, etc.)
    new_tatsaechliche_pm = recalculate_with_rank_logic(
        product_demand_new,
        saddle_available_new,
        daily_capacity,
        rank,  # Aus statischen Logs
        ...
    )
    df.at[idx, 'tatsächliche PM'] = new_tatsaechliche_pm
else:
    # 5. WENN sich Inputs NICHT geändert haben:
    #    Verwende statische Werte (keine Überschreibung)
    df.at[idx, 'tatsächliche PM'] = base_tatsaechliche_pm  # Behalte 230
```

---

## 2. Konkrete Auswirkungen auf UI-Tabellen

### 2.1 Produktion (`pages/6_produktion.py`)

#### Aktuell (FALSCH):

| Spalte | Wert (aktuell) | Quelle |
|--------|----------------|--------|
| Geplante PM | 180 | `daily_demands_actual[day]` (mit Marketing) ✅ |
| Tatsächliche PM | **180** | Dynamisch berechnet (vereinfacht, KEINE Rang-Logik) ❌ |
| Fertiggestellte PM | 200 | Aus aktualisiertem "Tatsächliche PM" vom Vortag |
| Backlog | 30 | Dynamisch berechnet |
| Spark (Material) | 500 | Aus `material_inventory_data` ✅ |

**Problem:**
- "Tatsächliche PM" = 180 (dynamisch, ohne Rang-Logik)
- Statische Logik hatte 230 produziert (mit Rang-Logik)
- **Inkonsistenz!**

#### Mit Option 3 (KORREKT):

| Spalte | Wert (Option 3) | Quelle |
|--------|----------------|--------|
| Geplante PM | 180 | `daily_demands_actual[day]` (mit Marketing) ✅ |
| Tatsächliche PM | **230** | Statische Logik mit aktualisierten Inputs (MIT Rang-Logik) ✅ |
| Fertiggestellte PM | 200 | Aus statischem "Tatsächliche PM" vom Vortag ✅ |
| Backlog | 30 | Berechnet aus statischen Werten ✅ |
| Spark (Material) | 500 | Aus `material_inventory_data` ✅ |

**Vorteil:**
- "Tatsächliche PM" = 230 (konsistent mit statischer Logik)
- Rang-Logik wird verwendet
- Materialverbrauch ist konsistent

### 2.2 Materiallager (`pages/5_materiallager.py`)

#### Aktuell (FALSCH):

| Spalte | Wert (aktuell) | Quelle |
|--------|----------------|--------|
| Lagerzugang | 100 | Aus Inbound-Tabelle ✅ |
| Bestand morgens | 500 | Aus `material_inventory_data` ✅ |
| Lagerabgang | **180** | Aus `production_logs_cache` (dynamisch, ohne Rang-Logik) ❌ |
| Bestand abends | 320 | 500 - 180 = 320 |

**Problem:**
- "Lagerabgang" = 180 (aus dynamischer Logik, ohne Rang-Logik)
- Statische Logik hat 230 verbraucht
- **Inkonsistenz!**

#### Mit Option 3 (KORREKT):

| Spalte | Wert (Option 3) | Quelle |
|--------|----------------|--------|
| Lagerzugang | 100 | Aus Inbound-Tabelle ✅ |
| Bestand morgens | 500 | Aus `material_inventory_data` ✅ |
| Lagerabgang | **230** | Aus `production_logs_cache` (statische Logik mit Rang-Logik) ✅ |
| Bestand abends | 270 | 500 - 230 = 270 ✅ |

**Vorteil:**
- "Lagerabgang" = 230 (konsistent mit statischer Logik)
- Materialverbrauch ist korrekt
- Bestand abends ist konsistent

---

## 3. Implementierung von Option 3

### 3.1 Neue Funktion: `recalculate_with_rank_logic()`

**Aufgabe:** Repliziert die komplette statische Produktionslogik mit aktualisierten Inputs

**Eingaben:**
- `product_demands_new`: Aktualisierte Nachfrage (mit Marketing)
- `saddle_available_new`: Korrigierte Materialverfügbarkeit
- `daily_capacity`: Tageskapazität (aus statischen Logs)
- `rank`: Rang (aus statischen Logs)
- `production_demand_by_product_new`: Produktionsbedarf (Nachfrage + Backlog)

**Ausgabe:**
- `scheduled_qty`: "zu produzierende Mengen" (mit Rang-Logik)

### 3.2 Schritt-für-Schritt Implementierung

```python
def recalculate_with_rank_logic(
    product: str,
    product_demand: int,  # Aktualisierte Nachfrage (mit Marketing)
    production_demand: float,  # Produktionsbedarf (Nachfrage + Backlog)
    saddle_available: float,  # Korrigierte Materialverfügbarkeit
    daily_capacity: float,  # Tageskapazität
    rank: int,  # Rang (aus statischen Logs)
    total_production_demand: float,  # Gesamt-Produktionsbedarf (alle Produkte)
    total_scheduled_so_far: float,  # Bereits geplante Produktion (für Rang 5-8)
    sorted_products: list,  # Sortierte Produktliste (nach Rang)
    current_product_index: int  # Index in sortierter Liste
) -> int:
    """
    Repliziert die komplette statische Produktionslogik mit aktualisierten Inputs.
    
    WICHTIG: Diese Funktion implementiert die EXAKTE Logik aus production_planner.py,
    nur mit aktualisierten Inputs (Nachfrage mit Marketing, korrigierte Materialverfügbarkeit).
    """
    # Schritt 1: Anteilige Produktion berechnen
    if total_production_demand > 0:
        proportional = math.floor(production_demand * daily_capacity / total_production_demand)
    else:
        proportional = 0
    
    # Schritt 2: Minimale Produktion (Material-Limit)
    minimal = max(0.0, saddle_available)
    
    # Schritt 3: Rang-basierte Berechnung (EXAKT wie in production_planner.py)
    if rank <= 4:
        # Rang 1-4: MIN(Bedarf, Anteilige, Minimale)
        scheduled_qty = min(production_demand, proportional, minimal)
    else:
        # Rang 5-8: MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung
        base_qty = min(production_demand, proportional, minimal)
        
        remaining_capacity = daily_capacity - total_scheduled_so_far
        remaining_demand = production_demand - base_qty
        
        if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
            rest_production = min(remaining_capacity, minimal, remaining_demand)
            scheduled_qty = base_qty + rest_production
        else:
            scheduled_qty = base_qty
    
    return int(max(0.0, scheduled_qty))
```

### 3.3 Integration in `calculate_production_logs()`

**Aktuell (FALSCH):**
```python
# Vereinfachte proportionale Verteilung (KEINE Rang-Logik)
proportional_pm = int(daily_capacity * (product_demand / total_demand))
dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
df.at[idx, 'tatsächliche PM'] = dynamic_pm
```

**Mit Option 3 (KORREKT):**
```python
# Hole statische Werte als Basis
base_tatsaechliche_pm = row.get('tatsächliche PM', 0)
base_geplante_pm = row.get('geplante PM', 0)
base_saddle_stock = row.get(saddle_name, 0)
rank = row.get('_Rang', 999)  # Aus statischen Logs
proportional_static = row.get('_Anteilige_Produktion', 0)  # Aus statischen Logs
scheduled_static = row.get('_zu_produzierende_Mengen', 0)  # Aus statischen Logs

# Hole aktualisierte Inputs
product_demand_new = daily_demands_actual[day][product]  # Mit Marketing
saddle_available_new = material_inventory_data[row_date].get(saddle_name, 0.0)  # Korrigiert

# Prüfe ob sich Inputs geändert haben
if product_demand_new != base_geplante_pm or saddle_available_new != base_saddle_stock:
    # Inputs haben sich geändert → Repliziere statische Logik mit neuen Inputs
    # WICHTIG: Berechne für ALLE Produkte (für korrekte Rang-Logik und Material-Reduktion)
    new_tatsaechliche_pm = recalculate_with_rank_logic_for_all_products(
        day,
        daily_demands_actual[day],  # Alle Produkte mit Marketing
        material_inventory_data[row_date],  # Alle Sättel korrigiert
        daily_capacity,
        production_logs  # Für Rang-Informationen
    )
    df.at[idx, 'tatsächliche PM'] = new_tatsaechliche_pm[product]
else:
    # Inputs haben sich NICHT geändert → Verwende statische Werte
    df.at[idx, 'tatsächliche PM'] = base_tatsaechliche_pm
```

---

## 4. Konkrete Auswirkungen auf UI-Tabellen (Detailliert)

### 4.1 Beispiel: MTB Allrounder am 11.01.2027

**Ausgangssituation:**
- Geplante PM (ohne Marketing): 150
- Marketing-Szenario aktiv: +20% → Geplante PM (mit Marketing): 180
- Backlog vom Vortag: 50
- Materialverfügbarkeit (Spark) morgens: 500
- Tageskapazität: 3120 (3 Schichten)
- Rang: 1 (höchster Support)

#### Statische Logik (während Simulation):

```
1. Nachfrage: 180 (mit Marketing)
2. Produktionsbedarf: 180 + 50 = 230
3. Anteilige Produktion: floor(230 * 3120 / 2000) = 358
4. Rang: 1
5. Minimale Produktion: 500 (Material verfügbar)
6. "zu produzierende Mengen": min(230, 358, 500) = 230
7. Material reduziert: 500 - 230 = 270
8. "Tatsächliche PM": 230
```

#### Dynamische Logik (aktuell - FALSCH):

```
1. Nachfrage: 180 (mit Marketing) ✅
2. Material: 500 (korrigiert) ✅
3. Anteilige Produktion: int(3120 * (180 / 2000)) = 280
4. Rang: IGNORIERT ❌
5. "Tatsächliche PM": min(280, 500, 180) = 180 ❌
```

**Problem:**
- Statische Logik: 230 (mit Rang-Logik)
- Dynamische Logik: 180 (ohne Rang-Logik)
- **Unterschied: 50 Einheiten**

#### Dynamische Logik (Option 3 - KORREKT):

```
1. Nachfrage: 180 (mit Marketing) ✅
2. Material: 500 (korrigiert) ✅
3. Produktionsbedarf: 180 + 50 = 230 (Backlog vom Vortag)
4. Anteilige Produktion: floor(230 * 3120 / 2000) = 358
5. Rang: 1 (aus statischen Logs) ✅
6. Minimale Produktion: 500 (Material verfügbar)
7. "zu produzierende Mengen": min(230, 358, 500) = 230 ✅
8. "Tatsächliche PM": 230 ✅
```

**Vorteil:**
- Statische Logik: 230
- Dynamische Logik: 230
- **Konsistent!**

### 4.2 Beispiel: Rang 5-Produkt (z.B. E-Bike City)

**Ausgangssituation:**
- Geplante PM (mit Marketing): 200
- Backlog vom Vortag: 0
- Materialverfügbarkeit (Fizik Tundra) morgens: 300
- Tageskapazität: 3120
- Rang: 5 (Rest-Verteilung)

#### Statische Logik:

```
1. Produktionsbedarf: 200 + 0 = 200
2. Anteilige Produktion: floor(200 * 3120 / 2000) = 312
3. Rang: 5
4. Minimale Produktion: 300
5. Basis: min(200, 312, 300) = 200
6. Rest-Kapazität: 3120 - 2000 (bereits geplant) = 1120
7. Rest-Produktion: min(1120, 300, 0) = 0
8. "zu produzierende Mengen": 200 + 0 = 200
9. "Tatsächliche PM": 200
```

#### Dynamische Logik (aktuell - FALSCH):

```
1. Anteilige Produktion: int(3120 * (200 / 2000)) = 312
2. Rang: IGNORIERT ❌
3. "Tatsächliche PM": min(312, 300, 200) = 200
```

**Problem:**
- Statische Logik: 200 (mit Rang-Logik, aber kein Rest)
- Dynamische Logik: 200 (zufällig gleich, aber ohne Rang-Logik)
- **Bei anderen Werten könnte es unterschiedlich sein!**

#### Dynamische Logik (Option 3 - KORREKT):

```
1. Produktionsbedarf: 200 + 0 = 200
2. Anteilige Produktion: floor(200 * 3120 / 2000) = 312
3. Rang: 5 (aus statischen Logs) ✅
4. Minimale Produktion: 300
5. Basis: min(200, 312, 300) = 200
6. Rest-Kapazität: 3120 - 2000 (bereits geplant) = 1120
7. Rest-Produktion: min(1120, 300, 0) = 0
8. "zu produzierende Mengen": 200 + 0 = 200 ✅
9. "Tatsächliche PM": 200 ✅
```

**Vorteil:**
- Rang-Logik wird verwendet
- Rest-Verteilung wird berücksichtigt
- Konsistent mit statischer Logik

---

## 5. Konkrete Auswirkungen auf UI-Tabellen

### 5.1 Produktion (`pages/6_produktion.py`)

#### Spalte: "Tatsächliche PM"

**Aktuell:**
- Wert: 180 (dynamisch, ohne Rang-Logik)
- Problem: Inkonsistent mit statischer Logik (230)

**Mit Option 3:**
- Wert: 230 (statische Logik mit aktualisierten Inputs, MIT Rang-Logik)
- Vorteil: Konsistent mit statischer Logik

#### Spalte: "Fertiggestellte PM"

**Aktuell:**
- Wert: 200 (aus aktualisiertem "Tatsächliche PM" vom Vortag)
- Problem: Basierend auf inkonsistentem "Tatsächliche PM"

**Mit Option 3:**
- Wert: 200 (aus statischem "Tatsächliche PM" vom Vortag)
- Vorteil: Konsistent mit statischer Logik

#### Spalte: "Backlog"

**Aktuell:**
- Wert: 30 (dynamisch berechnet aus inkonsistenten Werten)
- Problem: Basierend auf inkonsistentem "Tatsächliche PM"

**Mit Option 3:**
- Wert: 30 (berechnet aus konsistenten statischen Werten)
- Vorteil: Konsistent mit statischer Logik

#### Spalte: "Spark" (Material)

**Aktuell:**
- Wert: 500 (aus `material_inventory_data`)
- Problem: Inkonsistent mit Materialverbrauch (180 statt 230)

**Mit Option 3:**
- Wert: 500 (aus `material_inventory_data`)
- Vorteil: Konsistent (Materialverbrauch ist 230, nicht 180)

### 5.2 Materiallager (`pages/5_materiallager.py`)

#### Spalte: "Lagerabgang"

**Aktuell:**
- Wert: 180 (aus `production_logs_cache`, dynamisch, ohne Rang-Logik)
- Problem: Inkonsistent mit statischer Logik (230)

**Mit Option 3:**
- Wert: 230 (aus `production_logs_cache`, statische Logik mit Rang-Logik)
- Vorteil: Konsistent mit statischer Logik

#### Spalte: "Bestand abends"

**Aktuell:**
- Wert: 320 (500 - 180 = 320)
- Problem: Falsch (Material wurde bereits statisch verbraucht: 500 - 230 = 270)

**Mit Option 3:**
- Wert: 270 (500 - 230 = 270)
- Vorteil: Konsistent mit statischer Logik

---

## 6. Implementierungsstrategie

### 6.1 Schritt 1: Rang-Logik in dynamische Berechnung integrieren

**Neue Funktion:** `recalculate_production_with_rank_logic()`

**Aufgabe:**
- Repliziert die komplette statische Produktionslogik
- Verwendet aktualisierte Inputs (Nachfrage mit Marketing, korrigierte Materialverfügbarkeit)
- Behält Rang-Logik bei

### 6.2 Schritt 2: Material-Reduktion während Berechnung

**Wichtig:**
- Material muss während Berechnung reduziert werden (wie in statischer Logik)
- Rang 1-4: Material wird reduziert
- Rang 5-8: Material wird reduziert (für Basis + Rest)

### 6.3 Schritt 3: Nur bei Input-Änderungen neu berechnen

**Optimierung:**
- Wenn sich Nachfrage oder Materialverfügbarkeit NICHT geändert haben:
  - Verwende statische Werte (keine Neuberechnung)
- Wenn sich Nachfrage oder Materialverfügbarkeit geändert haben:
  - Neuberechnung mit Rang-Logik

---

## 7. Zusammenfassung

### 7.1 Option 3: Hybrid-Ansatz

**Prinzip:**
- Statische Produktionslogik ist die Basis
- Dynamische Logik macht nur Input-Anpassungen
- Rang-Logik wird IMMER verwendet

### 7.2 Konkrete Auswirkungen

**Produktion:**
- "Tatsächliche PM": Statische Werte (mit Rang-Logik)
- "Fertiggestellte PM": Statische Werte
- Backlog: Berechnet aus statischen Werten

**Materiallager:**
- "Lagerabgang": Statische Werte (mit Rang-Logik)
- Bestand abends: Konsistent mit statischem Materialverbrauch

### 7.3 Vorteile

1. ✅ Konsistenz: Statische und dynamische Werte sind identisch
2. ✅ Rang-Logik: Wird immer verwendet
3. ✅ Materialverbrauch: Korrekt und konsistent
4. ✅ Marketing-Reaktivität: Wird berücksichtigt (durch aktualisierte Inputs)

### 7.4 Nachteile

1. ⚠️ Komplexität: Rang-Logik muss in dynamischer Berechnung repliziert werden
2. ⚠️ Performance: Neuberechnung für alle Produkte bei Input-Änderungen
3. ⚠️ Wartbarkeit: Zwei Stellen mit ähnlicher Logik (statisch und dynamisch)

---

## 8. Konkrete Implementierung: Rang-Logik in dynamische Berechnung

### 8.1 Problem: Aktuelle dynamische Logik überschreibt statische Werte

**Aktuell in `ui/production_calculations.py` (Zeile 79-101):**
```python
# Vereinfachte proportionale Verteilung (KEINE Rang-Logik)
proportional_pm = int(daily_capacity * (product_demand / total_demand))
dynamic_pm = min(proportional_pm, int(saddle_available), product_demand)
df.at[idx, 'tatsächliche PM'] = max(0, dynamic_pm)  # Überschreibt statischen Wert!
```

**Problem:**
- Rang-Logik fehlt
- Material-Reduktion fehlt
- Überschreibt statische Werte

### 8.2 Lösung: Rang-Logik replizieren

**Neue Implementierung:**
```python
# Hole statische Werte als Basis
base_tatsaechliche_pm = row.get('tatsächliche PM', 0)
base_geplante_pm = row.get('geplante PM', 0)
base_saddle_stock = row.get(saddle_name, 0)
rank = row.get('_Rang', 999)  # WICHTIG: Aus statischen Logs
proportional_static = row.get('_Anteilige_Produktion', 0)
scheduled_static = row.get('_zu_produzierende_Mengen', 0)
production_demand_static = row.get('_Produktionsbedarf', 0)

# Hole aktualisierte Inputs
product_demand_new = daily_demands_actual[day][product]  # Mit Marketing
saddle_available_new = material_inventory_data[row_date].get(saddle_name, 0.0)  # Korrigiert

# Prüfe ob sich Inputs geändert haben
inputs_changed = (
    product_demand_new != base_geplante_pm or 
    saddle_available_new != base_saddle_stock
)

if inputs_changed:
    # WICHTIG: Repliziere KOMPLETTE statische Logik mit neuen Inputs
    # Berechne für ALLE Produkte (für korrekte Rang-Logik und Material-Reduktion)
    new_production = recalculate_all_products_with_rank_logic(
        day,
        daily_demands_actual[day],  # Alle Produkte mit Marketing
        material_inventory_data[row_date],  # Alle Sättel korrigiert
        daily_capacity,
        production_logs  # Für Rang-Informationen
    )
    df.at[idx, 'tatsächliche PM'] = new_production[product]
else:
    # Inputs haben sich NICHT geändert → Verwende statische Werte
    df.at[idx, 'tatsächliche PM'] = base_tatsaechliche_pm
```

### 8.3 Funktion: `recalculate_all_products_with_rank_logic()`

**Aufgabe:** Repliziert die komplette statische Produktionslogik für ALLE Produkte mit aktualisierten Inputs

**Eingaben:**
- `day`: Tag-Index
- `product_demands_new`: Dict[product] -> demand (mit Marketing)
- `saddle_available_new`: Dict[saddle] -> stock (korrigiert)
- `daily_capacity`: Tageskapazität
- `production_logs`: Statische Logs (für Rang-Informationen)

**Ausgabe:**
- Dict[product] -> "Tatsächliche PM" (mit Rang-Logik)

**Implementierung:**
```python
def recalculate_all_products_with_rank_logic(
    day: int,
    product_demands_new: Dict[str, int],
    saddle_available_new: Dict[str, float],
    daily_capacity: float,
    production_logs: Dict[str, pd.DataFrame]
) -> Dict[str, int]:
    """
    Repliziert die komplette statische Produktionslogik für ALLE Produkte
    mit aktualisierten Inputs (Nachfrage mit Marketing, korrigierte Materialverfügbarkeit).
    
    WICHTIG: Diese Funktion implementiert die EXAKTE Logik aus production_planner.py,
    nur mit aktualisierten Inputs.
    """
    import math
    
    # Schritt 1: Hole Backlog vom Vortag (aus statischen Logs)
    backlog_by_product = {}
    for product in MasterData.BOM.keys():
        if product in production_logs:
            df = production_logs[product]
            if not df.empty and day > 0:
                # Finde vorherigen Arbeitstag
                prev_workday = find_previous_workday(day)
                # Hole Backlog vom vorherigen Arbeitstag
                backlog_by_product[product] = get_backlog_from_logs(df, prev_workday)
            else:
                backlog_by_product[product] = 0.0
    
    # Schritt 2: Produktionsbedarf = Nachfrage + Backlog
    production_demand_by_product = {}
    for product in MasterData.BOM.keys():
        demand = product_demands_new.get(product, 0)
        backlog = backlog_by_product.get(product, 0.0)
        production_demand_by_product[product] = demand + backlog
    
    # Schritt 3: Anteilige Produktion berechnen
    total_production_demand = sum(production_demand_by_product.values())
    proportional_production_by_product = {}
    for product in MasterData.BOM.keys():
        demand = production_demand_by_product.get(product, 0.0)
        if total_production_demand > 0:
            proportional = math.floor(demand * daily_capacity / total_production_demand)
        else:
            proportional = 0
        proportional_production_by_product[product] = proportional
    
    # Schritt 4: Rang berechnen (EXAKT wie in production_planner.py)
    products_list = list(MasterData.BOM.keys())
    rank_support_by_product = {}
    for idx, product in enumerate(products_list):
        row_number = idx + 1
        proportional = proportional_production_by_product.get(product, 0)
        rank_support = (row_number / 1000000.0) + proportional
        rank_support_by_product[product] = rank_support
    
    sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
    rank_by_product = {}
    for i, p in enumerate(sorted_products):
        rank_by_product[p] = i + 1
    
    # Schritt 5: "zu produzierende Mengen" berechnen (mit Material-Reduktion)
    scheduled_production_by_product = {}
    total_scheduled_so_far = 0.0
    
    # WICHTIG: Material wird dynamisch reduziert (wie in statischer Logik)
    stock_by_saddle_type = saddle_available_new.copy()
    
    for product in sorted_products:
        demand = production_demand_by_product.get(product, 0.0)
        proportional = proportional_production_by_product.get(product, 0)
        rank = rank_by_product.get(product, 999)
        
        if demand <= 0:
            scheduled_production_by_product[product] = 0.0
            continue
        
        # Minimale Produktion (Material-Limit)
        required_saddle_type = MasterData.BOM[product]['saddle']
        saddle_available = stock_by_saddle_type.get(required_saddle_type, 0.0)
        minimal = max(0.0, saddle_available)
        
        # Rang-basierte Berechnung (EXAKT wie in production_planner.py)
        if rank <= 4:
            scheduled_qty = min(demand, proportional, minimal)
        else:
            base_qty = min(demand, proportional, minimal)
            remaining_capacity = daily_capacity - total_scheduled_so_far
            remaining_demand = demand - base_qty
            
            if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
                rest_production = min(remaining_capacity, minimal, remaining_demand)
                scheduled_qty = base_qty + rest_production
            else:
                scheduled_qty = base_qty
        
        scheduled_qty = max(0.0, scheduled_qty)
        scheduled_production_by_product[product] = scheduled_qty
        total_scheduled_so_far += scheduled_qty
        
        # KRITISCH: Reduziere Material SOFORT (dynamisch)
        if scheduled_qty > 0:
            stock_by_saddle_type[required_saddle_type] = max(0.0, stock_by_saddle_type[required_saddle_type] - scheduled_qty)
    
    # Schritt 6: "Tatsächliche PM" = "zu produzierende Mengen"
    result = {}
    for product in products_list:
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        result[product] = int(scheduled_qty)
    
    return result
```

---

## 9. Konkrete Auswirkungen auf UI-Tabellen (Final)

### 9.1 Produktion (`pages/6_produktion.py`)

#### Vor Option 3 (aktuell - FALSCH):

| Spalte | Wert | Quelle | Problem |
|--------|------|--------|---------|
| Geplante PM | 180 | `daily_demands_actual` (mit Marketing) | ✅ |
| Tatsächliche PM | **180** | Dynamisch (vereinfacht, KEINE Rang-Logik) | ❌ Sollte 230 sein |
| Fertiggestellte PM | 200 | Aus aktualisiertem "Tatsächliche PM" | ⚠️ Basierend auf falschem Wert |
| Backlog | 30 | Dynamisch berechnet | ⚠️ Basierend auf falschem Wert |
| Spark | 500 | `material_inventory_data` | ✅ |

#### Nach Option 3 (KORREKT):

| Spalte | Wert | Quelle | Status |
|--------|------|--------|--------|
| Geplante PM | 180 | `daily_demands_actual` (mit Marketing) | ✅ |
| Tatsächliche PM | **230** | Statische Logik mit aktualisierten Inputs (MIT Rang-Logik) | ✅ |
| Fertiggestellte PM | 200 | Aus statischem "Tatsächliche PM" | ✅ |
| Backlog | 30 | Berechnet aus statischen Werten | ✅ |
| Spark | 500 | `material_inventory_data` | ✅ |

**Änderung:**
- "Tatsächliche PM": 180 → **230** (konsistent mit statischer Logik)
- Alle anderen Werte bleiben gleich (bereits korrekt)

### 9.2 Materiallager (`pages/5_materiallager.py`)

#### Vor Option 3 (aktuell - FALSCH):

| Spalte | Wert | Quelle | Problem |
|--------|------|--------|---------|
| Lagerzugang | 100 | Inbound-Tabelle | ✅ |
| Bestand morgens | 500 | `material_inventory_data` | ✅ |
| Lagerabgang | **180** | `production_logs_cache` (dynamisch, ohne Rang-Logik) | ❌ Sollte 230 sein |
| Bestand abends | 320 | 500 - 180 = 320 | ❌ Sollte 270 sein |

#### Nach Option 3 (KORREKT):

| Spalte | Wert | Quelle | Status |
|--------|------|--------|--------|
| Lagerzugang | 100 | Inbound-Tabelle | ✅ |
| Bestand morgens | 500 | `material_inventory_data` | ✅ |
| Lagerabgang | **230** | `production_logs_cache` (statische Logik mit Rang-Logik) | ✅ |
| Bestand abends | 270 | 500 - 230 = 270 | ✅ |

**Änderung:**
- "Lagerabgang": 180 → **230** (konsistent mit statischer Logik)
- "Bestand abends": 320 → **270** (konsistent mit Materialverbrauch)

---

## 10. Zusammenfassung

### 10.1 Option 3: Hybrid-Ansatz

**Prinzip:**
- Statische Produktionslogik ist die Basis
- Dynamische Logik repliziert statische Logik mit aktualisierten Inputs
- Rang-Logik wird IMMER verwendet

### 10.2 Konkrete Auswirkungen

**Produktion:**
- "Tatsächliche PM": **230** (statt 180) - mit Rang-Logik
- Alle anderen Werte bleiben gleich

**Materiallager:**
- "Lagerabgang": **230** (statt 180) - konsistent mit Produktion
- "Bestand abends": **270** (statt 320) - konsistent mit Materialverbrauch

### 10.3 Vorteile

1. ✅ Konsistenz: Statische und dynamische Werte sind identisch
2. ✅ Rang-Logik: Wird immer verwendet
3. ✅ Materialverbrauch: Korrekt und konsistent
4. ✅ Marketing-Reaktivität: Wird berücksichtigt (durch aktualisierte Inputs)

### 10.4 Implementierung

**Schritt 1:** Funktion `recalculate_all_products_with_rank_logic()` implementieren
**Schritt 2:** In `calculate_production_logs()` integrieren
**Schritt 3:** Nur bei Input-Änderungen neu berechnen (Optimierung)
