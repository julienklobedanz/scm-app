# Detaillierte Problem-Analyse

**Datum:** 2026-01-25  
**Status:** Nach Implementierung der Fixes sind die Zahlen schlechter geworden

---

## 🔴 IDENTIFIZIERTE PROBLEME

### Problem 1: Fizik Tundra: 99899 → 95469 (viel schlechter!)

**Ursache:** Durch das Überspringen von Bestelleingang an chinesischen Feiertagen fehlen Bestellungen komplett.

**Excel-Logik:**
- Bestelleingang wird an ALLEN Tagen berechnet (auch Feiertagen)
- Das Freigabedatum wird auf den nächsten chinesischen Arbeitstag verschoben
- Bestelleingang wird in der Zeile des Bestelldatums angezeigt

**Aktuelle Implementierung (FALSCH):**
```python
# Prüfe chinesische Feiertage
chinese_holidays = self._get_chinese_holidays()
if curr_date in chinese_holidays:
    continue  # Überspringe chinesische Feiertage
```

**Korrektur:**
- Bestelleingang an ALLEN Tagen berechnen (auch Feiertagen)
- Freigabedatum wird automatisch auf nächsten chinesischen Arbeitstag verschoben
- Bestelleingang wird in der Zeile des Bestelldatums angezeigt

---

### Problem 2: Produktionsdatum ist gleich "Datum" (keine Neuberechnung)

**Ursache:** Das Produktionsdatum wird in Zeile 708 überschrieben mit dem Datum der Zeile.

**Aktuelle Implementierung (FALSCH):**
```python
# Zeile 687: Produktionsdatum wird in released_day_idx gespeichert
raw_data_map[released_day_idx]['production_date_str'] = production_end_date.strftime(...)

# Zeile 708: Wird überschrieben mit dem Datum der Zeile!
prod_date = start_date + timedelta(days=production_end_day_idx)
raw_data_map[production_end_day_idx]['production_date_str'] = prod_date.strftime(...)
```

**Excel-Logik:**
- Produktionsdatum wird basierend auf Freigabedatum + 4 AT berechnet
- Produktionsdatum wird in der Zeile des Freigabedatums angezeigt (nicht in der Zeile des Produktionsdatums!)

**Korrektur:**
- Zeile 708 entfernen oder anpassen
- Produktionsdatum sollte nur in `released_day_idx` gespeichert werden
- In der finalen Tabelle wird `raw['production_date_str']` aus der Zeile des Freigabedatums gelesen

---

### Problem 3: Inbound beginnt am 23.11. statt 24.11.

**Ursache:** Startdatum ist `date(self.workday_calculator.year - 1, 11, 1)` = 01.11.2026

**Excel-Logik:**
- Inbound beginnt am 24.11.2026 (erste Versendung)

**Korrektur:**
- Finde das Datum der ersten Versendung
- Beginne Tabelle ab diesem Datum (oder 24.11.2026, falls das die erste Versendung ist)

---

### Problem 4: Inbound-Summe: 353500 statt 369500 (viel schlechter!)

**Mögliche Ursachen:**
1. Durch das Überspringen von Bestelleingang an Feiertagen fehlen Bestellungen
2. Durch falsche Produktionsdatum-Berechnung werden Produktionsmengen falsch zugeordnet
3. Restbestand am letzten Tag wird nicht mitversendet (bereits identifiziert)

**Korrektur:**
- Nach Fix von Problem 1 und 2 sollte die Summe wieder steigen
- Zusätzlich: Restbestand am letzten Tag mitversenden (bereits in ANALYSE_INKONSISTENZEN.md dokumentiert)

---

## ✅ LÖSUNGEN

### Lösung 1: Bestelleingang an ALLEN Tagen berechnen

```python
# ENTFERNE die Prüfung auf chinesische Feiertage
# Bestelleingang wird an ALLEN Tagen berechnet
for day_idx in range(min(total_days, last_relevant_day_idx + 1)):
    curr_date = start_date + timedelta(days=day_idx)
    
    # Berechne Bestellmenge für diesen Tag aus Volumenplanung
    order_qty = self._calculate_order_quantity_from_volume_planning(curr_date, saddle_name, daily_demands_actual_cache)
    if order_qty > 0:
        raw_data_map[day_idx]['order'] = order_qty
        
        # Freigabedatum wird automatisch auf nächsten chinesischen Arbeitstag verschoben
        order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
        released_day = self._get_next_workday(order_day, use_chinese_holidays=True)
        # ... rest bleibt gleich
```

### Lösung 2: Produktionsdatum korrekt speichern

```python
# ENTFERNE Zeile 708 (Überschreibung)
# Produktionsdatum wird nur in released_day_idx gespeichert (Zeile 687)
# In der finalen Tabelle wird es aus der Zeile des Freigabedatums gelesen

# Zeile 700-708: ENTFERNE die Überschreibung
for production_end_day_idx, order_quantities in release_production_map.items():
    if 0 <= production_end_day_idx < total_days:
        total_production = sum(order_quantities)
        raw_data_map[production_end_day_idx]['prod'] = total_production
        # ENTFERNE: raw_data_map[production_end_day_idx]['production_date_str'] = ...
        # Das Produktionsdatum steht bereits in released_day_idx!
```

### Lösung 3: Inbound Startdatum korrigieren

```python
# Finde erste Versendung
first_shipment_date = None
# ... Logik zum Finden der ersten Versendung ...

# Startdatum = erste Versendung oder 24.11.2026
start_date = first_shipment_date or date(self.workday_calculator.year - 1, 11, 24)
```

---

## 📋 IMPLEMENTIERUNGSSCHRITTE

1. **Rückgängig machen:** Bestelleingang-Prüfung auf chinesische Feiertage entfernen
2. **Korrigieren:** Produktionsdatum-Überschreibung entfernen
3. **Korrigieren:** Inbound Startdatum auf 24.11.2026 setzen
4. **Hinzufügen:** Restbestand am letzten Tag mitversenden (aus ANALYSE_INKONSISTENZEN.md)
5. **Testen:** Alle Zahlen sollten wieder besser werden
