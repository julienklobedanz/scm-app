"""
SCM App - Supply Chain Simulation
Hauptseite mit SCOR-Metriken
"""

import streamlit as st
import pandas as pd
from datetime import date
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from config.master_data import MasterData
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, create_simulator

st.set_page_config(page_title="App", layout="wide", page_icon="📊")

# CSS für Menü-Formatierung (Großbuchstaben und Fett)
st.markdown("""
<style>
    /* Menüeinträge großgeschrieben und fett */
    [data-testid="stSidebarNav"] a {
        font-weight: bold !important;
        text-transform: capitalize !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialisiere Session State
initialize_session_state()

# WICHTIG: Happy Path Simulation SOFORT beim Start ausführen (vor dem Rendering)
# Dies stellt sicher, dass die Simulation im Hintergrund läuft, auch wenn keine Page geöffnet wird
from ui.utils import run_happy_path_simulation
run_happy_path_simulation()

st.title("📊 SCOR Metriken")
st.markdown("Supply Chain Operations Reference (SCOR) Metriken")

# Szenarien-Sidebar rendern
render_scenario_sidebar(key_suffix="_app")

# Simulation ausführen (für manuellen Neustart)
if st.session_state.get('run_simulation', False):
    try:
        # Setze Flags zurück für Neustart
        st.session_state.happy_path_run = False
        st.session_state.results_df = None
        st.session_state.simulator = None
        st.session_state.simulation_running = False
        st.session_state.simulation_started = False
        
        with st.spinner("Simulation läuft..."):
            simulator = create_simulator()
            results_df, kpis = simulator.run()
            st.session_state.results_df = results_df
            st.session_state.kpis = kpis
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
            st.session_state.run_simulation = False
            st.success("✅ Simulation erfolgreich abgeschlossen!")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.run_simulation = False

# Ergebnisse anzeigen
if st.session_state.results_df is not None and 'simulator' in st.session_state:
    results_df = st.session_state.results_df
    simulator = st.session_state.simulator
    
    # ============================================================================
    # SCOR METRIKEN BERECHNEN
    # ============================================================================
    
    # 1. Perfect Order Fulfillment (Inbound)
    st.header("Perfect Order Fulfillment (Inbound)")
    
    def calculate_inbound_metrics():
        """Berechnet Inbound-Metriken für alle Lieferanten"""
        inbound_metrics = {}
        
        # Nur China (Deutschland und Spanien entfernt, da wir nur einen Lieferanten haben)
        suppliers = ['China']
        
        for supplier in suppliers:
            if supplier == 'China':
                transport_manager = simulator.china_transport_manager
                transport_status = transport_manager.transport_status
                
                # Analysiere alle Transporte
                total_deliveries = 0
                total_failures = 0
                quantity_losses = 0
                late_deliveries = 0
                late_delivery_days = []
                machine_downtime_days = 0
                
                # Zähle Versendungen (shipped = True)
                shipments = {}
                for (order_day, order_id), status in transport_status.items():
                    if status.get('shipped', False):
                        ship_day = status.get('ship_departure_day')
                        if ship_day is not None:
                            if ship_day not in shipments:
                                shipments[ship_day] = []
                            shipments[ship_day].append(status)
                
                # Analysiere jede Versendung
                for ship_day, status_list in shipments.items():
                    for status in status_list:
                        if status.get('received', False):
                            total_deliveries += 1
                            
                            # Prüfe auf Totalausfall (100% Verlust)
                            original_qty = status.get('quantity', 0.0)
                            actual_qty = status.get('actual_quantity', 0.0)
                            if actual_qty <= 0 and original_qty > 0:
                                total_failures += 1
                            
                            # Prüfe auf Mengenverlust (0 < actual < original)
                            elif actual_qty < original_qty and original_qty > 0:
                                quantity_losses += 1
                            
                            # Prüfe auf Verspätung
                            if status.get('available_day') is not None and status.get('order_day') is not None:
                                # Erwartete Lead Time: 49 Tage (Standard)
                                expected_days = 49
                                actual_days = status['available_day'] - status['order_day']
                                if actual_days > expected_days:
                                    late_deliveries += 1
                                    late_delivery_days.append(actual_days - expected_days)
                            
                            # Maschinenausfall: Wenn production_loss_percentage > 0
                            if status.get('production_loss_percentage', 0.0) > 0:
                                machine_downtime_days += 1
                
                perfect_deliveries_pct = ((total_deliveries - total_failures - quantity_losses - late_deliveries) / total_deliveries * 100) if total_deliveries > 0 else 100.0
                avg_late_days = sum(late_delivery_days) / len(late_delivery_days) if late_delivery_days else 0.0
                
                inbound_metrics[supplier] = {
                    'Anzahl Lieferungen': total_deliveries,
                    'Anzahl Lieferungen mit Totalausfall': total_failures,
                    'Anzahl Lieferungen mit Mengenverlust': quantity_losses,
                    'verspätete Lieferungen': late_deliveries,
                    'Perfekte Lieferungen in %': round(perfect_deliveries_pct, 2),
                    'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': round(avg_late_days, 2) if late_deliveries > 0 else 0.0,
                    'Anzahl von Tagen eines Maschinenausfalls': machine_downtime_days
                }
        
        return inbound_metrics
    
    inbound_metrics = calculate_inbound_metrics()
    inbound_df = pd.DataFrame(inbound_metrics).T
    # Formatierung: Ganze Zahlen für Zählungen, 2 Dezimalstellen für % und Durchschnitt
    for col in inbound_df.columns:
        if '%' not in col and 'durchschnittliche' not in col:
            inbound_df[col] = inbound_df[col].astype(int)
        else:
            inbound_df[col] = inbound_df[col].round(2)
    st.dataframe(inbound_df, width='stretch')
    
    st.divider()
    
    # 2. Source Cycle Time
    st.header("Source Cycle Time")
    
    def calculate_source_cycle_time():
        """Berechnet Source Cycle Time für alle Lieferanten"""
        source_metrics = {}
        
        # Nur China (Deutschland und Spanien entfernt, da wir nur einen Lieferanten haben)
        suppliers = ['China']
        
        for supplier in suppliers:
            if supplier == 'China':
                transport_manager = simulator.china_transport_manager
                transport_status = transport_manager.transport_status
                
                lead_time = MasterData.SUPPLIERS[supplier]['lead_time']
                delivery_times = []
                
                for (order_day, order_id), status in transport_status.items():
                    if status.get('received', False) and status.get('available_day') is not None:
                        actual_days = status['available_day'] - status['order_day']
                        delivery_times.append(actual_days)
                
                if delivery_times:
                    fastest = min(delivery_times)
                    slowest = max(delivery_times)
                    avg = sum(delivery_times) / len(delivery_times)
                else:
                    fastest = lead_time
                    slowest = lead_time
                    avg = lead_time
                
                source_metrics[supplier] = {
                    'Vorlaufzeit in Tagen': lead_time,
                    'Schnellste Lieferung in Tagen': fastest,
                    'Langsamste Lieferung in Tagen': slowest,
                    'Durchschnittliche Lieferzeit in Tagen': round(avg, 2)
                }
        
        return source_metrics
    
    source_metrics = calculate_source_cycle_time()
    source_df = pd.DataFrame(source_metrics).T
    # Formatierung: Ganze Zahlen für Tage, 2 Dezimalstellen für Durchschnitt
    for col in source_df.columns:
        if 'durchschnittliche' in col.lower():
            source_df[col] = source_df[col].round(2)
        else:
            source_df[col] = source_df[col].astype(int)
    st.dataframe(source_df, width='stretch')
    
    st.divider()
    
    # 3. Produktionsmetriken
    st.header("Produktionsmetriken")
    
    def calculate_production_metrics():
        """Berechnet Produktionsmetriken"""
        # Hole Produktionslogs
        planner = simulator.production_planner
        if not hasattr(planner, 'production_logs') or not planner.production_logs:
            return {}
        
        production_logs = planner.production_logs
        
        # Berechne Gesamtmetriken
        total_produced = 0.0
        total_planned = 0.0
        total_demand = 0.0
        total_backlog_end = 0.0
        days_with_production = 0
        days_stopped_materials = 0
        utilization_sum = 0.0
        utilization_count = 0
        
        # OPTIMIERUNG: Nutze bereits berechnete Nachfrage aus Session State (nicht neu berechnen!)
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
        # Falls nicht vorhanden, verwende leeres Dict (verhindert Neuberechnung)
        if not daily_demands_actual:
            daily_demands_actual = {}
        
        for day in range(365):
            day_total_produced = 0.0
            day_total_planned = 0.0
            day_total_demand = 0.0
            day_utilization = 0.0
            day_materials_complete = True
            
            # Summiere über alle Produkte
            for product, logs in production_logs.items():
                if logs and day < len(logs):
                    log_entry = logs[day]
                    day_total_produced += log_entry.get('tatsächliche PM', 0.0)
                    day_total_planned += log_entry.get('geplante PM', 0.0)
                    
                    # Auslastung (nur wenn geplante PM > 0)
                    if log_entry.get('geplante PM', 0) > 0:
                        util = log_entry.get('Auslastung (%)', 0.0)
                        if isinstance(util, (int, float)) and util > 0:
                            day_utilization = max(day_utilization, util)
                    
                    # Materialien vollständig?
                    if log_entry.get('Materialien vollständig?', 'Ja') != 'Ja':
                        day_materials_complete = False
            
            # Nachfrage für diesen Tag
            day_demand = daily_demands_actual.get(day, {})
            day_total_demand = sum(day_demand.values()) if isinstance(day_demand, dict) else 0.0
            
            total_produced += day_total_produced
            total_planned += day_total_planned
            total_demand += day_total_demand
            
            if day_total_produced > 0:
                days_with_production += 1
            
            if not day_materials_complete:
                days_stopped_materials += 1
            
            if day_utilization > 0:
                utilization_sum += day_utilization
                utilization_count += 1
        
        # Backlog am Ende (letzter Tag)
        for product, logs in production_logs.items():
            if logs and len(logs) > 0:
                last_log = logs[-1]
                total_backlog_end += last_log.get('Backlog', 0.0)
        
        # Berechne Durchschnitte
        avg_utilization = (utilization_sum / utilization_count) if utilization_count > 0 else 0.0
        avg_daily_production = (total_produced / days_with_production) if days_with_production > 0 else 0.0
        
        # Service Level
        service_level = (total_produced / total_demand * 100) if total_demand > 0 else 0.0
        
        # Planabweichung
        plan_deviation_pct = ((total_produced - total_planned) / total_planned * 100) if total_planned > 0 else 0.0
        
        return {
            'Gesamtproduktion': int(round(total_produced)),
            'Geplante Produktion': int(round(total_planned)),
            'Gesamtnachfrage': int(round(total_demand)),
            'Service Level (%)': round(service_level, 2),
            'Planabweichung (%)': round(plan_deviation_pct, 2),
            'Durchschnittliche Auslastung (%)': round(avg_utilization, 2),
            'Durchschnittliche Tagesproduktion': int(round(avg_daily_production)),
            'Produktionstage': days_with_production,
            'Tage mit Materialmangel': days_stopped_materials,
            'Backlog am Jahresende': int(round(total_backlog_end))
        }
    
    production_metrics = calculate_production_metrics()
    if production_metrics:
        # Erstelle DataFrame (eine Zeile)
        production_df = pd.DataFrame([production_metrics])
        # Formatierung: Ganze Zahlen für Zählungen, 2 Dezimalstellen für %
        for col in production_df.columns:
            if '%' in col or 'Auslastung' in col:
                production_df[col] = production_df[col].round(2)
            else:
                production_df[col] = production_df[col].astype(int)
        st.dataframe(production_df, width='stretch', hide_index=True)
    else:
        st.info("Keine Produktionsmetriken verfügbar.")

else:
    st.info("🔄 Die Simulation wird automatisch gestartet...")
