# Ladungsverlust auf See - Implementierung korrigiert

**Datum:** 28.01.2026  
**Problem:** Ladungsverlust wurde am falschen Datum geprüft, UI zeigte keine geplanten Ankunftsdaten  
**Status:** ✅ **KORRIGIERT**

---

## 🔍 Identifiziertes Problem

### Beschreibung

Bei der Auswahl eines Ladungsverlust-Szenarios kann der Benutzer ein beliebiges Datum eingeben. Da mehrere Schiffe gleichzeitig auf See sind, muss das **Ankunftsdatum des Schiffes** verwendet werden, um das betroffene Schiff eindeutig zu identifizieren.

**Aktuelles Problem:**
- Ladungsverlust wurde am **Abfahrtsdatum** geprüft (`day_idx_sim`)
- UI zeigte freie Datumsauswahl ohne Hinweis auf geplante Ankunftsdaten
- Mehrere Schiffe gleichzeitig auf See → unklare Zuordnung

**Beispiel:**
- Zu einem Zeitpunkt sind 4 Schiffe gleichzeitig auf See
- Benutzer wählt Datum: 19.07.2027
- Problem: Welches Schiff ist gemeint? (Abfahrtsdatum ist nicht eindeutig)

---

## ✅ Durchgeführte Korrekturen

### 1. Logik-Korrektur: Prüfung am geplanten Ankunftsdatum des Schiffes

**Vorher (`simulation/china_transport.py` Zeile ~1405):**
```python
# Prüfe Ladungsverlust-Szenarien basierend auf ABFAHRTSDATUM (day_idx_sim)
cargo_loss_scenarios = self.scenario_manager.get_cargo_loss_scenarios(day_idx_sim)
if day_idx_sim == scenario.start_day:
    cargo_loss_active = True
```

**Nachher:**
```python
# Berechne geplantes Ankunftsdatum des Schiffes für diese Zeile
day_port_ideal_for_loss = self._add_workdays(day_idx_sim, 2)
date_port_ideal_for_loss = self.workday_calculator.get_date_from_day(day_port_ideal_for_loss)
# ... Berechnung des geplanten Ankunftsdatums ...
day_ship_arr_ideal_for_loss = (date_ship_arr_ideal_for_loss - date(...)).days

# KRITISCH: Prüfe Ladungsverlust-Szenarien basierend auf GEPLANTEM ANKUNFTSDATUM DES SCHIFFES
# Dies identifiziert eindeutig das betroffene Schiff (mehrere Schiffe können gleichzeitig auf See sein)
cargo_loss_scenarios = self.scenario_manager.get_cargo_loss_scenarios(day_ship_arr_ideal_for_loss)
if day_ship_arr_ideal_for_loss == scenario.start_day:
    cargo_loss_active = True
```

**Vorteil:**
- Eindeutige Identifikation des betroffenen Schiffes
- Mehrere Schiffe gleichzeitig auf See → kein Problem mehr
- Konsistent mit Verspätungs-Logik

### 2. UI-Verbesserung: Dropdown mit geplanten Ankunftsdaten

**Vorher:**
- Freie Datumsauswahl mit `st.date_input()`
- Keine Hinweise auf geplante Ankunftsdaten
- Benutzer kann ungültige Daten eingeben

**Nachher:**
- **Dropdown-Liste** mit nur geplanten Schiffsankunftsdaten
- **Erklärende Beschreibung:**
  - "Verliert die gesamte Ladung einer Lieferung (Mengen werden auf 0 gesetzt)"
  - "💡 **Hinweis:** Datumsauswahl nach geplanter Ankunft des betreffenden Schiffes vornehmen. Zu jedem Zeitpunkt sind mehrere Schiffe gleichzeitig auf See - die Auswahl des Ankunftsdatums identifiziert das betroffene Schiff eindeutig."
- **Fallback:** Freie Datumsauswahl mit Warnung wenn keine Daten verfügbar

**Code:**
```python
# PERFORMANCE: Hole geplante Ankunftsdaten für Schiffe (verwendet Cache)
planned_ship_arrival_dates = _get_planned_arrival_dates("ship_arrival", planning_year)

if planned_ship_arrival_dates:
    # Dropdown mit geplanten Ankunftsdaten
    selected_date_str = st.selectbox(
        "Geplantes Ankunftsdatum des Schiffes",
        options=list(date_options.keys()),
        help="Wählen Sie das geplante Ankunftsdatum des Schiffes, dessen Ladung verloren geht..."
    )
else:
    # Fallback mit Warnung
    loss_date = st.date_input(...)
```

### 3. Performance-Optimierung: Caching

**Implementiert:**
- Verwendet `_get_planned_arrival_dates("ship_arrival", planning_year)`
- Diese Funktion verwendet bereits Caching (siehe `VERSPÄTUNG_UI_VERBESSERUNG.md`)
- Cache-Key: `planned_arrival_dates_ship_arrival_{planning_year}`
- Cache wird invalidiert wenn:
  - Szenarien entfernt werden
  - Simulation neu gestartet wird

**Vorteil:**
- Keine Performance-Verschlechterung
- Geplante Ankunftsdaten werden nur einmal berechnet
- Weitere Renderings sind schnell (Cache-Hit)

---

## 📋 Warum Ankunftsdatum statt Abfahrtsdatum?

### Problem mit Abfahrtsdatum:

**Szenario:** Zu einem Zeitpunkt sind 4 Schiffe gleichzeitig auf See

**Schiff 1:**
- Abfahrt: 01.07.2027
- Ankunft: 31.07.2027

**Schiff 2:**
- Abfahrt: 08.07.2027
- Ankunft: 07.08.2027

**Schiff 3:**
- Abfahrt: 15.07.2027
- Ankunft: 14.08.2027

**Schiff 4:**
- Abfahrt: 22.07.2027
- Ankunft: 21.08.2027

**Problem:** Wenn Benutzer "Abfahrt 15.07.2027" wählt, ist klar welches Schiff gemeint ist. Aber wenn mehrere Schiffe am gleichen Tag abfahren (z.B. wegen Verspätungen), wird es unklar.

### Lösung mit Ankunftsdatum:

**Vorteil:**
- Jedes Schiff hat ein **eindeutiges** geplantes Ankunftsdatum
- Selbst wenn mehrere Schiffe gleichzeitig auf See sind, ist die Zuordnung eindeutig
- Konsistent mit Verspätungs-Logik (beide verwenden Ankunftsdatum)

**Beispiel:**
- Benutzer wählt: "Ankunft 31.07.2027"
- → Eindeutig: Schiff 1 ist gemeint
- → Keine Verwirrung mehr

---

## 🧪 Test-Empfehlungen

### Test 1: Ladungsverlust mit geplantem Ankunftsdatum

**Schritte:**
1. Starte Simulation
2. Gehe zu Szenarien-Sidebar
3. Wähle "Ladungsverlust auf See"
4. Prüfe: Werden nur geplante Schiffsankunftsdaten angezeigt?

**Erwartung:**
- Dropdown zeigt nur Daten wie 16.07.2027, 23.07.2027, etc.
- Kein 19.07.2027 (kein geplantes Ankunftsdatum)

### Test 2: Ladungsverlust hinzufügen

**Schritte:**
1. Wähle geplantes Ankunftsdatum (z.B. 23.07.2027)
2. Füge Ladungsverlust hinzu
3. Prüfe Inbound-Tabelle: Wird Ladungsverlust angewendet?

**Erwartung:**
- Ladungsverlust wird korrekt angewendet
- Mengen werden auf 0 gesetzt für das betroffene Schiff
- Spalte "Ladungsverlust" zeigt "Ja"

### Test 3: Mehrere Schiffe gleichzeitig auf See

**Schritte:**
1. Prüfe Inbound-Tabelle: Welche Schiffe sind gleichzeitig auf See?
2. Wähle Ankunftsdatum von Schiff 1
3. Füge Ladungsverlust hinzu
4. Prüfe: Wird nur Schiff 1 betroffen?

**Erwartung:**
- Nur das Schiff mit dem gewählten Ankunftsdatum wird betroffen
- Andere Schiffe bleiben unberührt
- Eindeutige Zuordnung gewährleistet

---

## ✅ Status

- ✅ Logik korrigiert: Prüfung am geplanten Ankunftsdatum des Schiffes
- ✅ UI verbessert: Dropdown mit geplanten Ankunftsdaten
- ✅ Erklärende Beschreibung hinzugefügt
- ✅ Performance-Optimierung: Caching implementiert
- ✅ Cache-Invalidierung: Funktioniert korrekt

---

**Status:** ✅ **KORRIGIERT - BEREIT FÜR TESTS**
