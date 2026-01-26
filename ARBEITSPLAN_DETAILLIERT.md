# Detaillierter Arbeitsplan - To-Do Umsetzung

**Erstellt:** 2026-01-25  
**Basis:** TO_DO_LISTE_DETAILLIERT.md  
**Status:** Vorbereitung

---

## 📋 Übersicht: 9 To-Do's + 5 neu identifizierte Probleme

### Priorisierung nach Kritikalität

**🔴 HOCH (Kritisch für Datenkonsistenz):**
- **NEU:** Bestelleingang an Feiertagen (01.01.2027, 09.02.2027, etc.)
- **NEU:** Materiallager: Lagerzugang an Wochenenden (Sonntagen)
- **NEU:** Mengenabweichungen (Fizik Tundra: 99899 statt 99900, Gesamt: 362000 statt 370000)
- To-Do 2: Inbound-Tage prüfen (Verfügbarkeit +1 Tag)
- To-Do 3: Material am Wochenende (Verfügbarkeit korrigieren)
- To-Do 6: Schichtenplanung bei Backlog (zu aggressiv)

**🟡 MITTEL (Wichtig für Benutzerfreundlichkeit):**
- **NEU:** Abweichungen zwischen Produktion und Fertigproduktelager (MTB Allrounder: +8)
- To-Do 1: SCOR-Metriken verschieben/umstrukturieren
- To-Do 4: Spalten in Produktion entfernen
- To-Do 5: Farbliche Markierungen in Inbound

**🟢 NIEDRIG (Erweiterungen):**
- To-Do 7: Marketing für einzelne Produkte
- To-Do 8: Nachfrage-Faktor in Prozent
- To-Do 9: Andere Szenarien implementieren

**📄 Detaillierte Analyse:** Siehe `PROBLEME_IDENTIFIZIERT.md`

---

## 🔴 PHASE 1: Kritische Datenkonsistenz-Fixes

### NEU: Bestelleingang an Feiertagen

**Ziel:** Verhindere Bestelleingang an Feiertagen (z.B. 01.01.2027, 09.02.2027).

**Betroffene Dateien:**
- `simulation/simulator.py` - Zeile 422-423 (Prüft nur `is_weekend()`, nicht `is_workday()`)
- `simulation/china_transport.py` - `get_supplier_log_dataframe()` (Bestelleingang-Berechnung)

**Schritte:**

1. **Korrektur in simulator.py:**
   ```python
   # ALT (Zeile 422-423):
   if not self.workday_calculator.is_weekend(day):
       self.procurement_manager.check_and_order(day, expected_future_demand)
   
   # NEU:
   if self.workday_calculator.is_workday(day):  # Statt is_weekend()
       self.procurement_manager.check_and_order(day, expected_future_demand)
   ```

2. **Prüfe get_supplier_log_dataframe():**
   - [ ] Stelle sicher: Bestelleingang wird nur an Arbeitstagen berechnet
   - [ ] Prüfe: Wird `_calculate_order_quantity_from_volume_planning()` nur an Arbeitstagen aufgerufen?

3. **Validierung:**
   - [ ] Teste: Kein Bestelleingang am 01.01.2027
   - [ ] Teste: Kein Bestelleingang am 09.02.2027
   - [ ] Prüfe: Alle Feiertage werden korrekt übersprungen

**Kritische Aspekte:**
- ⚠️ Beeinflusst Bestelllogik direkt
- ⚠️ Kann zu Mengenabweichungen führen (siehe Problem 2)

---

### NEU: Materiallager - Lagerzugang an Wochenenden

**Ziel:** Verhindere Lagerzugang an Wochenenden (Sonntagen).

**Betroffene Dateien:**
- `ui/material_calculations.py` - Zeile 92 (Prüft nicht `is_workday`)

**Schritte:**

1. **Korrektur in material_calculations.py:**
   ```python
   # ALT (Zeile 92):
   receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
   
   # NEU:
   # Am Wochenende: Lagerzugang = 0
   if is_weekend or is_holiday:
       receipt_by_saddle = {s: 0.0 for s in saddle_types}
   else:
       receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {s: 0.0 for s in saddle_types})
   ```

2. **Validierung:**
   - [ ] Teste: Kein Lagerzugang an Sonntagen
   - [ ] Prüfe: Bestand morgens = Bestand abends (vom Vortag) an Wochenenden

**Hinweis:** Bereits dokumentiert in EXCEL_LOGIK_ANALYSE_AP12.md (Zeile 127-146), aber noch nicht implementiert!

**Kritische Aspekte:**
- ⚠️ Beeinflusst Materialverfügbarkeit
- ⚠️ Kann zu falschen Produktionsplanungen führen

---

### NEU: Mengenabweichungen analysieren und korrigieren

**Ziel:** Analysiere und korrigiere Mengenabweichungen:
- Fizik Tundra (Lieferant China): 99899 statt 99900 (-1)
- Gesamte Menge (Inbound): 362000 statt 370000 (-8000, 2.16%)
- Fizik Tundra (Inbound): 97739 (abweichend von 99899)
- Fizik Tundra (Materiallager): 97731 (abweichend von 97739)

**Betroffene Dateien:**
- `simulation/china_transport.py` - Warenausgang-Berechnung, Pool-Logik
- `ui/material_calculations.py` - Materialverbrauch-Berechnung

**Schritte:**

1. **Warte auf Excel-Berechnungen:**
   - [ ] Excel-Formeln für Gesamtmenge Inbound (SOLL: 370000)
   - [ ] Excel-Formeln für Fizik Tundra Verteilung
   - [ ] Excel-Formeln für Materiallager Lagerabgang

2. **Analyse:**
   - [ ] Prüfe: Warenausgang-Berechnung (siehe EXCEL_LOGIK_ANALYSE_AP12.md)
   - [ ] Prüfe: Pool-Logik (Rundungsfehler?)
   - [ ] Prüfe: Transportverluste (DeliveryProblemScenario)
   - [ ] Prüfe: Materialverbrauch-Berechnung

3. **Korrektur:**
   - [ ] Implementiere Korrektur für Rundungsdifferenzen (EXCEL_LOGIK_ANALYSE_AP12.md, Zeile 276-293)
   - [ ] Korrigiere Warenausgang-Berechnung (EXCEL_LOGIK_ANALYSE_AP12.md, Zeile 260-274)
   - [ ] Stelle sicher: Konsistenz zwischen Lieferant China, Inbound, Materiallager

**Kritische Aspekte:**
- ⚠️ Benötigt Excel-Berechnungen für vollständige Analyse
- ⚠️ Könnte durch andere Probleme verursacht sein (Bestelleingang an Feiertagen, etc.)

---

### To-Do 2: Inbound-Tage - Verfügbarkeit im Lager +1 Tag prüfen

**Ziel:** Sicherstellen, dass `available_day = arrival_day + 1` (Arbeitstag) korrekt implementiert ist.

**Betroffene Dateien:**
- `simulation/china_transport.py` - `place_order()`, `get_inbound_log_dataframe()`, `get_daily_arrival_qty()`
- `simulation/simulator.py` - Verwendung von `get_daily_arrival_qty()`

**Schritte:**

1. **Analyse der aktuellen Logik:**
   - [ ] Prüfe `place_order()`: Wie wird `available_day` berechnet?
   - [ ] Prüfe `get_inbound_log_dataframe()`: Welches Datum wird als "Verfügbar im Lager 🇩🇪" angezeigt?
   - [ ] Prüfe `get_daily_arrival_qty()`: Verwendet es `available_day` oder `arrival_day`?
   - [ ] Prüfe Konsistenz: Werden Wochenenden/Feiertage korrekt übersprungen?

2. **Korrektur (falls nötig):**
   - [ ] Stelle sicher: `available_day = nächster Arbeitstag nach arrival_day`
   - [ ] Stelle sicher: `get_daily_arrival_qty(day)` gibt nur an `available_day` zurück
   - [ ] Stelle sicher: Inbound-Tabelle zeigt beide Daten (Ankunft + Verfügbarkeit)

3. **Validierung:**
   - [ ] Vergleiche Inbound-Tabelle mit Materiallager
   - [ ] Prüfe: Bestand morgens = Zugang am `available_day`?
   - [ ] Teste mit Wochenende-Ankunft

**Kritische Aspekte:**
- ⚠️ Diese Logik beeinflusst Materialverfügbarkeit direkt
- ⚠️ Falsche Berechnung führt zu falschen Produktionsplanungen
- ⚠️ Muss konsistent mit `get_daily_arrival_qty()` sein

---

### To-Do 3: Material am Wochenende - Verfügbarkeit korrigieren

**Ziel:** Sicherstellen, dass Material, das am Wochenende physisch ankommt, erst am nächsten Arbeitstag verfügbar ist.

**Betroffene Dateien:**
- `simulation/china_transport.py` - `place_order()`, `process_shipments()`
- `simulation/workday_calculator.py` - `is_workday()`

**Schritte:**

1. **Prüfe aktuelle Logik:**
   - [ ] Prüfe: Wird `available_day` korrekt berechnet (nächster Arbeitstag)?
   - [ ] Prüfe: Werden Wochenenden in `get_daily_arrival_qty()` übersprungen?
   - [ ] Prüfe: Zeigt Inbound-Tabelle beide Daten (Ankunft + Verfügbarkeit)?

2. **Korrektur (falls nötig):**
   - [ ] Stelle sicher: `arrival_day` kann Wochenende sein (physische Ankunft)
   - [ ] Stelle sicher: `available_day = nächster Arbeitstag nach arrival_day`
   - [ ] Stelle sicher: `get_daily_arrival_qty()` gibt nur an Arbeitstagen zurück

3. **Inbound-Tabelle anpassen:**
   - [ ] Zeige beide Spalten: "Tatsächliche Ankunft LKW 🇩🇪" + "Verfügbar im Lager 🇩🇪"
   - [ ] Markiere Wochenenden farblich (siehe To-Do 5)

**Kritische Aspekte:**
- ⚠️ Muss konsistent mit To-Do 2 sein
- ⚠️ Beeinflusst Materialverfügbarkeit
- ⚠️ Muss in `get_daily_arrival_qty()` berücksichtigt werden

---

### To-Do 6: Schichtenplanung bei Backlog - Zu aggressiv

**Ziel:** Korrigiere Logik: Bei Backlog > 0 maximale benötigte Kapazität nutzen (nicht zwingend 3 Schichten).

**Betroffene Dateien:**
- `simulation/production_planner.py` - Zeile 141-156
- `ui/production_calculations.py` - Dynamische Produktionsberechnung
- `pages/2_volumenplanung.py` - Schichtenberechnung (konsistenz prüfen)

**Schritte:**

1. **Prüfe aktuelle Logik:**
   - [ ] Prüfe `production_planner.py` Zeile 147-150: `if total_backlog > 0: shifts = 3`
   - [ ] Prüfe `production_calculations.py`: Wird dieselbe Logik verwendet?
   - [ ] Prüfe `volumenplanung.py`: Wird Backlog-Logik dort verwendet?

2. **Korrektur in production_planner.py:**
   ```python
   # ALT (Zeile 147-150):
   if total_backlog > 0:
       shifts = 3  # Zu aggressiv!
   
   # NEU:
   if total_backlog > 0:
       # Bei Backlog: Nutze maximale benötigte Kapazität (aber nicht zwingend 3)
       shifts_needed = math.ceil(total_demand / capacity_per_shift)
       shifts = min(3, max(1, shifts_needed))  # Begrenzt auf 1-3
   else:
       # Normal: Berechne Schichten basierend auf Bedarf
       shifts_needed = math.ceil(total_demand / capacity_per_shift)
       shifts = min(3, max(1, shifts_needed))
   ```

3. **Korrektur in production_calculations.py:**
   - [ ] Prüfe: Wird dieselbe Logik verwendet?
   - [ ] Stelle sicher: Konsistenz mit `production_planner.py`

4. **Validierung:**
   - [ ] Teste mit Backlog > 0: Werden Schichten korrekt berechnet?
   - [ ] Teste ohne Backlog: Bleibt Logik unverändert?
   - [ ] Prüfe: Konsistenz zwischen statischer und dynamischer Berechnung

**Kritische Aspekte:**
- ⚠️ Änderung beeinflusst gesamte Produktionsplanung
- ⚠️ Muss konsistent zwischen statischer und dynamischer Berechnung sein
- ⚠️ Kommentar "AGGRESSIVE BACKLOG-RECOVERY" sollte angepasst werden

---

## 🟡 PHASE 2: Benutzerfreundlichkeit

### NEU: Abweichungen zwischen Produktion und Fertigproduktelager

**Ziel:** Analysiere und korrigiere Abweichungen (MTB Allrounder: +8).

**Betroffene Dateien:**
- `pages/7_fertigproduktelager.py` - `create_finished_goods_log()`
- `ui/production_calculations.py` - `fertiggestellte PM` Berechnung

**Schritte:**

1. **Warte auf Excel-Berechnungen:**
   - [ ] Excel-Formeln für Fertigproduktelager-Berechnung
   - [ ] Wie wird `Lagerzugang` aus `fertiggestellte PM` berechnet?
   - [ ] Wie wird Verteilung auf Märkte berechnet?

2. **Analyse:**
   - [ ] Prüfe: Rundungsfehler in Verteilungslogik (PRODUCT_SALES_SHARES, MARKETS)
   - [ ] Prüfe: Inkonsistenz zwischen `production_logs_cache` und Fertigproduktelager
   - [ ] Prüfe: Carry-Over-Logik

3. **Korrektur:**
   - [ ] Implementiere Korrekturen basierend auf Excel-Formeln

**Kritische Aspekte:**
- ⚠️ Benötigt Excel-Berechnungen für vollständige Analyse
- ⚠️ Rundungsfehler könnten akzeptabel sein (abhängig von Excel-Logik)

---

### To-Do 1: SCOR-Metriken verschieben/umstrukturieren

**Ziel:** SCOR-Metriken von App-Page nach Reporting verschieben, App-Page mit Dashboard füllen.

**Betroffene Dateien:**
- `app.py` - SCOR-Metriken entfernen, Dashboard hinzufügen
- `pages/1_reporting.py` - SCOR-Metriken hinzufügen

**Schritte:**

1. **Analyse:**
   - [ ] Prüfe: Welche SCOR-Metriken sind in `app.py`?
   - [ ] Prüfe: Welche Metriken sind bereits in `pages/1_reporting.py`?
   - [ ] Entscheide: Welche Metriken sollen ins Dashboard?

2. **Dashboard auf App-Page erstellen:**
   - [ ] Service Level (aus `kpis` oder `results_df`)
   - [ ] Aktueller Backlog (aus `production_logs_cache` oder `production_logs`)
   - [ ] Materialbestand (aus `material_inventory_data`)
   - [ ] Aktive Szenarien (aus `scenario_manager`)
   - [ ] Status-Anzeige (z.B. "Alles im grünen Bereich" / "Achtung: Backlog vorhanden")

3. **SCOR-Metriken nach Reporting verschieben:**
   - [ ] Kopiere Code aus `app.py` nach `pages/1_reporting.py`
   - [ ] Erstelle neuen Tab oder Abschnitt "SCOR-Metriken"
   - [ ] Entferne Code aus `app.py`

4. **Validierung:**
   - [ ] Prüfe: Dashboard zeigt korrekte Werte?
   - [ ] Prüfe: SCOR-Metriken funktionieren in Reporting?
   - [ ] Prüfe: App-Page ist übersichtlicher?

**Kritische Aspekte:**
- ⚠️ Dashboard sollte wichtige KPIs auf einen Blick zeigen
- ⚠️ SCOR-Metriken sollten vollständig sein (oder klar als "teilweise" markiert)
- ⚠️ Rückwärtskompatibilität: Bestehende Links/Bookmarks könnten betroffen sein

---

### To-Do 4: Spalten in Produktion entfernen

**Ziel:** Entferne Spalten "Rahmen", "Gabel" und "Materialien vollständig?" aus Produktionstabelle.

**Betroffene Dateien:**
- `pages/6_produktion.py` - `column_order` (Zeile 133-146)
- `ui/production_calculations.py` - Optional: Spalten aus DataFrame entfernen

**Schritte:**

1. **Prüfe Verwendung:**
   - [ ] Suche nach Verwendung von "Rahmen" Spalten
   - [ ] Suche nach Verwendung von "Gabel" Spalten
   - [ ] Suche nach Verwendung von "Materialien vollständig"
   - [ ] Stelle sicher: Keine anderen Seiten verwenden diese Spalten

2. **Entferne aus column_order:**
   ```python
   # In pages/6_produktion.py, Zeile 133-146:
   # Entferne:
   # - frame_name (Rahmen)
   # - fork_name (Gabel)
   # - 'Materialien vollständig?'
   ```

3. **Optional - Entferne aus production_logs:**
   - [ ] Entscheide: Spalten aus DataFrame entfernen oder nur nicht anzeigen?
   - [ ] Empfehlung: Behalte sie, aber zeige sie nicht an (für andere Zwecke)

4. **Validierung:**
   - [ ] Prüfe: Tabelle zeigt keine Rahmen/Gabel-Spalten mehr?
   - [ ] Prüfe: "Materialien vollständig?" ist entfernt?
   - [ ] Prüfe: Andere Seiten funktionieren noch?

**Kritische Aspekte:**
- ⚠️ Andere Seiten könnten diese Spalten verwenden (prüfen!)
- ⚠️ Daten können bleiben, nur UI-Anzeige wird entfernt

---

### To-Do 5: Farbliche Markierungen in Inbound

**Ziel:** Füge farbliche Markierungen für Wochenende/Feiertage in Inbound-Tabelle hinzu (konsistent mit anderen Seiten).

**Betroffene Dateien:**
- `pages/4_inbound.py` - Styling hinzufügen

**Schritte:**

1. **Prüfe aktuelle Logik:**
   - [ ] Prüfe: Werden `Is_Weekend` und `Is_Holiday` bereits berechnet?
   - [ ] Prüfe: Werden sie aus DataFrame entfernt (Zeile 124-127)?

2. **Kopiere Styling-Logik:**
   - [ ] Kopiere aus `pages/3_lieferant_china.py`:
     - Farblegende oben rechts
     - `style_row()` Funktion
     - Wochenende: `#ffebee` (rot)
     - Feiertag: `#c8e6c9` (grün)

3. **Implementierung:**
   ```python
   # In pages/4_inbound.py:
   # - Füge Farblegende hinzu
   # - Füge style_row() Funktion hinzu
   # - Wende Styling auf DataFrame an
   ```

4. **Entscheidung Feiertage:**
   - [ ] Option A: Nur Wochenenden markieren
   - [ ] Option B: Wochenenden + Feiertage markieren
   - [ ] Empfehlung: Option B (konsistent mit anderen Seiten)

5. **Validierung:**
   - [ ] Prüfe: Wochenenden sind rot markiert?
   - [ ] Prüfe: Feiertage sind grün markiert?
   - [ ] Prüfe: Konsistenz mit anderen Seiten?

**Kritische Aspekte:**
- ⚠️ Konsistenz mit anderen Seiten (Lieferant China, Materiallager, Produktion)
- ⚠️ Feiertage könnten unterschiedlich behandelt werden (Deutschland vs. China)

---

## 🟢 PHASE 3: Erweiterungen

### To-Do 7: Marketing für einzelne Produkte

**Ziel:** Erweitere `MarketingCampaignScenario` um `affected_products` Liste.

**Betroffene Dateien:**
- `models/scenarios.py` - `MarketingCampaignScenario` Klasse
- `ui/scenario_sidebar.py` - UI für Szenario-Erstellung
- `ui/volume_planning_utils.py` - `scenario_fingerprint` (Cache-Key)
- `simulation/simulator.py` - Marketing-Add-ons Berechnung

**Schritte:**

1. **Erweitere MarketingCampaignScenario:**
   ```python
   # In models/scenarios.py:
   class MarketingCampaignScenario:
       def __init__(self, ..., affected_products: List[str] = None):
           # affected_products: Liste von Produktnamen
           # Wenn None: Alle Produkte (Rückwärtskompatibilität)
           self.affected_products = affected_products or list(MasterData.BOM.keys())
   ```

2. **Passe Berechnung an:**
   ```python
   # In simulation/simulator.py, Zeile 258-267:
   for scenario in marketing_scenarios:
       factor = scenario.demand_increase_factor
       affected_products = scenario.affected_products  # NEU
       for product in affected_products:  # GEÄNDERT
           base_float = base_daily_floats.get(product, 0.0)
           add_on = base_float * (factor - 1.0)
           marketing_add_ons[product] += add_on
   ```

3. **Passe UI an:**
   ```python
   # In ui/scenario_sidebar.py:
   # Füge Multi-Select für Produkte hinzu:
   affected_products = st.multiselect(
       "Betroffene Produkte",
       options=list(MasterData.BOM.keys()),
       default=list(MasterData.BOM.keys()),  # Alle als Standard
       key=f"marketing_products_global{key_suffix}"
   )
   ```

4. **Passe Cache-Key an:**
   ```python
   # In ui/volume_planning_utils.py, _scenario_fingerprint():
   if isinstance(s, MarketingCampaignScenario):
       extra = (
           getattr(s, "demand_increase_factor", None),
           tuple(sorted(getattr(s, "affected_products", [])))  # NEU
       )
   ```

5. **Validierung:**
   - [ ] Teste: Marketing nur für ein Produkt
   - [ ] Teste: Marketing für mehrere Produkte
   - [ ] Teste: Rückwärtskompatibilität (bestehende Szenarien)
   - [ ] Prüfe: Cache wird korrekt invalidiert?

**Kritische Aspekte:**
- ⚠️ Rückwärtskompatibilität: Bestehende Szenarien müssen weiter funktionieren
- ⚠️ Cache-Invalidierung: `scenario_fingerprint` muss erweitert werden
- ⚠️ Default-Wert: Alle Produkte (für Rückwärtskompatibilität)

---

### To-Do 8: Nachfrage-Faktor in Prozent

**Ziel:** Ändere Eingabe von Faktor (1.0-3.0) zu Prozent (0%-100%).

**Betroffene Dateien:**
- `ui/scenario_sidebar.py` - UI
- `models/scenarios.py` - Optional: Interne Speicherung (kann Faktor bleiben)

**Schritte:**

1. **Entscheidung:**
   - [ ] Option A: Prozent-basiert (0-100%)
   - [ ] Option B: Beide Optionen (Faktor oder Prozent)
   - [ ] Empfehlung: Option A (intuitiver)

2. **UI-Änderung:**
   ```python
   # In ui/scenario_sidebar.py:
   demand_increase_percent = st.slider(
       "Nachfrage-Erhöhung (%)",
       0, 100, 50, 5,  # 0% bis 100%, Standard 50%, Schritt 5%
       key=f"marketing_percent_global{key_suffix}"
   )
   # Konvertiere zu Faktor:
   demand_factor = 1.0 + (demand_increase_percent / 100.0)
   ```

3. **Interne Speicherung:**
   - [ ] Entscheide: Faktor oder Prozent intern speichern?
   - [ ] Empfehlung: Faktor (keine Änderung in `models/scenarios.py` nötig)

4. **Validierung:**
   - [ ] Teste: 50% = Faktor 1.5?
   - [ ] Teste: 100% = Faktor 2.0?
   - [ ] Prüfe: UI ist intuitiver?

**Kritische Aspekte:**
- ⚠️ Rückwärtskompatibilität: Bestehende Szenarien verwenden Faktor
- ⚠️ Konvertierung: Prozent → Faktor: `factor = 1.0 + (percent / 100.0)`
- ⚠️ Interne Speicherung kann Faktor bleiben (nur UI ändert sich)

---

### To-Do 9: Andere Szenarien implementieren

**Ziel:** Vollständige Implementierung von `WarehouseDamageScenario`, `SupplierBreakdownScenario`, `DeliveryProblemScenario`.

**Betroffene Dateien:**
- `models/scenarios.py` - Szenario-Klassen
- `ui/scenario_sidebar.py` - UI
- `ui/volume_planning_utils.py` - `scenario_fingerprint`
- `simulation/simulator.py` - Szenario-Verarbeitung
- `simulation/china_transport.py` - Transport-Szenarien

**Reihenfolge:**
1. WarehouseDamageScenario (einfachste)
2. SupplierBreakdownScenario (mittel)
3. DeliveryProblemScenario (komplexeste)

**Schritte für jedes Szenario:**

1. **Klasse prüfen/erweitern:**
   - [ ] Prüfe: Ist Klasse vollständig implementiert?
   - [ ] Prüfe: Werden alle Parameter korrekt verwendet?

2. **UI hinzufügen:**
   - [ ] Füge UI in `scenario_sidebar.py` hinzu
   - [ ] Stelle sicher: Alle Parameter sind editierbar

3. **Cache-Key erweitern:**
   - [ ] Erweitere `scenario_fingerprint` in `volume_planning_utils.py`
   - [ ] Stelle sicher: Alle Parameter sind im Fingerprint

4. **Verarbeitung implementieren:**
   - [ ] Implementiere Verarbeitung im Simulator
   - [ ] Stelle sicher: Sichtbarkeit in betroffenen Seiten

5. **Validierung:**
   - [ ] Teste: Szenario aktivieren/deaktivieren
   - [ ] Teste: Parameter ändern
   - [ ] Prüfe: Cache wird invalidiert?
   - [ ] Prüfe: Sichtbarkeit in betroffenen Seiten?

**Kritische Aspekte:**
- ⚠️ Cache-Invalidierung: Alle Szenarien müssen `scenario_fingerprint` beeinflussen
- ⚠️ Konsistenz: Szenarien müssen in allen betroffenen Seiten sichtbar sein
- ⚠️ Rückwärtskompatibilität: Bestehende Szenarien müssen weiter funktionieren

---

## 🔄 Abhängigkeiten und Reihenfolge

### Kritische Abhängigkeiten:

1. **To-Do 2 & 3:** Beide betreffen Inbound-Verfügbarkeit → zusammen bearbeiten
2. **To-Do 6:** Muss vor To-Do 7 (Marketing) bearbeitet werden (könnte Backlog beeinflussen)
3. **To-Do 7 & 8:** Beide betreffen Marketing → zusammen bearbeiten
4. **To-Do 9:** Kann parallel zu anderen bearbeitet werden

### Empfohlene Reihenfolge:

**Sprint 1 (Kritisch):**
1. **NEU:** Bestelleingang an Feiertagen (sofort fixen)
2. **NEU:** Materiallager Wochenende (bereits dokumentiert, sofort fixen)
3. **NEU:** Mengenabweichungen analysieren (nach Excel-Berechnungen)
4. To-Do 2: Inbound-Tage prüfen
5. To-Do 3: Material am Wochenende
6. To-Do 6: Schichtenplanung bei Backlog

**Sprint 2 (Benutzerfreundlichkeit):**
4. **NEU:** Abweichungen Produktion/Fertigproduktelager (nach Excel-Berechnungen)
5. To-Do 1: SCOR-Metriken verschieben
6. To-Do 4: Spalten entfernen
7. To-Do 5: Farbliche Markierungen

**Sprint 3 (Erweiterungen):**
7. To-Do 7: Marketing für einzelne Produkte
8. To-Do 8: Nachfrage-Faktor in Prozent
9. To-Do 9: Andere Szenarien implementieren

---

## ⚠️ Kritische Aspekte für alle To-Do's

### Cache-Management

**⚠️ KRITISCH:**
- Alle Änderungen, die Szenarien beeinflussen, müssen `scenario_fingerprint` erweitern
- Cache-Invalidierung muss getestet werden
- `volume_planning_cache_key` muss aktualisiert werden

### Datenkonsistenz

**⚠️ KRITISCH:**
- Statische Daten (`results_df`, `production_logs`) vs. dynamische Daten (`production_logs_cache`)
- Stelle sicher, dass dynamische Berechnungen konsistent sind
- Teste mit Marketingaktionen aktiviert/deaktiviert

### Rückwärtskompatibilität

**⚠️ WICHTIG:**
- Bestehende Szenarien müssen weiter funktionieren
- Default-Werte für neue Parameter
- Migration von alten zu neuen Formaten (falls nötig)

### Testing

**Empfohlene Test-Szenarien:**
1. Marketingaktion aktivieren/deaktivieren
2. Backlog > 0 prüfen (Schichtenplanung)
3. Material am Wochenende ankommend
4. Alle Szenarien einzeln testen
5. Kombinationen von Szenarien testen

---

## 📝 Notizen

- **Pull erfolgreich:** Commit von 13:35:25 heute
- **Dokumentation vorhanden:** PAGES_DOKUMENTATION.md, SIMULATION_DOKUMENTATION.md, UI_DOKUMENTATION.md, CACHING_DOKUMENTATION.md
- **Basis funktioniert:** Kollege hat viel funktionierenden Code implementiert
- **Caching-System:** Wichtig für Performance, muss bei Änderungen berücksichtigt werden
- **Neue Probleme identifiziert:** Siehe `PROBLEME_IDENTIFIZIERT.md`
- **Excel-Berechnungen benötigt:** Für vollständige Analyse der Mengenabweichungen

---

## ✅ Nächste Schritte

1. **Sofort starten:** Phase 1 (Kritische Datenkonsistenz-Fixes)
2. **Danach:** Phase 2 (Benutzerfreundlichkeit)
3. **Zum Schluss:** Phase 3 (Erweiterungen)

**Empfehlung:** Beginne mit To-Do 2 & 3 zusammen (beide betreffen Inbound-Verfügbarkeit).
