#!/usr/bin/env python3
"""
Debug: Prüft ob die Prüfung auf falsche statische Werte funktioniert
"""

# Beispiel: 06.08.2027 - MTB Allrounder
# Aus CSV:
base_geplante_pm = 454
base_tatsaechliche_pm = 1103  # Aus statischen Logs
base_backlog = 0  # Am 05.08.2027 (vorheriger Arbeitstag)

production_demand_expected = base_geplante_pm + base_backlog
print(f"Base Geplante PM: {base_geplante_pm}")
print(f"Base Backlog: {base_backlog}")
print(f"Production Demand Expected: {production_demand_expected}")
print(f"Base Tatsächliche PM: {base_tatsaechliche_pm}")
print(f"Base Tatsächliche PM > Production Demand Expected: {base_tatsaechliche_pm > production_demand_expected}")

if base_tatsaechliche_pm > production_demand_expected:
    print("\n✅ Prüfung sollte greifen: static_values_incorrect = True")
    print("   → Dynamische Neuberechnung sollte ausgeführt werden")
else:
    print("\n❌ Prüfung greift nicht: static_values_incorrect = False")
    print("   → Statische Werte werden verwendet (falsch!)")

print("\n" + "=" * 80)
print("PRÜFUNG: Was passiert in der dynamischen Neuberechnung?")
print("=" * 80)

# Simuliere dynamische Neuberechnung
product_demand_new = 454  # Mit Marketing
backlog_new = 0  # Vom vorherigen Arbeitstag
production_demand = product_demand_new + backlog_new  # = 454

daily_capacity = 3120.0
minimal = 1134.0  # Material verfügbar

# Anteilige Produktion
total_production_demand_all = 2000.0  # Angenommen (Summe aller Produkte)
proportional = int(product_demand_new * daily_capacity / total_production_demand_all)
print(f"\nProduktionsbedarf (dieses Produkt): {production_demand}")
print(f"Gesamt-Produktionsbedarf (alle Produkte): {total_production_demand_all}")
print(f"Anteilige Produktion: {proportional}")

# Rang-basierte Berechnung (angenommen Rang 5-8)
rank = 5
base_qty = min(production_demand, proportional, minimal)
remaining_demand = max(0.0, production_demand - base_qty)
remaining_capacity = daily_capacity - 0.0
rest_production = min(remaining_capacity, minimal, remaining_demand)
scheduled_qty = base_qty + rest_production

print(f"\nBase Qty: {base_qty}")
print(f"Remaining Demand: {remaining_demand}")
print(f"Rest Production: {rest_production}")
print(f"Scheduled Qty (vor Prüfung): {scheduled_qty}")

# Prüfung
scheduled_qty_after = min(max(0.0, scheduled_qty), production_demand)
print(f"Scheduled Qty (nach Prüfung): {scheduled_qty_after}")
print(f"Scheduled Qty <= Production Demand: {scheduled_qty_after <= production_demand}")

# Finale Prüfung
if scheduled_qty_after > production_demand:
    scheduled_qty_final = production_demand
    print(f"Scheduled Qty (nach finaler Prüfung): {scheduled_qty_final}")
else:
    scheduled_qty_final = scheduled_qty_after
    print(f"Scheduled Qty (nach finaler Prüfung): {scheduled_qty_final}")

print(f"\nErgebnis: {scheduled_qty_final} (sollte {production_demand} sein)")
