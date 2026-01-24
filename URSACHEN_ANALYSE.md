# Ursachen-Analyse: Warum ist Summe(Tatsächliche PM) > Summe(Geplante PM)?

## Analyse der CSV-Daten

### Beobachtungen aus der CSV:

**Summen:**
- Geplante PM: 111000
- Tatsächliche PM: 132678 (+21678)
- Fertiggestellte PM: 172526 (+61526)
- Endbacklog (31.12.2027): 435

**Beispiel-Tage:**
- 04.01.2027: Geplante PM = 222, Tatsächliche PM = 0, Backlog = 222
- 05.01.2027: Geplante PM = 222, Tatsächliche PM = 0, Backlog = 444
- 11.01.2027: Geplante PM = 222, Tatsächliche PM = 854, Backlog = 1332
- 12.01.2027: Geplante PM = 222, Tatsächliche PM = 159, Fertiggestellte PM = 854, Backlog = 700

---

## Mögliche Ursachen

### 1. Backlog-Berechnung

**Aktuelle Logik:**
```python
Backlog = geplante PM - fertiggestellte PM + Backlog gestern
```

**Prüfung:**
- 12.01.2027: Backlog = 222 - 854 + 1332 = 700 ✅ (korrekt)

**Problem:** Der Backlog wird korrekt berechnet, ABER:
- Wenn "Fertiggestellte PM" > "Geplante PM", wird der Backlog reduziert
- Das ist korrekt, ABER: Die "Tatsächliche PM" basiert auf `Produktionsbedarf = Nachfrage + Backlog`
- Wenn der Backlog reduziert wird, sollte die "Tatsächliche PM" auch reduziert werden

**Verdacht:** Die "Tatsächliche PM" wird einmal berechnet (mit Backlog), aber wenn der Backlog später reduziert wird (durch "Fertiggestellte PM"), wird die "Tatsächliche PM" nicht neu berechnet.

### 2. Produktionslogik: Rang 5-8 Rest-Verteilung

**Aktuelle Logik (Rang 5-8):**
```python
base_qty = min(demand, proportional, minimal)
remaining_capacity = daily_capacity - total_scheduled_so_far
remaining_demand = demand - base_qty

if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production
```

**Problem:** Die Rest-Verteilung für Rang 5-8 kann dazu führen, dass mehr produziert wird als der Produktionsbedarf (`demand`).

**Beispiel:**
- Produktionsbedarf (demand) = 222
- Anteilige Produktion (proportional) = 300
- Minimale Produktion (minimal) = 500
- base_qty = min(222, 300, 500) = 222
- remaining_demand = 222 - 222 = 0
- rest_production = min(remaining_capacity, 500, 0) = 0
- scheduled_qty = 222 + 0 = 222 ✅

**ABER:** Wenn `remaining_demand` falsch berechnet wird oder wenn `rest_production` nicht korrekt auf `remaining_demand` begrenzt wird, kann mehr produziert werden.

### 3. Sicherheitsprüfung: Kapazitätsüberschreitung

**Aktuelle Logik:**
```python
total_scheduled = sum(scheduled_production_by_product.values())
if total_scheduled > daily_capacity:
    scale_factor = daily_capacity / total_scheduled
    # Proportionale Reduktion
```

**Problem:** Diese Prüfung stellt sicher, dass die Summe nicht die Kapazität überschreitet, ABER sie prüft NICHT, ob die Summe den Produktionsbedarf überschreitet.

**Beispiel:**
- Produktionsbedarf (gesamt) = 1000
- Kapazität = 3120
- Summe(scheduled_production) = 1500
- Prüfung: 1500 < 3120 ✅ (keine Reduktion)
- ABER: 1500 > 1000 ❌ (mehr produziert als benötigt)

### 4. Dynamische Neuberechnung mit Rang-Logik

**Problem:** In `_recalculate_all_products_with_rank_logic()` wird die Produktion neu berechnet, aber:
- Die Funktion verwendet `production_demand_by_product = demand + backlog`
- Wenn der Backlog bereits reduziert wurde (durch "Fertiggestellte PM"), wird er trotzdem noch einmal addiert

**Verdacht:** Die dynamische Neuberechnung verwendet den Backlog vom Vortag, aber dieser Backlog wurde bereits durch "Fertiggestellte PM" reduziert. Das führt zu einer doppelten Berücksichtigung.

---

## Konkrete Prüfung

### Prüfung 1: Wird mehr produziert als der Produktionsbedarf?

**In `production_planner.py` (Zeile 239-254):**
```python
if rank <= 4:
    scheduled_qty = min(demand, proportional, minimal)
else:
    base_qty = min(demand, proportional, minimal)
    remaining_demand = demand - base_qty
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production
```

**Prüfung:** `scheduled_qty` sollte niemals größer sein als `demand` (Produktionsbedarf).

**ABER:** Für Rang 5-8: `scheduled_qty = base_qty + rest_production`
- `base_qty <= demand` ✅
- `rest_production <= remaining_demand` ✅
- `remaining_demand = demand - base_qty` ✅
- Also: `scheduled_qty = base_qty + rest_production <= base_qty + remaining_demand = demand` ✅

**Ergebnis:** Die Logik sollte korrekt sein. `scheduled_qty` sollte niemals größer sein als `demand`.

### Prüfung 2: Wird der Backlog korrekt reduziert?

**In `production_planner.py` (Zeile 380-381):**
```python
new_backlog = max(0.0, planned_pm - finished_pm + old_backlog)
```

**Prüfung:** Wenn `finished_pm > planned_pm + old_backlog`, dann wird `new_backlog = 0` (korrekt).

**ABER:** Die "Tatsächliche PM" wurde bereits mit `old_backlog` berechnet. Wenn `finished_pm` den Backlog überkompensiert, wird mehr "fertiggestellt" als "produziert" wurde.

**Beispiel:**
- Geplante PM = 222
- Backlog gestern = 1332
- Fertiggestellte PM = 854 (von gestern produziert)
- Neuer Backlog = 222 - 854 + 1332 = 700 ✅

**Problem:** Die "Tatsächliche PM" von gestern (854) wurde mit einem Backlog von 1110 berechnet. Aber heute wird sie als "Fertiggestellte PM" verwendet, um einen Backlog von 1332 zu reduzieren. Das ist inkonsistent.

### Prüfung 3: Wird die "Tatsächliche PM" korrekt auf Basis des Produktionsbedarfs begrenzt?

**In `_recalculate_all_products_with_rank_logic()` (Zeile 102-107):**
```python
production_demand_by_product = {}
for product in MasterData.BOM.keys():
    demand = product_demands_new.get(product, 0)
    backlog = backlog_by_product.get(product, 0.0)
    production_demand_by_product[product] = demand + backlog
```

**Prüfung:** Der Produktionsbedarf wird korrekt berechnet als `demand + backlog`.

**ABER:** Wenn die "Tatsächliche PM" später dynamisch neu berechnet wird, wird der Backlog vom Vortag verwendet. Dieser Backlog wurde aber bereits durch "Fertiggestellte PM" reduziert. Das führt zu einer Inkonsistenz.

---

## Das eigentliche Problem

**Die "Tatsächliche PM" wird mit einem Backlog berechnet, der später durch "Fertiggestellte PM" reduziert wird. Aber die "Tatsächliche PM" wird nicht neu berechnet, wenn der Backlog reduziert wird.**

**Beispiel:**
1. **Tag 1:** Backlog = 1000, Produktionsbedarf = 222 + 1000 = 1222, Tatsächliche PM = 854 (Material-Limit)
2. **Tag 2:** Fertiggestellte PM = 854, Backlog = 222 - 854 + 1000 = 368
3. **Problem:** Die "Tatsächliche PM" von Tag 1 (854) wurde mit Backlog = 1000 berechnet, aber der Backlog wurde auf 368 reduziert. Die "Tatsächliche PM" sollte eigentlich niedriger sein, wenn der Backlog reduziert wird.

**ABER:** Das ist nicht das Problem, weil die "Tatsächliche PM" die Produktion ist, die heute geplant wird. Sie sollte auf Basis des Backlogs vom Vortag berechnet werden, nicht auf Basis des reduzierten Backlogs.

---

## Die wahre Ursache

**Ich vermute:** Die "Tatsächliche PM" wird in der dynamischen Neuberechnung mit einem Backlog berechnet, der bereits durch "Fertiggestellte PM" reduziert wurde. Das führt dazu, dass mehr produziert wird als nötig.

**Oder:** Die Rang-Logik für Rang 5-8 produziert mehr als der Produktionsbedarf, weil `rest_production` nicht korrekt auf `remaining_demand` begrenzt wird.

**Oder:** Die Sicherheitsprüfung prüft nur die Kapazität, nicht den Produktionsbedarf.
