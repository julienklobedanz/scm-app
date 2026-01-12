"""
Reports-Seite
Advanced Reporting Dashboard mit SCOR Metrics und operativen KPIs
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
from config.master_data import MasterData
from simulation.simulator import Simulator
from models.scenarios import ScenarioManager
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Reports - Supply Chain Simulation", layout="wide", page_icon="📈")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Initialisiere Session State falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'kpis' not in st.session_state:
    st.session_state.kpis = None
if 'happy_path_run' not in st.session_state:
    st.session_state.happy_path_run = False
if 'yearly_volume' not in st.session_state:
    st.session_state.yearly_volume = 370000

st.title("📈 Reports")
st.markdown("Detaillierte Berichte und Analysen basierend auf SCOR Metrics")

# Hilfsfunktion: Kalenderwoche aus Datum berechnen
def get_week_number(d: date) -> int:
    """Berechnet ISO-Kalenderwoche"""
    return d.isocalendar()[1]

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
if not st.session_state.happy_path_run and st.session_state.results_df is None:
    # Führe Simulation sofort aus (blockierend)
    try:
        with st.spinner("🔄 Happy Path Simulation wird ausgeführt..."):
            vol = st.session_state.get('yearly_volume', 370000)
            simulator = Simulator(
                yearly_volume=vol,
                initial_stock_frames_alu=MasterData.DEFAULT_INITIAL_STOCK['frames_alu'],
                initial_stock_frames_carbon=MasterData.DEFAULT_INITIAL_STOCK['frames_carbon'],
                initial_stock_saddles=MasterData.DEFAULT_INITIAL_STOCK['saddles'],
                scenario_manager=st.session_state.scenario_manager
            )
            results_df, kpis = simulator.run()
            st.session_state.results_df = results_df
            st.session_state.kpis = kpis
            # Speichere auch den Simulator für Zugriff auf ChinaTransportManager
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
            st.rerun()  # Rerun, um die Ergebnisse anzuzeigen
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.happy_path_run = True  # Verhindere Endlosschleife

# Prüfe ob Ergebnisse vorhanden sind
if st.session_state.results_df is None:
    st.warning("⚠️ Keine Simulationsergebnisse verfügbar. Bitte führen Sie eine Simulation im Dashboard durch.")
    st.stop()

results_df = st.session_state.results_df
kpis = st.session_state.kpis

# ============================================================================
# SECTION 4: SCOR Metrics / KPIs (High Level) - Zuerst anzeigen
# ============================================================================
st.header("🎯 Key Performance Indicators (SCOR)")

# Berechne SCOR Metrics
col1, col2, col3, col4 = st.columns(4)

# Perfect Order Fulfillment
# Berechne Global Backlog (wird später auch für Charts benötigt)
results_df['Global_Backlog'] = (
    results_df['Backlog_DE'] + results_df['Backlog_USA'] + 
    results_df['Backlog_FR'] + results_df['Backlog_CN'] + 
    results_df['Backlog_CH'] + results_df['Backlog_AT']
)

# Perfect Order Fulfillment: Tage wo Actual_Build == Daily_Target (genau die Nachfrage geliefert)
days_perfect_fulfillment = (results_df['Actual_Build'] == results_df['Daily_Target']).sum()
perfect_order_fulfillment = (days_perfect_fulfillment / len(results_df) * 100) if len(results_df) > 0 else 0.0

with col1:
    st.metric(
        "Perfect Order Fulfillment",
        f"{perfect_order_fulfillment:.2f}%",
        help="Anteil der Tage, an denen genau die Nachfrage geliefert wurde"
    )

# Source Cycle Time (Inbound)
source_cycle_time = MasterData.CHINA_SUPPLIER['Frames']['lead_time']
with col2:
    st.metric(
        "Source Cycle Time (Eingehend)",
        f"{source_cycle_time} Tage",
        help="Durchschnittliche Lead Time für Bestellungen aus China"
    )

# Delivery Cycle Time (Outbound) - Gewichteter Durchschnitt
market_transit_times = {}
total_share = 0.0
for market, params in MasterData.MARKETS.items():
    market_transit_times[market] = params['transit_days']
    total_share += params['share']

weighted_delivery_time = sum(
    params['transit_days'] * params['share'] 
    for params in MasterData.MARKETS.values()
) if total_share > 0 else 0.0

with col3:
    st.metric(
        "Delivery Cycle Time (Ausgehend)",
        f"{weighted_delivery_time:.1f} Tage",
        help="Gewichteter Durchschnitt der Transitzeiten zu den Märkten"
    )

# Cash-to-Cash Cycle (vereinfacht: Average Inventory Coverage)
avg_daily_demand = results_df['Daily_Target'].mean() if len(results_df) > 0 else 1.0
avg_frames_stock = (results_df['Stock_Frames_Alu'].mean() + results_df['Stock_Frames_Carbon'].mean()) / 2
avg_saddles_stock = results_df['Stock_Saddles'].mean()
avg_total_stock = avg_frames_stock + avg_saddles_stock
inventory_coverage_days = (avg_total_stock / avg_daily_demand) if avg_daily_demand > 0 else 0.0

with col4:
    st.metric(
        "Lagerabdeckung",
        f"{inventory_coverage_days:.1f} Tage",
        help="Durchschnittliche Lagerabdeckung in Tagen"
    )

st.divider()

# ============================================================================
# SECTION 1: Production & Backlog Analysis (Visuals)
# ============================================================================
st.header("📊 Produktions- und Backlog-Analyse")

# Berechne Kalenderwoche für jeden Tag
if 'Date' in results_df.columns:
    results_df['KW'] = results_df['Date'].apply(get_week_number)
else:
    # Fallback: Berechne KW aus Day
    start_date = date(2026, 1, 1)
    results_df['KW'] = results_df.apply(
        lambda row: get_week_number(start_date + pd.Timedelta(days=int(row['Day']) - 1)),
        axis=1
    )

# Global View
st.subheader("Globale Ansicht")

col1, col2 = st.columns(2)

with col1:
    # Chart A: Cumulative Global Backlog auf KW-Basis
    st.write("**Kumulativer Globaler Backlog**")
    
    # Aggregiere auf Kalenderwochen-Basis (nehme letzten Wert der Woche)
    weekly_backlog = results_df.groupby('KW')['Global_Backlog'].last().reset_index()
    
    fig_backlog_cum = go.Figure()
    fig_backlog_cum.add_trace(go.Scatter(
        x=weekly_backlog['KW'],
        y=weekly_backlog['Global_Backlog'],
        name='Kumulativer Globaler Backlog',
        line=dict(color='#1f77b4', width=2),
        mode='lines+markers'
    ))
    
    fig_backlog_cum.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Globaler Backlog (Einheiten)",
        height=350,
        hovermode='x unified'
    )
    st.plotly_chart(fig_backlog_cum, use_container_width=True)

with col2:
    # Chart B: Production Deviation auf KW-Basis
    st.write("**Produktionsabweichung (Wöchentlich)**")
    
    # Berechne tägliche Deviation
    results_df['Production_Deviation'] = results_df['Actual_Build'] - results_df['Daily_Target']
    
    # Aggregiere auf Kalenderwochen-Basis (Summe der Abweichungen pro Woche)
    weekly_deviation = results_df.groupby('KW')['Production_Deviation'].sum().reset_index()
    
    # Farben basierend auf Deviation
    colors = ['#2ca02c' if x >= 0 else '#d62728' for x in weekly_deviation['Production_Deviation']]
    
    fig_deviation = go.Figure()
    fig_deviation.add_trace(go.Bar(
        x=weekly_deviation['KW'],
        y=weekly_deviation['Production_Deviation'],
        name='Produktionsabweichung',
        marker_color=colors,
        text=weekly_deviation['Production_Deviation'].round(0),
        textposition='outside'
    ))
    
    # Null-Linie hinzufügen
    fig_deviation.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig_deviation.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Abweichung (Ist - Soll)",
        height=350,
        hovermode='x unified',
        showlegend=False
    )
    st.plotly_chart(fig_deviation, use_container_width=True)

# Per Product View
st.subheader("Produktspezifische Ansicht")

# Produktauswahl
selected_product = st.selectbox(
    "Wählen Sie ein Bike Model:",
    list(MasterData.BOM.keys()),
    key="product_selection"
)

# Berechne produkt-spezifische Daten basierend auf Sales Share
product_share = MasterData.PRODUCT_SALES_SHARES.get(selected_product, 0.0)

# Produkt-spezifische Nachfrage und Produktion
results_df['Product_Demand'] = results_df['Daily_Target'] * product_share
results_df['Product_Production'] = results_df['Actual_Build'] * product_share
results_df['Product_Backlog'] = results_df['Global_Backlog'] * product_share
results_df['Product_Deviation'] = results_df['Product_Production'] - results_df['Product_Demand']

# Aggregiere auf KW-Basis
weekly_product_backlog = results_df.groupby('KW')['Product_Backlog'].last().reset_index()
weekly_product_deviation = results_df.groupby('KW')['Product_Deviation'].sum().reset_index()

col1, col2 = st.columns(2)

with col1:
    st.write(f"**Kumulativer Backlog - {selected_product}**")
    fig_product_backlog = go.Figure()
    fig_product_backlog.add_trace(go.Scatter(
        x=weekly_product_backlog['KW'],
        y=weekly_product_backlog['Product_Backlog'],
        name=f'Backlog {selected_product}',
        line=dict(color='#9467bd', width=2),
        mode='lines+markers'
    ))
    
    fig_product_backlog.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Backlog (Einheiten)",
        height=350,
        hovermode='x unified'
    )
    st.plotly_chart(fig_product_backlog, use_container_width=True)

with col2:
    st.write(f"**Produktionsabweichung - {selected_product}**")
    product_colors = ['#2ca02c' if x >= 0 else '#d62728' for x in weekly_product_deviation['Product_Deviation']]
    
    fig_product_deviation = go.Figure()
    fig_product_deviation.add_trace(go.Bar(
        x=weekly_product_deviation['KW'],
        y=weekly_product_deviation['Product_Deviation'],
        name='Abweichung',
        marker_color=product_colors,
        text=weekly_product_deviation['Product_Deviation'].round(0),
        textposition='outside'
    ))
    
    fig_product_deviation.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig_product_deviation.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Abweichung (Ist - Soll)",
        height=350,
        hovermode='x unified',
        showlegend=False
    )
    st.plotly_chart(fig_product_deviation, use_container_width=True)

st.divider()

# ============================================================================
# SECTION 2: Inventory Evolution (Visuals)
# ============================================================================
st.header("📦 Lagerbestandsentwicklung")

col1, col2 = st.columns(2)

with col1:
    # Raw Materials (China Components)
    st.subheader("Rohmaterialien (China Komponenten)")
    
    fig_raw_materials = go.Figure()
    
    x_axis = results_df['Date'] if 'Date' in results_df.columns else results_df['Day']
    
    fig_raw_materials.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Frames_Alu'],
        name='Rahmen Bestand (Alu)',
        line=dict(color='#1f77b4', width=2),
        mode='lines'
    ))
    
    fig_raw_materials.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Frames_Carbon'],
        name='Rahmen Bestand (Carbon)',
        line=dict(color='#ff7f0e', width=2),
        mode='lines'
    ))
    
    fig_raw_materials.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Saddles'],
        name='Sattel Bestand',
        line=dict(color='#2ca02c', width=2),
        mode='lines'
    ))
    
    fig_raw_materials.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="Lagerbestand (Einheiten)",
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_raw_materials, use_container_width=True)
    
    st.caption("💡 **Sägezahn-Muster:** Spitzen zeigen Bestellankünfte, abfallende Linien zeigen Verbrauch")

with col2:
    # Finished Goods Inventory (FGI)
    st.subheader("Fertigerzeugnislager (FGI)")
    
    # Da wir sofort versenden, ist FGI normalerweise 0 oder sehr niedrig
    # Berechne FGI als Differenz zwischen Produktion und Versand (vereinfacht)
    # In unserem Modell: FGI = 0, da sofort versendet wird
    results_df['FGI_Stock'] = 0.0  # Just-in-Time: Kein FGI
    
    fig_fgi = go.Figure()
    
    fig_fgi.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['FGI_Stock'],
        name='FGI Bestand',
        line=dict(color='#9467bd', width=2),
        mode='lines',
        fill='tozeroy'
    ))
    
    fig_fgi.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="FGI Bestand (Einheiten)",
        height=400,
        hovermode='x unified',
        showlegend=True
    )
    st.plotly_chart(fig_fgi, use_container_width=True)
    
    st.caption("💡 **Just-in-Time Flow:** FGI ist 0, da Produkte sofort nach Produktion versendet werden")

st.divider()

# ============================================================================
# SECTION 3: Market Performance Tables (Target vs. Actual)
# ============================================================================
st.header("🌍 Marktleistungs-Tabellen")

# Markt-Namen Mapping
market_names = {
    'DE': 'Deutschland',
    'USA': 'USA',
    'FR': 'Frankreich',
    'CN': 'China',
    'CH': 'Schweiz',
    'AT': 'Österreich'
}

# Berechne Market Performance für jeden Markt
for market_code, market_name in market_names.items():
    st.subheader(f"📊 {market_name} ({market_code})")
    
    # Berechne IST und Soll pro Produkt
    market_share = MasterData.MARKETS[market_code]['share']
    
    market_data = []
    global_actual_total = results_df['Actual_Build'].sum()
    
    for product in MasterData.BOM.keys():
        product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
        
        # IST-Wert: Tatsächlich gelieferte Menge (Actual_Build * market_share * product_share)
        ist_value = results_df['Actual_Build'].sum() * market_share * product_share
        
        # Soll-Wert: Geplante Nachfrage (Daily_Target * market_share * product_share)
        soll_value = results_df['Daily_Target'].sum() * market_share * product_share
        
        # Service Level %
        service_level = (ist_value / soll_value * 100) if soll_value > 0 else 0.0
        
        # Share % (Anteil am globalen Actual)
        market_actual = ist_value
        share_percent = (market_actual / global_actual_total * 100) if global_actual_total > 0 else 0.0
        
        market_data.append({
            'Produkt': product,
            'IST-Wert': round(ist_value, 0),
            'Soll-Wert': round(soll_value, 0),
            'Service Level (%)': round(service_level, 2),
            'Share (%)': round(share_percent, 2)
        })
    
    market_df = pd.DataFrame(market_data)
    
    # Formatiere für bessere Darstellung
    display_df = market_df.copy()
    display_df['IST-Wert'] = display_df['IST-Wert'].apply(lambda x: f"{x:,.0f}")
    display_df['Soll-Wert'] = display_df['Soll-Wert'].apply(lambda x: f"{x:,.0f}")
    display_df['Service Level (%)'] = display_df['Service Level (%)'].apply(lambda x: f"{x:.2f}%")
    display_df['Share (%)'] = display_df['Share (%)'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Zusammenfassung für diesen Markt
    total_ist = market_df['IST-Wert'].sum()
    total_soll = market_df['Soll-Wert'].sum()
    overall_service_level = (total_ist / total_soll * 100) if total_soll > 0 else 0.0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gesamt IST-Wert", f"{total_ist:,.0f}")
    with col2:
        st.metric("Gesamt Soll-Wert", f"{total_soll:,.0f}")
    with col3:
        st.metric("Gesamt Service Level", f"{overall_service_level:.2f}%")
    
    st.divider()
