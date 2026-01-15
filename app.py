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
render_scenario_sidebar()

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
        
        # Lieferanten aus MasterData
        suppliers = ['Deutschland', 'Spanien', 'China']
        
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
            else:
                # Deutschland und Spanien: Aktuell keine Implementierung (Rahmen sind unbegrenzt)
                inbound_metrics[supplier] = {
                    'Anzahl Lieferungen': 0,
                    'Anzahl Lieferungen mit Totalausfall': 0,
                    'Anzahl Lieferungen mit Mengenverlust': 0,
                    'verspätete Lieferungen': 0,
                    'Perfekte Lieferungen in %': 100.0,
                    'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': 0.0,
                    'Anzahl von Tagen eines Maschinenausfalls': 0
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
    
    # 2. Perfect Order Fulfillment (Outbound)
    st.header("Perfect Order Fulfillment (Outbound)")
    
    def calculate_outbound_metrics():
        """Berechnet Outbound-Metriken für alle Märkte"""
        outbound_metrics = {}
        
        # Märkte aus MasterData
        market_names = {
            'DE': 'Deutschland',
            'USA': 'USA',
            'FR': 'Frankreich',
            'CN': 'China',
            'CH': 'Schweiz',
            'AT': 'Österreich'
        }
        
        backlog = simulator.backlog
        
        # Zähle Versendungen pro Markt
        shipments_by_market = {code: 0 for code in market_names.keys()}
        
        # Zähle alle Versendungen aus in_transit
        for day, market_dict in backlog.in_transit.items():
            for market_code in market_dict.keys():
                if market_code in shipments_by_market:
                    shipments_by_market[market_code] += 1
        
        # Fallback: Wenn keine Daten, schätze basierend auf Produktion
        total_production_days = len(results_df[results_df['Actual_Build'] > 0])
        
        for market_code, market_name in market_names.items():
            total_deliveries = shipments_by_market.get(market_code, 0)
            
            # Wenn keine Daten, schätze basierend auf Marktanteil
            if total_deliveries == 0:
                market_share = MasterData.MARKETS[market_code]['share']
                total_deliveries = int(total_production_days * market_share)
            
            # Vereinfacht: Keine Fehler im Outbound (aktuell keine Szenarien)
            total_failures = 0
            quantity_losses = 0
            late_deliveries = 0
            perfect_deliveries_pct = 100.0
            
            outbound_metrics[market_name] = {
                'Anzahl Lieferungen': total_deliveries,
                'Anzahl Lieferungen mit Totalausfall': total_failures,
                'Anzahl Lieferungen mit Mengenverlust': quantity_losses,
                'verspätete Lieferungen': late_deliveries,
                'Perfekte Lieferungen in %': perfect_deliveries_pct
            }
        
        return outbound_metrics
    
    outbound_metrics = calculate_outbound_metrics()
    outbound_df = pd.DataFrame(outbound_metrics).T
    # Formatierung: Ganze Zahlen für Zählungen, 2 Dezimalstellen für %
    for col in outbound_df.columns:
        if '%' not in col:
            outbound_df[col] = outbound_df[col].astype(int)
        else:
            outbound_df[col] = outbound_df[col].round(2)
    st.dataframe(outbound_df, width='stretch')
    
    st.divider()
    
    # 3. Source Cycle Time
    st.header("Source Cycle Time")
    
    def calculate_source_cycle_time():
        """Berechnet Source Cycle Time für alle Lieferanten"""
        source_metrics = {}
        
        suppliers = ['Deutschland', 'Spanien', 'China']
        
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
            else:
                # Deutschland und Spanien
                lead_time = MasterData.SUPPLIERS[supplier]['lead_time']
                source_metrics[supplier] = {
                    'Vorlaufzeit in Tagen': lead_time,
                    'Schnellste Lieferung in Tagen': lead_time,
                    'Langsamste Lieferung in Tagen': lead_time,
                    'Durchschnittliche Lieferzeit in Tagen': lead_time
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
    
    # 4. Delivery Cycle Time
    st.header("Delivery Cycle Time")
    
    def calculate_delivery_cycle_time():
        """Berechnet Delivery Cycle Time für alle Märkte"""
        delivery_metrics = {}
        
        market_names = {
            'DE': 'Deutschland',
            'USA': 'USA',
            'FR': 'Frankreich',
            'CN': 'China',
            'CH': 'Schweiz',
            'AT': 'Österreich'
        }
        
        backlog = simulator.backlog
        
        for market_code, market_name in market_names.items():
            transit_days = MasterData.MARKETS[market_code]['transit_days']
            
            # Analysiere tatsächliche Transit-Zeiten aus in_transit
            delivery_times = []
            for day, market_dict in backlog.in_transit.items():
                if market_code in market_dict:
                    # Transit-Zeit ist die Differenz zwischen Versand-Tag und Ankunft-Tag
                    arrival_day = day
                    # Versand-Tag müsste aus results_df kommen (wenn produziert wurde)
                    # Vereinfacht: Nutze transit_days
                    delivery_times.append(transit_days)
            
            if not delivery_times:
                # Fallback: Nutze Standard-Transit-Zeit
                delivery_times = [transit_days]
            
            fastest = min(delivery_times)
            slowest = max(delivery_times)
            avg = sum(delivery_times) / len(delivery_times)
            
            delivery_metrics[market_name] = {
                'Schnellste Lieferung in Tagen': fastest,
                'Langsamste Lieferung in Tagen': slowest,
                'Durchschnittliche Lieferzeit in Tagen': round(avg, 2)
            }
        
        return delivery_metrics
    
    delivery_metrics = calculate_delivery_cycle_time()
    delivery_df = pd.DataFrame(delivery_metrics).T
    # Formatierung: Ganze Zahlen für Tage, 2 Dezimalstellen für Durchschnitt
    for col in delivery_df.columns:
        if 'durchschnittliche' in col.lower():
            delivery_df[col] = delivery_df[col].round(2)
        else:
            delivery_df[col] = delivery_df[col].astype(int)
    st.dataframe(delivery_df, width='stretch')
    
    st.divider()
    
    # 5. Order Fulfillment Cycle Time
    st.header("Order Fulfillment Cycle Time")
    st.markdown("Die gesamte Zeit von dem Zeitpunkt der Bestellung der Einzelteile bis hin zum Erreichen des Kunden im Zielland")
    
    def calculate_order_fulfillment_cycle_time():
        """Berechnet Order Fulfillment Cycle Time (Source + Delivery)"""
        fulfillment_metrics = {}
        
        market_names = {
            'DE': 'Deutschland',
            'USA': 'USA',
            'FR': 'Frankreich',
            'CN': 'China',
            'CH': 'Schweiz',
            'AT': 'Österreich'
        }
        
        # Kombiniere Source Cycle Time (China) + Delivery Cycle Time
        china_source_avg = source_metrics.get('China', {}).get('Durchschnittliche Lieferzeit in Tagen', 49)
        
        for market_code, market_name in market_names.items():
            delivery_avg = delivery_metrics.get(market_name, {}).get('Durchschnittliche Lieferzeit in Tagen', MasterData.MARKETS[market_code]['transit_days'])
            
            # Order Fulfillment = Source (China) + Delivery
            total_avg = china_source_avg + delivery_avg
            
            # Min/Max schätzen
            china_fastest = source_metrics.get('China', {}).get('Schnellste Lieferung in Tagen', 49)
            china_slowest = source_metrics.get('China', {}).get('Langsamste Lieferung in Tagen', 49)
            delivery_fastest = delivery_metrics.get(market_name, {}).get('Schnellste Lieferung in Tagen', MasterData.MARKETS[market_code]['transit_days'])
            delivery_slowest = delivery_metrics.get(market_name, {}).get('Langsamste Lieferung in Tagen', MasterData.MARKETS[market_code]['transit_days'])
            
            fastest = china_fastest + delivery_fastest
            slowest = china_slowest + delivery_slowest
            
            fulfillment_metrics[market_name] = {
                'Schnellste Lieferung in Tagen': fastest,
                'Langsamste Lieferung in Tagen': slowest,
                'Durchschnittliche Lieferzeit in Tagen': round(total_avg, 2)
            }
        
        return fulfillment_metrics
    
    fulfillment_metrics = calculate_order_fulfillment_cycle_time()
    fulfillment_df = pd.DataFrame(fulfillment_metrics).T
    # Formatierung: Ganze Zahlen für Tage, 2 Dezimalstellen für Durchschnitt
    for col in fulfillment_df.columns:
        if 'durchschnittliche' in col.lower():
            fulfillment_df[col] = fulfillment_df[col].round(2)
        else:
            fulfillment_df[col] = fulfillment_df[col].astype(int)
    st.dataframe(fulfillment_df, width='stretch')

else:
    st.info("🔄 Die Simulation wird automatisch gestartet...")
