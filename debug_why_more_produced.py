#!/usr/bin/env python3
"""
Debug: Warum wird mehr produziert als geplant (Backlog = 0)?
"""

import math

# Beispiel: 06.08.2027 - MTB Allrounder
geplante_pm = 454  # Mit Marketing bereits berücksichtigt
backlog = 0
produktionsbedarf = geplante_pm + backlog  # = 454

# Angenommene Werte
daily_capacity = 3120.0  # 3 Schichten * 8 Stunden * 130
minimal = 1134.0  # Material verfügbar (aus CSV)

print("=" * 80)
print("ANALYSE: Warum wird mehr produziert als geplant?")
print("=" * 80)
print()
print(f"Geplante PM (mit Marketing): {geplante_pm}")
print(f"Backlog: {backlog}")
print(f"Produktionsbedarf: {produktionsbedarf}")
print(f"Kapazität: {daily_capacity}")
print(f"Material verfügbar: {minimal}")
print()

# Simuliere verschiedene Szenarien
print("=" * 80)
print("SZENARIO 1: Nur ein Produkt hat Produktionsbedarf")
print("=" * 80)
total_production_demand = 454.0  # Nur MTB Allrounder

proportional = math.floor(produktionsbedarf * daily_capacity / total_production_demand)
print(f"Anteilige Produktion: {proportional}")
print(f"Proportional > Produktionsbedarf: {proportional > produktionsbedarf}")

# Rang 1-4
rank = 4
scheduled_qty_1_4 = min(produktionsbedarf, proportional, minimal)
print(f"\nRang 1-4: scheduled_qty = min({produktionsbedarf}, {proportional}, {minimal}) = {scheduled_qty_1_4}")
print(f"Scheduled Qty <= Produktionsbedarf: {scheduled_qty_1_4 <= produktionsbedarf}")

# Rang 5-8
rank = 5
base_qty = min(produktionsbedarf, proportional, minimal)
remaining_demand = max(0.0, produktionsbedarf - base_qty)
remaining_capacity = daily_capacity - 0.0  # total_scheduled_so_far = 0
rest_production = min(remaining_capacity, minimal, remaining_demand)
scheduled_qty_5_8 = base_qty + rest_production
print(f"\nRang 5-8:")
print(f"  base_qty = min({produktionsbedarf}, {proportional}, {minimal}) = {base_qty}")
print(f"  remaining_demand = max(0.0, {produktionsbedarf} - {base_qty}) = {remaining_demand}")
print(f"  rest_production = min({remaining_capacity}, {minimal}, {remaining_demand}) = {rest_production}")
print(f"  scheduled_qty = {base_qty} + {rest_production} = {scheduled_qty_5_8}")
print(f"Scheduled Qty <= Produktionsbedarf: {scheduled_qty_5_8 <= produktionsbedarf}")

# Prüfung
scheduled_qty_after_check = min(max(0.0, scheduled_qty_5_8), produktionsbedarf)
print(f"\nNach Prüfung: scheduled_qty = min(max(0.0, {scheduled_qty_5_8}), {produktionsbedarf}) = {scheduled_qty_after_check}")
print(f"Ergebnis: {scheduled_qty_after_check} (sollte {produktionsbedarf} sein)")

print()
print("=" * 80)
print("SZENARIO 2: Mehrere Produkte haben Produktionsbedarf")
print("=" * 80)

# Angenommen: 8 Produkte, alle mit ähnlichem Bedarf
num_products = 8
production_demand_per_product = 454.0
total_production_demand = num_products * production_demand_per_product  # = 3632

proportional_multi = math.floor(produktionsbedarf * daily_capacity / total_production_demand)
print(f"Gesamt-Produktionsbedarf (alle Produkte): {total_production_demand}")
print(f"Anteilige Produktion (MTB Allrounder): {proportional_multi}")
print(f"Proportional > Produktionsbedarf: {proportional_multi > produktionsbedarf}")

# Rang 1-4
scheduled_qty_1_4_multi = min(produktionsbedarf, proportional_multi, minimal)
print(f"\nRang 1-4: scheduled_qty = min({produktionsbedarf}, {proportional_multi}, {minimal}) = {scheduled_qty_1_4_multi}")
print(f"Scheduled Qty <= Produktionsbedarf: {scheduled_qty_1_4_multi <= produktionsbedarf}")

print()
print("=" * 80)
print("SZENARIO 3: Was wenn minimal > Produktionsbedarf?")
print("=" * 80)

# Wenn Material viel größer ist als Produktionsbedarf
minimal_large = 2000.0
proportional_test = 3120.0  # Wie in Szenario 1

base_qty_test = min(produktionsbedarf, proportional_test, minimal_large)
remaining_demand_test = max(0.0, produktionsbedarf - base_qty_test)
rest_production_test = min(remaining_capacity, minimal_large, remaining_demand_test)
scheduled_qty_test = base_qty_test + rest_production_test

print(f"Minimal (Material): {minimal_large}")
print(f"Base Qty: {base_qty_test}")
print(f"Remaining Demand: {remaining_demand_test}")
print(f"Rest Production: {rest_production_test}")
print(f"Scheduled Qty: {scheduled_qty_test}")
print(f"Scheduled Qty <= Produktionsbedarf: {scheduled_qty_test <= produktionsbedarf}")

# Prüfung
scheduled_qty_after_check_test = min(max(0.0, scheduled_qty_test), produktionsbedarf)
print(f"\nNach Prüfung: {scheduled_qty_after_check_test}")
print(f"Ergebnis korrekt: {scheduled_qty_after_check_test == produktionsbedarf}")

print()
print("=" * 80)
print("VERDACHT: Was wenn die Prüfung nicht ausgeführt wird?")
print("=" * 80)

# Was wenn scheduled_qty VOR der Prüfung bereits > demand ist?
scheduled_qty_before_check = 1103.0  # Wie in CSV
demand_check = 454.0

print(f"Scheduled Qty (vor Prüfung): {scheduled_qty_before_check}")
print(f"Produktionsbedarf: {demand_check}")
print(f"Sollte nach Prüfung sein: {min(scheduled_qty_before_check, demand_check)}")

# Was wenn die Prüfung nicht ausgeführt wird?
print(f"\nWenn Prüfung NICHT ausgeführt wird: {scheduled_qty_before_check} (falsch!)")
print(f"Wenn Prüfung ausgeführt wird: {min(scheduled_qty_before_check, demand_check)} (korrekt!)")
