# Beispiel: Datenfluss einer Bestellung mit Szenarien

**Datum:** 2026-01-22  
**Ziel:** Konkrete Visualisierung des Datenflusses einer Bestellung durch das System

---

## 📋 Beispiel-Bestellung

**Ausgangssituation:**
- **Tag:** 50 (20. Februar 2027, Dienstag - Arbeitstag)
- **Produkt:** MTB Allrounder
- **Basis-Nachfrage:** 100 Einheiten (ohne Marketing)
- **Marketing-Szenario aktiv:** Tag 45-55 (Faktor 1.5 = +50% Nachfrage)
- **Lieferantenausfall-Szenario:** Tag 60-70 (blockiert neue Bestellungen)
- **Lieferproblem-Szenario:** Tag 80-90 (10% Verlust, 2 Tage Verspätung)
- **Wasserschaden-Szenario:** Tag 100 (50% Verlust Sattelbestand)

---

## 🔄 Datenfluss Schritt für Schritt

### **LEVEL 1: NACHFRAGE (Single Source of Truth)**

#### Schritt 1.1: Basis-Nachfrage berechnen

**Komponente:** `calculate_volume_planning_demand()`  
**Datei:** `ui/volume_planning_utils.py`

```python
# Tag 50, MTB Allrounder
month = 2  # Februar
base_daily_float = yearly_volume * SEASONALITY[2] * PRODUCT_SALES_SHARES["MTB Allrounder"] / workdays_in_month
# Beispiel: 10000 * 0.08 * 0.25 / 20 = 10.0 Einheiten/Tag (Float)
```

**Ergebnis:**
- `base_daily_float = 10.0` (Float)
- `daily_demands_planned[50]["MTB Allrounder"] = 10` (ohne Marketing)

---

#### 🎯 **SZENARIO 1: Marketingaktion greift**

**Komponente:** `ScenarioManager.get_marketing_scenarios(50)`  
**Datei:** `models/scenarios.py`

```python
# Marketing-Szenario aktiv: Tag 45-55, Faktor 1.5
marketing_scenarios = [
    MarketingCampaignScenario(
        name="Frühjahrsaktion",
        start_day=45,
        end_day=55,
        demand_increase_factor=1.5  # +50% Nachfrage
    )
]
```

**Berechnung Marketing-Add-on:**
```python
# In calculate_volume_planning_demand()
marketing_add_ons = {}
for scenario in marketing_scenarios:
    factor = 1.5
    base_float = 10.0
    add_on = base_float * (factor - 1.0)  # 10.0 * 0.5 = 5.0
    marketing_add_ons["MTB Allrounder"] = 5.0
```

**Ergebnis:**
- `daily_demands_actual[50]["MTB Allrounder"] = 15` (10 + 5, gerundet)
- **Marketing erhöht Nachfrage um 50%**

---

### **LEVEL 2: PRODUKTION (Single Source of Truth)**

#### Schritt 2.1: Produktionsplanung

**Komponente:** `ProductionPlanner.plan_daily_production(50)`  
**Datei:** `simulation/production_planner.py`

**Input:**
- `daily_demands_actual[50]["MTB Allrounder"] = 15` (mit Marketing!)
- Materialbestände (Sättel, Rahmen, Gabeln)

**Berechnung:**
```python
# Geplante PM = Nachfrage (mit Marketing bereits berücksichtigt)
planned_pm = 15

# Materialverfügbarkeit prüfen
saddle_available = stock_by_saddle_type["Fizik Tundra"]  # z.B. 20 Einheiten
frame_available = stock_frames  # unbegrenzt
fork_available = stock_forks  # unbegrenzt

# Tatsächliche PM = min(planned_pm, material_limited)
actual_pm = min(15, 20)  # = 15 (Material ausreichend)
```

**Ergebnis in `production_logs`:**
```python
production_logs["MTB Allrounder"][50] = {
    'geplante PM': 15,  # Mit Marketing!
    'tatsächliche PM': 15,
    'fertiggestellte PM': 15,
    'Backlog': 0,
    'Materialverbrauch': {
        'Fizik Tundra': 15,  # 1 Bike = 1 Sattel
        'Rahmen': 15,
        'Gabel': 15
    }
}
```

**Wichtig:** Marketing ist bereits in `daily_demands_actual` enthalten, daher automatisch in Produktion!

---

### **LEVEL 3: TRANSPORT (Single Source of Truth)**

#### Schritt 3.1: Bestelleingang (China)

**Komponente:** `ChinaTransportManager.get_supplier_log_dataframe()`  
**Datei:** `simulation/china_transport.py`

**Input:**
- `daily_demands_actual[50]["MTB Allrounder"] = 15` (mit Marketing!)

**Berechnung:**
```python
# Bestelleingang = Summe aller Nachfragen für diesen Tag
bestelleingang = daily_demands_actual[50]["MTB Allrounder"]  # = 15
# (Für alle Produkte summiert, hier vereinfacht nur MTB Allrounder)
```

**Ergebnis:**
- `Bestelleingang (Tag 50) = 15` (mit Marketing bereits berücksichtigt)

---

#### Schritt 3.2: Freigabedatum

**Komponente:** `ChinaTransportManager.get_supplier_log_dataframe()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Freigabedatum = Bestelleingang-Datum (normalerweise sofort)
freigabedatum = Tag 50  # 20.02.2027
```

**Ergebnis:**
- `Freigabedatum = Tag 50`

---

#### Schritt 3.3: Produktionsdatum (China)

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Produktionsdatum = Freigabedatum + 4 chinesische Arbeitstage
freigabedatum = Tag 50  # 20.02.2027
chinese_workdays = 4
produktionsdatum = Tag 50 + 4 chinesische AT = Tag 54  # 24.02.2027
```

**Ergebnis:**
- `Produktionsdatum = Tag 54`

---

#### Schritt 3.4: Warenausgang (China)

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Warenausgang = Summe aller Bestellungen mit Produktionsdatum = Tag 54
# Pool-Logik: Alle Bestellungen mit Produktionsdatum Tag 54 werden zusammengefasst
warenausgang = sum(all_orders_with_produktionsdatum == 54)
# Beispiel: 15 Einheiten (unsere Bestellung)
```

**Ergebnis:**
- `Warenausgang (Tag 54) = 15` (ursprüngliche Menge)

---

#### Schritt 3.5: Transport-Status speichern

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Initialer Transport-Status:**
```python
transport_status[(50, order_id)] = {
    'quantity': 15,  # Ursprüngliche Menge
    'actual_quantity': 15,  # Wird später durch Szenarien angepasst
    'ship_departure_day': None,  # Noch nicht verschickt
    'available_day': None  # Noch nicht verfügbar
}
```

---

#### 🎯 **SZENARIO 2: Lieferantenausfall (blockiert neue Bestellungen)**

**Komponente:** `ScenarioManager.get_supplier_breakdown_scenarios(60)`  
**Datei:** `models/scenarios.py`

**Szenario:**
- **Aktiv:** Tag 60-70
- **Betroffen:** Sättel
- **Wirkung:** Blockiert **neue Bestellungen** (nicht bereits unterwegs befindliche Ware)

**Berechnung:**
```python
# In process_shipments() oder check_and_order()
if supplier_breakdown_active:
    # Neue Bestellungen werden blockiert
    # ABER: Bereits unterwegs befindliche Ware wird weiter transportiert!
    new_order_blocked = True
```

**Auswirkung auf unsere Bestellung:**
- ✅ **Unsere Bestellung (Tag 50) ist bereits produziert (Tag 54)**
- ✅ **Wird weiter transportiert (nicht blockiert)**
- ❌ **Neue Bestellungen ab Tag 60 werden blockiert**

**Ergebnis:**
- Unsere Bestellung: **Nicht betroffen** (bereits produziert)
- Neue Bestellungen: **Blockiert** (Tag 60-70)

---

#### Schritt 3.6: Abfahrt Schiff 🇨🇳

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Abfahrt Schiff = Produktionsdatum + 1 chinesischer Arbeitstag
produktionsdatum = Tag 54  # 24.02.2027
abfahrt_schiff = Tag 54 + 1 chinesischer AT = Tag 55  # 25.02.2027
```

**Ergebnis:**
- `Abfahrt Schiff 🇨🇳 = Tag 55`

**Transport-Status aktualisiert:**
```python
transport_status[(50, order_id)]['ship_departure_day'] = 55
```

---

#### Schritt 3.7: Ankunft Schiff 🇩🇪

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Ankunft Schiff = Abfahrt Schiff + 30 Tage (Schifffahrt)
abfahrt_schiff = Tag 55  # 25.02.2027
ankunft_schiff = Tag 55 + 30 = Tag 85  # 27.03.2027
```

**Ergebnis:**
- `Ankunft Schiff 🇩🇪 = Tag 85`

---

#### 🎯 **SZENARIO 3: Lieferprobleme (Verlust + Verspätung)**

**Komponente:** `ScenarioManager.get_delivery_problem_scenarios(85)`  
**Datei:** `models/scenarios.py`

**Szenario:**
- **Aktiv:** Tag 80-90
- **Verlust:** 10% (1.5 Einheiten → 1 Einheit verloren)
- **Verspätung:** +2 Tage

**Berechnung:**
```python
# In process_shipments() oder get_inbound_log_dataframe()
delivery_problems = scenario_manager.get_delivery_problem_scenarios(85)
if delivery_problems:
    for scenario in delivery_problems:
        loss_percentage = 0.1  # 10%
        delay_days = 2
        
        # Ursprüngliche Menge
        original_qty = 15
        
        # Verlust anwenden
        actual_quantity = original_qty * (1 - loss_percentage)  # 15 * 0.9 = 13.5 → 13 (gerundet)
        
        # Verspätung anwenden
        original_available_day = Tag 87  # (Ankunft Schiff + 2 Tage LKW)
        actual_available_day = original_available_day + delay_days  # Tag 87 + 2 = Tag 89
```

**Transport-Status aktualisiert:**
```python
transport_status[(50, order_id)] = {
    'quantity': 15,  # Ursprüngliche Menge
    'actual_quantity': 13,  # Nach Verlust (10% = 1.5 → 1 verloren)
    'ship_departure_day': 55,
    'available_day': 89  # Mit Verspätung (+2 Tage)
}
```

**Ergebnis:**
- `actual_quantity = 13` (statt 15, 2 Einheiten verloren)
- `available_day = Tag 89` (statt Tag 87, +2 Tage Verspätung)

---

#### Schritt 3.8: Ankunft LKW 🇩🇪

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Ankunft LKW = Ankunft Schiff + 2 deutsche Arbeitstage
ankunft_schiff = Tag 85  # 27.03.2027
ankunft_lkw = Tag 85 + 2 deutsche AT = Tag 87  # 29.03.2027

# ABER: Mit Lieferproblem-Verspätung
ankunft_lkw_actual = Tag 87 + 2 = Tag 89  # 31.03.2027
```

**Ergebnis:**
- `Geplante Ankunft LKW 🇩🇪 = Tag 87`
- `Tatsächliche Ankunft LKW 🇩🇪 = Tag 89` (mit Verspätung)

---

#### Schritt 3.9: Verfügbar im Lager 🇩🇪

**Komponente:** `ChinaTransportManager.process_shipments()`  
**Datei:** `simulation/china_transport.py`

**Berechnung:**
```python
# Verfügbar im Lager = Tatsächliche Ankunft LKW
verfuegbar_im_lager = Tag 89  # 31.03.2027
```

**Ergebnis:**
- `Verfügbar im Lager 🇩🇪 = Tag 89`
- **Menge:** 13 Einheiten (nach 10% Verlust)

---

### **LEVEL 4: MATERIALBESTÄNDE (Single Source of Truth)**

#### Schritt 4.1: Lagerzugang (Materiallager)

**Komponente:** `Materiallager.create_saddle_inventory_log()`  
**Datei:** `pages/5_materiallager.py`

**Input:**
- `transport_status[(50, order_id)]['actual_quantity'] = 13` (mit Lieferproblem!)
- `transport_status[(50, order_id)]['available_day'] = 89`

**Berechnung:**
```python
# Tag 89: Wareneingang
receipt_by_saddle["Fizik Tundra"] = 13  # Aus transport_status gelesen
```

**Ergebnis:**
- `Lagerzugang (Tag 89) = 13` (mit Lieferproblem bereits berücksichtigt)

---

#### Schritt 4.2: Bestand morgens (Materiallager)

**Komponente:** `Materiallager.create_saddle_inventory_log()`  
**Datei:** `pages/5_materiallager.py`

**Berechnung:**
```python
# Bestand morgens = Bestand abends (Vortag) + Lagerzugang (heute)
stock_evening_vortag = 20  # Beispiel
receipt_today = 13
stock_morning = 20 + 13 = 33
```

**Ergebnis:**
- `Bestand morgens (Tag 89) = 33`

---

#### Schritt 4.3: Lagerabgang (Materiallager)

**Komponente:** `Materiallager.create_saddle_inventory_log()`  
**Datei:** `pages/5_materiallager.py`

**Input:**
- `production_logs["MTB Allrounder"][89]` (aus ProductionPlanner, Single Source of Truth!)

**Berechnung:**
```python
# Liest aus production_logs (bereits berechnet, mit Marketing!)
planner = st.session_state.simulator.production_planner
production_logs = planner.production_logs

# Tag 89: Produktion
if "MTB Allrounder" in production_logs and 89 < len(production_logs["MTB Allrounder"]):
    log_entry = production_logs["MTB Allrounder"][89]
    production_qty = log_entry.get('tatsächliche PM', 0)  # z.B. 12 Einheiten
    
    # Materialverbrauch (1 Bike = 1 Sattel)
    issue_by_saddle["Fizik Tundra"] = production_qty  # = 12
```

**Ergebnis:**
- `Lagerabgang (Tag 89) = 12` (aus production_logs, mit Marketing bereits berücksichtigt!)

---

#### Schritt 4.4: Bestand abends (Materiallager)

**Komponente:** `Materiallager.create_saddle_inventory_log()`  
**Datei:** `pages/5_materiallager.py`

**Berechnung:**
```python
# Bestand abends = Bestand morgens - Lagerabgang
stock_morning = 33
issue_today = 12
stock_evening = 33 - 12 = 21
```

**Ergebnis:**
- `Bestand abends (Tag 89) = 21`

---

#### 🎯 **SZENARIO 4: Wasserschaden (reduziert Bestand)**

**Komponente:** `ScenarioManager.get_warehouse_damage_scenarios(100)`  
**Datei:** `models/scenarios.py`

**Szenario:**
- **Aktiv:** Tag 100
- **Betroffen:** Sättel
- **Verlust:** 50% des Lagerbestands

**Berechnung:**
```python
# In create_saddle_inventory_log() oder Simulator.run()
warehouse_damages = scenario_manager.get_warehouse_damage_scenarios(100)
if warehouse_damages:
    for scenario in warehouse_damages:
        if scenario.affected_component == "saddles":
            stock_before = 21  # Bestand vor Wasserschaden
            loss_percentage = 0.5  # 50%
            loss_amount = stock_before * loss_percentage  # 21 * 0.5 = 10.5 → 10
            stock_after = stock_before - loss_amount  # 21 - 10 = 11
```

**Ergebnis:**
- `Bestand nach Wasserschaden (Tag 100) = 11` (statt 21, 10 Einheiten verloren)

**Wichtig:** Wasserschaden wird **direkt im Materiallager** angewendet, nicht in transport_status!

---

### **LEVEL 5: FERTIGPRODUKTE (Single Source of Truth)**

#### Schritt 5.1: Lagerzugang (Fertigproduktelager)

**Komponente:** `Fertigproduktelager.create_finished_goods_log()`  
**Datei:** `pages/7_fertigproduktelager.py`

**Input:**
- `production_logs["MTB Allrounder"][89]` (aus ProductionPlanner, Single Source of Truth!)

**Berechnung:**
```python
# Liest aus production_logs (bereits berechnet, mit Marketing!)
planner = st.session_state.simulator.production_planner
production_logs = planner.production_logs

# Tag 89: Produktion
if "MTB Allrounder" in production_logs and 89 < len(production_logs["MTB Allrounder"]):
    log_entry = production_logs["MTB Allrounder"][89]
    production_qty = log_entry.get('tatsächliche PM', 0)  # z.B. 12 Einheiten
    
    # Verteile auf Märkte (basierend auf MARKETS)
    for market_code, market_params in MasterData.MARKETS.items():
        market_share = market_params['share']  # z.B. DE = 0.4
        receipt = production_qty * market_share  # 12 * 0.4 = 4.8 → 4
        total_receipt += receipt
```

**Ergebnis:**
- `Lagerzugang (Tag 89) = 12` (aus production_logs, mit Marketing bereits berücksichtigt!)

---

#### Schritt 5.2: Lagerabgang (Fertigproduktelager)

**Komponente:** `Fertigproduktelager.create_finished_goods_log()`  
**Datei:** `pages/7_fertigproduktelager.py`

**Berechnung:**
```python
# Just-in-Time: Sofort versendet
dispatch = receipt  # 12 Einheiten
```

**Ergebnis:**
- `Lagerabgang (Tag 89) = 12` (Just-in-Time)

---

## 📊 Zusammenfassung: Datenfluss mit Szenarien

### Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│  TAG 50: NACHFRAGE                                          │
│  └─→ Basis: 10 Einheiten                                    │
│  └─→ 🎯 Marketing (+50%): 15 Einheiten                      │
│      ↓                                                       │
│      daily_demands_actual[50] = 15                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 50: PRODUKTION                                         │
│  └─→ Geplante PM: 15 (mit Marketing!)                       │
│  └─→ Tatsächliche PM: 15                                    │
│      ↓                                                       │
│      production_logs["MTB Allrounder"][50] = 15              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 50: BESTELLUNG (China)                                 │
│  └─→ Bestelleingang: 15 (mit Marketing!)                    │
│  └─→ Freigabedatum: Tag 50                                  │
│  └─→ Produktionsdatum: Tag 54                               │
│      ↓                                                       │
│      transport_status[(50, order_id)] = {                   │
│          'quantity': 15,                                    │
│          'actual_quantity': 15                              │
│      }                                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 54: PRODUKTION (China)                                 │
│  └─→ Produktionsmenge: 15                                   │
│  └─→ Warenausgang: 15                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 55: ABFAHRT SCHIFF 🇨🇳                                  │
│  └─→ Abfahrt: Tag 55                                         │
│      ↓                                                       │
│      transport_status[(50, order_id)]['ship_departure_day'] = 55
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 60-70: 🎯 LIEFERANTENAUSFALL                            │
│  └─→ Blockiert neue Bestellungen                            │
│  └─→ ABER: Unsere Bestellung bereits produziert (Tag 54)    │
│  └─→ ✅ Weiter transportiert (nicht betroffen)              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 85: ANKUNFT SCHIFF 🇩🇪                                  │
│  └─→ Ankunft: Tag 85                                        │
│  └─→ 🎯 Lieferproblem aktiv (Tag 80-90)                     │
│      ↓                                                       │
│      transport_status[(50, order_id)] = {                   │
│          'actual_quantity': 13,  # -10% Verlust             │
│          'available_day': 89     # +2 Tage Verspätung       │
│      }                                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 89: ANKUNFT LKW 🇩🇪 & VERFÜGBAR IM LAGER 🇩🇪            │
│  └─→ Geplante Ankunft: Tag 87                                │
│  └─→ Tatsächliche Ankunft: Tag 89 (+2 Tage Verspätung)     │
│  └─→ Menge: 13 Einheiten (-10% Verlust)                     │
│      ↓                                                       │
│      material_inventory_data[89]["Fizik Tundra"] += 13      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 89: MATERIALBESTÄNDE                                   │
│  └─→ Lagerzugang: 13 (aus transport_status, mit            │
│      Lieferproblem bereits berücksichtigt!)                  │
│  └─→ Bestand morgens: 33                                    │
│  └─→ Lagerabgang: 12 (aus production_logs, mit Marketing!) │
│  └─→ Bestand abends: 21                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TAG 100: 🎯 WASSERSCHADEN                                  │
│  └─→ Bestand vorher: 21                                     │
│  └─→ Verlust: 50% = 10 Einheiten                           │
│  └─→ Bestand nachher: 11                                   │
│      ↓                                                       │
│      material_inventory_data[100]["Fizik Tundra"] = 11     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Szenarien-Übersicht

### Szenario 1: Marketingaktion (Tag 45-55)

**Greift an:** LEVEL 1 (Nachfrage)  
**Beeinflusst:**
- `daily_demands_actual[50] = 15` (statt 10)
- Automatisch weitergegeben an:
  - ProductionPlanner → `production_logs` (geplante PM = 15)
  - ChinaTransportManager → Bestelleingang = 15
  - Materiallager → Lagerabgang = 15 (aus production_logs)
  - Fertigproduktelager → Lagerzugang = 15 (aus production_logs)

**Ergebnis:** Alle abhängigen Komponenten sehen automatisch erhöhte Nachfrage!

---

### Szenario 2: Lieferantenausfall (Tag 60-70)

**Greift an:** LEVEL 3 (Transport, neue Bestellungen)  
**Beeinflusst:**
- Blockiert **neue Bestellungen** ab Tag 60
- **Nicht betroffen:** Bereits produzierte/unterwegs befindliche Ware (unsere Bestellung Tag 50)

**Ergebnis:** Unsere Bestellung wird weiter transportiert, neue Bestellungen werden blockiert.

---

### Szenario 3: Lieferprobleme (Tag 80-90)

**Greift an:** LEVEL 3 (Transport, `transport_status`)  
**Beeinflusst:**
- `transport_status[(50, order_id)]['actual_quantity'] = 13` (statt 15, -10% Verlust)
- `transport_status[(50, order_id)]['available_day'] = 89` (statt 87, +2 Tage Verspätung)
- Automatisch weitergegeben an:
  - Supplier-Log → Warenausgang = 13
  - Inbound-Log → Versandmengen = 13, Ankunft = Tag 89
  - Materiallager → Lagerzugang = 13 (aus transport_status)

**Ergebnis:** Alle abhängigen Komponenten sehen automatisch reduzierte Menge und Verspätung!

---

### Szenario 4: Wasserschaden (Tag 100)

**Greift an:** LEVEL 4 (Materialbestände, `material_inventory_data`)  
**Beeinflusst:**
- `material_inventory_data[100]["Fizik Tundra"] = 11` (statt 21, -50% Verlust)
- Automatisch weitergegeben an:
  - ProductionPlanner → Materialverfügbarkeit = 11
  - Reporting → Material-KPIs

**Ergebnis:** Alle abhängigen Komponenten sehen automatisch reduzierten Bestand!

---

## ✅ Vorteile der optimalen Architektur

### 1. Konsistenz

- ✅ Alle Komponenten sehen **gleiche Daten**
- ✅ Szenarien werden **zentral** angewendet
- ✅ Automatisch weitergegeben an alle abhängigen Komponenten

### 2. Szenarien-Ready

- ✅ Marketing → `daily_demands_actual` → automatisch in Produktion, Transport, Materiallager
- ✅ Lieferprobleme → `transport_status.actual_quantity` → automatisch in Supplier-Log, Inbound-Log, Materiallager
- ✅ Wasserschaden → `material_inventory_data` → automatisch in ProductionPlanner, Reporting

### 3. Einfachheit

- ✅ Szenarien werden **einmal** angewendet
- ✅ Keine Szenarien-Logik in jeder Komponente
- ✅ Änderungen nur an **einer Stelle**

---

## 📋 Zusammenfassung

### Datenfluss-Prinzip

**Single Source of Truth:**
1. **Nachfrage:** `daily_demands_actual` (mit Marketing)
2. **Produktion:** `production_logs` (mit Marketing)
3. **Transport:** `transport_status` (mit Lieferproblemen)
4. **Materialbestände:** `material_inventory_data` (mit Wasserschaden)

### Szenarien-Integration

**Prinzip:** Szenarien werden **zentral** angewendet und dann **automatisch weitergegeben**.

**Beispiel:**
- Marketingaktion → `daily_demands_actual` → ProductionPlanner → `production_logs` → Materiallager, Fertigproduktelager
- Lieferprobleme → `transport_status.actual_quantity` → Supplier-Log, Inbound-Log, Materiallager

**Ergebnis:** Konsistenz garantiert, Szenarien automatisch berücksichtigt!
