# Analyse: Schiff-Abfahrt und Feiertage

**Datum:** 2026-01-25  
**Problem:** 
1. Am 11.02.2027 (chinesischer Feiertag) sollten keine LKW/Schiff-Abfahrten stattfinden
2. Am 04.02.2027: Programm berechnet Abfahrt 10.02.2027, Excel: 17.02.2027

---

## 🔍 Aktuelle Implementierung

### Inbound: Berechnung des Abfahrtsdatums (Zeile 1140-1156)

```python
# Abfahrt LKW 🇨🇳 = curr_date (Tag der Versendung)
row['Abfahrt LKW 🇨🇳'] = curr_date.strftime(self.master_data.DATE_FORMAT)

# Ankunft LKW 🇨🇳 = Abfahrt + 2 AT
day_idx_sim = (curr_date - date(self.workday_calculator.year, 1, 1)).days
day_port = self._add_workdays(day_idx_sim, 2)
date_port = self.workday_calculator.get_date_from_day(day_port)
row['Ankunft LKW 🇨🇳'] = date_port.strftime(self.master_data.DATE_FORMAT)

# Abfahrt Schiff: Nächster Mittwoch nach Ankunft im Hafen
wd = date_port.weekday()
if wd == 2:  # Wenn bereits Mittwoch
    days_to_wed = 7
else:
    days_to_wed = (2 - wd) % 7
    if days_to_wed == 0:
        days_to_wed = 7

date_ship_dep = date_port + timedelta(days=days_to_wed)
row['Abfahrt Schiff 🇨🇳'] = date_ship_dep.strftime(self.master_data.DATE_FORMAT)
```

---

## ❌ IDENTIFIZIERTE PROBLEME

### Problem 1: Keine Feiertagsprüfung für LKW/Schiff-Abfahrten

**Aktuell:**
- Abfahrt LKW 🇨🇳 wird an ALLEN Tagen erlaubt (auch chinesischen Feiertagen)
- Abfahrt Schiff wird nur auf Mittwoch geprüft, nicht auf chinesische Feiertage

**Excel-Logik:**
- Am 11.02.2027 (chinesischer Feiertag) sollten keine LKW/Schiff-Abfahrten stattfinden
- Wenn Ankunft im Hafen auf einen chinesischen Feiertag fällt, muss auf den nächsten chinesischen Arbeitstag gewartet werden

**Korrektur:**
- Prüfe chinesische Feiertage für Abfahrt LKW 🇨🇳
- Prüfe chinesische Feiertage für Abfahrt Schiff (nicht nur Mittwoch, sondern auch kein chinesischer Feiertag)

---

### Problem 2: Falsche Berechnung des nächsten Mittwochs

**Beispiel: 04.02.2027**
- Programm: Ankunft LKW 🇨🇳 = 06.02.2027 (Montag) → Abfahrt Schiff = 10.02.2027 (Mittwoch)
- Excel: Abfahrt Schiff = 17.02.2027 (Mittwoch)

**Mögliche Ursachen:**
1. Ankunft LKW 🇨🇳 wird falsch berechnet (sollte später sein)
2. Nächster Mittwoch wird falsch berechnet (sollte 17.02. statt 10.02. sein)
3. Chinesische Feiertage werden nicht berücksichtigt (11.02. ist Feiertag → muss übersprungen werden)

**Analyse:**
- 04.02.2027 = Samstag
- Abfahrt LKW 🇨🇳 sollte nicht am Samstag sein (Wochenende)
- Wenn Abfahrt LKW am 06.02.2027 (Montag) ist:
  - Ankunft LKW 🇨🇳 = 08.02.2027 (Mittwoch) → Abfahrt Schiff = 15.02.2027 (Mittwoch) ❌
- Wenn Abfahrt LKW am 07.02.2027 (Dienstag) ist:
  - Ankunft LKW 🇨🇳 = 09.02.2027 (Donnerstag) → Abfahrt Schiff = 17.02.2027 (Mittwoch) ✅

**Ergebnis:** Abfahrt LKW 🇨🇳 sollte nur an chinesischen Arbeitstagen sein (nicht Wochenende, nicht chinesische Feiertage)

---

## ✅ LÖSUNGEN

### Lösung 1: Feiertagsprüfung für LKW/Schiff-Abfahrten

```python
# Prüfe ob curr_date ein chinesischer Arbeitstag ist
chinese_holidays = self._get_chinese_holidays()
is_chinese_workday = (curr_date.weekday() < 5 and curr_date not in chinese_holidays)

if not is_chinese_workday:
    # Keine Versendung an chinesischen Feiertagen oder Wochenenden
    continue  # Überspringe diesen Tag
```

### Lösung 2: Nächster Mittwoch mit Feiertagsprüfung

```python
# Ankunft im Hafen
date_port = self.workday_calculator.get_date_from_day(day_port)

# Finde nächsten Mittwoch, der KEIN chinesischer Feiertag ist
date_ship_dep = date_port
while True:
    wd = date_ship_dep.weekday()
    if wd == 2 and date_ship_dep not in chinese_holidays:
        break  # Mittwoch und kein Feiertag
    date_ship_dep += timedelta(days=1)
```

---

## 📋 IMPLEMENTIERUNGSSCHRITTE

1. **Entfernen:** Restbestand am letzten Tag mitversenden (bereits erledigt)
2. **Hinzufügen:** Feiertagsprüfung für Abfahrt LKW 🇨🇳 (nur chinesische Arbeitstage)
3. **Korrigieren:** Nächster Mittwoch mit Feiertagsprüfung (überspringe chinesische Feiertage)
4. **Testen:** Prüfe ob 04.02. → 17.02. korrekt berechnet wird
