#!/usr/bin/env python3
"""
Prüft Konsistenz zwischen Tatsächliche PM und Produktionsbedarf
"""

import csv
from datetime import datetime

# Lese CSV
data = []
with open('/Users/julienklobedanz/Downloads/2026-01-24T15-37_export.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Datum'] and row['Datum'] != 'Summe':
            data.append(row)

# Konvertiere zu Zahlen
for row in data:
    row['geplante_PM'] = int(row['geplante PM']) if row['geplante PM'] else 0
    row['tatsächliche_PM'] = int(row['tatsächliche PM']) if row['tatsächliche PM'] else 0
    row['fertiggestellte_PM'] = int(row['fertiggestellte PM']) if row['fertiggestellte PM'] else 0
    row['Backlog'] = int(row['Backlog']) if row['Backlog'] else 0
    row['Schichtanzahl'] = int(row['Schichtanzahl']) if row['Schichtanzahl'] else 0

print("=" * 100)
print("PRÜFUNG 1: Ist Tatsächliche PM > Produktionsbedarf?")
print("=" * 100)
print()

# Berechne Produktionsbedarf für jeden Tag
problems = []
for i, row in enumerate(data):
    if i == 0:
        prev_backlog = 0
    else:
        prev_backlog = data[i-1]['Backlog']
    
    planned_pm = row['geplante_PM']
    production_demand = planned_pm + prev_backlog  # Produktionsbedarf = Nachfrage + Backlog vom Vortag
    actual_pm = row['tatsächliche_PM']
    
    if actual_pm > production_demand and actual_pm > 0:
        problems.append({
            'date': row['Datum'],
            'planned_pm': planned_pm,
            'prev_backlog': prev_backlog,
            'production_demand': production_demand,
            'actual_pm': actual_pm,
            'difference': actual_pm - production_demand
        })

if problems:
    print(f"❌ PROBLEM: {len(problems)} Tage gefunden, an denen Tatsächliche PM > Produktionsbedarf ist:")
    print()
    for p in problems[:10]:  # Zeige erste 10
        print(f"  {p['date']}: Geplante PM={p['planned_pm']}, Backlog_vortag={p['prev_backlog']}, Produktionsbedarf={p['production_demand']}, Tatsächliche PM={p['actual_pm']}, Differenz=+{p['difference']}")
    if len(problems) > 10:
        print(f"  ... und {len(problems) - 10} weitere")
else:
    print("✅ OK: Keine Tage gefunden, an denen Tatsächliche PM > Produktionsbedarf ist")

print()
print("=" * 100)
print("PRÜFUNG 2: Wird der Backlog korrekt reduziert?")
print("=" * 100)
print()

# Prüfe Backlog-Berechnung
backlog_problems = []
for i, row in enumerate(data):
    if i == 0:
        continue
    
    prev_row = data[i-1]
    curr_row = row
    
    planned_pm = curr_row['geplante_PM']
    finished_pm = curr_row['fertiggestellte_PM']
    prev_backlog = prev_row['Backlog']
    expected_backlog = max(0, planned_pm - finished_pm + prev_backlog)
    actual_backlog = curr_row['Backlog']
    
    if abs(expected_backlog - actual_backlog) > 0.1:  # Toleranz für Rundung
        backlog_problems.append({
            'date': curr_row['Datum'],
            'planned_pm': planned_pm,
            'finished_pm': finished_pm,
            'prev_backlog': prev_backlog,
            'expected_backlog': expected_backlog,
            'actual_backlog': actual_backlog,
            'difference': actual_backlog - expected_backlog
        })

if backlog_problems:
    print(f"❌ PROBLEM: {len(backlog_problems)} Tage gefunden, an denen Backlog nicht korrekt berechnet wird:")
    print()
    for p in backlog_problems[:10]:  # Zeige erste 10
        print(f"  {p['date']}: Geplante PM={p['planned_pm']}, Fertiggestellte PM={p['finished_pm']}, Backlog_vortag={p['prev_backlog']}")
        print(f"           Erwarteter Backlog={p['expected_backlog']}, Tatsächlicher Backlog={p['actual_backlog']}, Differenz={p['difference']:+.1f}")
    if len(backlog_problems) > 10:
        print(f"  ... und {len(backlog_problems) - 10} weitere")
else:
    print("✅ OK: Backlog wird korrekt berechnet")

print()
print("=" * 100)
print("PRÜFUNG 3: Summen-Analyse")
print("=" * 100)
print()

# Berechne Summen
total_planned = sum(row['geplante_PM'] for row in data)
total_actual = sum(row['tatsächliche_PM'] for row in data)
total_finished = sum(row['fertiggestellte_PM'] for row in data)

# Berechne kumulativen Produktionsbedarf
total_production_demand = 0
for i, row in enumerate(data):
    if i == 0:
        prev_backlog = 0
    else:
        prev_backlog = data[i-1]['Backlog']
    planned_pm = row['geplante_PM']
    production_demand = planned_pm + prev_backlog
    total_production_demand += production_demand

start_backlog = data[0]['Backlog'] if data else 0
end_backlog = data[-1]['Backlog'] if data else 0

print(f"Summe(Geplante PM): {total_planned}")
print(f"Summe(Tatsächliche PM): {total_actual}")
print(f"Summe(Fertiggestellte PM): {total_finished}")
print(f"Summe(Produktionsbedarf): {total_production_demand}")
print()
print(f"Anfangsbacklog: {start_backlog}")
print(f"Endbacklog: {end_backlog}")
print()
print(f"Differenz (Tatsächliche PM - Geplante PM): {total_actual - total_planned}")
print(f"Differenz (Tatsächliche PM - Produktionsbedarf): {total_actual - total_production_demand}")
print(f"Erwartete Differenz (bei korrekter Logik): {start_backlog - end_backlog}")

print()
print("=" * 100)
print("PRÜFUNG 4: Tage mit hoher Produktion")
print("=" * 100)
print()

# Finde Tage mit hoher Produktion relativ zum Produktionsbedarf
high_production_days = []
for i, row in enumerate(data):
    if i == 0:
        prev_backlog = 0
    else:
        prev_backlog = data[i-1]['Backlog']
    
    planned_pm = row['geplante_PM']
    production_demand = planned_pm + prev_backlog
    actual_pm = row['tatsächliche_PM']
    
    if actual_pm > 0 and production_demand > 0:
        ratio = actual_pm / production_demand
        if ratio > 1.0 or actual_pm > planned_pm * 2:  # Mehr als 100% oder mehr als 2x geplante PM
            high_production_days.append({
                'date': row['Datum'],
                'planned_pm': planned_pm,
                'prev_backlog': prev_backlog,
                'production_demand': production_demand,
                'actual_pm': actual_pm,
                'ratio': ratio
            })

if high_production_days:
    print(f"Tage mit hoher Produktion (relativ zum Produktionsbedarf):")
    print()
    for p in sorted(high_production_days, key=lambda x: x['ratio'], reverse=True)[:20]:
        print(f"  {p['date']}: Geplante PM={p['planned_pm']}, Backlog_vortag={p['prev_backlog']}, Produktionsbedarf={p['production_demand']}, Tatsächliche PM={p['actual_pm']}, Verhältnis={p['ratio']:.2f}")
