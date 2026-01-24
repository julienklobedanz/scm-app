#!/usr/bin/env python3
"""
Debug: Prüft wie der Backlog in der dynamischen Neuberechnung verwendet wird
"""

# Beispiel: 05.08.2027
# Aus CSV:
planned_pm = 454
actual_pm = 1069
backlog_vortag = 0  # Aus CSV (04.08.2027)

print("=" * 80)
print("ANALYSE: Wie wird der Backlog in der dynamischen Neuberechnung verwendet?")
print("=" * 80)

print(f"\nTag: 05.08.2027")
print(f"Geplante PM: {planned_pm}")
print(f"Tatsächliche PM: {actual_pm}")
print(f"Backlog (Vortag): {backlog_vortag}")

production_demand = planned_pm + backlog_vortag
print(f"\nProduktionsbedarf = Geplante PM + Backlog = {planned_pm} + {backlog_vortag} = {production_demand}")
print(f"Tatsächliche PM = {actual_pm}")
print(f"Differenz = {actual_pm - production_demand} ({(actual_pm / production_demand * 100) if production_demand > 0 else 0:.1f}% mehr)")

print("\n" + "=" * 80)
print("PROBLEM-ANALYSE:")
print("=" * 80)

print("\n1. Die dynamische Neuberechnung liest den Backlog aus den statischen Logs")
print("   → Diese Logs haben möglicherweise noch die ALTE Backlog-Berechnung")
print("   → Oder: Die Logs wurden noch nicht aktualisiert, wenn die Neuberechnung läuft")

print("\n2. Die neue Backlog-Berechnung ist:")
print("   backlog = (planned_pm + old_backlog) - actual_started")
print("   → Das bedeutet: Backlog wird sofort reduziert, wenn produziert wird")
print("   → ABER: Die dynamische Neuberechnung liest den Backlog VOR der Produktion")
print("   → Daher verwendet sie den falschen Backlog (aus statischen Logs)")

print("\n3. Die Rang-Logik produziert basierend auf:")
print("   production_demand = demand + backlog")
print("   → Wenn backlog falsch ist, ist auch production_demand falsch")
print("   → Daher produziert die Rang-Logik mehr als erlaubt")

print("\n" + "=" * 80)
print("LÖSUNG:")
print("=" * 80)

print("\nDie dynamische Neuberechnung muss den Backlog SELBST berechnen,")
print("basierend auf den bereits berechneten Werten der vorherigen Tage.")
print("\nODER:")
print("Die Backlog-Berechnung muss VOR der dynamischen Neuberechnung ausgeführt werden,")
print("und die dynamische Neuberechnung muss den bereits berechneten Backlog verwenden.")

print("\n" + "=" * 80)
print("KONKRETE UMSETZUNG:")
print("=" * 80)

print("\n1. Verarbeite Tage in chronologischer Reihenfolge (✓ bereits implementiert)")
print("2. Für jeden Tag:")
print("   a) Berechne Backlog basierend auf bereits aktualisierten Werten")
print("   b) Verwende diesen Backlog für die dynamische Neuberechnung")
print("   c) Berechne Produktion mit Rang-Logik")
print("   d) Aktualisiere Backlog basierend auf neuer Produktion")
