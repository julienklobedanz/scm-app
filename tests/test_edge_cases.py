"""
Tests für Edge Cases und Robustheit

Prüft ob das System bei extremen Werten und Edge Cases stabil bleibt.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator
from config.master_data import MasterData


class TestEdgeCases:
    """Tests für Edge Cases"""
    
    def test_zero_yearly_volume(self):
        """Test: yearly_volume = 0 sollte nicht zu Fehlern führen"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Sollte keine Exception werfen
        try:
            demand_calc = DemandCalculator(yearly_volume=0.0, workday_calculator=workday_calc)
            # Berechnung sollte funktionieren (auch wenn Ergebnis 0 ist)
            demand = demand_calc.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0, "Nachfrage sollte nicht negativ sein"
        except (ZeroDivisionError, ValueError) as e:
            pytest.fail(f"Zero yearly_volume sollte nicht zu Fehler führen: {e}")
    
    def test_negative_days(self):
        """Test: Negative Tage sollten behandelt werden"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Negative Tage sollten funktionieren (für Vorlauf-Berechnungen)
        try:
            date_neg = workday_calc.get_date_from_day(-10)
            assert date_neg.year == 2026, "Negativer Tag sollte ins Vorjahr führen"
        except Exception as e:
            pytest.fail(f"Negative Tage sollten behandelt werden: {e}")
    
    def test_days_over_365(self):
        """Test: Tage > 365 sollten behandelt werden"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Tage > 365 sollten funktionieren
        try:
            date_over = workday_calc.get_date_from_day(400)
            assert date_over.year >= 2027, "Tag > 365 sollte ins nächste Jahr führen"
        except Exception as e:
            pytest.fail(f"Tage > 365 sollten behandelt werden: {e}")
    
    def test_workday_calculator_edge_cases(self):
        """Test: WorkdayCalculator sollte Edge Cases behandeln"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Tag 0 (01.01.2027)
        assert workday_calc.is_workday(0) == True, "01.01.2027 sollte Arbeitstag sein (Neujahr ist Sonntag)"
        
        # Tag 364 (31.12.2027)
        is_workday_364 = workday_calc.is_workday(364)
        assert isinstance(is_workday_364, bool), "is_workday sollte boolean zurückgeben"
    
    def test_division_by_zero_protection(self):
        """Test: Division durch Null sollte verhindert werden"""
        # Prüfe kritische Stellen wo Division durch Null auftreten könnte
        
        # 1. num_workdays in DemandCalculator
        workday_calc = WorkdayCalculator(year=2027)
        demand_calc = DemandCalculator(yearly_volume=370000, workday_calculator=workday_calc)
        
        # Sollte keine Division durch Null geben
        try:
            # Berechne für verschiedenen Monat
            demand = demand_calc.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0, "Nachfrage sollte nicht negativ sein"
        except ZeroDivisionError as e:
            pytest.fail(f"Division durch Null sollte verhindert werden: {e}")
    
    def test_empty_bom(self):
        """Test: Leere BOM sollte behandelt werden"""
        # Dokumentiert Anforderung: BOM sollte nicht leer sein
        assert len(MasterData.BOM) > 0, "BOM sollte nicht leer sein"
    
    def test_empty_product_sales_shares(self):
        """Test: Leere PRODUCT_SALES_SHARES sollte behandelt werden"""
        # Dokumentiert Anforderung: PRODUCT_SALES_SHARES sollte nicht leer sein
        assert len(MasterData.PRODUCT_SALES_SHARES) > 0, "PRODUCT_SALES_SHARES sollte nicht leer sein"
    
    def test_extreme_yearly_volume(self):
        """Test: Extreme yearly_volume Werte sollten funktionieren"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Sehr große Werte
        try:
            demand_calc_large = DemandCalculator(yearly_volume=10000000, workday_calculator=workday_calc)
            demand = demand_calc_large.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0, "Nachfrage sollte nicht negativ sein"
        except Exception as e:
            pytest.fail(f"Große yearly_volume sollte funktionieren: {e}")
        
        # Sehr kleine Werte
        try:
            demand_calc_small = DemandCalculator(yearly_volume=100, workday_calculator=workday_calc)
            demand = demand_calc_small.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0, "Nachfrage sollte nicht negativ sein"
        except Exception as e:
            pytest.fail(f"Kleine yearly_volume sollte funktionieren: {e}")
    
    def test_invalid_product_name(self):
        """Test: Ungültiger Produktname sollte behandelt werden"""
        workday_calc = WorkdayCalculator(year=2027)
        demand_calc = DemandCalculator(yearly_volume=370000, workday_calculator=workday_calc)
        
        # Ungültiger Produktname sollte nicht zu Exception führen
        try:
            demand = demand_calc.calculate_daily_demand_per_product(0, 'INVALID_PRODUCT')
            # Sollte 0 zurückgeben oder Exception werfen (beides OK)
            assert demand >= 0, "Nachfrage sollte nicht negativ sein"
        except KeyError:
            # KeyError ist OK - Produkt existiert nicht
            pass
        except Exception as e:
            pytest.fail(f"Ungültiger Produktname sollte behandelt werden: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
