# To-Do Liste - Detaillierte Implementierungsanleitung

Diese Dokumentation beschreibt alle offenen To-Do's mit Hintergründen, kritischen Aspekten und Implementierungshinweisen.

---

## 1. SCOR-Metriken auf App-Page: Sinnhaftigkeit hinterfragen

### Aktueller Zustand

**Location:** `app.py` (Hauptseite)

**Was wird angezeigt:**
- Perfect Order Fulfillment (Inbound)
- Source Cycle Time
- Produktionsmetriken

**Problem:**
- SCOR-Metriken sind aufgabenbedingt unvollständig
- Nur Inbound-Metriken sind implementiert
- Outbound-Metriken fehlen komplett
- Weitere SCOR-Level (Plan, Make, Deliver, Return) sind nicht abgedeckt

### Hintergrund

**SCOR-Modell (Supply Chain Operations Reference):**
- Level 1: Plan, Source, Make, Deliver, Return
- Level 2: Prozesskategorien
- Level 3: Detaillierte Prozesse und Metriken

**Aktuelle Implementierung:**
- Nur "Source" (Inbound) ist teilweise implementiert
- "Make" (Produktion) hat nur Basis-Metriken
- "Deliver" (Outbound) fehlt komplett
- "Plan" und "Return" sind nicht implementiert

### Kritische Aspekte

**⚠️ WICHTIG:**
- SCOR-Metriken sind ein Standard-Framework
- Unvollständige Darstellung kann irreführend sein
- Benutzer könnten erwarten, dass alle SCOR-Bereiche abgedeckt sind

**Abhängigkeiten:**
- Inbound-Metriken: `china_transport_manager.transport_status`
- Produktionsmetriken: `production_logs` (statisch) oder `production_logs_cache` (dynamisch)
- Outbound-Metriken: Müssten aus Fertigproduktelager berechnet werden

### Lösungsoptionen

#### Option 1: In Reporting verschieben
**Vorteile:**
- Reporting-Seite ist für Metriken gedacht
- Bessere Gruppierung mit anderen KPIs
- App-Page wird übersichtlicher

**Nachteile:**
- App-Page könnte zu leer werden
- Benutzer müssen zu Reporting navigieren

**Implementierung:**
```python
# In pages/1_reporting.py hinzufügen:
# Neuer Tab oder Abschnitt "SCOR-Metriken"
# Kopiere Code aus app.py
```

#### Option 2: App-Page mit Dashboard füllen
**Vorschlag für App-Page:**
- Übersichtsdashboard mit wichtigsten KPIs
- Links zu detaillierten Seiten
- Aktuelle Status-Anzeige (z.B. "Alles im grünen Bereich" / "Achtung: Backlog vorhanden")

**Implementierung:**
```python
# In app.py:
# - Entferne SCOR-Metriken
# - Füge Dashboard mit:
#   - Service Level (aus Reporting)
#   - Aktueller Backlog (aus Produktion)
#   - Materialbestand (aus Materiallager)
#   - Aktive Szenarien (aus ScenarioManager)
```

### Empfehlung

**Option 1 (In Reporting verschieben) + Option 2 (Dashboard auf App-Page)**

**Begründung:**
- SCOR-Metriken gehören zu Reporting
- App-Page sollte Übersichtsdashboard sein
- Bessere Benutzerführung

---

## 2. Inbound-Tage: Verfügbarkeit im Lager +1 Tag prüfen

### Aktueller Zustand

**Location:** `simulation/china_transport.py`

**Transport-Logik:**
1. Produktion in China: 5 AT (Tag der Bestellung zählt NICHT)
2. LKW zum Hafen (China): 2 AT
3. Warten auf Mittwoch (Schiff fährt nur Mittwochs ab)
4. Schiff: 30 KT (Kalendertage)
5. LKW zum Werk (Deutschland): 2 AT
6. **Wareneingang: +1 Tag zwischen physischer Ankunft und Verfügbarkeit**

**Problem:**
- Kommentar sagt "+1 Tag", aber Logik muss geprüft werden
- `available_day` vs. `arrival_day` muss verifiziert werden

### Hintergrund

**Transport-Zeitpunkte:**
- `order_day`: Tag der Bestellung
- `ship_departure_day`: Tag der Abfahrt vom Hafen
- `arrival_day`: Tag der physischen Ankunft im Lager
- `available_day`: Tag, an dem Ware verfügbar ist (für Produktion)

**Erwartung:**
- `available_day = arrival_day + 1` (wenn arrival_day Arbeitstag)
- `available_day = nächster Arbeitstag` (wenn arrival_day Wochenende/Feiertag)

### Kritische Aspekte

**⚠️ WICHTIG:**
- Diese Logik beeinflusst Materialverfügbarkeit
- Falsche Berechnung führt zu falschen Produktionsplanungen
- Muss konsistent mit `get_daily_arrival_qty()` sein

**Abhängigkeiten:**
- `get_inbound_log_dataframe()` - Berechnet Inbound-Tabelle
- `get_daily_arrival_qty()` - Wird im Simulator verwendet
- `_get_all_stocks_from_inbound_table()` - Wird in Produktion verwendet

### Zu prüfende Stellen

**1. `get_inbound_log_dataframe()` in `china_transport.py`:**
```python
# Prüfe: Wie wird 'Verfügbar im Lager 🇩🇪' berechnet?
# Ist es wirklich available_day oder arrival_day?
```

**2. `get_daily_arrival_qty()` in `china_transport.py`:**
```python
# Prüfe: Verwendet available_day oder arrival_day?
# Muss konsistent mit Inbound-Tabelle sein
```

**3. Simulator verwendet `get_daily_arrival_qty()`:**
```python
# In simulator.py, Zeile 217:
arrived_qty = self.china_transport_manager.get_daily_arrival_qty(day)
# Prüfe: Ist das der richtige Tag?
```

### Implementierung

**Schritt 1: Analyse**
- Prüfe `available_day` Berechnung in `place_order()`
- Prüfe `get_inbound_log_dataframe()` Logik
- Prüfe Konsistenz zwischen beiden Methoden

**Schritt 2: Korrektur (falls nötig)**
- Stelle sicher, dass `available_day = arrival_day + 1` (Arbeitstag)
- Stelle sicher, dass Wochenenden/Feiertage übersprungen werden
- Stelle sicher, dass `get_daily_arrival_qty()` denselben Tag verwendet

**Schritt 3: Validierung**
- Vergleiche Inbound-Tabelle mit Materiallager
- Prüfe, ob Bestand morgens korrekt ist

---

## 3. Material kommt teilweise am Wochenende im Lager an

### Aktueller Zustand

**Problem:**
- Material kann am Wochenende physisch ankommen
- Aber: Verfügbarkeit sollte erst am nächsten Arbeitstag sein

**Erwartung:**
- Physische Ankunft: Kann am Wochenende sein
- Verfügbarkeit: Nur an Arbeitstagen

### Hintergrund

**Transport-Logik:**
- Schiff fährt 30 Kalendertage (nicht Arbeitstage)
- LKW fährt 2 Arbeitstage
- Ankunft kann daher auf Wochenende fallen

**Lager-Logik:**
- Wareneingang wird nur an Arbeitstagen verarbeitet
- Material sollte erst am nächsten Arbeitstag verfügbar sein

### Kritische Aspekte

**⚠️ WICHTIG:**
- `available_day` muss nächster Arbeitstag sein (wenn arrival_day Wochenende)
- `get_daily_arrival_qty()` muss Wochenenden überspringen
- Inbound-Tabelle sollte beide Daten zeigen (Ankunft + Verfügbarkeit)

**Abhängigkeiten:**
- `WorkdayCalculator.is_workday()` - Prüft Arbeitstage
- `available_day` Berechnung in `place_order()`
- `get_inbound_log_dataframe()` - Zeigt beide Daten

### Implementierung

**Schritt 1: Prüfe aktuelle Logik**
```python
# In china_transport.py, place_order():
# Prüfe: Wird available_day korrekt berechnet?
# Prüfe: Werden Wochenenden übersprungen?
```

**Schritt 2: Korrektur (falls nötig)**
```python
# Stelle sicher, dass:
# - arrival_day = physische Ankunft (kann Wochenende sein)
# - available_day = nächster Arbeitstag nach arrival_day
```

**Schritt 3: Inbound-Tabelle anpassen**
```python
# Zeige beide Daten:
# - "Tatsächliche Ankunft LKW 🇩🇪" (kann Wochenende sein)
# - "Verfügbar im Lager 🇩🇪" (immer Arbeitstag)
```

---

## 4. Spalten in Produktion entfernen

### Zu entfernende Spalten

1. **Rahmen** (z.B. "Rahmen Alu", "Rahmen Carbon")
2. **Gabeln** (z.B. "Gabel Alu", "Gabel Carbon")
3. **Materialien vollständig?**

### Aktueller Zustand

**Location:** `pages/6_produktion.py`

**Spalten in Produktionstabelle:**
- Wochentag, Datum
- Schichtanzahl
- Auslastung (%)
- **Rahmen** (z.B. "Rahmen Alu")
- **Sattel** (z.B. "Spark")
- **Gabel** (z.B. "Gabel Alu")
- **Materialien vollständig?**
- geplante PM
- tatsächliche PM
- fertiggestellte PM
- Backlog

### Hintergrund

**Warum entfernen?**

1. **Rahmen:**
   - Rahmen sind unbegrenzt verfügbar (kein Engpass)
   - Zeigen immer gleichen Wert
   - Nicht relevant für Produktionsplanung

2. **Gabeln:**
   - Gabeln sind unbegrenzt verfügbar (kein Engpass)
   - Zeigen immer gleichen Wert
   - Nicht relevant für Produktionsplanung

3. **Materialien vollständig?:**
   - Wird bereits durch Sattel-Bestand implizit angezeigt
   - Wenn Sattel-Bestand = 0, dann Materialien nicht vollständig
   - Redundante Information

### Kritische Aspekte

**⚠️ WICHTIG:**
- Spalten werden in `column_order` definiert (Zeile 133-146)
- Spalten müssen in `production_logs_cache` vorhanden sein
- UI muss angepasst werden, aber Daten können bleiben (für andere Zwecke)

**Abhängigkeiten:**
- `ui/production_calculations.py` - Erstellt `production_logs_cache`
- `simulation/production_planner.py` - Erstellt `production_logs`
- Andere Seiten könnten diese Spalten verwenden (prüfen!)

### Implementierung

**Schritt 1: Prüfe Verwendung**
```python
# Suche nach Verwendung von:
# - "Rahmen" Spalten
# - "Gabel" Spalten
# - "Materialien vollständig"
# Stelle sicher, dass keine anderen Seiten diese verwenden
```

**Schritt 2: Entferne aus column_order**
```python
# In pages/6_produktion.py, Zeile 133-146:
# Entferne:
# - frame_name (Rahmen)
# - fork_name (Gabel)
# - 'Materialien vollständig?'
```

**Schritt 3: Optional - Entferne aus production_logs**
```python
# In ui/production_calculations.py:
# Optional: Entferne Spalten aus DataFrame
# ODER: Behalte sie, aber zeige sie nicht an
```

---

## 5. Inbound-Tabelle: Farbliche Markierungen für Wochenende/Feiertage

### Aktueller Zustand

**Location:** `pages/4_inbound.py`

**Status:**
- Wochenende/Feiertage werden bereits berechnet (`Is_Weekend`, `Is_Holiday`)
- Aber: Keine farbliche Markierung in der Tabelle
- Andere Seiten (z.B. Lieferant China, Materiallager) haben bereits Markierungen

### Hintergrund

**Andere Seiten:**
- `pages/3_lieferant_china.py` - Hat Wochenende/Feiertage-Markierungen
- `pages/5_materiallager.py` - Hat Wochenende/Feiertage-Markierungen
- `pages/6_produktion.py` - Hat Wochenende/Feiertage-Markierungen

**Frage: Sollen Feiertage berücksichtigt werden?**
- **Ja:** Realistischer (Lager arbeitet nicht an Feiertagen)
- **Nein:** Vereinfachung (nur Wochenenden)

### Kritische Aspekte

**⚠️ WICHTIG:**
- Konsistenz mit anderen Seiten
- Feiertage könnten unterschiedlich behandelt werden (Deutschland vs. China)
- Aktuell: Feiertage werden in `WorkdayCalculator` berücksichtigt

**Abhängigkeiten:**
- `WorkdayCalculator.is_workday()` - Berechnet Arbeitstage
- `WorkdayCalculator.is_weekend()` - Berechnet Wochenenden
- `HolidaysConfig` - Feiertage-Konfiguration

### Implementierung

**Schritt 1: Prüfe aktuelle Logik**
```python
# In pages/4_inbound.py:
# Prüfe: Werden Is_Weekend und Is_Holiday bereits berechnet?
# Prüfe: Werden sie aus DataFrame entfernt (Zeile 124-127)?
```

**Schritt 2: Füge Styling hinzu**
```python
# In pages/4_inbound.py:
# Kopiere Styling-Logik aus pages/3_lieferant_china.py
# - Farblegende oben rechts
# - style_row() Funktion
# - Wochenende: #ffebee (rot)
# - Feiertag: #c8e6c9 (grün)
```

**Schritt 3: Entscheidung Feiertage**
```python
# Option A: Nur Wochenenden markieren
# Option B: Wochenenden + Feiertage markieren
# Empfehlung: Option B (konsistent mit anderen Seiten)
```

---

## 6. Schichtenplanung: Bei Backlog > 0 maximale Kapazität

### Aktueller Zustand

**Location:** `simulation/production_planner.py`, Zeile 141-156

**Aktuelle Logik:**
```python
# AGGRESSIVE BACKLOG-RECOVERY: Wenn Backlog vorhanden ist, nutze IMMER MAXIMALE Kapazität (3 Schichten)
if total_backlog > 0:
    shifts = 3  # Maximale Kapazität für Backlog-Aufholung
else:
    # Normal: Berechne Schichten basierend auf Bedarf
    shifts_needed = math.ceil(total_demand / capacity_per_shift)
    shifts = min(3, max(1, shifts_needed))
```

**Problem:**
- Logik ist zu aggressiv
- Fährt IMMER 3 Schichten, wenn Backlog > 0
- Sollte nur bei Backlog > 0 maximale Kapazität nutzen (aber nicht zwingend 3 Schichten)

### Hintergrund

**Schichtenplanung:**
- 1 Schicht = 8 Stunden × 130 Einheiten/Stunde = 1040 Einheiten
- 2 Schichten = 2080 Einheiten
- 3 Schichten = 3120 Einheiten (Maximum)

**Aktuelle Strategie:**
- Backlog vorhanden → IMMER 3 Schichten
- Kein Backlog → Normale Berechnung

**Gewünschte Strategie:**
- Backlog vorhanden → Maximale Kapazität (aber nicht zwingend 3 Schichten)
- Kein Backlog → Normale Berechnung

### Kritische Aspekte

**⚠️ WICHTIG:**
- Diese Logik beeinflusst Produktionskapazität
- Änderung beeinflusst gesamte Produktionsplanung
- Muss konsistent mit `ui/production_calculations.py` sein

**Abhängigkeiten:**
- `simulation/production_planner.py` - Statische Produktionsplanung
- `ui/production_calculations.py` - Dynamische Produktionsplanung (muss angepasst werden!)
- `pages/2_volumenplanung.py` - Schichtenberechnung (muss konsistent sein)

### Implementierung

**Schritt 1: Prüfe aktuelle Logik**
```python
# In simulation/production_planner.py, Zeile 141-156:
# Aktuell: if total_backlog > 0: shifts = 3
# Sollte sein: if total_backlog > 0: shifts = min(3, max(1, shifts_needed))
```

**Schritt 2: Korrigiere in production_planner.py**
```python
# Ändere Logik zu:
if total_backlog > 0:
    # Bei Backlog: Nutze maximale benötigte Kapazität (aber nicht zwingend 3)
    shifts_needed = math.ceil(total_demand / capacity_per_shift)
    shifts = min(3, max(1, shifts_needed))  # Begrenzt auf 1-3
else:
    # Normal: Berechne Schichten basierend auf Bedarf
    shifts_needed = math.ceil(total_demand / capacity_per_shift)
    shifts = min(3, max(1, shifts_needed))
```

**Schritt 3: Korrigiere in production_calculations.py**
```python
# In ui/production_calculations.py:
# Prüfe: Wird dieselbe Logik verwendet?
# Stelle sicher, dass dynamische Berechnung konsistent ist
```

**Schritt 4: Prüfe Volumenplanung**
```python
# In pages/2_volumenplanung.py:
# Prüfe: Wird Schichtenberechnung konsistent verwendet?
# Stelle sicher, dass keine Backlog-Logik dort verwendet wird
```

---

## 7. Marketingszenario: Erweitern um einzelne Fertigprodukte

### Aktueller Zustand

**Location:** `models/scenarios.py`

**Aktuelle Implementierung:**
- `MarketingCampaignScenario` wirkt auf ALLE Produkte
- `demand_increase_factor` wird auf alle Produkte angewendet

**Gewünschte Erweiterung:**
- Marketingaktion sollte auf einzelne Produkte beschränkt werden können
- Z.B. "Marketing nur für MTB Allrounder mit Faktor 1.5"

### Hintergrund

**Aktuelle Logik:**
```python
# In simulation/simulator.py, Zeile 258-267:
for scenario in marketing_scenarios:
    factor = scenario.demand_increase_factor
    for product in self.master_data.BOM.keys():
        base_float = base_daily_floats.get(product, 0.0)
        add_on = base_float * (factor - 1.0)
        marketing_add_ons[product] += add_on
```

**Problem:**
- Alle Produkte werden gleich behandelt
- Keine Möglichkeit, nur bestimmte Produkte zu bewerben

### Kritische Aspekte

**⚠️ WICHTIG:**
- Änderung beeinflusst `MarketingCampaignScenario` Klasse
- Cache-Invalidierung muss angepasst werden (scenario_fingerprint)
- UI muss angepasst werden (scenario_sidebar.py)
- Rückwärtskompatibilität: Bestehende Szenarien müssen weiter funktionieren

**Abhängigkeiten:**
- `models/scenarios.py` - MarketingCampaignScenario Klasse
- `ui/scenario_sidebar.py` - UI für Szenario-Erstellung
- `ui/volume_planning_utils.py` - scenario_fingerprint (Cache-Key)
- `simulation/simulator.py` - Marketing-Add-ons Berechnung

### Implementierung

**Schritt 1: Erweitere MarketingCampaignScenario**
```python
# In models/scenarios.py:
class MarketingCampaignScenario:
    def __init__(self, ..., affected_products: List[str] = None):
        # affected_products: Liste von Produktnamen
        # Wenn None: Alle Produkte (Rückwärtskompatibilität)
        self.affected_products = affected_products or list(MasterData.BOM.keys())
```

**Schritt 2: Passe Berechnung an**
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

**Schritt 3: Passe UI an**
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

**Schritt 4: Passe Cache-Key an**
```python
# In ui/volume_planning_utils.py, _scenario_fingerprint():
if isinstance(s, MarketingCampaignScenario):
    extra = (
        getattr(s, "demand_increase_factor", None),
        tuple(sorted(getattr(s, "affected_products", [])))  # NEU
    )
```

---

## 8. Nachfrage-Faktor überdenken (vielleicht in Prozent bis 100)

### Aktueller Zustand

**Location:** `ui/scenario_sidebar.py`, `models/scenarios.py`

**Aktuelle Implementierung:**
- `demand_increase_factor` als Float (z.B. 1.5 = 50% Erhöhung)
- Slider: 1.0 bis 3.0 (Faktor)

**Gewünschte Änderung:**
- Prozent-basierte Eingabe (0% bis 100%)
- Oder: Beide Optionen (Faktor oder Prozent)

### Hintergrund

**Aktuelle Logik:**
```python
# Faktor 1.5 = 50% Erhöhung
# Faktor 2.0 = 100% Erhöhung (Verdopplung)
# Faktor 3.0 = 200% Erhöhung (Verdreifachung)
```

**Prozent-Logik:**
```python
# 50% Erhöhung = Faktor 1.5
# 100% Erhöhung = Faktor 2.0
# 200% Erhöhung = Faktor 3.0
```

### Kritische Aspekte

**⚠️ WICHTIG:**
- Rückwärtskompatibilität: Bestehende Szenarien verwenden Faktor
- Konvertierung: Prozent → Faktor: `factor = 1.0 + (percent / 100.0)`
- UI-Änderung: Slider oder Input-Feld

**Abhängigkeiten:**
- `models/scenarios.py` - MarketingCampaignScenario
- `ui/scenario_sidebar.py` - UI
- `ui/volume_planning_utils.py` - scenario_fingerprint (Cache-Key)

### Implementierung

**Option A: Prozent-basiert (0-100%)**
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

**Option B: Beide Optionen (Faktor oder Prozent)**
```python
# In ui/scenario_sidebar.py:
input_mode = st.radio(
    "Eingabe-Modus",
    ["Prozent", "Faktor"],
    key=f"marketing_mode_global{key_suffix}"
)

if input_mode == "Prozent":
    demand_increase_percent = st.slider(...)
    demand_factor = 1.0 + (demand_increase_percent / 100.0)
else:
    demand_factor = st.slider(1.0, 3.0, 1.5, 0.1)
```

**Empfehlung: Option A (Prozent-basiert)**
- Intuitiver für Benutzer
- Einfacher zu verstehen
- Konsistent mit anderen Prozent-Eingaben

---

## 9. Andere Szenarien implementieren

### Aktueller Zustand

**Location:** `models/scenarios.py`

**Implementierte Szenarien:**
- ✅ `StandardScenario` - Basis-Szenario (läuft permanent)
- ✅ `MarketingCampaignScenario` - Marketingaktionen
- ⚠️ `WarehouseDamageScenario` - Wasserschaden im Lager (teilweise implementiert)
- ⚠️ `SupplierBreakdownScenario` - Maschinenausfall (teilweise implementiert)
- ⚠️ `DeliveryProblemScenario` - Lieferprobleme (teilweise implementiert)

### Zu implementierende Szenarien

#### 9.1 WarehouseDamageScenario (Wasserschaden im Lager)

**Aktueller Status:**
- ✅ Klasse existiert
- ✅ Wird im Simulator verarbeitet (Zeile 202-207)
- ⚠️ UI existiert, aber Logik muss geprüft werden

**Zu prüfen:**
- Wird `stock_loss_percentage` korrekt angewendet?
- Wird nur `affected_component` betroffen?
- Wird Bestand korrekt reduziert?

**Kritische Aspekte:**
- Muss konsistent mit `material_inventory_data` sein
- Muss Cache invalidiert werden
- Muss in Materiallager sichtbar sein

#### 9.2 SupplierBreakdownScenario (Maschinenausfall)

**Aktueller Status:**
- ✅ Klasse existiert
- ✅ Wird im Simulator verarbeitet (Zeile 230-234)
- ⚠️ Blockiert nur neue Bestellungen, nicht bereits unterwegs befindliche Ware

**Zu prüfen:**
- Wird Bestellung korrekt blockiert?
- Wird `component_type` korrekt berücksichtigt?
- Wird in Lieferant China angezeigt?

**Kritische Aspekte:**
- Muss in `ChinaTransportManager.place_order()` geprüft werden
- Muss in `get_supplier_log_dataframe()` angezeigt werden
- Muss Cache invalidiert werden

#### 9.3 DeliveryProblemScenario (Lieferprobleme)

**Aktueller Status:**
- ✅ Klasse existiert
- ⚠️ Wird in `ChinaTransportManager` verarbeitet
- ⚠️ Logik muss geprüft werden

**Zu prüfen:**
- Wird `loss_percentage` korrekt angewendet?
- Wird `delay_days` korrekt angewendet?
- Wird `component_type` korrekt berücksichtigt?

**Kritische Aspekte:**
- Muss in `place_order()` oder `process_transport()` verarbeitet werden
- Muss in Inbound-Tabelle sichtbar sein
- Muss Cache invalidiert werden

### Implementierungsreihenfolge

**Empfohlene Reihenfolge:**
1. **WarehouseDamageScenario** - Einfachste Implementierung (nur Bestandsreduktion)
2. **SupplierBreakdownScenario** - Mittlere Komplexität (Bestellblockierung)
3. **DeliveryProblemScenario** - Höchste Komplexität (Verluste + Verzögerungen)

### Kritische Aspekte für alle Szenarien

**⚠️ WICHTIG:**
- **Cache-Invalidierung:** Alle Szenarien müssen `scenario_fingerprint` beeinflussen
- **Konsistenz:** Szenarien müssen in allen betroffenen Seiten sichtbar sein
- **Rückwärtskompatibilität:** Bestehende Szenarien müssen weiter funktionieren
- **UI:** Alle Szenarien müssen in `scenario_sidebar.py` verfügbar sein

**Abhängigkeiten:**
- `models/scenarios.py` - Szenario-Klassen
- `ui/scenario_sidebar.py` - UI für Szenario-Erstellung
- `ui/volume_planning_utils.py` - scenario_fingerprint (Cache-Key)
- `simulation/simulator.py` - Szenario-Verarbeitung
- `simulation/china_transport.py` - Transport-Szenarien
- `simulation/production_planner.py` - Produktions-Szenarien

### Implementierungs-Checkliste

**Für jedes Szenario:**
- [ ] Klasse in `models/scenarios.py` vollständig implementiert
- [ ] UI in `ui/scenario_sidebar.py` hinzugefügt
- [ ] scenario_fingerprint erweitert (Cache-Key)
- [ ] Verarbeitung im Simulator implementiert
- [ ] Sichtbarkeit in betroffenen Seiten (z.B. Materiallager, Inbound)
- [ ] Cache-Invalidierung getestet
- [ ] Rückwärtskompatibilität getestet

---

## Zusammenfassung: Prioritäten

### Hoch (Kritisch für Datenkonsistenz)
1. **To-Do 2:** Inbound-Tage prüfen (Verfügbarkeit +1 Tag)
2. **To-Do 3:** Material am Wochenende (Verfügbarkeit korrigieren)
3. **To-Do 6:** Schichtenplanung bei Backlog (zu aggressiv)

### Mittel (Wichtig für Benutzerfreundlichkeit)
4. **To-Do 1:** SCOR-Metriken verschieben/umstrukturieren
5. **To-Do 4:** Spalten in Produktion entfernen
6. **To-Do 5:** Farbliche Markierungen in Inbound

### Niedrig (Erweiterungen)
7. **To-Do 7:** Marketing für einzelne Produkte
8. **To-Do 8:** Nachfrage-Faktor in Prozent
9. **To-Do 9:** Andere Szenarien implementieren

---

## Allgemeine Implementierungshinweise

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
