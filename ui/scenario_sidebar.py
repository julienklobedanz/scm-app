"""
Szenarien Sidebar Component
Wiederverwendbare Sidebar-Komponente für Szenarien-Management
"""

import streamlit as st
from datetime import date, datetime, timedelta
from typing import List, Optional
from models.scenarios import (
    ScenarioManager,
    MarketingCampaignScenario,
    WarehouseDamageScenario,
    SupplierBreakdownScenario,
    DelayScenario,
    WaterDamageScenario,
    CargoLossScenario,
    StandardScenario
)
from simulation.workday_calculator import WorkdayCalculator
from config.master_data import MasterData


def _day_index_to_date(day_idx: int, planning_year: int) -> date:
    """Konvertiert Tages-Index (relativ zum Planungsjahr/Vorjahr) in Datum."""
    start_of_year = date(planning_year, 1, 1)
    if day_idx >= 0:
        return start_of_year + timedelta(days=day_idx)
    # Vorjahr (z. B. 2026 bei planning_year 2027)
    offset_2026 = (date(2026, 1, 1) - start_of_year).days
    return date(2026, 1, 1) + timedelta(days=day_idx - offset_2026)


def _format_scenario_details(scenario, planning_year: int) -> Optional[str]:
    """
    Erzeugt eine kompakte Parameter-Zeile für die Anzeige aktiver Szenarien.
    Returns None wenn keine Zusatzinfos nötig sind.
    """
    if isinstance(scenario, MarketingCampaignScenario):
        total = getattr(scenario, "additional_demand_total", 0)
        products = getattr(scenario, "affected_products", None)
        if products and len(products) > 0:
            product_str = ", ".join(products) if len(products) <= 3 else ", ".join(products[:2]) + f" (+{len(products) - 2} weitere)"
        else:
            product_str = "Alle Produkte"
        return f"Zusatzbedarf: {int(total)} Stück · Produkte: {product_str}"

    if isinstance(scenario, WaterDamageScenario):
        loss = getattr(scenario, "loss_quantity_absolute", 0)
        saddles = getattr(scenario, "affected_saddles", None)
        if saddles and len(saddles) > 0:
            saddle_str = ", ".join(saddles) if len(saddles) <= 3 else ", ".join(saddles[:2]) + f" (+{len(saddles) - 2} weitere)"
        else:
            saddle_str = "Alle Satteltypen"
        return f"Verlustmenge: {int(loss)} Stück · Satteltypen: {saddle_str}"

    if isinstance(scenario, SupplierBreakdownScenario):
        comp = getattr(scenario, "component_type", "saddles")
        comp_label = "Sättel" if comp in ("saddles", "all") else comp
        return f"Komponente: {comp_label}"

    if isinstance(scenario, DelayScenario):
        days = getattr(scenario, "delay_days", 0)
        stage = getattr(scenario, "delay_stage", "")
        stage_labels = {"truck_china_arrival": "Ankunft LKW China", "ship_arrival": "Ankunft Schiff", "truck_de_arrival": "Ankunft LKW Deutschland"}
        stage_label = stage_labels.get(stage, stage)
        return f"Verspätung: {int(days)} Tage · Stufe: {stage_label}"

    if isinstance(scenario, CargoLossScenario):
        return "Komponente: Sättel (Schiffsankunft)"

    if isinstance(scenario, WarehouseDamageScenario):
        pct = getattr(scenario, "stock_loss_percentage", 0) * 100
        comp = getattr(scenario, "affected_component", "saddles")
        return f"Verlust: {pct:.0f}% · Komponente: {comp}"

    return None


def _get_planned_arrival_dates(delay_stage: str, planning_year: int) -> List[date]:
    """
    Extrahiert alle geplanten Ankunftsdaten für einen bestimmten Verspätungstyp aus der Inbound-Tabelle.
    
    PERFORMANCE-OPTIMIERT: Verwendet Caching um mehrfache Berechnungen zu vermeiden.
    
    Args:
        delay_stage: "truck_china_arrival", "ship_arrival", oder "truck_de_arrival"
        planning_year: Planungsjahr
    
    Returns:
        Liste von Datums-Objekten (sortiert)
    """
    # PERFORMANCE: Cache-Key für geplante Ankunftsdaten
    cache_key = f"planned_arrival_dates_{delay_stage}_{planning_year}"
    
    # Prüfe Cache zuerst
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    arrival_dates = []
    
    # Prüfe ob Simulator verfügbar ist
    if 'simulator' not in st.session_state or not st.session_state.simulator:
        # Cache leeres Ergebnis
        st.session_state[cache_key] = arrival_dates
        return arrival_dates
    
    try:
        manager = st.session_state.simulator.china_transport_manager
        if not manager:
            # Cache leeres Ergebnis
            st.session_state[cache_key] = arrival_dates
            return arrival_dates
        
        # PERFORMANCE: Hole Inbound-Tabelle (verwendet internes Caching)
        # Die get_inbound_log_dataframe() Methode cached bereits das Ergebnis,
        # daher ist dieser Aufruf nicht so teuer wie es scheint
        from config.master_data import MasterData
        saddle_shares = MasterData.calculate_saddle_shares()
        inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
        
        if inbound_df.empty:
            # Cache leeres Ergebnis
            st.session_state[cache_key] = arrival_dates
            return arrival_dates
        
        # Bestimme Spaltenname basierend auf delay_stage
        # HINWEIS: "Ankunft LKW 🇨🇳" und "Ankunft Schiff 🇩🇪" zeigen die tatsächlichen Ankünfte,
        # aber ohne Verspätungen sind sie gleich den geplanten Ankünften.
        # Für die Verspätungsprüfung verwenden wir diese Spalten, da sie die geplanten Ankünfte repräsentieren
        # (wenn keine Verspätungen aktiv sind).
        column_map = {
            "truck_china_arrival": "Ankunft LKW 🇨🇳",  # Tatsächliche Ankunft = geplante Ankunft (ohne Verspätungen)
            "ship_arrival": "Ankunft Schiff 🇩🇪",  # Tatsächliche Ankunft = geplante Ankunft (ohne Verspätungen)
            "truck_de_arrival": "Geplante Ankunft LKW 🇩🇪"  # Explizit geplante Ankunft
        }
        
        column_name = column_map.get(delay_stage)
        if not column_name or column_name not in inbound_df.columns:
            # Cache leeres Ergebnis
            st.session_state[cache_key] = arrival_dates
            return arrival_dates
        
        # PERFORMANCE: Verwende Set für schnelleres Duplikat-Check
        seen_dates = set()
        
        # Extrahiere alle eindeutigen Datums aus der Spalte
        for _, row in inbound_df.iterrows():
            date_str = row.get(column_name, '')
            if date_str and isinstance(date_str, str) and date_str.strip():
                try:
                    parsed_date = datetime.strptime(date_str.strip(), MasterData.DATE_FORMAT).date()
                    # Nur Daten im Planungsjahr oder 2026 (für Vorlauf)
                    if (parsed_date.year == planning_year or parsed_date.year == 2026) and parsed_date not in seen_dates:
                        arrival_dates.append(parsed_date)
                        seen_dates.add(parsed_date)
                except (ValueError, TypeError):
                    continue
        
        # Sortiere Datums
        arrival_dates.sort()
        
        # Cache Ergebnis
        st.session_state[cache_key] = arrival_dates
        return arrival_dates
        
    except Exception:
        # Bei Fehler: Cache leeres Ergebnis und zurückgeben
        st.session_state[cache_key] = arrival_dates
        return arrival_dates


def _safe_rerun():
    """
    Führt st.rerun() sicher aus, prüft ob Simulation läuft.
    Wenn Simulation läuft, zeigt Warnung statt rerun.
    """
    if not st.session_state.get('simulation_running', False):
        st.rerun()
    else:
        st.warning("⚠️ Simulation läuft. Die Änderungen werden nach Abschluss der Simulation übernommen.")


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
        
        st.header("Szenarien hinzufügen")
        st.caption("Standard-Szenario läuft permanent im Hintergrund. Zusätzliche Szenarien können parallel aktiviert werden.")
        
        # Szenario-Auswahl mit eindeutigem Key
        scenario_type = st.selectbox(
            "Szenario-Typ",
            ["Marketingaktion", "Wasserschaden im Lager", "Maschinenausfall (China)", "Verspätung", "Ladungsverlust auf See"],
            key=f"scenario_type_global{key_suffix}"
        )
        
        planning_year = st.session_state.get('planning_year', 2027)
        workday_calc = WorkdayCalculator(year=planning_year)
        start_of_year = date(planning_year, 1, 1)
        # Erlaube auch Daten aus 2026
        min_date = date(2026, 1, 1)
        max_date = date(planning_year, 12, 31)
        
        if scenario_type == "Marketingaktion":
            st.subheader("Marketingaktion")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 2, 19), min_value=min_date, max_value=max_date, format="DD.MM.YYYY", key=f"marketing_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 3, 11), min_value=min_date, max_value=max_date, format="DD.MM.YYYY", key=f"marketing_end_global{key_suffix}")
            # Anzahl Arbeitstage im gewählten Zeitraum (für Info und Verteilung)
            start_of_year = date(planning_year, 1, 1)
            _start_day = (start_date - start_of_year).days if start_date.year == planning_year else (start_date - date(2026, 1, 1)).days + (date(2026, 1, 1) - start_of_year).days
            _end_day = (end_date - start_of_year).days if end_date.year == planning_year else (end_date - date(2026, 1, 1)).days + (date(2026, 1, 1) - start_of_year).days
            workdays_in_range = sum(1 for d in range(_start_day, _end_day + 1) if workday_calc.is_workday(d))
            if workdays_in_range > 0:
                st.caption(f"Im gewählten Zeitraum: **{workdays_in_range}** Arbeitstage. Der Gesamtbedarf wird gleichmäßig auf diese Tage verteilt.")
            additional_demand_total = st.number_input(
                "Zusätzlicher Bedarf gesamt",
                min_value=0,
                value=5000,
                step=500,
                key=f"marketing_additional_global{key_suffix}",
                help="Gesamtmenge an zusätzlicher Nachfrage für den gesamten ausgewählten Zeitraum. Wird automatisch auf die Arbeitstage im Zeitraum verteilt und auf die betroffenen Produkte anteilig."
            )
            
            # Produktauswahl: Multi-Select für betroffene Produkte
            all_products = list(MasterData.BOM.keys())
            selected_products = st.multiselect(
                "Betroffene Produkte",
                all_products,
                default=all_products,  # Standard: Alle Produkte (Rückwärtskompatibilität)
                placeholder="Optionen wählen",
                help="Wählen Sie die Produkte aus, für die die Marketingaktion gelten soll. Wenn keine Auswahl getroffen wird, wirkt die Aktion auf alle Produkte.",
                key=f"marketing_products_global{key_suffix}"
            )
            
            if st.button("➕ Marketingaktion hinzufügen", key=f"add_marketing_global{key_suffix}"):
                # Berechne start_day und end_day relativ zum Planungsjahr
                # Wenn das Datum aus 2026 stammt, berechne es relativ zu 2026, dann addiere Offset
                if start_date.year == 2026:
                    start_date_base = date(2026, 1, 1)
                    start_day = (start_date - start_date_base).days
                    # Offset: Tage zwischen 1.1.2026 und 1.1.planning_year (negativ, da 2026 vor 2027)
                    offset = (start_date_base - start_of_year).days
                    start_day = start_day + offset
                else:
                    start_day = (start_date - start_of_year).days
                
                if end_date.year == 2026:
                    end_date_base = date(2026, 1, 1)
                    end_day = (end_date - end_date_base).days
                    offset = (end_date_base - start_of_year).days
                    end_day = end_day + offset
                else:
                    end_day = (end_date - start_of_year).days
                
                workdays_in_period = sum(1 for d in range(start_day, end_day + 1) if workday_calc.is_workday(d))
                workdays_in_period = max(1, workdays_in_period)
                
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
                    additional_demand_total=float(additional_demand_total),
                    workdays_in_period=workdays_in_period,
                    affected_products=affected_products
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                _safe_rerun()
        
        elif scenario_type == "Wasserschaden im Lager":
            st.subheader("Wasserschaden im Materiallager")
            damage_date = st.date_input("Datum", value=date(planning_year, 4, 10), min_value=min_date, max_value=max_date, format="DD.MM.YYYY", key=f"water_damage_date_global{key_suffix}")
            loss_quantity_absolute = st.number_input(
                "Verlustmenge",
                min_value=0,
                value=0,
                step=1,
                key=f"water_damage_loss_abs_global{key_suffix}",
                help="0 = kein Abzug. Sonst: Verlust = min(Eingabe, Bestand abends) pro betroffener Satteltyp; bei Eingabe > Bestand abends wird nur auf 0 gesetzt."
            )
            all_saddles = list(MasterData.calculate_saddle_shares().keys())
            selected_saddles = st.multiselect(
                "Betroffene Satteltypen",
                all_saddles,
                default=all_saddles,
                placeholder="Optionen wählen",
                help="Nur für die ausgewählten Satteltypen wird die Verlustmenge abgezogen. Keine Auswahl = alle.",
                key=f"water_damage_saddles_global{key_suffix}"
            )
            if st.button("➕ Wasserschaden hinzufügen", key=f"add_water_damage_global{key_suffix}"):
                # Berechne damage_day relativ zum Planungsjahr
                if damage_date.year == 2026:
                    damage_date_base = date(2026, 1, 1)
                    damage_day = (damage_date - damage_date_base).days
                    offset = (damage_date_base - start_of_year).days
                    damage_day = damage_day + offset
                else:
                    damage_day = (damage_date - start_of_year).days
                affected_saddles = None if (not selected_saddles or len(selected_saddles) == len(all_saddles)) else selected_saddles
                scenario = WaterDamageScenario(
                    name=f"Wasserschaden im Materiallager ({damage_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=damage_day,
                    end_day=damage_day,  # Exaktes Datum: start_day = end_day
                    damage_date=damage_day,
                    affected_component="saddles",
                    loss_quantity_absolute=float(loss_quantity_absolute),
                    affected_saddles=affected_saddles
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                
                # WICHTIG: Invalidiere alle Caches, da Wasserschaden die Berechnungen beeinflusst
                # 1. Invalidiere volume_planning Cache
                st.session_state.volume_planning_calculated = False
                st.session_state.volume_planning_cache_key = None
                # 2. Invalidiere Materiallager Cache
                if 'saddle_logs_cache' in st.session_state:
                    del st.session_state.saddle_logs_cache
                if 'material_inventory_data' in st.session_state:
                    del st.session_state.material_inventory_data
                if 'material_inventory_cache_key' in st.session_state:
                    del st.session_state.material_inventory_cache_key
                # 3. Invalidiere Produktionslogs Cache
                if 'production_logs_cache' in st.session_state:
                    del st.session_state.production_logs_cache
                if 'production_logs_cache_key' in st.session_state:
                    del st.session_state.production_logs_cache_key
                # 4. Invalidiere Caches in ChinaTransportManager (wenn Simulator vorhanden)
                if 'simulator' in st.session_state and st.session_state.simulator:
                    if hasattr(st.session_state.simulator, 'china_transport_manager'):
                        manager = st.session_state.simulator.china_transport_manager
                        manager._supplier_log_cache = {}
                        manager._inbound_df_cache = {}
                        manager._inbound_df_cache_key = None
                
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                _safe_rerun()
        
        elif scenario_type == "Maschinenausfall (China)":
            st.subheader("Maschinenausfall (China)")
            start_date = st.date_input("Start-Datum", value=date(planning_year, 6, 1), min_value=min_date, max_value=max_date, format="DD.MM.YYYY", key=f"supplier_breakdown_start_global{key_suffix}")
            end_date = st.date_input("End-Datum", value=date(planning_year, 6, 10), min_value=min_date, max_value=max_date, format="DD.MM.YYYY", key=f"supplier_breakdown_end_global{key_suffix}")
            
            if st.button("➕ Lieferantenausfall hinzufügen", key=f"add_supplier_breakdown_global{key_suffix}"):
                # Berechne start_day und end_day relativ zum Planungsjahr
                if start_date.year == 2026:
                    start_date_base = date(2026, 1, 1)
                    start_day = (start_date - start_date_base).days
                    offset = (start_date_base - start_of_year).days
                    start_day = start_day + offset
                else:
                    start_day = (start_date - start_of_year).days
                
                if end_date.year == 2026:
                    end_date_base = date(2026, 1, 1)
                    end_day = (end_date - end_date_base).days
                    offset = (end_date_base - start_of_year).days
                    end_day = end_day + offset
                else:
                    end_day = (end_date - start_of_year).days
                scenario = SupplierBreakdownScenario(
                    name=f"Maschinenausfall Sättel ({start_date.strftime(MasterData.DATE_FORMAT)} - {end_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=start_day,
                    end_day=end_day,
                    component_type="saddles"  # Immer Sättel
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                _safe_rerun()
        
        elif scenario_type == "Verspätung":
            st.subheader("Verspätung")
            delay_stage = st.selectbox(
                "Lieferkette",
                ["truck_china_arrival", "ship_arrival", "truck_de_arrival"],
                format_func=lambda x: {
                    "truck_china_arrival": "Ankunft LKW China",
                    "ship_arrival": "Ankunft Schiff",
                    "truck_de_arrival": "Ankunft LKW Deutschland"
                }[x],
                key=f"delay_stage_global{key_suffix}"
            )
            
            # Hole geplante Ankunftsdaten für den ausgewählten Verspätungstyp
            planned_dates = _get_planned_arrival_dates(delay_stage, planning_year)
            
            if planned_dates:
                # Zeige nur geplante Ankunftsdaten als Optionen
                stage_name = {
                    "truck_china_arrival": "Ankunft LKW China",
                    "ship_arrival": "Ankunft Schiff",
                    "truck_de_arrival": "Ankunft LKW Deutschland"
                }[delay_stage]
                
                # Erstelle Options-Liste mit Format: "DD.MM.YYYY"
                date_options = {d.strftime(MasterData.DATE_FORMAT): d for d in planned_dates}
                default_date_str = planned_dates[0].strftime(MasterData.DATE_FORMAT) if planned_dates else date(planning_year, 7, 19).strftime(MasterData.DATE_FORMAT)
                
                selected_date_str = st.selectbox(
                    "Geplantes Ankunftsdatum",
                    options=list(date_options.keys()),
                    index=0 if default_date_str in date_options else 0,
                    help=f"Wählen Sie ein geplantes Ankunftsdatum für {stage_name}. Nur Daten mit tatsächlichen Ankünften werden angezeigt.",
                    key=f"delay_date_select_{delay_stage}_{key_suffix}"
                )
                delay_date = date_options[selected_date_str]
                
                # Zeige Info wenn keine Daten verfügbar
                if len(planned_dates) == 0:
                    st.info("⚠️ Keine geplanten Ankunftsdaten verfügbar. Bitte starten Sie zuerst die Simulation.")
            else:
                # Fallback: Freie Datumsauswahl wenn keine geplanten Daten verfügbar
                st.warning("⚠️ Keine geplanten Ankunftsdaten gefunden. Verwenden Sie freie Datumsauswahl.")
                delay_date = st.date_input(
                    "Datum (geplantes Ankunftsdatum)",
                    value=date(planning_year, 7, 19),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD.MM.YYYY",
                    help="⚠️ Wichtig: Das Datum muss einem geplanten Ankunftsdatum entsprechen, sonst wird die Verspätung nicht angewendet.",
                    key=f"delay_date_global{key_suffix}"
                )
            
            delay = st.number_input("Verspätung (Tage)", min_value=0, max_value=30, value=0, key=f"delay_days_global{key_suffix}")
            
            if st.button("➕ Verspätung hinzufügen", key=f"add_delay_global{key_suffix}"):
                # Berechne delay_day relativ zum Planungsjahr
                if delay_date.year == 2026:
                    delay_date_base = date(2026, 1, 1)
                    delay_day = (delay_date - delay_date_base).days
                    offset = (delay_date_base - start_of_year).days
                    delay_day = delay_day + offset
                else:
                    delay_day = (delay_date - start_of_year).days
                stage_name = {
                    "truck_china_arrival": "Ankunft LKW China",
                    "ship_arrival": "Ankunft Schiff",
                    "truck_de_arrival": "Ankunft LKW Deutschland"
                }[delay_stage]
                scenario = DelayScenario(
                    name=f"Verspätung {stage_name} ({delay_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=delay_day,
                    end_day=delay_day,  # Exaktes Datum: start_day = end_day
                    component_type="saddles",  # Immer Sättel
                    delay_days=delay,
                    delay_stage=delay_stage
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                _safe_rerun()
        
        elif scenario_type == "Ladungsverlust auf See":
            st.subheader("Ladungsverlust auf See")
            
            # PERFORMANCE: Hole geplante Ankunftsdaten für Schiffe (verwendet Cache)
            # Ladungsverlust bezieht sich immer auf Schiffe, daher verwenden wir "ship_arrival"
            planned_ship_arrival_dates = _get_planned_arrival_dates("ship_arrival", planning_year)
            
            if planned_ship_arrival_dates:
                # Zeige nur geplante Ankunftsdaten als Optionen
                # Erstelle Options-Liste mit Format: "DD.MM.YYYY"
                date_options = {d.strftime(MasterData.DATE_FORMAT): d for d in planned_ship_arrival_dates}
                default_date_str = planned_ship_arrival_dates[0].strftime(MasterData.DATE_FORMAT) if planned_ship_arrival_dates else date(planning_year, 8, 15).strftime(MasterData.DATE_FORMAT)
                
                selected_date_str = st.selectbox(
                    "Geplantes Ankunftsdatum des Schiffes",
                    options=list(date_options.keys()),
                    index=0 if default_date_str in date_options else 0,
                    help="Wählen Sie das geplante Ankunftsdatum des Schiffes, dessen Ladung verloren geht. Nur Daten mit tatsächlichen Schiffsankünften werden angezeigt.",
                    key=f"cargo_loss_date_select_{key_suffix}"
                )
                loss_date = date_options[selected_date_str]
            else:
                # Fallback: Freie Datumsauswahl wenn keine geplanten Daten verfügbar
                st.warning("⚠️ Keine geplanten Schiffsankunftsdaten gefunden. Verwenden Sie freie Datumsauswahl.")
                loss_date = st.date_input(
                    "Datum (geplantes Ankunftsdatum des Schiffes)",
                    value=date(planning_year, 8, 15),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD.MM.YYYY",
                    help="⚠️ Wichtig: Das Datum muss einem geplanten Ankunftsdatum eines Schiffes entsprechen, sonst wird der Ladungsverlust nicht angewendet.",
                    key=f"cargo_loss_date_global{key_suffix}"
                )
            
            if st.button("➕ Ladungsverlust hinzufügen", key=f"add_cargo_loss_global{key_suffix}"):
                # Berechne loss_day relativ zum Planungsjahr
                if loss_date.year == 2026:
                    loss_date_base = date(2026, 1, 1)
                    loss_day = (loss_date - loss_date_base).days
                    offset = (loss_date_base - start_of_year).days
                    loss_day = loss_day + offset
                else:
                    loss_day = (loss_date - start_of_year).days
                scenario = CargoLossScenario(
                    name=f"Ladungsverlust auf See ({loss_date.strftime(MasterData.DATE_FORMAT)})",
                    start_day=loss_day,
                    end_day=loss_day,  # Exaktes Datum: start_day = end_day
                    loss_date=loss_day,
                    component_type="saddles"
                )
                st.session_state.scenario_manager.add_scenario(scenario)
                st.success(f"Szenario hinzugefügt: {scenario.name}")
                _safe_rerun()
        
        st.divider()
        
        # Aktive Szenarien anzeigen (ohne Standard-Szenario)
        custom_scenarios = [
            s for s in st.session_state.scenario_manager.scenarios
            if not isinstance(s, StandardScenario)
        ]
        
        if custom_scenarios:
            st.subheader("📋 Aktive Szenarien")
            planning_year = st.session_state.get('planning_year', 2027)
            for i, scenario in enumerate(custom_scenarios):
                # Finde Index im ursprünglichen Array
                original_idx = st.session_state.scenario_manager.scenarios.index(scenario)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {scenario.name}")
                    details = _format_scenario_details(scenario, planning_year)
                    if details:
                        st.caption(details)
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
                        # 5. PERFORMANCE: Invalidiere Cache für geplante Ankunftsdaten
                        planning_year = st.session_state.get('planning_year', 2027)
                        for delay_stage in ["truck_china_arrival", "ship_arrival", "truck_de_arrival"]:
                            cache_key = f"planned_arrival_dates_{delay_stage}_{planning_year}"
                            if cache_key in st.session_state:
                                del st.session_state[cache_key]
                        _safe_rerun()
        else:
            st.caption("Keine zusätzlichen Szenarien aktiv")
        
        st.divider()
        
        # Hinweis: Simulation kann durch Neustart der Seite neu gestartet werden
        st.caption("💡 Tipp: Die Simulation kann durch Neustart der Seite neu gestartet werden.")

