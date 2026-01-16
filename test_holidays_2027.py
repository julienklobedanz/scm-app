#!/usr/bin/env python3
"""Test-Skript um Feiertage für 2027 zu prüfen"""

import holidays
from datetime import date
from config.holidays_config import HolidaysConfig

print("=" * 60)
print("Feiertage 2027 - Test")
print("=" * 60)

# Test 1: Direkt mit holidays library
print("\n1. Direkt mit holidays library:")
try:
    de_2027 = holidays.country_holidays('DE', years=2027)
    print(f"   Anzahl Feiertage 2027 (DE): {len(de_2027)}")
    print("   Erste 10 Feiertage:")
    for d, name in sorted(list(de_2027.items())[:10]):
        print(f"     {d}: {name}")
except Exception as e:
    print(f"   FEHLER: {e}")

# Test 2: Über HolidaysConfig
print("\n2. Über HolidaysConfig:")
try:
    de_holidays = HolidaysConfig.get_holidays_for_year(2027, 'DE')
    print(f"   Anzahl Feiertage 2027 (DE): {len(de_holidays)}")
    print("   Erste 10 Feiertage:")
    for d, name in sorted(list(de_holidays.items())[:10]):
        print(f"     {d}: {name}")
except Exception as e:
    print(f"   FEHLER: {e}")

# Test 3: Vergleich mit hardcodierter Liste in procurement_manager
print("\n3. Vergleich mit hardcodierter Liste (procurement_manager.HOLIDAYS_2027):")
hardcoded = [
    "01.01.2027", "26.03.2027", "29.03.2027", "01.05.2027",
    "06.05.2027", "17.05.2027", "03.10.2027",
    "01.11.2027", "25.12.2027", "26.12.2027"
]
print(f"   Hardcodierte Feiertage: {len(hardcoded)}")
for h in hardcoded:
    print(f"     {h}")

# Test 4: Prüfe ob hardcodierte Feiertage in holidays library enthalten sind
print("\n4. Prüfe ob hardcodierte Feiertage in holidays library enthalten sind:")
try:
    de_2027 = holidays.country_holidays('DE', years=2027)
    from datetime import datetime
    
    missing = []
    for h_str in hardcoded:
        h_date = datetime.strptime(h_str, "%d.%m.%Y").date()
        if h_date not in de_2027:
            missing.append(h_str)
    
    if missing:
        print(f"   ⚠️  FEHLENDE Feiertage in holidays library: {missing}")
    else:
        print("   ✅ Alle hardcodierten Feiertage sind in holidays library enthalten")
except Exception as e:
    print(f"   FEHLER: {e}")

# Test 5: Prüfe WorkdayCalculator
print("\n5. Test WorkdayCalculator mit 2027:")
try:
    from simulation.workday_calculator import WorkdayCalculator
    wc = WorkdayCalculator(year=2027)
    
    # Test ein paar bekannte Feiertage
    test_dates = [
        date(2027, 1, 1),   # Neujahr
        date(2027, 3, 26),   # Karfreitag?
        date(2027, 5, 1),    # Tag der Arbeit
        date(2027, 12, 25),  # Weihnachten
        date(2027, 12, 26),  # 2. Weihnachtsfeiertag
    ]
    
    print("   Test einiger Feiertage:")
    for test_date in test_dates:
        day = (test_date - date(2027, 1, 1)).days
        is_workday = wc.is_workday(day)
        is_holiday = test_date in wc.german_holidays
        print(f"     {test_date.strftime('%d.%m.%Y')}: Arbeitstag={is_workday}, Feiertag={is_holiday}")
        
except Exception as e:
    print(f"   FEHLER: {e}")

print("\n" + "=" * 60)

