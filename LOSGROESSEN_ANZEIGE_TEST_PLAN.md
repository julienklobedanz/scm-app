# Test-Plan: Losgrößen-Anzeige Anpassung

**Datum:** 01.02.2026  
**Status:** Implementiert, Tests erforderlich

---

## Implementierte Änderung

**Datei:** `simulation/china_transport.py`  
**Zeile:** 1474

**Änderung:**
```python
# VORHER:
if current_lot_size > 0:
    is_transport_day = True

# NACHHER:
if current_lot_size > 0 and curr_date.weekday() == 2:  # Mittwoch = 2
    is_transport_day = True
```

---

## Test-Szenarien

### 1. Standard-Verhalten: Versand nur mittwochs

**Erwartung:**
- Versand nur an Mittwochen
- Reste bleiben im Hafen bis nächster Mittwoch
- Gesamtmengen stimmen (kumuliert)

**Prüfung:**
- Inbound-Tabelle: Versand nur mittwochs sichtbar
- "Lieferant China"-Tabelle: Warenbestand zeigt Reste im Hafen

### 2. Edge Case: Mittwoch mit genau 500 Stück

**Erwartung:**
- Versand: 500 Stück
- Rest: 0 Stück

**Prüfung:**
- Inbound-Tabelle zeigt Versand von 500 Stück
- Keine Reste im Hafen

### 3. Edge Case: Mittwoch mit 550 Stück

**Erwartung:**
- Versand: 500 Stück (Losgröße)
- Rest: 50 Stück bleibt im Hafen

**Prüfung:**
- Inbound-Tabelle zeigt Versand von 500 Stück
- "Lieferant China"-Tabelle zeigt Warenbestand von 50 Stück

### 4. Edge Case: Dienstag mit 1000 Stück

**Erwartung:**
- Kein Versand (nicht Mittwoch)
- Rest: 1000 Stück bleibt im Hafen

**Prüfung:**
- Inbound-Tabelle zeigt keinen Versand
- "Lieferant China"-Tabelle zeigt Warenbestand von 1000 Stück

### 5. Edge Case: Mittwoch mit 250 Stück

**Erwartung:**
- Kein Versand (< 500, Losgröße nicht erreicht)
- Rest: 250 Stück bleibt im Hafen

**Prüfung:**
- Inbound-Tabelle zeigt keinen Versand
- "Lieferant China"-Tabelle zeigt Warenbestand von 250 Stück

### 6. Konsistenz-Check: Materiallager

**Erwartung:**
- Materiallager zeigt korrekte Zugänge
- Zugänge basieren auf "Tatsächliche Ankunft LKW 🇩🇪" (nicht betroffen)

**Prüfung:**
- Materiallager-Tabelle zeigt korrekte Mengen
- Zugänge stimmen mit Inbound-Tabelle überein

### 7. Konsistenz-Check: Produktion

**Erwartung:**
- Produktion verwendet korrekte Materialzugänge
- Initialbestand stimmt mit Inbound-Tabelle überein

**Prüfung:**
- Produktion-Tabelle zeigt korrekte Materialverfügbarkeit
- Initialbestand stimmt mit Inbound-Tabelle überein

---

## Manuelle Test-Schritte

1. **App starten:**
   ```bash
   streamlit run app.py
   ```

2. **Standard-Szenario laden:**
   - Seite "Inbound" öffnen
   - Prüfen: Versand nur mittwochs sichtbar

3. **"Lieferant China" prüfen:**
   - Seite "Lieferant China" öffnen
   - Prüfen: Warenbestand zeigt Reste im Hafen

4. **Materiallager prüfen:**
   - Seite "Materiallager" öffnen
   - Prüfen: Zugänge stimmen mit Inbound-Tabelle überein

5. **Produktion prüfen:**
   - Seite "Produktion" öffnen
   - Prüfen: Materialverfügbarkeit stimmt

---

## Erwartete Ergebnisse

### Vor Änderung:
- Versand täglich (wenn ≥ 500)
- Reste werden schnell mitverschifft
- Alle Mengen durch 500 teilbar

### Nach Änderung:
- Versand nur mittwochs (wenn ≥ 500)
- Reste bleiben im Hafen bis nächster Mittwoch
- Konsistent mit `process_shipments()`

---

## Rollback-Anleitung

Falls Probleme auftreten:

1. **Zurück zum Saving Point:**
   ```bash
   git checkout simulation/china_transport.py
   ```

2. **Oder manuell:**
   - Zeile 1474 ändern von:
     ```python
     if current_lot_size > 0 and curr_date.weekday() == 2:
     ```
   - Zurück zu:
     ```python
     if current_lot_size > 0:
     ```
