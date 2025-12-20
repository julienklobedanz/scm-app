"""
Sidebar UI Component
"""

import streamlit as st
from typing import Tuple


def render_sidebar() -> Tuple[int, int, int, int, int]:
    """Rendert die Sidebar und gibt Parameter zurück"""
    with st.sidebar:
        st.header("⚙️ Parameter")
        
        yearly_volume = st.number_input(
            "Jährliches Volumen",
            min_value=100000,
            max_value=1000000,
            value=370000,
            step=10000
        )
        
        st.subheader("Initialer Lagerbestand (China)")
        initial_stock_frames_alu = st.number_input(
            "Rahmen Alu (Initial)",
            min_value=0,
            value=1000,
            step=100
        )
        initial_stock_frames_carbon = st.number_input(
            "Rahmen Carbon (Initial)",
            min_value=0,
            value=1000,
            step=100
        )
        initial_stock_saddles_standard = st.number_input(
            "Sättel Standard (Initial)",
            min_value=0,
            value=1000,
            step=100
        )
        initial_stock_saddles_premium = st.number_input(
            "Sättel Premium (Initial)",
            min_value=0,
            value=1000,
            step=100
        )
        
        if st.button("🚀 Simulation starten", type="primary"):
            st.session_state.run_simulation = True
        
        return (
            yearly_volume,
            initial_stock_frames_alu,
            initial_stock_frames_carbon,
            initial_stock_saddles_standard,
            initial_stock_saddles_premium
        )

