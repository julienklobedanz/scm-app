"""
Inbound Logistik-Seite
Zeigt Ware, die das chinesische Festland verlassen hat und auf dem Weg zum Lager Dortmund ist
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Inbound Logistik", page_icon="🚢", layout="wide")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

st.title("🚢 Inbound Logistik")
st.markdown("Überwachung der Verschiffungen und Zuläufe zum Lager Dortmund.")

# Initialisiere Session State falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    from models.scenarios import ScenarioManager
    st.session_state.scenario_manager = ScenarioManager()
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'simulator' not in st.session_state:
    st.session_state.simulator = None
if 'happy_path_run' not in st.session_state:
    st.session_state.happy_path_run = False
if 'yearly_volume' not in st.session_state:
    st.session_state.yearly_volume = 370000

# Happy Path: Automatische Simulation wenn noch keine Ergebnisse vorhanden
if not st.session_state.happy_path_run and st.session_state.results_df is None:
    try:
        with st.spinner("🔄 Happy Path Simulation wird ausgeführt..."):
            from simulation.simulator import Simulator
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
            st.session_state.simulator = simulator
            st.session_state.happy_path_run = True
            st.rerun()
    except Exception as e:
        st.error(f"❌ Fehler bei der Simulation: {str(e)}")
        st.exception(e)
        st.session_state.happy_path_run = True

if 'simulator' not in st.session_state or st.session_state.simulator is None:
    st.warning("⚠️ Bitte führen Sie zuerst die Simulation auf dem Dashboard aus.")
else:
    manager = st.session_state.simulator.china_transport_manager
    workday_calc = manager.workday_calculator
    
    # 2. Gruppiere Verschiffungen nach ship_departure_day
    shipments_by_departure = {}  # {ship_departure_day: {data}}
    product_mix = MasterData.PRODUCT_SALES_SHARES.copy()
    
    # Sammle alle verschifften Pakete und gruppiere nach Verschiffungstag
    for (order_day, order_id), status in manager.transport_status.items():
        if status.get('shipped', False) and status.get('ship_departure_day') is not None:
            ship_dep_day = status['ship_departure_day']
            
            if ship_dep_day not in shipments_by_departure:
                ship_dep = workday_calc.get_date_from_day(status['ship_departure_day'])
                ship_arr = workday_calc.get_date_from_day(status['ship_arrival_day']) if status.get('ship_arrival_day') is not None else None
                truck_start = workday_calc.get_date_from_day(status['truck_de_start_day']) if status.get('truck_de_start_day') is not None else None
                phys_arr = workday_calc.get_date_from_day(status['physical_arrival_day']) if status.get('physical_arrival_day') is not None else None
                avail = workday_calc.get_date_from_day(status['available_day']) if status.get('available_day') is not None else None
                
                shipments_by_departure[ship_dep_day] = {
                    "Schiffsabfahrt (CN)": ship_dep,
                    "Schiffsankunft (HH)": ship_arr,
                    "LKW Start (DE)": truck_start,
                    "Ankunft Werk (Physisch)": phys_arr,
                    "Verfügbar (Lager)": avail,
                    "Menge Gesamt": 0,
                    "Status": "Unterwegs",
                    "saddle_quantities": {}
                }
            
            qty = status.get('shipped_quantity', status.get('quantity', 0))
            shipments_by_departure[ship_dep_day]["Menge Gesamt"] += qty
            
            if status.get('received', False):
                shipments_by_departure[ship_dep_day]["Status"] = "Verfügbar"
            
            # Aufschlüsselung nach Sattel-Typen (Proportional)
            for product, share in product_mix.items():
                saddle_name = MasterData.BOM[product]['saddle']
                col_name = f"{saddle_name} ({product})"
                if col_name not in shipments_by_departure[ship_dep_day]["saddle_quantities"]:
                    shipments_by_departure[ship_dep_day]["saddle_quantities"][col_name] = 0
                shipments_by_departure[ship_dep_day]["saddle_quantities"][col_name] += int(qty * share)
    
    # 3. Erstelle tägliche Zeilen (Beginn: 16.11.2026)
    start_date = date(2026, 11, 16)
    end_date = date(2027, 12, 31)
    total_days = (end_date - start_date).days + 1
    
    inbound_data = []
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        
        # Prüfe ob chinesischer Feiertag oder Wochenende
        weekday = current_date.weekday()
        is_weekend = weekday >= 5
        is_chinese_holiday = HolidaysConfig.is_holiday(current_date, 'CN')
        is_weekend_or_holiday = is_weekend or is_chinese_holiday
        
        # Finde Verschiffung, die an diesem Tag abfährt
        row = {
            "Datum": current_date,
            "Schiffsabfahrt (CN)": "",
            "Schiffsankunft (HH)": "",
            "LKW Start (DE)": "",
            "Ankunft Werk (Physisch)": "",
            "Verfügbar (Lager)": "",
            "Menge Gesamt": 0,
            "Is_Weekend_Or_Holiday": is_weekend_or_holiday
        }
        
        # Füge Sattel-Spalten hinzu (initialisiert mit 0) - nur Sattel-Name, ohne Produkt
        unique_saddles = set()
        for product in MasterData.BOM.values():
            unique_saddles.add(product['saddle'])
        for saddle_name in sorted(unique_saddles):
            row[saddle_name] = 0
        
        # Prüfe ob an diesem Tag eine Verschiffung stattfindet
        day = (current_date - date(2027, 1, 1)).days
        if day in shipments_by_departure:
            shipment = shipments_by_departure[day]
            row["Schiffsabfahrt (CN)"] = shipment["Schiffsabfahrt (CN)"].strftime('%d.%m.%Y') if shipment["Schiffsabfahrt (CN)"] else ""
            row["Schiffsankunft (HH)"] = shipment["Schiffsankunft (HH)"].strftime('%d.%m.%Y') if shipment["Schiffsankunft (HH)"] else ""
            row["LKW Start (DE)"] = shipment["LKW Start (DE)"].strftime('%d.%m.%Y') if shipment["LKW Start (DE)"] else ""
            row["Ankunft Werk (Physisch)"] = shipment["Ankunft Werk (Physisch)"].strftime('%d.%m.%Y') if shipment["Ankunft Werk (Physisch)"] else ""
            row["Verfügbar (Lager)"] = shipment["Verfügbar (Lager)"].strftime('%d.%m.%Y') if shipment["Verfügbar (Lager)"] else ""
            row["Menge Gesamt"] = int(shipment["Menge Gesamt"])
            # Füge Sattel-Aufschlüsselung hinzu - aggregiere nach Sattel-Name (ohne Produkt)
            for col_name, qty in shipment["saddle_quantities"].items():
                # Extrahiere Sattel-Name aus "Sattel_Name (Produkt)"
                saddle_name = col_name.split(' (')[0]
                if saddle_name in row:
                    row[saddle_name] += qty
        
        inbound_data.append(row)
    
    if inbound_data:
        df_inbound = pd.DataFrame(inbound_data)
        
        # Metriken (Nur für Ware, die noch unterwegs ist - Status-Spalte wurde entfernt)
        # Berechne total_on_water basierend auf Verschiffungen, die noch nicht verfügbar sind
        total_on_water = 0
        next_arrival = None
        for day_key, shipment in shipments_by_departure.items():
            if shipment["Status"] == "Unterwegs":
                total_on_water += shipment["Menge Gesamt"]
                if shipment["Schiffsankunft (HH)"] and (next_arrival is None or shipment["Schiffsankunft (HH)"] < next_arrival):
                    next_arrival = shipment["Schiffsankunft (HH)"]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Ware auf See / Unterwegs", f"{int(total_on_water):,} Stk")
        col2.metric("Nächste Schiffsankunft", str(next_arrival.strftime('%d.%m.%Y')) if next_arrival else "-")
        col3.metric("Anzahl Container unterwegs", f"{int(total_on_water / 500) if total_on_water > 0 else 0} Container")
        
        st.divider()
        
        # Tabelle anzeigen
        st.subheader("Detaillierte Lieferübersicht")
        
        # Spaltenreihenfolge: Datum zuerst
        display_columns = ["Datum", "Schiffsabfahrt (CN)", "Schiffsankunft (HH)", "LKW Start (DE)", 
                          "Ankunft Werk (Physisch)", "Verfügbar (Lager)", "Menge Gesamt"]
        # Füge Sattel-Spalten hinzu (nur eindeutige Sattel-Namen)
        unique_saddles = set()
        for product in MasterData.BOM.values():
            unique_saddles.add(product['saddle'])
        for saddle_name in sorted(unique_saddles):
            display_columns.append(saddle_name)
        
        df_display = df_inbound[display_columns].copy()
        
        # Konvertiere Datum zu String für Anzeige
        # Da 'Datum' ein date-Objekt ist, konvertieren wir es direkt zu String
        df_display['Datum'] = df_display['Datum'].apply(lambda x: x.strftime('%d.%m.%Y') if isinstance(x, date) else str(x))
        
        # Speichere Is_Weekend_Or_Holiday Flag
        weekend_holiday_flags = df_inbound['Is_Weekend_Or_Holiday'].values
        
        # Zeige Tabelle mit Styling
        styled_df = df_display.style.apply(
            lambda row: ['background-color: #ffebee' if weekend_holiday_flags[row.name] else '' for _ in row],
            axis=1
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Datum": st.column_config.TextColumn("Datum"),
                "Schiffsabfahrt (CN)": st.column_config.TextColumn("Abfahrt (CN)"),
                "Schiffsankunft (HH)": st.column_config.TextColumn("Ankunft (HH)"),
                "LKW Start (DE)": st.column_config.TextColumn("LKW Start"),
                "Ankunft Werk (Physisch)": st.column_config.TextColumn("Ankunft Tor"),
                "Verfügbar (Lager)": st.column_config.TextColumn("Verfügbar"),
                "Menge Gesamt": st.column_config.NumberColumn("Gesamtmenge", format="%d"),
            }
        )
    else:
        st.info("Noch keine Ware verschifft.")
