# Detaillierte Analyse der Inkonsistenzen

**Datum:** 2026-01-25  
**Ziel:** Glasklare Identifikation der Ursachen für:
1. 500 zu wenig in Inbound
2. Fitzik Tundra: 99899 statt 99900 (1 zu wenig)

---

## 🔍 Problem 1: Fitzik Tundra = 99899 statt 99900 (1 zu wenig)

### Excel-Formel (P172):
```
P172 = ABRUNDEN(P157;0) + P165
```

### Aktuelle Implementierung in `get_supplier_log_dataframe()` (Zeile 765-781):

```python
# B. Runden & Differenz finden (Largest Remainder Method)
rounded = {s: int(val) for s, val in unrounded.items()}
diff = current_lot_size - sum(rounded.values())

# C. Differenz verteilen
if diff > 0:
    remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
    remainders.sort(key=lambda x: x[1], reverse=True)
    
    for s, rem in remainders:
        if diff <= 0: 
            break
        rounded[s] += 1
        diff -= 1

shipments_today = rounded
```

### ❌ FEHLER IDENTIFIZIERT:

**Die Excel P165-Korrektur fehlt komplett!**

Laut Dokumentation (`LIEFERANT_CHINA_LOGIK_EXPORT.md`, Zeile 424-433) sollte nach der Largest Remainder Method zusätzlich die P165-Korrektur angewendet werden:

```python
# D. P165: Korrektur für Rundungsdifferenzen
remaining_diff = current_lot_size - sum(rounded.values())
if remaining_diff > 0:
    for s in all_saddles:
        if remaining_diff <= 0:
            break
        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
        correction = min(remaining_diff, available_after_rounded)
        rounded[s] += correction
        remaining_diff -= correction
```

**Ursache:** Nach Largest Remainder Method kann noch eine Differenz übrig bleiben (z.B. wenn `available_after_rounded` für alle Sättel = 0 ist). Diese Differenz wird durch P165-Korrektur verteilt.

**Ergebnis:** Ohne P165-Korrektur fehlt am Ende 1 Stück → 99899 statt 99900.

---

## 🔍 Problem 2: 500 zu wenig in Inbound

### Vergleich der beiden Funktionen:

#### `get_supplier_log_dataframe()` (Zeile 748-749):
```python
# Am letzten Tag: Restbestand mitversenden
if day_idx == total_days - 1 and total_accumulated > 0:
    current_lot_size = int(round(total_accumulated))
else:
    current_lot_size = int(total_accumulated / lot_size) * lot_size
```

#### `get_inbound_log_dataframe()` (Zeile 1057):
```python
# C. Losgröße berechnen (wie in get_supplier_log_dataframe)
current_lot_size = int(total_accumulated / lot_size) * lot_size
```

### ❌ FEHLER IDENTIFIZIERT:

**In `get_inbound_log_dataframe()` wird am letzten Tag KEIN Restbestand mitversendet!**

**Ursache:** 
- In `get_supplier_log_dataframe()` wird am letzten Tag der gesamte Restbestand mitversendet (Zeile 748-749)
- In `get_inbound_log_dataframe()` fehlt diese Logik komplett (Zeile 1057)
- Wenn am Ende des Jahres noch z.B. 500 Stück im Hafen liegen, werden diese nicht mitversendet

**Ergebnis:** Inbound-Summe ist 500 zu niedrig, weil der letzte Restbestand nicht mitversendet wird.

---

## 🔍 Problem 3: Mengenverlust-Formel (P71) fehlt in Inbound

### Excel-Formel (P71):
```
P71 = WENN(P57<>""; 
    WENN(ODER(P68="Ausgefallen";P68="Ladung verloren");0; 
    WENN('Lieferant China (Sattel)'!P172-P87>=0; 
        'Lieferant China (Sattel)'!P172-P87; 
        'Lieferant China (Sattel)'!P172));"")
```

### Bedeutung:
- **P172** = Warenausgang aus "Lieferant China"
- **P87** = Mengenverlust (aus DeliveryProblemScenario mit `loss_percentage < 1.0`)
- **Formel:** `WENN(Warenausgang - Mengenverlust >= 0; Warenausgang - Mengenverlust; Warenausgang)`

### Aktuelle Implementierung:

In `get_inbound_log_dataframe()` wird direkt `shipments_today[s]` verwendet (Zeile 1125-1128), ohne Mengenverlust abzuziehen.

### ❌ FEHLER IDENTIFIZIERT:

**Mengenverlust (P87) wird nicht berücksichtigt!**

**Ursache:** 
- Inbound verwendet `shipments_today[s]` direkt aus der Pool-Logik
- DeliveryProblemScenario mit `loss_percentage < 1.0` (z.B. 10% Verlust) wird nicht angewendet
- Excel-Formel P71 würde den Mengenverlust abziehen: `Warenausgang - Mengenverlust`

**Ergebnis:** Inbound zeigt zu hohe Mengen, wenn es DeliveryProblemScenario mit `loss_percentage < 1.0` gibt.

**HINWEIS:** Dies könnte erklären, warum die Summe nicht stimmt, ABER der Benutzer sagt "500 zu wenig", nicht "zu viel". Daher ist Problem 2 (Restbestand am letzten Tag) wahrscheinlich die Hauptursache.

---

## 📋 Zusammenfassung der Ursachen

### Glasklare Erkenntnisse:

1. **Fitzik Tundra: 99899 statt 99900**
   - **Ursache:** Excel P165-Korrektur fehlt in `get_supplier_log_dataframe()` (Zeile 765-781)
   - **Lösung:** P165-Korrektur nach Largest Remainder Method hinzufügen

2. **500 zu wenig in Inbound**
   - **Ursache:** Am letzten Tag wird Restbestand nicht mitversendet in `get_inbound_log_dataframe()` (Zeile 1057)
   - **Lösung:** Logik aus `get_supplier_log_dataframe()` übernehmen: Am letzten Tag `current_lot_size = int(round(total_accumulated))`

3. **Mengenverlust-Formel (P71) fehlt**
   - **Ursache:** Mengenverlust (P87) wird nicht von Inbound abgezogen
   - **Lösung:** DeliveryProblemScenario mit `loss_percentage < 1.0` prüfen und Formel anwenden: `WENN(Warenausgang - Mengenverlust >= 0; Warenausgang - Mengenverlust; Warenausgang)`

---

## ✅ Nächste Schritte

1. **P165-Korrektur hinzufügen** in `get_supplier_log_dataframe()` (nach Zeile 779)
2. **Restbestand am letzten Tag** in `get_inbound_log_dataframe()` (Zeile 1057 korrigieren)
3. **Mengenverlust-Formel (P71)** in `get_inbound_log_dataframe()` implementieren (bei Zeile 1125-1128)
