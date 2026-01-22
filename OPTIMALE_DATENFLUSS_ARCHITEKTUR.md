# Optimale Datenfluss-Architektur - Grundlage für Szenarien

**Datum:** 2026-01-22  
**Ziel:** Single Source of Truth etablieren, Mehrfachberechnungen eliminieren, Szenarien-Vorbereitung

---

## 🤔 Warum werden Dinge mehrfach berechnet?

### Historische/Technische Gründe

1. **Entwicklungsreihenfolge:**
   - Materiallager und Fertigproduktelager wurden **vor** `production_logs` erstellt
   - Sie mussten Produktionsverteilung selbst berechnen
   - Später wurde `production_logs` hinzugefügt, aber alte Logik blieb bestehen

2. **Unabhängigkeit:**
   - Jede Seite sollte "autonom" funktionieren können
   - Man wollte nicht von anderen Komponenten abhängen
   - **Problem:** Führt zu Inkonsistenzen

3. **Performance-Überlegungen:**
   - Man dachte, direkte Berechnung sei schneller als Lesen aus anderen Quellen
   - **Problem:** `production_logs` sind bereits berechnet, Lesen ist schneller als Neuberechnung

4. **Fehlende Architektur:**
   - Keine klare Definition von "Single Source of Truth"
   - Jede Komponente hat ihre eigene Logik entwickelt
   - **Problem:** Inkonsistenzen sind vorprogrammiert

---

## 🎯 Optimale Datenfluss-Architektur

### Prinzip: Single Source of Truth (SSoT)

**Grundregel:** Jede Information wird **einmal berechnet** und dann **weitergegeben**, nicht neu berechnet.

### Datenfluss-Hierarchie

```
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 1: ROHDATEN (Input)                                  │
│  └─→ Stammdaten (MasterData)                                │
│  └─→ Szenarien (ScenarioManager)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 2: NACHFRAGE (Single Source of Truth)                │
│  └─→ calculate_volume_planning_demand()                     │
│      ├─→ daily_demands_planned (ohne Marketing)            │
│      └─→ daily_demands_actual (mit Marketing)              │
│                                                              │
│  VERWENDET VON:                                              │
│  • Simulator (für Produktionsplanung)                        │
│  • ChinaTransportManager (für Bestelleingang)                │
│  • Volumenplanung-Seite (Anzeige)                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 3: PRODUKTION (Single Source of Truth)               │
│  └─→ ProductionPlanner.plan_daily_production()            │
│      └─→ production_logs[product][day]                     │
│          ├─→ geplante PM                                    │
│          ├─→ tatsächliche PM                                │
│          ├─→ fertiggestellte PM                             │
│          ├─→ Backlog                                        │
│          └─→ Materialverbrauch                              │
│                                                              │
│  VERWENDET VON:                                              │
│  • Materiallager (für Verbrauch pro Satteltyp)               │
│  • Fertigproduktelager (für Produktionsmengen)              │
│  • Reporting (für KPIs)                                     │
│  • Produktion-Seite (Anzeige)                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 4: TRANSPORT (Single Source of Truth)                │
│  └─→ ChinaTransportManager.process_shipments()              │
│      └─→ transport_status[(order_day, order_id)]            │
│          ├─→ quantity (ursprünglich)                        │
│          ├─→ actual_quantity (nach Szenarien)              │
│          ├─→ shipped (verschickt?)                          │
│          └─→ available_day (verfügbar im Lager)             │
│                                                              │
│  VERWENDET VON:                                              │
│  • Supplier-Log (für Warenausgang)                           │
│  • Inbound-Log (für Versandmengen)                          │
│  • Materiallager (für Zugänge)                               │
│  • Simulator (für Wareneingang)                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 5: MATERIALBESTÄNDE (Single Source of Truth)          │
│  └─→ Materiallager.create_saddle_inventory_log()            │
│      └─→ material_inventory_data[date][saddle_type]         │
│          ├─→ Bestand morgens                                │
│          ├─→ Bestand abends                                 │
│          ├─→ Lagerzugang                                    │
│          └─→ Lagerabgang                                    │
│                                                              │
│  VERWENDET VON:                                              │
│  • ProductionPlanner (für Materialverfügbarkeit)             │
│  • Reporting (für Material-KPIs)                            │
│  • Materiallager-Seite (Anzeige)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Konkrete Umsetzung

### 1. ProductionPlanner als Single Source of Truth für Produktion

**Aktuell:**
- Materiallager: Berechnet Produktionsverteilung neu (Zeilen 196-227)
- Fertigproduktelager: Verteilt proportional (Zeile 84)

**Optimal:**
```python
# Materiallager (pages/5_materiallager.py)
def create_saddle_inventory_log():
    # VORHER: Neu berechnen
    # product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
    # production_by_product = {...}  # Neu berechnet
    
    # NACHHER: Aus production_logs lesen
    if 'simulator' in st.session_state and st.session_state.simulator:
        planner = st.session_state.simulator.production_planner
        production_logs = planner.production_logs
        
        for day in range(365):
            production_by_product = {}
            for product in MasterData.BOM.keys():
                if product in production_logs and day < len(production_logs[product]):
                    log_entry = production_logs[product][day]
                    production_by_product[product] = log_entry.get('tatsächliche PM', 0)
                else:
                    production_by_product[product] = 0
            
            # Verwende production_by_product für Verbrauch
```

```python
# Fertigproduktelager (pages/7_fertigproduktelager.py)
def create_finished_goods_log():
    # VORHER: Proportional verteilen
    # product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
    # production_qty = actual_build * product_share
    
    # NACHHER: Aus production_logs lesen
    if 'simulator' in st.session_state and st.session_state.simulator:
        planner = st.session_state.simulator.production_planner
        production_logs = planner.production_logs
        
        for day in range(365):
            for product in MasterData.BOM.keys():
                if product in production_logs and day < len(production_logs[product]):
                    log_entry = production_logs[product][day]
                    production_qty = log_entry.get('tatsächliche PM', 0)
                else:
                    production_qty = 0
```

**Vorteile:**
- ✅ Konsistenz: Alle Seiten zeigen gleiche Produktionsmengen
- ✅ Performance: Keine Neuberechnung nötig
- ✅ Szenarien-ready: Szenarien werden automatisch berücksichtigt (sind bereits in production_logs)

---

### 2. transport_status als Single Source of Truth für Transport

**Aktuell:**
- Supplier-Log: Berechnet Versandmengen neu (Pool-Logik)
- Inbound-Log: Berechnet Versandmengen neu (Pool-Logik)

**Optimal:**
```python
# Supplier-Log (simulation/china_transport.py)
def get_supplier_log_dataframe(self, saddle_name: str, saddle_share: float):
    # VORHER: Pool-Logik + Bestandslogik
    # shipments_today = {...}  # Neu berechnet
    # shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
    
    # NACHHER: Aus transport_status lesen
    for day_idx in range(total_days):
        # Sammle alle Transporte für diesen Tag
        shipments_today = {}
        for (order_day, order_id), status in self.transport_status.items():
            if status.get('ship_departure_day') == day_idx:
                # Berechne Anteil dieses Sattels
                total_qty = status.get('actual_quantity', 0.0)
                shipments_today[saddle_name] = shipments_today.get(saddle_name, 0.0) + total_qty * saddle_share
        
        shipment_qty = shipments_today.get(saddle_name, 0.0)
```

```python
# Inbound-Log (simulation/china_transport.py)
def get_inbound_log_dataframe(self, saddle_shares_dict: Dict[str, float]):
    # VORHER: Pool-Logik (neu berechnen)
    # shipments_today = {...}  # Neu berechnet
    
    # NACHHER: Aus transport_status lesen
    for day_idx in range(total_days):
        # Sammle alle Transporte für diesen Tag
        shipments_today = {}
        for (order_day, order_id), status in self.transport_status.items():
            if status.get('ship_departure_day') == day_idx:
                total_qty = status.get('actual_quantity', 0.0)
                # Verteile auf Satteltypen (basierend auf Shares)
                for s, share in saddle_shares_dict.items():
                    shipments_today[s] = shipments_today.get(s, 0.0) + total_qty * share
```

**Vorteile:**
- ✅ Konsistenz: Beide Tabellen zeigen gleiche Versandmengen
- ✅ Szenarien-ready: Szenarien sind bereits in `actual_quantity` angewendet
- ✅ Performance: Keine Neuberechnung nötig

---

### 3. Materiallager als Single Source of Truth für Materialbestände

**Aktuell:**
- ProductionPlanner: Berechnet Bestände aus Inbound-Tabelle (minus Verbrauch)
- Simulator: Verwendet globalen Pool (`inventory.stock_saddles`)

**Optimal:**
```python
# ProductionPlanner (simulation/production_planner.py)
def _get_all_stocks_from_inbound_table(self, day: int, saddle_shares: Dict[str, float]):
    # VORHER: Liest aus Inbound-Tabelle und reduziert um Verbrauch
    # inbound_stock = ...  # Aus Inbound-Tabelle
    # consumption = self._consumption_by_saddle.get(s_type, 0.0)
    # stock_by_saddle_type[s_type] = max(0.0, inbound_stock - consumption)
    
    # NACHHER: Liest aus Materiallager (Single Source of Truth)
    if 'material_inventory_data' in st.session_state:
        material_inventory_data = st.session_state.material_inventory_data
        target_date = self.workday_calculator.get_date_from_day(day)
        
        # Hole Bestand morgens aus Materiallager
        if target_date in material_inventory_data:
            for saddle_name in saddle_shares.keys():
                stock_by_saddle[saddle_name] = material_inventory_data[target_date].get(saddle_name, 0.0)
        else:
            # Fallback: Suche nächsten verfügbaren Tag
            for date_key in sorted(material_inventory_data.keys()):
                if date_key <= target_date:
                    for saddle_name in saddle_shares.keys():
                        stock_by_saddle[saddle_name] = material_inventory_data[date_key].get(saddle_name, 0.0)
```

```python
# Simulator (simulation/simulator.py)
def _initialize_stock_from_inbound(self):
    # VORHER: Berechnet aus transport_status
    # initial_stock = sum(...)  # Aus transport_status
    
    # NACHHER: Liest aus Materiallager (Single Source of Truth)
    if 'material_inventory_data' in st.session_state:
        material_inventory_data = st.session_state.material_inventory_data
        cutoff_date = date(self.workday_calculator.year - 1, 12, 31)
        
        # Hole Bestand vom letzten Tag des Vorjahres
        if cutoff_date in material_inventory_data:
            initial_stock = sum(material_inventory_data[cutoff_date].values())
        else:
            # Fallback: Suche letzten verfügbaren Tag
            for date_key in sorted(material_inventory_data.keys(), reverse=True):
                if date_key <= cutoff_date:
                    initial_stock = sum(material_inventory_data[date_key].values())
                    break
        self.inventory.stock_saddles = initial_stock
```

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Bestände
- ✅ Szenarien-ready: Materiallager berücksichtigt bereits Szenarien (Wasserschaden)
- ✅ Einfacher: Keine komplexe Verbrauchsberechnung nötig

---

## 🎯 Optimale Architektur für Szenarien

### Szenarien-Integration in Datenfluss

**Prinzip:** Szenarien werden **zentral** angewendet, nicht in jeder Komponente.

```
┌─────────────────────────────────────────────────────────────┐
│  SZENARIEN (ScenarioManager)                                │
│  └─→ Marketingaktion → daily_demands_actual                 │
│  └─→ Wasserschaden → material_inventory_data               │
│  └─→ Lieferantenausfall → transport_status                 │
│  └─→ Lieferprobleme → transport_status.actual_quantity    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DATENFLUSS MIT SZENARIEN                                   │
│                                                              │
│  1. NACHFRAGE:                                              │
│     calculate_volume_planning_demand()                      │
│     └─→ Berücksichtigt Marketingaktion                      │
│     └─→ daily_demands_actual (mit Szenarien)               │
│                                                              │
│  2. PRODUKTION:                                             │
│     ProductionPlanner.plan_daily_production()                │
│     └─→ Verwendet daily_demands_actual (mit Szenarien)     │
│     └─→ production_logs (bereits mit Szenarien)            │
│                                                              │
│  3. TRANSPORT:                                              │
│     ChinaTransportManager.process_shipments()                │
│     └─→ Berücksichtigt Lieferprobleme                       │
│     └─→ transport_status.actual_quantity (mit Szenarien)    │
│                                                              │
│  4. MATERIALBESTÄNDE:                                       │
│     Materiallager.create_saddle_inventory_log()              │
│     └─→ Verwendet production_logs (mit Szenarien)           │
│     └─→ Verwendet transport_status (mit Szenarien)          │
│     └─→ Berücksichtigt Wasserschaden                        │
│     └─→ material_inventory_data (mit Szenarien)             │
└─────────────────────────────────────────────────────────────┘
```

### Szenarien-Anwendung (Zentral)

**Aktuell:**
- Szenarien werden an verschiedenen Stellen angewendet
- Inkonsistente Anwendung

**Optimal:**
```python
# ZENTRALE SZENARIEN-ANWENDUNG

# 1. NACHFRAGE (in calculate_volume_planning_demand)
marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
# → Wird in daily_demands_actual berücksichtigt

# 2. TRANSPORT (in process_shipments)
delivery_problems = scenario_manager.get_delivery_problem_scenarios(day)
# → Wird in transport_status.actual_quantity berücksichtigt

# 3. MATERIALBESTÄNDE (in create_saddle_inventory_log)
warehouse_damages = scenario_manager.get_warehouse_damage_scenarios(day)
# → Wird in material_inventory_data berücksichtigt

# 4. PRODUKTION (in plan_daily_production)
# → Verwendet bereits daily_demands_actual (mit Marketing)
# → Szenarien sind bereits angewendet!
```

**Vorteile:**
- ✅ Konsistenz: Szenarien werden zentral angewendet
- ✅ Einfach: Keine Szenarien-Logik in jeder Komponente
- ✅ Wartbar: Änderungen nur an einer Stelle

---

## 📋 Konkrete Umsetzungsschritte

### Phase 1: ProductionPlanner als SSoT für Produktion

**Änderungen:**

1. **Materiallager** (`pages/5_materiallager.py`):
   ```python
   # VORHER: Neu berechnen (Zeilen 196-227)
   product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
   production_by_product = {...}  # Neu berechnet
   
   # NACHHER: Aus production_logs lesen
   planner = st.session_state.simulator.production_planner
   production_logs = planner.production_logs
   for product in MasterData.BOM.keys():
       if product in production_logs and day < len(production_logs[product]):
           production_by_product[product] = production_logs[product][day].get('tatsächliche PM', 0)
   ```

2. **Fertigproduktelager** (`pages/7_fertigproduktelager.py`):
   ```python
   # VORHER: Proportional (Zeile 84)
   production_qty = actual_build * product_share
   
   # NACHHER: Aus production_logs lesen
   planner = st.session_state.simulator.production_planner
   production_logs = planner.production_logs
   if product in production_logs and day < len(production_logs[product]):
       production_qty = production_logs[product][day].get('tatsächliche PM', 0)
   ```

**Vorteile:**
- ✅ Konsistenz: Alle Seiten zeigen gleiche Produktionsmengen
- ✅ Szenarien-ready: Marketingaktion wird automatisch berücksichtigt
- ✅ Performance: Keine Neuberechnung

---

### Phase 2: transport_status als SSoT für Transport

**Änderungen:**

1. **Supplier-Log** (`simulation/china_transport.py`):
   - Liest Versandmengen aus `transport_status` (nicht neu berechnen)
   - Vereinfachte Bestandslogik (wie bereits vorgeschlagen)

2. **Inbound-Log** (`simulation/china_transport.py`):
   - Liest Versandmengen aus `transport_status` (nicht neu berechnen)
   - Szenarien sind bereits in `actual_quantity` angewendet

**Vorteile:**
- ✅ Konsistenz: Beide Tabellen zeigen gleiche Versandmengen
- ✅ Szenarien-ready: Lieferprobleme werden automatisch berücksichtigt
- ✅ Performance: Keine Neuberechnung

---

### Phase 3: Materiallager als SSoT für Materialbestände

**Änderungen:**

1. **ProductionPlanner** (`simulation/production_planner.py`):
   - Liest Bestände aus Materiallager (nicht neu berechnen)

2. **Simulator** (`simulation/simulator.py`):
   - Synchronisiert `inventory.stock_saddles` mit Materiallager

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Bestände
- ✅ Szenarien-ready: Wasserschaden wird automatisch berücksichtigt
- ✅ Einfacher: Keine komplexe Verbrauchsberechnung

---

## 🎯 Optimale Datenfluss-Architektur (Final)

### Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT                                                      │
│  • MasterData (Stammdaten)                                  │
│  • ScenarioManager (Szenarien)                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE (SSoT)                                  │
│  calculate_volume_planning_demand()                         │
│  └─→ daily_demands_actual (mit Marketing)                  │
│      ↓                                                       │
│      • Simulator (Produktionsplanung)                       │
│      • ChinaTransportManager (Bestelleingang)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 2: PRODUKTION (SSoT)                                 │
│  ProductionPlanner.plan_daily_production()                  │
│  └─→ production_logs[product][day]                          │
│      ↓                                                       │
│      • Materiallager (Verbrauch)                            │
│      • Fertigproduktelager (Produktionsmengen)               │
│      • Reporting (KPIs)                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 3: TRANSPORT (SSoT)                                  │
│  ChinaTransportManager.process_shipments()                  │
│  └─→ transport_status (mit Szenarien)                       │
│      ↓                                                       │
│      • Supplier-Log (Warenausgang)                          │
│      • Inbound-Log (Versandmengen)                          │
│      • Materiallager (Zugänge)                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LEVEL 4: MATERIALBESTÄNDE (SSoT)                          │
│  Materiallager.create_saddle_inventory_log()               │
│  └─→ material_inventory_data (mit Szenarien)                │
│      ↓                                                       │
│      • ProductionPlanner (Materialverfügbarkeit)            │
│      • Reporting (Material-KPIs)                           │
└─────────────────────────────────────────────────────────────┘
```

### Szenarien-Integration

**Prinzip:** Szenarien werden **einmal** angewendet und dann **weitergegeben**.

```
SZENARIEN → DATENQUELLE → ALLE VERBRAUCHER
```

**Beispiel:**
- Marketingaktion → `daily_demands_actual` → Simulator, ProductionPlanner, Materiallager
- Lieferprobleme → `transport_status.actual_quantity` → Supplier-Log, Inbound-Log, Materiallager
- Wasserschaden → `material_inventory_data` → ProductionPlanner, Reporting

**Vorteile:**
- ✅ Konsistenz: Szenarien werden zentral angewendet
- ✅ Einfach: Keine Szenarien-Logik in jeder Komponente
- ✅ Wartbar: Änderungen nur an einer Stelle

---

## 🔧 Konkrete Code-Änderungen

### Änderung 1: Materiallager liest aus production_logs

**Datei:** `pages/5_materiallager.py`

**Vorher (Zeilen 152-227):**
```python
# Neu berechnen
product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
production_by_product = {...}  # Neu berechnet
```

**Nachher:**
```python
# Aus production_logs lesen
production_by_product = {}
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    if hasattr(planner, 'production_logs') and planner.production_logs:
        for product in MasterData.BOM.keys():
            if product in planner.production_logs and day < len(planner.production_logs[product]):
                log_entry = planner.production_logs[product][day]
                production_by_product[product] = log_entry.get('tatsächliche PM', 0)
            else:
                production_by_product[product] = 0
    else:
        # Fallback: Alte Logik (wenn production_logs nicht verfügbar)
        product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
        # ... alte Logik ...
else:
    production_by_product = {product: 0 for product in MasterData.BOM.keys()}
```

---

### Änderung 2: Fertigproduktelager liest aus production_logs

**Datei:** `pages/7_fertigproduktelager.py`

**Vorher (Zeile 84):**
```python
product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
production_qty = actual_build * product_share
```

**Nachher:**
```python
# Aus production_logs lesen
production_qty = 0
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    if hasattr(planner, 'production_logs') and planner.production_logs:
        if product in planner.production_logs and day < len(planner.production_logs[product]):
            log_entry = planner.production_logs[product][day]
            production_qty = log_entry.get('tatsächliche PM', 0)
    else:
        # Fallback: Proportional (wenn production_logs nicht verfügbar)
        product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
        production_qty = actual_build * product_share
```

---

### Änderung 3: Supplier-Log liest aus transport_status

**Datei:** `simulation/china_transport.py`

**Vorher (Zeilen 671-714):**
```python
# Pool-Logik (neu berechnen)
for day_idx in range(total_days):
    shipments_today = {...}  # Neu berechnet
    shipment_results[day_idx] = shipments_today[saddle_name]
```

**Nachher:**
```python
# Aus transport_status lesen
shipment_results = [0.0] * total_days
for (order_day, order_id), status in self.transport_status.items():
    ship_departure_day = status.get('ship_departure_day')
    if ship_departure_day is not None and 0 <= ship_departure_day < total_days:
        # Berechne Anteil dieses Sattels
        total_qty = status.get('actual_quantity', 0.0)
        # Verteile basierend auf Shares (für diesen Sattel)
        saddle_share = saddle_shares_all.get(saddle_name, 0.0)
        shipment_results[ship_departure_day] += total_qty * saddle_share
```

---

### Änderung 4: Inbound-Log liest aus transport_status

**Datei:** `simulation/china_transport.py`

**Vorher (Zeilen 906-963):**
```python
# Pool-Logik (neu berechnen)
for day_idx in range(max_calculation_days):
    shipments_today = {...}  # Neu berechnet
```

**Nachher:**
```python
# Aus transport_status lesen
for day_idx in range(max_calculation_days):
    shipments_today = {s: 0.0 for s in all_saddles}
    curr_date = start_date + timedelta(days=day_idx)
    
    # Sammle alle Transporte für diesen Tag
    for (order_day, order_id), status in self.transport_status.items():
        ship_departure_day = status.get('ship_departure_day')
        if ship_departure_day is not None:
            ship_departure_date = self.workday_calculator.get_date_from_day(ship_departure_day)
            if ship_departure_date == curr_date:
                total_qty = status.get('actual_quantity', 0.0)
                # Verteile auf Satteltypen (basierend auf Shares)
                for s, share in saddle_shares_all.items():
                    shipments_today[s] += total_qty * share
```

---

## ✅ Vorteile der optimalen Architektur

### 1. Konsistenz

- ✅ Alle Seiten zeigen **gleiche Daten**
- ✅ Keine Inkonsistenzen zwischen Tabellen
- ✅ Massenerhaltung garantiert

### 2. Performance

- ✅ Keine Mehrfachberechnungen
- ✅ Daten werden einmal berechnet, dann gelesen
- ✅ Schnellere Seitenwechsel

### 3. Szenarien-Ready

- ✅ Szenarien werden **zentral** angewendet
- ✅ Automatisch in allen abhängigen Komponenten sichtbar
- ✅ Einfach zu erweitern

### 4. Wartbarkeit

- ✅ Änderungen nur an **einer Stelle**
- ✅ Klare Datenfluss-Hierarchie
- ✅ Einfacher zu debuggen

### 5. Testbarkeit

- ✅ Jede Komponente kann isoliert getestet werden
- ✅ Mock-Daten einfach einzubinden
- ✅ Konsistenz-Tests möglich

---

## 🎯 Zusammenfassung

### Warum Mehrfachberechnungen?

1. **Historisch gewachsen:** Komponenten wurden nacheinander entwickelt
2. **Unabhängigkeit:** Jede Komponente sollte autonom funktionieren
3. **Fehlende Architektur:** Keine klare Definition von Single Source of Truth

### Optimale Lösung

**Prinzip:** Daten werden **einmal berechnet** und dann **weitergegeben**, nicht neu berechnet.

**Hierarchie:**
1. Nachfrage → `daily_demands_actual`
2. Produktion → `production_logs`
3. Transport → `transport_status`
4. Materialbestände → `material_inventory_data`

### Konkrete Umsetzung

1. **Materiallager** liest Produktion aus `production_logs`
2. **Fertigproduktelager** liest Produktion aus `production_logs`
3. **Supplier-Log** liest Versandmengen aus `transport_status`
4. **Inbound-Log** liest Versandmengen aus `transport_status`
5. **ProductionPlanner** liest Bestände aus Materiallager

### Szenarien-Vorbereitung

- Szenarien werden **zentral** angewendet
- Automatisch in allen abhängigen Komponenten sichtbar
- Einfach zu erweitern

---

## 📋 Nächste Schritte

1. **Phase 1:** Materiallager und Fertigproduktelager auf `production_logs` umstellen
2. **Phase 2:** Supplier-Log und Inbound-Log auf `transport_status` umstellen
3. **Phase 3:** ProductionPlanner auf Materiallager-Bestände umstellen
4. **Phase 4:** Szenarien zentral anwenden

**Priorität:**
- 🔴 Hoch: Phase 1 (Produktionskonsistenz)
- 🟡 Mittel: Phase 2 (Transportkonsistenz)
- 🟢 Niedrig: Phase 3 (Materialbestands-Konsistenz)
