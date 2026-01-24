# Warum wird mehr produziert als geplant (Backlog = 0)?

## Die Frage

**Warum produzieren wir an manchen Tagen mehr als geplant, während der Backlog 0 ist?**

**Beispiel: 06.08.2027**
- Geplante PM = 454 (mit Marketing bereits berücksichtigt)
- Backlog = 0
- Produktionsbedarf = 454 + 0 = 454
- **Tatsächliche PM = 1103** (2.43x mehr!)

## Analyse der Produktionslogik

### Schritt 1: Produktionsbedarf berechnen
```python
production_demand_by_product[product] = planned_demand + backlog
# = 454 + 0 = 454 ✅
```

### Schritt 2: Anteilige Produktion berechnen
```python
proportional = floor(demand * daily_capacity / total_production_demand)
# = floor(454 * 3120 / total_production_demand)
```

**Problem:** `total_production_demand` ist die Summe aller Produkte! Wenn andere Produkte einen höheren Produktionsbedarf haben, wird `proportional` für dieses Produkt kleiner. ABER: Wenn `total_production_demand` klein ist (z.B. nur 454 für dieses Produkt), dann:
- `proportional = floor(454 * 3120 / 454) = 3120` ❌

**Das ist das Problem!** Die anteilige Produktion kann größer sein als der Produktionsbedarf, wenn die Kapazität viel größer ist als der Gesamtbedarf.

### Schritt 3: Rang-basierte Berechnung

**Für Rang 1-4:**
```python
scheduled_qty = min(demand, proportional, minimal)
# = min(454, 3120, 1134) = 454 ✅
```

**Für Rang 5-8:**
```python
base_qty = min(demand, proportional, minimal)
# = min(454, 3120, 1134) = 454 ✅

remaining_demand = max(0.0, demand - base_qty)
# = max(0.0, 454 - 454) = 0 ✅

rest_production = min(remaining_capacity, minimal, remaining_demand)
# = min(remaining_capacity, 1134, 0) = 0 ✅

scheduled_qty = base_qty + rest_production
# = 454 + 0 = 454 ✅
```

**ABER:** Die Prüfung `scheduled_qty = min(scheduled_qty, demand)` sollte das verhindern.

## Das eigentliche Problem

**Ich vermute:** Die Prüfung `scheduled_qty = min(scheduled_qty, demand)` wird ausgeführt, ABER:

1. **Die Prüfung wird NACH der Material-Reduktion ausgeführt:**
   - Material wird während der Berechnung reduziert
   - Wenn mehrere Produkte den gleichen Sattel verwenden, wird Material mehrfach reduziert
   - Die Prüfung wird für jedes Produkt einzeln ausgeführt, aber Material wird global reduziert

2. **Die Prüfung wird VOR der Sicherheitsprüfung 2 ausgeführt:**
   - Sicherheitsprüfung 2 prüft nur die Summe, nicht einzelne Produkte
   - Wenn einzelne Produkte mehr produzieren, aber die Summe noch unter dem Gesamtbedarf liegt, greift sie nicht

3. **Die statischen Werte stammen von einer Simulation VOR den Korrekturen:**
   - Die Simulation wurde vor den Korrekturen ausgeführt
   - Die statischen Werte sind falsch (1103 statt 454)
   - Die dynamische Neuberechnung wird nicht ausgeführt, weil sich Inputs nicht geändert haben

## Die wahre Ursache

**Das Problem ist:** Die anteilige Produktion kann größer sein als der Produktionsbedarf, wenn:
- Die Kapazität viel größer ist als der Gesamtbedarf
- `proportional = floor(demand * capacity / total_demand)` kann sehr groß sein

**Beispiel:**
- Produktionsbedarf (dieses Produkt) = 454
- Gesamt-Produktionsbedarf (alle Produkte) = 2000
- Kapazität = 3120
- `proportional = floor(454 * 3120 / 2000) = floor(708.24) = 708` ✅ (OK)

**ABER:** Wenn Gesamt-Produktionsbedarf sehr klein ist:
- Gesamt-Produktionsbedarf = 454 (nur dieses Produkt)
- `proportional = floor(454 * 3120 / 454) = 3120` ❌ (zu groß!)

**Oder:** Wenn andere Produkte bereits produziert haben:
- `total_scheduled_so_far` ist bereits hoch
- `remaining_capacity` ist klein
- ABER: `minimal` (Material) ist groß (1134)
- `rest_production = min(remaining_capacity, minimal, remaining_demand)`
- Wenn `remaining_capacity` groß ist und `remaining_demand` falsch berechnet wird, kann `rest_production` größer sein als `remaining_demand`

## Lösung

**Die Lösung ist einfach:** Die Prüfung `scheduled_qty = min(scheduled_qty, demand)` sollte das verhindern. ABER: Sie wird möglicherweise nicht ausgeführt oder die statischen Werte werden verwendet.

**Ich muss prüfen:**
1. Wird die Prüfung wirklich ausgeführt?
2. Werden die statischen Werte verwendet statt der dynamischen Neuberechnung?
3. Gibt es einen Fehler in der Berechnung von `remaining_demand`?
