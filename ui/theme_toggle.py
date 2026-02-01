"""
Theme Toggle Component
Globaler Dark/Light Mode Toggle für alle Seiten
"""

import streamlit as st


def render_theme_toggle():
    """Rendert den Theme-Toggle oben rechts (global für alle Seiten)"""
    # Initialisiere Theme im Session State
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'  # Standard: Dark Mode
    
    # KRITISCH: Wende Theme SOFORT an (vor allem anderen), um Dark Mode Flash zu vermeiden
    apply_theme(st.session_state.theme)
    
    # CSS für Theme-Toggle (oben rechts fixiert)
    st.markdown("""
    <style>
    .theme-toggle-wrapper {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Toggle-Button oben rechts mit Columns (unsichtbare Spalten für Positionierung)
    col1, col2, col3 = st.columns([20, 1, 1])
    with col3:
        current_theme = st.session_state.theme
        theme_icon = "🌙" if current_theme == "dark" else "☀️"
        theme_text = "Dark" if current_theme == "dark" else "Light"
        
        # Kleiner Button oben rechts
        if st.button(f"{theme_icon}", key="theme_toggle_global", help=f"Wechsel zu {theme_text} Mode", use_container_width=False):
            # Toggle Theme
            st.session_state.theme = "light" if current_theme == "dark" else "dark"
            st.rerun()


def apply_theme(theme: str):
    """Wendet das Theme auf die gesamte Seite an - KRITISCH: Muss SOFORT nach st.set_page_config aufgerufen werden"""
    if theme == "dark":
        # Dark Mode (Standard Streamlit Dark - keine Änderungen nötig)
        pass  # Streamlit verwendet bereits Dark Mode als Standard
    else:
        # Light Mode - Vollständige Umstellung aller Komponenten
        # KRITISCH: CSS wird sofort geladen, um Dark Mode Flash zu vermeiden
        st.markdown("""
        <style>
        /* ============================================
           LIGHT MODE: Vollständige Umstellung
           KRITISCH: Wird sofort nach st.set_page_config geladen
           ============================================ */
        
        /* KRITISCH: Streamlit Topbar (mit Stop/Deploy) - Light Mode */
        header[data-testid="stHeader"],
        .stApp > header,
        header[data-testid="stHeader"] > div,
        header[data-testid="stHeader"] > div > div,
        header[data-testid="stHeader"] > div > div > div,
        /* Alle möglichen Topbar-Varianten */
        [data-testid="stHeader"] {
            background-color: #ffffff !important;
            border-bottom: 1px solid #e5e7eb !important;
        }
        header[data-testid="stHeader"] *,
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] span,
        header[data-testid="stHeader"] div,
        header[data-testid="stHeader"] a,
        [data-testid="stHeader"] * {
            color: #262730 !important;
        }
        /* Topbar Buttons */
        header[data-testid="stHeader"] button,
        [data-testid="stHeader"] button {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
        }
        
        /* Haupt-Container - SOFORT anwenden */
        .stApp {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .main .block-container {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        
        /* Text-Elemente - Schritt 7: Verbesserte Typografie */
        h1, h2, h3, h4, h5, h6 {
            color: #262730 !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
        }
        h1 {
            font-size: 2.25rem !important;
            margin-bottom: 1rem !important;
        }
        h2 {
            font-size: 1.75rem !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.75rem !important;
        }
        h3 {
            font-size: 1.5rem !important;
            margin-top: 1.25rem !important;
            margin-bottom: 0.5rem !important;
        }
        p, span, div, label {
            color: #262730 !important;
            line-height: 1.6 !important;
        }
        /* Mehr Abstand zwischen Absätzen */
        p {
            margin-bottom: 0.75rem !important;
        }
        
        /* ============================================
           SIDEBAR - Vollständige Light Mode Umstellung
           ============================================ */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div {
            background-color: #f0f2f6 !important;
        }
        [data-testid="stSidebar"] * {
            color: #262730 !important;
        }
        [data-testid="stSidebar"] .css-1d391kg,
        [data-testid="stSidebar"] .css-1lcbmhc,
        [data-testid="stSidebar"] [class*="css"] {
            background-color: #f0f2f6 !important;
        }
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] label {
            color: #262730 !important;
        }
        
        /* Sidebar Input-Felder - Schritt 1: Fokus-Indikatoren */
        [data-testid="stSidebar"] input[type="text"],
        [data-testid="stSidebar"] input[type="number"],
        [data-testid="stSidebar"] input[type="date"],
        [data-testid="stSidebar"] .stTextInput > div > div > input,
        [data-testid="stSidebar"] .stNumberInput > div > div > input,
        [data-testid="stSidebar"] .stDateInput > div > div > input,
        [data-testid="stSidebar"] [data-baseweb="input"] input {
            color: #262730 !important;
            background-color: #ffffff !important;
            border-color: #d1d5db !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        [data-testid="stSidebar"] input[type="text"]:focus,
        [data-testid="stSidebar"] input[type="number"]:focus,
        [data-testid="stSidebar"] input[type="date"]:focus,
        [data-testid="stSidebar"] .stTextInput > div > div > input:focus,
        [data-testid="stSidebar"] .stNumberInput > div > div > input:focus,
        [data-testid="stSidebar"] .stDateInput > div > div > input:focus,
        [data-testid="stSidebar"] [data-baseweb="input"] input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        
        /* Sidebar Select-Boxen - Schritt 1: Fokus-Indikatoren */
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] .stSelectbox > div > div > select,
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="select"] input {
            color: #262730 !important;
            background-color: #ffffff !important;
            border-color: #d1d5db !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        [data-testid="stSidebar"] select:focus,
        [data-testid="stSidebar"] .stSelectbox > div > div > select:focus,
        [data-testid="stSidebar"] [data-baseweb="select"]:focus,
        [data-testid="stSidebar"] [data-baseweb="select"] input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        
        /* Sidebar DateInput */
        [data-testid="stSidebar"] [data-baseweb="datepicker"],
        [data-testid="stSidebar"] [data-baseweb="datepicker"] input {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
        }
        
        /* Sidebar Multi-Select Tags - Helles Pastellblau (heller und blauer) */
        [data-testid="stSidebar"] [data-baseweb="tag"],
        [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"],
        [data-testid="stSidebar"] [data-baseweb="tag"] > span {
            background-color: #d0e0f0 !important;
            color: #3d4a5f !important;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"] span,
        [data-testid="stSidebar"] [data-baseweb="tag"] button {
            color: #3d4a5f !important;
        }
        
        /* Sidebar Textarea */
        [data-testid="stSidebar"] textarea {
            color: #262730 !important;
            background-color: #ffffff !important;
            border-color: #d1d5db !important;
        }
        
        /* Sidebar Buttons - Schritt 2: Hover-Effekte */
        [data-testid="stSidebar"] .stButton > button,
        [data-testid="stSidebar"] button[type="button"],
        [data-testid="stSidebar"] button:not([data-baseweb="button"]),
        [data-testid="stSidebar"] button[kind="secondary"] {
            color: #262730 !important;
            border: 1px solid #262730 !important;
            background-color: #ffffff !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] button[type="button"]:hover,
        [data-testid="stSidebar"] button[kind="secondary"]:hover {
            background-color: #f3f4f6 !important;
            border-color: #1f2937 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }
        [data-testid="stSidebar"] .stButton > button:active,
        [data-testid="stSidebar"] button[type="button"]:active,
        [data-testid="stSidebar"] button[kind="secondary"]:active {
            transform: translateY(0) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Primary Button - Schritt 2: Hover-Effekte */
        [data-testid="stSidebar"] button[type="submit"],
        [data-testid="stSidebar"] .stButton > button[kind="primary"],
        [data-testid="stSidebar"] button[kind="primary"] {
            color: #262730 !important;
            border: 1px solid #262730 !important;
            background-color: #ffffff !important;
            font-weight: 700 !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }
        [data-testid="stSidebar"] button[type="submit"]:hover,
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background-color: #f3f4f6 !important;
            border-color: #1f2937 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15) !important;
        }
        [data-testid="stSidebar"] button[type="submit"]:active,
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:active,
        [data-testid="stSidebar"] button[kind="primary"]:active {
            transform: translateY(0) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Baseweb Buttons in Sidebar - Schritt 2: Hover-Effekte */
        [data-testid="stSidebar"] [data-baseweb="button"] {
            color: #262730 !important;
            border: 1px solid #262730 !important;
            background-color: #ffffff !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }
        [data-testid="stSidebar"] [data-baseweb="button"]:hover {
            background-color: #f3f4f6 !important;
            border-color: #1f2937 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }
        [data-testid="stSidebar"] [data-baseweb="button"]:active {
            transform: translateY(0) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Sidebar Checkbox */
        [data-testid="stSidebar"] [data-baseweb="checkbox"],
        [data-testid="stSidebar"] .stCheckbox label {
            color: #262730 !important;
        }
        
        /* Szenarien-Sidebar: Alle schwarzen Elemente hell machen */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] .stSubheader,
        [data-testid="stSidebar"] .stHeader,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stInfo,
        [data-testid="stSidebar"] .stSuccess,
        [data-testid="stSidebar"] .stWarning,
        [data-testid="stSidebar"] .stError,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] strong,
        [data-testid="stSidebar"] b {
            color: #262730 !important;
        }
        
        /* Sidebar Selectbox Labels und Text - Schritt 8: Verbesserte Lesbarkeit */
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stDateInput label,
        [data-testid="stSidebar"] .stMultiSelect label {
            color: #262730 !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Sidebar Checkbox Labels */
        [data-testid="stSidebar"] .stCheckbox label,
        [data-testid="stSidebar"] .stCheckbox > label {
            color: #262730 !important;
        }
        
        /* ============================================
           TABELLEN (DataFrames) - KRITISCH: Header müssen sofort hell sein
           ============================================ */
        /* DataFrame Container */
        .stDataFrame,
        [data-testid="stDataFrame"],
        div[data-testid="stDataFrame"],
        .element-container .stDataFrame {
            background-color: #ffffff !important;
        }
        
        /* DataFrame Tabellen */
        [data-testid="stDataFrame"] table,
        .stDataFrame table,
        table[data-testid="stDataFrame"],
        .dataframe {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        
        /* KRITISCH: DataFrame Header - MAXIMALE SPEZIFITÄT für sofortige Anwendung */
        /* WICHTIG: Diese Regeln gelten für ALLE Tabellen, auch ohne pandas Styling */
        [data-testid="stDataFrame"] thead,
        .stDataFrame thead,
        .dataframe thead,
        table thead,
        .stApp table thead,
        .stApp [data-testid="stDataFrame"] thead,
        div[data-testid="stDataFrame"] thead,
        .element-container [data-testid="stDataFrame"] thead,
        /* KRITISCH: Auch für Tabellen ohne data-testid */
        .stApp table:not([class*="dataframe"]) thead,
        .main table thead,
        .block-container table thead {
            background-color: #f0f2f6 !important;
        }
        [data-testid="stDataFrame"] thead th,
        .stDataFrame thead th,
        .dataframe thead th,
        table thead th,
        .stApp table thead th,
        .stApp [data-testid="stDataFrame"] thead th,
        [data-testid="stDataFrame"] thead td,
        .dataframe thead td,
        .stApp table thead td,
        div[data-testid="stDataFrame"] thead th,
        div[data-testid="stDataFrame"] thead td,
        .element-container [data-testid="stDataFrame"] thead th,
        .element-container [data-testid="stDataFrame"] thead td,
        /* KRITISCH: Auch für Tabellen ohne data-testid */
        .stApp table:not([class*="dataframe"]) thead th,
        .main table thead th,
        .block-container table thead th,
        /* Überschreibe auch inline styles von pandas */
        [data-testid="stDataFrame"] thead th[style],
        [data-testid="stDataFrame"] thead td[style],
        .dataframe thead th[style],
        .dataframe thead td[style],
        table thead th[style],
        table thead td[style] {
            background-color: #f0f2f6 !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
        }
        [data-testid="stDataFrame"] thead tr,
        .stDataFrame thead tr,
        .dataframe thead tr,
        .stApp table thead tr,
        div[data-testid="stDataFrame"] thead tr,
        /* KRITISCH: Auch für Tabellen ohne data-testid */
        .stApp table:not([class*="dataframe"]) thead tr,
        .main table thead tr {
            background-color: #f0f2f6 !important;
        }
        
        /* KRITISCH: Tabellen-Body für Tabellen ohne pandas Styling */
        .stApp table:not([class*="dataframe"]) tbody tr,
        .main table tbody tr,
        .block-container table tbody tr {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .stApp table:not([class*="dataframe"]) tbody tr:nth-child(even),
        .main table tbody tr:nth-child(even) {
            background-color: #f9fafb !important;
        }
        .stApp table:not([class*="dataframe"]) tbody td,
        .main table tbody td {
            background-color: inherit !important;
            color: #262730 !important;
        }
        
        /* DataFrame Body */
        [data-testid="stDataFrame"] tbody,
        .stDataFrame tbody,
        .dataframe tbody,
        table tbody {
            background-color: #ffffff !important;
        }
        [data-testid="stDataFrame"] tbody tr,
        .stDataFrame tbody tr,
        .dataframe tbody tr,
        table tbody tr {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        [data-testid="stDataFrame"] tbody tr:nth-child(even),
        .stDataFrame tbody tr:nth-child(even),
        .dataframe tbody tr:nth-child(even),
        table tbody tr:nth-child(even) {
            background-color: #f9fafb !important;
        }
        [data-testid="stDataFrame"] tbody tr:hover,
        .stDataFrame tbody tr:hover,
        .dataframe tbody tr:hover {
            background-color: #f3f4f6 !important;
        }
        
        /* DataFrame Zellen - Schritt 5: Verbesserte Lesbarkeit */
        [data-testid="stDataFrame"] tbody td,
        .stDataFrame tbody td,
        .dataframe tbody td,
        table tbody td {
            background-color: inherit !important;
            color: #262730 !important;
            border-color: #e5e7eb !important;
            padding: 0.75rem 1rem !important;
            font-size: 0.95rem !important;
            line-height: 1.5 !important;
        }
        /* Tabellen-Header - Schritt 5: Größeres Padding */
        [data-testid="stDataFrame"] thead th,
        .stDataFrame thead th,
        .dataframe thead th,
        table thead th {
            padding: 0.875rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
        }
        
        /* Summenzeile */
        [data-testid="stDataFrame"] tbody tr:last-child,
        .stDataFrame tbody tr:last-child,
        .dataframe tbody tr:last-child {
            background-color: #e5e7eb !important;
        }
        [data-testid="stDataFrame"] tbody tr:last-child td,
        .stDataFrame tbody tr:last-child td,
        .dataframe tbody tr:last-child td {
            background-color: #e5e7eb !important;
            color: #262730 !important;
            font-weight: bold !important;
        }
        
        /* Pandas Styled DataFrames - Explizite Überschreibung */
        .dataframe,
        .dataframe * {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .dataframe thead,
        .dataframe thead * {
            background-color: #f0f2f6 !important;
            color: #262730 !important;
        }
        .dataframe tbody tr {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .dataframe tbody tr:nth-child(even) {
            background-color: #f9fafb !important;
        }
        .dataframe tbody td {
            background-color: inherit !important;
            color: #262730 !important;
        }
        
        /* KRITISCH: Überschreibe inline-Styles mit höchster CSS-Spezifität */
        .stApp [data-testid="stDataFrame"] table tbody tr:not([style*="#4a2525"]):not([style*="#1e3d2a"]) {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .stApp [data-testid="stDataFrame"] table tbody tr:nth-child(even):not([style*="#4a2525"]):not([style*="#1e3d2a"]) {
            background-color: #f9fafb !important;
        }
        .stApp [data-testid="stDataFrame"] table tbody td:not([style*="#4a2525"]):not([style*="#1e3d2a"]):not([style*="#404040"]) {
            background-color: inherit !important;
            color: #262730 !important;
        }
        
        /* Überschreibe Summenzeile */
        .stApp [data-testid="stDataFrame"] table tbody tr[style*="#404040"],
        .stApp [data-testid="stDataFrame"] table tbody tr:last-child {
            background-color: #e5e7eb !important;
            color: #262730 !important;
        }
        .stApp [data-testid="stDataFrame"] table tbody tr[style*="#404040"] td,
        .stApp [data-testid="stDataFrame"] table tbody tr:last-child td {
            background-color: #e5e7eb !important;
            color: #262730 !important;
        }
        
        /* Überschreibe auch für .dataframe Klassen */
        .stApp .dataframe tbody tr:not([style*="#4a2525"]):not([style*="#1e3d2a"]) {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        .stApp .dataframe tbody tr:nth-child(even):not([style*="#4a2525"]):not([style*="#1e3d2a"]) {
            background-color: #f9fafb !important;
        }
        .stApp .dataframe tbody tr[style*="#404040"],
        .stApp .dataframe tbody tr:last-child {
            background-color: #e5e7eb !important;
            color: #262730 !important;
        }
        .stApp .dataframe tbody tr[style*="#404040"] td,
        .stApp .dataframe tbody tr:last-child td {
            background-color: #e5e7eb !important;
            color: #262730 !important;
        }
        
        /* ============================================
           WEITERE UI-ELEMENTE
           ============================================ */
        /* Buttons - Schritt 2: Hover-Effekte */
        .stButton > button {
            color: #262730 !important;
            border: 1px solid #262730 !important;
            background-color: #ffffff !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }
        .stButton > button:hover {
            background-color: #f3f4f6 !important;
            border-color: #1f2937 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Input-Felder - Schritt 1: Fokus-Indikatoren */
        .stTextInput > div > div > input {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        .stNumberInput > div > div > input {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stNumberInput > div > div > input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        .stSelectbox > div > div > select {
            background-color: #ffffff !important;
            color: #262730 !important;
            border-color: #d1d5db !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stSelectbox > div > div > select:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        
        /* Metriken - Schritt 6: Verbesserte Lesbarkeit */
        [data-testid="stMetricValue"] {
            color: #262730 !important;
            font-size: 2rem !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #262730 !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
        }
        /* Metriken-Container mit Hover-Effekt */
        [data-testid="stMetricContainer"] {
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
            border-radius: 0.5rem !important;
            padding: 0.5rem !important;
        }
        [data-testid="stMetricContainer"]:hover {
            background-color: #f9fafb !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #f0f2f6 !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #262730 !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background-color: #f0f2f6 !important;
            color: #262730 !important;
        }
        
        /* Info/Warning/Error Boxes - Schritt 3: Verbesserte Darstellung */
        .stAlert {
            background-color: #f0f2f6 !important;
            padding: 1rem !important;
            border-radius: 0.5rem !important;
            border-left: 4px solid #3b82f6 !important;
            transition: box-shadow 0.2s ease !important;
        }
        .stAlert:hover {
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        }
        .stAlert p, .stAlert div {
            line-height: 1.6 !important;
            margin-bottom: 0.5rem !important;
        }
        /* Success Boxes */
        [data-baseweb="notification"]:has([class*="success"]),
        .stAlert:has([class*="success"]) {
            border-left-color: #10b981 !important;
        }
        /* Warning Boxes */
        [data-baseweb="notification"]:has([class*="warning"]),
        .stAlert:has([class*="warning"]) {
            border-left-color: #f59e0b !important;
        }
        /* Error Boxes */
        [data-baseweb="notification"]:has([class*="error"]),
        .stAlert:has([class*="error"]) {
            border-left-color: #ef4444 !important;
        }
        
        /* Schritt 10: Verbesserte Captions */
        .stCaption {
            color: #6b7280 !important;
            font-size: 0.875rem !important;
            line-height: 1.5 !important;
            margin-top: 0.25rem !important;
        }
        
        /* Schritt 4: Verbesserte Tooltips/Help-Icons - Sofortige Tooltips ohne Verzögerung */
        [data-testid="stTooltipIcon"] {
            color: #6b7280 !important;
            cursor: help !important;
            transition: color 0.05s ease !important;
        }
        [data-testid="stTooltipIcon"]:hover {
            color: #3b82f6 !important;
        }
        /* Info-Icons in Headers - Sofortige Tooltips ohne Verzögerung */
        span[title] {
            position: relative !important;
            cursor: help !important;
            transition: color 0.05s ease !important;
        }
        /* Custom Tooltip für sofortige Anzeige - Größerer Text, hellerer Hintergrund, vollständige Einblendung */
        span[title] {
            position: relative !important;
            cursor: help !important;
            transition: color 0.05s ease !important;
        }
        /* KRITISCH: Verstecke natives Browser-Tooltip wenn Custom Tooltip angezeigt wird */
        span[title]:hover {
            color: #3b82f6 !important;
            /* Entferne title-Attribut temporär um natives Tooltip zu verstecken */
        }
        span[title]:hover::after {
            content: attr(title) !important;
            position: absolute !important;
            padding: 14px 18px !important;
            background-color: #f3f4f6 !important;
            color: #262730 !important;
            font-size: 1rem !important;
            line-height: 1.5 !important;
            white-space: pre-line !important;
            border-radius: 6px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15) !important;
            border: 1px solid #d1d5db !important;
            z-index: 10000 !important;
            pointer-events: none !important;
            max-width: 750px !important;
            min-width: 450px !important;
            word-wrap: break-word !important;
            opacity: 1 !important;
            transition: opacity 0s !important;
            /* Tooltip rechts am Icon ausrichten, wächst nach links */
            right: var(--tooltip-horizontal-right, 0) !important;
            left: var(--tooltip-horizontal-left, auto) !important;
            /* Standard: Unten anzeigen (verhindert Überlauf nach oben) - wird durch JavaScript angepasst wenn oben Platz ist */
            top: var(--tooltip-position-top, 100%) !important;
            bottom: var(--tooltip-position-bottom, auto) !important;
            margin-top: var(--tooltip-margin-top, 8px) !important;
            margin-bottom: var(--tooltip-margin-bottom, 0) !important;
            /* Sicherstellen, dass Tooltip nicht über Ränder hinausgeht */
            max-width: min(750px, calc(100vw - 40px)) !important;
            max-height: calc(100vh - 100px) !important;
            overflow-y: auto !important;
        }
        /* Divider - Klarere Trennlinien */
        hr {
            border: none !important;
            border-top: 2px solid #e5e7eb !important;
            margin: 1.5rem 0 !important;
        }
        </style>
        
        <script>
        // Tooltip-Positionierung: Dynamisch anpassen wenn über Rand hinausgeht
        (function() {
            function adjustTooltipPosition(icon) {
                const iconRect = icon.getBoundingClientRect();
                const tooltipText = icon.getAttribute('title');
                
                // Erstelle temporäres Element um Tooltip-Größe zu messen
                const tempDiv = document.createElement('div');
                tempDiv.style.cssText = 'position: absolute; visibility: hidden; white-space: pre-line; font-size: 1rem; line-height: 1.5; padding: 14px 18px; max-width: 750px; min-width: 450px; word-wrap: break-word; font-family: inherit;';
                tempDiv.textContent = tooltipText;
                document.body.appendChild(tempDiv);
                const tooltipHeight = tempDiv.offsetHeight;
                const tooltipWidth = Math.min(tempDiv.offsetWidth, 750);
                document.body.removeChild(tempDiv);
                
                // Prüfe ob oben genug Platz ist
                const spaceAbove = iconRect.top;
                const spaceBelow = window.innerHeight - iconRect.bottom;
                
                // Setze Tooltip-Styles dynamisch über CSS-Variablen
                if (spaceAbove < tooltipHeight + 30 && spaceBelow > tooltipHeight + 30) {
                    // Nicht genug Platz oben, zeige unten
                    icon.style.setProperty('--tooltip-position-top', '100%');
                    icon.style.setProperty('--tooltip-position-bottom', 'auto');
                    icon.style.setProperty('--tooltip-margin-top', '8px');
                    icon.style.setProperty('--tooltip-margin-bottom', '0');
                } else {
                    // Genug Platz oben, zeige oben
                    icon.style.setProperty('--tooltip-position-top', 'auto');
                    icon.style.setProperty('--tooltip-position-bottom', '100%');
                    icon.style.setProperty('--tooltip-margin-top', '0');
                    icon.style.setProperty('--tooltip-margin-bottom', '8px');
                }
                
                // Prüfe horizontale Position
                const spaceRight = window.innerWidth - iconRect.right;
                if (spaceRight < tooltipWidth + 20 && iconRect.left > tooltipWidth + 20) {
                    // Nicht genug Platz rechts, zeige links
                    icon.style.setProperty('--tooltip-horizontal-right', 'auto');
                    icon.style.setProperty('--tooltip-horizontal-left', '0');
                } else {
                    // Genug Platz rechts, zeige rechts
                    icon.style.setProperty('--tooltip-horizontal-right', '0');
                    icon.style.setProperty('--tooltip-horizontal-left', 'auto');
                }
            }
            
            function initTooltips() {
                document.querySelectorAll('span[title]').forEach(function(icon) {
                    // Speichere original title-Attribut
                    const originalTitle = icon.getAttribute('title');
                    
                    icon.addEventListener('mouseenter', function() {
                        adjustTooltipPosition(icon);
                        // Entferne title-Attribut temporär um natives Browser-Tooltip zu verstecken
                        icon.removeAttribute('title');
                    }, { once: false });
                    
                    icon.addEventListener('mouseleave', function() {
                        // Stelle title-Attribut wieder her
                        icon.setAttribute('title', originalTitle);
                    }, { once: false });
                });
            }
            
            // Führe nach DOMContentLoaded aus
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(initTooltips, 100);
                });
            } else {
                setTimeout(initTooltips, 100);
            }
            
            // Beobachte neue Elemente (vereinfacht)
            const observer = new MutationObserver(function() {
                setTimeout(initTooltips, 100);
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        
        // KRITISCH: Vereinfachtes JavaScript für Header-Styling - verhindert Blockierung
        (function() {
            let updateCount = 0;
            const MAX_UPDATES = 10; // Verhindere Endlosschleife
            
            function updateTableHeaders() {
                if (updateCount >= MAX_UPDATES) return;
                updateCount++;
                
                try {
                    // Prüfe ob Light Mode aktiv ist (einfache Prüfung)
                    const bodyBg = window.getComputedStyle(document.body).backgroundColor;
                    const isLightMode = bodyBg.includes('255') || bodyBg.includes('rgb(255');
                    
                    if (isLightMode) {
                        // Finde ALLE Tabellen-Header (auch ohne data-testid)
                        const headers = document.querySelectorAll('[data-testid="stDataFrame"] thead th, [data-testid="stDataFrame"] thead td, .dataframe thead th, .dataframe thead td, table thead th, table thead td');
                        if (headers.length > 0) {
                            headers.forEach(header => {
                                header.style.setProperty('background-color', '#f0f2f6', 'important');
                                header.style.setProperty('color', '#262730', 'important');
                            });
                        }
                        
                        // Überschreibe auch Header-Zeilen
                        const headerRows = document.querySelectorAll('[data-testid="stDataFrame"] thead tr, .dataframe thead tr, table thead tr');
                        if (headerRows.length > 0) {
                            headerRows.forEach(row => {
                                row.style.setProperty('background-color', '#f0f2f6', 'important');
                            });
                        }
                        
                        // Überschreibe auch Tabellen-Body für Tabellen ohne pandas Styling
                        const tableRows = document.querySelectorAll('table tbody tr:not([style*="#4a2525"]):not([style*="#1e3d2a"])');
                        tableRows.forEach((row, idx) => {
                            if (idx % 2 === 0) {
                                row.style.setProperty('background-color', '#ffffff', 'important');
                            } else {
                                row.style.setProperty('background-color', '#f9fafb', 'important');
                            }
                            row.style.setProperty('color', '#262730', 'important');
                        });
                        
                        const tableCells = document.querySelectorAll('table tbody td');
                        tableCells.forEach(cell => {
                            cell.style.setProperty('color', '#262730', 'important');
                        });
                    }
                } catch (e) {
                    // Bei Fehler: Stoppe Updates
                    updateCount = MAX_UPDATES;
                }
            }
            
            // Führe nach DOMContentLoaded aus
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(updateTableHeaders, 100);
                    setTimeout(updateTableHeaders, 500);
                });
            } else {
                setTimeout(updateTableHeaders, 100);
                setTimeout(updateTableHeaders, 500);
            }
            
            // Vereinfachter MutationObserver (nur für neue Tabellen)
            try {
                const observer = new MutationObserver(function(mutations) {
                    let hasNewTable = false;
                    for (let i = 0; i < Math.min(mutations.length, 5); i++) { // Limit auf 5 Mutationen
                        if (mutations[i].addedNodes.length > 0) {
                            hasNewTable = true;
                            break;
                        }
                    }
                    if (hasNewTable && updateCount < MAX_UPDATES) {
                        setTimeout(updateTableHeaders, 200);
                    }
                });
                
                observer.observe(document.body, { 
                    childList: true, 
                    subtree: false  // Nur direkte Kinder, nicht den ganzen Baum
                });
            } catch (e) {
                // MutationObserver nicht unterstützt - ignoriere
            }
        })();
        </script>
        """, unsafe_allow_html=True)
