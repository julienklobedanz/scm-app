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
from ui.utils import initialize_session_state, create_simulator, run_happy_path_simulation

st.set_page_config(page_title="App", layout="wide", page_icon="📊")

# Theme Toggle (oben rechts, global)
# Theme-Toggle entfernt - Light Mode ist Standard
from ui.theme_toggle import apply_theme
apply_theme("light")  # Light Mode immer aktiv

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

# PERFORMANCE: Happy Path Simulation automatisch starten wenn noch keine Ergebnisse vorhanden
# (ähnlich wie in anderen Seiten, z.B. pages/1_reporting.py)
# PERFORMANCE: Prüfe ob Simulation läuft bevor run_happy_path_simulation() aufgerufen wird
if not st.session_state.get('simulation_running', False):
    run_happy_path_simulation()
else:
    # Simulation läuft bereits - zeige Info und warte
    import time
    elapsed = time.time() - st.session_state.get('simulation_start_time', time.time())
    st.info(f"🔄 Simulation läuft... Bitte warten Sie ({int(elapsed)}s)")
    st.stop()

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
if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar. Die Simulation wird gestartet...")
    st.stop()

if 'simulator' not in st.session_state or st.session_state.simulator is None:
    st.warning("⚠️ Simulator nicht verfügbar. Bitte warten Sie, bis die Simulation abgeschlossen ist...")
    st.stop()

if st.session_state.results_df is not None and 'simulator' in st.session_state:
    results_df = st.session_state.results_df
    simulator = st.session_state.simulator
    
    # ============================================================================
    # SCOR METRIKEN BERECHNEN
    # ============================================================================
    
    # PERFORMANCE: Hole Inbound-DF einmalig (wird für mehrere Metriken benötigt)
    transport_manager = simulator.china_transport_manager
    saddle_shares = MasterData.calculate_saddle_shares()
    
    # PERFORMANCE: Cache für Inbound-DF prüfen
    inbound_df_cache_key = 'scor_inbound_df_cache'
    inbound_df_hash_key = 'scor_inbound_df_hash'
    
    # Erstelle Hash für Cache-Validierung
    current_hash = None
    if transport_manager:
        try:
            import hashlib
            # Hash aus Anzahl Transporte und Szenarien
            transport_count = len(transport_manager.transport_status) if hasattr(transport_manager, 'transport_status') else 0
            scenario_fingerprint = str(st.session_state.get('scenario_manager', None))
            hash_input = f"{transport_count}_{scenario_fingerprint}"
            current_hash = hashlib.md5(hash_input.encode()).hexdigest()
        except:
            pass
    
    # Cache ist gültig wenn Hash gleich ist
    if (inbound_df_cache_key in st.session_state and 
        inbound_df_hash_key in st.session_state and
        st.session_state[inbound_df_hash_key] == current_hash and
        current_hash is not None):
        inbound_df = st.session_state[inbound_df_cache_key]
    else:
        # Berechne Inbound-DF einmalig
        inbound_df = transport_manager.get_inbound_log_dataframe(saddle_shares)
        # Cache speichern
        st.session_state[inbound_df_cache_key] = inbound_df
        if current_hash:
            st.session_state[inbound_df_hash_key] = current_hash
    
    # PERFORMANCE: Hole Supplier-Log einmalig (wird für Maschinenausfall benötigt)
    supplier_df_cache_key = 'scor_supplier_df_cache'
    supplier_df_hash_key = 'scor_supplier_df_hash'
    
    if (supplier_df_cache_key in st.session_state and 
        supplier_df_hash_key in st.session_state and
        st.session_state[supplier_df_hash_key] == current_hash and
        current_hash is not None):
        supplier_df = st.session_state[supplier_df_cache_key]
    else:
        # Hole Supplier-Log für ersten Sattel (Störung ist global)
        supplier_df = None
        if saddle_shares:
            first_saddle = next(iter(saddle_shares))
            supplier_df = transport_manager.get_supplier_log_dataframe(first_saddle, saddle_shares[first_saddle])
            st.session_state[supplier_df_cache_key] = supplier_df
            if current_hash:
                st.session_state[supplier_df_hash_key] = current_hash
    
    # 1. Perfect Order Fulfillment (Inbound)
    col_header1, col_help1 = st.columns([20, 1])
    with col_header1:
        st.header("Perfect Order Fulfillment (Inbound)")
    with col_help1:
        st.markdown("""
        <div style="margin-top: 1.5rem;">
            <span title="Berechnung: Perfekte Lieferungen = (Gesamtlieferungen - Fehler) / Gesamtlieferungen × 100%. 
Fehler sind: Totalausfall (Ladungsverlust = 'Ja', keine Ware angekommen), Verspätung (Verspätung = 'Ja', tatsächliche Ankunft > geplante Ankunft). 
Hinweis: Mengenverlust (Teilmengen) wird aktuell nicht separat erfasst, nur Vollverlust zählt als Totalausfall. 
Die Metrik reagiert auf Szenarien wie Verspätungen, Ladungsverlust und Maschinenausfall." 
            style="cursor: help; color: #6b7280; font-size: 1.2rem; display: inline-block;">ℹ️</span>
        </div>
        """, unsafe_allow_html=True)
    
    def calculate_inbound_metrics_from_table():
        """POF aus der Inbound-Tabelle (Single Source of Truth, reagiert auf Szenarien)."""
        from datetime import datetime
        # PERFORMANCE: Verwende gecachte inbound_df und supplier_df (bereits oben geladen)
        df = inbound_df
        # supplier_df ist bereits oben geladen und als Closure-Variable verfügbar
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
        # PERFORMANCE: Prüfe ob Spalte existiert
        if abfahrt_col not in df.columns:
            return {'China': {
                'Anzahl Lieferungen': 0, 'Anzahl Lieferungen mit Totalausfall': 0,
                'Anzahl Lieferungen mit Mengenverlust': 0, 'verspätete Lieferungen': 0,
                'Perfekte Lieferungen in %': 100.0,
                'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': 0.0,
                'Anzahl von Tagen eines Maschinenausfalls': 0
            }}
        shipment_mask = df[abfahrt_col].notna() & (df[abfahrt_col].astype(str).str.strip() != '')
        shipments_df = df[shipment_mask]
        total = len(shipments_df)
        if total == 0:
            downtime_days = 0
            # PERFORMANCE: Verwende gecachte supplier_df (bereits oben geladen)
            if supplier_df is not None and not supplier_df.empty and 'Störung' in supplier_df.columns:
                stoerung = supplier_df['Störung'].astype(str).str.strip().str.lower()
                downtime_days = int((stoerung == 'ja').sum())
            return {'China': {
                'Anzahl Lieferungen': 0, 'Anzahl Lieferungen mit Totalausfall': 0,
                'Anzahl Lieferungen mit Mengenverlust': 0, 'verspätete Lieferungen': 0,
                'Perfekte Lieferungen in %': 100.0,
                'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': 0.0,
                'Anzahl von Tagen eines Maschinenausfalls': downtime_days
            }}
        # Totalausfall: Ladungsverlust = 'Ja' (Vollverlust). Mengenverlust (Teilmengen) wird aktuell nicht separat erfasst, nur Vollverlust zählt als Totalausfall.
        # PERFORMANCE: Prüfe ob Spalten existieren
        fail_total = 0
        fail_time = 0
        if 'Ladungsverlust' in shipments_df.columns:
            loss_str = shipments_df['Ladungsverlust'].astype(str).str.strip().str.lower()
            fail_total = int((loss_str == 'ja').sum())
        # Verspätung: Verspätung = 'Ja'
        if 'Verspätung' in shipments_df.columns:
            delay_str = shipments_df['Verspätung'].astype(str).str.strip().str.lower()
            fail_time = int((delay_str == 'ja').sum())
        # Durchschnitt Verspätung in Tagen (Geplante vs. Tatsächliche Ankunft LKW DE)
        planned_col = 'Geplante Ankunft LKW 🇩🇪'
        actual_col = 'Tatsächliche Ankunft LKW 🇩🇪'
        fmt = MasterData.DATE_FORMAT
        delay_days_list = []
        # PERFORMANCE: Prüfe ob Spalten für Verspätungsberechnung existieren
        if planned_col in shipments_df.columns and actual_col in shipments_df.columns and 'Verspätung' in shipments_df.columns:
            delay_str = shipments_df['Verspätung'].astype(str).str.strip().str.lower()
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
        error_count = min(fail_total + fail_time, total)
        pct_perfect = ((total - error_count) / total * 100) if total > 0 else 100.0
        # Maschinenausfall aus Lieferant-China-Tabelle (Spalte „Störung“), ein Sattel reicht (Störung global)
        # PERFORMANCE: Verwende gecachte supplier_df (bereits oben geladen, als Closure-Variable verfügbar)
        downtime_days = 0
        if supplier_df is not None and not supplier_df.empty and 'Störung' in supplier_df.columns:
            stoerung = supplier_df['Störung'].astype(str).str.strip().str.lower()
            downtime_days = int((stoerung == 'ja').sum())
        return {'China': {
            'Anzahl Lieferungen': total,
            'Anzahl Lieferungen mit Totalausfall': fail_total,
            'verspätete Lieferungen': fail_time,
            'Perfekte Lieferungen in %': round(pct_perfect, 2),
            'durchschnittliche Anzahl von Tagen der verspäteten Lieferungen': round(avg_delay, 2),
            'Anzahl von Tagen eines Maschinenausfalls': downtime_days
        }}
    
    inbound_metrics = calculate_inbound_metrics_from_table()
    inbound_metrics_df = pd.DataFrame(inbound_metrics).T
    # Formatierung: Ganze Zahlen für Zählungen, 2 Dezimalstellen für % und Durchschnitt
    for col in inbound_metrics_df.columns:
        if '%' not in col and 'durchschnittliche' not in col:
            inbound_metrics_df[col] = inbound_metrics_df[col].astype(int)
        else:
            inbound_metrics_df[col] = inbound_metrics_df[col].round(2)
    st.dataframe(inbound_metrics_df, width='stretch')
    
    st.divider()
    
    # 2. Source Cycle Time
    col_header2, col_help2 = st.columns([20, 1])
    with col_header2:
        st.header("Source Cycle Time")
    with col_help2:
        st.markdown("""
        <div style="margin-top: 1.5rem;">
            <span title="Berechnung: Durchschnittliche Lieferzeit von China nach Deutschland. 
Für jede Lieferung: Lieferzeit = Tatsächliche Ankunft LKW Deutschland - Abfahrt LKW China (in Tagen). 
Der Durchschnitt wird über alle Lieferungen berechnet. 
Reagiert auf Verspätungs-Szenarien." 
            style="cursor: help; color: #6b7280; font-size: 1.2rem; display: inline-block;">ℹ️</span>
        </div>
        """, unsafe_allow_html=True)
    
    def calculate_source_cycle_time_from_table():
        """SCT aus der Inbound-Tabelle: Schnellste/langsamste/durchschnittliche Lieferzeit = Tatsächliche Ankunft LKW DE − Abfahrt LKW China (in Tagen)."""
        from datetime import datetime
        # WICHTIG: Vollständige Inbound-Log-Tabelle verwenden (nicht die POF-Metriken-Tabelle)
        df = inbound_df
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
        # PERFORMANCE: Prüfe ob Spalten existieren
        if abfahrt_col not in df.columns or ankunft_col not in df.columns:
            return {'China': {
                'Vorlaufzeit in Tagen (Soll)': lead_time,
                'Schnellste Lieferung in Tagen': lead_time,
                'Langsamste Lieferung in Tagen': lead_time,
                'Durchschnittliche Lieferzeit in Tagen': float(lead_time)
            }}
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
    
    # 3. Pipeline-Bestand (VERSTECKT - temporär ausgeblendet)
    # Die gesamte Pipeline-Bestand-Logik wurde temporär ausgeblendet
    pass
    
else:
    st.info("🔄 Die Simulation wird automatisch gestartet...")
