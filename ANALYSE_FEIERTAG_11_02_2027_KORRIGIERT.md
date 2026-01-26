# Analyse: Feiertag 11.02.2027 (KORRIGIERT)

**Datum:** 2026-01-25  
**Problem:** Inkonsistenz zwischen Programm und Excel bezüglich chinesischer Feiertag 11.02.2027

---

## 🔍 Beobachtung

- **Programm:** 11.02.2027 hat 2000, 12.02.2027 hat 1500
- **Excel:** 11.02.2027 ist chinesischer Feiertag "Goldene Woche (Frühlingsferien)" (0), 12.02.2027 hat 2000
- **Folge:** Abweichungen über das ganze Jahr

---

## 📅 Ist der 11.02.2027 ein chinesischer Feiertag?

### Web-Recherche:
- **11.02.2027 ist ein Donnerstag**
- **Goldene Woche (Frühlingsferien) 2027:** Hauptfeiertag am Mittwoch, 10. Februar 2027
- **Chinesisches Neujahr 2027:** 6. Februar 2027
- **Frühlingsferien:** Die Goldene Woche ist Teil der Frühjahrsferien, die **rund um das Chinesische Neujahrsfest** stattfinden
- **Ergebnis:** Der 11.02.2027 ist wahrscheinlich Teil der chinesischen Feiertagsperiode (Frühlingsferien)

### Excel-Formel:
```
=WENNNV(INDEX(Tabelle4[Feiertag];VERGLEICH(CQ54&"China";Tabelle4[Tag]&Tabelle4[Land];0));"")
```
**Ergebnis:** "Goldene Woche (Frühlingsferien)"

**Bedeutung:** Excel prüft chinesische Feiertage für Abfahrten in China (Tag + "China")

---

## 🔍 Aktuelle Implementierung

### Chinesische Feiertage werden verwendet für:

1. **Freigabedatum** (Zeile 647):
   ```python
   released_day = self._get_next_workday(order_day, use_chinese_holidays=True)
   ```
   ✅ **KORREKT:** Verwendet chinesische Feiertage

2. **Produktionsdatum** (Zeile 663):
   ```python
   production_end_day = self._add_workdays(released_day, production_time_days, exclude_start=True, use_chinese_holidays=True)
   ```
   ✅ **KORREKT:** Verwendet chinesische Feiertage

### Bestelleingang-Berechnung:

**`simulation/china_transport.py` (get_supplier_log_dataframe, Zeile 637-641):**
```python
for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
    curr_date = start_date + timedelta(days=day_idx)
    # Berechne Bestellmenge für diesen Tag aus Volumenplanung
    order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
```

**Problem:** Wird für ALLE Tage aufgerufen, auch chinesische Feiertage. Es gibt keine Prüfung auf chinesische Feiertage vor dem Aufruf.

---

## ❌ IDENTIFIZIERTE FEHLER

### Bestelleingang wird an chinesischen Feiertagen berechnet

**Ursache:** 
- `get_supplier_log_dataframe()` ruft `_calculate_order_quantity_from_volume_planning()` für ALLE Tage auf (Zeile 640)
- Keine Prüfung auf chinesische Feiertage vor dem Aufruf
- Das Freigabedatum wird zwar auf den nächsten chinesischen Arbeitstag verschoben, aber der Bestelleingang wird trotzdem am Feiertag berechnet

**Ergebnis:** 
- Am 11.02.2027 wird Bestelleingang berechnet (2000), obwohl es ein chinesischer Feiertag ist
- In Excel wird am 11.02.2027 kein Bestelleingang berechnet (chinesischer Feiertag)
- Die 2000 werden auf den 12.02.2027 verschoben → Excel hat 2000 am 12.02.2027
- Im Programm: 11.02.2027 hat 2000, 12.02.2027 hat 1500 → **VERSCHIEBUNG!**

---

## ✅ LÖSUNG

### Bestelleingang nur an chinesischen Arbeitstagen berechnen

**In `simulation/china_transport.py` (get_supplier_log_dataframe, Zeile 637-641):**

```python
for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
    curr_date = start_date + timedelta(days=day_idx)
    
    # NEU: Prüfe ob chinesischer Arbeitstag (Mo-Fr, keine chinesischen Feiertage)
    order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
    if not self.workday_calculator.is_weekend(order_day):
        # Prüfe chinesische Feiertage
        chinese_holidays = self._get_chinese_holidays()
        if curr_date in chinese_holidays:
            continue  # Überspringe chinesische Feiertage
    
    # Berechne Bestellmenge für diesen Tag aus Volumenplanung
    order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
```

**ODER einfacher (konsistent mit Freigabedatum-Logik):**

```python
for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
    curr_date = start_date + timedelta(days=day_idx)
    
    # NEU: Prüfe ob chinesischer Arbeitstag
    # Verwende die gleiche Logik wie für Freigabedatum
    order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
    
    # Prüfe Wochenende
    if self.workday_calculator.is_weekend(order_day):
        continue
    
    # Prüfe chinesische Feiertage
    chinese_holidays = self._get_chinese_holidays()
    if curr_date in chinese_holidays:
        continue  # Überspringe chinesische Feiertage
    
    # Berechne Bestellmenge für diesen Tag aus Volumenplanung
    order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
```

---

## 📋 ZUSAMMENFASSUNG

### Problem:
- **Excel:** Bestelleingang wird an chinesischen Feiertagen NICHT berechnet (11.02.2027 = 0)
- **Programm:** Bestelleingang wird an chinesischen Feiertagen berechnet (11.02.2027 = 2000)
- **Ergebnis:** Verschiebung der Mengen → Abweichungen über das ganze Jahr

### Lösung:
- Bestelleingang nur an chinesischen Arbeitstagen berechnen (Mo-Fr, keine chinesischen Feiertage)
- Konsistent mit Excel-Logik: Excel prüft `Tag + "China"` = Feiertag → kein Bestelleingang

### Implementierung:
- Prüfe Wochenende UND chinesische Feiertage vor `_calculate_order_quantity_from_volume_planning()`
- Verwende `self._get_chinese_holidays()` für Feiertagsprüfung (bereits vorhanden)
