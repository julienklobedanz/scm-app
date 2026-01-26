# Implementierte Fixes - Zusammenfassung

**Datum:** 2026-01-25

---

## ✅ Fix 1: Bestelleingang an Feiertagen (zurückgesetzt)

**Status:** Zurückgesetzt (wie in Excel erlaubt)

**Änderungen:**
- `simulation/simulator.py`: Beibehalten `is_weekend()` statt `is_workday()`
- `simulation/china_transport.py`: Bestelleingang wird auch an Feiertagen berechnet

---

## ✅ Fix 2: Materiallager - Lagerzugang an Wochenenden

**Status:** Implementiert

**Datei:** `ui/material_calculations.py`

**Änderungen:**
- Lagerzugang an Wochenenden/Feiertagen = 0
- Lagerabgang an Wochenenden/Feiertagen = 0
- Berechnung des Lagerabgangs nur an Arbeitstagen

---

## ✅ Fix 3: Warenausgang-Berechnung (Excel P172)

**Status:** Implementiert

**Dateien:** 
- `simulation/china_transport.py` - `get_supplier_log_dataframe()`
- `simulation/china_transport.py` - `get_inbound_log_dataframe()`

### Änderungen:

1. **P165-Korrektur hinzugefügt:**
   ```python
   # D. Excel P165-Korrektur für jeden Sattel
   # P165 = WENN(P154=P161;0; WENN((P154-P161)<=(P20+O22-ABRUNDEN(P157;0));P154-P161;P20+O22-ABRUNDEN(P157;0)))
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

2. **cumulative_shipped entfernt:**
   ```python
   # ALT (falsch):
   if current_stock - cumulative_shipped >= 0:
       shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
   cumulative_shipped += shipment_qty
   
   # NEU (korrekt):
   shipment_qty = min(planned_shipment_qty, current_stock)
   ```

**Erwartetes Ergebnis:**
- Warenausgang = ABRUNDEN(P157;0) + P165 (wie Excel)
- Fizik Tundra: SOLL 99900, sollte jetzt erreicht werden

---

## ⚠️ Offen: Inbound-Berechnung mit Mengenverlust

**Excel-Formel P71:**
```
=WENN(P57<>"";WENN(ODER(P68="Ausgefallen";P68="Ladung verloren");0;
WENN('Lieferant China (Sattel)'!P172-P87>=0;'Lieferant China (Sattel)'!P172-P87;
'Lieferant China (Sattel)'!P172));"")
```

**Bedeutung:**
- P71 = Inbound-Menge pro Sattel
- P172 = Warenausgang aus "Lieferant China"
- P87 = Mengenverlust (kann leer sein)
- Formel: `WENN(Warenausgang - Mengenverlust >= 0; Warenausgang - Mengenverlust; Warenausgang)`

**Aktueller Status:**
- Inbound verwendet Pool-Logik direkt (nicht Warenausgang aus get_supplier_log_dataframe)
- Mengenverlust (P87) wird nicht berücksichtigt

**Frage:** Soll Inbound den Warenausgang aus "Lieferant China" verwenden oder die Pool-Logik direkt?

---

## ⚠️ Offen: Startdatum Inbound

**Problem:** Inbound beginnt am 01.12.2026, sollte aber ab 24.11.2026 beginnen

**Aktuell:** `start_date = date(self.workday_calculator.year - 1, 11, 1)` = 01.11.2026

**Frage:** Wann findet die erste tatsächliche Versendung statt? Sollte die Tabelle ab diesem Datum beginnen oder ab 24.11.2026?

---

## 📋 Nächste Schritte

1. **Validierung:**
   - Prüfe: Warenausgang-Berechnung mit P165-Korrektur
   - Prüfe: Summenzeilen (SOLL: 370000)
   - Prüfe: Fizik Tundra (SOLL: 99900)

2. **Inbound-Berechnung:**
   - Entscheidung: Warenausgang aus "Lieferant China" oder Pool-Logik direkt?
   - Implementierung: Mengenverlust-Formel (P71)

3. **Startdatum:**
   - Prüfe: Wann erste Versendung stattfindet
   - Korrigiere: Startdatum auf 24.11.2026 oder erstes Versendungsdatum
