"""
Feiertags-Konfiguration
Verwaltet Feiertage für alle relevanten Länder
"""

import holidays
from typing import Dict, List
from datetime import date
from config.master_data import MasterData


class HolidaysConfig:
    """Verwaltet Feiertage für verschiedene Länder"""
    
    # Länder-Codes für holidays library
    COUNTRY_CODES = {
        'DE': 'DE',  # Deutschland
        'USA': 'US',  # USA
        'FR': 'FR',  # Frankreich
        'CN': 'CN',  # China
        'CH': 'CH',  # Schweiz
        'AT': 'AT'   # Österreich
    }
    
    @classmethod
    def get_holidays_for_year(cls, year: int, country_code: str) -> Dict[date, str]:
        """Gibt alle Feiertage für ein Jahr und Land zurück"""
        if country_code not in cls.COUNTRY_CODES:
            return {}
        
        holidays_lib_code = cls.COUNTRY_CODES[country_code]
        try:
            country_holidays = holidays.country_holidays(holidays_lib_code, years=year)
            return country_holidays
        except Exception as e:
            # Fallback falls Library-Problem
            return {}
    
    @classmethod
    def get_all_holidays(cls, year: int) -> Dict[str, List[Dict[str, str]]]:
        """Gibt alle Feiertage für alle Länder zurück"""
        all_holidays = {}
        
        for country_code in cls.COUNTRY_CODES.keys():
            country_holidays = cls.get_holidays_for_year(year, country_code)
            holiday_list = []
            
            for holiday_date, holiday_name in sorted(country_holidays.items()):
                holiday_list.append({
                    'Datum': holiday_date.strftime(MasterData.DATE_FORMAT),
                    'Feiertag': holiday_name,
                    'Wochentag': holiday_date.strftime('%A')
                })
            
            all_holidays[country_code] = holiday_list
        
        return all_holidays
    
    @classmethod
    def is_holiday(cls, date_obj: date, country_code: str) -> bool:
        """Prüft ob ein Datum ein Feiertag ist"""
        if country_code not in cls.COUNTRY_CODES:
            return False
        
        holidays_lib_code = cls.COUNTRY_CODES[country_code]
        try:
            country_holidays = holidays.country_holidays(holidays_lib_code, years=date_obj.year)
            return date_obj in country_holidays
        except Exception:
            return False

