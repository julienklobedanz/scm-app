#!/usr/bin/env python3
"""
Debug: Warum wird mehr produziert als der Produktionsbedarf erlaubt?
"""

import math

# Beispiel: 06.08.2027
# Geplante PM = 454
# Backlog_vortag = 0
# Produktionsbedarf = 454 + 0 = 454
# Tatsächliche PM = 1103

# Simuliere die Rang-Logik
demand = 454.0  # Produktionsbedarf
daily_capacity = 3120.0  # 3 Schichten * 8 Stunden * 130 Kapazität/Stunde
minimal = 1103.0  # Material verfügbar (angenommen)

# Anteilige Produktion
total_production_demand = 454.0  # Angenommen nur ein Produkt
proportional = math.floor(demand * daily_capacity / total_production_demand)
print(f"Anteilige Produktion: {proportional}")

# Rang (angenommen Rang 5-8)
rank = 5
base_qty = min(demand, proportional, minimal)
print(f"Base Qty: {base_qty}")

remaining_capacity = daily_capacity - 0.0  # total_scheduled_so_far = 0
remaining_demand = max(0.0, demand - base_qty)
print(f"Remaining Demand: {remaining_demand}")

if remaining_capacity > 0:
    rest_production = min(remaining_capacity, minimal, remaining_demand)
    scheduled_qty = base_qty + rest_production
    print(f"Rest Production: {rest_production}")
    print(f"Scheduled Qty (vor Prüfung): {scheduled_qty}")
    
    # Prüfung
    scheduled_qty = min(max(0.0, scheduled_qty), demand)
    print(f"Scheduled Qty (nach Prüfung): {scheduled_qty}")
    print(f"Scheduled Qty <= Demand: {scheduled_qty <= demand}")

# ABER: Was wenn mehrere Produkte?
print("\n=== MEHRERE PRODUKTE ===")
products = [
    {"demand": 454.0, "minimal": 1103.0, "rank": 5},
    {"demand": 200.0, "minimal": 500.0, "rank": 6},
]

total_production_demand = sum(p["demand"] for p in products)
print(f"Total Production Demand: {total_production_demand}")

total_scheduled_so_far = 0.0
for i, product in enumerate(products):
    demand_p = product["demand"]
    minimal_p = product["minimal"]
    rank_p = product["rank"]
    
    proportional_p = math.floor(demand_p * daily_capacity / total_production_demand)
    print(f"\nProdukt {i+1}:")
    print(f"  Demand: {demand_p}")
    print(f"  Proportional: {proportional_p}")
    print(f"  Minimal: {minimal_p}")
    
    if rank_p <= 4:
        scheduled_qty = min(demand_p, proportional_p, minimal_p)
    else:
        base_qty = min(demand_p, proportional_p, minimal_p)
        remaining_capacity = daily_capacity - total_scheduled_so_far
        remaining_demand = max(0.0, demand_p - base_qty)
        
        if remaining_capacity > 0:
            rest_production = min(remaining_capacity, minimal_p, remaining_demand)
            scheduled_qty = base_qty + rest_production
        else:
            scheduled_qty = base_qty
    
    scheduled_qty = min(max(0.0, scheduled_qty), demand_p)
    print(f"  Scheduled Qty: {scheduled_qty}")
    print(f"  Scheduled Qty <= Demand: {scheduled_qty <= demand_p}")
    
    total_scheduled_so_far += scheduled_qty

print(f"\nTotal Scheduled: {total_scheduled_so_far}")
print(f"Total Production Demand: {total_production_demand}")
print(f"Total Scheduled <= Total Demand: {total_scheduled_so_far <= total_production_demand}")
