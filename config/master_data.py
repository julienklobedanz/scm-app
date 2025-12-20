"""
Master Data Konfiguration
Enthält alle statischen Daten: BOM, Saisonalität, Märkte, Supplier-Parameter
"""

from typing import Dict, Any


class MasterData:
    """Zentraler Container für alle Master Data"""
    
    # Saisonalität (Prozentanteil pro Monat)
    SEASONALITY: Dict[int, float] = {
        1: 0.04,   # Jan
        2: 0.06,   # Feb
        3: 0.10,   # Mar
        4: 0.16,   # Apr
        5: 0.14,   # May
        6: 0.13,   # Jun
        7: 0.12,   # Jul
        8: 0.09,   # Aug
        9: 0.06,   # Sep
        10: 0.03,  # Oct
        11: 0.04,  # Nov
        12: 0.03   # Dec
    }
    
    # Marktverteilung und Transitzeiten
    MARKETS: Dict[str, Dict[str, Any]] = {
        'DE': {'share': 0.37, 'transit_days': 2},
        'USA': {'share': 0.23, 'transit_days': 16},
        'FR': {'share': 0.18, 'transit_days': 3},
        'CN': {'share': 0.10, 'transit_days': 30},
        'CH': {'share': 0.06, 'transit_days': 2},
        'AT': {'share': 0.06, 'transit_days': 2}
    }
    
    # Bill of Materials (BOM) - basierend auf Stammdaten_Produkt
    BOM: Dict[str, Dict[str, str]] = {
        'MTB Allrounder': {
            'frame': 'Aluminium 7005DB',
            'saddle': 'Spark',
            'fork': 'Fox32 F100'
        },
        'MTB Competition': {
            'frame': 'Carbon Monocoque',
            'saddle': 'Speed line',
            'fork': 'Fox Talas140'
        },
        'MTB Downhill': {
            'frame': 'Aluminium 7005TB',
            'saddle': 'Fizik Tundra',
            'fork': 'Rock Schox Recon351'
        },
        'MTB Extreme': {
            'frame': 'Carbon Monocoque',
            'saddle': 'Spark',
            'fork': 'Rock Schox Reba'
        },
        'MTB Freeride': {
            'frame': 'Aluminium 7005TB',
            'saddle': 'Fizik Tundra',
            'fork': 'Fox32 F80'
        },
        'MTB Marathon': {
            'frame': 'Aluminium 7005DB',
            'saddle': 'Race line',
            'fork': 'Rock Schox ReconSL'
        },
        'MTB Performance': {
            'frame': 'Aluminium 7005TB',
            'saddle': 'Fizik Tundra',
            'fork': 'Rock Schox Reba'
        },
        'MTB Trail': {
            'frame': 'Carbon Monocoque',
            'saddle': 'Speed line',
            'fork': 'SR Suntour Raidon'
        }
    }
    
    # Verkaufsanteile (basierend auf Stammdaten_Planung)
    PRODUCT_SALES_SHARES: Dict[str, float] = {
        'MTB Allrounder': 0.30,
        'MTB Competition': 0.15,
        'MTB Downhill': 0.10,
        'MTB Extreme': 0.07,
        'MTB Freeride': 0.05,
        'MTB Marathon': 0.08,
        'MTB Performance': 0.12,
        'MTB Trail': 0.13
    }
    
    # Globale Konfiguration (basierend auf Stammdaten_Planung)
    GLOBAL_CONFIG: Dict[str, Any] = {
        'total_volume': 370000,
        'capacity_per_hour': 130,
        'assembly_lines': 1,
        'min_shifts_per_day': 1,
        'max_shifts_per_day': 3,
        'working_hours_per_shift': 8,
        'batch_size': 1
    }
    
    # Tägliche Arbeitslast (basierend auf Stammdaten_Planung)
    DAILY_WORKLOAD: Dict[str, float] = {
        'Montag': 0.2,
        'Dienstag': 0.2,
        'Mittwoch': 0.2,
        'Donnerstag': 0.2,
        'Freitag': 0.2,
        'Samstag': 0.0,
        'Sonntag': 0.0
    }
    
    # Lieferanten (basierend auf Stammdaten_Logistik)
    SUPPLIERS: Dict[str, Dict[str, Any]] = {
        'Deutschland': {
            'federal_state': 'BW',
            'lead_time': 7,
            'order_entry_duration': 1,
            'production_time': 2,
            'lot_size': 10
        },
        'Spanien': {
            'federal_state': 'Alle',
            'lead_time': 14,
            'order_entry_duration': 1,
            'production_time': 5,
            'lot_size': 75
        },
        'China': {
            'federal_state': 'Alle',
            'lead_time': 49,
            'order_entry_duration': 1,
            'production_time': 5,
            'lot_size': 500
        }
    }
    
    # Auslieferungs-Routen (basierend auf Stammdaten_Logistik)
    DELIVERY_ROUTES: list[Dict[str, Any]] = [
        {'destination': 'China', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT'},
        {'destination': 'China', 'departure': 'Deutschland', 'arrival': 'China', 
         'transport': 'Schiff-Typ30', 'duration': 30, 'type': 'KT'},
        {'destination': 'China', 'departure': 'China', 'arrival': 'China', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT'},
        {'destination': 'Deutschland', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ3', 'duration': 3, 'type': 'AT'},
        {'destination': 'Frankreich', 'departure': 'Deutschland', 'arrival': 'Frankreich', 
         'transport': 'LKW-Typ5', 'duration': 5, 'type': 'AT'},
        {'destination': 'Österreich', 'departure': 'Deutschland', 'arrival': 'Österreich', 
         'transport': 'LKW-Typ4', 'duration': 4, 'type': 'AT'},
        {'destination': 'Schweiz', 'departure': 'Deutschland', 'arrival': 'Schweiz', 
         'transport': 'LKW-Typ4', 'duration': 4, 'type': 'AT'},
        {'destination': 'USA', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT'},
        {'destination': 'USA', 'departure': 'Deutschland', 'arrival': 'USA', 
         'transport': 'Schiff-Typ14', 'duration': 14, 'type': 'KT'},
        {'destination': 'USA', 'departure': 'USA', 'arrival': 'USA', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT'}
    ]
    
    # Beschaffungs-Routen (basierend auf Beschaffung)
    PROCUREMENT_ROUTES: list[Dict[str, Any]] = [
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'China', 'arrival': 'China', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT', 'standard_duration': 2},
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'China', 'arrival': 'Deutschland', 
         'transport': 'Schiff-Typ30', 'duration': 30, 'type': 'KT', 'standard_duration': 22},
        {'supplier': 'China', 'component': 'Sattel', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ2', 'duration': 2, 'type': 'AT', 'standard_duration': 2},
        {'supplier': 'Deutschland', 'component': 'Rahmen', 'departure': 'Deutschland', 'arrival': 'Deutschland', 
         'transport': 'LKW-Typ3', 'duration': 3, 'type': 'AT', 'standard_duration': 3},
        {'supplier': 'Spanien', 'component': 'Gabel', 'departure': 'Spanien', 'arrival': 'Deutschland', 
         'transport': 'Bahn-Typ9', 'duration': 9, 'type': 'KT', 'standard_duration': 7}
    ]
    
    # China Supplier Parameter (basierend auf Stammdaten_Logistik: Lead Time 49 Tage)
    CHINA_SUPPLIER: Dict[str, Dict[str, Any]] = {
        'Frames': {
            'lead_time': 49,  # Basierend auf Stammdaten_Logistik
            'lot_size': 500,  # Basierend auf Stammdaten_Logistik
            'reorder_threshold_days': 2
        },
        'Saddles': {
            'lead_time': 49,  # Basierend auf Stammdaten_Logistik
            'lot_size': 500,  # Basierend auf Stammdaten_Logistik
            'reorder_threshold_days': 2
        }
    }
    
    # Tage pro Monat (für präzise Berechnung)
    DAYS_PER_MONTH: Dict[int, int] = {
        1: 31,   # Jan
        2: 28,   # Feb (2027 ist kein Schaltjahr)
        3: 31,   # Mar
        4: 30,   # Apr
        5: 31,   # May
        6: 30,   # Jun
        7: 31,   # Jul
        8: 31,   # Aug
        9: 30,   # Sep
        10: 31,  # Oct
        11: 30,  # Nov
        12: 31   # Dec
    }
    
    @classmethod
    def get_month_from_day(cls, day: int) -> int:
        """Berechnet den Monat aus dem Tag (0-basiert)"""
        day_of_year = day % 365
        cumulative_days = 0
        for month in range(1, 13):
            days_in_month = cls.DAYS_PER_MONTH[month]
            if day_of_year < cumulative_days + days_in_month:
                return month
            cumulative_days += days_in_month
        return 12  # Fallback
    
    @classmethod
    def get_day_in_month(cls, day: int) -> int:
        """Berechnet den Tag im Monat (1-basiert)"""
        day_of_year = day % 365
        cumulative_days = 0
        for month in range(1, 13):
            days_in_month = cls.DAYS_PER_MONTH[month]
            if day_of_year < cumulative_days + days_in_month:
                return day_of_year - cumulative_days + 1
            cumulative_days += days_in_month
        return 31  # Fallback
    
    @classmethod
    def get_frame_category(cls, frame_type: str) -> str:
        """Mappt spezifischen Rahmen-Typ auf Kategorie (Alu/Carbon) für Simulation"""
        if 'Aluminium' in frame_type or 'Alu' in frame_type:
            return 'Alu'
        elif 'Carbon' in frame_type:
            return 'Carbon'
        else:
            return 'Alu'  # Fallback
    
    # Standard Initialer Lagerbestand (festgelegt)
    DEFAULT_INITIAL_STOCK = {
        'frames_alu': 5000,
        'frames_carbon': 2000,
        'saddles': 7000  # Zusammenführung von Standard + Premium
    }

