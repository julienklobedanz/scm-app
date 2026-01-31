"""
SCM App - Supply Chain Simulation
Hauptseite mit SCOR-Metriken
"""

import streamlit as st
import pandas as pd
from datetime import date
from simulation.simulator import Simulator
from simulation.workday_calculator import WorkdayCalculator
from models.scenarios import ScenarioManager
from config.master_data import MasterData
from ui.scenario_sidebar import render_scenario_sidebar
from ui.utils import initialize_session_state, create_simulator

st.set_page_config(page_title="App", layout="wide", page_icon="📊")

# Theme Toggle (oben rechts, global)
from ui.theme_toggle import render_theme_toggle
render_theme_toggle()

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

# PERFORMANCE: Initialisiere Berechnungen nur wenn nötig (nicht beim App-Start)
# Dies verhindert lange Ladezeiten. Berechnungen werden lazy geladen wenn Seiten besucht werden.
# from ui.page_initialization import initialize_all_page_calculations
# initialize_all_page_calculations()  # DEAKTIVIERT für bessere Performance

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
    
    def calculate_inbound_metrics_from_table():
        """POF aus der Inbound-Tabelle (Single Source of Truth, reagiert auf Szenarien)."""
        from datetime import datetime
        transport_manager = simulator.china_transport_manager
        saddle_shares = MasterData.calculate_saddle_shares()
        df = transport_manager.get_inbound_log_dataframe(saddle_shares)
        if df.empty:
            return {'China': {
                'Anzahl Lieferungen': 0, 'Anzahl Lieferungen mit Totalausfall': 0,
                'Anzahl Lieferungen mit Mengenverlust': 0, 'verspätete Lieferungen': 0,
                'Perfekte Lieferungen in %': 100.0,
                'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': 0.0,
                'Anzahl von Tagen eines Maschinenausfalls': 0
            }}
        # Lieferungen = Zeilen mit Versand (Abfahrt LKW China gesetzt)
        abfahrt_col = 'Abfahrt LKW 🇨🇳'
        shipment_mask = df[abfahrt_col].notna() & (df[abfahrt_col].astype(str).str.strip() != '')
        shipments_df = df[shipment_mask]
        total = len(shipments_df)
        if total == 0:
            downtime_days = 0
            if saddle_shares:
                first_saddle = next(iter(saddle_shares))
                supplier_df = transport_manager.get_supplier_log_dataframe(first_saddle, saddle_shares[first_saddle])
                if not supplier_df.empty and 'Störung' in supplier_df.columns:
                    stoerung = supplier_df['Störung'].astype(str).str.strip().str.lower()
                    downtime_days = int((stoerung == 'ja').sum())
            return {'China': {
                'Anzahl Lieferungen': 0, 'Anzahl Lieferungen mit Totalausfall': 0,
                'Anzahl Lieferungen mit Mengenverlust': 0, 'verspätete Lieferungen': 0,
                'Perfekte Lieferungen in %': 100.0,
                'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': 0.0,
                'Anzahl von Tagen eines Maschinenausfalls': downtime_days
            }}
        # Totalausfall: Ladungsverlust = 'Ja' (Vollverlust). Mengenverlust nur bei Teilmengen – in der Tabelle nur Vollverlust.
        loss_str = shipments_df['Ladungsverlust'].astype(str).str.strip().str.lower()
        fail_total = int((loss_str == 'ja').sum())
        fail_qty = 0  # Inbound-Tabelle kennt nur Vollverlust (Ladungsverlust), kein Teilmengenverlust
        # Verspätung: Verspätung = 'Ja'
        delay_str = shipments_df['Verspätung'].astype(str).str.strip().str.lower()
        fail_time = int((delay_str == 'ja').sum())
        # Durchschnitt Verspätung in Tagen (Geplante vs. Tatsächliche Ankunft LKW DE)
        planned_col = 'Geplante Ankunft LKW 🇩🇪'
        actual_col = 'Tatsächliche Ankunft LKW 🇩🇪'
        fmt = MasterData.DATE_FORMAT
        delay_days_list = []
        delayed_shipments = shipments_df[delay_str == 'ja']
        for _, row in delayed_shipments.iterrows():
            try:
                p = row.get(planned_col, '')
                a = row.get(actual_col, '')
                if p and a and str(p).strip() and str(a).strip():
                    d_plan = datetime.strptime(str(p).strip(), fmt).date()
                    d_act = datetime.strptime(str(a).strip(), fmt).date()
                    delay_days = (d_act - d_plan).days
                    if delay_days > 0:  # Nur positive Verspätungen zählen
                        delay_days_list.append(delay_days)
            except (ValueError, TypeError) as e:
                # Debug: Zeige Fehler bei Parsing
                pass
        avg_delay = (sum(delay_days_list) / len(delay_days_list)) if delay_days_list else 0.0
        error_count = min(fail_total + fail_qty + fail_time, total)
        pct_perfect = ((total - error_count) / total * 100) if total > 0 else 100.0
        # Maschinenausfall aus Lieferant-China-Tabelle (Spalte „Störung“), ein Sattel reicht (Störung global)
        downtime_days = 0
        if saddle_shares:
            first_saddle = next(iter(saddle_shares))
            supplier_df = transport_manager.get_supplier_log_dataframe(first_saddle, saddle_shares[first_saddle])
            if not supplier_df.empty and 'Störung' in supplier_df.columns:
                stoerung = supplier_df['Störung'].astype(str).str.strip().str.lower()
                downtime_days = int((stoerung == 'ja').sum())
        return {'China': {
            'Anzahl Lieferungen': total,
            'Anzahl Lieferungen mit Totalausfall': fail_total,
            'Anzahl Lieferungen mit Mengenverlust': fail_qty,
            'verspätete Lieferungen': fail_time,
            'Perfekte Lieferungen in %': round(pct_perfect, 2),
            'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': round(avg_delay, 2),
            'Anzahl von Tagen eines Maschinenausfalls': downtime_days
        }}
    
    inbound_metrics = calculate_inbound_metrics_from_table()
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
    
    def calculate_source_cycle_time_from_table():
        """SCT aus der Inbound-Tabelle: Lieferzeit pro Zeile = Tatsächliche Ankunft − Abfahrt (in Tagen)."""
        from datetime import datetime
        transport_manager = simulator.china_transport_manager
        saddle_shares = MasterData.calculate_saddle_shares()
        df = transport_manager.get_inbound_log_dataframe(saddle_shares)
        lead_time = MasterData.SUPPLIERS['China']['lead_time']
        if df.empty:
            return {'China': {
                'Vorlaufzeit in Tagen (Soll)': lead_time,
                'Schnellste Lieferung in Tagen': lead_time,
                'Langsamste Lieferung in Tagen': lead_time,
                'Durchschnittliche Lieferzeit in Tagen': float(lead_time)
            }}
        abfahrt_col = 'Abfahrt LKW 🇨🇳'
        ankunft_col = 'Tatsächliche Ankunft LKW 🇩🇪'
        shipment_mask = df[abfahrt_col].notna() & (df[abfahrt_col].astype(str).str.strip() != '')
        shipments_df = df[shipment_mask]
        if shipments_df.empty:
            return {'China': {
                'Vorlaufzeit in Tagen (Soll)': lead_time,
                'Schnellste Lieferung in Tagen': lead_time,
                'Langsamste Lieferung in Tagen': lead_time,
                'Durchschnittliche Lieferzeit in Tagen': float(lead_time)
            }}
        fmt = MasterData.DATE_FORMAT
        cycle_times = []
        for _, row in shipments_df.iterrows():
            try:
                abfahrt = row.get(abfahrt_col, '')
                ankunft = row.get(ankunft_col, '')
                if abfahrt and ankunft:
                    d_abfahrt = datetime.strptime(str(abfahrt).strip(), fmt).date()
                    d_ankunft = datetime.strptime(str(ankunft).strip(), fmt).date()
                    tage = (d_ankunft - d_abfahrt).days
                    cycle_times.append(tage)
            except (ValueError, TypeError):
                pass
        if cycle_times:
            fastest = int(min(cycle_times))
            slowest = int(max(cycle_times))
            avg = sum(cycle_times) / len(cycle_times)
        else:
            fastest = lead_time
            slowest = lead_time
            avg = float(lead_time)
        return {'China': {
            'Vorlaufzeit in Tagen (Soll)': lead_time,
            'Schnellste Lieferung in Tagen': fastest,
            'Langsamste Lieferung in Tagen': slowest,
            'Durchschnittliche Lieferzeit in Tagen': round(avg, 2)
        }}
    
    source_metrics = calculate_source_cycle_time_from_table()
    source_df = pd.DataFrame(source_metrics).T
    # Formatierung: Ganze Zahlen für Tage, 2 Dezimalstellen für Durchschnitt
    for col in source_df.columns:
        if 'durchschnittliche' in col.lower():
            source_df[col] = source_df[col].round(2)
        else:
            source_df[col] = source_df[col].astype(int)
    st.dataframe(source_df, width='stretch')
    
    st.divider()
    
    # 3. Order Fulfillment Cycle Time
    st.header("Order Fulfillment Cycle Time")
    st.caption("Zeit von Bestellung bis Auslieferung an den Kunden (Bestellung → Materiallieferung → Produktion → Auslieferung)")
    
    def calculate_order_fulfillment_cycle_time():
        """OFCT: Zeit von Bestellung bis Auslieferung"""
        from datetime import datetime
        from ui.production_calculations import calculate_production_logs
        
        transport_manager = simulator.china_transport_manager
        saddle_shares = MasterData.calculate_saddle_shares()
        inbound_df = transport_manager.get_inbound_log_dataframe(saddle_shares)
        
        # Hole Produktionslogs
        production_logs_cache = calculate_production_logs()
        
        if inbound_df.empty or not production_logs_cache:
            return {}
        
        fmt = MasterData.DATE_FORMAT
        planning_year = st.session_state.get('planning_year', 2027)
        workday_calc = WorkdayCalculator(year=planning_year)
        
        # Sammle alle Bestelldaten aus der Inbound-Tabelle
        # Bestelldatum = Abfahrt LKW 🇨🇳 (oder früher, wenn bekannt)
        abfahrt_col = 'Abfahrt LKW 🇨🇳'
        shipment_mask = inbound_df[abfahrt_col].notna() & (inbound_df[abfahrt_col].astype(str).str.strip() != '')
        shipments_df = inbound_df[shipment_mask].copy()
        
        if shipments_df.empty:
            return {}
        
        # Berechne Order Fulfillment Cycle Time für jeden Markt
        ofct_by_market = {}
        
        for market_code, market_params in MasterData.MARKETS.items():
            transit_days = market_params.get('transit_days', 0)
            market_share = market_params.get('share', 0.0)
            
            cycle_times = []
            
            # Für jede Lieferung: Verfolge die gesamte Kette
            for _, row in shipments_df.iterrows():
                try:
                    # 1. Bestelldatum (Abfahrt LKW China)
                    order_date_str = str(row.get(abfahrt_col, '')).strip()
                    if not order_date_str:
                        continue
                    order_date = datetime.strptime(order_date_str, fmt).date()
                    order_day = (order_date - date(planning_year, 1, 1)).days
                    
                    # 2. Materiallieferung (Tatsächliche Ankunft LKW Deutschland)
                    arrival_col = 'Tatsächliche Ankunft LKW 🇩🇪'
                    arrival_date_str = str(row.get(arrival_col, '')).strip()
                    if not arrival_date_str:
                        continue
                    arrival_date = datetime.strptime(arrival_date_str, fmt).date()
                    arrival_day = (arrival_date - date(planning_year, 1, 1)).days
                    
                    # 3. Produktion: Finde ersten Produktionstag nach Materialankunft
                    # Verwende "fertiggestellte PM" aus production_logs
                    production_day = None
                    for product, df in production_logs_cache.items():
                        if df.empty or 'Datum' not in df.columns:
                            continue
                        
                        # Suche nach Produktionstag nach Materialankunft
                        for idx, prod_row in df.iterrows():
                            prod_date_str = prod_row.get('Datum', '')
                            if not prod_date_str:
                                continue
                            try:
                                prod_date = datetime.strptime(prod_date_str, fmt).date()
                                prod_day = (prod_date - date(planning_year, 1, 1)).days
                                
                                # Prüfe ob Material verwendet wurde (fertiggestellte PM > 0)
                                finished_pm = prod_row.get('fertiggestellte PM', 0)
                                try:
                                    finished_pm = float(finished_pm) if finished_pm else 0.0
                                except (ValueError, TypeError):
                                    finished_pm = 0.0
                                
                                if prod_day >= arrival_day and finished_pm > 0:
                                    if production_day is None or prod_day < production_day:
                                        production_day = prod_day
                                    break
                            except (ValueError, TypeError):
                                continue
                    
                    if production_day is None:
                        # Fallback: Verwende Materialankunftstag als Produktionstag
                        production_day = arrival_day
                    
                    # 4. Auslieferung: Produktionstag + Transit-Tage
                    delivery_day = production_day + transit_days
                    
                    # 5. Order Fulfillment Cycle Time = Auslieferung - Bestellung
                    ofct_days = delivery_day - order_day
                    if ofct_days > 0:
                        cycle_times.append(ofct_days)
                        
                except (ValueError, TypeError) as e:
                    continue
            
            if cycle_times:
                fastest = int(min(cycle_times))
                slowest = int(max(cycle_times))
                avg = sum(cycle_times) / len(cycle_times)
                
                # Marktname für Anzeige
                market_names = {
                    'DE': 'Deutschland',
                    'USA': 'USA',
                    'FR': 'Frankreich',
                    'CN': 'China',
                    'CH': 'Schweiz',
                    'AT': 'Österreich'
                }
                market_name = market_names.get(market_code, market_code)
                
                ofct_by_market[market_name] = {
                    'Transit-Tage (Soll)': transit_days,
                    'Schnellste Lieferung in Tagen': fastest,
                    'Langsamste Lieferung in Tagen': slowest,
                    'Durchschnittliche Lieferzeit in Tagen': round(avg, 2),
                    'Anzahl Lieferungen': len(cycle_times)
                }
        
        return ofct_by_market
    
    ofct_metrics = calculate_order_fulfillment_cycle_time()
    if ofct_metrics:
        ofct_df = pd.DataFrame(ofct_metrics).T
        # Formatierung: Ganze Zahlen für Tage, 2 Dezimalstellen für Durchschnitt
        for col in ofct_df.columns:
            if 'durchschnittliche' in col.lower():
                ofct_df[col] = ofct_df[col].round(2)
            else:
                ofct_df[col] = ofct_df[col].astype(int)
        st.dataframe(ofct_df, width='stretch')
    else:
        st.info("Keine Daten verfügbar für Order Fulfillment Cycle Time.")
    
else:
    st.info("🔄 Die Simulation wird automatisch gestartet...")
