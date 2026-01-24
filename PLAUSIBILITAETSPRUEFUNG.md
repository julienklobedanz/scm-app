# Plausibilitätsprüfung: Materiallager Spark vs. Produktion

## Dateien
1. **Materiallager Spark**: `2026-01-24T15-48_export-3.csv`
2. **Produktion MTB Allrounder**: `2026-01-24T15-48_export.csv`
3. **Produktion MTB Extreme**: `2026-01-24T15-52_export.csv`

## Prüfungen

### 1. Materiallager-Berechnung: Bestand_Abend = Bestand_Morgen + Zugang - Abgang

**Beispiel 11.01.2027:**
- Bestand morgens: 1295
- Lagerzugang: 0
- Lagerabgang: 1136
- Bestand abends: 159
- **Prüfung**: 1295 + 0 - 1136 = 159 ✅

**Beispiel 12.01.2027:**
- Bestand morgens: 159
- Lagerzugang: 0
- Lagerabgang: 159
- Bestand abends: 0
- **Prüfung**: 159 + 0 - 159 = 0 ✅

**Beispiel 18.01.2027:**
- Bestand morgens: 1295
- Lagerzugang: 0
- Lagerabgang: 1052
- Bestand abends: 243
- **Prüfung**: 1295 + 0 - 1052 = 243 ✅

**Beispiel 25.01.2027:**
- Bestand morgens: 1480
- Lagerzugang: 0
- Lagerabgang: 1169
- Bestand abends: 311
- **Prüfung**: 1480 + 0 - 1169 = 311 ✅

### 2. Konsistenz: Materialabgang = Summe Produktion (Allrounder + Extreme)

**Beispiel 11.01.2027:**
- Materialabgang: 1136
- Produktion Allrounder: 854
- Produktion Extreme: 282
- **Erwarteter Abgang**: 854 + 282 = 1136 ✅

**Beispiel 12.01.2027:**
- Materialabgang: 159
- Produktion Allrounder: 159
- Produktion Extreme: 0
- **Erwarteter Abgang**: 159 + 0 = 159 ✅

**Beispiel 18.01.2027:**
- Materialabgang: 1052
- Produktion Allrounder: 877
- Produktion Extreme: 175
- **Erwarteter Abgang**: 877 + 175 = 1052 ✅

**Beispiel 19.01.2027:**
- Materialabgang: 243
- Produktion Allrounder: 243
- Produktion Extreme: 0
- **Erwarteter Abgang**: 243 + 0 = 243 ✅

**Beispiel 25.01.2027:**
- Materialabgang: 1169
- Produktion Allrounder: 836
- Produktion Extreme: 333
- **Erwarteter Abgang**: 836 + 333 = 1169 ✅

**Beispiel 26.01.2027:**
- Materialabgang: 311
- Produktion Allrounder: 311
- Produktion Extreme: 0
- **Erwarteter Abgang**: 311 + 0 = 311 ✅

**Beispiel 01.02.2027:**
- Materialabgang: 1127
- Produktion Allrounder: 860
- Produktion Extreme: 267
- **Erwarteter Abgang**: 860 + 267 = 1127 ✅

**Beispiel 08.02.2027:**
- Materialabgang: 983
- **Tatsächlicher Verbrauch Allrounder**: 811 (nicht 786 aus CSV)
- Produktion Extreme: 169
- **Erwarteter Abgang**: 811 + 169 = 980
- **Differenz**: +3 (sehr gering, möglicherweise Rundungsfehler) ⚠️

**Beispiel 15.02.2027:**
- Materialabgang: 1175
- **Tatsächlicher Verbrauch Allrounder**: 811 (nicht 705 aus CSV)
- Produktion Extreme: 233
- **Erwarteter Abgang**: 811 + 233 = 1044
- **Differenz**: +131 (signifikant) ❌

**Beispiel 16.02.2027:**
- Materialabgang: 661
- Produktion Allrounder: 661
- Produktion Extreme: 0
- **Erwarteter Abgang**: 661 + 0 = 661 ✅

## Gefundene Inkonsistenzen

### ⚠️ 08.02.2027
- **Materialabgang**: 983
- **Tatsächlicher Verbrauch Allrounder**: 811 (korrigiert vom Benutzer)
- **Produktion Extreme**: 169
- **Erwarteter Abgang**: 811 + 169 = 980
- **Differenz**: +3 (sehr gering, möglicherweise Rundungsfehler)
- **Status**: Nahezu konsistent

### ❌ 15.02.2027
- **Materialabgang**: 1175
- **Tatsächlicher Verbrauch Allrounder**: 811 (korrigiert vom Benutzer)
- **Produktion Extreme**: 233
- **Erwarteter Abgang**: 811 + 233 = 1044
- **Differenz**: +131 (signifikant)
- **Mögliche Ursache**: 
  - Fehler in der Berechnung des Materialabgangs
  - Die "tatsächliche PM" in der CSV entspricht nicht dem tatsächlichen Materialverbrauch
  - Es könnte ein Problem mit der Rang-Logik geben, die mehr Material verbraucht als produziert wird

## Weitere Prüfungen

### Bestandskontinuität: Bestand_Abend(t) = Bestand_Morgen(t+1)

**Prüfung für 11.01.2027 → 12.01.2027:**
- Bestand abends (11.01): 159
- Bestand morgens (12.01): 159 ✅

**Prüfung für 12.01.2027 → 13.01.2027:**
- Bestand abends (12.01): 0
- Bestand morgens (13.01): 0 ✅

**Prüfung für 18.01.2027 → 19.01.2027:**
- Bestand abends (18.01): 243
- Bestand morgens (19.01): 243 ✅

**Prüfung für 25.01.2027 → 26.01.2027:**
- Bestand abends (25.01): 311
- Bestand morgens (26.01): 311 ✅

✅ **Bestandskontinuität ist korrekt**

## Mögliche Ursachen

1. **Weitere Produkte verwenden Spark**: Es könnte sein, dass noch andere Produkte (außer Allrounder und Extreme) Spark verwenden, die nicht in den bereitgestellten Dateien enthalten sind.

2. **Timing-Unterschiede**: Die Produktion könnte an einem anderen Tag gebucht werden als der Materialabgang.

3. **Rundungsfehler oder Berechnungsfehler**: Es könnte ein Fehler in der Berechnung des Materialabgangs geben.

## Empfehlung

1. Prüfe, ob es weitere Produkte gibt, die Spark verwenden.
2. Prüfe die Berechnung des Materialabgangs für die Tage 08.02.2027 und 15.02.2027.
3. Prüfe, ob es Timing-Unterschiede zwischen Produktion und Materialabgang gibt.
