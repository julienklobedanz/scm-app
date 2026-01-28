# Backlog-Problem nach Performance-Optimierung

**Datum:** 28.01.2026  
**Problem:** Backlog ist nach Performance-Optimierungen viel höher geworden  
**Status:** 🔍 **IN ANALYSE**

---

## 🔴 Problem-Beschreibung

### Vorher (vor Performance-Optimierungen):
- MTB Allrounder: 145
- Competition: 73
- Downhill: 48
- Extreme: 25
- Marathon: 40
- Performance: 62
- Trail: 67
- **Gesamt:** ~460

### Nachher (nach Performance-Optimierungen):
- MTB Allrounder: 2536
- Competition: 1250
- Downhill: 869
- Extreme: 609
- Marathon: 435
- Performance: 680
- Trail: 991
- **Gesamt:** ~7470

**Verschlechterung:** ~16x höherer Backlog!

---

## 🔍 Mögliche Ursachen

### 1. **Reduzierte Berechnungsgrenzen schneiden Transporte ab**

**Problem in `get_inbound_log_dataframe()`:**
- `max_calculation_days = min(total_days, last_relevant_day + 1, 350)`
- Wenn `last_relevant_day > 350`, werden Transporte nach Tag 350 nicht berechnet
- **Auswirkung:** Material fehlt → Produktion kann nicht stattfinden → Backlog wächst

**Fix:** Begrenzung auf 350 Tage entfernt, stattdessen:
```python
plan_year_end_day = (date(self.workday_calculator.year, 12, 31) - start_date).days
max_calculation_days = min(total_days, max(last_relevant_day + 1, plan_year_end_day + 1))
```

### 2. **Vektorisierte Verarbeitung könnte Daten verlieren**

**Problem in `_get_inbound_arrivals_by_day_and_saddle()`:**
- Vektorisierte Version verwendet `qty_series[qty_series > 0]` und dann `valid_rows.loc[qty_series.index]`
- **Mögliches Problem:** Wenn `qty_series` gefiltert wird, könnten Zeilen mit `_day_idx` verloren gehen

**Fix:** Verwende `valid_rows.groupby('_day_idx')` direkt statt gefilterte `qty_series`:
```python
grouped = valid_rows.groupby('_day_idx')[saddle_name].sum()
```

### 3. **Reduzierte Berechnungsgrenzen in `get_supplier_log_dataframe()`**

**Problem:**
- `last_relevant_day_idx = min(last_relevant_day_idx, 350)` könnte Transporte abschneiden
- **Auswirkung:** Wenn letzte Produktion am Tag 320, dann `last_relevant_day = 360`, aber wird auf 350 begrenzt
- Transporte zwischen Tag 350-360 fehlen!

**Fix:** Begrenzung auf 350 Tage entfernt, stattdessen:
```python
plan_year_end_day_idx = (date(self.workday_calculator.year, 12, 31) - start_date).days
last_relevant_day_idx = max(last_relevant_day_idx, plan_year_end_day_idx)
```

---

## ✅ Implementierte Fixes

### 1. **Begrenzung auf 350 Tage entfernt**

**In `get_inbound_log_dataframe()`:**
- Vorher: `max_calculation_days = min(total_days, last_relevant_day + 1, 350)`
- Nachher: `max_calculation_days = min(total_days, max(last_relevant_day + 1, plan_year_end_day + 1))`

**In `get_supplier_log_dataframe()`:**
- Vorher: `last_relevant_day_idx = min(last_relevant_day_idx, 350)`
- Nachher: `last_relevant_day_idx = max(last_relevant_day_idx, plan_year_end_day_idx)`

### 2. **Vektorisierte Verarbeitung korrigiert**

**In `_get_inbound_arrivals_by_day_and_saddle()`:**
- Vorher: `grouped = valid_rows.loc[qty_series.index].groupby('_day_idx')[saddle_name].sum()`
- Nachher: `grouped = valid_rows.groupby('_day_idx')[saddle_name].sum()`

**Vorteil:** Alle Zeilen mit `_day_idx` werden berücksichtigt, nicht nur die mit `qty > 0`

---

## 📊 Erwartetes Ergebnis

Nach diesen Fixes:
- ✅ Alle Transporte bis Ende des Jahres werden berechnet
- ✅ Keine Transporte werden abgeschnitten
- ✅ Material kommt korrekt an → Produktion kann stattfinden → Backlog sollte wieder niedrig sein

---

**Status:** ✅ **FIXES IMPLEMENTIERT**  
**Nächster Schritt:** Testen ob Backlog wieder auf normale Werte zurückgeht
