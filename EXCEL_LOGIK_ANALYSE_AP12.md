# Excel-Logik Analyse für AP 12

**Datum:** 2026-01-22  
**Ziel:** Verständnis der Excel-Formeln für korrekte Implementierung

---

## 📊 Excel-Formeln (Fizik Tundra als Beispiel)

### Warenausgang-Berechnung

**Hauptformel (NO172):**
```
=ABRUNDEN(NO157;0)+NO165
```

**NO157 (Anteilige Losgröße):**
```
=WENN(NO154<>0;(NO20+NN22)*(NO154/(NO20+NO45+NO70+NO95+NN22+NN47+NN72+NN97));0)
```

**Erklärung:**
- `NO20` = Produziert (z.B. 132)
- `NN22` = Warenbestand (z.B. 2)
- `NO154` = Berechnete Losgröße (z.B. 134)
- `NO20+NO45+NO70+NO95+NN22+NN47+NN72+NN97` = Gesamt-Verfügbarkeit (alle Sättel)

**Formel bedeutet:**
```
Anteilige Losgröße = (Produziert + Warenbestand) * (Losgröße / Gesamt-Verfügbarkeit)
```

**NO165 (Korrektur für Rundungsdifferenzen):**
```
=WENN(NO154=NO161;0;
WENN((NO154-NO161)<=(NO20+NN22-ABRUNDEN(NO157;0));NO154-NO161;NO20+NN22-ABRUNDEN(NO157;0)))
```

**Erklärung:**
- `NO154` = Berechnete Losgröße
- `NO161` = Summe aller anteiligen Losgrößen (gerundet)
- `NO20+NN22-ABRUNDEN(NO157;0)` = Verfügbarer Bestand nach anteiliger Losgröße

**Formel bedeutet:**
- Wenn Losgröße = Summe anteiliger Losgrößen: Korrektur = 0
- Sonst: Korrektur = MIN(Differenz, Verfügbarer Bestand)

**Warenausgang (NO172):**
```
=WENN(ODER('Inbound (Material)'!NO68="Ausgefallen";'Inbound (Material)'!NO68="");0;NO172)
```

**Erklärung:**
- Wenn "Ausgefallen" oder leer: Warenausgang = 0
- Sonst: Warenausgang = ABRUNDEN(anteilige Losgröße) + Korrektur

---

## 🔍 Aktuelle Implementierung vs. Excel

### Aktuelle Implementierung (simulation/china_transport.py, Zeilen 747-784)

**Problem 1: Verwendung von `cumulative_shipped`**
```python
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
```

**Excel-Logik:**
- Warenausgang = ABRUNDEN(anteilige Losgröße) + Korrektur
- Keine Verwendung von `cumulative_shipped`

**Problem 2: Pool-Logik vs. Excel-Logik**

**Aktuelle Pool-Logik (Zeilen 671-724):**
- Berechnet anteilige Losgröße korrekt (ähnlich NO157)
- Verwendet Largest Remainder Method für Rundung
- **ABER:** Keine Korrektur für Rundungsdifferenzen (NO165 fehlt)

**Excel-Logik:**
- Anteilige Losgröße (NO157) ✅
- Korrektur für Rundungsdifferenzen (NO165) ❌ Fehlt

---

## 💡 Lösung

### Schritt 1: Warenausgang-Berechnung korrigieren

**Entferne `cumulative_shipped`-Logik:**
```python
# VORHER (falsch):
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
cumulative_shipped += shipment_qty

# NACHHER (korrekt):
# Warenausgang = Min(Geplante Versandmenge, Verfügbarer Bestand)
shipment_qty = min(planned_shipment_qty, current_stock)
```

### Schritt 2: Korrektur für Rundungsdifferenzen hinzufügen

**In Pool-Logik (Zeilen 689-714):**
```python
# Nach Largest Remainder Method:
rounded = {s: int(val) for s, val in unrounded.items()}
diff = current_lot_size - sum(rounded.values())

# NEU: Korrektur für jeden Sattel (ähnlich NO165)
for s in all_saddles:
    if diff > 0:
        # Verfügbarer Bestand nach anteiliger Losgröße
        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
        # Korrektur = MIN(Differenz, Verfügbarer Bestand)
        correction = min(diff, available_after_rounded)
        rounded[s] += correction
        diff -= correction
```

---

## 📋 Materiallager: Wochenende-Problem

### Problem
- Am Wochenende werden Lagerzugang und Lagerabgang eingeplant
- Sollte: Beide = 0 sein
- Bestand morgens = Bestand abends (vom Vortag übernommen)

### Aktuelle Implementierung (pages/5_materiallager.py, Zeilen 150-270)

**Prüfung:**
- `is_workday` wird geprüft (Zeile 152)
- Aber: `receipt_by_saddle` und `issue_by_saddle` werden möglicherweise trotzdem berechnet

**Lösung:**
```python
# Am Wochenende: Lagerzugang und Lagerabgang = 0
if not is_workday:
    receipt_by_saddle = {s: 0.0 for s in saddle_types}
    issue_by_saddle = {s: 0.0 for s in saddle_types}
```

---

## 🎯 Umsetzungsschritte

1. **Warenausgang-Berechnung korrigieren** (simulation/china_transport.py)
   - Entferne `cumulative_shipped`-Logik
   - Vereinfache zu: `shipment_qty = min(planned_shipment_qty, current_stock)`

2. **Korrektur für Rundungsdifferenzen hinzufügen** (simulation/china_transport.py)
   - Nach Largest Remainder Method: Zusätzliche Korrektur für jeden Sattel

3. **Materiallager: Wochenende korrigieren** (pages/5_materiallager.py)
   - Am Wochenende: Lagerzugang = 0, Lagerabgang = 0
   - Bestand morgens = Bestand abends (vom Vortag)

---

## ✅ Erwartete Ergebnisse

### Nach Fix:
- **Warenausgang (Fizik Tundra):** 99.900 (wie Produktionsmenge)
- **Warenbestand (Ende):** 0 (wie Excel)
- **Materiallager (Wochenende):** Lagerzugang = 0, Lagerabgang = 0


**Datum:** 2026-01-22  
**Ziel:** Verständnis der Excel-Formeln für korrekte Implementierung

---

## 📊 Excel-Formeln (Fizik Tundra als Beispiel)

### Warenausgang-Berechnung

**Hauptformel (NO172):**
```
=ABRUNDEN(NO157;0)+NO165
```

**NO157 (Anteilige Losgröße):**
```
=WENN(NO154<>0;(NO20+NN22)*(NO154/(NO20+NO45+NO70+NO95+NN22+NN47+NN72+NN97));0)
```

**Erklärung:**
- `NO20` = Produziert (z.B. 132)
- `NN22` = Warenbestand (z.B. 2)
- `NO154` = Berechnete Losgröße (z.B. 134)
- `NO20+NO45+NO70+NO95+NN22+NN47+NN72+NN97` = Gesamt-Verfügbarkeit (alle Sättel)

**Formel bedeutet:**
```
Anteilige Losgröße = (Produziert + Warenbestand) * (Losgröße / Gesamt-Verfügbarkeit)
```

**NO165 (Korrektur für Rundungsdifferenzen):**
```
=WENN(NO154=NO161;0;
WENN((NO154-NO161)<=(NO20+NN22-ABRUNDEN(NO157;0));NO154-NO161;NO20+NN22-ABRUNDEN(NO157;0)))
```

**Erklärung:**
- `NO154` = Berechnete Losgröße
- `NO161` = Summe aller anteiligen Losgrößen (gerundet)
- `NO20+NN22-ABRUNDEN(NO157;0)` = Verfügbarer Bestand nach anteiliger Losgröße

**Formel bedeutet:**
- Wenn Losgröße = Summe anteiliger Losgrößen: Korrektur = 0
- Sonst: Korrektur = MIN(Differenz, Verfügbarer Bestand)

**Warenausgang (NO172):**
```
=WENN(ODER('Inbound (Material)'!NO68="Ausgefallen";'Inbound (Material)'!NO68="");0;NO172)
```

**Erklärung:**
- Wenn "Ausgefallen" oder leer: Warenausgang = 0
- Sonst: Warenausgang = ABRUNDEN(anteilige Losgröße) + Korrektur

---

## 🔍 Aktuelle Implementierung vs. Excel

### Aktuelle Implementierung (simulation/china_transport.py, Zeilen 747-784)

**Problem 1: Verwendung von `cumulative_shipped`**
```python
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
```

**Excel-Logik:**
- Warenausgang = ABRUNDEN(anteilige Losgröße) + Korrektur
- Keine Verwendung von `cumulative_shipped`

**Problem 2: Pool-Logik vs. Excel-Logik**

**Aktuelle Pool-Logik (Zeilen 671-724):**
- Berechnet anteilige Losgröße korrekt (ähnlich NO157)
- Verwendet Largest Remainder Method für Rundung
- **ABER:** Keine Korrektur für Rundungsdifferenzen (NO165 fehlt)

**Excel-Logik:**
- Anteilige Losgröße (NO157) ✅
- Korrektur für Rundungsdifferenzen (NO165) ❌ Fehlt

---

## 💡 Lösung

### Schritt 1: Warenausgang-Berechnung korrigieren

**Entferne `cumulative_shipped`-Logik:**
```python
# VORHER (falsch):
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
cumulative_shipped += shipment_qty

# NACHHER (korrekt):
# Warenausgang = Min(Geplante Versandmenge, Verfügbarer Bestand)
shipment_qty = min(planned_shipment_qty, current_stock)
```

### Schritt 2: Korrektur für Rundungsdifferenzen hinzufügen

**In Pool-Logik (Zeilen 689-714):**
```python
# Nach Largest Remainder Method:
rounded = {s: int(val) for s, val in unrounded.items()}
diff = current_lot_size - sum(rounded.values())

# NEU: Korrektur für jeden Sattel (ähnlich NO165)
for s in all_saddles:
    if diff > 0:
        # Verfügbarer Bestand nach anteiliger Losgröße
        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
        # Korrektur = MIN(Differenz, Verfügbarer Bestand)
        correction = min(diff, available_after_rounded)
        rounded[s] += correction
        diff -= correction
```

---

## 📋 Materiallager: Wochenende-Problem

### Problem
- Am Wochenende werden Lagerzugang und Lagerabgang eingeplant
- Sollte: Beide = 0 sein
- Bestand morgens = Bestand abends (vom Vortag übernommen)

### Aktuelle Implementierung (pages/5_materiallager.py, Zeilen 150-270)

**Prüfung:**
- `is_workday` wird geprüft (Zeile 152)
- Aber: `receipt_by_saddle` und `issue_by_saddle` werden möglicherweise trotzdem berechnet

**Lösung:**
```python
# Am Wochenende: Lagerzugang und Lagerabgang = 0
if not is_workday:
    receipt_by_saddle = {s: 0.0 for s in saddle_types}
    issue_by_saddle = {s: 0.0 for s in saddle_types}
```

---

## 🎯 Umsetzungsschritte

1. **Warenausgang-Berechnung korrigieren** (simulation/china_transport.py)
   - Entferne `cumulative_shipped`-Logik
   - Vereinfache zu: `shipment_qty = min(planned_shipment_qty, current_stock)`

2. **Korrektur für Rundungsdifferenzen hinzufügen** (simulation/china_transport.py)
   - Nach Largest Remainder Method: Zusätzliche Korrektur für jeden Sattel

3. **Materiallager: Wochenende korrigieren** (pages/5_materiallager.py)
   - Am Wochenende: Lagerzugang = 0, Lagerabgang = 0
   - Bestand morgens = Bestand abends (vom Vortag)

---

## ✅ Erwartete Ergebnisse

### Nach Fix:
- **Warenausgang (Fizik Tundra):** 99.900 (wie Produktionsmenge)
- **Warenbestand (Ende):** 0 (wie Excel)
- **Materiallager (Wochenende):** Lagerzugang = 0, Lagerabgang = 0





