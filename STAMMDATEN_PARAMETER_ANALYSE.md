# Stammdaten Parameter - Analyse und Korrekturen

**Datum:** 28.01.2026  
**Problem:** Parameteränderungen haben keine direkten Auswirkungen auf abhängige Sichten  
**Status:** ⚠️ **PROBLEME IDENTIFIZIERT**

---

## 🔍 Identifizierte Probleme

### Problem 1: `GLOBAL_CONFIG` wird nicht vollständig synchronisiert

**Aktuell:**
- Nur `total_volume` wird synchronisiert (Zeile 235, 257)
- Andere Parameter (`capacity_per_hour`, `working_hours_per_shift`, etc.) werden NICHT synchronisiert

**Verwendet in:**
- `simulation/production_planner.py` Zeile 137-138: `GLOBAL_CONFIG.get('working_hours_per_shift', 8)`, `GLOBAL_CONFIG.get('capacity_per_hour', 130)`
- `ui/production_calculations.py` Zeile 486-487: `GLOBAL_CONFIG.get('working_hours_per_shift', 8)`, `GLOBAL_CONFIG.get('capacity_per_hour', 130)`
- `pages/2_volumenplanung.py` Zeile 82, 258: `GLOBAL_CONFIG['capacity_per_hour']`

**Auswirkung:**
- Änderungen von `capacity_per_hour`, `working_hours_per_shift`, etc. haben keine Auswirkung
- Berechnungen verwenden immer Standard-Werte

---

### Problem 2: `PRODUCT_SALES_SHARES` wird nicht synchronisiert

**Aktuell:**
- `editable_product_sales_shares` wird geändert (Zeile 347)
- `MasterData.PRODUCT_SALES_SHARES` wird NICHT aktualisiert

**Verwendet in:**
- `simulation/demand_calculator.py` Zeile 64: `MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)`
- `config/master_data.py` Zeile 268: `MasterData.PRODUCT_SALES_SHARES.items()` (calculate_saddle_shares)
- `pages/7_fertigproduktelager.py` Zeile 102: `MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)`
- `pages/1_reporting.py` Zeile 96: `MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)`
- `ui/volume_planning_utils.py` Zeile 185: `MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)`

**Auswirkung:**
- Änderungen von Verkaufsanteilen haben keine Auswirkung
- Nachfrage-Berechnungen verwenden immer Standard-Werte

---

### Problem 3: `SEASONALITY` wird nicht synchronisiert

**Aktuell:**
- `editable_seasonality` wird geändert (Zeile 395)
- `MasterData.SEASONALITY` wird NICHT aktualisiert

**Verwendet in:**
- `simulation/demand_calculator.py` Zeile 39: `self.master_data.SEASONALITY.get(month, 0.0)`

**Auswirkung:**
- Änderungen von Saisonalität haben keine Auswirkung
- Nachfrage-Berechnungen verwenden immer Standard-Werte

---

### Problem 4: `DAILY_WORKLOAD` wird nicht synchronisiert

**Aktuell:**
- `editable_daily_workload` wird geändert (Zeile 308)
- `MasterData.DAILY_WORKLOAD` wird NICHT aktualisiert

**Verwendet in:**
- `simulation/workday_calculator.py` Zeile 83: `self.master_data.DAILY_WORKLOAD.get(weekday_name, 0.0)`

**Auswirkung:**
- Änderungen von täglicher Arbeitslast haben keine Auswirkung
- Arbeitstag-Berechnungen verwenden immer Standard-Werte

---

### Problem 5: Cache-Invalidierung fehlt für einige Parameter

**Aktuell:**
- Cache wird nur invalidiert wenn `config_changed` (nur `GLOBAL_CONFIG`)
- Cache wird NICHT invalidiert wenn:
  - `workload_changed` (tägliche Arbeitslast)
  - `sales_changed` (Verkaufsanteile)
  - `seasonality_changed` (Saisonalität)

**Auswirkung:**
- Änderungen werden nicht sofort wirksam
- Alte Cache-Werte werden weiterhin verwendet

---

## ✅ Empfohlene Korrekturen

### 1. Vollständige Synchronisation von `GLOBAL_CONFIG`

**Code-Änderung:**
```python
if config_changed:
    # Synchronisiere ALLE Parameter, nicht nur total_volume
    for key, value in st.session_state.editable_global_config.items():
        MasterData.GLOBAL_CONFIG[key] = value
    
    # Spezielle Synchronisation für total_volume
    if 'total_volume' in st.session_state.editable_global_config:
        st.session_state.yearly_volume = st.session_state.editable_global_config['total_volume']
```

### 2. Synchronisation von `PRODUCT_SALES_SHARES`

**Code-Änderung:**
```python
if sales_changed:
    # Synchronisiere PRODUCT_SALES_SHARES
    for product, share in st.session_state.editable_product_sales_shares.items():
        MasterData.PRODUCT_SALES_SHARES[product] = share
    
    # Cache-Invalidierung
    # ... (siehe unten)
```

### 3. Synchronisation von `SEASONALITY`

**Code-Änderung:**
```python
if seasonality_changed:
    # Synchronisiere SEASONALITY
    for month, factor in st.session_state.editable_seasonality.items():
        MasterData.SEASONALITY[month] = factor
    
    # Cache-Invalidierung
    # ... (siehe unten)
```

### 4. Synchronisation von `DAILY_WORKLOAD`

**Code-Änderung:**
```python
if workload_changed:
    # Synchronisiere DAILY_WORKLOAD
    for day, workload in st.session_state.editable_daily_workload.items():
        MasterData.DAILY_WORKLOAD[day] = workload
    
    # Cache-Invalidierung
    # ... (siehe unten)
```

### 5. Umfassende Cache-Invalidierung

**Code-Änderung:**
```python
def _invalidate_all_caches():
    """Invalidiert alle relevanten Caches bei Parameteränderungen"""
    keys_to_delete = [
        'production_logs_cache',
        'production_logs_cache_key',
        'material_inventory_data',
        'saddle_logs_cache',
        'material_logs_cache',
        'inventory_chart_cache',
        'daily_demands_planned',
        'daily_demands_actual',
        'volume_planning_calculated',
        'volume_planning_cache_key'
    ]
    
    for k in keys_to_delete:
        if k in st.session_state:
            del st.session_state[k]
    
    # Lösche auch alle Caches die mit "material_inventory_" beginnen
    for k in list(st.session_state.keys()):
        if k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key':
            del st.session_state[k]
    
    # Invalidiere auch ChinaTransportManager Caches
    if 'simulator' in st.session_state and st.session_state.simulator:
        if hasattr(st.session_state.simulator, 'china_transport_manager'):
            manager = st.session_state.simulator.china_transport_manager
            manager._supplier_log_cache = {}
            manager._inbound_df_cache = {}
            manager._inbound_df_cache_key = None
```

---

## 📋 Abhängigkeiten

### Parameter → Berechnungen:

1. **`total_volume` / `yearly_volume`:**
   - → `calculate_volume_planning_demand()` (Nachfrage-Berechnung)
   - → `DemandCalculator` (tägliche Nachfrage)
   - → `ProductionPlanner` (Produktionsplanung)

2. **`capacity_per_hour`:**
   - → `ProductionPlanner` (tägliche Kapazität)
   - → `calculate_production_logs()` (Produktionsberechnung)

3. **`working_hours_per_shift`:**
   - → `ProductionPlanner` (Kapazität pro Schicht)
   - → `calculate_production_logs()` (Produktionsberechnung)

4. **`PRODUCT_SALES_SHARES`:**
   - → `DemandCalculator` (Nachfrage-Verteilung)
   - → `calculate_saddle_shares()` (Sattel-Anteile)
   - → `Fertigproduktelager` (Marktverteilung)

5. **`SEASONALITY`:**
   - → `DemandCalculator` (monatliche Nachfrage-Verteilung)

6. **`DAILY_WORKLOAD`:**
   - → `WorkdayCalculator` (Arbeitslast-Faktor)

---

## ✅ Status

- ⚠️ **PROBLEME IDENTIFIZIERT**
- ⚠️ **KORREKTUREN ERFORDERLICH**

---

**Nächster Schritt:** Korrekturen implementieren
