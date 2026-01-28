# Backlog-Problem Analyse

**Datum:** 28.01.2026  
**Problem:** Gesamtvolumen erreicht nur 369.500 statt 370.000 (fehlt 500)  
**Status:** ⚠️ **IN ANALYSE**

---

## 🔴 Problem-Beschreibung

### Symptome:
- Am 19.11.2027 wird die letzte Abfahrt von China durchgeführt (500 als Losgröße)
- Am Ende kommt man nur auf **369.500** statt **370.000**
- Es fehlt eine Losgröße (500)
- Backlog bleibt bestehen (Gesamt: 460)
- **Nur bei MTB Downhill** tritt das Problem auf (sehr seltsam)

### Excel-Formel-Analyse:
Die Excel-Formel zeigt:
```
ABRUNDEN((Base * Share / AT) + Rest_Vortag; 0)
```

**Wichtig:** Am letzten Arbeitstag werden alle Reste aufsummiert.

---

## 🔍 Mögliche Ursachen

### 1. Rundungsfehler bei Gesamtsumme
- `int(yearly_volume * sales_share)` für jedes Produkt
- Summe aller `int()` Werte kann != `yearly_volume` sein
- **Prüfung:** Berechne manuell:
  - MTB Allrounder: int(370000 * 0.30) = 111000
  - MTB Competition: int(370000 * 0.15) = 55500
  - MTB Downhill: int(370000 * 0.10) = 37000
  - MTB Extreme: int(370000 * 0.07) = 25900
  - MTB Freeride: int(370000 * 0.05) = 18500
  - MTB Marathon: int(370000 * 0.08) = 29600
  - MTB Performance: int(370000 * 0.12) = 44400
  - MTB Trail: int(370000 * 0.13) = 48100
  - **Summe:** 111000 + 55500 + 37000 + 25900 + 18500 + 29600 + 44400 + 48100 = **370000** ✅

**Ergebnis:** Die Summe ist korrekt! Das Problem liegt woanders.

### 2. Carry-Over-Logik am letzten Arbeitstag
- Am letzten Arbeitstag werden Reste aufsummiert
- Vielleicht werden Reste nicht korrekt aufsummiert?
- Oder: Reste werden aufsummiert, aber dann nochmal abgerundet?

### 3. Problem nur bei MTB Downhill
- Sehr seltsam - warum nur bei einem Produkt?
- Vielleicht spezifisches Problem mit sales_share = 0.10?
- Oder Problem mit der Carry-Over-Logik für dieses Produkt?

---

## 💡 Lösungsansätze

### Ansatz 1: Gesamtsummen-Korrektur (aktuell implementiert)
- Berechne Gesamtsumme der Zielsummen
- Wenn != yearly_volume, korrigiere am letzten Arbeitstag
- **Problem:** Verursacht Performance-Probleme (3+ Minuten)

### Ansatz 2: Korrektur direkt in Carry-Over-Logik
- Am letzten Arbeitstag: Stelle sicher, dass Gesamtsumme = yearly_volume
- Korrigiere direkt beim Aufsummieren der Reste
- **Vorteil:** Keine zusätzliche Schleife nötig

### Ansatz 3: Korrektur nur bei MTB Downhill
- Da das Problem nur bei MTB Downhill auftritt
- Prüfe spezifisch dieses Produkt
- **Nachteil:** Nicht allgemein gültig

---

## 🎯 Empfohlener Ansatz

**Ansatz 2:** Korrektur direkt in Carry-Over-Logik am letzten Arbeitstag

**Vorteile:**
- Keine zusätzliche Schleife
- Keine Performance-Probleme
- Natürlicher Ort für die Korrektur
- Entspricht Excel-Logik (Reste werden am letzten Tag aufsummiert)

**Implementierung:**
- In `demand_calculator.py`: Am letzten Arbeitstag Gesamtsumme prüfen
- Oder: In `volume_planning_utils.py`: Nach Carry-Over-Logik Gesamtsumme korrigieren

---

**Status:** ⚠️ **IN ANALYSE**  
**Nächster Schritt:** Ansatz 2 implementieren
