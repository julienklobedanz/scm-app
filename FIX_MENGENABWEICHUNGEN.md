# Fix: Mengenabweichungen basierend auf Excel-Logik

**Erstellt:** 2026-01-25  
**Basis:** Excel-Formeln vom Benutzer

---

## Problem 1: Startdatum Inbound

**Aktuell:** Beginnt am 01.11.2026  
**SOLL:** Beginnt am 24.11.2026 (erste Eintragung)

**Lösung:** Prüfe, wann die erste tatsächliche Versendung stattfindet und beginne die Tabelle ab diesem Datum.

---

## Problem 2: Warenausgang-Berechnung (Lieferant China)

### Excel-Formel:
- **P172** = ABRUNDEN(P157;0) + P165
- **P157** = (P20+O22) * (P154 / (P20+P45+P70+P95+O22+O47+O72+O97))
- **P165** = WENN(P154=P161;0; WENN((P154-P161)<=(P20+O22-ABRUNDEN(P157;0));P154-P161;P20+O22-ABRUNDEN(P157;0)))
- **P161** = ABRUNDEN(P157;0) + ABRUNDEN(P158;0) + ABRUNDEN(P159;0) + ABRUNDEN(P160;0)

### Bedeutung:
- **P157** = Anteilige Losgröße (ungerundet) = `unrounded[s]`
- **P161** = Summe aller anteiligen Losgrößen (gerundet) = `sum(rounded.values())`
- **P154** = Berechnete Losgröße = `current_lot_size`
- **P20+O22** = Produziert + Warenbestand = `accumulated_by_saddle[s]`
- **P165** = Korrektur für Rundungsdifferenzen

### Aktuelle Implementierung (Zeile 754-768):
```python
# B. Runden & Differenz finden (Largest Remainder Method)
rounded = {s: int(val) for s, val in unrounded.items()}
diff = current_lot_size - sum(rounded.values())

# C. Differenz verteilen
if diff > 0:
    # Sortieren nach Nachkommastelle
    remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
    remainders.sort(key=lambda x: x[1], reverse=True)
    
    for s, rem in remainders:
        if diff <= 0: 
            break
        rounded[s] += 1
        diff -= 1
```

**Problem:** Fehlt die P165-Korrektur! Nach Largest Remainder Method sollte zusätzlich die Excel-P165-Logik angewendet werden.

### Korrektur:
```python
# B. Runden & Differenz finden (Largest Remainder Method)
rounded = {s: int(val) for s, val in unrounded.items()}
diff = current_lot_size - sum(rounded.values())

# C. Differenz verteilen (Largest Remainder Method)
if diff > 0:
    remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
    remainders.sort(key=lambda x: x[1], reverse=True)
    
    for s, rem in remainders:
        if diff <= 0: 
            break
        rounded[s] += 1
        diff -= 1

# D. NEU: Excel P165-Korrektur für jeden Sattel
# P165 = WENN(P154=P161;0; WENN((P154-P161)<=(P20+O22-ABRUNDEN(P157;0));P154-P161;P20+O22-ABRUNDEN(P157;0)))
# Für jeden Sattel: correction = MIN(diff, available_after_rounded)
remaining_diff = current_lot_size - sum(rounded.values())
if remaining_diff > 0:
    for s in all_saddles:
        if remaining_diff <= 0:
            break
        # Verfügbarer Bestand nach anteiliger Losgröße
        available_after_rounded = accumulated_by_saddle[s] - rounded[s]
        # Korrektur = MIN(Differenz, Verfügbarer Bestand)
        correction = min(remaining_diff, available_after_rounded)
        rounded[s] += correction
        remaining_diff -= correction
```

### Warenausgang-Berechnung (Zeile 807-833):
**Aktuell:** Verwendet `cumulative_shipped` (FALSCH laut EXCEL_LOGIK_ANALYSE_AP12.md)

**Korrektur:**
```python
# ALT (falsch):
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
cumulative_shipped += shipment_qty

# NEU (korrekt):
# Warenausgang = Min(Geplante Versandmenge, Verfügbarer Bestand)
# planned_shipment_qty ist bereits aus Pool-Logik (rounded[s] + correction)
shipment_qty = min(planned_shipment_qty, current_stock)
```

---

## Problem 3: Inbound-Berechnung

### Excel-Formel:
- **P71** = WENN(P57<>""; WENN(ODER(P68="Ausgefallen";P68="Ladung verloren");0; WENN('Lieferant China (Sattel)'!P172-P87>=0;'Lieferant China (Sattel)'!P172-P87;'Lieferant China (Sattel)'!P172));"")
- **P57** = Abfahrtsdatum
- **P68** = Status (Ausgefallen/Ladung verloren)
- **P87** = Mengenverlust
- **P172** = Warenausgang aus "Lieferant China"

### Bedeutung:
- Wenn Abfahrtsdatum vorhanden:
  - Wenn "Ausgefallen" oder "Ladung verloren": Inbound = 0
  - Sonst: Inbound = WENN(Warenausgang - Mengenverlust >= 0; Warenausgang - Mengenverlust; Warenausgang)

### Aktuelle Implementierung:
Inbound verwendet bereits `get_supplier_log_dataframe()` für Warenausgang, aber prüft nicht auf Mengenverlust (P87).

**Korrektur:** Prüfe auf Mengenverlust aus DeliveryProblemScenario und wende Formel an.

---

## Problem 4: Summenzeilen prüfen

**SOLL:** Gesamtmenge = 370000  
**IST:** Gesamtmenge = 362000  
**Abweichung:** -8000

**Ursache:** Könnte durch:
1. Fehlende Eintragungen vor 24.11.2026
2. Falsche Warenausgang-Berechnung (cumulative_shipped)
3. Fehlende P165-Korrektur
4. Mengenverluste (DeliveryProblemScenario)

**Lösung:** Nach Fix der obigen Probleme prüfen, ob Summe korrekt ist.

---

## Umsetzungsschritte

1. **Warenausgang-Berechnung korrigieren:**
   - Entferne `cumulative_shipped`-Logik
   - Füge P165-Korrektur hinzu
   - Stelle sicher: `shipment_qty = min(planned_shipment_qty, current_stock)`

2. **Inbound-Berechnung korrigieren:**
   - Prüfe auf Mengenverlust (P87)
   - Wende Formel an: `WENN(Warenausgang - Mengenverlust >= 0; Warenausgang - Mengenverlust; Warenausgang)`

3. **Startdatum prüfen:**
   - Prüfe, wann erste Versendung stattfindet
   - Stelle sicher, dass Tabelle ab diesem Datum beginnt

4. **Summenzeilen validieren:**
   - Prüfe Gesamtmenge nach Fixes
   - Stelle sicher: Summe = 370000
