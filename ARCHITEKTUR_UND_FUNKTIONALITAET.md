# Supply Chain Simulation - Architektur und Funktionalität

## 1. Tech-Stack und Architektur

### 1.1 Technologie-Stack

**Frontend-Framework:**
- **Streamlit** (`streamlit>=1.28.0`): Web-Framework für Python-Apps
  - Ermöglicht schnelle Entwicklung interaktiver Web-Apps ohne HTML/JavaScript
  - Multi-Page-App-Struktur mit automatischer Navigation
  - Session State Management für Zustandsverwaltung zwischen Seitenaufrufen
  - Widgets für Eingaben (Sliders, Date Picker, etc.)
  - DataFrames und Charts direkt darstellbar

**Datenverarbeitung:**
- **Pandas** (`pandas>=2.0.0`): Datenanalyse und -manipulation
  - DataFrames für tabellarische Datenstrukturen
  - Datenaggregation, Filterung, Transformation
  - Integration mit Streamlit für Tabellendarstellung
- **NumPy** (`numpy>=1.24.0`): Numerische Berechnungen
  - Unterstützt Pandas bei mathematischen Operationen
  - Vektoroperationen für Performance

**Visualisierung:**
- **Plotly** (`plotly>=5.17.0`): Interaktive Charts
  - Interaktive Diagramme (Balken, Linien, gestapelt)
  - Hover-Effekte, Zoom, Pan
  - Integration mit Streamlit über `st.plotly_chart()`

**Business-Logik:**
- **Holidays** (`holidays>=0.34`): Feiertagsberechnung
  - Länder-spezifische Feiertage (DE, CN, etc.)
  - Integration in WorkdayCalculator für korrekte Arbeitstagsberechnung

**Python-Version:**
- Python 3.x (empfohlen 3.9+)

### 1.2 Architektur-Übersicht

Die Anwendung folgt einer **layered architecture** mit klarer Trennung von Verantwortlichkeiten:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  (Streamlit Pages: app.py, pages/*.py)                  │
│  - UI-Komponenten                                        │
│  - Benutzerinteraktion                                   │
│  - Datenvisualisierung                                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Business Logic Layer                  │
│  (simulation/*.py)                                       │
│  - Simulator (Haupt-Orchestrator)                        │
│  - DemandCalculator (Nachfrageberechnung)               │
│  - ProductionPlanner (Produktionsplanung)                │
│  - ProcurementManager (Beschaffung)                     │
│  - ChinaTransportManager (Transport-Logistik)            │
│  - WorkdayCalculator (Arbeitstagsberechnung)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Data Model Layer                      │
│  (models/*.py)                                           │
│  - Inventory (Lagerbestände)                            │
│  - MarketBacklog (Kunden-Backlog)                        │
│  - ScenarioManager (Szenarien-Verwaltung)               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Configuration Layer                   │
│  (config/*.py)                                           │
│  - MasterData (Stammdaten)                               │
│  - HolidaysConfig (Feiertagskonfiguration)               │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Datenfluss

1. **Initialisierung**: `app.py` → `Simulator.__init__()` → Initialisierung aller Komponenten
2. **Simulation**: `Simulator.run()` → Tägliche Schleife über 365 Tage
3. **Täglicher Ablauf**:
   - Nachfrageberechnung (`DemandCalculator`)
   - Produktionsplanung (`ProductionPlanner`)
   - Beschaffung (`ProcurementManager`)
   - Transport-Logistik (`ChinaTransportManager`)
   - Lagerverwaltung (`Inventory`)
   - Auslieferung (`MarketBacklog`)
4. **Visualisierung**: Ergebnisse werden in Streamlit-Seiten dargestellt

---

## 2. Verzeichnisstruktur

```
scm-app/
├── app.py                          # Hauptseite (SCOR-Metriken)
├── pages/                          # Streamlit-Seiten (Multi-Page-App)
│   ├── 1_reporting.py             # Reporting-Dashboard
│   ├── 2_volumenplanung.py        # Volumenplanung (wöchentlich/täglich)
│   ├── 3_lieferant_china.py       # Lieferant China Übersicht
│   ├── 4_inbound.py               # Inbound-Logistik
│   ├── 5_materiallager.py         # Materiallager
│   ├── 6_produktion.py            # Produktion
│   ├── 7_fertigproduktelager.py  # Fertigproduktelager
│   └── 8_stammdaten.py            # Stammdaten-Anzeige
├── simulation/                     # Business-Logik
│   ├── simulator.py               # Haupt-Orchestrator
│   ├── demand_calculator.py       # Nachfrageberechnung
│   ├── production_planner.py      # Produktionsplanung
│   ├── procurement_manager.py    # Beschaffung
│   ├── china_transport.py         # Transport-Logistik
│   └── workday_calculator.py      # Arbeitstagsberechnung
├── models/                         # Datenmodelle
│   ├── inventory.py               # Lagerbestand
│   ├── backlog.py                 # Kunden-Backlog
│   └── scenarios.py                # Szenarien-Verwaltung
├── config/                         # Konfiguration
│   ├── master_data.py             # Stammdaten
│   └── holidays_config.py         # Feiertagskonfiguration
└── ui/                            # UI-Hilfsfunktionen
    ├── utils.py                   # Zentrale Utility-Funktionen
    ├── scenario_sidebar.py        # Szenarien-Sidebar
    └── charts.py                  # Chart-Hilfsfunktionen
```

---

## 3. Detaillierte Dateibeschreibung

### 3.1 Frontend-Layer

#### `app.py` - Hauptseite (SCOR-Metriken)
**Zweck**: Zentrale Dashboard-Seite mit SCOR-Metriken

**Funktionalität**:
- **Automatische Simulation**: Führt beim ersten Laden automatisch "Happy Path" Simulation aus
- **SCOR-Metriken**: Zeigt 5 SCOR-Bereiche:
  - **Inbound**: Lieferanten-Performance (Liefertreue, Durchlaufzeit, etc.)
  - **Outbound**: Kunden-Performance (Liefertreue, Durchlaufzeit, etc.)
  - **Source**: Beschaffungs-Performance (Bestelltreue, Durchlaufzeit, etc.)
  - **Delivery**: Auslieferungs-Performance (Liefertreue, Durchlaufzeit, etc.)
  - **Fulfillment**: Gesamt-Performance (Perfect Order Fulfillment, etc.)
- **Visualisierung**: Balkendiagramme für Metriken
- **Session State**: Speichert Simulator-Instanz und Ergebnisse für andere Seiten

**Wichtige Funktionen**:
- `initialize_session_state()`: Initialisiert alle Session-Variablen
- `create_simulator()`: Erstellt Simulator-Instanz
- Automatischer `st.rerun()` nach Simulation

---

#### `pages/1_reporting.py` - Reporting-Dashboard
**Zweck**: Übersicht über Lagerbestände und Produktionsleistung

**Funktionalität**:
- **Materiallager**: Zeigt Bestände für Sättel (Spark, Speedline, etc.)
- **Produktionsleistung**: Zeigt Produktionsmengen pro Produkt
- **Visualisierung**: Gestapelte Balkendiagramme, Liniendiagramme
- **Datenquelle**: Nutzt `simulator.production_planner.production_logs` und Materiallager-Daten

**Wichtige Funktionen**:
- `get_saddle_inventory_data()`: Holt Sattel-Bestände aus Materiallager-Seite
- Dynamischer Import von `pages.5_Materiallager` (wegen Zahl im Dateinamen)

---

#### `pages/2_volumenplanung.py` - Volumenplanung
**Zweck**: Wöchentliche und tägliche Nachfrageplanung

**Funktionalität**:
- **Wöchentliche Planung**:
  - Nachfrage pro Kalenderwoche
  - Schichten-Berechnung basierend auf Kapazität
  - Visualisierung: Schichten-Balken, Produkt-Vergleich
  - **WICHTIG**: Sequenzielle Berechnung für alle 365 Tage (für korrekte Carry-Over-Logik)
- **Tägliche Planung**:
  - Nachfrage pro Tag
  - Filter nach Datumsbereich
  - Markierung von Feiertagen/Wochenenden (rot hinterlegt)
  - Visualisierung: Gestapeltes Balkendiagramm
- **Summenzeilen**: In beiden Ansichten (grau hinterlegt, fett)
- **Feiertags-Behandlung**: Nachfrage = 0 an Feiertagen/Wochenenden

**Wichtige Funktionen**:
- `calculate_product_demand()`: Berechnet Nachfrage mit Carry-Over-Logik
- Sequenzielle Berechnung: `for day in range(365)` vor wöchentlicher Aggregation
- Marketing-Add-ons werden berücksichtigt

**Bekanntes Problem**: KW 5 zeigt 1057 statt 1058 MTB Allrounder (Carry-Over-Logik)

---

#### `pages/3_lieferant_china.py` - Lieferant China
**Zweck**: Übersicht über Bestellungen und Produktion in China

**Funktionalität**:
- **Sattel-Auswahl**: Dropdown für Sattel-Typ (Spark, Speedline, etc.)
- **Tabelle**: Zeigt tägliche Daten:
  - Bestelleingang
  - Freigegebene Bestellungen
  - Produktionsmenge
  - Warenausgang
  - Warenbestand
- **Datenquelle**: `ChinaTransportManager.get_supplier_log_dataframe()`

**Wichtige Funktionen**:
- Sattel-Anteile werden aus `MasterData.SADDLE_SHARES` geladen
- Rundung auf ganze Zahlen für alle Mengen

---

#### `pages/4_inbound.py` - Inbound-Logistik
**Zweck**: Übersicht über eingehende Lieferungen aus China

**Funktionalität**:
- **Sattel-Auswahl**: Dropdown für Sattel-Typ
- **Tabelle**: Zeigt tägliche Daten:
  - Menge Gesamt (gerundet auf ganze Zahlen)
  - Individuelle Sattel-Mengen
- **Datenquelle**: `ChinaTransportManager.get_inbound_log_dataframe()`

**Wichtige Funktionen**:
- Port-Buckets für Transport-Logistik
- Optimierung: Early-Exit wenn keine weiteren Transporte erwartet

---

#### `pages/5_materiallager.py` - Materiallager
**Zweck**: Übersicht über Materiallager-Bestände

**Funktionalität**:
- **Sattel-Auswahl**: Dropdown für Sattel-Typ
- **Tabelle**: Zeigt tägliche Daten:
  - Lagerzugang (ganze Zahlen)
  - Bestand morgens (ganze Zahlen)
  - Lagerabgang (ganze Zahlen)
  - Verlustmenge
  - Bestand abends (ganze Zahlen)
- **Datenquelle**: `create_saddle_inventory_log()` (lokale Funktion)

**Wichtige Funktionen**:
- `create_saddle_inventory_log()`: Wird auch von Reporting-Seite genutzt
- Dynamischer Import wegen Zahl im Dateinamen (`5_Materiallager.py`)

---

#### `pages/6_produktion.py` - Produktion
**Zweck**: Übersicht über Produktionsleistung

**Funktionalität**:
- **Produkt-Auswahl**: Dropdown für Produkt
- **Tabelle**: Zeigt tägliche Daten:
  - Geplante PM (ganze Zahlen)
  - Tatsächliche PM (ganze Zahlen)
  - Fertiggestellte PM (ganze Zahlen)
  - Backlog (ganze Zahlen)
  - Auslastung (%) (1 Dezimalstelle, oder 0 wenn < 0.05)
  - Sattel-Bestand (ganze Zahlen)
- **Datenquelle**: `ProductionPlanner.production_logs`

**Wichtige Funktionen**:
- Auslastung wird dynamisch berechnet basierend auf Kapazität

---

#### `pages/7_fertigproduktelager.py` - Fertigproduktelager
**Zweck**: Übersicht über Fertigproduktelager-Bestände

**Funktionalität**:
- **Produkt-Auswahl**: Dropdown für Produkt
- **Tabelle**: Zeigt tägliche Daten:
  - Lagerzugang (1 Dezimalstelle) - **WICHTIG**: Float-Werte erlaubt
  - Bestand morgens (1 Dezimalstelle)
  - Lagerabgang (1 Dezimalstelle) - **WICHTIG**: Float-Werte erlaubt
  - Bestand abends (1 Dezimalstelle)
- **Datenquelle**: `create_finished_goods_log()` (lokale Funktion)

**Wichtige Funktionen**:
- Float-Werte für Lagerzugang/Lagerabgang (Bug-Fix: wurde vorher auf ganze Zahlen gerundet)

---

#### `pages/8_stammdaten.py` - Stammdaten
**Zweck**: Anzeige aller Stammdaten

**Funktionalität**:
- **6 Tabs**:
  1. **Stückliste (BOM)**: Produktstruktur aller Bike-Modelle
  2. **Planung**: Planungsparameter (Volumen, Kapazität, etc.)
  3. **Märkte & Kunden**: Marktverteilung, Transitzeiten
  4. **Auslieferung**: Auslieferungsparameter
  5. **Beschaffung**: Beschaffungsparameter (China)
  6. **Feiertage**: Feiertagskonfiguration (DE, CN)
- **Visualisierung**: Charts für Saisonalität, Marktverteilung, etc.

**Datenquelle**: `MasterData` Klasse

---

### 3.2 Business-Logic-Layer

#### `simulation/simulator.py` - Haupt-Orchestrator
**Zweck**: Koordiniert alle Simulationskomponenten

**Klassenstruktur**:
```python
class Simulator:
    def __init__(yearly_volume, initial_stock_*, scenario_manager)
    def run() -> tuple[pd.DataFrame, Dict[str, Any]]
    def _place_initial_orders()
    def _warmup_logistics()
    def _initialize_stock_from_inbound()
    def _calculate_scor_metrics()
```

**Funktionalität**:
- **Initialisierung**: Erstellt alle Komponenten (Inventory, Backlog, Calculators, Managers)
- **Initial Orders**: Platziert Bestellungen 49 Tage vor Simulationsbeginn
- **Warm-Up**: Simuliert Logistik für Tage vor Simulationsbeginn (damit Schiffe bereits im Dezember abfahren)
- **Simulation Loop**: 365 Tage:
  1. Nachfrageberechnung
  2. Produktionsplanung
  3. Beschaffung
  4. Transport-Logistik
  5. Lagerverwaltung
  6. Auslieferung
- **SCOR-Metriken**: Berechnet alle SCOR-Metriken am Ende

**Wichtige Abhängigkeiten**:
- `DemandCalculator`: Nachfrageberechnung
- `ProductionPlanner`: Produktionsplanung
- `ProcurementManager`: Beschaffung
- `ChinaTransportManager`: Transport-Logistik
- `Inventory`: Lagerverwaltung
- `MarketBacklog`: Kunden-Backlog

---

#### `simulation/demand_calculator.py` - Nachfrageberechnung
**Zweck**: Berechnet tägliche Nachfrage mit Carry-Over-Logik

**Klassenstruktur**:
```python
class DemandCalculator:
    def __init__(yearly_volume, workday_calculator)
    def _calculate_monthly_base_daily_float(month) -> Dict[str, float]
    def calculate_daily_demand_per_product(day, product, marketing_add_on, is_last_workday_of_year) -> int
    def calculate_daily_demand_per_product_dict(day, marketing_add_ons) -> Dict[str, int]
    def aggregate_bom_demand(product_demands) -> Tuple[Dict[str, float], float]
```

**Funktionalität**:
- **Monatliche Base-Daily-Float**: Berechnet tägliche Nachfrage pro Produkt basierend auf:
  - Saisonalität (`MasterData.SEASONALITY`)
  - Verkaufsanteile (`MasterData.PRODUCT_SALES_SHARES`)
  - Arbeitstage pro Monat
- **Carry-Over-Logik**: 
  - Rest vom vorherigen Tag wird zum nächsten Tag addiert
  - An Feiertagen/Wochenenden: Rest bleibt unverändert
  - Excel-Formel-Logik: `ABRUNDEN((Base + Rest); 0) + Marketing-Add-on`
- **Marketing-Add-ons**: Werden nach Rundung addiert (nicht in Rest übernommen)

**Wichtige Datenstrukturen**:
- `product_remainders`: Dict[str, float] - Rest pro Produkt
- `monthly_base_daily_float`: Dict[int, Dict[str, float]] - Base-Daily-Float pro Monat

**Bekanntes Problem**: Carry-Over-Logik funktioniert nicht korrekt (KW 5 zeigt 1057 statt 1058)

---

#### `simulation/production_planner.py` - Produktionsplanung
**Zweck**: Plant Produktion basierend auf Bottleneck-Logik und Priorisierung

**Klassenstruktur**:
```python
class ProductionPlanner:
    def __init__(inventory, demand_calculator, workday_calculator, china_transport_manager)
    def plan_daily_production(day, marketing_add_ons, scenario_manager) -> Dict[str, int]
    def _log_production(day, product, planned_pm, actual_qty, finished_pm, backlog, utilization, stock_saddle_specific)
    def get_production_logs() -> Dict[str, list]
```

**Funktionalität**:
- **Bottleneck-Logik**: Produziert basierend auf verfügbaren Komponenten (Frames, Sättel)
- **Priorisierung**: Produziert zuerst Produkte mit höherem Backlog
- **Kapazitätsberechnung**: 
  - Schichten: 1-3 (konfigurierbar)
  - Kapazität pro Stunde: 130 (konfigurierbar)
  - Tägliche Kapazität: Schichten × 8 Stunden × 130
- **Backlog-Tracking**: Verfolgt unerfüllte Nachfrage pro Produkt
- **Produktionslogs**: Speichert tägliche Produktionsdaten für UI

**Wichtige Datenstrukturen**:
- `backlog`: Dict[str, float] - Backlog pro Produkt
- `production_plan`: Dict[int, Dict[str, int]] - Produktionsplan
- `production_logs`: Dict[str, list] - Produktionslogs für UI

---

#### `simulation/procurement_manager.py` - Beschaffung
**Zweck**: Verwaltet Beschaffung von Komponenten

**Klassenstruktur**:
```python
class ProcurementManager:
    def __init__(inventory, china_transport_manager, workday_calculator)
    def process_procurement(day)
```

**Funktionalität**:
- **Bestellungen**: Erstellt Bestellungen basierend auf Bedarf
- **Integration**: Nutzt `ChinaTransportManager` für Bestellungen nach China
- **Lagerverwaltung**: Aktualisiert `Inventory` mit eingehenden Lieferungen

---

#### `simulation/china_transport.py` - Transport-Logistik
**Zweck**: Verwaltet detaillierte Transport-Logistik von China nach Deutschland

**Klassenstruktur**:
```python
class ChinaTransportManager:
    def __init__(inventory, workday_calculator, scenario_manager)
    def process_shipments(day)
    def get_supplier_log_dataframe(saddle_name, saddle_share) -> pd.DataFrame
    def get_inbound_log_dataframe(saddle_name, saddle_share) -> pd.DataFrame
    def _get_next_workday(start_day, use_chinese_holidays) -> int
    def _add_workdays(start_day, num_workdays, exclude_start, use_chinese_holidays) -> int
```

**Funktionalität**:
- **Transport-Logistik**: 
  - Produktion in China
  - Transport zum Hafen
  - Verschiffung (Losgröße-basiert)
  - Ankunft in Deutschland
- **Port-Buckets**: Verwaltet Bestände im Hafen
- **Losgröße**: Verschifft nur wenn Losgröße erreicht
- **Optimierung**: Early-Exit wenn keine weiteren Transporte erwartet

**Wichtige Datenstrukturen**:
- `port_buckets`: Dict[str, float] - Bestände im Hafen pro Sattel-Typ
- `shipment_schedule`: Liste von geplanten Verschiffungen

---

#### `simulation/workday_calculator.py` - Arbeitstagsberechnung
**Zweck**: Berechnet Arbeitstage unter Berücksichtigung von Feiertagen

**Klassenstruktur**:
```python
class WorkdayCalculator:
    def __init__(year)
    def is_workday(day) -> bool
    def is_weekend(day) -> bool
    def get_date_from_day(day) -> date
```

**Funktionalität**:
- **Feiertags-Integration**: Nutzt `HolidaysConfig` für Feiertage
- **Länder-spezifisch**: DE, CN (für China-Transport)
- **Arbeitstags-Prüfung**: Kombiniert Wochenende + Feiertage

---

### 3.3 Data-Model-Layer

#### `models/inventory.py` - Lagerbestand
**Zweck**: Verwaltet Lagerbestände für Komponenten

**Klassenstruktur**:
```python
@dataclass
class Inventory:
    stock_alu: float
    stock_carbon: float
    stock_saddles: float
    
    def add_stock(component_type, quantity)
    def remove_stock(component_type, quantity)
    def get_stock(component_type) -> float
```

**Funktionalität**:
- **Komponenten-Typen**: 
  - `frames_alu`: Aluminium-Rahmen
  - `frames_carbon`: Carbon-Rahmen
  - `saddles`: Sättel
- **CRUD-Operationen**: Add, Remove, Get

---

#### `models/backlog.py` - Kunden-Backlog
**Zweck**: Verwaltet Kunden-Backlog (unerfüllte Nachfrage)

**Klassenstruktur**:
```python
class MarketBacklog:
    def __init__()
    def initialize_markets(markets)
    def add_demand(day, market, product, quantity)
    def fulfill_demand(day, market, product, quantity)
    def get_backlog(day, market, product) -> float
```

**Funktionalität**:
- **Markt-spezifisch**: Backlog pro Markt (DE, USA, FR, etc.)
- **Transitzeiten**: Berücksichtigt Transitzeiten für Auslieferung
- **In-Transit**: Verfolgt Bestellungen auf dem Weg zum Kunden

---

#### `models/scenarios.py` - Szenarien-Verwaltung
**Zweck**: Verwaltet Szenarien (Marketing, Störungen, etc.)

**Klassenstruktur**:
```python
class Scenario:
    start_day: int
    end_day: int
    active: bool

class MarketingScenario(Scenario):
    demand_increase_factor: float

class BreakdownScenario(Scenario):
    breakdown_type: str
    breakdown_duration: int

class ScenarioManager:
    def add_scenario(scenario)
    def get_marketing_scenarios(day) -> List[MarketingScenario]
    def get_breakdown_scenarios(day) -> List[BreakdownScenario]
```

**Funktionalität**:
- **Marketing-Szenarien**: Erhöhen Nachfrage um Faktor
- **Störungs-Szenarien**: Reduzieren Produktion/Kapazität
- **Zeit-basiert**: Szenarien haben Start- und Enddatum

---

### 3.4 Configuration-Layer

#### `config/master_data.py` - Stammdaten
**Zweck**: Zentrale Stammdaten-Klasse

**Klassenstruktur**:
```python
class MasterData:
    # Konstanten
    DATE_FORMAT = '%d.%m.%Y'
    
    # Saisonalität
    SEASONALITY: Dict[int, float]
    
    # Märkte
    MARKETS: Dict[str, Dict[str, Any]]
    
    # BOM
    BOM: Dict[str, Dict[str, str]]
    
    # Verkaufsanteile
    PRODUCT_SALES_SHARES: Dict[str, float]
    
    # Globale Konfiguration
    GLOBAL_CONFIG: Dict[str, Any]
    
    # Sattel-Anteile
    SADDLE_SHARES: Dict[str, float]
    
    # Statische Methoden
    @staticmethod
    def get_month_from_day(day) -> int
    @staticmethod
    def get_frame_category(frame_type) -> str
```

**Funktionalität**:
- **Zentrale Datenquelle**: Alle Stammdaten an einem Ort
- **Statische Klasse**: Keine Instanziierung nötig
- **Konstanten**: Alle konfigurierbaren Parameter

---

#### `config/holidays_config.py` - Feiertagskonfiguration
**Zweck**: Feiertags-Konfiguration

**Funktionalität**:
- **Holidays-Integration**: Nutzt `holidays`-Bibliothek
- **Länder-spezifisch**: DE, CN, etc.
- **Integration**: Wird von `WorkdayCalculator` genutzt

---

### 3.5 UI-Layer

#### `ui/utils.py` - Utility-Funktionen
**Zweck**: Zentrale Hilfsfunktionen für Streamlit-Seiten

**Funktionen**:
- `initialize_session_state()`: Initialisiert alle Session-Variablen
- `create_simulator()`: Erstellt Simulator-Instanz
- `run_happy_path_simulation()`: Führt Happy Path Simulation aus
- `ensure_simulator_available()`: Prüft ob Simulator verfügbar ist

---

#### `ui/scenario_sidebar.py` - Szenarien-Sidebar
**Zweck**: Sidebar für Szenarien-Verwaltung

**Funktionalität**:
- **Szenarien-Verwaltung**: UI für Hinzufügen/Entfernen von Szenarien
- **Marketing-Szenarien**: Faktor-Eingabe
- **Störungs-Szenarien**: Typ- und Dauer-Eingabe

---

#### `ui/charts.py` - Chart-Hilfsfunktionen
**Zweck**: Wiederverwendbare Chart-Funktionen

**Funktionalität**:
- **Chart-Templates**: Vordefinierte Chart-Konfigurationen
- **Wiederverwendbarkeit**: Einheitliche Chart-Darstellung

---

## 4. Interaktionen und Datenfluss

### 4.1 Simulations-Ablauf

```
1. Initialisierung (app.py)
   ↓
2. Simulator.__init__()
   ├── Inventory erstellen
   ├── MarketBacklog erstellen
   ├── WorkdayCalculator erstellen
   ├── DemandCalculator erstellen
   ├── ChinaTransportManager erstellen
   ├── ProductionPlanner erstellen
   ├── ProcurementManager erstellen
   ├── _place_initial_orders() (49 Tage vorher)
   ├── _warmup_logistics() (Logistik vor Simulationsbeginn)
   └── _initialize_stock_from_inbound() (Initialbestand)
   ↓
3. Simulator.run() - 365 Tage Schleife
   Für jeden Tag:
   ├── Nachfrageberechnung (DemandCalculator)
   │   ├── Monatliche Base-Daily-Float
   │   ├── Carry-Over-Logik
   │   └── Marketing-Add-ons
   ├── Produktionsplanung (ProductionPlanner)
   │   ├── Bottleneck-Logik
   │   ├── Priorisierung
   │   └── Backlog-Tracking
   ├── Beschaffung (ProcurementManager)
   │   └── Bestellungen an ChinaTransportManager
   ├── Transport-Logistik (ChinaTransportManager)
   │   ├── Produktion in China
   │   ├── Transport zum Hafen
   │   ├── Verschiffung (Losgröße)
   │   └── Ankunft in Deutschland
   ├── Lagerverwaltung (Inventory)
   │   ├── Add Stock (von Transport)
   │   └── Remove Stock (für Produktion)
   └── Auslieferung (MarketBacklog)
       ├── Fulfill Demand
       └── In-Transit Tracking
   ↓
4. SCOR-Metriken Berechnung
   ├── Inbound-Metriken
   ├── Outbound-Metriken
   ├── Source-Metriken
   ├── Delivery-Metriken
   └── Fulfillment-Metriken
   ↓
5. Ergebnisse in Session State speichern
   ↓
6. Visualisierung in Streamlit-Seiten
```

### 4.2 Datenfluss zwischen Komponenten

```
DemandCalculator
    ↓ (Nachfrage)
ProductionPlanner
    ↓ (Produktionsplan)
Inventory
    ↓ (Komponenten-Verfügbarkeit)
ProductionPlanner
    ↓ (Tatsächliche Produktion)
MarketBacklog
    ↓ (Auslieferung)

ProcurementManager
    ↓ (Bestellungen)
ChinaTransportManager
    ↓ (Transport-Logistik)
Inventory
    ↓ (Eingehende Lieferungen)
ProductionPlanner
```

### 4.3 Session State Management

**Wichtige Session State Variablen**:
- `scenario_manager`: ScenarioManager-Instanz
- `results_df`: Simulations-Ergebnisse (DataFrame)
- `kpis`: SCOR-Metriken (Dict)
- `simulator`: Simulator-Instanz
- `happy_path_run`: Boolean (verhindert mehrfache Ausführung)
- `yearly_volume`: Jährliches Volumen (370000)

**Verwendung**:
- Alle Seiten teilen sich die gleichen Session State Variablen
- `app.py` führt Simulation aus und speichert Ergebnisse
- Andere Seiten lesen Ergebnisse aus Session State

---

## 5. Wichtige Konzepte und Logik

### 5.1 Carry-Over-Logik (Nachfrageberechnung)

**Zweck**: Präzise Ganzzahl-Produktion durch Rest-Übertragung

**Logik**:
1. Monatliche Base-Daily-Float berechnen: `(Monatliches Ziel / Arbeitstage)`
2. Rest vom vorherigen Tag addieren
3. Abrunden: `ABRUNDEN((Base + Rest); 0)`
4. Marketing-Add-on addieren (nach Rundung)
5. Neuen Rest berechnen: `(Base + Rest) - ABRUNDEN(Base + Rest; 0)`
6. An Feiertagen/Wochenenden: Rest bleibt unverändert

**Problem**: Funktioniert nicht korrekt (KW 5 zeigt 1057 statt 1058)

---

### 5.2 Bottleneck-Logik (Produktionsplanung)

**Zweck**: Produziert basierend auf verfügbaren Komponenten

**Logik**:
1. Nachfrage pro Produkt berechnen
2. Komponenten-Bedarf aggregieren (BOM)
3. Verfügbare Komponenten prüfen (Inventory)
4. Produktion planen basierend auf Bottleneck
5. Priorisierung: Produkte mit höherem Backlog zuerst

---

### 5.3 Transport-Logistik (China → Deutschland)

**Zweck**: Realistische Transport-Simulation

**Logik**:
1. Produktion in China (täglich)
2. Transport zum Hafen (chinesische Arbeitstage)
3. Verschiffung (nur wenn Losgröße erreicht)
4. Transportzeit (Schiff)
5. Ankunft in Deutschland (deutsche Arbeitstage)
6. Port-Buckets für Zwischenlagerung

---

### 5.4 SCOR-Metriken

**Zweck**: Supply Chain Performance Measurement

**Metriken**:
- **Inbound**: Lieferanten-Performance
- **Outbound**: Kunden-Performance
- **Source**: Beschaffungs-Performance
- **Delivery**: Auslieferungs-Performance
- **Fulfillment**: Gesamt-Performance (Perfect Order Fulfillment)

---

## 6. Bekannte Probleme und Offene Punkte

### 6.1 KW 5 Problem (Volumenplanung)
- **Problem**: KW 5 zeigt 1057 statt 1058 MTB Allrounder
- **Ursache**: Carry-Over-Logik funktioniert nicht korrekt
- **Status**: Offen

### 6.2 Performance
- **Problem**: Lange Ladezeiten (3+ Minuten)
- **Ursache**: HDD-Laufwerk, umfangreiche Berechnungen
- **Status**: Teilweise optimiert (Early-Exit, Caching)

---

## 7. Erweiterungsmöglichkeiten

1. **Weitere Szenarien**: Mehr Szenario-Typen
2. **Mehrere Lieferanten**: Nicht nur China
3. **Multi-Product-Linien**: Mehrere Produktionslinien
4. **Erweiterte Visualisierung**: Mehr Chart-Typen
5. **Export-Funktionalität**: Excel-Export
6. **Historische Daten**: Vergleich mehrerer Simulationen

---

## 8. Deployment und Ausführung

### 8.1 Lokale Ausführung
```bash
streamlit run app.py
```

### 8.2 Requirements
Siehe `requirements.txt`

### 8.3 Konfiguration
- Stammdaten: `config/master_data.py`
- Feiertage: `config/holidays_config.py`

---

**Dokumentation erstellt am**: 2024
**Version**: 1.0
**Autor**: AI Assistant

