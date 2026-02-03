"""
Stammdaten-Seite
Zeigt alle Stammdaten logisch gruppiert
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from models.scenarios import ScenarioManager
from ui.scenario_sidebar import render_scenario_sidebar
from ui.page_initialization import initialize_all_page_calculations


def _invalidate_all_caches():
    """
    Invalidiert alle relevanten Caches bei Parameteränderungen (inkl. Stückliste, Arbeitslast, Planung, Vorlaufzeit).
    Wird aufgerufen wenn Planungsparameter oder BOM-Zusammensetzung geändert werden.
    """
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
        'volume_planning_cache_key',
        # Simulation: Bei BOM-/Parameteränderung neu berechnen
        'simulation_cache',
        'results_df',
        'kpis',
        'simulator',
        'happy_path_run',
        'simulation_year',
        # KRITISCH: Lauf-Flags zurücksetzen, damit run_happy_path_simulation() neu startet (nicht "Simulation läuft..." blockiert)
        'simulation_running',
        'simulation_started',
        'simulation_start_time',
        # Materiallager/Inbound: abgeleitete Caches und erstes Datum
        'material_inventory_last_cache_key',
        'material_lager_first_date',
    ]
    
    for k in keys_to_delete:
        if k in st.session_state:
            del st.session_state[k]
    
    # Lösche auch alle dynamischen Cache-Keys die mit "material_inventory_" beginnen
    for k in list(st.session_state.keys()):
        if k.startswith('material_inventory_'):
            del st.session_state[k]
    
    # PERFORMANCE: Invalidiere auch Cache für geplante Ankunftsdaten
    planning_year = st.session_state.get('planning_year', 2027)
    for delay_stage in ["truck_china_arrival", "ship_arrival", "truck_de_arrival"]:
        cache_key = f"planned_arrival_dates_{delay_stage}_{planning_year}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    
    # Invalidiere auch ChinaTransportManager Caches (wenn Simulator vorhanden)
    # KRITISCH: Prüfe ob Simulator wirklich verfügbar ist (könnte None sein bei Fehlern)
    if 'simulator' in st.session_state and st.session_state.simulator is not None:
        if hasattr(st.session_state.simulator, 'china_transport_manager'):
            manager = st.session_state.simulator.china_transport_manager
            manager._supplier_log_cache = {}
            manager._inbound_df_cache = {}
            manager._inbound_df_cache_key = None

st.set_page_config(page_title="Stammdaten", layout="wide", page_icon="📋")

# Theme Toggle (oben rechts, global)
# Theme-Toggle entfernt - Light Mode ist Standard
from ui.theme_toggle import apply_theme
apply_theme("light")  # Light Mode immer aktiv

# PERFORMANCE: Stammdaten-Seite benötigt KEINE Simulation oder schwere Berechnungen
# Sie zeigt nur statische Daten. initialize_all_page_calculations() würde eine Simulation starten,
# was sehr langsam ist. Stattdessen initialisieren wir nur die Session State falls nötig.
from ui.utils import initialize_session_state
initialize_session_state()

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

# Szenarien-Sidebar rendern
render_scenario_sidebar(key_suffix="_stammdaten")

# Initialisiere ScenarioManager falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()

# FIX: Initialisiere editierbare Stammdaten in Session State
# WICHTIG: Bei Browser-Reload (wenn stammdaten_initialized nicht gesetzt ist) werden alle Werte auf Standard zurückgesetzt
def _reset_to_defaults():
    """Setzt alle editierbaren Parameter auf Standardwerte zurück"""
    # Standardwerte aus MasterData-Klassendefinition
    default_bom = {
        'MTB Allrounder': {'frame': 'Aluminium 7005DB', 'saddle': 'Spark', 'fork': 'Fox32 F100'},
        'MTB Competition': {'frame': 'Carbon Monocoque', 'saddle': 'Speed line', 'fork': 'Fox Talas140'},
        'MTB Downhill': {'frame': 'Aluminium 7005TB', 'saddle': 'Fizik Tundra', 'fork': 'Rock Schox Recon351'},
        'MTB Extreme': {'frame': 'Carbon Monocoque', 'saddle': 'Spark', 'fork': 'Rock Schox Reba'},
        'MTB Freeride': {'frame': 'Aluminium 7005TB', 'saddle': 'Fizik Tundra', 'fork': 'Fox32 F80'},
        'MTB Marathon': {'frame': 'Aluminium 7005DB', 'saddle': 'Race line', 'fork': 'Rock Schox ReconSL'},
        'MTB Performance': {'frame': 'Aluminium 7005TB', 'saddle': 'Fizik Tundra', 'fork': 'Rock Schox Reba'},
        'MTB Trail': {'frame': 'Carbon Monocoque', 'saddle': 'Speed line', 'fork': 'SR Suntour Raidon'}
    }
    default_global_config = {
        'total_volume': 370000,
        'capacity_per_hour': 130,
        'assembly_lines': 1,
        'min_shifts_per_day': 1,
        'max_shifts_per_day': 3,
        'working_hours_per_shift': 8,
        'batch_size': 1
    }
    default_daily_workload = {
        'Montag': 0.2, 'Dienstag': 0.2, 'Mittwoch': 0.2, 'Donnerstag': 0.2,
        'Freitag': 0.2, 'Samstag': 0.0, 'Sonntag': 0.0
    }
    default_product_sales_shares = {
        'MTB Allrounder': 0.30, 'MTB Competition': 0.15, 'MTB Downhill': 0.10,
        'MTB Extreme': 0.07, 'MTB Freeride': 0.05, 'MTB Marathon': 0.08,
        'MTB Performance': 0.12, 'MTB Trail': 0.13
    }
    default_seasonality = {
        1: 0.04, 2: 0.06, 3: 0.10, 4: 0.16, 5: 0.14, 6: 0.13,
        7: 0.12, 8: 0.09, 9: 0.06, 10: 0.03, 11: 0.04, 12: 0.03
    }
    
    # Setze Session State auf Standardwerte
    st.session_state.editable_bom = default_bom.copy()
    st.session_state.editable_global_config = default_global_config.copy()
    st.session_state.editable_daily_workload = default_daily_workload.copy()
    st.session_state.editable_product_sales_shares = default_product_sales_shares.copy()
    st.session_state.editable_seasonality = default_seasonality.copy()
    
    # KRITISCH: Synchronisiere auch MasterData mit Standardwerten
    MasterData.BOM = default_bom.copy()
    MasterData.GLOBAL_CONFIG = default_global_config.copy()
    MasterData.DAILY_WORKLOAD = default_daily_workload.copy()
    MasterData.PRODUCT_SALES_SHARES = default_product_sales_shares.copy()
    MasterData.SEASONALITY = default_seasonality.copy()
    
    # KRITISCH: Setze Beschaffungs-Parameter auf Standardwerte zurück
    # Lieferanten-Parameter (China)
    default_supplier_params = {
        'federal_state': 'Alle',
        'lead_time': 49,
        'order_entry_duration': 1,
        'production_time': 5,
        'lot_size': 500
    }
    MasterData.SUPPLIERS['China'] = default_supplier_params.copy()
    
    # CHINA_SUPPLIER Parameter synchronisieren
    MasterData.CHINA_SUPPLIER['Saddles']['lead_time'] = 49
    MasterData.CHINA_SUPPLIER['Saddles']['lot_size'] = 500
    MasterData.CHINA_SUPPLIER['Frames']['lead_time'] = 49
    MasterData.CHINA_SUPPLIER['Frames']['lot_size'] = 500
    
    # Beschaffungs-Routen auf Standardwerte zurücksetzen (duration aus MasterData, nicht standard_duration)
    # WICHTIG: Verwende die aktuellen duration-Werte aus MasterData.PROCUREMENT_ROUTES als Standard
    # Diese sind die korrekten Werte für die Berechnung (z.B. 30 KT für Schiff, nicht 22)
    default_procurement_routes = [
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'China', 'arrival': 'China', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT', 'standard_duration': 2},
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'China', 'arrival': 'Deutschland', 
         'transport': 'Schiff-Typ30', 'duration': 30, 'type': 'KT', 'standard_duration': 22},
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT', 'standard_duration': 2},
        {'supplier': 'Deutschland', 'component': 'Rahmen', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ3', 'duration': 3, 'type': 'AT', 'standard_duration': 3},
        {'supplier': 'Spanien', 'component': 'Gabel', 'departure': 'Spanien', 'arrival': 'Deutschland', 
         'transport': 'Bahn-Typ9', 'duration': 9, 'type': 'KT', 'standard_duration': 7}
    ]
    
    # Setze PROCUREMENT_ROUTES auf Standardwerte zurück (duration-Werte, nicht standard_duration)
    for i, route in enumerate(MasterData.PROCUREMENT_ROUTES):
        if i < len(default_procurement_routes):
            default_route = default_procurement_routes[i]
            # Setze duration auf den Standardwert (30 für Schiff, nicht 22)
            route['duration'] = default_route['duration']
            # Behalte standard_duration als Referenzwert
            if 'standard_duration' in default_route:
                route['standard_duration'] = default_route['standard_duration']
    
    # Synchronisiere auch yearly_volume
    st.session_state.yearly_volume = default_global_config['total_volume']

if 'stammdaten_initialized' not in st.session_state:
    _reset_to_defaults()
    st.session_state.stammdaten_initialized = True

st.title("📋 Stammdaten")
st.markdown("Alle Stammdaten der Supply Chain Simulation")

# Tabs für verschiedene Stammdaten-Gruppen
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Stückliste", 
    "📊 Planung", 
    "📥 Beschaffung", 
    "🌍 Märkte & Kunden",
    "📅 Feiertage"
])

with tab1:
    st.header("Stückliste")
    st.markdown("Produktstruktur aller Bike-Modelle - Zusammensetzung jedes Fahrrads")
    
    # Sammle alle verfügbaren Komponenten
    all_frames = sorted(set(comp['frame'] for comp in MasterData.BOM.values()))
    all_saddles = sorted(set(comp['saddle'] for comp in MasterData.BOM.values()))
    all_forks = sorted(set(comp['fork'] for comp in MasterData.BOM.values()))
    
    # Erstelle editierbare BOM-Tabelle
    bom_data = []
    for product in sorted(st.session_state.editable_bom.keys()):
        components = st.session_state.editable_bom[product]
        bom_data.append({
            'Endprodukt': product,
            'Rahmen': components['frame'],
            'Sattel': components['saddle'],
            'Gabel': components['fork']
        })
    bom_df = pd.DataFrame(bom_data)
    
    # Editierbare Tabelle mit Dropdowns
    edited_bom = st.data_editor(
        bom_df,
        column_config={
            "Endprodukt": st.column_config.TextColumn("Endprodukt", disabled=True),
            "Rahmen": st.column_config.SelectboxColumn("Rahmen", options=all_frames),
            "Sattel": st.column_config.SelectboxColumn("Sattel", options=all_saddles),
            "Gabel": st.column_config.SelectboxColumn("Gabel", options=all_forks)
        },
        width='stretch',
        hide_index=True,
        key="bom_editor"
    )
    
    # Speichere Änderungen in Session State (nur bei tatsächlichen Änderungen)
    if not edited_bom.equals(bom_df):
        changed = False
        for _, row in edited_bom.iterrows():
            product = row['Endprodukt']
            if product in st.session_state.editable_bom:
                old_comp = st.session_state.editable_bom[product]
                new_comp = {
                    'frame': row['Rahmen'],
                    'saddle': row['Sattel'],
                    'fork': row['Gabel']
                }
                if old_comp != new_comp:
                    st.session_state.editable_bom[product] = new_comp
                    changed = True
        if changed:
            # KRITISCH: Synchronisiere MasterData.BOM, damit die neue Zusammensetzung in der gesamten App wirkt
            MasterData.BOM = {p: {'frame': c['frame'], 'saddle': c['saddle'], 'fork': c['fork']}
                             for p, c in st.session_state.editable_bom.items()}
            # Cache-Invalidierung: Volumenplanung, Simulation, Produktion, Lieferant China, Material
            _invalidate_all_caches()
            st.success("✅ Stückliste aktualisiert! Volumenplanung und Simulation werden beim nächsten Aufruf neu berechnet.")
            # Kein st.rerun() - Streamlit aktualisiert automatisch

with tab2:
    st.header("Planungs-Parameter")
    
    # Planungsbeginn (aus Sidebar hierher verschoben)
    if 'planning_year' not in st.session_state:
        st.session_state.planning_year = 2027
    
    planning_year = st.number_input(
        "Planungsbeginn (Jahr)",
        min_value=2020,
        max_value=2030,
        value=st.session_state.planning_year,
        step=1,
        key="planning_year_stammdaten"
    )
    
    # Wenn Jahr geändert wurde, setze volume_planning_calculated zurück, damit neu berechnet wird
    # WICHTIG: Beende alte Simulation sauber und lade neue aus Cache, falls vorhanden
    if planning_year != st.session_state.planning_year:
        old_year = st.session_state.planning_year
        
        # KRITISCH: Beende alte Simulation sauber, wenn sie läuft
        if st.session_state.get('simulation_running', False):
            # Setze Flags zurück, um alte Simulation zu beenden
            st.session_state.simulation_running = False
            st.session_state.simulation_started = False
            st.info(f"🔄 Jahr geändert: Alte Simulation für {old_year} wurde beendet. Neue Simulation für {planning_year} wird gestartet...")
        
        # Jahr ändern
        st.session_state.planning_year = planning_year
        
        # Prüfe ob für das neue Jahr bereits ein Cache existiert
        simulation_cache = st.session_state.get('simulation_cache', {})
        if planning_year in simulation_cache and simulation_cache[planning_year].get('results_df') is not None:
            # Lade aus Cache - KEINE neue Berechnung nötig!
            cached_data = simulation_cache[planning_year]
            st.session_state.results_df = cached_data['results_df']
            st.session_state.kpis = cached_data.get('kpis')
            st.session_state.simulator = cached_data.get('simulator')
            st.session_state.happy_path_run = True
            st.session_state.simulation_running = False
            st.session_state.simulation_started = False
            st.session_state.simulation_year = planning_year
            st.success(f"✅ Simulation für {planning_year} wurde aus dem Cache geladen!")
        else:
            # Kein Cache vorhanden - setze Flags zurück für neue Berechnung
            st.session_state.volume_planning_calculated = False
            st.session_state.happy_path_run = False
            st.session_state.results_df = None
            st.session_state.simulation_year = None
            st.info(f"🔄 Simulation für {planning_year} wird neu berechnet...")
        
        # WICHTIG: Kein st.rerun() hier - die Seite wird automatisch neu geladen
    
    st.divider()
    
    # Weitere globale Konfigurationsparameter (editierbar) – 6 Parameter im Raster 3×2
    st.write("**Globale Konfigurationsparameter:**")
    param_translations = {
        'total_volume': 'Gesamtvolumen',
        'capacity_per_hour': 'Kapazität pro Stunde',
        'assembly_lines': 'Anzahl Montagelinien',
        'min_shifts_per_day': 'Min. Schichten/Tag',
        'max_shifts_per_day': 'Max. Schichten/Tag',
        'working_hours_per_shift': 'Anzahl Arbeitsstunden/Schicht',
    }
    
    # Definiere max_value pro Parameter (Losgröße nicht anzeigen)
    max_values = {
        'total_volume': 1000000,
        'capacity_per_hour': 500,
        'assembly_lines': 10,
        'min_shifts_per_day': 5,
        'max_shifts_per_day': 5,
        'working_hours_per_shift': 24,
    }
    
    # Feste Reihenfolge: Zeile 1 = Gesamtvolumen, Kapazität, Montagelinien | Zeile 2 = Min. Schichten, Max. Schichten, Arbeitsstunden/Schicht
    # WICHTIG: batch_size ist nicht in ordered_keys enthalten und wird daher nicht angezeigt
    ordered_keys = [
        'total_volume', 'capacity_per_hour', 'assembly_lines',
        'min_shifts_per_day', 'max_shifts_per_day', 'working_hours_per_shift'
    ]
    config_items = [(k, st.session_state.editable_global_config[k]) for k in ordered_keys if k in st.session_state.editable_global_config]
    config_changed = False
    
    def _render_config_input(key, value, param_translations, max_values):
        param_name = param_translations.get(key, key.replace('_', ' ').title())
        max_val = max_values.get(key, 1000)
        new_value = st.number_input(
            param_name,
            min_value=1 if key != 'total_volume' else 1000,
            max_value=max_val,
            value=int(value),
            step=1 if key != 'total_volume' else 1000,
            key=f"config_{key}"
        )
        return new_value
    
    # Zeile 1: 3 Spalten
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        key, value = config_items[0]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
            if key == 'total_volume':
                st.session_state.yearly_volume = new_value
                MasterData.GLOBAL_CONFIG['total_volume'] = new_value
    with row1_col2:
        key, value = config_items[1]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
    with row1_col3:
        key, value = config_items[2]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
    
    # Zeile 2: Min. Schichten, Max. Schichten, Arbeitsstunden/Schicht nebeneinander
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        key, value = config_items[3]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
    with row2_col2:
        key, value = config_items[4]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
    with row2_col3:
        key, value = config_items[5]
        new_value = _render_config_input(key, value, param_translations, max_values)
        if new_value != value:
            st.session_state.editable_global_config[key] = new_value
            config_changed = True
    
    if config_changed:
        st.success("✅ Globale Konfiguration aktualisiert!")
        
        # KRITISCH: Synchronisiere ALLE Parameter mit MasterData.GLOBAL_CONFIG
        # Nicht nur total_volume, sondern auch capacity_per_hour, working_hours_per_shift, etc.
        for key, value in st.session_state.editable_global_config.items():
            MasterData.GLOBAL_CONFIG[key] = value
        
        # Spezielle Synchronisation für total_volume (auch yearly_volume)
        if 'total_volume' in st.session_state.editable_global_config:
            st.session_state.yearly_volume = st.session_state.editable_global_config['total_volume']
        
        # Cache-Invalidierung bei Parameteränderungen
        _invalidate_all_caches()
        
        # Kein st.rerun() - Streamlit aktualisiert automatisch
    
    # Tägliche Arbeitslast (editierbar) – alle 7 Wochentage nebeneinander
    col_workload_title, col_workload_help = st.columns([20, 1])
    with col_workload_title:
        st.subheader("Tägliche Arbeitslast")
    with col_workload_help:
        st.markdown("""
        <div style="margin-top: 1.5rem;">
            <span title="Ein Wert von 0.0 bedeutet, dass dieser Wochentag wie ein freier Tag behandelt wird (kein Arbeitstag). Dies wird in allen abhängigen Berechnungen berücksichtigt."
                style="cursor: help; color: #6b7280; font-size: 1.2rem; display: inline-block;">ℹ️</span>
        </div>
        """, unsafe_allow_html=True)
    st.write("**Arbeitslast pro Wochentag in Prozent (0% = kein Arbeitstag):**")
    
    workload_changed = False
    weekday_cols = st.columns(5)
    
    # Nur Mo–Fr anzeigen (Sa/So werden intern weiterhin als 0% geführt)
    weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
    workload_values_pct = {}
    
    for i, day in enumerate(weekdays):
        with weekday_cols[i]:
            new_workload_pct = st.number_input(
                day,
                min_value=0,
                max_value=100,
                value=int(round(float(st.session_state.editable_daily_workload[day]) * 100)),
                step=1,
                key=f"workload_{day}"
            )
            workload_values_pct[day] = int(new_workload_pct)
            if (new_workload_pct / 100.0) != float(st.session_state.editable_daily_workload[day]):
                workload_changed = True
    
    # Berechne Wochensumme
    week_total_pct = sum(workload_values_pct.values())
    st.markdown(f"**Wochensumme (Mo–Fr): {week_total_pct:d}% (muss exakt 100% sein)**")
    
    # Validierung: Wochensumme muss genau 100% sein
    if workload_changed:
        if week_total_pct == 100:
            # Summe ist genau 100% - speichere Änderungen (als Dezimalwerte 0.0–1.0)
            for day, pct in workload_values_pct.items():
                st.session_state.editable_daily_workload[day] = pct / 100.0
            # Sa/So nicht editierbar: immer 0.0
            st.session_state.editable_daily_workload['Samstag'] = 0.0
            st.session_state.editable_daily_workload['Sonntag'] = 0.0
            
            # KRITISCH: Synchronisiere DAILY_WORKLOAD mit MasterData
            for day, workload in st.session_state.editable_daily_workload.items():
                MasterData.DAILY_WORKLOAD[day] = workload
            
            st.success("✅ Tägliche Arbeitslast aktualisiert!")
            
            # Cache-Invalidierung bei Parameteränderungen
            _invalidate_all_caches()
            
            # KRITISCH: Setze Simulator zurück, damit neue DAILY_WORKLOAD-Werte verwendet werden
            # Der WorkdayCalculator im Simulator muss die neuen Werte aus MasterData.DAILY_WORKLOAD lesen
            st.session_state.happy_path_run = False
            st.session_state.results_df = None
            st.session_state.simulator = None
            st.session_state.simulation_running = False
            st.session_state.simulation_started = False
        else:
            diff = abs(week_total_pct - 100)
            st.error(f"❌ **Wochensumme (Mo–Fr) beträgt {week_total_pct:d}% (Abweichung: {diff:d}%). Die Summe muss exakt 100% ergeben!**")
    
    # Verkaufsanteile (editierbar)
    st.subheader("Verkaufsanteile pro Produkt")
    st.write("**Verkaufsanteile in Prozent (Summe muss exakt 100% ergeben):**")
    
    # Berechne aktuelle Summe für Validierung
    current_total = sum(st.session_state.editable_product_sales_shares.values()) * 100
    
    # Warnung wenn Summe nicht 100%
    if abs(current_total - 100.0) >= 0.01:
        st.error(f"⚠️ **ACHTUNG:** Die Summe der Verkaufsanteile beträgt aktuell {current_total:.1f}%. Berechnungen können erst erfolgen, wenn die Summe exakt 100% beträgt!")
        st.info("💡 **Hinweis:** Bitte passen Sie die Werte unten an, bis die Summe genau 100% ergibt. Sie können auch die automatische Normalisierung verwenden.")
    
    # Editierbare Parameter – zwei Reihen à 4 Spalten
    sales_changed = False
    sales_values = {}
    
    products = sorted(st.session_state.editable_product_sales_shares.keys())
    
    # Zeile 1: erste 4 Produkte
    row1_cols = st.columns(4)
    for i, product in enumerate(products[:4]):
        with row1_cols[i]:
            current_share = st.session_state.editable_product_sales_shares[product]
            new_share = st.number_input(
                product,
                min_value=0.0,
                max_value=100.0,
                value=float(current_share * 100),
                step=0.1,
                format="%.1f",
                key=f"sales_{product}"
            )
            sales_values[product] = new_share
    
    # Zeile 2: restliche Produkte (bis zu 4)
    row2_products = products[4:8]
    if row2_products:
        row2_cols = st.columns(4)
        for i, product in enumerate(row2_products):
            with row2_cols[i]:
                current_share = st.session_state.editable_product_sales_shares[product]
                new_share = st.number_input(
                    product,
                    min_value=0.0,
                    max_value=100.0,
                    value=float(current_share * 100),
                    step=0.1,
                    format="%.1f",
                    key=f"sales_{product}"
                )
                sales_values[product] = new_share
    
    # Berechne neue Summe
    new_total = sum(sales_values.values())
    
    # Zeige aktuelle Summe
    st.markdown(f"**Aktuelle Summe: {new_total:.1f}%**")
    
    # Prüfe ob sich Werte geändert haben
    values_changed = any(
        abs(sales_values[p] - st.session_state.editable_product_sales_shares[p] * 100) >= 0.01
        for p in products
    )
    
    if values_changed:
        # Validierung: Summe muss genau 100% sein
        if abs(new_total - 100.0) < 0.01:  # Toleranz von 0.01%
            # Summe ist genau 100% - speichere Änderungen
            for product, percentage in sales_values.items():
                st.session_state.editable_product_sales_shares[product] = percentage / 100.0
            
            # KRITISCH: Synchronisiere PRODUCT_SALES_SHARES mit MasterData
            for product, share in st.session_state.editable_product_sales_shares.items():
                MasterData.PRODUCT_SALES_SHARES[product] = share
            
            st.success(f"✅ Verkaufsanteile aktualisiert! (Gesamt: {new_total:.1f}%)")
            sales_changed = True
        elif new_total > 0:
            # Summe ist nicht 100%, aber > 0
            diff = abs(new_total - 100.0)
            st.error(f"❌ **Summe beträgt {new_total:.1f}% (Abweichung: {diff:.1f}%). Die Summe muss exakt 100% ergeben, damit Berechnungen erfolgen können!**")
        else:
            st.error("❌ **Summe der Verkaufsanteile muss größer als 0 sein!**")
    
    if sales_changed:
        # Cache-Invalidierung bei Parameteränderungen
        _invalidate_all_caches()
    
    # Saisonalität (editierbar)
    st.subheader("Saisonaler Produktionsverlauf")
    st.write("**Produktionsanteil pro Monat in Prozent (Summe muss exakt 100% ergeben):**")
    
    month_names = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
    }
    
    # Berechne aktuelle Summe für Validierung
    current_total = sum(st.session_state.editable_seasonality.values()) * 100
    
    # Warnung wenn Summe nicht 100%
    if abs(current_total - 100.0) >= 0.01:
        st.error(f"⚠️ **ACHTUNG:** Die Summe der Produktionsanteile beträgt aktuell {current_total:.1f}%. Berechnungen können erst erfolgen, wenn die Summe exakt 100% beträgt!")
        st.info("💡 **Hinweis:** Bitte passen Sie die Werte unten an, bis die Summe genau 100% ergibt. Sie können auch die automatische Normalisierung verwenden.")
    
    # Editierbare Parameter – drei Reihen à 4 Spalten
    seasonality_changed = False
    seasonality_values = {}
    
    months = sorted(st.session_state.editable_seasonality.keys())
    
    # Zeile 1: Januar – April
    row1_cols = st.columns(4)
    for i, month in enumerate(months[:4]):
        with row1_cols[i]:
            month_name = month_names[month]
            current_factor = st.session_state.editable_seasonality[month]
            new_factor = st.number_input(
                month_name,
                min_value=0.0,
                max_value=100.0,
                value=float(current_factor * 100),
                step=0.1,
                format="%.1f",
                key=f"seasonality_{month}"
            )
            seasonality_values[month] = new_factor
    
    # Zeile 2: Mai – August
    row2_cols = st.columns(4)
    for i, month in enumerate(months[4:8]):
        with row2_cols[i]:
            month_name = month_names[month]
            current_factor = st.session_state.editable_seasonality[month]
            new_factor = st.number_input(
                month_name,
                min_value=0.0,
                max_value=100.0,
                value=float(current_factor * 100),
                step=0.1,
                format="%.1f",
                key=f"seasonality_{month}"
            )
            seasonality_values[month] = new_factor
    
    # Zeile 3: September – Dezember
    row3_cols = st.columns(4)
    for i, month in enumerate(months[8:12]):
        with row3_cols[i]:
            month_name = month_names[month]
            current_factor = st.session_state.editable_seasonality[month]
            new_factor = st.number_input(
                month_name,
                min_value=0.0,
                max_value=100.0,
                value=float(current_factor * 100),
                step=0.1,
                format="%.1f",
                key=f"seasonality_{month}"
            )
            seasonality_values[month] = new_factor
    
    # Berechne neue Summe
    new_total = sum(seasonality_values.values())
    
    # Zeige aktuelle Summe
    st.markdown(f"**Aktuelle Summe: {new_total:.1f}%**")
    
    # Prüfe ob sich Werte geändert haben
    values_changed = any(
        abs(seasonality_values[m] - st.session_state.editable_seasonality[m] * 100) >= 0.01
        for m in months
    )
    
    if values_changed:
        # Validierung: Summe muss genau 100% sein
        if abs(new_total - 100.0) < 0.01:  # Toleranz von 0.01%
            # Summe ist genau 100% - speichere Änderungen
            for month, percentage in seasonality_values.items():
                st.session_state.editable_seasonality[month] = percentage / 100.0
            
            # KRITISCH: Synchronisiere SEASONALITY mit MasterData
            for month, factor in st.session_state.editable_seasonality.items():
                MasterData.SEASONALITY[month] = factor
            
            st.success(f"✅ Saisonalität aktualisiert! (Gesamt: {new_total:.1f}%)")
            seasonality_changed = True
        elif new_total > 0:
            # Summe ist nicht 100%, aber > 0
            diff = abs(new_total - 100.0)
            st.error(f"❌ **Summe beträgt {new_total:.1f}% (Abweichung: {diff:.1f}%). Die Summe muss exakt 100% ergeben, damit Berechnungen erfolgen können!**")
        else:
            st.error("❌ **Summe der Produktionsanteile muss größer als 0 sein!**")
    
    if seasonality_changed:
        # Cache-Invalidierung bei Parameteränderungen
        _invalidate_all_caches()

with tab4:
    st.header("Märkte & Kunden")
    st.markdown("Zielmärkte und Marktverteilung")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Zielmärkte
        st.subheader("Zielmärkte")
        markets_data = []
        for market, params in MasterData.MARKETS.items():
            market_names = {
                'DE': 'Deutschland',
                'USA': 'USA',
                'FR': 'Frankreich',
                'CN': 'China',
                'CH': 'Schweiz',
                'AT': 'Österreich'
            }
            markets_data.append({
                'Land': market_names.get(market, market),
                'Code': market,
                'Anteil (%)': f"{params['share'] * 100:.1f}%",
                'Anteil (dezimal)': params['share'],
                'Transitzeit (Tage)': params['transit_days']
            })
        markets_df = pd.DataFrame(markets_data)
        st.dataframe(markets_df[['Land', 'Code', 'Anteil (%)', 'Transitzeit (Tage)']], width='stretch', hide_index=True)
    
    with col2:
        # Visualisierung Marktverteilung
        st.subheader("Marktverteilung")
        fig_markets = go.Figure(data=[go.Pie(
            labels=markets_df['Land'],
            values=markets_df['Anteil (dezimal)'] * 100,
            hole=0.3
        )])
        fig_markets.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_markets, width='stretch')

with tab3:
    st.header("Beschaffung")
    
    # Lieferanten-Parameter
    st.subheader("Lieferanten-Parameter")
    
    # Standard-Vorlaufzeit für Label (49 Tage)
    standard_lead_time = MasterData.CHINA_SUPPLIER['Saddles']['lead_time']
    
    suppliers_data = []
    # Nur China (Deutschland und Spanien entfernt)
    for supplier, params in MasterData.SUPPLIERS.items():
        if supplier == 'China':  # Nur China behalten
            suppliers_data.append({
                'Lieferant': supplier,
                'Bundesland/Region': params['federal_state'],
                'Vorlaufzeit (Tage)': params['lead_time'],
                'Dauer Auftragserfassung (Tage)': params['order_entry_duration'],
                'Produktionszeit (Tage)': params['production_time'],
                'Losgröße': params['lot_size']
            })
    if suppliers_data:
        # Zeige Tabelle mit statischen Werten
        suppliers_df = pd.DataFrame(suppliers_data)
        st.dataframe(suppliers_df[['Lieferant', 'Bundesland/Region']], width='stretch', hide_index=True)
        
        # Editierbare Parameter mit st.number_input() (wie Planungs-Parameter)
        supplier_changed = False
        china_params = MasterData.SUPPLIERS['China']
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_lead_time = st.number_input(
                "Vorlaufzeit (Tage)",
                min_value=1,
                max_value=365,
                value=int(china_params['lead_time']),
                step=1,
                key="supplier_lead_time"
            )
            new_order_entry = st.number_input(
                "Dauer Auftragserfassung (Tage)",
                min_value=1,
                max_value=30,
                value=int(china_params['order_entry_duration']),
                step=1,
                key="supplier_order_entry"
            )
        
        with col2:
            new_production_time = st.number_input(
                "Produktionszeit (Tage)",
                min_value=1,
                max_value=30,
                value=int(china_params['production_time']),
                step=1,
                key="supplier_production_time"
            )
            new_lot_size = st.number_input(
                "Losgröße",
                min_value=1,
                max_value=10000,
                value=int(china_params['lot_size']),
                step=1,
                key="supplier_lot_size"
            )
        
        # Prüfe auf Änderungen und synchronisiere
        if (new_lead_time != china_params['lead_time'] or
            new_order_entry != china_params['order_entry_duration'] or
            new_production_time != china_params['production_time'] or
            new_lot_size != china_params['lot_size']):
            
            # Synchronisiere SUPPLIERS
            MasterData.SUPPLIERS['China']['lead_time'] = new_lead_time
            MasterData.SUPPLIERS['China']['order_entry_duration'] = new_order_entry
            MasterData.SUPPLIERS['China']['production_time'] = new_production_time
            MasterData.SUPPLIERS['China']['lot_size'] = new_lot_size
            
            # KRITISCH: Synchronisiere auch CHINA_SUPPLIER
            MasterData.CHINA_SUPPLIER['Saddles']['lead_time'] = new_lead_time
            MasterData.CHINA_SUPPLIER['Saddles']['lot_size'] = new_lot_size
            MasterData.CHINA_SUPPLIER['Frames']['lead_time'] = new_lead_time
            MasterData.CHINA_SUPPLIER['Frames']['lot_size'] = new_lot_size
            
            st.success("✅ Lieferanten-Parameter aktualisiert! Bitte Simulation neu starten.")
            # Cache-Invalidierung bei Parameteränderungen
            _invalidate_all_caches()
            supplier_changed = True
            st.rerun()
        
        # Zeige berechnete Vorlaufzeit mit Standard-Referenz
        current_lead_time = MasterData.SUPPLIERS['China']['lead_time']
        st.markdown(f"**Berechnete Vorlaufzeit (Worst Case/Standard: {standard_lead_time} Tage):** {current_lead_time} Tage")
    
    st.divider()
    
    # Beschaffungs-Routen (nur China - Deutschland und Spanien entfernt)
    col_routes_title, col_routes_help = st.columns([20, 1])
    with col_routes_title:
        st.subheader("Beschaffungs-Routen")
    with col_routes_help:
        st.markdown("""
        <div style="margin-top: 1.5rem;">
            <span title="Änderungen an Routen-Dauer erfordern Neustart der Simulation für korrekte Berechnungen."
                style="cursor: help; color: #6b7280; font-size: 1.2rem; display: inline-block;">ℹ️</span>
        </div>
        """, unsafe_allow_html=True)
    
    procurement_data = []
    route_keys = []  # Speichere Keys für Synchronisierung
    for route in MasterData.PROCUREMENT_ROUTES:
        # Nur China-Routen anzeigen (Deutschland und Spanien entfernt)
        if route['supplier'] == 'China':
            route_key = (route['supplier'], route['component'], route['departure'], route['arrival'], route['transport'])
            route_keys.append(route_key)
            procurement_data.append({
                'Lieferant': route['supplier'],
                'Produktkomponente': route['component'],
                'Abfahrt': route['departure'],
                'Ankunft': route['arrival'],
                'Transportmittel': route['transport'],
                'Dauer': route['duration'],
                'Art': route['type'],
                'Dauer Standard': route.get('standard_duration', route['duration'])
            })
    
    if procurement_data:
        # Zeige Tabelle mit statischen Werten
        procurement_df = pd.DataFrame(procurement_data)
        display_df = procurement_df[['Lieferant', 'Produktkomponente', 'Abfahrt', 'Ankunft', 'Transportmittel', 'Art']].copy()
        st.dataframe(display_df, width='stretch', hide_index=True)
        
        # Editierbare Dauer-Werte mit st.number_input()
        procurement_changed = False
        for idx, route_info in enumerate(procurement_data):
            route_key = route_keys[idx]
            current_duration = route_info['Dauer']
            transport_name = route_info['Transportmittel']
            route_label = f"{route_info['Abfahrt']} → {route_info['Ankunft']} ({transport_name})"
            
            # Finde entsprechende Route in MasterData für Updates
            target_route = None
            for route in MasterData.PROCUREMENT_ROUTES:
                if (route['supplier'] == route_key[0] and 
                    route['component'] == route_key[1] and
                    route['departure'] == route_key[2] and
                    route['arrival'] == route_key[3] and
                    route['transport'] == route_key[4]):
                    target_route = route
                    break
            
            if target_route:
                new_duration = st.number_input(
                    f"Dauer: {route_label}",
                    min_value=1,
                    max_value=365,
                    value=int(current_duration),
                    step=1,
                    key=f"procurement_duration_{idx}_{route_key[4]}"
                )
                
                if new_duration != current_duration:
                    target_route['duration'] = new_duration
                    procurement_changed = True
        
        if procurement_changed:
            st.success("✅ Beschaffungs-Routen aktualisiert! Bitte Simulation neu starten.")
            # Cache-Invalidierung bei Parameteränderungen
            _invalidate_all_caches()

with tab5:
    st.header("Feiertage")
    st.markdown("Relevante Feiertage für alle betroffenen Länder")
    
    year = st.selectbox("Jahr", [2027, 2028, 2029], index=0, key="holiday_year")
    
    try:
        all_holidays = HolidaysConfig.get_all_holidays(year)
        
        # Länder-Namen und Flaggen (nur relevante Länder - Deutschland und China, da nur Inbound von China)
        country_info = {
            'DE': {'name': 'Deutschland', 'flag': '🇩🇪'},
            'CN': {'name': 'China', 'flag': '🇨🇳', 'note': 'Enthält nationale chinesische Feiertage + lokale Shanghai-Feiertage'}
        }
        
        # Zusammenfassung ZUERST (nach oben verschoben)
        summary_data = []
        for country_code, holidays_list in all_holidays.items():
            if country_code in country_info:
                info = country_info[country_code]
                summary_data.append({
                    'Land': f"{info['flag']} {info['name']}",
                    'Anzahl Feiertage': len(holidays_list)
                })
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df[['Land', 'Anzahl Feiertage']], width='stretch', hide_index=True)
        
        st.divider()
        
        # Detaillierte Feiertage (nur relevante Länder)
        for country_code, holidays_list in all_holidays.items():
            if country_code in country_info:
                info = country_info[country_code]
                st.subheader(f"{info['flag']} {info['name']}")
                
                # Zeige Hinweis für Shanghai-Feiertage
                if country_code == 'CN' and 'note' in info:
                    st.info(f"ℹ️ {info['note']}")
                
                if holidays_list:
                    holidays_df = pd.DataFrame(holidays_list)
                    st.dataframe(holidays_df, width='stretch', hide_index=True)
                else:
                    st.info(f"Keine Feiertagsdaten verfügbar für {info['name']}")
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Feiertage: {str(e)}")
        st.info("💡 Bitte installieren Sie die holidays-Library: `pip install holidays`")
