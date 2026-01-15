# Architektur-Umbau: Volumenplanung als "Single Source of Truth"

## Überblick

Dieses Dokument beschreibt die Strategie, um die Volumenplanung als einzige Quelle für Nachfrageberechnungen zu etablieren. Die aktuelle Architektur hat mehrere parallele Berechnungen, die zu Inkonsistenzen führen können.

## Aktuelle Architektur (Probleme)

### Parallele Berechnungen

1. **Volumenplanung (Page 2)**
   - Berechnet Nachfrage für Anzeige
   - Eigene `DemandCalculator`-Instanzen
   - Speichert in `st.session_state.daily_demands_actual`
   - **Problem:** Daten werden nicht von anderen Komponenten verwendet

2. **Simulator**
   - Berechnet Nachfrage für Simulation
   - Eigene `DemandCalculator`-Instanz
   - Berechnet Marketing-Add-ons selbst
   - **Problem:** Parallele Berechnung, mögliche Inkonsistenzen

3. **Lieferant China (Page 3)**
   - Zeigt Daten aus Simulator
   - **Problem:** Basiert nicht auf Volumenplanung

## Zielarchitektur

```
┌─────────────────────────────────────────────────────────────┐
│  VOLUMENPLANUNG (Page 2) - "Single Source of Truth"        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Berechnet Nachfrage für ALLE 365 Tage               │ │
│  │ • Inkl. Marketing-Add-ons                             │ │
│  │ • Inkl. Carry-Over-Logik                              │ │
│  │ • Speichert in session_state.daily_demands_actual     │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┬───────────────────────────────────┘
                         │
                         │ Übergibt Daten
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  LIEFERANT CHINA (Page 3) - Datenkonsument                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Liest daily_demands_actual aus session_state          │ │
│  │ • Berechnet Bestellungen für 49 Tage im Voraus           │ │
│  │ • Zeigt Bestellungen basierend auf Nachfrage            │ │
│  │ • Übergibt Bestellungen an Simulator                    │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┬───────────────────────────────────┘
                         │
                         │ Übergibt Bestellungen
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SIMULATOR - Verwendet vorgegebene Nachfrage                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Erhält daily_demands_actual (statt selbst zu        │ │
│  │   berechnen)                                            │ │
│  │ • Verwendet daily_demands_actual für Produktionsplanung│ │
│  │ • ProcurementManager verwendet daily_demands_actual     │ │
│  │ • ChinaTransportManager erhält Bestellungen            │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┬───────────────────────────────────┘
                         │
                         │ Weiterleitung
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  INBOUND (Page 4) - Zeigt Transport-Daten                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Liest aus china_transport_manager                   │ │
│  │ • Zeigt Ankunftsdaten basierend auf Bestellungen      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Implementierungsstatus

### ✅ Bereits implementiert

1. **Volumenplanung berechnet Nachfrage**
   - `ui/volume_planning_utils.py` berechnet Nachfrage für alle 365 Tage
   - Speichert in `st.session_state.daily_demands_actual`
   - Wird beim Start der App ausgeführt

2. **Simulator verwendet Volumenplanung-Daten**
   - `simulation/simulator.py` liest `daily_demands_actual` aus `st.session_state`
   - Verwendet diese Daten für tägliche Nachfrage (Zeile 255-270)
   - Verwendet diese Daten für zukünftige Nachfrage (Bestellungen) (Zeile 347-365)

3. **Bestelleingang-Berechnung korrigiert**
   - `simulation/china_transport.py` berechnet Bestelleingang direkt aus Volumenplanung
   - Methode `_calculate_order_quantity_from_volume_planning()` implementiert
   - Summiert Nachfrage aller Produkte, die den gleichen Sattel verwenden

### ⚠️ Noch zu implementieren

1. **ProcurementManager sollte Bestellungen aus Volumenplanung verwenden**
   - Aktuell: Berechnet Bestellungen selbst
   - Ziel: Verwendet `daily_demands_actual` für Bestellungen
   - **Status:** Teilweise implementiert (Simulator verwendet bereits Volumenplanung-Daten)

2. **Validierung und Konsistenz-Checks**
   - Prüfen, ob `daily_demands_actual` vorhanden ist
   - Prüfen, ob Daten aktuell sind
   - Warnung/Fehler, falls Daten fehlen

3. **Cache-Invalidierung**
   - Bei Änderung von `yearly_volume` → `daily_demands_actual` invalidieren
   - Bei Änderung von Marketing-Szenarien → `daily_demands_actual` invalidieren
   - Bei Neuberechnung → abhängige Daten invalidieren

## Datenstruktur

### Session State

```python
st.session_state.daily_demands_actual = {
    0: {  # Tag 0 (01.01.2026)
        'MTB Allrounder': 123,
        'MTB Competition': 45,
        # ... alle Produkte
    },
    1: { ... },
    # ... alle 365 Tage
}

st.session_state.daily_demands_planned = {
    # Gleiche Struktur, aber ohne Marketing
}
```

### Bestellplan (Zukünftig)

```python
st.session_state.procurement_plan = {
    'orders': [
        {
            'order_day': -46,  # Tag der Bestellung
            'target_day': 3,    # Tag, für den bestellt wird
            'saddle_demand': 456.0,
            'order_quantity': 456.0,
            'status': 'pending'
        },
        # ... alle Bestellungen
    ],
    'calculated_at': datetime,
    'based_on_demand_plan': True
}
```

## Nächste Schritte

### Phase 1: Validierung hinzufügen ✅ (Teilweise)

- [x] Prüfen, ob `daily_demands_actual` vorhanden ist
- [x] Fallback-Logik im Simulator
- [ ] Warnung/Fehler, falls Daten fehlen

### Phase 2: Cache-Invalidierung

- [ ] Bei Änderung von `yearly_volume` → `daily_demands_actual` invalidieren
- [ ] Bei Änderung von Marketing-Szenarien → `daily_demands_actual` invalidieren
- [ ] Bei Neuberechnung → abhängige Daten invalidieren

### Phase 3: ProcurementManager anpassen

- [ ] `ProcurementManager` sollte Bestellungen aus Volumenplanung verwenden
- [ ] `procurement_plan` in `st.session_state` speichern
- [ ] Bestellungen aus `procurement_plan` lesen, statt selbst zu berechnen

### Phase 4: Cleanup

- [ ] Alte Berechnungen im Simulator entfernen
- [ ] `DemandCalculator` im Simulator entfernen (nur noch in Volumenplanung)
- [ ] Code aufräumen

## Vorteile der neuen Architektur

1. **Single Source of Truth**
   - Eine Berechnung, keine Redundanz
   - Konsistenz garantiert

2. **Klare Verantwortlichkeiten**
   - Volumenplanung: Berechnung
   - Lieferant China: Bestellplanung
   - Simulator: Simulation basierend auf vorgegebenen Daten

3. **Bessere Testbarkeit**
   - Volumenplanung isoliert testbar
   - Simulator testbar mit vorgegebenen Daten

4. **Weniger Abhängigkeiten**
   - Klare Datenflüsse
   - Einfacher zu verstehen

5. **Performance**
   - Berechnung nur einmal (in Volumenplanung)
   - Simulator nur Lookup, keine Berechnung

6. **Wartbarkeit**
   - Änderungen an Nachfrage-Logik nur in Volumenplanung
   - Klare Datenflüsse

## Potenzielle Herausforderungen

1. **Session State Management**
   - Große Datenstrukturen (365 Tage × 8 Produkte)
   - Cache-Invalidierung bei Änderungen
   - Serialisierung/Deserialisierung

2. **Rückwärtskompatibilität**
   - Alte Logik als Fallback
   - Graduelle Migration

3. **Validierung**
   - Prüfen, ob Daten vollständig und konsistent
   - Fehlerbehandlung bei fehlenden Daten

4. **Timing**
   - Wann wird `daily_demands_actual` berechnet?
   - Wann wird `procurement_plan` berechnet?
   - Wann läuft der Simulator?

## Empfohlene Reihenfolge

1. ✅ **Volumenplanung erweitern** (Bereits implementiert)
   - `daily_demands_actual` speichern
   - Validierung hinzufügen

2. ✅ **Simulator vorbereiten** (Bereits implementiert)
   - `daily_demands_actual`-Parameter hinzufügen
   - Fallback-Logik beibehalten

3. ✅ **Bestelleingang-Berechnung korrigieren** (Bereits implementiert)
   - Direkt aus Volumenplanung berechnen
   - Excel-Formel nachbilden

4. ⚠️ **Validierung und Cache-Invalidierung** (Noch zu implementieren)
   - Prüfen, ob Daten vorhanden sind
   - Cache-Invalidierung bei Änderungen

5. ⚠️ **ProcurementManager anpassen** (Noch zu implementieren)
   - Bestellungen aus Volumenplanung verwenden
   - `procurement_plan` speichern

6. ⚠️ **Cleanup** (Noch zu implementieren)
   - Redundanzen entfernen
   - Code aufräumen

## Zusammenfassung

Die Architektur-Umbau-Strategie ist **größtenteils implementiert**. Die wichtigsten Änderungen:

- ✅ Volumenplanung berechnet Nachfrage für alle 365 Tage
- ✅ Simulator verwendet Volumenplanung-Daten
- ✅ Bestelleingang-Berechnung korrigiert

**Noch zu tun:**
- ⚠️ Validierung und Cache-Invalidierung
- ⚠️ ProcurementManager vollständig anpassen
- ⚠️ Cleanup

Die Architektur ist bereits auf dem richtigen Weg, aber es gibt noch einige Optimierungen und Validierungen, die hinzugefügt werden sollten.

