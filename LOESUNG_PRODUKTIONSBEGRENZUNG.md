# Lösung: Produktionsbegrenzung auf Geplante PM

## Problem

**Warum wird mehr produziert als geplant, wenn Backlog = 0?**

**Beispiel: 06.08.2027**
- Geplante PM = 454 (mit Marketing bereits berücksichtigt)
- Backlog = 0
- Produktionsbedarf = 454 + 0 = 454
- **Tatsächliche PM = 1103** (2.43x mehr!)

## Analyse

### Die Logik sollte korrekt sein

Meine Test-Berechnung zeigt:
- Scheduled Qty (nach Prüfung) = 454 ✅
- Scheduled Qty <= Produktionsbedarf: True ✅

**ABER:** Die CSV zeigt 1103, nicht 454!

### Mögliche Ursachen

1. **Statische Werte werden verwendet:**
   - Die Simulation wurde vor den Korrekturen ausgeführt
   - Die statischen Werte sind falsch (1103 statt 454)
   - Die dynamische Neuberechnung wird nicht ausgeführt, weil sich Inputs nicht geändert haben

2. **Die Prüfung wird nicht ausgeführt:**
   - Die Prüfung `scheduled_qty = min(scheduled_qty, demand)` wird möglicherweise nicht ausgeführt
   - Oder sie wird ausgeführt, aber `demand` ist falsch

3. **Die Sicherheitsprüfung 2 greift nicht:**
   - Die Prüfung prüft nur die Summe, nicht einzelne Produkte
   - Wenn einzelne Produkte mehr produzieren, aber die Summe noch unter dem Gesamtbedarf liegt, greift sie nicht

## Die Lösung

### Option 1: Zusätzliche Prüfung nach der Berechnung

**Füge eine explizite Prüfung hinzu, die sicherstellt, dass `scheduled_qty <= demand` ist:**

```python
# Nach der Berechnung von scheduled_qty für jedes Produkt
scheduled_qty = min(max(0.0, scheduled_qty), demand)
```

**Diese Prüfung ist bereits implementiert!** ABER: Sie wird möglicherweise nicht ausgeführt, wenn statische Werte verwendet werden.

### Option 2: Dynamische Neuberechnung immer ausführen, wenn statische Werte falsch sind

**Prüfe, ob statische Werte korrekt sind, und führe Neuberechnung aus, wenn nicht:**

```python
# Prüfe ob statische Werte korrekt sind
base_tatsaechliche_pm = info['base_tatsaechliche_pm']
base_geplante_pm = info['base_geplante_pm']
base_backlog = ...  # Hole Backlog vom Vortag

production_demand_expected = base_geplante_pm + base_backlog

if base_tatsaechliche_pm > production_demand_expected:
    # Statische Werte sind falsch → Neuberechnung
    inputs_changed = True
```

### Option 3: Explizite Begrenzung auf Geplante PM

**Die einfachste Lösung:** Stelle sicher, dass `scheduled_qty` niemals größer ist als die "Geplante PM" (ohne Backlog):

```python
# Nach der Berechnung
planned_pm = product_demands_new.get(product, 0)  # Geplante PM (mit Marketing)
scheduled_qty = min(scheduled_qty, planned_pm)  # Begrenze auf Geplante PM
```

**ABER:** Das ist nicht korrekt, weil der Produktionsbedarf = Geplante PM + Backlog ist. Wenn Backlog > 0, sollte mehr produziert werden.

## Die korrekte Lösung

**Die Lösung ist:** Stelle sicher, dass die Prüfung `scheduled_qty = min(scheduled_qty, demand)` IMMER ausgeführt wird, auch wenn statische Werte verwendet werden.

**Implementierung:**
1. Prüfe, ob statische Werte korrekt sind (Option 2)
2. Wenn nicht, führe dynamische Neuberechnung aus
3. Stelle sicher, dass die Prüfung in der dynamischen Neuberechnung ausgeführt wird
