"""
Charts UI Component
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict


def render_bom_view() -> None:
    """Zeigt die BOM-Tabelle an"""
    from config.master_data import MasterData
    
    st.header("📋 Bill of Materials (BOM)")
    bom_data = []
    for product, components in MasterData.BOM.items():
        bom_data.append({
            'Produkt': product,
            'Rahmen': components['frame'],
            'Sattel': components['saddle'],
            'Gabel': components['fork']
        })
    bom_df = pd.DataFrame(bom_data)
    st.dataframe(bom_df, use_container_width=True, hide_index=True)


def render_kpis(kpis: Dict[str, float]) -> None:
    """Zeigt die KPIs an"""
    st.header("📊 Key Performance Indicators (KPIs)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Service Level", f"{kpis['service_level']:.2f}%")
    with col2:
        st.metric("Tage gestoppt (Sättel)", kpis['days_stopped_saddles'])
    with col3:
        # Rahmen sind unbegrenzt verfügbar, daher immer 0
        st.metric("Tage gestoppt (Rahmen)", 0)


def render_inventory_chart(results_df: pd.DataFrame) -> None:
    """Zeigt das Lagerbestands-Chart"""
    st.subheader("Lagerbestände (Rahmen vs. Sättel)")
    fig_inventory = go.Figure()
    
    # Verwende Datum für x-Achse, falls verfügbar
    x_axis = results_df['Date'] if 'Date' in results_df.columns else results_df['Day']
    
    fig_inventory.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Frames_Alu'],
        name='Rahmen Alu',
        line=dict(color='#1f77b4')
    ))
    fig_inventory.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Frames_Carbon'],
        name='Rahmen Carbon',
        line=dict(color='#ff7f0e')
    ))
    fig_inventory.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Stock_Saddles'],
        name='Sättel',
        line=dict(color='#2ca02c')
    ))
    
    fig_inventory.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="Lagerbestand",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_inventory, use_container_width=True)


def render_backlog_chart_de(results_df: pd.DataFrame) -> None:
    """Zeigt das Backlog-Chart für Deutschland"""
    st.subheader("Backlog-Entwicklung (Deutschland)")
    fig_backlog = go.Figure()
    
    x_axis = results_df['Date'] if 'Date' in results_df.columns else results_df['Day']
    fig_backlog.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Backlog_DE'],
        name='Backlog DE',
        fill='tozeroy',
        line=dict(color='#9467bd')
    ))
    
    fig_backlog.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="Backlog (Einheiten)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_backlog, use_container_width=True)


def render_backlog_chart_all(results_df: pd.DataFrame) -> None:
    """Zeigt das Backlog-Chart für alle Märkte"""
    from config.master_data import MasterData
    
    st.subheader("Backlog-Entwicklung (Alle Märkte)")
    fig_backlog_all = go.Figure()
    
    x_axis = results_df['Date'] if 'Date' in results_df.columns else results_df['Day']
    for market in MasterData.MARKETS.keys():
        fig_backlog_all.add_trace(go.Scatter(
            x=x_axis,
            y=results_df[f'Backlog_{market}'],
            name=f'Backlog {market}',
            mode='lines'
        ))
    
    fig_backlog_all.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="Backlog (Einheiten)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_backlog_all, use_container_width=True)


def render_production_chart(results_df: pd.DataFrame) -> None:
    """Zeigt das Produktions-Chart"""
    st.subheader("Produktion vs. Ziel")
    fig_production = go.Figure()
    
    x_axis = results_df['Date'] if 'Date' in results_df.columns else results_df['Day']
    fig_production.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Daily_Target'],
        name='Tägliches Ziel',
        line=dict(color='#2ca02c', dash='dash')
    ))
    fig_production.add_trace(go.Scatter(
        x=x_axis,
        y=results_df['Actual_Build'],
        name='Tatsächliche Produktion',
        line=dict(color='#d62728')
    ))
    
    fig_production.update_layout(
        xaxis_title="Datum" if 'Date' in results_df.columns else "Tag",
        yaxis_title="Einheiten",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_production, use_container_width=True)

