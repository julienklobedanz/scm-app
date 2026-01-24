# Problem identifiziert: Tatsächliche PM > Produktionsbedarf

## Ergebnis der Prüfung

### ❌ KRITISCHES PROBLEM: 89 Tage mit Überschreitung

**Gefunden:** 89 Tage, an denen "Tatsächliche PM" > Produktionsbedarf ist!

**Beispiele:**
- **06.08.2027:** Geplante PM=454, Backlog_vortag=0, Produktionsbedarf=454, **Tatsächliche PM=1103** (2.43x mehr!)
- **11.08.2027:** Geplante PM=454, Backlog_vortag=0, Produktionsbedarf=454, **Tatsächliche PM=1101** (2.43x mehr!)
- **22.04.2027:** Geplante PM=807, Backlog_vortag=0, Produktionsbedarf=807, **Tatsächliche PM=1048** (1.30x mehr!)

### ✅ Backlog-Berechnung: KORREKT

Die Backlog-Berechnung funktioniert korrekt.

### 📊 Summen-Analyse

- **Summe(Geplante PM):** 111000
- **Summe(Tatsächliche PM):** 132678 (+21678)
- **Summe(Produktionsbedarf):** 405385
- **Summe(Fertiggestellte PM):** 172526

**Wichtig:** Die Summe der "Tatsächlichen PM" ist **niedriger** als die Summe des Produktionsbedarfs, was bedeutet, dass nicht genug produziert wurde. ABER: An einzelnen Tagen wird **mehr** produziert als der Produktionsbedarf erlaubt!

---

## Ursache: Rang-Logik für Rang 5-8

### Das Problem

**Aktuelle Logik (Rang 5-8):**
```python
base_qty = min(demand, proportional, minimal)
remaining_demand = demand - base_qty
rest_production = min(remaining_capacity, minimal, remaining_demand)
scheduled_qty = base_qty + rest_production
```

**Mathematisch sollte gelten:**
- `scheduled_qty = base_qty + rest_production`
- `rest_production <= remaining_demand`
- Also: `scheduled_qty <= base_qty + remaining_demand = demand` ✅

**ABER:** In der Praxis wird `scheduled_qty > demand` beobachtet!

### Mögliche Ursachen

1. **`remaining_demand` wird falsch berechnet:**
   - Wenn `base_qty` nicht korrekt ist (z.B. durch Rundungsfehler)
   - Dann ist `remaining_demand = demand - base_qty` falsch

2. **`rest_production` wird nicht korrekt auf `remaining_demand` begrenzt:**
   - Die Bedingung `min(remaining_capacity, minimal, remaining_demand)` sollte `remaining_demand` berücksichtigen
   - ABER: Wenn `minimal` oder `remaining_capacity` größer sind, könnte `rest_production` größer sein als `remaining_demand`

3. **Die Sicherheitsprüfung prüft nur die Kapazität, nicht den Produktionsbedarf:**
   - Die Prüfung `if total_scheduled > daily_capacity` stellt sicher, dass die Kapazität nicht überschritten wird
   - ABER: Sie prüft NICHT, ob `total_scheduled <= total_production_demand`

---

## Konkrete Beispiele aus der CSV

### Beispiel 1: 06.08.2027
- Geplante PM = 454
- Backlog_vortag = 0
- Produktionsbedarf = 454 + 0 = 454
- **Tatsächliche PM = 1103** ❌ (2.43x mehr!)

**Was passiert hier?**
- Die Produktionslogik produziert 1103, obwohl der Produktionsbedarf nur 454 ist
- Das bedeutet, dass die Rang-Logik mehr produziert als erlaubt

### Beispiel 2: 22.04.2027
- Geplante PM = 807
- Backlog_vortag = 0
- Produktionsbedarf = 807 + 0 = 807
- **Tatsächliche PM = 1048** ❌ (1.30x mehr!)

---

## Lösung

### Option 1: Zusätzliche Prüfung in der Produktionslogik

**Nach der Berechnung von `scheduled_qty`:**
```python
# Stelle sicher, dass scheduled_qty nicht größer ist als demand
scheduled_qty = min(scheduled_qty, demand)
```

### Option 2: Prüfung der Summe gegen Produktionsbedarf

**Nach der Berechnung aller Produkte:**
```python
total_production_demand = sum(production_demand_by_product.values())
total_scheduled = sum(scheduled_production_by_product.values())

if total_scheduled > total_production_demand:
    # Proportionale Reduktion auf Produktionsbedarf
    scale_factor = total_production_demand / total_scheduled
    for product in sorted_products:
        scheduled_production_by_product[product] *= scale_factor
```

### Option 3: Korrektur der Rang-Logik

**Prüfe, ob `remaining_demand` korrekt berechnet wird:**
```python
remaining_demand = max(0, demand - base_qty)  # Stelle sicher, dass es nicht negativ ist
rest_production = min(remaining_capacity, minimal, remaining_demand)
scheduled_qty = base_qty + rest_production

# Zusätzliche Sicherheitsprüfung
scheduled_qty = min(scheduled_qty, demand)
```

---

## Empfehlung

**Implementiere Option 1 + Option 2:**
1. Stelle sicher, dass `scheduled_qty <= demand` für jedes Produkt (Option 1)
2. Stelle sicher, dass `Summe(scheduled_qty) <= Summe(demand)` (Option 2)

Dies stellt sicher, dass niemals mehr produziert wird als der Produktionsbedarf erlaubt.
