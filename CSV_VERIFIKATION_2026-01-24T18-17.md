# CSV-Verifikation: Spark, MTB Allrounder, MTB Extreme

## Übersicht

- **Spark (Materiallager)**: Lagerzugang, Bestand morgens, Lagerabgang, Bestand abends
- **MTB Allrounder (Produktion)**: tatsächliche PM
- **MTB Extreme (Produktion)**: tatsächliche PM

**Beide Produkte verwenden Spark-Sattel**, daher sollte gelten:
**Lagerabgang (Spark) = Summe(tatsächliche PM MTB Allrounder + tatsächliche PM MTB Extreme)**

---

## Stichproben-Prüfung kritischer Tage

### 22.11.2027
- **Materiallager Spark**: Lagerabgang = **1156**
- **MTB Allrounder**: tatsächliche PM = **754**
- **MTB Extreme**: tatsächliche PM = **402**
- **Summe Produktion**: 754 + 402 = **1156** ✓ **KONSISTENT**

### 29.11.2027
- **Materiallager Spark**: Lagerabgang = **1078**
- **MTB Allrounder**: tatsächliche PM = **744**
- **MTB Extreme**: tatsächliche PM = **334**
- **Summe Produktion**: 744 + 334 = **1078** ✓ **KONSISTENT**

### 23.11.2027
- **Materiallager Spark**: Lagerabgang = **139**
- **MTB Allrounder**: tatsächliche PM = **0**
- **MTB Extreme**: tatsächliche PM = **139**
- **Summe Produktion**: 0 + 139 = **139** ✓ **KONSISTENT**

### 30.11.2027
- **Materiallager Spark**: Lagerabgang = **957**
- **MTB Allrounder**: tatsächliche PM = **906**
- **MTB Extreme**: tatsächliche PM = **51**
- **Summe Produktion**: 906 + 51 = **957** ✓ **KONSISTENT**

### 15.02.2027
- **Materiallager Spark**: Lagerabgang = **1026**
- **MTB Allrounder**: tatsächliche PM = **866**
- **MTB Extreme**: tatsächliche PM = **160**
- **Summe Produktion**: 866 + 160 = **1026** ✓ **KONSISTENT**

### 16.02.2027
- **Materiallager Spark**: Lagerabgang = **1010**
- **MTB Allrounder**: tatsächliche PM = **1010**
- **MTB Extreme**: tatsächliche PM = **0**
- **Summe Produktion**: 1010 + 0 = **1010** ✓ **KONSISTENT**

### 08.02.2027
- **Materiallager Spark**: Lagerabgang = **1200**
- **MTB Allrounder**: tatsächliche PM = **858**
- **MTB Extreme**: tatsächliche PM = **342**
- **Summe Produktion**: 858 + 342 = **1200** ✓ **KONSISTENT**

### 11.01.2027
- **Materiallager Spark**: Lagerabgang = **1136**
- **MTB Allrounder**: tatsächliche PM = **854**
- **MTB Extreme**: tatsächliche PM = **282**
- **Summe Produktion**: 854 + 282 = **1136** ✓ **KONSISTENT**

### 18.01.2027
- **Materiallager Spark**: Lagerabgang = **1054**
- **MTB Allrounder**: tatsächliche PM = **878**
- **MTB Extreme**: tatsächliche PM = **176**
- **Summe Produktion**: 878 + 176 = **1054** ✓ **KONSISTENT**

### 25.01.2027
- **Materiallager Spark**: Lagerabgang = **1169**
- **MTB Allrounder**: tatsächliche PM = **837**
- **MTB Extreme**: tatsächliche PM = **332**
- **Summe Produktion**: 837 + 332 = **1169** ✓ **KONSISTENT**

---

## Gesamtsummen-Prüfung

### Materiallager Spark
- **Lagerzugang**: 133,942
- **Lagerabgang**: 133,751
- **Bestand abends**: 324,725

### Produktion
- **MTB Allrounder - tatsächliche PM**: 109,506
- **MTB Extreme - tatsächliche PM**: 24,793
- **Summe Produktion**: 109,506 + 24,793 = **134,299**

### Vergleich
- **Lagerabgang (Spark)**: 133,751
- **Summe Produktion (MTB Allrounder + MTB Extreme)**: 134,299
- **Differenz**: 134,299 - 133,751 = **548**

⚠️ **INKONSISTENZ**: Die Summe der Produktion ist um 548 Stück höher als der Lagerabgang.

---

## Mögliche Ursachen

1. **Andere Produkte verwenden auch Spark**: Es könnten weitere Produkte Spark verwenden, die nicht in den beiden Exporten enthalten sind.
2. **Zeitraum-Unterschiede**: Die Produktions-Exporte könnten einen anderen Zeitraum abdecken als der Materiallager-Export.
3. **Rounding-Fehler**: Bei der Berechnung könnten Rundungsfehler auftreten.
4. **Cache-Problem**: Möglicherweise werden noch veraltete Daten angezeigt.

---

## Empfehlung

1. **Prüfe alle Produkte, die Spark verwenden**: Nicht nur MTB Allrounder und MTB Extreme, sondern alle Produkte.
2. **Prüfe den Zeitraum**: Stelle sicher, dass alle Exporte denselben Zeitraum abdecken.
3. **Prüfe die Summenzeile**: Die Summenzeile könnte falsch berechnet sein.

---

## Fazit

✅ **Tagesweise Konsistenz**: Alle geprüften Tage zeigen konsistente Werte zwischen Produktion und Materiallager.

⚠️ **Gesamtsummen-Inkonsistenz**: Die Gesamtsummen weichen um 548 Stück ab. Dies könnte auf:
- Fehlende Produkte in den Exporten
- Zeitraum-Unterschiede
- Berechnungsfehler in der Summenzeile

hinweisen.
