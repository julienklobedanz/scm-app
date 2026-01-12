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
    
    def __init__(self, year: int = 2026):
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
    
    def is_workday(self, day: int) -> bool:
        """
        Prüft ob ein Tag ein Arbeitstag ist
        
        Arbeitstage: Montag bis Freitag, keine Feiertage
        """
        day_date = self.get_date_from_day(day)
        weekday = day_date.weekday()  # 0=Montag, 6=Sonntag
        
        # Wochenende (Samstag=5, Sonntag=6)
        if weekday >= 5:
            return False
        
        # Feiertag in Deutschland
        if day_date in self.german_holidays:
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

