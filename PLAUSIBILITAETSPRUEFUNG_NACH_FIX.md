# Plausibilitätsprüfung nach Materialverbrauch-Fix

## Dateien (nach Fix)
1. **Materiallager Spark**: `2026-01-24T16-02_export-2.csv`
2. **Produktion MTB Allrounder**: `2026-01-24T16-02_export.csv`
3. **Produktion MTB Extreme**: `2026-01-24T16-03_export.csv`

## Prüfung der kritischen Tage

### 08.02.2027

**Materiallager Spark:**
- Bestand morgens: 1787
- Lagerzugang: 0
- Lagerabgang: 1084
- Bestand abends: 703
- **Prüfung**: 1787 + 0 - 1084 = 703 ✅

**Produktion MTB Allrounder:**
- Tatsächliche PM: 786

**Produktion MTB Extreme:**
- Tatsächliche PM: 197

**Erwarteter Abgang**: 786 + 197 = 983
**Tatsächlicher Abgang**: 1084
**Differenz**: +101 ❌

### 15.02.2027

**Materiallager Spark:**
- Bestand morgens: 2097
- Lagerzugang: 0
- Lagerabgang: 1436
- Bestand abends: 661
- **Prüfung**: 2097 + 0 - 1436 = 661 ✅

**Produktion MTB Allrounder:**
- Tatsächliche PM: 705

**Produktion MTB Extreme:**
- Tatsächliche PM: 470

**Erwarteter Abgang**: 705 + 470 = 1175
**Tatsächlicher Abgang**: 1436
**Differenz**: +261 ❌

## Ergebnis

❌ **Das Problem besteht weiterhin!**

Die Korrektur hat nicht funktioniert. Es gibt immer noch Inkonsistenzen:
- 08.02.2027: Materialabgang ist 101 höher als erwartet
- 15.02.2027: Materialabgang ist 261 höher als erwartet

## Mögliche Ursachen

1. **Die finale Prüfung wird nicht ausgeführt**: Möglicherweise wird die Produktion nicht reduziert, weil die Bedingung `scheduled_qty > demand` nicht erfüllt ist.

2. **Material wird an anderer Stelle verbraucht**: Möglicherweise wird Material verbraucht, bevor die finale Prüfung ausgeführt wird.

3. **Die Rang-Logik verbraucht mehr Material als produziert wird**: Möglicherweise wird Material verbraucht, aber die Produktion wird später reduziert, ohne dass Material zurückgegeben wird.

4. **Timing-Problem**: Möglicherweise wird Material verbraucht, aber die Produktion wird erst später reduziert.
