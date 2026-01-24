# Problem: Materialverbrauch > Tatsächliche PM

## Problem-Identifikation

Die "tatsächliche PM" in der Produktionstabelle stimmt nicht mit dem tatsächlichen Materialverbrauch überein.

**Beispiel 08.02.2027:**
- Tatsächliche PM (in CSV): 786
- Tatsächlicher Materialverbrauch: 811
- Differenz: +25

**Beispiel 15.02.2027:**
- Tatsächliche PM (in CSV): 705
- Tatsächlicher Materialverbrauch: 811
- Differenz: +106

## Root Cause Analysis

### Problem in `ui/production_calculations.py` (Zeile 227-236)

```python
# Schritt 6: Finale Prüfung - Stelle sicher, dass jedes Produkt nicht mehr produziert als sein Produktionsbedarf
for product in products_list:
    demand = production_demand_by_product.get(product, 0.0)
    scheduled_qty = scheduled_production_by_product.get(product, 0.0)
    
    # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
    if scheduled_qty > demand:
        scheduled_production_by_product[product] = demand
```

**Problem:** 
1. Material wird bereits reduziert basierend auf `scheduled_qty` (Zeile 190)
2. Später wird `scheduled_production_by_product[product]` auf `demand` begrenzt (Zeile 236)
3. **ABER:** Das Material wurde bereits verbraucht und wird nicht zurückgegeben!

### Problem in `simulation/production_planner.py` (Zeile 306-315)

Das gleiche Problem existiert auch im statischen System:

```python
# 8. Finale Prüfung - Stelle sicher, dass jedes Produkt nicht mehr produziert als sein Produktionsbedarf
for product in products_list:
    demand = production_demand_by_product.get(product, 0.0)
    scheduled_qty = scheduled_production_by_product.get(product, 0.0)
    
    # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
    if scheduled_qty > demand:
        scheduled_production_by_product[product] = demand
```

**Problem:** 
- Material wurde bereits reduziert (Zeile 265)
- Produktion wird reduziert (Zeile 315)
- **ABER:** Material wird nicht zurückgegeben!

## Lösung

Die finale Prüfung muss auch Material zurückgeben, wenn die Produktion reduziert wird:

```python
# Schritt 6: Finale Prüfung - Stelle sicher, dass jedes Produkt nicht mehr produziert als sein Produktionsbedarf
for product in products_list:
    demand = production_demand_by_product.get(product, 0.0)
    scheduled_qty = scheduled_production_by_product.get(product, 0.0)
    
    # KRITISCH: Stelle sicher, dass scheduled_qty nicht größer ist als demand
    if scheduled_qty > demand:
        old_qty = scheduled_production_by_product[product]
        scheduled_production_by_product[product] = demand
        reduction = old_qty - demand
        
        # Gebe reduziertes Material zurück
        if reduction > 0:
            required_saddle_type = MasterData.BOM[product]['saddle']
            stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
```

## Warum passiert das?

Die finale Prüfung wird **NACH** den Sicherheitsprüfungen 1 und 2 ausgeführt. Diese Prüfungen geben bereits Material zurück, wenn die Produktion reduziert wird. Aber die finale Prüfung (Schritt 6) prüft nur die einzelnen Produkte und gibt kein Material zurück.

Das Problem tritt auf, wenn:
1. Ein Produkt mehr produziert wird als sein `demand` (z.B. durch Rang-Logik)
2. Die Sicherheitsprüfungen 1 und 2 greifen nicht (weil die Summe korrekt ist)
3. Die finale Prüfung reduziert die Produktion, aber gibt kein Material zurück

## Betroffene Stellen

1. `ui/production_calculations.py` - Zeile 227-236
2. `simulation/production_planner.py` - Zeile 306-315
