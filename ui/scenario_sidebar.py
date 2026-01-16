"""
Szenarien Sidebar Component
Wiederverwendbare Sidebar-Komponente für Szenarien-Management
"""

import streamlit as st
from datetime import date
from models.scenarios import (
    ScenarioManager,
    MarketingCampaignScenario,
    WarehouseDamageScenario,
    SupplierBreakdownScenario,
    DeliveryProblemScenario,
    StandardScenario
)
from simulation.workday_calculator import WorkdayCalculator
from config.master_data import MasterData


def render_scenario_sidebar():
    """Rendert die Szenarien-Sidebar mit allen Funktionen zum Hinzufügen und Verwalten von Szenarien"""
    
    # Initialisiere ScenarioManager falls nicht vorhanden
    if 'scenario_manager' not in st.session_state:
        st.session_state.scenario_manager = ScenarioManager()
    
    with st.sidebar:
        # Jahr-Auswahl (Planungsbeginn) - oberhalb von Szenarien
        if 'planning_year' not in st.session_state:
            st.session_state.planning_year = 2027
        
        planning_year = st.number_input(
            "Planungsbeginn",
            min_value=2020,
            max_value=2030,
            value=st.session_state.planning_year,
            step=1,
            key="planning_year_input"
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
        
        st.header("🎭 Szenarien")
        st.caption("Standard-Szenario läuft permanent im Hintergrund. Zusätzliche Szenarien können parallel aktiviert werden.")
        
        st.subheader("➕ Szenarien hinzufügen")
        
        # Szenario-Auswahl
        scenario_type = st.selectbox(
            "Szenario-Typ",
            ["Marketingaktion", "Wasserschaden im Lager", "Maschinenausfall (China)", "Lieferprobleme (China)"],
            key="scenario_type_global"
        )
        
        planning_year = st.session_state.get('planning_year', 2027)
        workday_calc = WorkdayCalculator(year=planning_year)
        start_of_year = date(planning_year, 1, 1)
        
        if scenario_type == "Marketingaktion":
            st.subheader("Marketingaktion")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 2, 19), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="marketing_start_global")
            end_date = st.date_input("End-Datum", value=date(planning_year, 3, 11), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="marketing_end_global")
            demand_factor = st.slider("Nachfrage-Erhöhung (Faktor)", 1.0, 3.0, 1.5, 0.1, key="marketing_factor_global")
            
            if st.button("➕ Marketingaktion hinzufügen", key="add_marketing_global"):
                start_day = (start_date - start_of_year).days
                end_day = (end_date - start_of_year).days
                scenario = MarketingCampaignScenario(
                    name=f"Marketingaktion ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=start_day,
                    end_day=end_day,
                    demand_increase_factor=demand_factor
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                st.rerun()
        
        elif scenario_type == "Wasserschaden im Lager":
            st.subheader("Wasserschaden im Lager")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 4, 10), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="warehouse_damage_start_global")
            end_date = st.date_input("End-Datum", value=date(planning_year, 4, 20), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="warehouse_damage_end_global")
            stock_loss = st.slider("Lagerbestands-Verlust (%)", 0.0, 1.0, 0.5, 0.1, key="warehouse_damage_loss_global")
            
            if st.button("➕ Wasserschaden hinzufügen", key="add_warehouse_damage_global"):
                start_day = (start_date - start_of_year).days
                end_day = (end_date - start_of_year).days
                scenario = WarehouseDamageScenario(
                    name=f"Wasserschaden im Lager ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=start_day,
                    end_day=end_day,
                    stock_loss_percentage=stock_loss,
                    affected_component="saddles"
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                st.rerun()
        
        elif scenario_type == "Maschinenausfall (China)":
            st.subheader("Maschinenausfall (China)")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 6, 1), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="supplier_breakdown_start_global")
            end_date = st.date_input("End-Datum", value=date(planning_year, 6, 10), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="supplier_breakdown_end_global")
            component = st.selectbox("Betroffene Komponente", ["saddles"], key="supplier_component_global")  # Nur Sättel
            
            if st.button("➕ Lieferantenausfall hinzufügen", key="add_supplier_breakdown_global"):
                start_day = (start_date - start_of_year).days
                end_day = (end_date - start_of_year).days
                scenario = SupplierBreakdownScenario(
                    name=f"Lieferantenausfall Sättel ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=start_day,
                    end_day=end_day,
                    component_type="saddles"  # Immer Sättel
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                st.rerun()
        
        elif scenario_type == "Lieferprobleme (China)":
            st.subheader("Lieferprobleme (China)")
            st.info("Betroffene Komponente: Sättel")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 7, 19), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="delivery_start_global")
            end_date = st.date_input("End-Datum", value=date(planning_year, 7, 29), min_value=start_of_year, max_value=date(planning_year, 12, 31), key="delivery_end_global")
            loss = st.slider("Warenverlust (%)", 0.0, 1.0, 0.0, 0.1, key="delivery_loss_global")
            delay = st.number_input("Verspätung (Tage)", min_value=0, max_value=30, value=0, key="delivery_delay_global")
            
            if st.button("➕ Lieferproblem hinzufügen", key="add_delivery_global"):
                start_day = (start_date - start_of_year).days
                end_day = (end_date - start_of_year).days
                scenario = DeliveryProblemScenario(
                    name=f"Lieferproblem Sättel ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=start_day,
                    end_day=end_day,
                    component_type="saddles",  # Immer Sättel
                    loss_percentage=loss,
                    delay_days=delay
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                st.rerun()
        
        st.divider()
        
        # Aktive Szenarien anzeigen (ohne Standard-Szenario)
        custom_scenarios = [
            s for s in st.session_state.scenario_manager.scenarios
            if not isinstance(s, StandardScenario)
        ]
        
        if custom_scenarios:
            st.subheader("📋 Aktive Szenarien")
            for i, scenario in enumerate(custom_scenarios):
                # Finde Index im ursprünglichen Array
                original_idx = st.session_state.scenario_manager.scenarios.index(scenario)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {scenario.name}")
                with col2:
                    if st.button("🗑️", key=f"remove_{original_idx}_global"):
                        st.session_state.scenario_manager.scenarios.pop(original_idx)
                        st.rerun()
        else:
            st.caption("Keine zusätzlichen Szenarien aktiv")
        
        st.divider()
        
        # Simulation starten
        if st.button("🔄 Simulation neu starten", type="primary", use_container_width=True):
            st.session_state.run_simulation = True
            st.session_state.manual_restart = True
            st.rerun()

