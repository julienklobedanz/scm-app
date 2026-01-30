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
    
    # Lokale Shanghai-Feiertage (zusätzlich zu nationalen chinesischen Feiertagen)
    # Shanghai folgt den nationalen Feiertagen, aber hier können lokale Feiertage hinzugefügt werden
    SHANGHAI_LOCAL_HOLIDAYS = {
        2027: {
            # Beispiel: Lokale Feiertage können hier hinzugefügt werden
            # Format: date(year, month, day): "Feiertagsname"
            # Aktuell keine zusätzlichen lokalen Feiertage bekannt
        },
        2028: {
            # Beispiel: Lokale Feiertage können hier hinzugefügt werden
        },
        2029: {
            # Beispiel: Lokale Feiertage können hier hinzugefügt werden
        }
    }
    
    @classmethod
    def get_holidays_for_year(cls, year: int, country_code: str) -> Dict[date, str]:
        """Gibt alle Feiertage für ein Jahr und Land zurück"""
        if country_code not in cls.COUNTRY_CODES:
            return {}
        
        holidays_lib_code = cls.COUNTRY_CODES[country_code]
        try:
            country_holidays = holidays.country_holidays(holidays_lib_code, years=year)
            
            # Für China: Füge lokale Shanghai-Feiertage hinzu
            if country_code == 'CN' and year in cls.SHANGHAI_LOCAL_HOLIDAYS:
                local_holidays = cls.SHANGHAI_LOCAL_HOLIDAYS[year]
                # Füge lokale Feiertage zu den nationalen hinzu
                country_holidays.update(local_holidays)
            
            return country_holidays
        except Exception as e:
            # Fallback falls Library-Problem
            return {}
    
    @classmethod
    def get_shanghai_holidays_for_year(cls, year: int) -> Dict[date, str]:
        """
        Gibt alle Feiertage für Shanghai für ein Jahr zurück.
        Enthält nationale chinesische Feiertage + lokale Shanghai-Feiertage.
        
        Args:
            year: Jahr (z.B. 2027)
        
        Returns:
            Dict[date, str]: Dictionary mit Datum -> Feiertagsname
        """
        # Hole nationale chinesische Feiertage
        national_holidays = cls.get_holidays_for_year(year, 'CN')
        
        # Füge lokale Shanghai-Feiertage hinzu
        if year in cls.SHANGHAI_LOCAL_HOLIDAYS:
            local_holidays = cls.SHANGHAI_LOCAL_HOLIDAYS[year]
            national_holidays.update(local_holidays)
        
        return national_holidays
    
    @classmethod
    def get_all_holidays(cls, year: int) -> Dict[str, List[Dict[str, str]]]:
        """Gibt alle Feiertage für alle Länder zurück"""
        all_holidays = {}
        
        for country_code in cls.COUNTRY_CODES.keys():
            # Für China: Verwende explizit Shanghai-Feiertage (nationale + lokale)
            if country_code == 'CN':
                country_holidays = cls.get_shanghai_holidays_for_year(year)
            else:
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

