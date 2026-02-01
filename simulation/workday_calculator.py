"""
Workday Calculator
Berechnet Arbeitstage unter Berücksichtigung von Wochentagen und Feiertagen
"""

from datetime import date, timedelta
from typing import Dict
from config.master_data import MasterData
from config.holidays_config import HolidaysConfig


class WorkdayCalculator:
    """Berechnet ob ein Tag ein Arbeitstag ist"""
    
    def __init__(self, year: int = 2027):
        self.year = year
        self.master_data = MasterData
        self.holidays_config = HolidaysConfig
        
        # Wochentage (0=Montag, 6=Sonntag)
        self.weekday_names = {
            0: 'Montag',
            1: 'Dienstag',
            2: 'Mittwoch',
            3: 'Donnerstag',
            4: 'Freitag',
            5: 'Samstag',
            6: 'Sonntag'
        }
        
        # Lade Feiertage für Deutschland (Hauptstandort)
        self.german_holidays = HolidaysConfig.get_holidays_for_year(year, 'DE')
    
    def get_date_from_day(self, day: int) -> date:
        """Konvertiert Tag (0-basiert) zu Datum (unterstützt auch negative Tage)"""
        start_date = date(self.year, 1, 1)
        return start_date + timedelta(days=day)
    
    def is_weekend(self, day: int) -> bool:
        """
        Prüft ob ein Tag ein Wochenende ist (Samstag oder Sonntag)
        
        Returns:
            True wenn Samstag oder Sonntag, sonst False
        """
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()  # 0=Montag, 6=Sonntag
        return weekday >= 5  # Samstag=5, Sonntag=6
    
    def is_workday(self, day: int) -> bool:
        """
        Prüft ob ein Tag ein Arbeitstag ist
        
        Arbeitstage: Montag bis Freitag, keine Feiertage, und DAILY_WORKLOAD > 0.0
        """
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()  # 0=Montag, 6=Sonntag
        
        # Wochenende (Samstag=5, Sonntag=6)
        if weekday >= 5:
            return False
        
        # Feiertag in Deutschland
        if day_date in self.german_holidays:
            return False
        
        # KRITISCH: Prüfe auch DAILY_WORKLOAD - wenn 0.0, dann kein Arbeitstag
        weekday_name = self.weekday_names[weekday]
        workload_factor = self.master_data.DAILY_WORKLOAD.get(weekday_name, 0.0)
        if workload_factor <= 0.0:
            return False
        
        return True
    
    def get_workday_factor(self, day: int) -> float:
        """
        Gibt den Arbeitslast-Faktor für einen Tag zurück
        
        Returns:
            0.0 wenn kein Arbeitstag, sonst den Faktor aus DAILY_WORKLOAD
        """
        if not self.is_workday(day):
            return 0.0
        
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()
        weekday_name = self.weekday_names[weekday]
        
        return self.master_data.DAILY_WORKLOAD.get(weekday_name, 0.0)
    
    def get_weekday_name(self, day: int) -> str:
        """Gibt den Wochentag-Namen zurück"""
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()
        return self.weekday_names[weekday]
    
    def get_weekday_abbr(self, day: int) -> str:
        """
        Gibt die Wochentag-Abkürzung zurück (Mo, Di, Mi, Do, Fr, Sa, So)
        
        Args:
            day: Tag (0-basiert)
            
        Returns:
            Wochentag-Abkürzung (2 Zeichen)
        """
        weekday_abbrs = {
            0: 'Mo',
            1: 'Di',
            2: 'Mi',
            3: 'Do',
            4: 'Fr',
            5: 'Sa',
            6: 'So'
        }
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()
        return weekday_abbrs[weekday]
    
    def get_day_info(self, day: int) -> Dict[str, any]:
        """
        Gibt alle Informationen zu einem Tag zurück (Wochentag, Is_Workday, Is_Weekend, Is_Holiday)
        
        Args:
            day: Tag (0-basiert)
            
        Returns:
            Dictionary mit:
            - 'weekday_name': Vollständiger Wochentag-Name (z.B. 'Montag')
            - 'weekday_abbr': Wochentag-Abkürzung (z.B. 'Mo')
            - 'is_workday': True wenn Arbeitstag
            - 'is_weekend': True wenn Wochenende
            - 'is_holiday': True wenn Feiertag (aber nicht Wochenende)
        """
        weekday_name = self.get_weekday_name(day)
        weekday_abbr = self.get_weekday_abbr(day)
        is_workday = self.is_workday(day)
        is_weekend = self.is_weekend(day)
        is_holiday = not is_workday and not is_weekend
        
        return {
            'weekday_name': weekday_name,
            'weekday_abbr': weekday_abbr,
            'is_workday': is_workday,
            'is_weekend': is_weekend,
            'is_holiday': is_holiday
        }

