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

st.set_page_config(page_title="Stammdaten - Supply Chain Simulation", layout="wide", page_icon="📋")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Initialisiere ScenarioManager falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()

st.title("📋 Stammdaten")
st.markdown("Alle Stammdaten der Supply Chain Simulation")

# Tabs für verschiedene Stammdaten-Gruppen
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📦 Produkt-BOM", 
    "📊 Planung", 
    "🌍 Märkte & Kunden", 
    "🏭 Lieferanten", 
    "🚚 Logistik (Auslieferung)",
    "📥 Logistik (Beschaffung)",
    "📅 Feiertage",
    "⚙️ System-Parameter"
])

with tab1:
    st.header("Bill of Materials (BOM)")
    st.markdown("Produktstruktur aller Bike-Modelle - Zusammensetzung jedes Fahrrads")
    
    # BOM-Tabelle
    bom_data = []
    for product, components in MasterData.BOM.items():
        bom_data.append({
            'Endprodukt': product,
            'Rahmen': components['frame'],
            'Sattel': components['saddle'],
            'Gabel': components['fork']
        })
    bom_df = pd.DataFrame(bom_data)
    st.dataframe(bom_df, use_container_width=True, hide_index=True)
    
    # BOM-Statistiken
    st.subheader("BOM-Statistiken")
    frame_counts = {}
    saddle_counts = {}
    fork_counts = {}
    
    for product, components in MasterData.BOM.items():
        frame = components['frame']
        saddle = components['saddle']
        fork = components['fork']
        
        frame_counts[frame] = frame_counts.get(frame, 0) + 1
        saddle_counts[saddle] = saddle_counts.get(saddle, 0) + 1
        fork_counts[fork] = fork_counts.get(fork, 0) + 1
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**Rahmen-Verteilung:**")
        for frame, count in sorted(frame_counts.items()):
            st.write(f"- {frame}: {count} Produkte")
    with col2:
        st.write("**Sattel-Verteilung:**")
        for saddle, count in sorted(saddle_counts.items()):
            st.write(f"- {saddle}: {count} Produkte")
    with col3:
        st.write("**Gabel-Verteilung:**")
        for fork, count in sorted(fork_counts.items()):
            st.write(f"- {fork}: {count} Produkte")

with tab2:
    st.header("Planungs-Parameter")
    st.markdown("Globale Konfiguration und Saisonalität")
    
    # Globale Konfiguration
    st.subheader("Globale Konfiguration")
    config_data = []
    for key, value in MasterData.GLOBAL_CONFIG.items():
        config_data.append({
            'Parameter': key.replace('_', ' ').title(),
            'Wert': value
        })
    config_df = pd.DataFrame(config_data)
    st.dataframe(config_df, use_container_width=True, hide_index=True)
    
    # Tägliche Arbeitslast
    st.subheader("Tägliche Arbeitslast")
    workload_data = []
    for day, workload in MasterData.DAILY_WORKLOAD.items():
        workload_data.append({
            'Wochentag': day,
            'Arbeitslast': workload
        })
    workload_df = pd.DataFrame(workload_data)
    st.dataframe(workload_df, use_container_width=True, hide_index=True)
    
    # Verkaufsanteile
    st.subheader("Verkaufsanteile pro Produkt")
    sales_data = []
    for product, share in MasterData.PRODUCT_SALES_SHARES.items():
        sales_data.append({
            'Produkt': product,
            'Verkaufsanteil': f"{share * 100:.1f}%",
            'Anteil (dezimal)': share
        })
    sales_df = pd.DataFrame(sales_data)
    st.dataframe(sales_df, use_container_width=True, hide_index=True)
    
    # Visualisierung Verkaufsanteile
    fig_sales = go.Figure(data=[go.Pie(
        labels=sales_df['Produkt'],
        values=sales_df['Anteil (dezimal)'] * 100,
        hole=0.3
    )])
    fig_sales.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_sales, use_container_width=True)
    
    # Saisonalität
    st.subheader("Saisonaler Produktionsverlauf")
    seasonality_data = []
    for month, factor in MasterData.SEASONALITY.items():
        month_names = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
        }
        seasonality_data.append({
            'Monat': month_names[month],
            'Produktionsanteil': f"{factor * 100:.1f}%",
            'Anteil (dezimal)': factor,
            'Tage': MasterData.DAYS_PER_MONTH[month]
        })
    seasonality_df = pd.DataFrame(seasonality_data)
    st.dataframe(seasonality_df[['Monat', 'Produktionsanteil', 'Tage']], use_container_width=True, hide_index=True)
    
    # Visualisierung Saisonalität
    fig_seasonality = go.Figure()
    fig_seasonality.add_trace(go.Scatter(
        x=seasonality_df['Monat'],
        y=seasonality_df['Anteil (dezimal)'] * 100,
        mode='lines+markers',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8)
    ))
    fig_seasonality.update_layout(
        xaxis_title="Monat",
        yaxis_title="Produktionsanteil (%)",
        height=400
    )
    st.plotly_chart(fig_seasonality, use_container_width=True)

with tab3:
    st.header("Märkte & Kunden")
    st.markdown("Zielmärkte und Marktverteilung")
    
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
    st.dataframe(markets_df[['Land', 'Code', 'Anteil (%)', 'Transitzeit (Tage)']], use_container_width=True, hide_index=True)
    
    # Visualisierung Marktverteilung
    st.subheader("Marktverteilung")
    fig_markets = go.Figure(data=[go.Pie(
        labels=markets_df['Land'],
        values=markets_df['Anteil (dezimal)'] * 100,
        hole=0.3
    )])
    fig_markets.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_markets, use_container_width=True)

with tab4:
    st.header("Lieferanten")
    st.markdown("Lieferanten-Parameter und Standorte")
    
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
    st.dataframe(suppliers_df, use_container_width=True, hide_index=True)

with tab5:
    st.header("Logistik - Auslieferung")
    st.markdown("Routen und Transportmittel für die Auslieferung")
    
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
    st.dataframe(delivery_df, use_container_width=True, hide_index=True)
    
    # Gruppierung nach Ziel
    st.subheader("Auslieferung nach Ziel")
    for destination in delivery_df['Ziel'].unique():
        with st.expander(f"📦 {destination}"):
            dest_routes = delivery_df[delivery_df['Ziel'] == destination]
            st.dataframe(dest_routes, use_container_width=True, hide_index=True)

with tab6:
    st.header("Logistik - Beschaffung")
    st.markdown("Routen und Transportmittel für die Beschaffung")
    
    procurement_data = []
    for route in MasterData.PROCUREMENT_ROUTES:
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
    procurement_df = pd.DataFrame(procurement_data)
    st.dataframe(procurement_df, use_container_width=True, hide_index=True)
    
    # Gruppierung nach Lieferant
    st.subheader("Beschaffung nach Lieferant")
    for supplier in procurement_df['Lieferant'].unique():
        with st.expander(f"🏭 {supplier}"):
            supp_routes = procurement_df[procurement_df['Lieferant'] == supplier]
            st.dataframe(supp_routes, use_container_width=True, hide_index=True)

with tab7:
    st.header("Feiertage")
    st.markdown("Relevante Feiertage für alle betroffenen Länder (2027)")
    
    year = st.selectbox("Jahr", [2027, 2026, 2028], index=0, key="holiday_year")
    
    try:
        all_holidays = HolidaysConfig.get_all_holidays(year)
        
        # Länder-Namen
        country_names = {
            'DE': 'Deutschland',
            'USA': 'USA',
            'FR': 'Frankreich',
            'CN': 'China',
            'CH': 'Schweiz',
            'AT': 'Österreich'
        }
        
        for country_code, holidays_list in all_holidays.items():
            country_name = country_names.get(country_code, country_code)
            st.subheader(f"🇺🇳 {country_name} ({country_code})")
            
            if holidays_list:
                holidays_df = pd.DataFrame(holidays_list)
                st.dataframe(holidays_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"Keine Feiertagsdaten verfügbar für {country_name}")
        
        # Zusammenfassung
        st.subheader("Zusammenfassung")
        summary_data = []
        for country_code, holidays_list in all_holidays.items():
            country_name = country_names.get(country_code, country_code)
            summary_data.append({
                'Land': country_name,
                'Anzahl Feiertage': len(holidays_list)
            })
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Feiertage: {str(e)}")
        st.info("💡 Bitte installieren Sie die holidays-Library: `pip install holidays`")

with tab8:
    st.header("System-Parameter")
    st.markdown("Allgemeine System-Parameter")
    
    st.subheader("Simulations-Parameter")
    system_params = pd.DataFrame({
        'Parameter': ['Simulationsdauer', 'Tage pro Jahr'],
        'Wert': ['365 Tage', '365']
    })
    st.dataframe(system_params, use_container_width=True, hide_index=True)
    
    st.subheader("Komponenten-Kategorien")
    # Gruppiere Rahmen nach Typ
    frame_types = {}
    for product, components in MasterData.BOM.items():
        frame = components['frame']
        if 'Aluminium' in frame:
            frame_type = 'Aluminium'
        elif 'Carbon' in frame:
            frame_type = 'Carbon'
        else:
            frame_type = 'Sonstige'
        frame_types[frame_type] = frame_types.get(frame_type, 0) + 1
    
    components_data = []
    for frame_type, count in frame_types.items():
        components_data.append({
            'Kategorie': f'Rahmen - {frame_type}',
            'Anzahl Produkte': count
        })
    
    # Sattel-Kategorien
    saddle_types = {}
    for product, components in MasterData.BOM.items():
        saddle = components['saddle']
        saddle_types[saddle] = saddle_types.get(saddle, 0) + 1
    
    for saddle, count in saddle_types.items():
        components_data.append({
            'Kategorie': f'Sattel - {saddle}',
            'Anzahl Produkte': count
        })
    
    components_df = pd.DataFrame(components_data)
    st.dataframe(components_df, use_container_width=True, hide_index=True)
