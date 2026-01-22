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

st.set_page_config(page_title="Stammdaten", layout="wide", page_icon="📋")

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
    
    if config_changed:
        st.success("✅ Globale Konfiguration aktualisiert!")
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
        # Kein st.rerun() - Streamlit aktualisiert automatisch
    
    # Verkaufsanteile (editierbar)
    st.subheader("Verkaufsanteile pro Produkt")
    st.write("**Verkaufsanteile in Prozent (Summe sollte 100% ergeben):**")
    
    sales_data = []
    for product in sorted(st.session_state.editable_product_sales_shares.keys()):
        share = st.session_state.editable_product_sales_shares[product]
        sales_data.append({
            'Produkt': product,
            'Verkaufsanteil (%)': share * 100
        })
    sales_df = pd.DataFrame(sales_data)
    
    edited_sales = st.data_editor(
        sales_df,
        column_config={
            "Produkt": st.column_config.TextColumn("Produkt", disabled=True),
            "Verkaufsanteil (%)": st.column_config.NumberColumn("Verkaufsanteil (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        },
        width='stretch',
        hide_index=True,
        key="sales_editor"
    )
    
    # Speichere Änderungen und normalisiere auf Dezimalwerte
    if not edited_sales.equals(sales_df):
        total = edited_sales['Verkaufsanteil (%)'].sum()
        if total > 0:
            # Normalisiere auf 1.0 (100%)
            for _, row in edited_sales.iterrows():
                product = row['Produkt']
                percentage = row['Verkaufsanteil (%)']
                st.session_state.editable_product_sales_shares[product] = percentage / 100.0
            st.success(f"✅ Verkaufsanteile aktualisiert! (Gesamt: {total:.1f}%)")
            # Kein st.rerun() - Streamlit aktualisiert automatisch
        else:
            st.error("⚠️ Summe der Verkaufsanteile muss größer als 0 sein!")
    
    # Saisonalität (editierbar)
    st.subheader("Saisonaler Produktionsverlauf")
    st.write("**Produktionsanteil pro Monat in Prozent (Summe sollte 100% ergeben):**")
    
    month_names = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
    }
    
    seasonality_data = []
    for month in sorted(st.session_state.editable_seasonality.keys()):
        factor = st.session_state.editable_seasonality[month]
        seasonality_data.append({
            'Monat': month_names[month],
            'Produktionsanteil (%)': factor * 100,
            'Tage': MasterData.DAYS_PER_MONTH[month]
        })
    seasonality_df = pd.DataFrame(seasonality_data)
    
    edited_seasonality = st.data_editor(
        seasonality_df,
        column_config={
            "Monat": st.column_config.TextColumn("Monat", disabled=True),
            "Produktionsanteil (%)": st.column_config.NumberColumn("Produktionsanteil (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"),
            "Tage": st.column_config.NumberColumn("Tage", disabled=True)
        },
        width='stretch',
        hide_index=True,
        key="seasonality_editor"
    )
    
    # Speichere Änderungen und normalisiere auf Dezimalwerte
    if not edited_seasonality.equals(seasonality_df):
        total = edited_seasonality['Produktionsanteil (%)'].sum()
        if total > 0:
            # Normalisiere auf 1.0 (100%)
            month_name_to_num = {v: k for k, v in month_names.items()}
            for _, row in edited_seasonality.iterrows():
                month_name = row['Monat']
                month_num = month_name_to_num[month_name]
                percentage = row['Produktionsanteil (%)']
                st.session_state.editable_seasonality[month_num] = percentage / 100.0
            st.success(f"✅ Saisonalität aktualisiert! (Gesamt: {total:.1f}%)")
            # Kein st.rerun() - Streamlit aktualisiert automatisch
        else:
            st.error("⚠️ Summe der Produktionsanteile muss größer als 0 sein!")

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
    
    # Auslieferungs-Routen
    st.subheader("Auslieferungs-Routen")
    
    delivery_data = []
    for route in MasterData.DELIVERY_ROUTES:
        delivery_data.append({
            'Ziel': route['destination'],
            'Abfahrt': route['departure'],
            'Ankunft': route['arrival'],
            'Transportmittel': route['transport'],
            'Dauer': route['duration'],
            'Art': route['type']
        })
    delivery_df = pd.DataFrame(delivery_data)
    st.dataframe(delivery_df, width='stretch', hide_index=True)
    
    # Gruppierung nach Ziel
    st.subheader("Auslieferung nach Ziel")
    for destination in delivery_df['Ziel'].unique():
        with st.expander(f"📦 {destination}"):
            dest_routes = delivery_df[delivery_df['Ziel'] == destination]
            st.dataframe(dest_routes, width='stretch', hide_index=True)

with tab5:
    st.header("Beschaffung")
    st.markdown("Routen und Transportmittel für die Beschaffung")
    
    # Lieferanten-Parameter und Standorte (aus Auslieferung hierher verschoben)
    st.subheader("Lieferanten-Parameter und Standorte")
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
        suppliers_df = pd.DataFrame(suppliers_data)
        st.dataframe(suppliers_df, width='stretch', hide_index=True)
    
    st.divider()
    
    # Beschaffungs-Routen (nur China - Deutschland und Spanien entfernt)
    st.subheader("Beschaffungs-Routen")
    procurement_data = []
    for route in MasterData.PROCUREMENT_ROUTES:
        # Nur China-Routen anzeigen (Deutschland und Spanien entfernt)
        if route['supplier'] == 'China':
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
        procurement_df = pd.DataFrame(procurement_data)
        st.dataframe(procurement_df, width='stretch', hide_index=True)

with tab6:
    st.header("Feiertage")
    st.markdown("Relevante Feiertage für alle betroffenen Länder")
    
    year = st.selectbox("Jahr", [2027, 2028, 2029], index=0, key="holiday_year")
    
    try:
        all_holidays = HolidaysConfig.get_all_holidays(year)
        
        # Länder-Namen und Flaggen (nur relevante Länder - Deutschland und China, da nur Inbound von China)
        country_info = {
            'DE': {'name': 'Deutschland', 'flag': '🇩🇪'},
            'CN': {'name': 'China', 'flag': '🇨🇳'}
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
                
                if holidays_list:
                    holidays_df = pd.DataFrame(holidays_list)
                    st.dataframe(holidays_df, width='stretch', hide_index=True)
                else:
                    st.info(f"Keine Feiertagsdaten verfügbar für {info['name']}")
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Feiertage: {str(e)}")
        st.info("💡 Bitte installieren Sie die holidays-Library: `pip install holidays`")
