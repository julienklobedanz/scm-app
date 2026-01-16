"""
Volumenplanung-Seite
Wöchentliche und tägliche Volumenplanung
"""

import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig
from models.scenarios import ScenarioManager
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from ui.scenario_sidebar import render_scenario_sidebar

st.set_page_config(page_title="Volumenplanung", layout="wide", page_icon="📅")

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

# Initialisiere ScenarioManager falls nicht vorhanden
if 'scenario_manager' not in st.session_state:
    st.session_state.scenario_manager = ScenarioManager()

st.title("📅 Volumenplanung")
st.markdown("Wöchentliche und tägliche Volumenplanung basierend auf Saisonalität")

# Szenarien-Sidebar rendern
render_scenario_sidebar()

# Berechne Planung basierend auf jährlichem Volumen
yearly_volume = st.session_state.get('yearly_volume', 370000)
workday_calc = WorkdayCalculator(year=2027)
# Zwei separate DemandCalculator-Instanzen: eine für geplant, eine für tatsächlich
# (um Carry-Over-Logik nicht zu beeinflussen)
demand_calculator_planned = DemandCalculator(yearly_volume, workday_calc)
demand_calculator_actual = DemandCalculator(yearly_volume, workday_calc)

# Hilfsfunktionen
def get_week_number(d: date) -> int:
    """Berechnet ISO-Kalenderwoche"""
    return d.isocalendar()[1]

def calculate_shifts_from_demand(daily_target: float) -> int:
    """
    Berechnet benötigte Schichten basierend auf Nachfrage (dynamisch)
    
    Returns:
        Anzahl Schichten (1-3)
    """
    # Konstanten aus MasterData
    MIN_SHIFTS = 1
    MAX_SHIFTS = 3
    HOURS_PER_SHIFT = 8
    CAPACITY_PER_HOUR = MasterData.GLOBAL_CONFIG['capacity_per_hour']  # 130
    CAPACITY_PER_SHIFT = HOURS_PER_SHIFT * CAPACITY_PER_HOUR  # 1040
    
    if daily_target == 0:
        return 0
    
    # Required_Shifts_Float = Daily_Target / Capacity_Per_Shift
    required_shifts_float = daily_target / CAPACITY_PER_SHIFT
    
    # Required_Shifts_Int = ceil(Required_Shifts_Float)
    required_shifts_int = math.ceil(required_shifts_float)
    
    # Actual_Shifts = max(Min_Shifts, min(Max_Shifts, Required_Shifts_Int))
    actual_shifts = max(MIN_SHIFTS, min(MAX_SHIFTS, required_shifts_int))
    
    return actual_shifts

def calculate_product_demand(day: int, product: str, include_marketing: bool = True) -> float:
    """
    Berechnet Nachfrage für ein spezifisches Produkt an einem Tag (mit Carry-Over-Logik)
    
    Args:
        day: Tag (0-basiert)
        product: Produktname
        include_marketing: Wenn True, berücksichtigt Marketing-Szenarien
    """
    # Finde letzten Arbeitstag des Jahres (für korrekte Rest-Aufsummierung)
    last_workday_of_year = None
    for d in range(364, -1, -1):
        if workday_calc.is_workday(d):
            last_workday_of_year = d
            break
    is_last_workday = (day == last_workday_of_year)
    
    if include_marketing:
        # Verwende demand_calculator_actual für tatsächliche Nachfrage
        calculator = demand_calculator_actual
        
        # Berechne Marketing-Add-ons (wie im Simulator)
        marketing_add_ons = {}
        scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
        marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
        
        if marketing_scenarios:
            month = MasterData.get_month_from_day(day)
            is_workday = workday_calc.is_workday(day)
            
            if is_workday:
                # Hole Base_Daily_Float für Add-on-Berechnung
                base_daily_floats = calculator._calculate_monthly_base_daily_float(month)
                
                for scenario in marketing_scenarios:
                    factor = scenario.demand_increase_factor
                    base_float = base_daily_floats.get(product, 0.0)
                    # Marketing-Add-on = zusätzliche Nachfrage durch Marketing
                    add_on = base_float * (factor - 1.0)
                    if product not in marketing_add_ons:
                        marketing_add_ons[product] = 0.0
                    marketing_add_ons[product] += add_on
        
        # Berechne Nachfrage mit Marketing
        # WICHTIG: Am letzten Arbeitstag müssen Reste aufsummiert werden
        product_demands = calculator.calculate_daily_demand_per_product_dict(
            day, marketing_add_ons, is_last_workday_of_year=is_last_workday
        )
    else:
        # Verwende demand_calculator_planned für geplante Nachfrage (ohne Marketing)
        calculator = demand_calculator_planned
        # WICHTIG: Am letzten Arbeitstag müssen Reste aufsummiert werden
        product_demands = calculator.calculate_daily_demand_per_product_dict(
            day, {}, is_last_workday_of_year=is_last_workday
        )
    
    return float(product_demands.get(product, 0))

# Tabs für wöchentlich und täglich
tab1, tab2 = st.tabs(["📊 Wöchentliche Planung", "📋 Tägliche Planung"])

with tab1:
    st.header("Wöchentliche Volumenplanung")
    
    # Erstelle wöchentliche Planung
    start_date = date(2027, 1, 1)
    end_date = date(2027, 12, 31)
    
    # KRITISCH: Berechne Nachfrage für ALLE Tage sequenziell (für korrekte Carry-Over-Logik)
    # Die DemandCalculator-Instanzen haben einen Zustand (product_remainders), der sequenziell aktualisiert werden muss
    # WICHTIG: Berechne für alle Produkte gleichzeitig, damit der Rest korrekt weitergegeben wird
    # WICHTIG: Verwende bereits berechnete Daten aus Session State, falls vorhanden
    from ui.volume_planning_utils import calculate_volume_planning_demand
    
    if st.session_state.get('volume_planning_calculated', False):
        # Verwende bereits berechnete Daten
        daily_demands_planned = st.session_state.get('daily_demands_planned', {})
        daily_demands_actual = st.session_state.get('daily_demands_actual', {})
    else:
        # Berechne neu (sollte normalerweise nicht passieren, da calculate_volume_planning_demand beim Start aufgerufen wird)
        daily_demands_planned, daily_demands_actual = calculate_volume_planning_demand()
    
    # Falls Daten noch nicht vollständig sind, berechne sie
    if not daily_demands_planned or not daily_demands_actual:
        daily_demands_planned, daily_demands_actual = calculate_volume_planning_demand()
    
    # Finde letzten Arbeitstag des Jahres (für korrekte Rest-Aufsummierung)
    last_workday_of_year = None
    for day in range(364, -1, -1):
        if workday_calc.is_workday(day):
            last_workday_of_year = day
            break
    
    # Berechne Nachfrage für alle 365 Tage sequenziell (nur wenn nicht bereits vorhanden)
    if not daily_demands_planned or len(daily_demands_planned) < 365:
        daily_demands_planned = {}  # day -> {product -> demand}
        daily_demands_actual = {}   # day -> {product -> demand}
        
        for day in range(365):
            daily_demands_planned[day] = {}
            daily_demands_actual[day] = {}
        
        is_workday = workday_calc.is_workday(day)
        is_last_workday = (day == last_workday_of_year)
        
        if is_workday:
            # Berechne Marketing-Add-ons (wenn vorhanden)
            marketing_add_ons = {}
            scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
            marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
            
            if marketing_scenarios:
                month = MasterData.get_month_from_day(day)
                base_daily_floats = demand_calculator_actual._calculate_monthly_base_daily_float(month)
                
                for scenario in marketing_scenarios:
                    factor = scenario.demand_increase_factor
                    for product in MasterData.BOM.keys():
                        base_float = base_daily_floats.get(product, 0.0)
                        add_on = base_float * (factor - 1.0)
                        if product not in marketing_add_ons:
                            marketing_add_ons[product] = 0.0
                        marketing_add_ons[product] += add_on
            
            # Berechne Nachfrage für alle Produkte gleichzeitig (wichtig für korrekte Carry-Over-Logik)
            # WICHTIG: Am letzten Arbeitstag müssen Reste aufsummiert werden
            # Geplante Nachfrage (ohne Marketing)
            planned_demands = demand_calculator_planned.calculate_daily_demand_per_product_dict(
                day, {}, is_last_workday_of_year=is_last_workday
            )
            # Tatsächliche Nachfrage (mit Marketing)
            actual_demands = demand_calculator_actual.calculate_daily_demand_per_product_dict(
                day, marketing_add_ons, is_last_workday_of_year=is_last_workday
            )
            
            for product in MasterData.BOM.keys():
                daily_demands_planned[day][product] = planned_demands.get(product, 0)
                daily_demands_actual[day][product] = actual_demands.get(product, 0)
        else:
            # An Feiertagen/Wochenenden: Alle Nachfragen sind 0
            for product in MasterData.BOM.keys():
                daily_demands_planned[day][product] = 0
                daily_demands_actual[day][product] = 0
    
    # WICHTIG: Speichere Nachfrage im Session State für Simulator
    # Der Simulator verwendet diese Daten als Basis, anstatt sie parallel zu berechnen
    st.session_state.daily_demands_actual = daily_demands_actual
    st.session_state.daily_demands_planned = daily_demands_planned
    
    # Berechne letzte Kalenderwoche des Jahres
    last_week = get_week_number(end_date)
    
    weekly_data = []
    
    for week_num in range(1, last_week + 1):  # Alle Wochen des Jahres
        # Finde ersten Tag der Woche (ISO-Woche)
        # ISO-Woche 1 beginnt am ersten Montag des Jahres oder früher
        jan_1 = date(2027, 1, 1)
        jan_1_weekday = jan_1.weekday()  # 0=Montag, 6=Sonntag
        
        # Berechne Start der ersten ISO-Woche
        if jan_1_weekday <= 3:  # Mo-Do: Woche beginnt am Montag dieser Woche
            first_monday = jan_1 - timedelta(days=jan_1_weekday)
        else:  # Fr-So: Woche beginnt am nächsten Montag
            first_monday = jan_1 + timedelta(days=7 - jan_1_weekday)
        
        # Start der gewünschten Woche
        week_start = first_monday + timedelta(weeks=week_num - 1)
        
        # Aggregiere Nachfrage für alle Tage der Woche (aus bereits berechneten Daten)
        # WICHTIG: Nutze die sequenziell berechneten Nachfragen (für korrekte Carry-Over-Logik)
        week_demand_planned = {}
        week_demand_actual = {}
        total_week_demand_planned = 0.0
        total_week_demand_actual = 0.0
        daily_demands = []  # Für Kapazitätsberechnung (verwende tatsächliche Nachfrage)
        
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            # Nur Tage im Jahr 2027 berücksichtigen
            if current_date.year == 2027:
                day_of_year = (current_date - start_date).days
                if 0 <= day_of_year < 365:
                    # Nutze bereits berechnete Nachfragen (sequenziell berechnet)
                    day_planned = daily_demands_planned.get(day_of_year, {})
                    day_actual = daily_demands_actual.get(day_of_year, {})
                    
                    day_total_planned = 0.0
                    day_total_actual = 0.0
                    
                    for product in MasterData.BOM.keys():
                        planned_demand = day_planned.get(product, 0)
                        actual_demand = day_actual.get(product, 0)
                        
                        if product not in week_demand_planned:
                            week_demand_planned[product] = 0.0
                        if product not in week_demand_actual:
                            week_demand_actual[product] = 0.0
                        
                        week_demand_planned[product] += planned_demand
                        week_demand_actual[product] += actual_demand
                        day_total_planned += planned_demand
                        day_total_actual += actual_demand
                    
                    total_week_demand_planned += day_total_planned
                    total_week_demand_actual += day_total_actual
                    
                    # Nur Arbeitstage für Kapazitätsberechnung (verwende tatsächliche Nachfrage)
                    if workday_calc.is_workday(day_of_year):
                        daily_demands.append(day_total_actual)
        
        # Berechne Schichten (exakt wie Excel-Formel)
        # Konstanten
        HOURS_PER_SHIFT = 8
        CAPACITY_PER_HOUR = MasterData.GLOBAL_CONFIG['capacity_per_hour']  # 130
        PRODUCTION_LINES = 1  # Anzahl Montagelinien (Basisdaten!$E$10)
        CAPACITY_PER_SHIFT = HOURS_PER_SHIFT * CAPACITY_PER_HOUR * PRODUCTION_LINES  # 1040
        MIN_SHIFTS = 1
        MAX_SHIFTS = 3
        
        # Anzahl Arbeitstage in dieser Woche (H105 in Excel)
        num_workdays = len(daily_demands)
        
        # Excel-Formel: AUFRUNDEN(N8/H105/(Basisdaten!$E$9*Basisdaten!$E$13*Basisdaten!$E$10);0)
        # N8 = Gesamtvolumen der Woche (total_week_demand_actual)
        # H105 = Anzahl Arbeitstage (num_workdays)
        # Basisdaten!$E$9 = CAPACITY_PER_HOUR (130)
        # Basisdaten!$E$13 = HOURS_PER_SHIFT (8)
        # Basisdaten!$E$10 = PRODUCTION_LINES (1)
        
        # Szenario A: Wenn Volumen = 0, dann Min. Schichten (1)
        if total_week_demand_actual == 0:
            actual_shifts = MIN_SHIFTS
        elif num_workdays == 0:
            # Fallback: Wenn keine Arbeitstage, dann Min. Schichten
            actual_shifts = MIN_SHIFTS
        else:
            # Berechne täglichen Bedarf: Gesamtvolumen / Anzahl Arbeitstage
            daily_demand = total_week_demand_actual / num_workdays
            
            # Berechne benötigte Schichten: täglicher Bedarf / Kapazität pro Schicht
            # AUFRUNDEN(daily_demand / CAPACITY_PER_SHIFT; 0)
            required_shifts_float = daily_demand / CAPACITY_PER_SHIFT
            required_shifts_int = math.ceil(required_shifts_float)
            
            # WENN-Formel: max(Min, min(Max, berechneter_Wert))
            # Szenario B: Wenn berechneter Wert < Min: Min. Schichten
            # Szenario C: Wenn berechneter Wert > Max: Max. Schichten
            # Szenario D: Normalfall (zwischen Min und Max)
            actual_shifts = max(MIN_SHIFTS, min(MAX_SHIFTS, required_shifts_int))
        
        # Erstelle Basis-Row
        row = {
            'Kalenderwoche': week_num,
            'Schichten': actual_shifts  # Für Visualisierung
        }
        
        # Füge für jedes Produkt geplant und tatsächlich hinzu
        for product in MasterData.BOM.keys():
            row[f'{product}_geplant'] = round(week_demand_planned.get(product, 0))
            row[f'{product}_tatsächlich'] = round(week_demand_actual.get(product, 0))
        
        row['Gesamt_geplant'] = round(total_week_demand_planned)
        row['Gesamt_tatsächlich'] = round(total_week_demand_actual)
        
        weekly_data.append(row)
    
    weekly_df = pd.DataFrame(weekly_data)
    
    # Erstelle Multi-Index Spalten
    # Basis-Spalten
    base_columns = [
        ('', 'Kalenderwoche'),
        ('', 'Schichten')
    ]
    
    # Produkt-Spalten mit Multi-Index
    for product in MasterData.BOM.keys():
        base_columns.append((product, 'Geplanter Bedarf'))
        base_columns.append((product, 'Tatsächlicher Bedarf'))
    
    # Gesamt-Spalten
    base_columns.append(('Gesamt', 'Geplanter Bedarf'))
    base_columns.append(('Gesamt', 'Tatsächlicher Bedarf'))
    
    # Erstelle MultiIndex
    multi_index = pd.MultiIndex.from_tuples(base_columns)
    
    # Erstelle neues DataFrame mit Multi-Index Spalten
    data_dict = {}
    data_dict[('', 'Kalenderwoche')] = weekly_df['Kalenderwoche']
    data_dict[('', 'Schichten')] = weekly_df['Schichten']
    
    for product in MasterData.BOM.keys():
        data_dict[(product, 'Geplanter Bedarf')] = weekly_df[f'{product}_geplant']
        data_dict[(product, 'Tatsächlicher Bedarf')] = weekly_df[f'{product}_tatsächlich']
    
    data_dict[('Gesamt', 'Geplanter Bedarf')] = weekly_df['Gesamt_geplant']
    data_dict[('Gesamt', 'Tatsächlicher Bedarf')] = weekly_df['Gesamt_tatsächlich']
    
    display_weekly_df = pd.DataFrame(data_dict, columns=multi_index)
    
    # Berechne Summenzeile
    sum_row = {}
    sum_row[('', 'Kalenderwoche')] = 'Summe'
    sum_row[('', 'Schichten')] = ''
    
    for product in MasterData.BOM.keys():
        sum_row[(product, 'Geplanter Bedarf')] = display_weekly_df[(product, 'Geplanter Bedarf')].sum()
        sum_row[(product, 'Tatsächlicher Bedarf')] = display_weekly_df[(product, 'Tatsächlicher Bedarf')].sum()
    
    sum_row[('Gesamt', 'Geplanter Bedarf')] = display_weekly_df[('Gesamt', 'Geplanter Bedarf')].sum()
    sum_row[('Gesamt', 'Tatsächlicher Bedarf')] = display_weekly_df[('Gesamt', 'Tatsächlicher Bedarf')].sum()
    
    # Füge Summenzeile hinzu
    sum_df = pd.DataFrame([sum_row], columns=multi_index)
    display_weekly_df_with_sum = pd.concat([display_weekly_df, sum_df], ignore_index=True)
    
    # Styling für Summenzeile
    def style_weekly_row(row):
        """Styling-Funktion für wöchentliche Tabelle"""
        row_idx = row.name
        if row_idx < len(display_weekly_df):
            # Normale Zeile: kein spezielles Styling
            return [''] * len(row)
        else:
            # Summenzeile: Fett markieren
            return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
    
    styled_weekly_df = display_weekly_df_with_sum.style.apply(style_weekly_row, axis=1)
    
    # Zeige Tabelle
    st.dataframe(styled_weekly_df, width='stretch', hide_index=True)
    
    # Visualisierung der Schichten
    st.subheader("Schichten-Visualisierung")
    fig_shifts = go.Figure()
    
    fig_shifts.add_trace(go.Bar(
        x=weekly_df['Kalenderwoche'],
        y=weekly_df['Schichten'],
        name='Schichten',
        marker_color='#1f77b4',
        text=weekly_df['Schichten'],
        textposition='auto'
    ))
    
    fig_shifts.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Anzahl Schichten",
        height=300,
        yaxis=dict(range=[0, 4], tickmode='linear', tick0=0, dtick=1)
    )
    st.plotly_chart(fig_shifts, width='stretch')
    
    # Vergleich aller Fahrräder über die Kalenderwochen
    st.subheader("Fahrrad-Vergleich über Kalenderwochen")
    fig_products = go.Figure()
    
    # Farben für die verschiedenen Produkte
    product_colors = {
        'MTB Allrounder': '#1f77b4',
        'MTB Competition': '#ff7f0e',
        'MTB Downhill': '#2ca02c',
        'MTB Extreme': '#d62728',
        'MTB Freeride': '#9467bd',
        'MTB Marathon': '#8c564b',
        'MTB Performance': '#e377c2',
        'MTB Trail': '#7f7f7f'
    }
    
    # Füge für jedes Produkt eine Linie hinzu (tatsächlicher Bedarf)
    for product in MasterData.BOM.keys():
        fig_products.add_trace(go.Scatter(
            x=weekly_df['Kalenderwoche'],
            y=weekly_df[f'{product}_tatsächlich'],
            name=product,
            mode='lines+markers',
            line=dict(color=product_colors.get(product, '#1f77b4'), width=2),
            marker=dict(size=4)
        ))
    
    fig_products.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Nachfrage (Einheiten)",
        height=400,
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    st.plotly_chart(fig_products, width='stretch')
    
    # Zusätzlich: Stacked Bar Chart für besseren Vergleich
    st.subheader("Fahrrad-Vergleich (Gestapelt)")
    fig_stacked = go.Figure()
    
    # Erstelle gestapeltes Balkendiagramm (tatsächlicher Bedarf)
    for product in MasterData.BOM.keys():
        fig_stacked.add_trace(go.Bar(
            x=weekly_df['Kalenderwoche'],
            y=weekly_df[f'{product}_tatsächlich'],
            name=product,
            marker_color=product_colors.get(product, '#1f77b4')
        ))
    
    fig_stacked.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Nachfrage (Einheiten)",
        height=400,
        barmode='stack',
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    st.plotly_chart(fig_stacked, width='stretch')

with tab2:
    st.header("Tägliche Volumenplanung")
    
    # KRITISCH: Berechne Nachfrage für ALLE Tage sequenziell (für korrekte Carry-Over-Logik)
    # Die tägliche Planung muss die gleiche sequenzielle Berechnung wie die wöchentliche verwenden
    # WICHTIG: Nutze session_state, um zu prüfen, ob bereits berechnet wurde (Tabs werden separat ausgeführt)
    if 'daily_demands_planned_tab2' not in st.session_state:
        # Berechne Nachfrage für alle 365 Tage sequenziell (wie in wöchentlicher Planung)
        daily_demands_planned_tab2 = {}  # day -> {product -> demand}
        daily_demands_actual_tab2 = {}   # day -> {product -> demand}
        
        # Finde letzten Arbeitstag des Jahres (für korrekte Rest-Aufsummierung)
        last_workday_of_year_tab2 = None
        for day in range(364, -1, -1):
            if workday_calc.is_workday(day):
                last_workday_of_year_tab2 = day
                break
        
        # Erstelle separate DemandCalculator-Instanzen für tägliche Planung
        demand_calculator_planned_tab2 = DemandCalculator(yearly_volume, workday_calc)
        demand_calculator_actual_tab2 = DemandCalculator(yearly_volume, workday_calc)
        
        # Berechne Nachfrage für alle 365 Tage sequenziell
        for day in range(365):
            daily_demands_planned_tab2[day] = {}
            daily_demands_actual_tab2[day] = {}
            
            is_workday = workday_calc.is_workday(day)
            is_last_workday = (day == last_workday_of_year_tab2)
            
            if is_workday:
                # Berechne Marketing-Add-ons (wenn vorhanden)
                marketing_add_ons = {}
                scenario_manager = st.session_state.get('scenario_manager', ScenarioManager())
                marketing_scenarios = scenario_manager.get_marketing_scenarios(day)
                
                if marketing_scenarios:
                    month = MasterData.get_month_from_day(day)
                    base_daily_floats = demand_calculator_actual_tab2._calculate_monthly_base_daily_float(month)
                    
                    for scenario in marketing_scenarios:
                        factor = scenario.demand_increase_factor
                        for product in MasterData.BOM.keys():
                            base_float = base_daily_floats.get(product, 0.0)
                            add_on = base_float * (factor - 1.0)
                            if product not in marketing_add_ons:
                                marketing_add_ons[product] = 0.0
                            marketing_add_ons[product] += add_on
                
                # Berechne Nachfrage für alle Produkte gleichzeitig (wichtig für korrekte Carry-Over-Logik)
                # WICHTIG: Am letzten Arbeitstag müssen Reste aufsummiert werden
                # Geplante Nachfrage (ohne Marketing)
                planned_demands = demand_calculator_planned_tab2.calculate_daily_demand_per_product_dict(
                    day, {}, is_last_workday_of_year=is_last_workday
                )
                # Tatsächliche Nachfrage (mit Marketing)
                actual_demands = demand_calculator_actual_tab2.calculate_daily_demand_per_product_dict(
                    day, marketing_add_ons, is_last_workday_of_year=is_last_workday
                )
                
                for product in MasterData.BOM.keys():
                    daily_demands_planned_tab2[day][product] = planned_demands.get(product, 0)
                    daily_demands_actual_tab2[day][product] = actual_demands.get(product, 0)
            else:
                # An Feiertagen/Wochenenden: Alle Nachfragen sind 0
                for product in MasterData.BOM.keys():
                    daily_demands_planned_tab2[day][product] = 0
                    daily_demands_actual_tab2[day][product] = 0
        
        # Speichere in session_state für Wiederverwendung
        st.session_state.daily_demands_planned_tab2 = daily_demands_planned_tab2
        st.session_state.daily_demands_actual_tab2 = daily_demands_actual_tab2
    else:
        # Nutze bereits berechnete Daten aus session_state
        daily_demands_planned_tab2 = st.session_state.daily_demands_planned_tab2
        daily_demands_actual_tab2 = st.session_state.daily_demands_actual_tab2
    
    # Filter-Optionen mit Datum
    col1, col2 = st.columns(2)
    with col1:
        start_date_filter = st.date_input(
            "Start-Datum",
            value=date(2027, 1, 1),
            min_value=date(2027, 1, 1),
            max_value=date(2027, 12, 31),
            key="daily_start_date"
        )
    with col2:
        end_date_filter = st.date_input(
            "End-Datum",
            value=date(2027, 12, 31),
            min_value=date(2027, 1, 1),
            max_value=date(2027, 12, 31),
            key="daily_end_date"
        )
    
    # Konvertiere Datum zu Tag
    start_day = (start_date_filter - date(2027, 1, 1)).days
    end_day = (end_date_filter - date(2027, 1, 1)).days
    
    # Erstelle tägliche Planung
    daily_data = []
    start_date = date(2027, 1, 1)
    
    # WICHTIG: Nutze die bereits sequenziell berechneten Nachfragen (für korrekte Carry-Over-Logik)
    for day in range(start_day, min(end_day + 1, 365)):
        current_date = start_date + timedelta(days=day)
        week_num = get_week_number(current_date)
        
        # Prüfe ob Feiertag oder Wochenende
        is_workday = workday_calc.is_workday(day)
        is_holiday = HolidaysConfig.is_holiday(current_date, 'DE')
        is_weekend = current_date.weekday() >= 5  # Samstag=5, Sonntag=6
        is_non_workday = not is_workday or is_holiday or is_weekend
        
        # Nutze bereits berechnete Nachfragen (sequenziell berechnet)
        day_planned = daily_demands_planned_tab2.get(day, {})
        day_actual = daily_demands_actual_tab2.get(day, {})
        
        product_demands_planned = {}
        product_demands_actual = {}
        total_demand_planned = 0.0
        total_demand_actual = 0.0
        
        for product in MasterData.BOM.keys():
            planned_demand = day_planned.get(product, 0)
            actual_demand = day_actual.get(product, 0)
            
            product_demands_planned[product] = planned_demand
            product_demands_actual[product] = actual_demand
            total_demand_planned += planned_demand
            total_demand_actual += actual_demand
        
        # Erstelle Basis-Row
        row = {
            'Datum': current_date.strftime(MasterData.DATE_FORMAT),
            'Kalenderwoche': week_num,
            '_is_non_workday': is_non_workday  # Für Styling
        }
        
        # Füge für jedes Produkt geplant und tatsächlich hinzu
        for product in MasterData.BOM.keys():
            row[f'{product}_geplant'] = round(product_demands_planned.get(product, 0))
            row[f'{product}_tatsächlich'] = round(product_demands_actual.get(product, 0))
        
        row['Gesamt_geplant'] = round(total_demand_planned)
        row['Gesamt_tatsächlich'] = round(total_demand_actual)
        
        daily_data.append(row)
    
    daily_df = pd.DataFrame(daily_data)
    
    # Speichere Nachfrage-Daten in session_state für andere Seiten (z.B. Lieferant China)
    # WICHTIG: Nutze die bereits sequenziell berechneten Daten (für korrekte Carry-Over-Logik)
    if 'daily_demand_data' not in st.session_state:
        st.session_state.daily_demand_data = {}
    
    # Speichere Nachfrage für alle Tage des Jahres (nutze bereits berechnete Daten)
    for day in range(365):
        if day not in st.session_state.daily_demand_data:
            # Nutze die bereits sequenziell berechneten Daten
            product_demands_actual = daily_demands_actual_tab2.get(day, {})
            st.session_state.daily_demand_data[day] = product_demands_actual
    
    # Erstelle Multi-Index Spalten
    # Basis-Spalten
    base_columns = [('', 'Datum'), ('', 'Kalenderwoche')]
    
    # Produkt-Spalten mit Multi-Index
    for product in MasterData.BOM.keys():
        base_columns.append((product, 'Geplanter Bedarf'))
        base_columns.append((product, 'Tatsächlicher Bedarf'))
    
    # Gesamt-Spalten
    base_columns.append(('Gesamt', 'Geplanter Bedarf'))
    base_columns.append(('Gesamt', 'Tatsächlicher Bedarf'))
    
    # Erstelle MultiIndex
    multi_index = pd.MultiIndex.from_tuples(base_columns)
    
    # Erstelle neues DataFrame mit Multi-Index Spalten
    data_dict = {}
    data_dict[('', 'Datum')] = daily_df['Datum']
    data_dict[('', 'Kalenderwoche')] = daily_df['Kalenderwoche']
    
    for product in MasterData.BOM.keys():
        data_dict[(product, 'Geplanter Bedarf')] = daily_df[f'{product}_geplant']
        data_dict[(product, 'Tatsächlicher Bedarf')] = daily_df[f'{product}_tatsächlich']
    
    data_dict[('Gesamt', 'Geplanter Bedarf')] = daily_df['Gesamt_geplant']
    data_dict[('Gesamt', 'Tatsächlicher Bedarf')] = daily_df['Gesamt_tatsächlich']
    
    display_df = pd.DataFrame(data_dict, columns=multi_index)
    
    # Berechne Summenzeile
    sum_row = {}
    sum_row[('', 'Datum')] = 'Summe'
    sum_row[('', 'Kalenderwoche')] = ''
    
    for product in MasterData.BOM.keys():
        sum_row[(product, 'Geplanter Bedarf')] = display_df[(product, 'Geplanter Bedarf')].sum()
        sum_row[(product, 'Tatsächlicher Bedarf')] = display_df[(product, 'Tatsächlicher Bedarf')].sum()
    
    sum_row[('Gesamt', 'Geplanter Bedarf')] = display_df[('Gesamt', 'Geplanter Bedarf')].sum()
    sum_row[('Gesamt', 'Tatsächlicher Bedarf')] = display_df[('Gesamt', 'Tatsächlicher Bedarf')].sum()
    
    # Füge Summenzeile hinzu
    sum_df = pd.DataFrame([sum_row], columns=multi_index)
    display_df_with_sum = pd.concat([display_df, sum_df], ignore_index=True)
    
    # Erweitere daily_df um eine Dummy-Zeile für die Summenzeile
    daily_df_with_sum = daily_df.copy()
    dummy_row = daily_df.iloc[0].copy()
    dummy_row['_is_non_workday'] = False
    daily_df_with_sum = pd.concat([daily_df_with_sum, pd.DataFrame([dummy_row])], ignore_index=True)
    
    # Wende Styling an (rote Markierung für Wochenenden/Feiertage)
    def style_row_with_sum(row):
        """Styling-Funktion die auch die Summenzeile berücksichtigt"""
        row_idx = row.name
        if row_idx < len(daily_df):
            # Normale Zeile: Prüfe ob Feiertag/Wochenende
            is_non_workday = daily_df.iloc[row_idx]['_is_non_workday']
            return ['background-color: #ffcccc' if is_non_workday else '' for _ in row]
        else:
            # Summenzeile: Fett markieren
            return ['background-color: #e0e0e0; font-weight: bold' for _ in row]
    
    styled_df = display_df_with_sum.style.apply(style_row_with_sum, axis=1)
    st.dataframe(styled_df, width='stretch', hide_index=True)
    
    # Visualisierung: Gestapeltes Balkendiagramm (tatsächlicher Bedarf)
    st.subheader("Tägliche Entwicklung (Tatsächlicher Bedarf)")
    
    # Farben für die verschiedenen Produkte (gleiche wie in wöchentlicher Planung)
    product_colors = {
        'MTB Allrounder': '#1f77b4',
        'MTB Competition': '#ff7f0e',
        'MTB Downhill': '#2ca02c',
        'MTB Extreme': '#d62728',
        'MTB Freeride': '#9467bd',
        'MTB Marathon': '#8c564b',
        'MTB Performance': '#e377c2',
        'MTB Trail': '#7f7f7f'
    }
    
    fig_daily = go.Figure()
    
    # Konvertiere Datum-Strings zu Datetime für x-Achse
    x_axis = pd.to_datetime(daily_df['Datum'], format='%d.%m.%Y')
    
    # Füge für jedes Produkt einen gestapelten Balken hinzu (tatsächlicher Bedarf)
    for product in MasterData.BOM.keys():
        fig_daily.add_trace(go.Bar(
            x=x_axis,
            y=daily_df[f'{product}_tatsächlich'],
            name=product,
            marker_color=product_colors.get(product, '#1f77b4')
        ))
    
    fig_daily.update_layout(
        xaxis_title="Datum",
        yaxis_title="Volumen (Einheiten)",
        height=400,
        barmode='stack',  # Gestapeltes Balkendiagramm
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    st.plotly_chart(fig_daily, width='stretch')
    
    # Statistiken
    st.subheader("Statistiken")
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        st.metric("Durchschn. geplant", f"{daily_df['Gesamt_geplant'].mean():.0f}")
    with col2:
        st.metric("Gesamt geplant", f"{daily_df['Gesamt_geplant'].sum():,.0f}")
    with col3:
        st.metric("Max geplant", f"{daily_df['Gesamt_geplant'].max():,.0f}")
    with col4:
        st.metric("Min geplant", f"{daily_df['Gesamt_geplant'].min():,.0f}")
    with col5:
        st.metric("Durchschn. tatsächlich", f"{daily_df['Gesamt_tatsächlich'].mean():.0f}")
    with col6:
        st.metric("Gesamt tatsächlich", f"{daily_df['Gesamt_tatsächlich'].sum():,.0f}")
    with col7:
        st.metric("Max tatsächlich", f"{daily_df['Gesamt_tatsächlich'].max():,.0f}")
    with col8:
        st.metric("Min tatsächlich", f"{daily_df['Gesamt_tatsächlich'].min():,.0f}")
