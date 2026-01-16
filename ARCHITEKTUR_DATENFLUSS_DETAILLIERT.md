# Detaillierte Architektur und Datenfluss

## 1. Volumenplanung als "Single Source of Truth" - Aktueller Stand

### ✅ Was ist die Volumenplanung?

Die **Volumenplanung** ist die **einzige Quelle für Nachfrageberechnungen**. Sie berechnet:
- **Tägliche Nachfrage** für alle 365 Tage des Jahres 2026
- **Für alle Produkte** (MTB Allrounder, E-Bike City, etc.)
- **Mit Carry-Over-Logik** (präzise Ganzzahl-Produktion)
- **Mit Marketing-Add-ons** (wenn Szenarien aktiv sind)

### ✅ Wo wird die Volumenplanung berechnet?

**Funktion:** `calculate_volume_planning_demand()` in `ui/volume_planning_utils.py`

**Wann wird sie aufgerufen?**
1. **Beim Start der App** (`app.py` → `run_happy_path_simulation()` → `calculate_volume_planning_demand()`)
2. **Vor der Simulation** (damit Daten verfügbar sind)
3. **Einmalig** (wird gecacht in `st.session_state.volume_planning_calculated`)

**Was wird gespeichert?**
- `st.session_state.daily_demands_planned`: Nachfrage OHNE Marketing (für "Geplante Planung")
- `st.session_state.daily_demands_actual`: Nachfrage MIT Marketing (für "Tatsächliche Planung" und Simulation)

### ✅ Wer verwendet die Volumenplanung-Daten?

1. **Simulator** (`simulation/simulator.py`):
   - Liest `daily_demands_actual` aus `st.session_state` (Zeile 156, 274, 382)
   - Verwendet diese Daten für die tägliche Nachfrage im Simulation-Loop
   - **WICHTIG**: Der Simulator berechnet die Nachfrage NICHT selbst, sondern liest sie aus der Volumenplanung

2. **China Transport Manager** (`simulation/china_transport.py`):
   - `_calculate_order_quantity_from_volume_planning()` (Zeile 368)
   - Berechnet "Bestelleingang" basierend auf `daily_demands_actual`
   - **WICHTIG**: "Bestelleingang" = Summe der Nachfrage aller Produkte mit dem spezifischen Sattel-Typ für `order_date + lead_time_days`

3. **Procurement Manager** (`simulation/procurement_manager.py`):
   - Erhält `expected_demand` vom Simulator
   - Dieser `expected_demand` stammt aus `daily_demands_actual` (vom Simulator übergeben)

4. **Volumenplanung-Seite** (`pages/2_volumenplanung.py`):
   - Zeigt die berechneten Daten an (wöchentlich und täglich)
   - Verwendet die gecachten Daten aus `st.session_state`

---

## 2. Was macht die Simulation zusätzlich?

Die Simulation macht **weitere Berechnungen**, die über die reine Nachfrage hinausgehen:

### 2.1 Produktionsplanung (`ProductionPlanner`)
- **Input**: Nachfrage aus Volumenplanung
- **Berechnet**: 
  - Welche Produkte produziert werden sollen
  - Priorisierung bei Engpässen
  - Schichtplanung
- **Output**: Produktionsplan pro Tag

### 2.2 Beschaffung (`ProcurementManager`)
- **Input**: Zukünftige Nachfrage aus Volumenplanung (für Tag `day + 49`)
- **Berechnet**: 
  - Bestellmenge für Sättel
  - Reorder Points
- **Output**: Bestellungen an `ChinaTransportManager`

### 2.3 Transport-Logistik (`ChinaTransportManager`)
- **Input**: Bestellungen vom `ProcurementManager`
- **Berechnet**: 
  - Produktion in China (mit Produktionszeit, Feiertagen, Ausfällen)
  - Transport zum Hafen
  - Verschiffung (Losgröße >= 500)
  - Ankunft in Deutschland
- **Output**: 
  - `transport_status` (Status aller Bestellungen)
  - `get_inbound_log_dataframe()` (Inbound-Tabelle)
  - `get_supplier_log_dataframe()` (Lieferant-China-Tabelle)

### 2.4 Lagerverwaltung (`Inventory`)
- **Input**: Wareneingänge aus `ChinaTransportManager`, Produktionsentnahmen
- **Berechnet**: 
  - Lagerbestände (Frames Alu, Frames Carbon, Sättel)
  - Verfügbarkeit für Produktion
- **Output**: Aktuelle Lagerbestände

### 2.5 Auslieferung (`MarketBacklog`)
- **Input**: Produzierte Mengen, Marktverteilung
- **Berechnet**: 
  - Backlog pro Markt
  - In-Transit-Mengen
  - Fulfillment
- **Output**: Backlog-Status, Auslieferungen

---

## 3. Datenfluss-Diagramm (Aktuell)

```
┌─────────────────────────────────────────────────────────────┐
│  VOLUMENPLANUNG (Page 2) - "Single Source of Truth"        │
│  • calculate_volume_planning_demand()                       │
│  • Berechnet Nachfrage für ALLE 365 Tage                    │
│  • Inkl. Marketing-Add-ons                                   │
│  • Inkl. Carry-Over-Logik                                   │
│  • Speichert in st.session_state.daily_demands_actual      │
└───────────────────────┬───────────────────────────────────┘
                         │
                         │ Übergibt Daten
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SIMULATOR - Verwendet vorgegebene Nachfrage                 │
│  • Liest daily_demands_actual aus session_state              │
│  • Verwendet für tägliche Nachfrage                          │
│  • Verwendet für zukünftige Nachfrage (Bestellungen)        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Tägliche Schleife über 365 Tage                   │    │
│  │  Für jeden Tag:                                     │    │
│  │  1. Nachfrage aus daily_demands_actual lesen       │    │
│  │  2. Produktionsplanung (ProductionPlanner)          │    │
│  │  3. Beschaffung (ProcurementManager)                │    │
│  │     └─> Verwendet Volumenplanung-Daten             │    │
│  │  4. Transport-Logistik (ChinaTransportManager)      │    │
│  │     └─> Berechnet Produktion, Transport, Verschiffung│    │
│  │  5. Lagerverwaltung (Inventory)                     │    │
│  │  6. Auslieferung (MarketBacklog)                    │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬───────────────────────────────────┘
                         │
                         │ Ergebnisse
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  VISUALISIERUNG (Streamlit Pages)                           │
│  • Page 3: Lieferant China                                   │
│    └─> get_supplier_log_dataframe()                         │
│        └─> Verwendet transport_status                       │
│        └─> "Bestelleingang" aus Volumenplanung berechnet   │
│  • Page 4: Inbound                                           │
│    └─> get_inbound_log_dataframe()                          │
│        └─> Verwendet transport_status                       │
│  • Page 5: Materiallager                                    │
│    └─> Zeigt Inventory-Bestände                            │
│  • Page 6: Produktion                                        │
│    └─> Zeigt Produktionsplan                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Antwort auf Ihre Frage: "Macht nicht die Simulation ab Lieferant China die Berechnungen?"

### ✅ Klarstellung:

**Die Simulation macht Berechnungen, aber:**
- **Nachfrage** kommt aus der Volumenplanung (nicht selbst berechnet)
- **Produktion, Transport, Lager, Auslieferung** werden von der Simulation berechnet

**"Lieferant China" (Page 3) zeigt:**
- **Bestelleingang**: Berechnet aus Volumenplanung (über `_calculate_order_quantity_from_volume_planning()`)
- **Produktionsdatum, Produktionsmenge, Warenausgang, Warenbestand**: Berechnet von `ChinaTransportManager` (basierend auf Bestellungen, Produktionszeit, Feiertagen, Ausfällen)

**"Inbound" (Page 4) zeigt:**
- Daten aus `ChinaTransportManager.transport_status`
- Diese werden von der Simulation berechnet (Transport-Logistik)

**Fazit:**
- **Nachfrage** = Volumenplanung (Single Source of Truth) ✅
- **Produktion, Transport, Lager** = Simulation (verwendet Nachfrage als Input) ✅

---

## 5. Carry-Over-Logik - Detaillierte Erklärung

### 5.1 Problemstellung

**Problem**: Jahresvolumen = 370.000 Bikes, aber:
- Monatliche Saisonalität (z.B. Januar: 0.05 = 5% des Jahresvolumens)
- Verkaufsanteile pro Produkt (z.B. MTB Allrounder: 0.35 = 35%)
- Arbeitstage pro Monat (z.B. Januar: 22 Arbeitstage)

**Ergebnis**: Tägliche Nachfrage = `370.000 * 0.05 * 0.35 / 22 = 294,32 Bikes`

**Problem**: Wir können keine 0,32 Bikes produzieren! Wir brauchen Ganzzahlen.

### 5.2 Lösung: Carry-Over-Logik

**Idee**: Reste (Dezimalstellen) werden auf den nächsten Arbeitstag übertragen.

**Beispiel:**
- Tag 1: `294,32` → Produziere `294` (Rest: `0,32`)
- Tag 2: `294,32 + 0,32 = 294,64` → Produziere `294` (Rest: `0,64`)
- Tag 3: `294,32 + 0,64 = 294,96` → Produziere `294` (Rest: `0,96`)
- Tag 4: `294,32 + 0,96 = 295,28` → Produziere `295` (Rest: `0,28`)

**Ergebnis**: Über mehrere Tage wird die Nachfrage exakt erfüllt (gerundete Summe = exakte Summe).

### 5.3 Implementierung im Code

**Datei:** `simulation/demand_calculator.py`

**Methode:** `calculate_daily_demand_per_product()`

**Schritte:**

1. **Base_Daily_Float berechnen** (monatlich):
   ```python
   monthly_target = yearly_volume * seasonality_factor * sales_share
   base_daily_float = monthly_target / num_workdays_in_month
   ```

2. **Rest vom vorherigen Tag holen**:
   ```python
   remainder = self.product_remainders.get(product, 0.0)
   ```

3. **Base + Rest zusammenfassen**:
   ```python
   base_with_remainder = round(base_daily_float + remainder, 12)
   # WICHTIG: Runde auf 12 Dezimalstellen, um Floating-Point-Fehler zu vermeiden
   ```

4. **Abrunden (wie Excel ABRUNDEN)**:
   ```python
   rounded_base = math.floor(base_with_remainder)
   # WICHTIG: math.floor() für korrekte Abrundung
   ```

5. **Marketing-Add-on addieren** (NACH der Rundung):
   ```python
   daily_target_float = rounded_base + marketing_add_on
   ```

6. **Am letzten Arbeitstag: Reste aufsummieren**:
   ```python
   if is_last_workday_of_year:
       remainder_to_add = base_with_remainder - rounded_base
       daily_target_float = rounded_base + remainder_to_add + marketing_add_on
   ```

7. **Neuen Rest berechnen** (für nächsten Tag):
   ```python
   new_remainder = base_with_remainder - rounded_base
   new_remainder = round(new_remainder, 12)  # Runde auf 12 Dezimalstellen
   self.product_remainders[product] = new_remainder
   ```

8. **Ergebnis zurückgeben** (Ganzzahl):
   ```python
   return math.floor(daily_target_float)
   ```

### 5.4 Wichtige Details

**Floating-Point-Präzision:**
- Problem: `0.1 + 0.2 = 0.30000000000000004` (Floating-Point-Fehler)
- Lösung: Runde auf 12 Dezimalstellen vor Berechnungen
- Code: `round(value, 12)`

**Wochenenden/Feiertage:**
- Problem: Rest bleibt unverändert, wenn kein Arbeitstag
- Lösung: Rest wird nur an Arbeitstagen aktualisiert
- Code: `if not is_workday: return 0` (Rest bleibt unverändert)

**Letzter Arbeitstag des Jahres:**
- Problem: Reste würden sonst verworfen
- Lösung: Alle Reste am letzten Arbeitstag aufsummieren
- Code: `if is_last_workday_of_year: remainder_to_add = ...`

**Sequenzielle Berechnung:**
- Problem: Reste müssen chronologisch übertragen werden
- Lösung: Berechne für alle Tage sequenziell (Tag 0 → Tag 1 → ... → Tag 364)
- Code: `for day in range(365): ...`

---

## 6. Tägliche vs. Wöchentliche Volumenplanung

### 6.1 Gemeinsamkeiten

**Beide verwenden die gleichen Daten:**
- `st.session_state.daily_demands_planned` (ohne Marketing)
- `st.session_state.daily_demands_actual` (mit Marketing)

**Beide verwenden die gleiche Berechnung:**
- `calculate_volume_planning_demand()` (einmalig beim Start)
- Sequenzielle Berechnung für alle 365 Tage
- Gleiche Carry-Over-Logik

### 6.2 Unterschiede

**Wöchentliche Planung:**
- **Darstellung**: Aggregiert nach Kalenderwochen
- **Zeigt**: Wochensummen, Wochenmittelwerte
- **Zweck**: Übersichtliche Planung über längere Zeiträume

**Tägliche Planung:**
- **Darstellung**: Einzelne Tage
- **Zeigt**: Tageswerte, Tagesdetails
- **Zweck**: Detaillierte Tagesplanung

### 6.3 Abhängigkeiten

**Beide hängen ab von:**
1. **Jahresvolumen** (`yearly_volume`): Gesamtes Jahresvolumen (Standard: 370.000)
2. **Saisonalität** (`MasterData.SEASONALITY`): Monatliche Faktoren
3. **Verkaufsanteile** (`MasterData.PRODUCT_SALES_SHARES`): Anteil pro Produkt
4. **Arbeitstage** (`WorkdayCalculator`): Welche Tage sind Arbeitstage?
5. **Marketing-Szenarien** (`ScenarioManager`): Zusätzliche Nachfrage durch Marketing

**Wichtig**: Alle diese Abhängigkeiten werden in `calculate_volume_planning_demand()` berücksichtigt.

---

## 7. Ist das Bild noch korrekt?

**Das Bild zeigt:**
1. ✅ `app.py` ruft `calculate_volume_planning_demand()` auf
2. ✅ `app.py` ruft `Simulator.__init__()` auf
3. ✅ `Simulator.__init__()` ruft `_place_initial_orders()` auf (verwendet Volumenplanung-Daten)
4. ✅ `Simulator.run()` liest Nachfrage aus `daily_demands_actual`
5. ✅ `ProcurementManager` verwendet Volumenplanung-Daten
6. ✅ `ChinaTransportManager` berechnet "Bestelleingang" aus Volumenplanung
7. ✅ Ergebnisse werden in Streamlit-Seiten dargestellt

**Das Bild ist korrekt!** ✅

**Kleine Ergänzung:**
- Die Simulation macht zusätzliche Berechnungen (Produktion, Transport, Lager, Auslieferung), die im Bild nicht explizit gezeigt werden, aber implizit enthalten sind (durch die Manager-Komponenten).

---

## 8. Zusammenfassung

### ✅ Volumenplanung = Single Source of Truth für Nachfrage

- **Berechnet**: Tägliche Nachfrage für alle 365 Tage
- **Speichert**: In `st.session_state.daily_demands_actual`
- **Verwendet von**: Simulator, ProcurementManager, ChinaTransportManager

### ✅ Simulation = Verarbeitet Nachfrage weiter

- **Input**: Nachfrage aus Volumenplanung
- **Berechnet**: Produktion, Transport, Lager, Auslieferung
- **Output**: Ergebnisse für Visualisierung

### ✅ Carry-Over-Logik = Präzise Ganzzahl-Produktion

- **Problem**: Dezimalstellen in täglicher Nachfrage
- **Lösung**: Reste werden auf nächsten Arbeitstag übertragen
- **Ergebnis**: Exakte Jahresgesamtsumme (370.000)

### ✅ Tägliche vs. Wöchentliche Planung

- **Gleiche Datenquelle**: `daily_demands_actual`
- **Unterschiedliche Darstellung**: Tageswerte vs. Wochenwerte
- **Gleiche Berechnung**: Sequenziell, mit Carry-Over-Logik

