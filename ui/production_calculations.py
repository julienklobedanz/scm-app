"""
Production Calculations
Berechnungslogik für Produktionslogs (ohne UI-Rendering)
"""

import streamlit as st
import pandas as pd
import math
from datetime import date, datetime, timedelta
from typing import Dict
from config.master_data import MasterData
from simulation.workday_calculator import WorkdayCalculator
from models.scenarios import WaterDamageScenario

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def _get_backlog_from_previous_workday(
    production_logs: Dict[str, pd.DataFrame],
    product: str,
    day: int,
    planning_year: int,
    workday_calc: WorkdayCalculator
) -> float:
    """Holt Backlog vom vorherigen Arbeitstag."""
    if product not in production_logs:
        return 0.0
    
    df = production_logs[product]
    if df.empty or 'Datum' not in df.columns or 'Backlog' not in df.columns:
        return 0.0
    
    prev_day = day - 1
    while prev_day >= 0:
        if workday_calc.is_workday(prev_day):
            break
        prev_day -= 1
    
    if prev_day < 0:
        return 0.0
    
    prev_date = workday_calc.get_date_from_day(prev_day)
    prev_date_str = prev_date.strftime(MasterData.DATE_FORMAT)
    
    matching_rows = df[df['Datum'] == prev_date_str]
    if not matching_rows.empty:
        try:
            val = matching_rows.iloc[0].get('Backlog', 0)
            return float(val) if val > 0 else 0.0
        except: return 0.0
    
    return 0.0

def _recalculate_all_products_with_rank_logic(
    day: int,
    product_demands_new: Dict[str, int],
    saddle_available_new: Dict[str, float],
    daily_capacity: float,
    production_logs: Dict[str, pd.DataFrame],
    planning_year: int,
    workday_calc: WorkdayCalculator,
    backlog_by_product: Dict[str, float] = None
) -> Dict[str, int]:
    """
    Repliziert die Produktionslogik (Ranking, Kapazität, Material).
    """
    # 1. Backlog holen (falls nicht übergeben)
    if backlog_by_product is None:
        backlog_by_product = {}
        for product in sorted(MasterData.BOM.keys()):
            backlog_by_product[product] = _get_backlog_from_previous_workday(
                production_logs, product, day, planning_year, workday_calc
            )
    
    # 2. Bedarf = Tagesbedarf + Backlog
    production_demand_by_product = {}
    for product in sorted(MasterData.BOM.keys()):
        demand = product_demands_new.get(product, 0)
        backlog = backlog_by_product.get(product, 0.0)
        production_demand_by_product[product] = demand + backlog
    
    # 3. Anteilige Produktion
    total_production_demand = sum(production_demand_by_product.values())
    proportional_production_by_product = {}
    products_list = sorted(MasterData.BOM.keys())
    
    for product in products_list:
        demand = production_demand_by_product.get(product, 0.0)
        if total_production_demand > 0:
            proportional = math.floor(demand * daily_capacity / total_production_demand)
        else:
            proportional = 0
        proportional_production_by_product[product] = proportional
    
    # 4. Ranking
    rank_support_by_product = {}
    for idx, product in enumerate(products_list):
        row_number = idx + 1
        proportional = proportional_production_by_product.get(product, 0)
        rank_support = (row_number / 1000000.0) + proportional
        rank_support_by_product[product] = rank_support
    
    sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
    rank_by_product = {p: i + 1 for i, p in enumerate(sorted_products)}
    
    # 5. Verteilung mit Material-Check
    scheduled_production_by_product = {}
    total_scheduled_so_far = 0.0
    stock_by_saddle_type = saddle_available_new.copy()
    
    for product in sorted_products:
        demand = production_demand_by_product.get(product, 0.0)
        proportional = proportional_production_by_product.get(product, 0)
        rank = rank_by_product.get(product, 999)
        
        if demand <= 0:
            scheduled_production_by_product[product] = 0.0
            continue
        
        required_saddle_type = MasterData.BOM[product]['saddle']
        saddle_available = stock_by_saddle_type.get(required_saddle_type, 0.0)
        minimal = max(0.0, saddle_available)
        
        if rank <= 4:
            scheduled_qty = min(demand, proportional, minimal)
        else:
            base_qty = min(demand, proportional, minimal)
            remaining_capacity = daily_capacity - total_scheduled_so_far
            remaining_demand = max(0.0, demand - base_qty)
            
            if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
                rest_production = min(remaining_capacity, minimal, remaining_demand)
                scheduled_qty = base_qty + rest_production
            else:
                scheduled_qty = base_qty
        
        scheduled_qty = min(max(0.0, scheduled_qty), demand)
        scheduled_production_by_product[product] = scheduled_qty
        total_scheduled_so_far += scheduled_qty
        
        if scheduled_qty > 0:
            stock_by_saddle_type[required_saddle_type] = max(0.0, stock_by_saddle_type[required_saddle_type] - scheduled_qty)
    
    # Sicherheitsprüfungen (Kapazität & Bedarf)
    total_scheduled = sum(scheduled_production_by_product.values())
    if total_scheduled > daily_capacity:
        scale_factor = daily_capacity / total_scheduled if total_scheduled > 0 else 0
        for product in sorted_products:
            old_qty = scheduled_production_by_product.get(product, 0.0)
            new_qty = old_qty * scale_factor
            reduction = old_qty - new_qty
            scheduled_production_by_product[product] = new_qty
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction

    total_production_demand = sum(production_demand_by_product.values())
    total_scheduled = sum(scheduled_production_by_product.values())
    if total_scheduled > total_production_demand:
        scale_factor = total_production_demand / total_scheduled if total_scheduled > 0 else 0
        for product in sorted_products:
            old_qty = scheduled_production_by_product.get(product, 0.0)
            new_qty = old_qty * scale_factor
            reduction = old_qty - new_qty
            scheduled_production_by_product[product] = new_qty
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
    
    for product in products_list:
        demand = production_demand_by_product.get(product, 0.0)
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        if scheduled_qty > demand:
            old_qty = scheduled_production_by_product[product]
            scheduled_production_by_product[product] = demand
            reduction = old_qty - demand
            if reduction > 0:
                required_saddle_type = MasterData.BOM[product]['saddle']
                stock_by_saddle_type[required_saddle_type] = stock_by_saddle_type.get(required_saddle_type, 0.0) + reduction
    
    result = {}
    for product in products_list:
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        result[product] = int(scheduled_qty)
    
    return result

def _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year: int) -> Dict[int, Dict[str, float]]:
    """Erstellt Map Tag -> {Sattel: Menge} aus Inbound-Tabelle."""
    inbound_map = {}
    manager = simulator.china_transport_manager
    if not manager: return inbound_map
    
    saddle_shares = MasterData.calculate_saddle_shares()
    inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
    if inbound_df.empty: return inbound_map
    
    start_date_sim = date(planning_year, 1, 1)
    avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
    
    if avail_col not in inbound_df.columns: return inbound_map
    
    # Filter & Parse
    valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')].copy()
    if valid_rows.empty: return inbound_map
    
    try:
        valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=MasterData.DATE_FORMAT, errors='coerce').dt.date
        valid_rows = valid_rows[valid_rows['_parsed_date'].notna()]
        if valid_rows.empty: return inbound_map
        
        valid_rows['_day_idx'] = (pd.to_datetime(valid_rows['_parsed_date']) - pd.Timestamp(start_date_sim)).dt.days
        # Nur Tage im Simulationsjahr (0-364)
        valid_rows = valid_rows[(valid_rows['_day_idx'] >= 0) & (valid_rows['_day_idx'] < 365)]
        
        if valid_rows.empty: return inbound_map
        
        for saddle_name in saddle_shares.keys():
            if saddle_name in valid_rows.columns:
                # Summiere pro Tag
                grouped = valid_rows.groupby('_day_idx')[saddle_name].apply(
                    lambda x: pd.to_numeric(x, errors='coerce').fillna(0).sum()
                )
                for day_idx, total_qty in grouped.items():
                    if total_qty > 0:
                        day_idx_int = int(day_idx)
                        if day_idx_int not in inbound_map:
                            inbound_map[day_idx_int] = {s: 0.0 for s in saddle_shares.keys()}
                        inbound_map[day_idx_int][saddle_name] += float(total_qty)
    except:
        return inbound_map
        
    return inbound_map

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------

def calculate_production_logs():
    """
    Berechnet production_logs_cache mit Running Inventory.
    
    FIX: Startbestand wird nun ZWINGEND aus der Inbound-Tabelle berechnet,
    genau wie im Materiallager. Keine Verwendung von transport_status mehr!
    
    WICHTIG: Berechnungen werden nur durchgeführt, wenn PRODUCT_SALES_SHARES und SEASONALITY jeweils 100% ergeben.
    """
    # KRITISCH: Validiere Parameter bevor Berechnungen erfolgen
    from ui.volume_planning_utils import _validate_parameters
    is_valid, error_message = _validate_parameters()
    if not is_valid:
        return {}
    
    if 'simulator' not in st.session_state or st.session_state.simulator is None:
        return {}
    
    simulator = st.session_state.simulator
    planner = simulator.production_planner
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {}
    
    # Cache-Key update
    volume_planning_cache_key = st.session_state.get('volume_planning_cache_key', None)
    cache_key = f"production_logs_running_v7_FINAL_{volume_planning_cache_key}"
    
    if ('production_logs_cache' in st.session_state and 
        st.session_state.get('production_logs_cache_key') == cache_key):
        return st.session_state.production_logs_cache
    
    planning_year = st.session_state.get('planning_year', 2027)
    workday_calc = WorkdayCalculator(year=planning_year)
    scenario_manager = getattr(simulator, 'scenario_manager', None)
    
    saddle_shares = MasterData.calculate_saddle_shares()
    saddles = list(saddle_shares.keys())
    
    # Init Running Stock
    running_stock = {s: 0.0 for s in saddles}
    
    manager = simulator.china_transport_manager
    if manager:
        cutoff_date = date(planning_year, 1, 1)
        
        # --- FIX: Initialbestand AUSSCHLIESSLICH aus Inbound-Tabelle berechnen ---
        # Dies ist der entscheidende Fix für die Konsistenz mit dem Materiallager
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        if not inbound_df.empty:
            avail_col = 'Tatsächliche Ankunft LKW 🇩🇪'
            
            # Vektorisierte Berechnung
            try:
                if avail_col in inbound_df.columns:
                    valid_rows = inbound_df[inbound_df[avail_col].notna() & (inbound_df[avail_col].astype(str).str.strip() != '')].copy()
                    if not valid_rows.empty:
                        valid_rows['_parsed_date'] = pd.to_datetime(valid_rows[avail_col], format=MasterData.DATE_FORMAT, errors='coerce').dt.date
                        
                        # Filter: Alles was VOR dem 01.01.2027 ankommt, ist Initialbestand
                        initial_rows = valid_rows[valid_rows['_parsed_date'] < cutoff_date]
                        
                        for saddle_name in saddles:
                            if saddle_name in initial_rows.columns:
                                qty_series = pd.to_numeric(initial_rows[saddle_name], errors='coerce').fillna(0.0)
                                total_qty = qty_series.sum()
                                if total_qty > 0:
                                    running_stock[saddle_name] += float(total_qty)
            except Exception:
                pass # Falls Fehler, bleibt running_stock 0 (sicherer als falsche Daten)

    # DataFrames erstellen
    production_logs = {}
    for product, logs in planner.production_logs.items():
        if logs:
            production_logs[product] = pd.DataFrame(logs)
        else:
            production_logs[product] = pd.DataFrame()
            
    # Spalten sichern
    for product, df in production_logs.items():
        if not df.empty:
            saddle_name = MasterData.BOM.get(product, {}).get('saddle')
            if saddle_name and saddle_name not in df.columns:
                df[saddle_name] = 0
            if 'material_verbrauch' not in df.columns:
                df['material_verbrauch'] = 0
    
    # Row Map
    day_row_map = {}
    for p, df in production_logs.items():
        if df.empty: continue
        for idx, row in df.iterrows():
            d_str = row.get('Datum', '')
            if d_str:
                try:
                    d = datetime.strptime(d_str, MasterData.DATE_FORMAT).date()
                    day_idx = (d - date(planning_year, 1, 1)).days
                    if 0 <= day_idx < 365:
                        if day_idx not in day_row_map: day_row_map[day_idx] = {}
                        day_row_map[day_idx][p] = idx
                except: pass
    
    # Inbound Map für tägliche Zugänge (ab 01.01.)
    inbound_arrivals = {}
    if manager:
        inbound_arrivals = _get_inbound_arrivals_by_day_and_saddle(simulator, planning_year)
    
    current_backlog = {p: 0.0 for p in sorted(MasterData.BOM.keys())}
    daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    
    # ------------------------------------------------------------
    # HAUPTSCHLEIFE
    # ------------------------------------------------------------
    for day in range(365):
        current_date = workday_calc.get_date_from_day(day)
        
        # A. Inbound (ab Tag 0)
        if day in inbound_arrivals:
            for saddle_name, qty in inbound_arrivals[day].items():
                if qty > 0: running_stock[saddle_name] += qty
        
        # Bestand sichern für Anzeige (vor Verbrauch = „morgens“)
        daily_start_stock = running_stock.copy()
        
        is_workday = workday_calc.is_workday(day)
        
        # C. Kein Arbeitstag
        if not is_workday:
            if day in day_row_map:
                for p, idx in day_row_map[day].items():
                    saddle = MasterData.BOM[p]['saddle']
                    df = production_logs[p]
                    if saddle not in df.columns: df[saddle] = 0
                    df.at[idx, saddle] = int(round(daily_start_stock[saddle])) if daily_start_stock[saddle] > 0 else 0
                    df.at[idx, 'Backlog'] = int(round(current_backlog[p]))
            continue
        
        # D. Produktion
        todays_demand_map = daily_demands_actual.get(day, {})
        
        daily_capacity = 0.0
        if day in day_row_map and day_row_map[day]:
            first_prod = next(iter(day_row_map[day]))
            first_idx = day_row_map[day][first_prod]
            df = production_logs[first_prod]
            shifts = df.at[first_idx, 'Schichtanzahl']
            # Kapazität aus Stammdaten (Schichten × Arbeitsstunden × Kapazität/Stunde × Montagelinien)
            wh = MasterData.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
            cph = MasterData.GLOBAL_CONFIG.get('capacity_per_hour', 130)
            lines = MasterData.GLOBAL_CONFIG.get('assembly_lines', 1)
            daily_capacity = shifts * wh * cph * lines
        
        # E. Ranking
        if daily_capacity > 0:
            scheduled_production = _recalculate_all_products_with_rank_logic(
                day,
                todays_demand_map,
                running_stock.copy(),
                daily_capacity,
                production_logs,
                planning_year,
                workday_calc,
                current_backlog.copy()
            )
        else:
            scheduled_production = {p: 0 for p in sorted(MasterData.BOM.keys())}
        
        # F. Verbuchen
        for p, qty in scheduled_production.items():
            saddle = MasterData.BOM[p]['saddle']
            
            qty_to_book = min(qty, running_stock[saddle])
            running_stock[saddle] -= qty_to_book
            
            total_req = current_backlog[p] + todays_demand_map.get(p, 0)
            current_backlog[p] = max(0.0, total_req - qty_to_book)
            
            df = production_logs[p]
            if not df.empty and 'Datum' in df.columns:
                current_date_str = current_date.strftime(MasterData.DATE_FORMAT)
                matching_rows = df[df['Datum'] == current_date_str]
                if not matching_rows.empty:
                    idx = matching_rows.index[0]
                    if 'material_verbrauch' not in df.columns: df['material_verbrauch'] = 0
                    df.at[idx, 'material_verbrauch'] = qty_to_book
                    
                    if day in day_row_map and p in day_row_map[day]:
                        df.at[idx, 'tatsächliche PM'] = qty_to_book
                        df.at[idx, 'Backlog'] = int(round(current_backlog[p]))
                        if saddle not in df.columns: df[saddle] = 0
                        df.at[idx, saddle] = int(round(daily_start_stock[saddle])) if daily_start_stock[saddle] > 0 else 0
                        
                        planned = todays_demand_map.get(p, 0)
                        df.at[idx, 'geplante PM'] = int(planned)

        # G. Wasserschaden auf Bestand abends (nach Verbrauch)
        if scenario_manager:
            water_damage_scenarios = scenario_manager.get_water_damage_scenarios(day)
            for scenario in water_damage_scenarios:
                if scenario.affected_component == "saddles" and scenario.start_day == scenario.end_day and day == scenario.start_day:
                    loss_abs = max(0.0, getattr(scenario, 'loss_quantity_absolute', 0.0))
                    affected_saddles = getattr(scenario, 'affected_saddles', None)
                    if loss_abs > 0:
                        for s in saddles:
                            applies = (not affected_saddles or len(affected_saddles) == 0 or s in affected_saddles)
                            if applies:
                                deduct = min(loss_abs, running_stock[s])
                                running_stock[s] = max(0.0, running_stock[s] - deduct)
                    break

    # Fertiggestellte PM (Logic bleibt gleich, nur minimal gesäubert)
    try:
        for product, df in production_logs.items():
            if df.empty or 'Datum' not in df.columns: continue
            df_sorted = df.copy()
            df_sorted['_date_parsed'] = pd.to_datetime(df_sorted['Datum'], format=MasterData.DATE_FORMAT)
            df_sorted = df_sorted.sort_values('_date_parsed').reset_index(drop=True)
            
            date_to_idx = {}
            for idx, row in df_sorted.iterrows():
                try: date_to_idx[datetime.strptime(row['Datum'], MasterData.DATE_FORMAT).date()] = idx
                except: pass
            
            for idx, row in df_sorted.iterrows():
                try:
                    row_date = datetime.strptime(row['Datum'], MasterData.DATE_FORMAT).date()
                    day = (row_date - date(planning_year, 1, 1)).days
                    
                    if not workday_calc.is_workday(day):
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                        continue
                        
                    # Nur bei tatsächlichem Verlust fertiggestellte PM auf 0
                    water_damage_with_loss = False
                    if scenario_manager:
                        for wd in scenario_manager.get_water_damage_scenarios(day):
                            complete_loss = getattr(wd, 'complete_loss', False)
                            loss_by_saddle = getattr(wd, 'loss_by_saddle', None)
                            loss_quantity_absolute = getattr(wd, 'loss_quantity_absolute', 0.0)
                            if complete_loss or (loss_by_saddle and any(v > 0 for v in loss_by_saddle.values())) or loss_quantity_absolute > 0:
                                water_damage_with_loss = True
                                break
                    if water_damage_with_loss:
                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                    else:
                        prev_workday_found = False
                        prev_day = day - 1
                        lookback = 0
                        while prev_day >= 0 and lookback < 15:
                            if workday_calc.is_workday(prev_day):
                                p_date = workday_calc.get_date_from_day(prev_day)
                                if p_date in date_to_idx:
                                    p_idx = date_to_idx[p_date]
                                    prev_val = df_sorted.at[p_idx, 'tatsächliche PM']
                                    
                                    prev_wd_loss = False
                                    if scenario_manager:
                                        for wd in scenario_manager.get_water_damage_scenarios(prev_day):
                                            complete_loss = getattr(wd, 'complete_loss', False)
                                            loss_by_saddle = getattr(wd, 'loss_by_saddle', None)
                                            loss_quantity_absolute = getattr(wd, 'loss_quantity_absolute', 0.0)
                                            if complete_loss or (loss_by_saddle and any(v > 0 for v in loss_by_saddle.values())) or loss_quantity_absolute > 0:
                                                prev_wd_loss = True
                                                break
                                    if prev_wd_loss and prev_val == 0:
                                        df_sorted.at[idx, 'fertiggestellte PM'] = 0
                                    else:
                                        df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_val)) if prev_val > 0 else 0
                                    prev_workday_found = True
                                    break
                            prev_day -= 1
                            lookback += 1
                        
                        if not prev_workday_found:
                            val = row.get('tatsächliche PM', 0)
                            df_sorted.at[idx, 'fertiggestellte PM'] = int(round(val)) if val > 0 else 0
                except:
                    df_sorted.at[idx, 'fertiggestellte PM'] = 0
            
            if '_date_parsed' in df_sorted.columns: df_sorted = df_sorted.drop(columns=['_date_parsed'])
            production_logs[product] = df_sorted
    except: pass

    st.session_state.production_logs_cache = production_logs
    st.session_state.production_logs_cache_key = cache_key
    
    if planner:
        for product, df in production_logs.items():
            if not df.empty:
                planner.production_logs[product] = df.to_dict('records')
    
    keys = ['saddle_logs_cache', 'material_logs_cache', 'inventory_chart_cache', 'material_inventory_data']
    for k in list(st.session_state.keys()):
        if k in keys or (k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key'):
            del st.session_state[k]
            
    return production_logs
