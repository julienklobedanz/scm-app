# Arbeitsplan - Inkrementelle Umsetzung der ausstehenden Arbeitspakete

**Erstellt:** 2026-01-22  
**Basis:** `DATENFLUSS_GESAMTUEBERSICHT.md`, `OFFENE_ARBEITSPAKETE.md`, `WARENBESTAND_PROBLEM_ANALYSE.md`  
**Ziel:** Systematische, testbare und dokumentierte Umsetzung aller ausstehenden Arbeitspakete

---

## 📊 Übersicht der ausstehenden Arbeitspakete

### 🔴 KRITISCH (Höchste Priorität)
1. **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️
   - Problem: Zu hoher Bestandsaufbau (4177 Fizik Tundra Sättel bleiben)
   - Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
   - **Dateien:** `pages/3_lieferant_china.py`, `simulation/china_transport.py`

### 🟡 MITTEL (Funktionalität)
2. **Globale Konfigurationsparameter funktional machen**
   - Problem: Parameter sind editierbar, werden aber nicht in Simulation verwendet
   - **Dateien:** `pages/8_stammdaten.py`, `ui/volume_planning_utils.py`, `simulation/simulator.py`, `config/master_data.py`

3. **AP 15-18: Alle Szenarien implementieren**
   - AP 15: Marketingaktion (Produktauswahl, prozentualer Faktor)
   - AP 16: Wasserschaden im Lager
   - AP 17: Maschinenausfall beim Lieferanten
   - AP 18: Lieferprobleme beim Lieferanten
   - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`, `simulation/simulator.py`

---

## 🎯 Phase 1: AP 12 - Warenbestandslogik korrigieren (KRITISCH)

### Problem-Analyse (aus `WARENBESTAND_PROBLEM_ANALYSE.md`)
- **Root Cause:** Inkonsistenz zwischen Pool-Logik und Bestandslogik
- Pool-Logik plant Versandmengen basierend auf täglicher Produktion + Carry-Over
- Bestandslogik begrenzt Versand durch `current_stock - cumulative_shipped`
- **Ergebnis:** Geplante Versandmenge > Verfügbarer Bestand → Rest bleibt im Bestand

### Lösung (Empfohlen aus Analyse)
Vereinfachte Bestandslogik ohne `cumulative_shipped`:
```python
# WARENBESTAND: Vorheriger Bestand + Produziert
current_stock = previous_stock + production_qty

# WARENAUSGANG: Min(Geplante Versandmenge, Verfügbarer Bestand)
planned_shipment_qty = shipment_results[day_idx]
shipment_qty = min(planned_shipment_qty, current_stock)

# Aktualisiere Warenbestand nach Versand
current_stock = current_stock - shipment_qty
previous_stock = current_stock
```

### Umsetzungsschritte

#### Schritt 1.1: Code-Analyse und Verständnis
- [ ] `simulation/china_transport.py` Zeilen 747-784 genau analysieren
- [ ] Pool-Logik (Zeilen 671-724) verstehen
- [ ] Bestandslogik (Zeilen 747-784) verstehen
- [ ] `cumulative_shipped`-Verwendung dokumentieren

**Test:** Code-Review, keine Änderungen

#### Schritt 1.2: Fix implementieren
- [ ] Vereinfachte Bestandslogik implementieren (ohne `cumulative_shipped`)
- [ ] Code-Kommentare hinzufügen
- [ ] Linter-Fehler beheben

**Test:** 
- [ ] Linter-Check (`read_lints`)
- [ ] Code-Review

#### Schritt 1.3: Validierung
- [ ] Simulation ausführen
- [ ] Warenbestand (Ende) für alle Satteltypen prüfen (sollte = 0 oder erwarteter Wert)
- [ ] Summe Warenausgang = Summe Produktionsmenge (oder erwarteter Wert nach Verlusten)
- [ ] Vergleich: Warenausgang (Lieferant China) = Menge Gesamt (Inbound)

**Test:** 
- [ ] Manuelle Prüfung in Streamlit
- [ ] Dokumentation der Ergebnisse

#### Schritt 1.4: Dokumentation aktualisieren
- [ ] `WARENBESTAND_PROBLEM_ANALYSE.md` aktualisieren (Lösung dokumentieren)
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 12 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren
- [ ] `ARBEITSPAKETE_STATUS.md` aktualisieren

**Test:** Dokumentation prüfen

---

## 🎯 Phase 2: Globale Konfigurationsparameter funktional machen

### Problem-Analyse
- Parameter sind in `st.session_state.editable_*` editierbar
- Aber: Simulation verwendet immer noch `MasterData.*` direkt
- **Ergebnis:** Änderungen haben keine Auswirkung

### Lösung
1. Helper-Funktion erstellen: `get_master_data_for_simulation()`
2. Diese Funktion liest aus `st.session_state.editable_*` (wenn vorhanden), sonst Fallback auf `MasterData.*`
3. Alle Stellen, die `MasterData.*` verwenden, auf Helper-Funktion umstellen

### Umsetzungsschritte

#### Schritt 2.1: Helper-Funktion erstellen
- [ ] Neue Datei: `config/dynamic_master_data.py`
- [ ] Funktion: `get_master_data_for_simulation()` implementieren
- [ ] Liest aus `st.session_state.editable_*` (wenn vorhanden)
- [ ] Fallback auf `MasterData.*` (wenn nicht vorhanden)

**Test:**
- [ ] Unit-Tests (falls vorhanden)
- [ ] Linter-Check

#### Schritt 2.2: Volumenplanung umstellen
- [ ] `ui/volume_planning_utils.py` umstellen
- [ ] `calculate_volume_planning_demand()` verwendet Helper-Funktion
- [ ] Test: Volumenplanung mit geänderten Parametern

**Test:**
- [ ] Manuelle Prüfung in Streamlit
- [ ] Ändere `Gesamtvolumen` → Prüfe ob Volumenplanung sich ändert

#### Schritt 2.3: Simulator umstellen
- [ ] `simulation/simulator.py` umstellen
- [ ] `create_simulator()` verwendet Helper-Funktion
- [ ] Test: Simulation mit geänderten Parametern

**Test:**
- [ ] Manuelle Prüfung in Streamlit
- [ ] Ändere `Kapazität pro Stunde` → Prüfe ob Produktion sich ändert

#### Schritt 2.4: Weitere Stellen umstellen
- [ ] `simulation/demand_calculator.py` (falls verwendet)
- [ ] `simulation/production_planner.py` (falls verwendet)
- [ ] Alle anderen Stellen, die `MasterData.*` verwenden

**Test:**
- [ ] Linter-Check
- [ ] Manuelle Prüfung in Streamlit

#### Schritt 2.5: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren
- [ ] `ARCHITEKTUR_DATENFLUSS_DETAILLIERT.md` aktualisieren (falls nötig)
- [ ] Neue Datei: `GLOBALE_KONFIGURATION_ANLEITUNG.md` (optional)

**Test:** Dokumentation prüfen

---

## 🎯 Phase 3: Szenarien implementieren

### Grundprinzipien (aus `DATENFLUSS_GESAMTUEBERSICHT.md`)
1. **Single Source of Truth:** Szenarien werden zentral angewendet
2. **Automatische Weitergabe:** Szenarien werden weitergegeben (nicht überschrieben)
3. **Konsistenz:** Alle Komponenten sehen gleiche Daten

### AP 15: Marketingaktion

#### Schritt 3.1.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Produktauswahl hinzufügen
- [ ] `ui/scenario_sidebar.py`: Prozentualer Faktor (0-100%) statt Faktor (1.0-2.0)
- [ ] UI-Test: Marketingaktion kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.1.2: Datenfluss prüfen
- [ ] Prüfe: `calculate_volume_planning_demand()` verwendet Marketing-Szenarien ✅ (bereits implementiert)
- [ ] Prüfe: `daily_demands_actual` enthält Marketing-Add-ons ✅ (bereits implementiert)
- [ ] Test: Marketingaktion aktivieren → Prüfe Volumenplanung

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.1.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 15 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 16: Wasserschaden im Lager

#### Schritt 3.2.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Konkretes Lager benennen (z.B. "Materiallager Dortmund")
- [ ] `ui/scenario_sidebar.py`: Komponente auswählbar (Sättel, Frames, etc.)
- [ ] `ui/scenario_sidebar.py`: Verlust-Prozent (0-100%)
- [ ] UI-Test: Wasserschaden kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.2.2: Implementierung
- [ ] `simulation/simulator.py`: Wasserschaden anwenden (bereits teilweise implementiert, Zeilen 202-207)
- [ ] `pages/5_materiallager.py`: Wasserschaden berücksichtigen (wenn verfügbar)
- [ ] Test: Wasserschaden aktivieren → Prüfe Materiallager-Bestände

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.2.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 16 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 17: Maschinenausfall beim Lieferanten

#### Schritt 3.3.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Betroffene Komponente auswählbar (Sättel, Frames, etc.)
- [ ] `ui/scenario_sidebar.py`: Zeitraum (Start-Tag, End-Tag)
- [ ] UI-Test: Maschinenausfall kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.3.2: Implementierung
- [ ] `simulation/china_transport.py`: `place_order()` prüft `SupplierBreakdownScenario`
- [ ] `simulation/china_transport.py`: Bestellungen werden blockiert (wenn Szenario aktiv)
- [ ] Test: Maschinenausfall aktivieren → Prüfe Lieferant China (keine neuen Bestellungen)

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.3.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 17 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 18: Lieferprobleme beim Lieferanten

#### Schritt 3.4.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Blauer Hinweis "Betroffene Komponente" entfernen
- [ ] `ui/scenario_sidebar.py`: Warenverlust-Konfiguration überdenken (ganz oder gar nicht: 0% oder 100%)
- [ ] `ui/scenario_sidebar.py`: Verspätung (Tage)
- [ ] UI-Test: Lieferprobleme können konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.4.2: Implementierung prüfen
- [ ] `simulation/china_transport.py`: `process_shipments()` verwendet bereits `DeliveryProblemScenario` ✅ (bereits implementiert, Zeilen 182-194)
- [ ] Prüfe: `actual_quantity` wird korrekt reduziert ✅ (bereits implementiert)
- [ ] Prüfe: Verspätung wird korrekt angewendet ✅ (bereits implementiert)
- [ ] Test: Lieferprobleme aktivieren → Prüfe Inbound (Verluste, Verspätungen)

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.4.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 18 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

---

## 📋 Test-Strategie (nach jeder Phase)

### Automatische Tests
- [ ] Linter-Check (`read_lints` für alle geänderten Dateien)
- [ ] Code-Review (selbst)

### Manuelle Tests
- [ ] Simulation läuft ohne Fehler
- [ ] Keine nicht abbaubaren Bestände (nach AP 12)
- [ ] Alle Tabellen zeigen korrekte Werte
- [ ] Farbmarkierungen funktionieren korrekt
- [ ] Summenzeilen sind korrekt
- [ ] Keine Performance-Regressionen

### Szenarien-Tests (nach Phase 3)
- [ ] Marketingaktion: Volumenplanung zeigt erhöhte Nachfrage
- [ ] Wasserschaden: Materiallager zeigt reduzierte Bestände
- [ ] Maschinenausfall: Lieferant China zeigt keine neuen Bestellungen
- [ ] Lieferprobleme: Inbound zeigt Verluste/Verspätungen

---

## 📝 Dokumentations-Strategie

### Automatische Dokumentations-Updates
Nach jeder Änderung werden folgende Dateien automatisch aktualisiert:

1. **`AENDERUNGEN_ARBEITSPAKETE.md`**
   - Status der Arbeitspakete aktualisieren
   - Änderungsprotokoll erweitern

2. **`OFFENE_ARBEITSPAKETE.md`**
   - Abgeschlossene Arbeitspakete entfernen
   - Status aktualisieren

3. **`ARBEITSPAKETE_STATUS.md`**
   - Status nach Pages aktualisieren
   - Abgeschlossene Arbeitspakete markieren

4. **Relevante `.md`-Dateien**
   - `WARENBESTAND_PROBLEM_ANALYSE.md` (nach AP 12)
   - `DATENFLUSS_GESAMTUEBERSICHT.md` (falls Datenfluss geändert)
   - `ARCHITEKTUR_DATENFLUSS_DETAILLIERT.md` (falls Architektur geändert)

### Dokumentations-Template
```markdown
### [Datum] - [Phase X] - [Schritt Y.Z]

**Änderungen:**
- [ ] Beschreibung der Änderung
- [ ] Dateien: `datei1.py`, `datei2.py`
- [ ] Getestet: [Beschreibung der Tests]

**Status:** ✅ Abgeschlossen / ⏳ In Bearbeitung / ❌ Fehler
```

---

## 🎯 Priorisierung und Reihenfolge

### Empfohlene Reihenfolge
1. **Phase 1: AP 12** (KRITISCH - muss zuerst behoben werden)
2. **Phase 2: Globale Konfiguration** (Grundlage für Szenarien)
3. **Phase 3: Szenarien** (können parallel oder nacheinander bearbeitet werden)

### Warum diese Reihenfolge?
- **AP 12** ist kritisch und blockiert möglicherweise andere Tests
- **Globale Konfiguration** ist Grundlage für Szenarien (Marketingaktion benötigt z.B. `yearly_volume`)
- **Szenarien** können unabhängig voneinander implementiert werden

---

## ⚠️ Wichtige Hinweise

### Datenfluss beachten
- **WICHTIG:** Alle Änderungen müssen den Datenfluss aus `DATENFLUSS_GESAMTUEBERSICHT.md` beachten
- **WICHTIG:** Single Source of Truth-Prinzip einhalten
- **WICHTIG:** Szenarien werden zentral angewendet und automatisch weitergegeben

### Testing
- **WICHTIG:** Nach jeder Phase testen (nicht erst am Ende)
- **WICHTIG:** Dokumentation nach jeder Phase aktualisieren
- **WICHTIG:** Bei Fehlern: Rollback und Analyse

### Kommunikation
- **WICHTIG:** Bei kritischen Änderungen: Zwischenstand mitteilen
- **WICHTIG:** Bei Fragen: Dokumentation prüfen (`DATENFLUSS_GESAMTUEBERSICHT.md`)

---

## 📊 Fortschritts-Tracking

### Phase 1: AP 12
- [ ] Schritt 1.1: Code-Analyse
- [ ] Schritt 1.2: Fix implementieren
- [ ] Schritt 1.3: Validierung
- [ ] Schritt 1.4: Dokumentation

### Phase 2: Globale Konfiguration
- [ ] Schritt 2.1: Helper-Funktion
- [ ] Schritt 2.2: Volumenplanung
- [ ] Schritt 2.3: Simulator
- [ ] Schritt 2.4: Weitere Stellen
- [ ] Schritt 2.5: Dokumentation

### Phase 3: Szenarien
- [ ] AP 15: Marketingaktion
- [ ] AP 16: Wasserschaden
- [ ] AP 17: Maschinenausfall
- [ ] AP 18: Lieferprobleme

---

**Nächster Schritt:** Beginne mit Phase 1, Schritt 1.1 (Code-Analyse für AP 12)


**Erstellt:** 2026-01-22  
**Basis:** `DATENFLUSS_GESAMTUEBERSICHT.md`, `OFFENE_ARBEITSPAKETE.md`, `WARENBESTAND_PROBLEM_ANALYSE.md`  
**Ziel:** Systematische, testbare und dokumentierte Umsetzung aller ausstehenden Arbeitspakete

---

## 📊 Übersicht der ausstehenden Arbeitspakete

### 🔴 KRITISCH (Höchste Priorität)
1. **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️
   - Problem: Zu hoher Bestandsaufbau (4177 Fizik Tundra Sättel bleiben)
   - Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
   - **Dateien:** `pages/3_lieferant_china.py`, `simulation/china_transport.py`

### 🟡 MITTEL (Funktionalität)
2. **Globale Konfigurationsparameter funktional machen**
   - Problem: Parameter sind editierbar, werden aber nicht in Simulation verwendet
   - **Dateien:** `pages/8_stammdaten.py`, `ui/volume_planning_utils.py`, `simulation/simulator.py`, `config/master_data.py`

3. **AP 15-18: Alle Szenarien implementieren**
   - AP 15: Marketingaktion (Produktauswahl, prozentualer Faktor)
   - AP 16: Wasserschaden im Lager
   - AP 17: Maschinenausfall beim Lieferanten
   - AP 18: Lieferprobleme beim Lieferanten
   - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`, `simulation/simulator.py`

---

## 🎯 Phase 1: AP 12 - Warenbestandslogik korrigieren (KRITISCH)

### Problem-Analyse (aus `WARENBESTAND_PROBLEM_ANALYSE.md`)
- **Root Cause:** Inkonsistenz zwischen Pool-Logik und Bestandslogik
- Pool-Logik plant Versandmengen basierend auf täglicher Produktion + Carry-Over
- Bestandslogik begrenzt Versand durch `current_stock - cumulative_shipped`
- **Ergebnis:** Geplante Versandmenge > Verfügbarer Bestand → Rest bleibt im Bestand

### Lösung (Empfohlen aus Analyse)
Vereinfachte Bestandslogik ohne `cumulative_shipped`:
```python
# WARENBESTAND: Vorheriger Bestand + Produziert
current_stock = previous_stock + production_qty

# WARENAUSGANG: Min(Geplante Versandmenge, Verfügbarer Bestand)
planned_shipment_qty = shipment_results[day_idx]
shipment_qty = min(planned_shipment_qty, current_stock)

# Aktualisiere Warenbestand nach Versand
current_stock = current_stock - shipment_qty
previous_stock = current_stock
```

### Umsetzungsschritte

#### Schritt 1.1: Code-Analyse und Verständnis
- [ ] `simulation/china_transport.py` Zeilen 747-784 genau analysieren
- [ ] Pool-Logik (Zeilen 671-724) verstehen
- [ ] Bestandslogik (Zeilen 747-784) verstehen
- [ ] `cumulative_shipped`-Verwendung dokumentieren

**Test:** Code-Review, keine Änderungen

#### Schritt 1.2: Fix implementieren
- [ ] Vereinfachte Bestandslogik implementieren (ohne `cumulative_shipped`)
- [ ] Code-Kommentare hinzufügen
- [ ] Linter-Fehler beheben

**Test:** 
- [ ] Linter-Check (`read_lints`)
- [ ] Code-Review

#### Schritt 1.3: Validierung
- [ ] Simulation ausführen
- [ ] Warenbestand (Ende) für alle Satteltypen prüfen (sollte = 0 oder erwarteter Wert)
- [ ] Summe Warenausgang = Summe Produktionsmenge (oder erwarteter Wert nach Verlusten)
- [ ] Vergleich: Warenausgang (Lieferant China) = Menge Gesamt (Inbound)

**Test:** 
- [ ] Manuelle Prüfung in Streamlit
- [ ] Dokumentation der Ergebnisse

#### Schritt 1.4: Dokumentation aktualisieren
- [ ] `WARENBESTAND_PROBLEM_ANALYSE.md` aktualisieren (Lösung dokumentieren)
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 12 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren
- [ ] `ARBEITSPAKETE_STATUS.md` aktualisieren

**Test:** Dokumentation prüfen

---

## 🎯 Phase 2: Globale Konfigurationsparameter funktional machen

### Problem-Analyse
- Parameter sind in `st.session_state.editable_*` editierbar
- Aber: Simulation verwendet immer noch `MasterData.*` direkt
- **Ergebnis:** Änderungen haben keine Auswirkung

### Lösung
1. Helper-Funktion erstellen: `get_master_data_for_simulation()`
2. Diese Funktion liest aus `st.session_state.editable_*` (wenn vorhanden), sonst Fallback auf `MasterData.*`
3. Alle Stellen, die `MasterData.*` verwenden, auf Helper-Funktion umstellen

### Umsetzungsschritte

#### Schritt 2.1: Helper-Funktion erstellen
- [ ] Neue Datei: `config/dynamic_master_data.py`
- [ ] Funktion: `get_master_data_for_simulation()` implementieren
- [ ] Liest aus `st.session_state.editable_*` (wenn vorhanden)
- [ ] Fallback auf `MasterData.*` (wenn nicht vorhanden)

**Test:**
- [ ] Unit-Tests (falls vorhanden)
- [ ] Linter-Check

#### Schritt 2.2: Volumenplanung umstellen
- [ ] `ui/volume_planning_utils.py` umstellen
- [ ] `calculate_volume_planning_demand()` verwendet Helper-Funktion
- [ ] Test: Volumenplanung mit geänderten Parametern

**Test:**
- [ ] Manuelle Prüfung in Streamlit
- [ ] Ändere `Gesamtvolumen` → Prüfe ob Volumenplanung sich ändert

#### Schritt 2.3: Simulator umstellen
- [ ] `simulation/simulator.py` umstellen
- [ ] `create_simulator()` verwendet Helper-Funktion
- [ ] Test: Simulation mit geänderten Parametern

**Test:**
- [ ] Manuelle Prüfung in Streamlit
- [ ] Ändere `Kapazität pro Stunde` → Prüfe ob Produktion sich ändert

#### Schritt 2.4: Weitere Stellen umstellen
- [ ] `simulation/demand_calculator.py` (falls verwendet)
- [ ] `simulation/production_planner.py` (falls verwendet)
- [ ] Alle anderen Stellen, die `MasterData.*` verwenden

**Test:**
- [ ] Linter-Check
- [ ] Manuelle Prüfung in Streamlit

#### Schritt 2.5: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren
- [ ] `ARCHITEKTUR_DATENFLUSS_DETAILLIERT.md` aktualisieren (falls nötig)
- [ ] Neue Datei: `GLOBALE_KONFIGURATION_ANLEITUNG.md` (optional)

**Test:** Dokumentation prüfen

---

## 🎯 Phase 3: Szenarien implementieren

### Grundprinzipien (aus `DATENFLUSS_GESAMTUEBERSICHT.md`)
1. **Single Source of Truth:** Szenarien werden zentral angewendet
2. **Automatische Weitergabe:** Szenarien werden weitergegeben (nicht überschrieben)
3. **Konsistenz:** Alle Komponenten sehen gleiche Daten

### AP 15: Marketingaktion

#### Schritt 3.1.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Produktauswahl hinzufügen
- [ ] `ui/scenario_sidebar.py`: Prozentualer Faktor (0-100%) statt Faktor (1.0-2.0)
- [ ] UI-Test: Marketingaktion kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.1.2: Datenfluss prüfen
- [ ] Prüfe: `calculate_volume_planning_demand()` verwendet Marketing-Szenarien ✅ (bereits implementiert)
- [ ] Prüfe: `daily_demands_actual` enthält Marketing-Add-ons ✅ (bereits implementiert)
- [ ] Test: Marketingaktion aktivieren → Prüfe Volumenplanung

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.1.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 15 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 16: Wasserschaden im Lager

#### Schritt 3.2.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Konkretes Lager benennen (z.B. "Materiallager Dortmund")
- [ ] `ui/scenario_sidebar.py`: Komponente auswählbar (Sättel, Frames, etc.)
- [ ] `ui/scenario_sidebar.py`: Verlust-Prozent (0-100%)
- [ ] UI-Test: Wasserschaden kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.2.2: Implementierung
- [ ] `simulation/simulator.py`: Wasserschaden anwenden (bereits teilweise implementiert, Zeilen 202-207)
- [ ] `pages/5_materiallager.py`: Wasserschaden berücksichtigen (wenn verfügbar)
- [ ] Test: Wasserschaden aktivieren → Prüfe Materiallager-Bestände

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.2.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 16 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 17: Maschinenausfall beim Lieferanten

#### Schritt 3.3.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Betroffene Komponente auswählbar (Sättel, Frames, etc.)
- [ ] `ui/scenario_sidebar.py`: Zeitraum (Start-Tag, End-Tag)
- [ ] UI-Test: Maschinenausfall kann konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.3.2: Implementierung
- [ ] `simulation/china_transport.py`: `place_order()` prüft `SupplierBreakdownScenario`
- [ ] `simulation/china_transport.py`: Bestellungen werden blockiert (wenn Szenario aktiv)
- [ ] Test: Maschinenausfall aktivieren → Prüfe Lieferant China (keine neuen Bestellungen)

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.3.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 17 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

### AP 18: Lieferprobleme beim Lieferanten

#### Schritt 3.4.1: UI erweitern
- [ ] `ui/scenario_sidebar.py`: Blauer Hinweis "Betroffene Komponente" entfernen
- [ ] `ui/scenario_sidebar.py`: Warenverlust-Konfiguration überdenken (ganz oder gar nicht: 0% oder 100%)
- [ ] `ui/scenario_sidebar.py`: Verspätung (Tage)
- [ ] UI-Test: Lieferprobleme können konfiguriert werden

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.4.2: Implementierung prüfen
- [ ] `simulation/china_transport.py`: `process_shipments()` verwendet bereits `DeliveryProblemScenario` ✅ (bereits implementiert, Zeilen 182-194)
- [ ] Prüfe: `actual_quantity` wird korrekt reduziert ✅ (bereits implementiert)
- [ ] Prüfe: Verspätung wird korrekt angewendet ✅ (bereits implementiert)
- [ ] Test: Lieferprobleme aktivieren → Prüfe Inbound (Verluste, Verspätungen)

**Test:** Manuelle Prüfung in Streamlit

#### Schritt 3.4.3: Dokumentation aktualisieren
- [ ] `AENDERUNGEN_ARBEITSPAKETE.md` aktualisieren (AP 18 als abgeschlossen markieren)
- [ ] `OFFENE_ARBEITSPAKETE.md` aktualisieren

**Test:** Dokumentation prüfen

---

## 📋 Test-Strategie (nach jeder Phase)

### Automatische Tests
- [ ] Linter-Check (`read_lints` für alle geänderten Dateien)
- [ ] Code-Review (selbst)

### Manuelle Tests
- [ ] Simulation läuft ohne Fehler
- [ ] Keine nicht abbaubaren Bestände (nach AP 12)
- [ ] Alle Tabellen zeigen korrekte Werte
- [ ] Farbmarkierungen funktionieren korrekt
- [ ] Summenzeilen sind korrekt
- [ ] Keine Performance-Regressionen

### Szenarien-Tests (nach Phase 3)
- [ ] Marketingaktion: Volumenplanung zeigt erhöhte Nachfrage
- [ ] Wasserschaden: Materiallager zeigt reduzierte Bestände
- [ ] Maschinenausfall: Lieferant China zeigt keine neuen Bestellungen
- [ ] Lieferprobleme: Inbound zeigt Verluste/Verspätungen

---

## 📝 Dokumentations-Strategie

### Automatische Dokumentations-Updates
Nach jeder Änderung werden folgende Dateien automatisch aktualisiert:

1. **`AENDERUNGEN_ARBEITSPAKETE.md`**
   - Status der Arbeitspakete aktualisieren
   - Änderungsprotokoll erweitern

2. **`OFFENE_ARBEITSPAKETE.md`**
   - Abgeschlossene Arbeitspakete entfernen
   - Status aktualisieren

3. **`ARBEITSPAKETE_STATUS.md`**
   - Status nach Pages aktualisieren
   - Abgeschlossene Arbeitspakete markieren

4. **Relevante `.md`-Dateien**
   - `WARENBESTAND_PROBLEM_ANALYSE.md` (nach AP 12)
   - `DATENFLUSS_GESAMTUEBERSICHT.md` (falls Datenfluss geändert)
   - `ARCHITEKTUR_DATENFLUSS_DETAILLIERT.md` (falls Architektur geändert)

### Dokumentations-Template
```markdown
### [Datum] - [Phase X] - [Schritt Y.Z]

**Änderungen:**
- [ ] Beschreibung der Änderung
- [ ] Dateien: `datei1.py`, `datei2.py`
- [ ] Getestet: [Beschreibung der Tests]

**Status:** ✅ Abgeschlossen / ⏳ In Bearbeitung / ❌ Fehler
```

---

## 🎯 Priorisierung und Reihenfolge

### Empfohlene Reihenfolge
1. **Phase 1: AP 12** (KRITISCH - muss zuerst behoben werden)
2. **Phase 2: Globale Konfiguration** (Grundlage für Szenarien)
3. **Phase 3: Szenarien** (können parallel oder nacheinander bearbeitet werden)

### Warum diese Reihenfolge?
- **AP 12** ist kritisch und blockiert möglicherweise andere Tests
- **Globale Konfiguration** ist Grundlage für Szenarien (Marketingaktion benötigt z.B. `yearly_volume`)
- **Szenarien** können unabhängig voneinander implementiert werden

---

## ⚠️ Wichtige Hinweise

### Datenfluss beachten
- **WICHTIG:** Alle Änderungen müssen den Datenfluss aus `DATENFLUSS_GESAMTUEBERSICHT.md` beachten
- **WICHTIG:** Single Source of Truth-Prinzip einhalten
- **WICHTIG:** Szenarien werden zentral angewendet und automatisch weitergegeben

### Testing
- **WICHTIG:** Nach jeder Phase testen (nicht erst am Ende)
- **WICHTIG:** Dokumentation nach jeder Phase aktualisieren
- **WICHTIG:** Bei Fehlern: Rollback und Analyse

### Kommunikation
- **WICHTIG:** Bei kritischen Änderungen: Zwischenstand mitteilen
- **WICHTIG:** Bei Fragen: Dokumentation prüfen (`DATENFLUSS_GESAMTUEBERSICHT.md`)

---

## 📊 Fortschritts-Tracking

### Phase 1: AP 12
- [ ] Schritt 1.1: Code-Analyse
- [ ] Schritt 1.2: Fix implementieren
- [ ] Schritt 1.3: Validierung
- [ ] Schritt 1.4: Dokumentation

### Phase 2: Globale Konfiguration
- [ ] Schritt 2.1: Helper-Funktion
- [ ] Schritt 2.2: Volumenplanung
- [ ] Schritt 2.3: Simulator
- [ ] Schritt 2.4: Weitere Stellen
- [ ] Schritt 2.5: Dokumentation

### Phase 3: Szenarien
- [ ] AP 15: Marketingaktion
- [ ] AP 16: Wasserschaden
- [ ] AP 17: Maschinenausfall
- [ ] AP 18: Lieferprobleme

---

**Nächster Schritt:** Beginne mit Phase 1, Schritt 1.1 (Code-Analyse für AP 12)





