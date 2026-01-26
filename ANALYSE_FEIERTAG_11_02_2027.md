# Analyse: Feiertag 11.02.2027

**Datum:** 2026-01-25  
**Problem:** Inkonsistenz zwischen Programm und Excel bezüglich Feiertag 11.02.2027

---

## 🔍 Beobachtung

- **Programm:** 11.02.2027 hat 2000, 12.02.2027 hat 1500
- **Excel:** 11.02.2027 ist Feiertag (0), 12.02.2027 hat 2000
- **Folge:** Abweichungen über das ganze Jahr

---

## 📅 Ist der 11.02.2027 ein Feiertag?

### Web-Recherche:
- **11.02.2027 ist ein Donnerstag**
- **KEIN bundesweiter Feiertag in Deutschland** laut Web-Recherche
- Nächste Feiertage: Rosenmontag (08.02), Faschingsdienstag (09.02), Aschermittwoch (10.02)

### Mögliche Erklärungen:

1. **Regionale Feiertage:**
   - Die `holidays`-Bibliothek könnte nur bundesweite Feiertage zurückgeben
   - Excel könnte regionale Feiertage (z.B. Bayern, Baden-Württemberg) berücksichtigen
   - Der 11.02.2027 könnte ein regionaler Feiertag sein (z.B. Faschingsdonnerstag in bestimmten Regionen)

2. **Unterschiedliche Feiertagskalender:**
   - Excel könnte einen anderen Feiertagskalender verwenden
   - Möglicherweise manuell eingetragene Feiertage in Excel

3. **Bibliothek-Problem:**
   - Die `holidays`-Bibliothek könnte den Feiertag nicht korrekt erkennen
   - Möglicherweise fehlt ein Update der Bibliothek

---

## 🔍 Aktuelle Implementierung

### Feiertagsprüfung im Programm:

**`config/holidays_config.py` (Zeile 32-34):**
```python
country_holidays = holidays.country_holidays(holidays_lib_code, years=year)
return country_holidays
```

**Problem:** Verwendet `holidays.country_holidays('DE', years=2027)` ohne regionale Optionen.

### Bestelleingang-Berechnung:

**`simulation/china_transport.py` (Zeile 640):**
```python
order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
```

**Problem:** Wird für ALLE Tage aufgerufen, auch Feiertage. Es gibt keine Prüfung auf `is_workday()`.

**`simulation/simulator.py` (Zeile 422-423):**
```python
# KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
if not self.workday_calculator.is_weekend(day):
    self.procurement_manager.check_and_order(day, expected_future_demand)
```

**Problem:** Prüft nur `is_weekend()`, nicht `is_workday()` (welches auch Feiertage berücksichtigt).

---

## ❌ IDENTIFIZIERTE FEHLER

### 1. Bestelleingang wird an Feiertagen berechnet

**Ursache:** 
- `get_supplier_log_dataframe()` ruft `_calculate_order_quantity_from_volume_planning()` für ALLE Tage auf (Zeile 640)
- Keine Prüfung auf `is_workday()` vor dem Aufruf

**Ergebnis:** 
- Am 11.02.2027 wird Bestelleingang berechnet (2000), obwohl es ein Feiertag sein sollte
- In Excel wird am 11.02.2027 kein Bestelleingang berechnet (Feiertag)
- Die 2000 werden auf den 12.02.2027 verschoben → Excel hat 2000 am 12.02.2027

### 2. Feiertagsprüfung verwendet nur bundesweite Feiertage

**Ursache:**
- `holidays.country_holidays('DE', years=2027)` gibt nur bundesweite Feiertage zurück
- Regionale Feiertage (z.B. Faschingsdonnerstag in bestimmten Bundesländern) werden nicht berücksichtigt

**Ergebnis:**
- Der 11.02.2027 wird nicht als Feiertag erkannt, obwohl Excel es als Feiertag behandelt

---

## ✅ LÖSUNGSVORSCHLÄGE

### Lösung 1: Bestelleingang nur an Arbeitstagen berechnen

**In `simulation/china_transport.py` (get_supplier_log_dataframe, Zeile 637-641):**
```python
for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
    curr_date = start_date + timedelta(days=day_idx)
    
    # NEU: Prüfe ob Arbeitstag (Mo-Fr, keine Feiertage)
    order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
    if not self.workday_calculator.is_workday(order_day):
        continue  # Überspringe Feiertage und Wochenenden
    
    # Berechne Bestellmenge für diesen Tag aus Volumenplanung
    order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
```

### Lösung 2: Regionale Feiertage unterstützen

**Option A: Manuelle Feiertagsliste erweitern**
```python
# In config/holidays_config.py
MANUAL_HOLIDAYS_2027 = {
    date(2027, 2, 11): "Faschingsdonnerstag"  # Falls regionaler Feiertag
}
```

**Option B: Regionale Optionen für holidays-Bibliothek**
```python
# Prüfe ob regionale Feiertage benötigt werden
# holidays.country_holidays('DE', years=2027, subdiv='BY')  # Bayern
```

### Lösung 3: Excel-Feiertagskalender abgleichen

- Prüfe, welche Feiertage Excel verwendet
- Erstelle manuelle Liste der Feiertage, die Excel verwendet
- Stelle sicher, dass Programm die gleichen Feiertage verwendet

---

## 📋 NÄCHSTE SCHRITTE

1. **Prüfe Excel:** Welche Feiertage werden in Excel verwendet? Ist der 11.02.2027 tatsächlich ein Feiertag?
2. **Prüfe Regionale Feiertage:** Ist der 11.02.2027 ein regionaler Feiertag (z.B. in Bayern)?
3. **Implementiere Lösung 1:** Bestelleingang nur an Arbeitstagen berechnen
4. **Implementiere Lösung 2 oder 3:** Regionale Feiertage unterstützen oder Excel-Feiertagskalender abgleichen

---

## ❓ FRAGE AN BENUTZER

**Ist der 11.02.2027 tatsächlich ein Feiertag in Ihrer Excel-Datei?**
- Wenn ja: Welcher Feiertag ist es? (z.B. Faschingsdonnerstag, regionaler Feiertag)
- Wenn nein: Könnte es ein Fehler in der Excel-Datei sein?

**Welche Feiertage sollten berücksichtigt werden?**
- Nur bundesweite Feiertage?
- Auch regionale Feiertage (z.B. Bayern, Baden-Württemberg)?
- Gibt es manuell eingetragene Feiertage in Excel?
