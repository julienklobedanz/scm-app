"""
Hilfsfunktionen für Tabellen-Styling
Markiert Zeilen die durch Szenarien beeinflusst werden
"""

import pandas as pd
from typing import List, Optional


def get_scenario_affected_rows(df: pd.DataFrame, table_type: str) -> List[bool]:
    """
    Identifiziert Zeilen die durch Szenarien beeinflusst werden.
    PERFORMANCE-OPTIMIERT: Verwendet vektorisierte Pandas-Operationen statt Schleifen.
    
    Args:
        df: DataFrame mit den Daten
        table_type: Typ der Tabelle ('production', 'inbound', 'material', 'volume_planning')
    
    Returns:
        Liste von Booleans (True = Zeile ist beeinflusst)
    """
    if len(df) == 0:
        return []
    
    affected = pd.Series([False] * len(df))
    
    if table_type == 'production':
        # Produktion: Markiere wenn tatsächliche PM != geplante PM oder Backlog > 0
        if 'geplante PM' in df.columns and 'tatsächliche PM' in df.columns:
            # PERFORMANCE: Vektorisierte Operation statt Schleife
            planned_series = pd.to_numeric(df['geplante PM'], errors='coerce')
            actual_series = pd.to_numeric(df['tatsächliche PM'], errors='coerce')
            # Nur markieren wenn beide Werte vorhanden UND unterschiedlich UND nicht beide 0
            both_valid = planned_series.notna() & actual_series.notna()
            different = planned_series != actual_series
            # Nicht markieren wenn beide 0 sind (das ist normal)
            not_both_zero = (planned_series != 0) | (actual_series != 0)
            affected = affected | (both_valid & different & not_both_zero)
        
        # Auch markieren wenn Backlog > 0
        if 'Backlog' in df.columns:
            backlog_series = pd.to_numeric(df['Backlog'], errors='coerce')
            affected = affected | (backlog_series.notna() & (backlog_series > 0))
    
    elif table_type == 'inbound':
        # Inbound: Markiere nur wenn tatsächlich Verspätung oder Ladungsverlust vorhanden
        if 'Verspätung' in df.columns:
            # Prüfe numerische Werte
            delay_series = pd.to_numeric(df['Verspätung'], errors='coerce')
            # Nur markieren wenn numerischer Wert > 0
            affected = affected | (delay_series.notna() & (delay_series > 0))
            # Prüfe String-Werte: Nur markieren wenn NICHT "Nein", leer oder "0"
            delay_str = df['Verspätung'].astype(str).str.strip().str.lower()
            # Nur wenn numerische Konvertierung fehlgeschlagen ist UND String nicht "nein" oder leer
            is_string_value = delay_series.isna()
            is_not_no = (delay_str != 'nein') & (delay_str != '') & (delay_str != 'nan') & (delay_str != '0')
            affected = affected | (is_string_value & is_not_no)
        
        if 'Ladungsverlust' in df.columns:
            # Prüfe numerische Werte
            loss_series = pd.to_numeric(df['Ladungsverlust'], errors='coerce')
            # Nur markieren wenn numerischer Wert > 0
            affected = affected | (loss_series.notna() & (loss_series > 0))
            # Prüfe String-Werte: Nur markieren wenn NICHT "Nein", leer oder "0"
            loss_str = df['Ladungsverlust'].astype(str).str.strip().str.lower()
            # Nur wenn numerische Konvertierung fehlgeschlagen ist UND String nicht "nein" oder leer
            is_string_value = loss_series.isna()
            is_not_no = (loss_str != 'nein') & (loss_str != '') & (loss_str != 'nan') & (loss_str != '0')
            affected = affected | (is_string_value & is_not_no)
        
        # Auch markieren wenn geplante != tatsächliche Ankunft (nur wenn beide vorhanden und unterschiedlich)
        if 'Geplante Ankunft LKW 🇩🇪' in df.columns and 'Tatsächliche Ankunft LKW 🇩🇪' in df.columns:
            planned_str = df['Geplante Ankunft LKW 🇩🇪'].astype(str).str.strip()
            actual_str = df['Tatsächliche Ankunft LKW 🇩🇪'].astype(str).str.strip()
            # Nur markieren wenn beide nicht leer/nan sind UND unterschiedlich
            both_valid = (planned_str != 'nan') & (actual_str != 'nan') & (planned_str != '') & (actual_str != '')
            affected = affected | (both_valid & (planned_str != actual_str))
    
    elif table_type == 'volume_planning':
        # Volumenplanung: Markiere wenn geplant != tatsächlich
        # WICHTIG: Unterstützt sowohl normale Spalten als auch MultiIndex-Spalten
        if isinstance(df.columns, pd.MultiIndex):
            # MultiIndex: Suche nach Spalten mit 'Geplanter Bedarf' und 'Tatsächlicher Bedarf'
            for col_tuple in df.columns:
                if isinstance(col_tuple, tuple) and len(col_tuple) == 2:
                    product, col_type = col_tuple
                    if col_type == 'Geplanter Bedarf':
                        actual_col = (product, 'Tatsächlicher Bedarf')
                        if actual_col in df.columns:
                            planned_series = pd.to_numeric(df[col_tuple], errors='coerce')
                            actual_series = pd.to_numeric(df[actual_col], errors='coerce')
                            affected = affected | (planned_series.notna() & actual_series.notna() & (planned_series != actual_series))
                            break  # Nur einmal pro Zeile markieren
        else:
            # Normale Spalten: Suche nach Spalten die mit '_geplant' enden
            for col in df.columns:
                if isinstance(col, str) and col.endswith('_geplant'):
                    actual_col = col.replace('_geplant', '_tatsächlich')
                    if actual_col in df.columns:
                        planned_series = pd.to_numeric(df[col], errors='coerce')
                        actual_series = pd.to_numeric(df[actual_col], errors='coerce')
                        affected = affected | (planned_series.notna() & actual_series.notna() & (planned_series != actual_series))
                        break  # Nur einmal pro Zeile markieren
    
    elif table_type == 'material':
        # Materiallager: Markiere wenn Bestand durch Szenarien beeinflusst wird
        # PERFORMANCE: Vektorisierte Operation für alle relevanten Spalten
        numeric_cols = [col for col in df.columns if col not in ['Wochentag', 'Datum', 'Is_Weekend', 'Is_Holiday']]
        for col in numeric_cols:
            if 'Bestand' in col or 'Lagerzugang' in col or 'Lagerabgang' in col:
                val_series = pd.to_numeric(df[col], errors='coerce')
                # Markiere wenn Bestand = 0 aber vorheriger Wert > 0
                is_zero = (val_series.notna() & (val_series == 0))
                prev_val_series = val_series.shift(1)
                was_positive = (prev_val_series.notna() & (prev_val_series > 0))
                affected = affected | (is_zero & was_positive)
    
    return affected.tolist()


def style_row_with_scenarios(row, affected_flags: List[bool], weekend_flags: Optional[List[bool]] = None, 
                             holiday_flags: Optional[List[bool]] = None) -> List[str]:
    """
    Styling-Funktion für DataFrame-Zeilen mit Szenario-Markierung.
    
    Args:
        row: DataFrame-Zeile
        affected_flags: Liste von Booleans (True = Zeile ist durch Szenario beeinflusst)
        weekend_flags: Optional - Liste von Booleans für Wochenenden
        holiday_flags: Optional - Liste von Booleans für Feiertage
    
    Returns:
        Liste von CSS-Styles (eine pro Spalte)
    """
    idx = row.name
    
    # Summenzeile: grauer Hintergrund
    if idx >= len(affected_flags):
        return ['background-color: #e0e0e0; font-weight: bold'] * len(row)
    
    # Wochenende hat höchste Priorität
    if weekend_flags and idx < len(weekend_flags) and weekend_flags[idx]:
        return ['background-color: #ffebee'] * len(row)
    
    # Feiertag hat zweite Priorität
    if holiday_flags and idx < len(holiday_flags) and holiday_flags[idx]:
        return ['background-color: #c8e6c9'] * len(row)
    
    # Szenario-beeinflusste Zeile: gelber Hintergrund
    if idx < len(affected_flags) and affected_flags[idx]:
        return ['background-color: #fff9c4'] * len(row)
    
    # Normale Zeile
    return [''] * len(row)
