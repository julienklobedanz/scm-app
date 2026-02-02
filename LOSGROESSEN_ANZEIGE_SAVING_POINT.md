# Saving Point: Vor Losgrößen-Anzeige Anpassung

**Datum:** 01.02.2026  
**Commit:** 6b5c10b (Feature: Materialverbrauch-Analyse pro Datum)

---

## Aktueller Stand

### Datei: `simulation/china_transport.py`
**Zeile 1463:** 
```python
if current_lot_size > 0:
    is_transport_day = True
```

**Verhalten:**
- Versand täglich, wenn `current_lot_size > 0`
- Reste werden als `carry_over` mitgenommen und am nächsten Tag mitverschifft
- **NICHT konsistent** mit `process_shipments()` (verschifft nur mittwochs)

---

## Zurückkehren zum Saving Point

**Falls Probleme auftreten:**

1. **Git Reset (falls committed):**
   ```bash
   git checkout simulation/china_transport.py
   ```

2. **Manuell rückgängig machen:**
   - Zeile 1463 ändern von:
     ```python
     if current_lot_size > 0 and curr_date.weekday() == 2:
     ```
   - Zurück zu:
     ```python
     if current_lot_size > 0:
     ```
   - Kommentare bei Zeile ~1460 entfernen

---

## Betroffene Dateien

- `simulation/china_transport.py` (Hauptänderung)
- `pages/4_inbound.py` (verwendet `get_inbound_log_dataframe()`)
- `ui/material_calculations.py` (verwendet Inbound-Daten)
- `simulation/production_planner.py` (verwendet Inbound-Daten)

---

## Erwartete Auswirkungen

**Vor Änderung:**
- Versand täglich (wenn ≥ 500)
- Reste werden schnell mitverschifft
- Alle Mengen durch 500 teilbar

**Nach Änderung:**
- Versand nur mittwochs (wenn ≥ 500)
- Reste bleiben im Hafen bis nächster Mittwoch
- Konsistent mit `process_shipments()`
