# Datenfluss-Übersicht: Alle Pages und ihre Datenquellen

**Datum:** 2026-01-22  
**Ziel:** Allgemeine Übersicht des Datenflusses über alle Pages hinweg

---

## 📊 Datenfluss-Diagramm (Gesamtübersicht)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: STAMMDATEN                                                          │
│  └─→ MasterData (BOM, Verkaufsanteile, Saisonalität, etc.)                │
│  └─→ ScenarioManager (Szenarien)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE (Single Source of Truth)                                │
│  └─→ calculate_volume_planning_demand()                                     │
│      ├─→ daily_demands_planned[day][product] (ohne Marketing)            │
│      └─→ daily_demands_actual[day][product] (mit Marketing)                │
│      └─→ Gespeichert in: st.session_state.daily_demands_*                   │
│                                                                              │
│  VERWENDET VON:                                                              │
│  • Page 2: Volumenplanung (Anzeige)                                         │
│  • Page 3: Lieferant China (Bestelleingang)                                 │
│  • Simulator (Produktionsplanung)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: SIMULATION (Simulator.run())                                     │
│  └─→ Verwendet daily_demands_actual für Produktionsplanung                  │
│  └─→ Erstellt:                                                               │
│      ├─→ results_df (Daily_Target, Actual_Build, etc.)                     │
│      ├─→ kpis (service_level, total_demand, total_produced)                │
│      └─→ simulator (ProductionPlanner, ChinaTransportManager, etc.)          │
│      └─→ Gespeichert in: st.session_state.results_df, kpis, simulator      │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: PRODUKTION (Single Source of Truth)                              │
│  └─→ ProductionPlanner.plan_daily_production()                              │
│      └─→ production_logs[product][day]                                     │
│          ├─→ geplante PM                                                    │
│          ├─→ tatsächliche PM                                                │
│          ├─→ fertiggestellte PM                                            │
│          ├─→ Backlog                                                        │
│          ├─→ Materialverbrauch                                             │
│          └─→ Auslastung (%)                                                │
│      └─→ Gespeichert in: simulator.production_planner.production_logs      │
│                                                                              │
│  VERWENDET VON:                                                              │
│  • Page 6: Produktion (Anzeige)                                            │
│  • Page 5: Materiallager (Lagerabgang - SOLLTE verwendet werden)          │
│  • Page 7: Fertigproduktelager (Lagerzugang - SOLLTE verwendet werden)     │
│  • Page 1: Reporting (KPIs)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: TRANSPORT (Single Source of Truth)                               │
│  └─→ ChinaTransportManager.process_shipments()                              │
│      └─→ transport_status[(order_day, order_id)]                            │
│          ├─→ quantity (ursprünglich)                                       │
│          ├─→ actual_quantity (nach Szenarien)                              │
│          ├─→ ship_departure_day                                            │
│          ├─→ ship_arrival_day                                              │
│          ├─→ available_day                                                 │
│          └─→ shipped (verschickt?)                                         │
│      └─→ Gespeichert in: simulator.china_transport_manager.transport_status│
│                                                                              │
│  VERWENDET VON:                                                              │
│  • Page 3: Lieferant China (Warenausgang - SOLLTE verwendet werden)        │
│  • Page 4: Inbound (Versandmengen - SOLLTE verwendet werden)               │
│  • Page 5: Materiallager (Lagerzugang)                                      │
│  • Simulator (Wareneingang)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 5: MATERIALBESTÄNDE (Single Source of Truth)                        │
│  └─→ Materiallager.create_saddle_inventory_log()                            │
│      └─→ material_inventory_data[date][saddle_type]                        │
│          ├─→ Bestand morgens                                               │
│          ├─→ Bestand abends                                                 │
│          ├─→ Lagerzugang                                                   │
│          └─→ Lagerabgang                                                   │
│      └─→ Gespeichert in: st.session_state.material_inventory_data           │
│                                                                              │
│  VERWENDET VON:                                                              │
│  • Page 5: Materiallager (Anzeige)                                          │
│  • Page 1: Reporting (Material-KPIs)                                         │
│  • ProductionPlanner (Materialverfügbarkeit - SOLLTE verwendet werden)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📄 Page-Übersicht: Was wird angezeigt und woher kommen die Daten?

### **Page 1: Reporting** 📊

**Angezeigte Daten:**
1. **KPI-Dashboard Produktion:**
   - Service Level
   - Gesamtnachfrage
   - Gesamtproduktion

2. **KPI-Dashboard Materiallager:**
   - Durchschnittlicher Lagerbestand
   - Tage mit 0 Bestand
   - Minimum/Maximum Lagerbestand
   - Ø Tagesverbrauch
   - Ø Reichweite (Tage)
   - Engpass-Analyse

3. **Produktionsauslastung:**
   - Auslastung über Zeit

**Datenquellen:**
- `st.session_state.kpis` → Service Level, Gesamtnachfrage, Gesamtproduktion
- `st.session_state.material_inventory_data` → Material-KPIs
- `simulator.production_planner.production_logs` → Produktionsauslastung

**Single Source of Truth:**
- ✅ KPIs: `st.session_state.kpis` (berechnet in `Simulator.run()`)
- ✅ Material-KPIs: `st.session_state.material_inventory_data` (berechnet in `Materiallager.create_saddle_inventory_log()`)
- ✅ Produktionsauslastung: `production_logs` (berechnet in `ProductionPlanner.plan_daily_production()`)

---

### **Page 2: Volumenplanung** 📅

**Angezeigte Daten:**
1. **Wöchentliche Volumenplanung:**
   - Kalenderwoche
   - Tägliche Nachfrage (geplant)
   - Tägliche Nachfrage (tatsächlich, mit Marketing)
   - Schichten

2. **Tägliche Volumenplanung:**
   - Datum
   - Wochentag
   - Tägliche Nachfrage (geplant)
   - Tägliche Nachfrage (tatsächlich, mit Marketing)
   - Schichten

**Datenquellen:**
- `calculate_volume_planning_demand()` → Berechnet `daily_demands_planned` und `daily_demands_actual`
- Gespeichert in: `st.session_state.daily_demands_planned` und `st.session_state.daily_demands_actual`

**Single Source of Truth:**
- ✅ **NACHFRAGE:** `st.session_state.daily_demands_actual` (berechnet in `calculate_volume_planning_demand()`)
- ✅ **Marketing:** Wird in `calculate_volume_planning_demand()` berücksichtigt (über `ScenarioManager.get_marketing_scenarios()`)

**Wird verwendet von:**
- Page 3: Lieferant China (Bestelleingang)
- Simulator (Produktionsplanung)

---

### **Page 3: Lieferant China** 🇨🇳

**Angezeigte Daten:**
1. **Supplier-Log (pro Sattel-Typ):**
   - Bestelleingang
   - Freigabedatum
   - Freigegebene Bestellungen
   - Produktionsdatum
   - Produktionsmenge
   - Warenausgang
   - Warenbestand

**Datenquellen:**
- `simulator.china_transport_manager.get_supplier_log_dataframe()`
- **Bestelleingang:** `st.session_state.daily_demands_actual` (aus Volumenplanung)
- **Rest:** `transport_status` (berechnet in `process_shipments()`)

**Single Source of Truth:**
- ✅ **Bestelleingang:** `st.session_state.daily_demands_actual` (aus Volumenplanung)
- ⚠️ **Warenausgang:** Wird derzeit neu berechnet (SOLLTE aus `transport_status` gelesen werden)
- ✅ **Transport-Daten:** `transport_status` (berechnet in `process_shipments()`)

**Probleme:**
- ⚠️ Warenausgang wird derzeit neu berechnet (Pool-Logik), sollte aus `transport_status` gelesen werden

---

### **Page 4: Inbound** 🚢

**Angezeigte Daten:**
1. **Inbound-Log (pro Sattel-Typ):**
   - Abfahrt Schiff 🇨🇳
   - Ankunft Schiff 🇩🇪
   - Geplante Ankunft LKW 🇩🇪
   - Tatsächliche Ankunft LKW 🇩🇪
   - Verfügbar im Lager 🇩🇪

**Datenquellen:**
- `simulator.china_transport_manager.get_inbound_log_dataframe()`
- **Versandmengen:** Wird derzeit neu berechnet (Pool-Logik)

**Single Source of Truth:**
- ⚠️ **Versandmengen:** Wird derzeit neu berechnet (SOLLTE aus `transport_status` gelesen werden)
- ✅ **Transport-Daten:** `transport_status` (berechnet in `process_shipments()`)

**Probleme:**
- ⚠️ Versandmengen werden derzeit neu berechnet (Pool-Logik), sollten aus `transport_status` gelesen werden

---

### **Page 5: Materiallager** 📦

**Angezeigte Daten:**
1. **Materiallager-Log (pro Sattel-Typ):**
   - Lagerzugang
   - Bestand morgens
   - Lagerabgang
   - Bestand abends

**Datenquellen:**
- `create_saddle_inventory_log()` (in `pages/5_materiallager.py`)
- **Lagerzugang:** `transport_status` (über `get_daily_arrival_qty()`)
- **Lagerabgang:** Wird derzeit neu berechnet (SOLLTE aus `production_logs` gelesen werden)

**Single Source of Truth:**
- ✅ **Lagerzugang:** `transport_status` (über `get_daily_arrival_qty()`)
- ⚠️ **Lagerabgang:** Wird derzeit neu berechnet (SOLLTE aus `production_logs` gelesen werden)
- ✅ **Materialbestände:** `st.session_state.material_inventory_data` (berechnet in `create_saddle_inventory_log()`)

**Probleme:**
- ⚠️ Lagerabgang wird derzeit neu berechnet (mit `DemandCalculator`), sollte aus `production_logs` gelesen werden

---

### **Page 6: Produktion** 🏭

**Angezeigte Daten:**
1. **Produktions-Log (pro Produkt):**
   - Geplante PM
   - Tatsächliche PM
   - Fertiggestellte PM
   - Backlog
   - Auslastung (%)
   - Material-Bestände (Frames, Sättel, Gabeln)

**Datenquellen:**
- `simulator.production_planner.production_logs`
- Direkt aus `ProductionPlanner` gelesen

**Single Source of Truth:**
- ✅ **Produktion:** `production_logs` (berechnet in `ProductionPlanner.plan_daily_production()`)
- ✅ **Material-Bestände:** Werden in `ProductionPlanner` berechnet (aus Inbound-Tabelle)

**Wird verwendet von:**
- Page 5: Materiallager (SOLLTE verwendet werden für Lagerabgang)
- Page 7: Fertigproduktelager (SOLLTE verwendet werden für Lagerzugang)
- Page 1: Reporting (KPIs)

---

### **Page 7: Fertigproduktelager** ✅

**Angezeigte Daten:**
1. **Fertigproduktelager-Log (pro Produkt):**
   - Lagerzugang
   - Bestand morgens
   - Lagerabgang
   - Bestand abends

**Datenquellen:**
- `create_finished_goods_log()` (in `pages/7_fertigproduktelager.py`)
- **Lagerzugang:** Wird derzeit proportional verteilt (SOLLTE aus `production_logs` gelesen werden)
- **Lagerabgang:** Just-in-Time (sofort versendet)

**Single Source of Truth:**
- ⚠️ **Lagerzugang:** Wird derzeit proportional verteilt (SOLLTE aus `production_logs` gelesen werden)
- ✅ **Lagerabgang:** Just-in-Time (sofort versendet)

**Probleme:**
- ⚠️ Lagerzugang wird derzeit proportional verteilt (`actual_build * product_share`), sollte aus `production_logs` gelesen werden

---

### **Page 8: Stammdaten** 📋

**Angezeigte Daten:**
1. **Stückliste (BOM):**
   - Endprodukt
   - Rahmen
   - Sattel
   - Gabel

2. **Planung:**
   - Globale Konfiguration
   - Tägliche Arbeitslast
   - Verkaufsanteile
   - Saisonalität

3. **Märkte & Kunden:**
   - Marktverteilung
   - Transitzeiten

4. **Auslieferung:**
   - Auslieferungsparameter

5. **Beschaffung:**
   - Beschaffungsparameter (China)

6. **Feiertage:**
   - Feiertagskonfiguration (DE, CN)

**Datenquellen:**
- `MasterData` (direkt aus `config/master_data.py`)
- `HolidaysConfig` (direkt aus `config/holidays_config.py`)
- Editierbare Stammdaten: `st.session_state.editable_*`

**Single Source of Truth:**
- ✅ **Stammdaten:** `MasterData` (zentrale Konfiguration)
- ✅ **Feiertage:** `HolidaysConfig` (zentrale Konfiguration)
- ✅ **Editierbare Stammdaten:** `st.session_state.editable_*` (wird in `MasterData` gespeichert)

---

## 🔄 Datenfluss-Details pro Page

### **Page 1: Reporting** 📊

```
INPUT:
├─→ st.session_state.kpis
│   └─→ service_level, total_demand, total_produced
│   └─→ Quelle: Simulator.run()
│
├─→ st.session_state.material_inventory_data
│   └─→ Bestände pro Sattel-Typ pro Tag
│   └─→ Quelle: Materiallager.create_saddle_inventory_log()
│
└─→ simulator.production_planner.production_logs
    └─→ Produktionsdaten pro Produkt pro Tag
    └─→ Quelle: ProductionPlanner.plan_daily_production()

OUTPUT:
├─→ KPI-Dashboard Produktion
│   ├─→ Service Level (aus kpis)
│   ├─→ Gesamtnachfrage (aus kpis)
│   └─→ Gesamtproduktion (aus kpis)
│
├─→ KPI-Dashboard Materiallager
│   ├─→ Durchschnittlicher Lagerbestand (aus material_inventory_data)
│   ├─→ Tage mit 0 Bestand (aus material_inventory_data)
│   └─→ Engpass-Analyse (aus material_inventory_data)
│
└─→ Produktionsauslastung
    └─→ Auslastung über Zeit (aus production_logs)
```

---

### **Page 2: Volumenplanung** 📅

```
INPUT:
├─→ MasterData (yearly_volume, PRODUCT_SALES_SHARES, SEASONALITY)
├─→ ScenarioManager (Marketing-Szenarien)
└─→ WorkdayCalculator (Arbeitstage)

PROZESS:
└─→ calculate_volume_planning_demand()
    ├─→ Berechnet daily_demands_planned (ohne Marketing)
    ├─→ Berechnet daily_demands_actual (mit Marketing)
    └─→ Speichert in st.session_state.daily_demands_*

OUTPUT:
├─→ Wöchentliche Volumenplanung
│   └─→ Tägliche Nachfrage (geplant/tatsächlich)
│   └─→ Schichten
│
└─→ Tägliche Volumenplanung
    └─→ Tägliche Nachfrage (geplant/tatsächlich)
    └─→ Schichten

WIRD VERWENDET VON:
├─→ Page 3: Lieferant China (Bestelleingang)
└─→ Simulator (Produktionsplanung)
```

---

### **Page 3: Lieferant China** 🇨🇳

```
INPUT:
├─→ st.session_state.daily_demands_actual
│   └─→ Bestelleingang (aus Volumenplanung)
│
└─→ simulator.china_transport_manager.transport_status
    └─→ Transport-Daten (Warenausgang, etc.)

PROZESS:
└─→ get_supplier_log_dataframe()
    ├─→ Bestelleingang: Aus daily_demands_actual
    ├─→ Freigabedatum: Berechnet
    ├─→ Produktionsdatum: Freigabedatum + 4 chinesische AT
    ├─→ Warenausgang: Wird derzeit neu berechnet (SOLLTE aus transport_status)
    └─→ Warenbestand: Berechnet

OUTPUT:
└─→ Supplier-Log (pro Sattel-Typ)
    ├─→ Bestelleingang ✅ (aus daily_demands_actual)
    ├─→ Freigabedatum ✅
    ├─→ Produktionsdatum ✅
    ├─→ Warenausgang ⚠️ (wird neu berechnet, SOLLTE aus transport_status)
    └─→ Warenbestand ✅
```

---

### **Page 4: Inbound** 🚢

```
INPUT:
└─→ simulator.china_transport_manager.transport_status
    └─→ Transport-Daten (Versandmengen, etc.)

PROZESS:
└─→ get_inbound_log_dataframe()
    ├─→ Versandmengen: Wird derzeit neu berechnet (SOLLTE aus transport_status)
    ├─→ Abfahrt Schiff: Aus transport_status
    ├─→ Ankunft Schiff: Aus transport_status
    └─→ Ankunft LKW: Aus transport_status

OUTPUT:
└─→ Inbound-Log (pro Sattel-Typ)
    ├─→ Abfahrt Schiff 🇨🇳 ✅ (aus transport_status)
    ├─→ Ankunft Schiff 🇩🇪 ✅ (aus transport_status)
    ├─→ Geplante Ankunft LKW 🇩🇪 ✅ (aus transport_status)
    ├─→ Tatsächliche Ankunft LKW 🇩🇪 ✅ (aus transport_status)
    └─→ Verfügbar im Lager 🇩🇪 ✅ (aus transport_status)
```

---

### **Page 5: Materiallager** 📦

```
INPUT:
├─→ simulator.china_transport_manager.transport_status
│   └─→ Lagerzugang (über get_daily_arrival_qty())
│
└─→ simulator.production_planner.production_logs
    └─→ Lagerabgang (SOLLTE verwendet werden, wird derzeit neu berechnet)

PROZESS:
└─→ create_saddle_inventory_log()
    ├─→ Lagerzugang: Aus transport_status ✅
    ├─→ Lagerabgang: Wird derzeit neu berechnet ⚠️ (SOLLTE aus production_logs)
    └─→ Bestand: Berechnet (morgens/abends)

OUTPUT:
└─→ Materiallager-Log (pro Sattel-Typ)
    ├─→ Lagerzugang ✅ (aus transport_status)
    ├─→ Bestand morgens ✅
    ├─→ Lagerabgang ⚠️ (wird neu berechnet, SOLLTE aus production_logs)
    └─→ Bestand abends ✅

WIRD VERWENDET VON:
├─→ Page 1: Reporting (Material-KPIs)
└─→ ProductionPlanner (SOLLTE verwendet werden für Materialverfügbarkeit)
```

---

### **Page 6: Produktion** 🏭

```
INPUT:
├─→ st.session_state.daily_demands_actual
│   └─→ Nachfrage (aus Volumenplanung)
│
└─→ Materialbestände (aus Inbound-Tabelle oder Materiallager)

PROZESS:
└─→ ProductionPlanner.plan_daily_production()
    ├─→ Geplante PM: Aus daily_demands_actual
    ├─→ Tatsächliche PM: Berechnet (mit Materialverfügbarkeit)
    ├─→ Fertiggestellte PM: Berechnet
    ├─→ Backlog: Berechnet
    └─→ Auslastung: Berechnet

OUTPUT:
└─→ production_logs[product][day]
    ├─→ Geplante PM ✅
    ├─→ Tatsächliche PM ✅
    ├─→ Fertiggestellte PM ✅
    ├─→ Backlog ✅
    ├─→ Auslastung (%) ✅
    └─→ Material-Bestände ✅

WIRD VERWENDET VON:
├─→ Page 5: Materiallager (SOLLTE verwendet werden für Lagerabgang)
├─→ Page 7: Fertigproduktelager (SOLLTE verwendet werden für Lagerzugang)
└─→ Page 1: Reporting (KPIs)
```

---

### **Page 7: Fertigproduktelager** ✅

```
INPUT:
└─→ simulator.production_planner.production_logs
    └─→ Produktionsmengen (SOLLTE verwendet werden, wird derzeit proportional verteilt)

PROZESS:
└─→ create_finished_goods_log()
    ├─→ Lagerzugang: Wird derzeit proportional verteilt ⚠️ (SOLLTE aus production_logs)
    ├─→ Lagerabgang: Just-in-Time (sofort versendet)
    └─→ Bestand: Berechnet (morgens/abends)

OUTPUT:
└─→ Fertigproduktelager-Log (pro Produkt)
    ├─→ Lagerzugang ⚠️ (wird proportional verteilt, SOLLTE aus production_logs)
    ├─→ Bestand morgens ✅
    ├─→ Lagerabgang ✅ (Just-in-Time)
    └─→ Bestand abends ✅
```

---

### **Page 8: Stammdaten** 📋

```
INPUT:
├─→ MasterData (direkt aus config/master_data.py)
└─→ HolidaysConfig (direkt aus config/holidays_config.py)

PROZESS:
└─→ Anzeige und Bearbeitung von Stammdaten
    ├─→ Stückliste (BOM)
    ├─→ Planung (Volumen, Kapazität, etc.)
    ├─→ Märkte & Kunden
    ├─→ Auslieferung
    ├─→ Beschaffung
    └─→ Feiertage

OUTPUT:
└─→ Editierbare Stammdaten
    └─→ Gespeichert in st.session_state.editable_*
    └─→ Wird in MasterData gespeichert (bei Änderung)
```

---

## ⚠️ Aktuelle Probleme (Inkonsistenzen)

### **Problem 1: Materiallager berechnet Produktion neu**

**Aktuell:**
- Materiallager berechnet Produktionsverteilung neu (mit `DemandCalculator`)
- Sollte aus `production_logs` lesen

**Auswirkung:**
- Inkonsistente Produktionsverteilung zwischen Materiallager und Produktion-Seite
- Materiallager zeigt falschen Verbrauch pro Satteltyp

**Fix:**
- Materiallager sollte `production_logs` verwenden (Single Source of Truth)

---

### **Problem 2: Fertigproduktelager verteilt proportional**

**Aktuell:**
- Fertigproduktelager verteilt Produktion proportional (`actual_build * product_share`)
- Sollte aus `production_logs` lesen

**Auswirkung:**
- Inkonsistente Produktionsverteilung zwischen Fertigproduktelager und Produktion-Seite
- Fertigproduktelager zeigt falsche Produktionsmengen

**Fix:**
- Fertigproduktelager sollte `production_logs` verwenden (Single Source of Truth)

---

### **Problem 3: Supplier-Log berechnet Warenausgang neu**

**Aktuell:**
- Supplier-Log berechnet Warenausgang neu (Pool-Logik)
- Sollte aus `transport_status` lesen

**Auswirkung:**
- Inkonsistente Versandmengen zwischen Supplier-Log und Inbound-Log
- Supplier-Log zeigt falsche Warenausgang-Mengen

**Fix:**
- Supplier-Log sollte `transport_status` verwenden (Single Source of Truth)

---

### **Problem 4: Inbound-Log berechnet Versandmengen neu**

**Aktuell:**
- Inbound-Log berechnet Versandmengen neu (Pool-Logik)
- Sollte aus `transport_status` lesen

**Auswirkung:**
- Inkonsistente Versandmengen zwischen Inbound-Log und Supplier-Log
- Inbound-Log zeigt falsche Versandmengen

**Fix:**
- Inbound-Log sollte `transport_status` verwenden (Single Source of Truth)

---

## ✅ Optimale Datenfluss-Architektur (Ziel)

### **Single Source of Truth pro Daten-Domäne:**

1. **Nachfrage:**
   - `st.session_state.daily_demands_actual` (berechnet in `calculate_volume_planning_demand()`)
   - Verwendet von: Volumenplanung, Lieferant China, Simulator

2. **Produktion:**
   - `simulator.production_planner.production_logs` (berechnet in `ProductionPlanner.plan_daily_production()`)
   - Verwendet von: Produktion, Materiallager, Fertigproduktelager, Reporting

3. **Transport:**
   - `simulator.china_transport_manager.transport_status` (berechnet in `process_shipments()`)
   - Verwendet von: Lieferant China, Inbound, Materiallager, Simulator

4. **Materialbestände:**
   - `st.session_state.material_inventory_data` (berechnet in `Materiallager.create_saddle_inventory_log()`)
   - Verwendet von: Materiallager, Reporting, ProductionPlanner

---

## 📋 Zusammenfassung

### **Datenfluss-Prinzip:**

**Single Source of Truth:**
- Jede Information wird **einmal berechnet** und dann **weitergegeben**
- Nicht neu berechnen, sondern aus der Quelle lesen

### **Aktuelle Situation:**

**✅ Konsistent:**
- Page 2: Volumenplanung (berechnet Nachfrage)
- Page 6: Produktion (berechnet Produktion)
- Page 8: Stammdaten (zeigt Stammdaten)

**⚠️ Inkonsistent (wird neu berechnet):**
- Page 3: Lieferant China (Warenausgang wird neu berechnet)
- Page 4: Inbound (Versandmengen werden neu berechnet)
- Page 5: Materiallager (Lagerabgang wird neu berechnet)
- Page 7: Fertigproduktelager (Lagerzugang wird proportional verteilt)

### **Ziel:**

**Alle Pages sollten aus Single Source of Truth lesen:**
- Page 3 & 4: Aus `transport_status` lesen
- Page 5 & 7: Aus `production_logs` lesen
- Page 1: Aus `kpis`, `material_inventory_data`, `production_logs` lesen

---

## 🎯 Nächste Schritte

1. **Phase 1:** Materiallager und Fertigproduktelager auf `production_logs` umstellen
2. **Phase 2:** Supplier-Log und Inbound-Log auf `transport_status` umstellen
3. **Phase 3:** ProductionPlanner auf Materiallager-Bestände umstellen

**Ergebnis:**
- ✅ Konsistenz: Alle Pages zeigen gleiche Daten
- ✅ Performance: Keine Mehrfachberechnungen
- ✅ Szenarien-ready: Szenarien werden automatisch weitergegeben
