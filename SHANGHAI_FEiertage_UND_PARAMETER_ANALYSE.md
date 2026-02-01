# Shanghai Feiertage und Parameter-Analyse

**Datum:** 2026-01-29

## 1. Shanghai Feiertage

### Aktuelle Implementierung
- Die `holidays` Library lädt nationale chinesische Feiertage (`CN`)
- Lokale Shanghai-spezifische Feiertage werden **nicht** explizit berücksichtigt
- Die `_get_chinese_holidays()` Methode verwendet `HolidaysConfig.get_holidays_for_year(year, 'CN')`

### Einschränkung
Die `holidays` Python Library unterstützt normalerweise nur **nationale** Feiertage, nicht lokale/regionale Feiertage wie Shanghai.

### Lösung
Wenn Shanghai-spezifische Feiertage benötigt werden, müssten diese manuell zur `HolidaysConfig` Klasse hinzugefügt werden.

**Status:** ✅ Aktuell werden nationale chinesische Feiertage berücksichtigt, die auch für Shanghai gelten.

---

## 2. Vorlaufzeit - Dynamische Berechnung

### Aktuelle Implementierung (Stand: 2026-01-31)
- ✅ **IMPLEMENTIERT:** Vorlaufzeit wird **dynamisch** aus `PROCUREMENT_ROUTES` berechnet
- Funktion: `MasterData.calculate_lead_time_from_routes()`
- Berechnet sich aus:
  - Dauer Auftragserfassung (`order_entry_duration` aus `SUPPLIERS['China']`)
  - Produktionszeit (`production_time` aus `SUPPLIERS['China']`)
  - LKW China (aus `PROCUREMENT_ROUTES`, z.B. 2 AT)
  - Schiff (aus `PROCUREMENT_ROUTES`, z.B. 30 KT)
  - LKW Deutschland (aus `PROCUREMENT_ROUTES`, z.B. 2 AT)
  - Wareneingang (+1 Tag)

### Verwendung
- `simulation/simulator.py`: Initial orders verwenden dynamische Lead Time
- `simulation/procurement_manager.py`: Tägliche Bestellungen verwenden dynamische Lead Time
- `pages/8_stammdaten.py`: Anzeige und Aktualisierung der Lead Time

### Wichtige Hinweise
- Bei Änderung der Beschaffungsrouten-Zeiten wird die Lead Time automatisch neu berechnet
- Die Simulation wird zurückgesetzt, damit initial orders mit der neuen Lead Time neu berechnet werden
- Initial orders decken auch negative Tage ab (wenn Lead Time größer wird)
- Bei Neustart werden `PROCUREMENT_ROUTES` auf Standardwerte zurückgesetzt (`standard_duration`)

---

## 3. Beschaffungs-Routen Dauer - Editierbar machen

### Aktuelle Implementierung (Stand: 2026-01-31)
- ✅ **IMPLEMENTIERT:** Dauer wird aus `MasterData.PROCUREMENT_ROUTES` gelesen
- ✅ **IMPLEMENTIERT:** Routen-Dauer ist **editierbar** in Stammdaten → Beschaffung
- ✅ **IMPLEMENTIERT:** Änderungen wirken sich sofort auf Berechnungen aus

### Implementierung
1. ✅ Hardcodierte Werte wurden durch `PROCUREMENT_ROUTES` Lookup ersetzt (`_get_route_duration()`)
2. ✅ Routen-Dauer ist editierbar in `pages/8_stammdaten.py` (Tab "Beschaffung")
3. ✅ Änderungen werden synchronisiert mit `MasterData.PROCUREMENT_ROUTES`
4. ✅ Bei Änderung wird die Lead Time neu berechnet und die Simulation zurückgesetzt
5. ✅ Bei Neustart werden `PROCUREMENT_ROUTES` auf Standardwerte zurückgesetzt (`standard_duration`)

### Wichtige Hinweise
- Änderungen an Routen-Dauer erfordern Neustart der Simulation für korrekte Berechnungen
- Die Lead Time wird automatisch neu berechnet bei Änderung der Routen-Dauer
- Initial orders werden mit der neuen Lead Time neu berechnet (inkl. negative Tage)

---

## 4. "Dauer Standard" Erklärung

### Definition
`standard_duration` ist ein **Referenzwert** in `PROCUREMENT_ROUTES`, der die ursprüngliche/Standard-Dauer einer Route zeigt.

### Unterschied zu `duration`
- `duration`: Aktuelle Dauer (kann geändert werden)
- `standard_duration`: Ursprüngliche Standard-Dauer (Referenzwert)

### Beispiel
```python
{
    'transport': 'Schiff-Typ30',
    'duration': 30,           # Aktuelle Dauer (editierbar)
    'standard_duration': 22  # Ursprüngliche Standard-Dauer (Referenz)
}
```

**Status:** `standard_duration` wird aktuell nicht im Code verwendet, ist nur ein Informationswert.

---

## 5. Editierbare Parameter - Verwendung prüfen

### Parameter die bereits verwendet werden:
- ✅ **Schichten**: `min_shifts_per_day`, `max_shifts_per_day` → verwendet in `production_planner.py`
- ✅ **Arbeitslast**: `DAILY_WORKLOAD` → verwendet in `workday_calculator.py`
- ✅ **Produktionszeit**: `production_time` → verwendet in `china_transport.py`

### Parameter die NICHT verwendet werden:
- ❌ **Dauer Auftragserfassung**: `order_entry_duration` → wird aktuell nicht verwendet

### Anforderung
- Wenn Montag = 0.0 in `DAILY_WORKLOAD`, sollten Montagszeilen überall Nullen zeigen
- Dies wird bereits durch `workday_calculator.get_workload_factor()` implementiert

---

## 6. Konsistenz bei Änderungen

### Problem
- Änderungen an Losgröße werden nicht sofort in anderen Sichten (z.B. "Auslieferung") sichtbar
- Benötigt Neuladen der Seite

### Lösung
- Verwende `st.rerun()` nach Parameteränderungen ODER
- Stelle sicher, dass alle Sichten `MasterData` direkt lesen (nicht aus Cache)

---

## 7. Verkaufsanteile - Validierung verbessern

### Aktuelle Implementierung
- Verkaufsanteile sind bereits editierbar
- Validierung normalisiert nur wenn `total > 0`, prüft aber nicht ob `total = 100%`

### Anforderung
- Summe muss **exakt 100%** sein
- Keine negativen Werte
- User-freundliche Fehlermeldungen

### Lösung
- Prüfe ob `total == 100.0` (mit Toleranz für Rundungsfehler)
- Zeige Warnung wenn `total != 100.0`
- Normalisiere automatisch oder zeige Fehler
