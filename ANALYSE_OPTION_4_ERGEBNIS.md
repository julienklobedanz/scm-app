# Analyse: Option 4 Implementierung - Ergebnisse

## Übersicht

**Ziel:** Prüfen, ob die Implementierung von Option 4 (Materialverbrauch explizit speichern) die Konsistenz zwischen Materiallager und Produktion hergestellt hat.

**Datenquellen:**
- `2026-01-24T16-12_export.csv`: MTB Allrounder Produktion
- `2026-01-24T16-12_export-2.csv`: MTB Extreme Produktion
- `2026-01-24T16-12_export-3.csv`: Materiallager Spark

**Produkte mit Spark-Sattel:**
- MTB Allrounder
- MTB Extreme

---

## Kritische Tage - Detaillierte Analyse

### 08.02.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **906**
- MTB Extreme: tatsächliche PM = **178**
- **Summe erwartet:** 906 + 178 = **1084**

**Materiallager Spark:**
- Lagerabgang = **1023**

**Ergebnis:**
- **Differenz:** 1023 - 1084 = **-61** (Materiallager zeigt 61 weniger als erwartet)

**Bewertung:**
- ⚠️ **Nicht konsistent:** Materiallager zeigt weniger als die Summe der Produktion

---

### 15.02.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **871**
- MTB Extreme: tatsächliche PM = **565**
- **Summe erwartet:** 871 + 565 = **1436**

**Materiallager Spark:**
- Lagerabgang = **1290**

**Ergebnis:**
- **Differenz:** 1290 - 1436 = **-146** (Materiallager zeigt 146 weniger als erwartet)

**Bewertung:**
- ⚠️ **Nicht konsistent:** Materiallager zeigt weniger als die Summe der Produktion

---

## Weitere Stichproben

### 11.01.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **854**
- MTB Extreme: tatsächliche PM = **282**
- **Summe erwartet:** 854 + 282 = **1136**

**Materiallager Spark:**
- Lagerabgang = **1136**

**Ergebnis:**
- **Differenz:** 1136 - 1136 = **0** ✅ **KONSISTENT**

---

### 18.01.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **877**
- MTB Extreme: tatsächliche PM = **175**
- **Summe erwartet:** 877 + 175 = **1052**

**Materiallager Spark:**
- Lagerabgang = **1053**

**Ergebnis:**
- **Differenz:** 1053 - 1052 = **+1** ✅ **KONSISTENT** (minimale Abweichung)

---

### 25.01.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **837**
- MTB Extreme: tatsächliche PM = **333**
- **Summe erwartet:** 837 + 333 = **1170**

**Materiallager Spark:**
- Lagerabgang = **1163**

**Ergebnis:**
- **Differenz:** 1163 - 1170 = **-7** ✅ **KONSISTENT** (minimale Abweichung)

---

## Zusammenfassung

### Positive Ergebnisse

1. **Viele Tage sind konsistent:** Die meisten Tage zeigen eine gute Übereinstimmung zwischen Materiallager und Produktion (z.B. 11.01.2027, 18.01.2027, 25.01.2027).

2. **Implementierung funktioniert grundsätzlich:** Die Materiallager-Werte werden jetzt aus `production_logs_cache` gelesen (Option 4).

### Verbleibende Probleme

1. **Inkonsistenzen an bestimmten Tagen:**
   - 08.02.2027: -61 Differenz
   - 15.02.2027: -146 Differenz

2. **Mögliche Ursachen:**
   - **Materialverbrauch wird möglicherweise nicht korrekt gespeichert:** Die Spalte `material_verbrauch` könnte an manchen Tagen nicht korrekt gesetzt werden.
   - **Fallback-Logik greift:** Wenn `material_verbrauch` nicht vorhanden ist, wird `tatsächliche PM` verwendet, aber möglicherweise gibt es Unterschiede zwischen dynamischer und statischer Berechnung.
   - **Timing-Problem:** Die Materiallager-Berechnung könnte zu einem Zeitpunkt erfolgen, wenn `material_verbrauch` noch nicht gesetzt ist.

---

## Nächste Schritte

1. **Prüfen, ob `material_verbrauch` korrekt gespeichert wird:**
   - Debug-Ausgabe in `ui/production_calculations.py` hinzufügen
   - Prüfen, ob die Spalte `material_verbrauch` für alle Tage vorhanden ist

2. **Prüfen, ob Materiallager korrekt liest:**
   - Debug-Ausgabe in `ui/material_calculations.py` hinzufügen
   - Prüfen, ob `material_verbrauch` oder `tatsächliche PM` verwendet wird

3. **Timing-Problem beheben:**
   - Sicherstellen, dass `material_verbrauch` gesetzt wird, bevor Materiallager-Berechnung erfolgt
   - Prüfen, ob die iterative Berechnung in `ui/page_initialization.py` korrekt funktioniert

---

## Fazit

**Status:** ⚠️ **Teilweise erfolgreich**

Die Implementierung von Option 4 funktioniert grundsätzlich, aber es gibt noch Inkonsistenzen an bestimmten Tagen. Die meisten Tage sind konsistent, aber einige Tage (z.B. 08.02.2027, 15.02.2027) zeigen noch Abweichungen.

**Empfehlung:** Weitere Debugging-Schritte durchführen, um die Ursache der verbleibenden Inkonsistenzen zu identifizieren.
