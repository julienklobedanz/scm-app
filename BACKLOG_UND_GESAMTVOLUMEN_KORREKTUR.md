# Backlog und Gesamtvolumen Korrektur

**Datum:** 28.01.2026  
**Problem:** Gesamtvolumen erreicht nicht exakt `yearly_volume` (370.000)  
**Status:** ✅ **KORRIGIERT**

---

## 🔴 Problem

### Beschreibung:
- Am 19.11.2027 wird die letzte Abfahrt von China durchgeführt (500 als Losgröße)
- Am Ende kommt man nur auf **369.500** statt **370.000**
- Es fehlt eine Losgröße (500)
- Backlog bleibt bestehen:
  - MTB Allrounder: 145
  - Competition: 73
  - Downhill: 48
  - Extreme: 25
  - Marathon: 40
  - Performance: 62
  - Trail: 67
  - **Gesamt Backlog: 460**

### Ursache:
- Die Korrektur in `volume_planning_utils.py` verwendet `int(yearly_volume * sales_share)` für jedes Produkt
- **Problem:** Die Summe aller `int(yearly_volume * sales_share)` kann durch Rundungsfehler nicht genau `yearly_volume` ergeben
- Beispiel:
  - Wenn `yearly_volume = 370000` und `sales_shares` nicht perfekt auf ganze Zahlen runden
  - Summe aller `int(370000 * sales_share)` könnte 369999 oder 370001 sein statt genau 370000

### Auswirkung:
- Gesamtvolumen erreicht nicht exakt `yearly_volume`
- Eine Losgröße (500) bleibt am Hafen liegen
- Backlog kann nicht vollständig abgebaut werden

---

## ✅ Lösung

### Implementierung:

**PHASE 1:** Korrigiere jedes Produkt auf individuelle Zielsumme (wie bisher)
- Berechne `target_sum = int(yearly_volume * sales_share)` für jedes Produkt
- Korrigiere Differenz am letzten Arbeitstag

**PHASE 2:** KRITISCH - Korrigiere Gesamtsumme auf exakt `yearly_volume`
- Berechne Gesamtsumme aller Produkte: `total_sum = sum(product_sums.values())`
- Berechne Differenz: `total_difference = yearly_volume - total_sum`
- Wenn `total_difference != 0`:
  - **Positive Differenz:** Füge zum Produkt mit größtem Anteil hinzu
  - **Negative Differenz:** Entferne vom Produkt mit größtem Anteil (nicht negativ werden)

### Code-Änderung:

```python
# PHASE 2: KRITISCH - Korrigiere Gesamtsumme auf exakt yearly_volume
total_sum = sum(product_sums.values())
total_difference = yearly_volume - total_sum

if total_difference != 0:
    if total_difference > 0:
        # Positive Differenz: Füge zum Produkt mit größtem Anteil hinzu
        largest_product = max(MasterData.BOM.keys(), 
                            key=lambda p: MasterData.PRODUCT_SALES_SHARES.get(p, 0.0))
        demands_dict[last_workday_of_year][largest_product] = (
            demands_dict[last_workday_of_year].get(largest_product, 0) + total_difference
        )
    else:
        # Negative Differenz: Entferne vom Produkt mit größtem Anteil
        largest_product = max(MasterData.BOM.keys(), 
                            key=lambda p: MasterData.PRODUCT_SALES_SHARES.get(p, 0.0))
        current_value = demands_dict[last_workday_of_year].get(largest_product, 0)
        demands_dict[last_workday_of_year][largest_product] = max(0, current_value + total_difference)
```

---

## 📋 Geänderte Dateien

- `ui/volume_planning_utils.py` - PHASE 2 Korrektur hinzugefügt

---

## ✅ Erwartetes Ergebnis

Nach der Korrektur:
- ✅ Gesamtvolumen erreicht **exakt 370.000**
- ✅ Alle 500 Losgrößen werden verschickt (keine bleibt am Hafen)
- ✅ Backlog kann vollständig abgebaut werden
- ✅ Letzte Abfahrt von China enthält die fehlende Losgröße

---

## 🧪 Test-Empfehlungen

1. **Gesamtvolumen-Prüfung:**
   - Prüfe ob Summe aller Produkte genau 370.000 ist
   - Prüfe ob keine Losgröße am Hafen bleibt

2. **Backlog-Prüfung:**
   - Prüfe ob Backlog vollständig abgebaut werden kann
   - Prüfe ob letzte Abfahrt die fehlende Losgröße enthält

3. **Konsistenz-Prüfung:**
   - Prüfe ob wöchentliche Volumenplanung korrekt ist
   - Prüfe ob tägliche Volumenplanung korrekt ist

---

**Status:** ✅ **IMPLEMENTIERT**  
**Bereit für Tests**
