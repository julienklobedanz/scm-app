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
    Invalidiert alle relevanten Caches bei Parameteränderungen.
    Wird aufgerufen wenn Planungsparameter geändert werden.
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
        'volume_planning_cache_key'
    ]
    
    for k in keys_to_delete:
        if k in st.session_state:
            del st.session_state[k]
    
    # Lösche auch alle Caches die mit "material_inventory_" beginnen (außer last_cache_key)
    for k in list(st.session_state.keys()):
        if k.startswith('material_inventory_') and k != 'material_inventory_last_cache_key':
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
from ui.theme_toggle import render_theme_toggle
render_theme_toggle()

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

# OPTIMIERUNG: Initialisiere editierbare Stammdaten in Session State (nur einmal beim ersten Laden)
# Verwende einen Flag, um zu prüfen, ob alle initialisiert wurden
if 'stammdaten_initialized' not in st.session_state:
    st.session_state.editable_bom = MasterData.BOM.copy()
    st.session_state.editable_global_config = MasterData.GLOBAL_CONFIG.copy()
    st.session_state.editable_daily_workload = MasterData.DAILY_WORKLOAD.copy()
    st.session_state.editable_product_sales_shares = MasterData.PRODUCT_SALES_SHARES.copy()
    st.session_state.editable_seasonality = MasterData.SEASONALITY.copy()
    st.session_state.stammdaten_initialized = True

st.title("📋 Stammdaten")
st.markdown("Alle Stammdaten der Supply Chain Simulation")

# DEBUG: Zeige Konvergenz-Info für Test-1.3
# WICHTIG: Zeige immer an, auch wenn Werte noch nicht gesetzt sind
if 'convergence_iterations' in st.session_state:
    convergence_reached = st.session_state.get('convergence_reached', False)
    iterations = st.session_state.get('convergence_iterations', 0)
    
    if convergence_reached:
        st.success(f"✅ **Konvergenz-Check:** {iterations} Iteration(en) durchgeführt, Konvergenz erreicht!")
    else:
        st.info(f"ℹ️ **Konvergenz-Check:** {iterations} Iteration(en) durchgeführt (max. 5)")
else:
    # Fallback: Zeige Info wenn Werte noch nicht gesetzt sind
    st.warning("⚠️ **Konvergenz-Check:** Wird beim nächsten Laden der Seite berechnet...")

# Tabs für verschiedene Stammdaten-Gruppen
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📦 Stückliste", 
    "📊 Planung", 
    "🌍 Märkte & Kunden", 
    "🚚 Auslieferung",
    "📥 Beschaffung",
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
            st.success("✅ Stückliste aktualisiert!")
            # Kein st.rerun() - Streamlit aktualisiert automatisch

with tab2:
    st.header("Planungs-Parameter")
    st.markdown("Globale Konfiguration und Saisonalität")
    
    # Globale Konfiguration
    st.subheader("Globale Konfiguration")
    
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
    
    # Weitere globale Konfigurationsparameter (editierbar)
    st.write("**Globale Konfigurationsparameter:**")
    param_translations = {
        'total_volume': 'Gesamtvolumen',
        'capacity_per_hour': 'Kapazität pro Stunde',
        'assembly_lines': 'Anzahl Montagelinien',
        'min_shifts_per_day': 'Min. Schichten/Tag',
        'max_shifts_per_day': 'Max. Schichten/Tag',
        'working_hours_per_shift': 'Anzahl Arbeitsstunden/Schicht',
        'batch_size': 'Losgröße'
    }
    
    col1, col2 = st.columns(2)
    config_changed = False
    
    # Definiere max_value pro Parameter
    max_values = {
        'total_volume': 1000000,
        'capacity_per_hour': 500,  # Erhöht von 100 auf 500 (aktueller Wert: 130)
        'assembly_lines': 10,
        'min_shifts_per_day': 5,
        'max_shifts_per_day': 5,
        'working_hours_per_shift': 24,
        'batch_size': 1000
    }
    
    with col1:
        for i, (key, value) in enumerate(list(st.session_state.editable_global_config.items())[:4]):
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
            if new_value != value:
                st.session_state.editable_global_config[key] = new_value
                config_changed = True
                
                # FIX: Synchronisiere yearly_volume mit total_volume
                if key == 'total_volume':
                    st.session_state.yearly_volume = new_value
                    # Aktualisiere auch MasterData.GLOBAL_CONFIG für Simulator
                    MasterData.GLOBAL_CONFIG['total_volume'] = new_value
    
    with col2:
        for i, (key, value) in enumerate(list(st.session_state.editable_global_config.items())[4:]):
            param_name = param_translations.get(key, key.replace('_', ' ').title())
            max_val = max_values.get(key, 1000)
            new_value = st.number_input(
                param_name,
                min_value=1,
                max_value=max_val,
                value=int(value),
                step=1,
                key=f"config_{key}"
            )
            if new_value != value:
                st.session_state.editable_global_config[key] = new_value
                config_changed = True
                
                # FIX: Synchronisiere yearly_volume mit total_volume
                if key == 'total_volume':
                    st.session_state.yearly_volume = new_value
                    # Aktualisiere auch MasterData.GLOBAL_CONFIG für Simulator
                    MasterData.GLOBAL_CONFIG['total_volume'] = new_value
    
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
    
    # Tägliche Arbeitslast (editierbar)
    st.subheader("Tägliche Arbeitslast")
    st.write("**Arbeitslast pro Wochentag (0.0 = kein Arbeitstag, 0.2 = 20% der Wochenlast):**")
    
    workload_changed = False
    col1, col2, col3, col4 = st.columns(4)
    
    weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    for i, day in enumerate(weekdays):
        col_idx = i % 4
        with [col1, col2, col3, col4][col_idx]:
            new_workload = st.number_input(
                day,
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.editable_daily_workload[day]),
                step=0.1,
                format="%.1f",
                key=f"workload_{day}"
            )
            if new_workload != st.session_state.editable_daily_workload[day]:
                st.session_state.editable_daily_workload[day] = new_workload
                workload_changed = True
    
    if workload_changed:
        st.success("✅ Tägliche Arbeitslast aktualisiert!")
        
        # KRITISCH: Synchronisiere DAILY_WORKLOAD mit MasterData
        for day, workload in st.session_state.editable_daily_workload.items():
            MasterData.DAILY_WORKLOAD[day] = workload
        
        # Cache-Invalidierung bei Parameteränderungen
        _invalidate_all_caches()
        
        # Kein st.rerun() - Streamlit aktualisiert automatisch
    
    # Verkaufsanteile (editierbar)
    st.subheader("Verkaufsanteile pro Produkt")
    st.write("**Verkaufsanteile in Prozent (Summe muss exakt 100% ergeben):**")
    
    # Berechne aktuelle Summe für Validierung
    current_total = sum(st.session_state.editable_product_sales_shares.values()) * 100
    
    # Warnung wenn Summe nicht 100%
    if abs(current_total - 100.0) >= 0.01:
        st.error(f"⚠️ **ACHTUNG:** Die Summe der Verkaufsanteile beträgt aktuell {current_total:.1f}%. Berechnungen können erst erfolgen, wenn die Summe exakt 100% beträgt!")
        st.info("💡 **Hinweis:** Bitte passen Sie die Werte unten an, bis die Summe genau 100% ergibt. Sie können auch die automatische Normalisierung verwenden.")
    
    # Editierbare Parameter mit st.number_input() (wie Planungs-Parameter)
    sales_changed = False
    sales_values = {}
    
    # Erstelle zwei Spalten für bessere Übersicht
    col1, col2 = st.columns(2)
    
    products = sorted(st.session_state.editable_product_sales_shares.keys())
    mid_point = len(products) // 2
    
    with col1:
        for product in products[:mid_point]:
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
    
    with col2:
        for product in products[mid_point:]:
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
            
            # Option zur automatischen Normalisierung
            if st.button("🔧 Automatisch auf 100% normalisieren", key="normalize_sales"):
                # Normalisiere auf 100%
                for product, percentage in sales_values.items():
                    normalized = (percentage / new_total) * 100.0
                    st.session_state.editable_product_sales_shares[product] = normalized / 100.0
                
                # KRITISCH: Synchronisiere PRODUCT_SALES_SHARES mit MasterData
                for product, share in st.session_state.editable_product_sales_shares.items():
                    MasterData.PRODUCT_SALES_SHARES[product] = share
                
                st.success("✅ Verkaufsanteile automatisch normalisiert!")
                sales_changed = True
                st.rerun()
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
    
    # Editierbare Parameter mit st.number_input() (wie Planungs-Parameter)
    seasonality_changed = False
    seasonality_values = {}
    
    # Erstelle drei Spalten für bessere Übersicht (4 Monate pro Spalte)
    col1, col2, col3 = st.columns(3)
    
    months = sorted(st.session_state.editable_seasonality.keys())
    
    with col1:
        for month in months[:4]:
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
    
    with col2:
        for month in months[4:8]:
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
    
    with col3:
        for month in months[8:]:
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
            
            # Option zur automatischen Normalisierung
            if st.button("🔧 Automatisch auf 100% normalisieren", key="normalize_seasonality"):
                # Normalisiere auf 100%
                for month, percentage in seasonality_values.items():
                    normalized = (percentage / new_total) * 100.0
                    st.session_state.editable_seasonality[month] = normalized / 100.0
                
                # KRITISCH: Synchronisiere SEASONALITY mit MasterData
                for month, factor in st.session_state.editable_seasonality.items():
                    MasterData.SEASONALITY[month] = factor
                
                st.success("✅ Saisonalität automatisch normalisiert!")
                seasonality_changed = True
                st.rerun()
        else:
            st.error("❌ **Summe der Produktionsanteile muss größer als 0 sein!**")
    
    if seasonality_changed:
        # Cache-Invalidierung bei Parameteränderungen
        _invalidate_all_caches()

with tab3:
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

with tab4:
    st.header("Auslieferung")
    st.markdown("Routen und Transportmittel für die Auslieferung")
    
    # Lieferanten-Parameter
    st.subheader("Lieferanten-Parameter und Standorte")
    suppliers_data = []
    for supplier, params in MasterData.SUPPLIERS.items():
        suppliers_data.append({
            'Lieferant': supplier,
            'Bundesland/Region': params['federal_state'],
            'Vorlaufzeit (Tage)': params['lead_time'],
            'Dauer Auftragserfassung (Tage)': params['order_entry_duration'],
            'Produktionszeit (Tage)': params['production_time'],
            'Losgröße': params['lot_size']
        })
    suppliers_df = pd.DataFrame(suppliers_data)
    st.dataframe(suppliers_df, width='stretch', hide_index=True)
    
    st.divider()

with tab5:
    st.header("Beschaffung")
    st.markdown("Routen und Transportmittel für die Beschaffung")
    
    # Lieferanten-Parameter und Standorte (aus Auslieferung hierher verschoben)
    st.subheader("Lieferanten-Parameter und Standorte")
    
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
        
        # Zeige berechnete Vorlaufzeit mit Standard-Referenz
        current_lead_time = MasterData.SUPPLIERS['China']['lead_time']
        st.markdown(f"**Berechnete Vorlaufzeit (Worst Case/Standard: {standard_lead_time} Tage):** {current_lead_time} Tage")
    
    st.divider()
    
    # Beschaffungs-Routen (nur China - Deutschland und Spanien entfernt)
    st.subheader("Beschaffungs-Routen")
    st.warning("⚠️ Änderungen an Routen-Dauer erfordern Neustart der Simulation für korrekte Berechnungen!")
    
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
        st.caption("💡 **Hinweis:** 'Dauer Standard' (z.B. 22 KT für Schiff) ist ein Referenzwert aus den ursprünglichen Stammdaten. Die aktuelle 'Dauer' kann unten geändert werden.")
        
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

with tab6:
    st.header("Feiertage")
    st.markdown("Relevante Feiertage für alle betroffenen Länder")
    
    year = st.selectbox("Jahr", [2027, 2028, 2029], index=0, key="holiday_year")
    
    try:
        all_holidays = HolidaysConfig.get_all_holidays(year)
        
        # Länder-Namen und Flaggen (nur relevante Länder - Deutschland und China, da nur Inbound von China)
        country_info = {
            'DE': {'name': 'Deutschland', 'flag': '🇩🇪'},
            'CN': {'name': 'China (Shanghai)', 'flag': '🇨🇳', 'note': 'Enthält nationale chinesische Feiertage + lokale Shanghai-Feiertage'}
        }
        
        # Zusammenfassung ZUERST (nach oben verschoben)
        st.subheader("Zusammenfassung")
        summary_data = []
        for country_code, holidays_list in all_holidays.items():
            if country_code in country_info:
                info = country_info[country_code]
                summary_data.append({
                    'Land': f"{info['flag']} {info['name']}",
                    'Code': country_code,
                    'Anzahl Feiertage': len(holidays_list)
                })
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, width='stretch', hide_index=True)
        
        st.divider()
        
        # Detaillierte Feiertage (nur relevante Länder)
        for country_code, holidays_list in all_holidays.items():
            if country_code in country_info:
                info = country_info[country_code]
                st.subheader(f"{info['flag']} {info['name']} ({country_code})")
                
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
