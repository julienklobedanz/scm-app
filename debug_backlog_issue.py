#!/usr/bin/env python3
"""
Debug: Prüft warum die Produktion immer noch zu viel produziert
"""

# Beispiel: 05.08.2027
# Aus CSV:
planned_pm = 454
actual_pm = 1069
backlog_vortag = 0  # Aus CSV (04.08.2027)

print("=" * 80)
print("ANALYSE: Warum wird mehr produziert als geplant?")
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
print("MÖGLICHE URSACHEN:")
print("=" * 80)

print("\n1. Backlog wird aus statischen Logs gelesen, die noch nicht aktualisiert wurden")
print("   → Die dynamische Neuberechnung liest den Backlog aus production_logs (statisch)")
print("   → Diese Logs haben möglicherweise noch die alte Backlog-Berechnung")
print("   → Oder: Die Logs wurden noch nicht aktualisiert, wenn die Neuberechnung läuft")

print("\n2. Die Rang-Logik produziert mehr als erlaubt")
print("   → Die Prüfung 'scheduled_qty <= demand' wird möglicherweise nicht korrekt ausgeführt")
print("   → Oder: Die Prüfung wird ausgeführt, aber 'demand' ist falsch (z.B. Backlog ist falsch)")

print("\n3. Die dynamische Neuberechnung wird nicht ausgeführt")
print("   → Die Prüfung 'static_values_incorrect' greift möglicherweise nicht")
print("   → Oder: Die Prüfung wird übersprungen, weil 'inputs_changed' bereits True ist")

print("\n" + "=" * 80)
print("LÖSUNG:")
print("=" * 80)

print("\nDie dynamische Neuberechnung sollte den Backlog NICHT aus den statischen Logs lesen,")
print("sondern ihn selbst berechnen, basierend auf den bereits berechneten Werten.")
print("\nODER:")
print("Die statischen Logs müssen ZUERST aktualisiert werden, bevor die dynamische")
print("Neuberechnung ausgeführt wird.")
