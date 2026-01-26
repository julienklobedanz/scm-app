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


def render_scenario_sidebar(key_suffix=""):
    """Rendert die Szenarien-Sidebar mit allen Funktionen zum Hinzufügen und Verwalten von Szenarien
    
    Args:
        key_suffix: Eindeutiger Suffix für Keys (z.B. "_reporting", "_app") um Duplikate zu vermeiden
    """
    
    # Initialisiere ScenarioManager falls nicht vorhanden
    if 'scenario_manager' not in st.session_state:
        st.session_state.scenario_manager = ScenarioManager()
    
    with st.sidebar:
        # Planungsbeginn wurde in globale Konfiguration (Stammdaten) verschoben
        
        st.header("🎭 Szenarien")
        st.caption("Standard-Szenario läuft permanent im Hintergrund. Zusätzliche Szenarien können parallel aktiviert werden.")
        
        st.subheader("➕ Szenarien hinzufügen")
        
        # Szenario-Auswahl mit eindeutigem Key
        scenario_type = st.selectbox(
            "Szenario-Typ",
            ["Marketingaktion", "Wasserschaden im Lager", "Maschinenausfall (China)", "Lieferprobleme (China)"],
            key=f"scenario_type_global{key_suffix}"
        )
        
        planning_year = st.session_state.get('planning_year', 2027)
        workday_calc = WorkdayCalculator(year=planning_year)
        start_of_year = date(planning_year, 1, 1)
        
        if scenario_type == "Marketingaktion":
            st.subheader("Marketingaktion")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 2, 19), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"marketing_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 3, 11), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"marketing_end_global{key_suffix}")
            demand_factor = st.slider("Nachfrage-Erhöhung (Faktor)", 1.0, 3.0, 1.5, 0.1, key=f"marketing_factor_global{key_suffix}")
            
            # Produktauswahl: Multi-Select für betroffene Produkte
            all_products = list(MasterData.BOM.keys())
            selected_products = st.multiselect(
                "Betroffene Produkte",
                all_products,
                default=all_products,  # Standard: Alle Produkte (Rückwärtskompatibilität)
                help="Wählen Sie die Produkte aus, für die die Marketingaktion gelten soll. Wenn keine Auswahl getroffen wird, wirkt die Aktion auf alle Produkte.",
                key=f"marketing_products_global{key_suffix}"
            )
            
            if st.button("➕ Marketingaktion hinzufügen", key=f"add_marketing_global{key_suffix}"):
                start_day = (start_date - start_of_year).days
                end_day = (end_date - start_of_year).days
                
                # Wenn alle Produkte ausgewählt oder keine Auswahl, dann None (alle Produkte)
                affected_products = None if (not selected_products or len(selected_products) == len(all_products)) else selected_products
                
                # Name mit Produktliste (wenn nicht alle Produkte)
                if affected_products:
                    products_str = ", ".join(affected_products[:3])  # Erste 3 Produkte
                    if len(affected_products) > 3:
                        products_str += f" (+{len(affected_products) - 3} weitere)"
                    name = f"Marketingaktion ({products_str}) ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})"
                else:
                    name = f"Marketingaktion ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})"
                
                scenario = MarketingCampaignScenario(
                    name=name,
                    start_day=start_day,
                    end_day=end_day,
                    demand_increase_factor=demand_factor,
                    affected_products=affected_products
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                st.rerun()
        
        elif scenario_type == "Wasserschaden im Lager":
            st.subheader("Wasserschaden im Lager")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 4, 10), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"warehouse_damage_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 4, 20), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"warehouse_damage_end_global{key_suffix}")
            stock_loss = st.slider("Lagerbestands-Verlust (%)", 0.0, 1.0, 0.5, 0.1, key=f"warehouse_damage_loss_global{key_suffix}")
            
            if st.button("➕ Wasserschaden hinzufügen", key=f"add_warehouse_damage_global{key_suffix}"):
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
            start_date = st.date_input("Start-Datum", value=date(planning_year, 6, 1), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"supplier_breakdown_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 6, 10), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"supplier_breakdown_end_global{key_suffix}")
            component = st.selectbox("Betroffene Komponente", ["saddles"], key=f"supplier_component_global{key_suffix}")  # Nur Sättel
            
            if st.button("➕ Lieferantenausfall hinzufügen", key=f"add_supplier_breakdown_global{key_suffix}"):
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
            start_date = st.date_input("Start-Datum", value=date(planning_year, 7, 19), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"delivery_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 7, 29), min_value=start_of_year, max_value=date(planning_year, 12, 31), key=f"delivery_end_global{key_suffix}")
            loss = st.slider("Warenverlust (%)", 0.0, 1.0, 0.0, 0.1, key=f"delivery_loss_global{key_suffix}")
            delay = st.number_input("Verspätung (Tage)", min_value=0, max_value=30, value=0, key=f"delivery_delay_global{key_suffix}")
            
            if st.button("➕ Lieferproblem hinzufügen", key=f"add_delivery_global{key_suffix}"):
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
                    if st.button("🗑️", key=f"remove_{original_idx}_global{key_suffix}"):
                        st.session_state.scenario_manager.scenarios.pop(original_idx)
                        # WICHTIG: Invalidiere alle Caches, die von Szenarien abhängen
                        # 1. Invalidiere volume_planning Cache
                        st.session_state.volume_planning_calculated = False
                        st.session_state.volume_planning_cache_key = None
                        # 2. Invalidiere Materiallager Cache
                        if 'saddle_logs_cache' in st.session_state:
                            del st.session_state.saddle_logs_cache
                        # 3. Invalidiere Caches in ChinaTransportManager (wenn Simulator vorhanden)
                        if 'simulator' in st.session_state and st.session_state.simulator:
                            if hasattr(st.session_state.simulator, 'china_transport_manager'):
                                manager = st.session_state.simulator.china_transport_manager
                                manager._supplier_log_cache = {}
                                manager._inbound_df_cache = {}
                                manager._inbound_df_cache_key = None
                        # 4. Invalidiere Produktionslogs Cache
                        if 'production_logs_cache' in st.session_state:
                            del st.session_state.production_logs_cache
                        if 'production_logs_cache_key' in st.session_state:
                            del st.session_state.production_logs_cache_key
                        st.rerun()
        else:
            st.caption("Keine zusätzlichen Szenarien aktiv")
        
        st.divider()
        
        # Simulation starten
        if st.button("🔄 Simulation neu starten", type="primary", use_container_width=True):
            st.session_state.run_simulation = True
            st.session_state.manual_restart = True
            st.rerun()

