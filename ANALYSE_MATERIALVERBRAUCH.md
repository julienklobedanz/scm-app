# Analyse: Materialverbrauch vs. Tatsächliche PM

## Problem

**08.02.2027:**
- Materialabgang: 1084
- Produktion Allrounder: 786
- Produktion Extreme: 197
- Erwarteter Abgang: 786 + 197 = 983
- **Differenz: +101**

**15.02.2027:**
- Materialabgang: 1436
- Produktion Allrounder: 705
- Produktion Extreme: 470
- Erwarteter Abgang: 705 + 470 = 1175
- **Differenz: +261**

## Root Cause Analysis

### Problem 1: Statische Simulation vs. Dynamische Neuberechnung

Die statische Simulation verbraucht Material basierend auf `production_by_product` aus `plan_daily_production()`. Aber die dynamische Neuberechnung produziert andere Werte.

**Ablauf:**
1. Statische Simulation: `plan_daily_production()` produziert z.B. 811 für Allrounder
2. Statische Simulation: Material wird verbraucht (811)
3. Dynamische Neuberechnung: Produziert 786 für Allrounder
4. Materiallager: Liest "tatsächliche PM" aus `production_logs_cache` (786)
5. **Problem:** Material wurde bereits verbraucht (811), aber "tatsächliche PM" ist 786

### Problem 2: Material wird nicht zurückgegeben

Die finale Prüfung gibt Material zurück, wenn die Produktion reduziert wird. Aber das Problem ist, dass:
- Material in der statischen Simulation verbraucht wird
- Die dynamische Neuberechnung reduziert die Produktion
- Aber das Material wurde bereits in der statischen Simulation verbraucht und wird nicht zurückgegeben

### Problem 3: Materiallager verwendet falsche Werte

Das Materiallager liest die "tatsächliche PM" aus `production_logs_cache`, das die dynamisch aktualisierten Werte hat. Aber das Material wurde bereits in der statischen Simulation verbraucht.

## Lösung

Die dynamische Neuberechnung muss das Material auch verbrauchen, oder das Materiallager muss die Werte aus der statischen Simulation verwenden.

**Option 1:** Materiallager verwendet statische Werte
- Problem: Reagiert nicht auf Marketing-Szenarien

**Option 2:** Dynamische Neuberechnung verbraucht Material
- Problem: Material wird doppelt verbraucht (statisch + dynamisch)

**Option 3:** Material wird nur in der dynamischen Neuberechnung verbraucht
- Problem: Statische Simulation verbraucht Material bereits

**Option 4:** Materiallager verwendet die Werte aus der dynamischen Neuberechnung, aber Material wird nur in der dynamischen Neuberechnung verbraucht
- Lösung: Statische Simulation verbraucht kein Material mehr, nur die dynamische Neuberechnung

## Empfehlung

Die beste Lösung wäre, dass die statische Simulation kein Material mehr verbraucht, sondern nur die dynamische Neuberechnung. Aber das würde eine größere Refaktorierung erfordern.

Eine einfachere Lösung wäre, dass das Materiallager die Werte aus der statischen Simulation verwendet, wenn keine dynamische Neuberechnung ausgeführt wurde.
