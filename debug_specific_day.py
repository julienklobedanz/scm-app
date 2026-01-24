#!/usr/bin/env python3
"""
Debug: Warum wird am 06.08.2027 mehr produziert als erlaubt?
"""

import math

# Daten aus CSV für 06.08.2027
# Geplante PM = 454
# Backlog_vortag = 0 (am 05.08.2027)
# Produktionsbedarf = 454 + 0 = 454
# Tatsächliche PM = 1103

# Angenommene Werte (basierend auf CSV)
geplante_pm = 454
backlog_vortag = 0
produktionsbedarf = geplante_pm + backlog_vortag  # = 454
tatsaechliche_pm = 1103

print(f"Geplante PM: {geplante_pm}")
print(f"Backlog vom Vortag: {backlog_vortag}")
print(f"Produktionsbedarf: {produktionsbedarf}")
print(f"Tatsächliche PM: {tatsaechliche_pm}")
print(f"Problem: Tatsächliche PM > Produktionsbedarf: {tatsaechliche_pm > produktionsbedarf}")
print()

# Simuliere die Produktionslogik
daily_capacity = 3120.0  # 3 Schichten * 8 Stunden * 130
minimal = 1134.0  # Aus CSV: Spark = 1134

# Angenommen: Es gibt mehrere Produkte, die den gleichen Sattel verwenden
# MTB Allrounder verwendet "Spark" Sattel
# Lass uns prüfen, ob andere Produkte auch "Spark" verwenden

# Für MTB Allrounder:
demand_allrounder = 454.0
total_production_demand_all_products = 2000.0  # Angenommen (Summe aller Produkte)

proportional_allrounder = math.floor(demand_allrounder * daily_capacity / total_production_demand_all_products)
print(f"Anteilige Produktion (MTB Allrounder): {proportional_allrounder}")

# Rang (angenommen Rang 5-8)
rank = 5
base_qty = min(demand_allrounder, proportional_allrounder, minimal)
print(f"Base Qty: {base_qty}")

# Angenommen: Andere Produkte haben bereits produziert
total_scheduled_so_far = 0.0  # Oder ein anderer Wert
remaining_capacity = daily_capacity - total_scheduled_so_far
remaining_demand = max(0.0, demand_allrounder - base_qty)

print(f"Remaining Capacity: {remaining_capacity}")
print(f"Remaining Demand: {remaining_demand}")

if remaining_capacity > 0:
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production
    print(f"Rest Production: {rest_production}")
    print(f"Scheduled Qty (vor Prüfung): {scheduled_qty}")
    
    # Prüfung
    scheduled_qty_after_check = min(max(0.0, scheduled_qty), demand_allrounder)
    print(f"Scheduled Qty (nach Prüfung): {scheduled_qty_after_check}")
    print(f"Scheduled Qty <= Demand: {scheduled_qty_after_check <= demand_allrounder}")
    
    if scheduled_qty_after_check != tatsaechliche_pm:
        print(f"\n❌ PROBLEM: Berechnete PM ({scheduled_qty_after_check}) != Tatsächliche PM ({tatsaechliche_pm})")
        print(f"   Das bedeutet, dass die Prüfung nicht greift oder die Berechnung anders ist.")

# Prüfe: Was wenn minimal > demand?
print("\n=== TEST: minimal > demand ===")
demand_test = 454.0
minimal_test = 1103.0
proportional_test = 3120.0

base_qty_test = min(demand_test, proportional_test, minimal_test)  # = 454
remaining_demand_test = max(0.0, demand_test - base_qty_test)  # = 0
rest_production_test = min(remaining_capacity, minimal_test, remaining_demand_test)  # = min(3120, 1103, 0) = 0
scheduled_qty_test = base_qty_test + rest_production_test  # = 454 + 0 = 454

print(f"Demand: {demand_test}")
print(f"Minimal: {minimal_test}")
print(f"Base Qty: {base_qty_test}")
print(f"Remaining Demand: {remaining_demand_test}")
print(f"Rest Production: {rest_production_test}")
print(f"Scheduled Qty: {scheduled_qty_test}")
print(f"Scheduled Qty <= Demand: {scheduled_qty_test <= demand_test}")

# ABER: Was wenn die Sicherheitsprüfung 2 nicht greift?
print("\n=== TEST: Sicherheitsprüfung 2 ===")
total_production_demand_all = 2000.0  # Summe aller Produktionsbedarfe
total_scheduled_all = 3000.0  # Summe aller scheduled_qty

print(f"Total Production Demand: {total_production_demand_all}")
print(f"Total Scheduled: {total_scheduled_all}")
print(f"Total Scheduled > Total Demand: {total_scheduled_all > total_production_demand_all}")

if total_scheduled_all > total_production_demand_all:
    scale_factor = total_production_demand_all / total_scheduled_all
    scheduled_qty_scaled = scheduled_qty_test * scale_factor
    print(f"Scale Factor: {scale_factor}")
    print(f"Scheduled Qty (nach Skalierung): {scheduled_qty_scaled}")
    print(f"Scheduled Qty (nach Skalierung) <= Demand: {scheduled_qty_scaled <= demand_test}")
