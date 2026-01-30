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

# WICHTIG: Initialisiere ALLE Page-Berechnungen beim App-Start
# Dies stellt sicher, dass alle Caches verfügbar sind, bevor Seiten geladen werden
# Dadurch müssen Seiten nicht erst besucht werden, damit ihre Berechnungen starten
from ui.page_initialization import initialize_all_page_calculations
initialize_all_page_calculations()

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
        for _, row in shipments_df[delay_str == 'ja'].iterrows():
            try:
                p = row.get(planned_col, '')
                a = row.get(actual_col, '')
                if p and a:
                    d_plan = datetime.strptime(str(p).strip(), fmt).date()
                    d_act = datetime.strptime(str(a).strip(), fmt).date()
                    delay_days_list.append((d_act - d_plan).days)
            except (ValueError, TypeError):
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
    
else:
    st.info("🔄 Die Simulation wird automatisch gestartet...")
