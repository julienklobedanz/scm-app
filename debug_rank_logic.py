#!/usr/bin/env python3
"""
Debug: Simuliert Rang-Logik für MTB Allrounder am 08.02.2027
"""

# Beispiel: MTB Allrounder am 08.02.2027
# Aus CSV: Tatsächliche PM = 786, Materialverbrauch = 811 (Differenz: +25)

demand = 333  # Geplante PM (ohne Backlog)
backlog = 0  # Backlog vom Vortag
production_demand = demand + backlog  # = 333

daily_capacity = 3120.0  # 3 Schichten * 8 Stunden * 130 Stück/Stunde
total_production_demand_all = 2000.0  # Angenommen (Summe aller Produkte)

# Anteilige Produktion
proportional = int(production_demand * daily_capacity / total_production_demand_all)
print(f"Produktionsbedarf: {production_demand}")
print(f"Anteilige Produktion: {proportional}")

# Material verfügbar
minimal = 1787.0  # Spark verfügbar

# Rang-basierte Berechnung (angenommen Rang 5-8)
rank = 5
base_qty = min(production_demand, proportional, minimal)
print(f"Base Qty: {base_qty}")

remaining_capacity = daily_capacity - 0.0  # Angenommen keine andere Produktion bisher
remaining_demand = max(0.0, production_demand - base_qty)
print(f"Remaining Demand: {remaining_demand}")

if remaining_capacity > 0:
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production
    print(f"Rest Production: {rest_production}")
    print(f"Scheduled Qty (vor Prüfung): {scheduled_qty}")
else:
    scheduled_qty = base_qty
    print(f"Scheduled Qty (vor Prüfung): {scheduled_qty}")

# Prüfung in Zeile 184
scheduled_qty_after_cap = min(max(0.0, scheduled_qty), production_demand)
print(f"Scheduled Qty (nach Cap in Zeile 184): {scheduled_qty_after_cap}")

# Material wird reduziert basierend auf scheduled_qty_after_cap
material_consumed = scheduled_qty_after_cap
print(f"Material verbraucht: {material_consumed}")

# Finale Prüfung (Zeile 236)
if scheduled_qty_after_cap > production_demand:
    print(f"\n⚠️ Finale Prüfung würde greifen (scheduled_qty > demand)")
    print(f"   Reduktion: {scheduled_qty_after_cap - production_demand}")
    print(f"   Material würde zurückgegeben")
else:
    print(f"\n✅ Finale Prüfung greift nicht (scheduled_qty <= demand)")
    print(f"   scheduled_qty_after_cap = {scheduled_qty_after_cap}, demand = {production_demand}")

print(f"\nErgebnis: Tatsächliche PM = {scheduled_qty_after_cap}, Materialverbrauch = {material_consumed}")
