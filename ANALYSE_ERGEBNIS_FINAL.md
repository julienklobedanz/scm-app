# Analyse-Ergebnis: Warum funktionieren die Korrekturen nicht?

## Problem

**63 Tage** gefunden, an denen "Tatsächliche PM" > Produktionsbedarf ist.

**Beispiel: 06.08.2027**
- Geplante PM = 454
- Backlog_vortag = 0
- Produktionsbedarf = 454 + 0 = 454
- **Tatsächliche PM = 1103** (2.43x mehr!)

## Analyse

### 1. Die Korrekturen sind implementiert

✅ `scheduled_qty = min(max(0.0, scheduled_qty), demand)` - Implementiert
✅ `remaining_demand = max(0.0, demand - base_qty)` - Implementiert
✅ Sicherheitsprüfung 2: Summe darf Produktionsbedarf nicht überschreiten - Implementiert

### 2. Die Test-Berechnung zeigt korrekte Werte

Meine Test-Berechnung zeigt:
- Scheduled Qty (nach Prüfung) = 454 ✅
- Scheduled Qty <= Demand: True ✅

**ABER:** Die CSV zeigt 1103, nicht 454!

### 3. Mögliche Ursachen

#### Ursache 1: Statische Werte werden verwendet

**Problem:** Die dynamische Neuberechnung wird nur ausgeführt, wenn sich Inputs geändert haben:
```python
if inputs_changed and daily_capacity > 0:
    # Neuberechnung
else:
    # Verwende statische Werte
```

**Wenn sich Inputs NICHT geändert haben:**
- Die statischen Werte werden verwendet
- Diese stammen von einer Simulation, die VOR den Korrekturen lief
- Die statischen Werte sind falsch (1103 statt 454)

**Lösung:** Die dynamische Neuberechnung sollte IMMER ausgeführt werden, wenn die statischen Werte falsch sind (Tatsächliche PM > Produktionsbedarf).

#### Ursache 2: Falscher Backlog in dynamischer Neuberechnung

**Problem:** Die dynamische Neuberechnung verwendet Backlog aus statischen Logs:
```python
backlog_by_product[product] = _get_backlog_from_previous_workday(
    production_logs, product, day, planning_year, workday_calc
)
```

**Wenn die statischen Logs falsche Werte haben:**
- Der Backlog ist falsch
- Der Produktionsbedarf ist falsch
- Die Neuberechnung produziert falsche Werte

#### Ursache 3: Die Sicherheitsprüfung 2 greift nicht

**Problem:** Die Sicherheitsprüfung 2 prüft nur, ob `total_scheduled > total_production_demand`. 

**Wenn einzelne Produkte mehr produzieren, aber die Summe noch unter dem Gesamtbedarf liegt:**
- Die Prüfung greift nicht
- Einzelne Produkte produzieren mehr als erlaubt

**ABER:** Die Prüfung `scheduled_qty = min(scheduled_qty, demand)` sollte das verhindern.

## Die wahre Ursache

**Ich vermute:** Die statischen Werte werden verwendet, weil sich Inputs nicht geändert haben. Diese statischen Werte stammen von einer Simulation, die VOR den Korrekturen lief.

**Beweis:**
- Die Test-Berechnung zeigt korrekte Werte (454)
- Die CSV zeigt falsche Werte (1103)
- Die dynamische Neuberechnung wird nur ausgeführt, wenn sich Inputs geändert haben

## Lösung

### Option 1: Dynamische Neuberechnung immer ausführen

**Ändere die Bedingung:**
```python
# ALT:
if inputs_changed and daily_capacity > 0:

# NEU:
if daily_capacity > 0:
    # Prüfe ob statische Werte korrekt sind
    base_tatsaechliche_pm = info['base_tatsaechliche_pm']
    base_geplante_pm = info['base_geplante_pm']
    base_backlog = ...  # Hole Backlog vom Vortag
    
    production_demand_expected = base_geplante_pm + base_backlog
    
    if base_tatsaechliche_pm > production_demand_expected:
        # Statische Werte sind falsch → Neuberechnung
        inputs_changed = True
    else:
        # Statische Werte sind korrekt → Prüfe ob Inputs geändert haben
        inputs_changed = ...  # Wie bisher
```

### Option 2: Prüfung in dynamischer Neuberechnung

**Füge eine zusätzliche Prüfung hinzu:**
```python
# Nach der Berechnung von scheduled_qty für alle Produkte
for product in products_list:
    demand = production_demand_by_product.get(product, 0.0)
    scheduled_qty = scheduled_production_by_product.get(product, 0.0)
    
    if scheduled_qty > demand:
        # KRITISCH: Reduziere auf Produktionsbedarf
        scheduled_production_by_product[product] = demand
```

### Option 3: Simulation neu starten

**Die einfachste Lösung:** Die Simulation muss neu gestartet werden, damit die statische Logik mit den Korrekturen läuft.

**ABER:** Das Problem besteht weiterhin, auch nach einem Neustart. Das bedeutet, dass die Korrekturen nicht greifen oder dass es ein anderes Problem gibt.

## Empfehlung

**Implementiere Option 1 + Option 2:**
1. Prüfe, ob statische Werte korrekt sind (Option 1)
2. Füge eine zusätzliche Prüfung hinzu (Option 2)

Dies stellt sicher, dass:
- Statische Werte korrigiert werden, wenn sie falsch sind
- Dynamische Neuberechnung immer korrekte Werte produziert
