# Identifizierte Probleme - Detaillierte Analyse

**Erstellt:** 2026-01-25  
**Status:** Neu identifiziert, nicht in TO_DO_LISTE_DETAILLIERT.md enthalten

---

## 🔴 KRITISCH: Bestelleingang an Feiertagen

### Problem
- **Beobachtung:** Bestelleingang wird an Feiertagen angezeigt (z.B. 300 am 01.01.2027, 475 am 09.02.2027, 478 am Folgetag)
- **Erwartung:** Bestelleingang sollte nur an Arbeitstagen (Mo-Fr, keine Feiertage) stattfinden

### Aktuelle Implementierung

**In `simulation/simulator.py` (Zeile 422-423):**
```python
# KORREKTUR: Bestellung findet an jedem Wochentag (Mo-Fr) statt, auch an deutschen Feiertagen
if not self.workday_calculator.is_weekend(day):
    self.procurement_manager.check_and_order(day, expected_future_demand)
```

**Problem:** Prüft nur `is_weekend()`, nicht `is_workday()` (welches auch Feiertage berücksichtigt)

**In `simulation/procurement_manager.py` (Zeile 81-91):**
```python
# Prüfe, ob das Ankunftsdatum ein Feiertag ist
if self.workday_calculator:
    lead_time = self.master_data.CHINA_SUPPLIER['Saddles'].get('lead_time_days', 49)
    target_day = day + lead_time
    target_date = self.workday_calculator.get_date_from_day(target_day)
    target_date_str = target_date.strftime(self.master_data.DATE_FORMAT)
    
    # Wenn Ankunft an Feiertag -> keine Bestellung
    if target_date_str in self.HOLIDAYS_2027:
        return  # Bestellung abbrechen
```

**Problem:** Prüft nur Ankunftsdatum, nicht Bestelldatum!

### Lösung

**In `simulation/simulator.py`:**
```python
# ÄNDERUNG: Bestellung nur an Arbeitstagen (Mo-Fr, keine Feiertage)
if self.workday_calculator.is_workday(day):  # Statt is_weekend()
    self.procurement_manager.check_and_order(day, expected_future_demand)
```

**In `simulation/china_transport.py` (get_supplier_log_dataframe):**
- Prüfe: Wird Bestelleingang nur an Arbeitstagen berechnet?
- Stelle sicher: `_calculate_order_quantity_from_volume_planning()` wird nur an Arbeitstagen aufgerufen

---

## 🔴 KRITISCH: Mengenabweichungen

### Problem 1: Fizik Tundra - Lieferant China

- **IST:** 99899
- **SOLL:** 99900
- **Abweichung:** -1

**Mögliche Ursachen:**
1. Rundungsfehler in Pool-Logik (Warenausgang-Berechnung)
2. Fehlende Korrektur für Rundungsdifferenzen (siehe EXCEL_LOGIK_ANALYSE_AP12.md)
3. Verlust durch Szenarien (DeliveryProblemScenario)

**Betroffene Dateien:**
- `simulation/china_transport.py` - `get_supplier_log_dataframe()` (Warenausgang-Berechnung)

### Problem 2: Gesamte Menge - Inbound

- **IST:** 362000
- **SOLL:** 370000
- **Abweichung:** -8000 (2.16%)

**Mögliche Ursachen:**
1. Verluste durch Transport-Szenarien (DeliveryProblemScenario)
2. Rundungsfehler in Pool-Logik
3. Fehlende Bestellungen (z.B. durch Feiertage-Problem)

**Betroffene Dateien:**
- `simulation/china_transport.py` - `get_inbound_log_dataframe()`
- `simulation/procurement_manager.py` - Bestelllogik

### Problem 3: Fizik Tundra - Inbound

- **IST:** 97739
- **Abweichung von Lieferant China:** -1160 (99899 - 97739)

**Mögliche Ursachen:**
1. Transportverluste (DeliveryProblemScenario)
2. Rundungsfehler in Verteilungslogik
3. Inkonsistenz zwischen `get_supplier_log_dataframe()` und `get_inbound_log_dataframe()`

**Betroffene Dateien:**
- `simulation/china_transport.py` - `get_inbound_log_dataframe()`
- `simulation/china_transport.py` - `process_shipments()` (Verlust-Anwendung)

### Problem 4: Fizik Tundra - Materiallager

- **Lagerzugang:** 97739 (entspricht Inbound, aber falsch)
- **Lagerabgang:** 97731
- **Abweichung:** -8

**Mögliche Ursachen:**
1. Rundungsfehler in Materialverbrauch-Berechnung
2. Inkonsistenz zwischen `material_verbrauch` und `tatsächliche PM`
3. Wochenende-Problem (siehe Problem 5)

**Betroffene Dateien:**
- `ui/material_calculations.py` - `calculate_material_inventory()`
- `ui/production_calculations.py` - `material_verbrauch` Berechnung

### Problem 5: Materiallager - Lagerzugang an Wochenenden

- **Beobachtung:** Lagerzugang an Sonntagen (sollte 0 sein)
- **Erwartung:** Lagerzugang nur an Arbeitstagen

**Aktuelle Implementierung (`ui/material_calculations.py`, Zeile 92):**
```python
receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
```

**Problem:** Prüft nicht, ob `current_date` ein Arbeitstag ist!

**Lösung:**
```python
# Am Wochenende: Lagerzugang = 0
if is_weekend or is_holiday:
    receipt_by_saddle = {s: 0.0 for s in saddle_types}
else:
    receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
```

**Hinweis:** Bereits dokumentiert in EXCEL_LOGIK_ANALYSE_AP12.md (Zeile 127-146), aber noch nicht implementiert!

---

## 🟡 MITTEL: Abweichungen zwischen Produktion und Fertigproduktelager

### Problem: MTB Allrounder

- **Produktion (tatsächliche PM):** 109877
- **Produktion (fertiggestellte PM):** 109877
- **Fertigproduktelager (Lagerzugang):** 109885
- **Fertigproduktelager (Lagerabgang):** 109885
- **Abweichung:** +8 (Lagerzugang vs. Produktion)

**Mögliche Ursachen:**
1. Rundungsfehler in Verteilungslogik (PRODUCT_SALES_SHARES, MARKETS)
2. Inkonsistenz zwischen `production_logs_cache` und Fertigproduktelager-Berechnung
3. Carry-Over-Logik in Fertigproduktelager

**Betroffene Dateien:**
- `pages/7_fertigproduktelager.py` - `create_finished_goods_log()`
- `ui/production_calculations.py` - `fertiggestellte PM` Berechnung

---

## 📋 Zusammenfassung: Prioritäten

### 🔴 HOCH (Kritisch für Datenkonsistenz):

1. **Bestelleingang an Feiertagen** - Verhindert korrekte Bestelllogik
2. **Materiallager: Lagerzugang an Wochenenden** - Bereits dokumentiert, aber nicht implementiert
3. **Mengenabweichungen (Fizik Tundra, Gesamtmenge)** - Könnten durch obige Probleme verursacht sein

### 🟡 MITTEL (Wichtig für Genauigkeit):

4. **Abweichungen zwischen Produktion und Fertigproduktelager** - Rundungsfehler

---

## 🔍 Benötigte Excel-Berechnungen

### Für Problem 1-3 (Mengenabweichungen):

**Benötigt:**
- Excel-Formeln für Warenausgang-Berechnung (bereits in EXCEL_LOGIK_ANALYSE_AP12.md)
- Excel-Formeln für Pool-Logik (bereits in EXCEL_LOGIK_ANALYSE_AP12.md)
- Excel-Formeln für Inbound-Verteilung (möglicherweise fehlt)

**Frage:** Gibt es Excel-Formeln für:
- Gesamtmenge Inbound (SOLL: 370000)?
- Fizik Tundra Verteilung in Inbound?
- Materiallager Lagerabgang-Berechnung?

### Für Problem 4 (Fertigproduktelager):

**Benötigt:**
- Excel-Formeln für Fertigproduktelager-Berechnung
- Wie wird `Lagerzugang` aus `fertiggestellte PM` berechnet?
- Wie wird Verteilung auf Märkte berechnet?

---

## ✅ Nächste Schritte

1. **Sofort prüfen:**
   - Bestelleingang an Feiertagen (simulator.py, procurement_manager.py)
   - Materiallager Wochenende (material_calculations.py)

2. **Excel-Berechnungen anfordern:**
   - Gesamtmenge Inbound (SOLL: 370000)
   - Fizik Tundra Verteilung
   - Fertigproduktelager-Berechnung

3. **Implementierung:**
   - Fix für Bestelleingang an Feiertagen
   - Fix für Materiallager Wochenende (bereits dokumentiert)
   - Analyse Mengenabweichungen (nach Excel-Berechnungen)
