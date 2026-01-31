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

### Aktuelle Implementierung
- Vorlaufzeit wird aus `MasterData.SUPPLIERS['China']['lead_time']` gelesen (statisch: 49 Tage)
- Wird in `app.py` für Source Cycle Time verwendet

### Anforderung
- Vorlaufzeit soll sich **dynamisch** aus den Beschaffungs-Routen berechnen
- Summe aller SC-Zeiten (Supply Chain Zeiten):
  - Dauer Auftragserfassung
  - Produktionszeit
  - LKW China (2 AT)
  - Schiff (30 KT)
  - LKW Deutschland (2 AT)
  - Wareneingang (+1 Tag)

### Lösung
Vorlaufzeit = Summe aller `duration` Werte aus `PROCUREMENT_ROUTES` für China + Wareneingang (+1 Tag)

---

## 3. Beschaffungs-Routen Dauer - Editierbar machen

### Aktuelle Implementierung
- Dauer ist **hardcodiert** in `china_transport.py`:
  - LKW China: 2 AT (Zeile 126, 230)
  - Schiff: 30 KT (Zeile 240, 306)
  - LKW Deutschland: 2 AT (Zeile 265, 334)

### Anforderung
- Dauer soll aus `MasterData.PROCUREMENT_ROUTES` gelesen werden
- Routen-Dauer soll **editierbar** sein in Stammdaten → Beschaffung
- Änderungen müssen sich sofort auf Berechnungen auswirken

### Lösung
1. Ersetze hardcodierte Werte durch `PROCUREMENT_ROUTES` Lookup
2. Mache Routen-Dauer editierbar in `pages/8_stammdaten.py`
3. Synchronisiere Änderungen mit `MasterData.PROCUREMENT_ROUTES`

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
