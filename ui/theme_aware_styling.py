"""
Theme-Aware Styling Utilities
Hilfsfunktionen für Styling die das aktuelle Theme berücksichtigen
"""

import streamlit as st
import pandas as pd


def get_theme_colors():
    """
    Gibt die Farben für das aktuelle Theme zurück.
    
    Returns:
        dict: Dictionary mit Farben für Header, Body, Summenzeile, etc.
    """
    current_theme = st.session_state.get('theme', 'dark')
    
    if current_theme == 'light':
        return {
            'header_bg': '#f0f2f6',
            'header_text': '#262730',
            'row_bg_even': '#ffffff',
            'row_bg_odd': '#f9fafb',
            'row_text': '#262730',
            'sum_row_bg': '#e5e7eb',
            'sum_row_text': '#262730',
            'weekend_bg': '#fee2e2',  # Hellrot für Wochenende im Light Mode
            'weekend_text': '#991b1b',
            'holiday_bg': '#d1fae5',  # Hellgrün für Feiertag im Light Mode
            'holiday_text': '#065f46',
            'border': '#e5e7eb'
        }
    else:
        # Dark Mode
        return {
            'header_bg': '#262730',
            'header_text': '#fafafa',
            'row_bg_even': '#0e1117',
            'row_bg_odd': '#262730',
            'row_text': '#fafafa',
            'sum_row_bg': '#404040',
            'sum_row_text': '#fafafa',
            'weekend_bg': '#4a2525',  # Dunkelrot für Wochenende
            'weekend_text': '#fafafa',
            'holiday_bg': '#1e3d2a',  # Dunkelgrün für Feiertag
            'holiday_text': '#fafafa',
            'border': '#404040'
        }


def style_row_with_theme(row, weekend_flags=None, holiday_flags=None, is_sum_row=False, row_index=None):
    """
    Styling-Funktion für Tabellen-Zeilen die das aktuelle Theme berücksichtigt.
    
    Args:
        row: pandas Series (Zeile)
        weekend_flags: Liste von bools für Wochenende (optional)
        holiday_flags: Liste von bools für Feiertage (optional)
        is_sum_row: True wenn es eine Summenzeile ist
        row_index: Index der Zeile (optional, wird aus row.name genommen wenn nicht gesetzt)
    
    Returns:
        Liste von CSS-Styles für jede Zelle
    """
    colors = get_theme_colors()
    
    if row_index is None:
        row_index = row.name
    
    # Summenzeile
    if is_sum_row:
        return [f'background-color: {colors["sum_row_bg"]}; color: {colors["sum_row_text"]}; font-weight: bold' for _ in row]
    
    # Wochenende (hat Priorität)
    # KRITISCH: Prüfe ob weekend_flags nicht None ist und ob es ein Array/Liste ist
    if weekend_flags is not None and len(weekend_flags) > 0 and row_index < len(weekend_flags):
        # Prüfe den Wert an der Position row_index (funktioniert für numpy arrays und Listen)
        try:
            if bool(weekend_flags[row_index]):
                return [f'background-color: {colors["weekend_bg"]}; color: {colors["weekend_text"]}' for _ in row]
        except (IndexError, TypeError):
            pass  # Fallback zu normaler Zeile
    
    # Feiertag
    # KRITISCH: Prüfe ob holiday_flags nicht None ist und ob es ein Array/Liste ist
    if holiday_flags is not None and len(holiday_flags) > 0 and row_index < len(holiday_flags):
        # Prüfe den Wert an der Position row_index (funktioniert für numpy arrays und Listen)
        try:
            if bool(holiday_flags[row_index]):
                return [f'background-color: {colors["holiday_bg"]}; color: {colors["holiday_text"]}' for _ in row]
        except (IndexError, TypeError):
            pass  # Fallback zu normaler Zeile
    
    # Normale Zeile (abwechselnd)
    bg_color = colors['row_bg_even'] if row_index % 2 == 0 else colors['row_bg_odd']
    return [f'background-color: {bg_color}; color: {colors["row_text"]}' for _ in row]


def apply_theme_to_styled_dataframe(styled_df):
    """
    Wendet Theme-Styling auf einen pandas Styler an, insbesondere für Header.
    
    PERFORMANCE: Diese Funktion ist jetzt ein No-Op, da CSS + JavaScript die Header stylen.
    Die Funktion bleibt für Kompatibilität, macht aber nichts mehr.
    
    Args:
        styled_df: Ein pandas Styler Objekt
    
    Returns:
        Der Styler unverändert zurück (CSS + JavaScript übernehmen das Styling)
    """
    # CSS + JavaScript übernehmen das Header-Styling
    # Diese Funktion wird nur noch für Kompatibilität aufgerufen
    return styled_df
