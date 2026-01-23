# Szenarien-Implementierung: Theoretische Analyse für flächendeckende Funktionalität

**Datum:** 2026-01-22  
**Ziel:** Theoretische Analyse, wie jedes Szenario in der aktuellen Datenflusslogik flächendeckend implementiert werden sollte

---

## 📋 Übersicht: Alle Szenarien

| Szenario | Typ | Betroffene Komponente | Aktueller Status |
|----------|-----|----------------------|------------------|
| **Marketingaktion** | Nachfrage | Volumenplanung, Simulator | ✅ Teilweise implementiert |
| **Wasserschaden** | Materialbestände | Simulator, Materiallager | ⚠️ Inkonsistent |
| **Lieferantenausfall** | Bestellungen | ProcurementManager, ChinaTransportManager | ✅ Teilweise implementiert |
| **Lieferprobleme** | Transport | ChinaTransportManager | ⚠️ Inkonsistent |

---

## 🎯 SZENARIO 1: Marketingaktion (MarketingCampaignScenario)

### **Beschreibung:**
- **Zweck:** Erhöht die Nachfrage für einen Zeitraum um einen Faktor (z.B. 1.5 = 50% mehr)
- **Parameter:** `demand_increase_factor` (z.B. 1.5)
- **Zeitraum:** `start_day` bis `end_day`

### **Aktueller Implementierungsstand:**

#### ✅ **Wo es bereits funktioniert:**

1. **Volumenplanung** (`ui/volume_planning_utils.py`, Zeilen 68-81):
   ```python
   marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
   if marketing_scenarios:
       for scenario in marketing_scenarios:
           factor = scenario.demand_increase_factor
           add_on = base_float * (factor - 1.0)
           marketing_add_ons[product] += add_on
   ```
   - ✅ Wird in `daily_demands_actual` berücksichtigt
   - ✅ Gespeichert in `st.session_state.daily_demands_actual`

2. **Simulator** (`simulation/simulator.py`, Zeilen 240-267):
   ```python
   marketing_scenarios = self.scenario_manager.get_marketing_scenarios(day)
   if marketing_scenarios:
       for scenario in marketing_scenarios:
           add_on = base_float * (factor - 1.0)
           marketing_add_ons[product] += add_on
   ```
   - ✅ Wird in Produktionsplanung berücksichtigt
   - ✅ Verwendet `daily_demands_actual` (mit Marketing)

3. **ProductionPlanner** (`simulation/production_planner.py`):
   - ✅ Verwendet `daily_demands_actual` (mit Marketing bereits enthalten)
   - ✅ Marketing wird automatisch in Produktionsplanung berücksichtigt

4. **Page 2: Volumenplanung** (`pages/2_volumenplanung.py`, Zeilen 118-135):
   - ✅ Zeigt Nachfrage mit Marketing (wenn `include_marketing=True`)

---

#### ⚠️ **Wo es fehlt oder inkonsistent ist:**

1. **Materiallager** (`pages/5_materiallager.py`, Zeilen 159-198):
   ```python
   # PROBLEM: Berechnet Nachfrage NEU (ohne Marketing)
   product_demands = demand_calc.calculate_daily_demand_per_product_dict(
       day, {}, is_last_workday_of_year=is_last_workday
   )
   # Marketing wird IGNORIERT!
   ```
   - ❌ Berechnet Nachfrage **neu** (ohne Marketing)
   - ❌ Verwendet `DemandCalculator` direkt (ignoriert `daily_demands_actual`)
   - ❌ Marketing wird **nicht** berücksichtigt

2. **Fertigproduktelager** (`pages/7_fertigproduktelager.py`):
   - ⚠️ Verwendet `actual_build` (aus `results_df`)
   - ⚠️ Marketing ist bereits in `actual_build` enthalten (indirekt)
   - ⚠️ Aber: Verteilungslogik könnte Marketing ignorieren

---

### **Theoretische Implementierung für flächendeckende Funktionalität:**

#### **Prinzip: Single Source of Truth**

**Marketingaktion sollte nur EINMAL angewendet werden:**
- ✅ In `calculate_volume_planning_demand()` → `daily_demands_actual`
- ✅ Alle anderen Komponenten sollten aus `daily_demands_actual` **lesen** (nicht neu berechnen)

---

#### **Schritt 1: Materiallager liest aus Single Source of Truth**

**Aktuell:**
```python
# pages/5_materiallager.py (Zeilen 159-198)
product_demands = demand_calc.calculate_daily_demand_per_product_dict(
    day, {}, is_last_workday_of_year=is_last_workday
)
# Marketing wird IGNORIERT!
```

**Optimal:**
```python
# pages/5_materiallager.py
# Liest aus Single Source of Truth (mit Marketing bereits enthalten)
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]  # Marketing bereits enthalten!
else:
    # Fallback: Alte Logik (wenn nicht verfügbar)
    product_demands = demand_calc.calculate_daily_demand_per_product_dict(
        day, {}, is_last_workday_of_year=is_last_workday
    )
```

**Vorteile:**
- ✅ Marketing wird automatisch berücksichtigt
- ✅ Konsistenz: Materiallager sieht gleiche Nachfrage wie Volumenplanung
- ✅ Keine Code-Duplikation (Marketing-Logik nur einmal)

---

#### **Schritt 2: Fertigproduktelager liest aus ProductionPlanner**

**Aktuell:**
```python
# pages/7_fertigproduktelager.py (Zeile 84)
production_qty = actual_build * product_share  # Proportional
# Marketing ist indirekt enthalten, aber Verteilung könnte abweichen
```

**Optimal:**
```python
# pages/7_fertigproduktelager.py
# Liest aus Single Source of Truth (mit Marketing bereits enthalten)
planner = st.session_state.simulator.production_planner
production_logs = planner.production_logs

if product in production_logs and day < len(production_logs[product]):
    log_entry = production_logs[product][day]
    production_qty = log_entry.get('tatsächliche PM', 0)  # Marketing bereits enthalten!
else:
    # Fallback: Alte Logik (wenn nicht verfügbar)
    production_qty = actual_build * product_share
```

**Vorteile:**
- ✅ Marketing wird automatisch berücksichtigt
- ✅ Konsistenz: Fertigproduktelager sieht gleiche Produktion wie ProductionPlanner
- ✅ Exakte Verteilung (nicht proportional)

---

#### **Schritt 3: Reporting liest aus Single Source of Truth**

**Aktuell:**
```python
# pages/1_reporting.py
# Verwendet bereits kpis (aus Simulator)
# Marketing ist bereits enthalten (indirekt)
```

**Optimal:**
```python
# pages/1_reporting.py
# Liest aus Single Source of Truth
daily_demands_actual = st.session_state.get('daily_demands_actual', {})
total_demand = sum(
    sum(product_demands.values())
    for product_demands in daily_demands_actual.values()
)
# Marketing bereits enthalten!
```

**Vorteile:**
- ✅ Konsistenz: Reporting zeigt gleiche Nachfrage wie Volumenplanung
- ✅ Marketing wird automatisch berücksichtigt

---

### **Datenfluss-Diagramm (Optimal):**

```
Marketingaktion (Szenario)
    ↓
calculate_volume_planning_demand()
    ↓
daily_demands_actual (mit Marketing) ✅ Single Source of Truth
    ↓
    ├─→ Simulator (Produktionsplanung) ✅
    ├─→ ProductionPlanner (Produktionsplanung) ✅
    ├─→ Page 2: Volumenplanung (Anzeige) ✅
    ├─→ Page 3: Lieferant China (Bestelleingang) ✅
    ├─→ Page 5: Materiallager (Nachfrage) ← NEU: Liest statt neu zu berechnen
    ├─→ Page 7: Fertigproduktelager (Produktion) ← NEU: Liest aus production_logs
    └─→ Page 1: Reporting (KPIs) ← NEU: Liest aus daily_demands_actual
```

---

### **Zusammenfassung: Marketingaktion**

| Komponente | Aktuell | Optimal | Status |
|------------|---------|---------|--------|
| **Volumenplanung** | ✅ Implementiert | ✅ Single Source of Truth | ✅ Fertig |
| **Simulator** | ✅ Implementiert | ✅ Liest aus daily_demands_actual | ✅ Fertig |
| **ProductionPlanner** | ✅ Implementiert | ✅ Liest aus daily_demands_actual | ✅ Fertig |
| **Materiallager** | ❌ Berechnet neu | ✅ Liest aus daily_demands_actual | ⏳ Zu implementieren |
| **Fertigproduktelager** | ⚠️ Proportional | ✅ Liest aus production_logs | ⏳ Zu implementieren |
| **Reporting** | ⚠️ Indirekt | ✅ Liest aus daily_demands_actual | ⏳ Zu implementieren |

---

## 🎯 SZENARIO 2: Wasserschaden (WarehouseDamageScenario)

### **Beschreibung:**
- **Zweck:** Reduziert Lagerbestand (z.B. Sättel werden beschädigt)
- **Parameter:** `stock_loss_percentage` (z.B. 0.5 = 50% Verlust), `affected_component` (z.B. "saddles")
- **Zeitraum:** `start_day` bis `end_day`

### **Aktueller Implementierungsstand:**

#### ✅ **Wo es bereits funktioniert:**

1. **Simulator** (`simulation/simulator.py`, Zeilen 201-207):
   ```python
   warehouse_damages = self.scenario_manager.get_warehouse_damage_scenarios(day)
   for scenario in warehouse_damages:
       if scenario.affected_component == "saddles":
           loss_amount = self.inventory.stock_saddles * scenario.stock_loss_percentage
           self.inventory.stock_saddles -= loss_amount
   ```
   - ✅ Wird **direkt** im Simulator angewendet
   - ✅ Reduziert `inventory.stock_saddles` (globaler Pool)

---

#### ⚠️ **Wo es fehlt oder inkonsistent ist:**

1. **Materiallager** (`pages/5_materiallager.py`):
   ```python
   # PROBLEM: Berechnet Bestände NEU (ohne Wasserschaden)
   stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
   # Wasserschaden wird IGNORIERT!
   ```
   - ❌ Berechnet Bestände **neu** (ohne Wasserschaden)
   - ❌ Liest aus Inbound-Tabelle (sieht Wasserschaden nicht)
   - ❌ Wasserschaden wird **nicht** berücksichtigt

2. **ProductionPlanner** (`simulation/production_planner.py`, Zeilen 507-577):
   ```python
   # PROBLEM: Berechnet Bestände NEU (aus Inbound-Tabelle)
   inbound_stock = self._get_all_stocks_from_inbound_table(day, saddle_shares)
   # Wasserschaden wird IGNORIERT!
   ```
   - ❌ Berechnet Bestände **neu** (aus Inbound-Tabelle)
   - ❌ Wasserschaden wird **nicht** berücksichtigt
   - ❌ Sieht andere Bestände als Simulator

3. **Reporting** (`pages/1_reporting.py`):
   - ⚠️ Zeigt Material-KPIs (aus Materiallager)
   - ⚠️ Wasserschaden wird möglicherweise nicht berücksichtigt

---

### **Theoretische Implementierung für flächendeckende Funktionalität:**

#### **Prinzip: Zwei-Phasen-Ansatz**

**Problem:** Zirkuläre Abhängigkeit
- ProductionPlanner benötigt Materialbestände **während** Simulation
- Materiallager berechnet Bestände **nach** Simulation
- Wasserschaden wird **während** Simulation angewendet (im Simulator)

**Lösung:** Zwei-Phasen-Ansatz

---

#### **Phase A: Simulation (Wasserschaden wird angewendet)**

**Aktuell:**
```python
# simulation/simulator.py (Zeilen 201-207)
warehouse_damages = self.scenario_manager.get_warehouse_damage_scenarios(day)
for scenario in warehouse_damages:
    if scenario.affected_component == "saddles":
        loss_amount = self.inventory.stock_saddles * scenario.stock_loss_percentage
        self.inventory.stock_saddles -= loss_amount
```

**Optimal:**
```python
# simulation/simulator.py
# Wasserschaden wird ZUERST angewendet (vor Produktion)
warehouse_damages = self.scenario_manager.get_warehouse_damage_scenarios(day)
for scenario in warehouse_damages:
    if scenario.affected_component == "saddles":
        loss_amount = self.inventory.stock_saddles * scenario.stock_loss_percentage
        self.inventory.stock_saddles -= loss_amount
        
        # WICHTIG: Speichere Wasserschaden-Info für Materiallager
        if not hasattr(self, 'warehouse_damages_log'):
            self.warehouse_damages_log = {}
        if day not in self.warehouse_damages_log:
            self.warehouse_damages_log[day] = []
        self.warehouse_damages_log[day].append({
            'component': scenario.affected_component,
            'loss_percentage': scenario.stock_loss_percentage,
            'loss_amount': loss_amount
        })
```

**Vorteile:**
- ✅ Wasserschaden wird **zentral** angewendet (im Simulator)
- ✅ Info wird für Materiallager gespeichert

---

#### **Phase B: Materiallager-Berechnung (Wasserschaden wird berücksichtigt)**

**Aktuell:**
```python
# pages/5_materiallager.py
# Berechnet Bestände NEU (ohne Wasserschaden)
stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
```

**Optimal:**
```python
# pages/5_materiallager.py
# Liest Wasserschaden-Info aus Simulator
simulator = st.session_state.get('simulator', None)
warehouse_damages_log = getattr(simulator, 'warehouse_damages_log', {})

# Berechne Bestände (wie bisher)
stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)

# Wende Wasserschaden an (wenn vorhanden)
if current_date in warehouse_damages_log:
    for damage in warehouse_damages_log[current_date]:
        if damage['component'] == 'saddles':
            # Reduziere Bestand um Verlust
            loss_amount = stock_morning[s] * damage['loss_percentage']
            stock_morning[s] -= loss_amount
            # Optional: Speichere Verlust für Anzeige
            damage_log_entry = {
                'date': current_date,
                'component': damage['component'],
                'loss_percentage': damage['loss_percentage'],
                'loss_amount': loss_amount
            }
```

**Vorteile:**
- ✅ Wasserschaden wird **konsistent** angewendet (wie im Simulator)
- ✅ Materiallager zeigt korrekte Bestände (mit Wasserschaden)

---

#### **Phase C: ProductionPlanner liest aus Materiallager (optional, für nächste Simulation)**

**Aktuell:**
```python
# simulation/production_planner.py (Zeilen 507-577)
# Berechnet Bestände NEU (aus Inbound-Tabelle)
inbound_stock = self._get_all_stocks_from_inbound_table(day, saddle_shares)
```

**Optimal:**
```python
# simulation/production_planner.py
# Liest aus Materiallager (wenn verfügbar, sonst Fallback)
material_inventory_data = st.session_state.get('material_inventory_data', {})
if material_inventory_data and target_date in material_inventory_data:
    # Liest aus Single Source of Truth (mit Wasserschaden bereits berücksichtigt)
    stock_by_saddle_type = material_inventory_data[target_date]
else:
    # Fallback: Alte Logik (aus Inbound-Tabelle)
    inbound_stock = self._get_all_stocks_from_inbound_table(day, saddle_shares)
```

**Vorteile:**
- ✅ ProductionPlanner sieht korrekte Bestände (mit Wasserschaden)
- ✅ Konsistenz: ProductionPlanner und Materiallager sehen gleiche Bestände

---

### **Datenfluss-Diagramm (Optimal):**

```
Wasserschaden (Szenario)
    ↓
Simulator.run() (Tag X)
    ↓
inventory.stock_saddles (reduziert) ✅ Single Source of Truth (während Simulation)
    ↓
warehouse_damages_log (gespeichert) ✅ Info für Materiallager
    ↓
Materiallager.create_saddle_inventory_log() (nach Simulation)
    ↓
material_inventory_data (mit Wasserschaden) ✅ Single Source of Truth (nach Simulation)
    ↓
    ├─→ Page 5: Materiallager (Anzeige) ✅
    ├─→ Page 1: Reporting (Material-KPIs) ✅
    └─→ ProductionPlanner (Materialverfügbarkeit) ← NEU: Liest aus material_inventory_data
```

---

### **Zusammenfassung: Wasserschaden**

| Komponente | Aktuell | Optimal | Status |
|------------|---------|---------|--------|
| **Simulator** | ✅ Implementiert | ✅ Wende Wasserschaden an + speichere Info | ✅ Fertig (kleine Anpassung) |
| **Materiallager** | ❌ Ignoriert Wasserschaden | ✅ Liest Info aus Simulator + wendet an | ⏳ Zu implementieren |
| **ProductionPlanner** | ❌ Ignoriert Wasserschaden | ✅ Liest aus material_inventory_data | ⏳ Zu implementieren |
| **Reporting** | ⚠️ Indirekt | ✅ Liest aus material_inventory_data | ⏳ Zu implementieren |

---

## 🎯 SZENARIO 3: Lieferantenausfall (SupplierBreakdownScenario)

### **Beschreibung:**
- **Zweck:** Stoppt Lieferungen (Maschinenausfall beim Lieferanten in China)
- **Parameter:** `component_type` (z.B. "saddles", "all")
- **Zeitraum:** `start_day` bis `end_day`

### **Aktueller Implementierungsstand:**

#### ✅ **Wo es bereits funktioniert:**

1. **Simulator** (`simulation/simulator.py`, Zeilen 230-234):
   ```python
   supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day)
   supplier_blocked_saddles = any(
       s.component_type in ['saddles', 'all'] for s in supplier_breakdowns
   )
   ```
   - ✅ Wird geprüft (für neue Bestellungen)

2. **ProcurementManager** (`simulation/procurement_manager.py`):
   - ⚠️ Wird möglicherweise verwendet (muss geprüft werden)

3. **ChinaTransportManager** (`simulation/china_transport.py`, `process_shipments()`):
   - ⚠️ Wird möglicherweise verwendet (muss geprüft werden)

---

#### ⚠️ **Wo es fehlt oder inkonsistent ist:**

1. **Supplier-Log** (`simulation/china_transport.py`, `get_supplier_log_dataframe()`):
   ```python
   # PROBLEM: Lieferantenausfall wird NICHT berücksichtigt
   # Berechnet Bestelleingang, Freigabedatum, etc. ohne Prüfung
   ```
   - ❌ Lieferantenausfall wird **nicht** berücksichtigt
   - ❌ Zeigt Bestelleingang auch bei Lieferantenausfall

2. **Inbound-Log** (`simulation/china_transport.py`, `get_inbound_log_dataframe()`):
   ```python
   # PROBLEM: Lieferantenausfall wird NICHT berücksichtigt
   # Berechnet Versandmengen ohne Prüfung
   ```
   - ❌ Lieferantenausfall wird **nicht** berücksichtigt
   - ❌ Zeigt Versandmengen auch bei Lieferantenausfall

---

### **Theoretische Implementierung für flächendeckende Funktionalität:**

#### **Prinzip: Blockierung von neuen Bestellungen**

**Lieferantenausfall sollte:**
- ✅ **Neue Bestellungen blockieren** (während Ausfall)
- ✅ **Bereits unterwegs befindliche Ware** weiter transportieren (nicht blockieren)
- ✅ **In allen Tabellen sichtbar sein** (Bestelleingang = 0, Freigabedatum = None, etc.)

---

#### **Schritt 1: ProcurementManager blockiert neue Bestellungen**

**Aktuell:**
```python
# simulation/procurement_manager.py
# Muss geprüft werden, ob Lieferantenausfall berücksichtigt wird
```

**Optimal:**
```python
# simulation/procurement_manager.py
def should_place_order(self, day: int, component_type: str) -> bool:
    """Prüft, ob eine Bestellung platziert werden sollte"""
    # Prüfe Lieferantenausfall
    if self.scenario_manager:
        supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day)
        for scenario in supplier_breakdowns:
            if scenario.component_type in [component_type, 'all']:
                return False  # Blockiert!
    return True  # Kein Ausfall, Bestellung möglich
```

**Vorteile:**
- ✅ Neue Bestellungen werden blockiert (während Ausfall)
- ✅ Bereits unterwegs befindliche Ware wird weiter transportiert

---

#### **Schritt 2: Supplier-Log zeigt Lieferantenausfall**

**Aktuell:**
```python
# simulation/china_transport.py (get_supplier_log_dataframe)
# Berechnet Bestelleingang, Freigabedatum, etc. ohne Prüfung
```

**Optimal:**
```python
# simulation/china_transport.py (get_supplier_log_dataframe)
# Prüfe Lieferantenausfall für jeden Tag
supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day_index)
supplier_blocked = any(
    s.component_type in ['saddles', 'all'] for s in supplier_breakdowns
)

if supplier_blocked:
    # Keine neuen Bestellungen möglich
    bestelleingang = 0
    freigabedatum = None
    freigegebene_bestellungen = 0
    produktionsdatum = None
    produktionsmenge = 0
    warenausgang = 0
    warenbestand = previous_stock  # Bleibt unverändert
else:
    # Normale Berechnung (wie bisher)
    bestelleingang = daily_demands_actual.get(day, {}).get('total', 0)
    # ... Rest der Berechnung
```

**Vorteile:**
- ✅ Lieferantenausfall wird **sichtbar** (Bestelleingang = 0)
- ✅ Konsistenz: Supplier-Log zeigt korrekte Daten

---

#### **Schritt 3: Inbound-Log zeigt Lieferantenausfall**

**Aktuell:**
```python
# simulation/china_transport.py (get_inbound_log_dataframe)
# Berechnet Versandmengen ohne Prüfung
```

**Optimal:**
```python
# simulation/china_transport.py (get_inbound_log_dataframe)
# Prüfe Lieferantenausfall für jeden Tag
supplier_breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(day_index)
supplier_blocked = any(
    s.component_type in ['saddles', 'all'] for s in supplier_breakdowns
)

if supplier_blocked:
    # Keine neuen Versandmengen (bereits unterwegs befindliche Ware wird weiter transportiert)
    # Versandmengen = 0 (nur für neue Bestellungen)
    shipments_today = {s: 0.0 for s in all_saddles}
else:
    # Normale Berechnung (wie bisher)
    # ... Pool-Logik
```

**Vorteile:**
- ✅ Lieferantenausfall wird **sichtbar** (Versandmengen = 0 für neue Bestellungen)
- ✅ Bereits unterwegs befindliche Ware wird weiter transportiert

---

### **Datenfluss-Diagramm (Optimal):**

```
Lieferantenausfall (Szenario)
    ↓
ProcurementManager.should_place_order()
    ↓
Neue Bestellungen = 0 (blockiert) ✅
    ↓
transport_status (keine neuen Bestellungen) ✅
    ↓
    ├─→ Supplier-Log (Bestelleingang = 0) ← NEU: Zeigt Lieferantenausfall
    ├─→ Inbound-Log (Versandmengen = 0) ← NEU: Zeigt Lieferantenausfall
    └─→ Bereits unterwegs befindliche Ware (wird weiter transportiert) ✅
```

---

### **Zusammenfassung: Lieferantenausfall**

| Komponente | Aktuell | Optimal | Status |
|------------|---------|---------|--------|
| **Simulator** | ✅ Geprüft | ✅ Blockiert neue Bestellungen | ✅ Fertig |
| **ProcurementManager** | ⚠️ Unklar | ✅ Blockiert neue Bestellungen | ⏳ Zu prüfen/implementieren |
| **Supplier-Log** | ❌ Ignoriert | ✅ Zeigt Lieferantenausfall | ⏳ Zu implementieren |
| **Inbound-Log** | ❌ Ignoriert | ✅ Zeigt Lieferantenausfall | ⏳ Zu implementieren |

---

## 🎯 SZENARIO 4: Lieferprobleme (DeliveryProblemScenario)

### **Beschreibung:**
- **Zweck:** Verlust und/oder Verspätung beim Transport (Container über Bord, Verspätung)
- **Parameter:** `loss_percentage` (z.B. 0.1 = 10% Verlust), `delay_days` (z.B. 5 = 5 Tage Verspätung)
- **Zeitraum:** `start_day` bis `end_day`

### **Aktueller Implementierungsstand:**

#### ✅ **Wo es bereits funktioniert:**

1. **process_shipments()** (`simulation/china_transport.py`, Zeilen 182-193):
   ```python
   delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(ship_departure_day)
   for scenario in delivery_problems:
       if scenario.component_type == 'saddles':
           delay_days = max(delay_days, scenario.delay_days)
           loss_factor *= (1.0 - scenario.loss_percentage)
   ```
   - ✅ Wird **korrekt** angewendet (Verluste und Verspätungen)
   - ✅ `actual_quantity` wird reduziert
   - ✅ `ship_arrival_day` wird verzögert

---

#### ⚠️ **Wo es fehlt oder inkonsistent ist:**

1. **Supplier-Log** (`simulation/china_transport.py`, `get_supplier_log_dataframe()`, Zeilen 755-764):
   ```python
   # PROBLEM: Nur 100% Verlust wird berücksichtigt
   if scenario.loss_percentage >= 1.0:
       shipment_qty = 0  # Nur 100% Verlust
   # Teilweise Verluste werden IGNORIERT!
   ```
   - ❌ Nur **100% Verlust** wird berücksichtigt
   - ❌ **Teilweise Verluste** werden ignoriert
   - ❌ **Verspätungen** werden ignoriert

2. **Inbound-Log** (`simulation/china_transport.py`, `get_inbound_log_dataframe()`):
   ```python
   # PROBLEM: KEINE Szenarien-Berücksichtigung
   # Berechnet Versandmengen ohne Verluste/Verspätungen
   ```
   - ❌ **KEINE** Szenarien-Berücksichtigung
   - ❌ Zeigt immer die volle geplante Versandmenge
   - ❌ Verluste und Verspätungen werden ignoriert

---

### **Theoretische Implementierung für flächendeckende Funktionalität:**

#### **Prinzip: Single Source of Truth**

**Lieferprobleme sollten nur EINMAL angewendet werden:**
- ✅ In `process_shipments()` → `transport_status.actual_quantity` (mit Verlusten)
- ✅ Alle anderen Komponenten sollten aus `transport_status` **lesen** (nicht neu berechnen)

---

#### **Schritt 1: Supplier-Log liest aus Single Source of Truth**

**Aktuell:**
```python
# simulation/china_transport.py (get_supplier_log_dataframe, Zeilen 755-764)
# Nur 100% Verlust wird berücksichtigt
if scenario.loss_percentage >= 1.0:
    shipment_qty = 0
```

**Optimal:**
```python
# simulation/china_transport.py (get_supplier_log_dataframe)
# Liest aus Single Source of Truth (transport_status)
# Berechnet Warenausgang aus transport_status (mit Verlusten bereits berücksichtigt)
for (order_day, order_id), status in self.transport_status.items():
    if status.get('ship_departure_day') == day:
        # Liest actual_quantity (mit Verlusten bereits berücksichtigt)
        shipment_qty = status.get('actual_quantity', status.get('quantity', 0.0))
        # Verspätungen sind bereits in ship_arrival_day berücksichtigt
```

**Vorteile:**
- ✅ Lieferprobleme werden automatisch berücksichtigt (aus `transport_status`)
- ✅ Konsistenz: Supplier-Log zeigt gleiche Mengen wie `process_shipments()`
- ✅ Keine Code-Duplikation (Szenarien-Logik nur einmal)

---

#### **Schritt 2: Inbound-Log liest aus Single Source of Truth**

**Aktuell:**
```python
# simulation/china_transport.py (get_inbound_log_dataframe)
# KEINE Szenarien-Berücksichtigung
shipments_today = rounded  # Volle geplante Menge
```

**Optimal:**
```python
# simulation/china_transport.py (get_inbound_log_dataframe)
# Liest aus Single Source of Truth (transport_status)
# Berechnet Versandmengen aus transport_status (mit Verlusten bereits berücksichtigt)
for (order_day, order_id), status in self.transport_status.items():
    if status.get('ship_departure_day') == day:
        # Liest actual_quantity (mit Verlusten bereits berücksichtigt)
        actual_qty = status.get('actual_quantity', status.get('quantity', 0.0))
        # Verteile auf Satteltypen (proportional)
        for saddle_name, share in saddle_shares.items():
            shipments_today[saddle_name] += actual_qty * share
        
        # Verspätungen sind bereits in ship_arrival_day berücksichtigt
        ship_arrival_day = status.get('ship_arrival_day')
        # ... Rest der Berechnung
```

**Vorteile:**
- ✅ Lieferprobleme werden automatisch berücksichtigt (aus `transport_status`)
- ✅ Konsistenz: Inbound-Log zeigt gleiche Mengen wie `process_shipments()`
- ✅ Keine Code-Duplikation (Szenarien-Logik nur einmal)

---

### **Datenfluss-Diagramm (Optimal):**

```
Lieferprobleme (Szenario)
    ↓
process_shipments() (Tag X)
    ↓
transport_status.actual_quantity (mit Verlusten) ✅ Single Source of Truth
transport_status.ship_arrival_day (mit Verspätungen) ✅ Single Source of Truth
    ↓
    ├─→ Simulator (Wareneingang) ✅
    ├─→ Materiallager (Lagerzugang) ✅
    ├─→ Supplier-Log (Warenausgang) ← NEU: Liest aus transport_status
    └─→ Inbound-Log (Versandmengen) ← NEU: Liest aus transport_status
```

---

### **Zusammenfassung: Lieferprobleme**

| Komponente | Aktuell | Optimal | Status |
|------------|---------|---------|--------|
| **process_shipments()** | ✅ Implementiert | ✅ Single Source of Truth | ✅ Fertig |
| **Supplier-Log** | ❌ Nur 100% Verlust | ✅ Liest aus transport_status | ⏳ Zu implementieren |
| **Inbound-Log** | ❌ Ignoriert | ✅ Liest aus transport_status | ⏳ Zu implementieren |
| **Materiallager** | ✅ Verwendet transport_status | ✅ Liest aus transport_status | ✅ Fertig |

---

## 📊 GESAMTÜBERSICHT: Alle Szenarien

### **Implementierungsstatus:**

| Szenario | Single Source of Truth | Fehlende Komponenten | Priorität |
|----------|----------------------|---------------------|-----------|
| **Marketingaktion** | ✅ `daily_demands_actual` | Materiallager, Fertigproduktelager, Reporting | 🔴 Hoch |
| **Wasserschaden** | ⚠️ `inventory.stock_saddles` (während Simulation) | Materiallager, ProductionPlanner | 🔴 Hoch |
| **Lieferantenausfall** | ⚠️ `supplier_blocked` (im Simulator) | Supplier-Log, Inbound-Log | 🟡 Mittel |
| **Lieferprobleme** | ✅ `transport_status.actual_quantity` | Supplier-Log, Inbound-Log | 🔴 Hoch |

---

### **Empfohlene Implementierungsreihenfolge:**

1. **Phase 1: Marketingaktion** (einfach, keine Zirkulären Abhängigkeiten)
   - Materiallager liest aus `daily_demands_actual`
   - Fertigproduktelager liest aus `production_logs`
   - Reporting liest aus `daily_demands_actual`

2. **Phase 2: Lieferprobleme** (einfach, Single Source of Truth bereits vorhanden)
   - Supplier-Log liest aus `transport_status`
   - Inbound-Log liest aus `transport_status`

3. **Phase 3: Wasserschaden** (komplex, Zirkuläre Abhängigkeit)
   - Simulator speichert Wasserschaden-Info
   - Materiallager liest Info und wendet an
   - ProductionPlanner liest aus `material_inventory_data`

4. **Phase 4: Lieferantenausfall** (mittel, muss in mehreren Komponenten geprüft werden)
   - ProcurementManager blockiert neue Bestellungen
   - Supplier-Log zeigt Lieferantenausfall
   - Inbound-Log zeigt Lieferantenausfall

---

## 🎯 FAZIT

### **Kernprinzipien für flächendeckende Szenarien-Implementierung:**

1. **Single Source of Truth:**
   - Jedes Szenario wird **einmal** angewendet (zentral)
   - Alle anderen Komponenten **lesen** aus Single Source of Truth (nicht neu berechnen)

2. **Konsistente Datenfluss-Hierarchie:**
   - Nachfrage → Produktion → Transport → Materialbestände
   - Szenarien werden **automatisch weitergegeben** (nicht überschrieben)

3. **Zwei-Phasen-Ansatz (für Zirkuläre Abhängigkeiten):**
   - Simulation läuft zuerst (Szenarien werden angewendet)
   - Materiallager berechnet danach (liest Szenarien-Info)

4. **Fallback-Mechanismen:**
   - Wenn Single Source of Truth nicht verfügbar ist, verwende alte Logik
   - Garantiert Rückwärtskompatibilität

---

**Die vollständige theoretische Analyse wurde in `SZENARIEN_IMPLEMENTIERUNG_THEORETISCH.md` gespeichert.**
