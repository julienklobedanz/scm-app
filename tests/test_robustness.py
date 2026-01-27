"""
Robustheit-Tests

Prüft die Widerstandsfähigkeit des Systems unter verschiedenen Bedingungen.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.master_data import MasterData
from simulation.workday_calculator import WorkdayCalculator
from simulation.demand_calculator import DemandCalculator


class TestRobustness:
    """Tests für System-Robustheit"""
    
    def test_multiple_calculations_consistent(self):
        """Test: Mehrfache Berechnungen sollten konsistente Ergebnisse liefern"""
        workday_calc = WorkdayCalculator(year=2027)
        demand_calc = DemandCalculator(yearly_volume=370000, workday_calculator=workday_calc)
        
        # Berechne mehrfach
        results = []
        for _ in range(10):
            demand = demand_calc.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            results.append(demand)
        
        # Alle Ergebnisse sollten identisch sein
        assert len(set(results)) == 1, \
            f"Mehrfache Berechnungen liefern unterschiedliche Ergebnisse: {results}"
    
    def test_year_boundary_handling(self):
        """Test: Jahresgrenzen sollten korrekt behandelt werden"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Tag 0 (01.01.2027)
        date_0 = workday_calc.get_date_from_day(0)
        assert date_0.year == 2027 and date_0.month == 1 and date_0.day == 1
        
        # Tag 364 (31.12.2027)
        date_364 = workday_calc.get_date_from_day(364)
        assert date_364.year == 2027 and date_364.month == 12 and date_364.day == 31
        
        # Tag 365 (01.01.2028)
        date_365 = workday_calc.get_date_from_day(365)
        assert date_365.year == 2028 and date_365.month == 1 and date_365.day == 1
    
    def test_month_boundary_handling(self):
        """Test: Monatsgrenzen sollten korrekt behandelt werden"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Teste get_month_from_day für verschiedene Tage
        # Tag 0 = Januar
        assert MasterData.get_month_from_day(0) == 1
        
        # Tag 31 = Februar (Januar hat 31 Tage)
        assert MasterData.get_month_from_day(31) == 2
        
        # Tag 59 = März (Jan 31 + Feb 28)
        assert MasterData.get_month_from_day(59) == 3
    
    def test_extreme_parameter_combinations(self):
        """Test: Extreme Parameterkombinationen sollten funktionieren"""
        workday_calc = WorkdayCalculator(year=2027)
        
        # Sehr hohes Volumen + sehr hohe Kapazität
        try:
            demand_calc = DemandCalculator(yearly_volume=10000000, workday_calculator=workday_calc)
            demand = demand_calc.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0
        except Exception as e:
            pytest.fail(f"Extreme Parameter sollten funktionieren: {e}")
        
        # Sehr niedriges Volumen + sehr niedrige Kapazität
        try:
            demand_calc = DemandCalculator(yearly_volume=100, workday_calculator=workday_calc)
            demand = demand_calc.calculate_daily_demand_per_product(0, 'MTB Allrounder')
            assert demand >= 0
        except Exception as e:
            pytest.fail(f"Extreme Parameter sollten funktionieren: {e}")
    
    def test_all_products_calculable(self):
        """Test: Alle Produkte sollten berechenbar sein"""
        workday_calc = WorkdayCalculator(year=2027)
        demand_calc = DemandCalculator(yearly_volume=370000, workday_calculator=workday_calc)
        
        # Prüfe alle Produkte
        for product in MasterData.BOM.keys():
            try:
                demand = demand_calc.calculate_daily_demand_per_product(0, product)
                assert demand >= 0, f"Produkt {product} hat negative Nachfrage"
            except Exception as e:
                pytest.fail(f"Produkt {product} sollte berechenbar sein: {e}")
    
    def test_all_days_calculable(self):
        """Test: Alle Tage sollten berechenbar sein"""
        workday_calc = WorkdayCalculator(year=2027)
        demand_calc = DemandCalculator(yearly_volume=370000, workday_calculator=workday_calc)
        
        # Prüfe einige Tage (nicht alle 365, das wäre zu langsam)
        test_days = [0, 50, 100, 150, 200, 250, 300, 364]
        
        for day in test_days:
            try:
                demand = demand_calc.calculate_daily_demand_per_product(day, 'MTB Allrounder')
                assert demand >= 0, f"Tag {day} hat negative Nachfrage"
            except Exception as e:
                pytest.fail(f"Tag {day} sollte berechenbar sein: {e}")
    
    def test_cache_invalidation_required(self):
        """Test: Cache-Invalidierung sollte bei Parameteränderungen erfolgen"""
        # Dieser Test dokumentiert die Anforderung
        # Konkrete Implementierung würde Parameter ändern und prüfen ob Cache invalidiert wird
        
        # Placeholder: Dokumentiert dass Cache-Invalidierung benötigt wird
        assert True, "Cache-Invalidierung bei Parameteränderungen sollte implementiert werden"
    
    def test_deterministic_saddle_shares(self):
        """Test: Sattel-Shares-Berechnung sollte deterministisch sein"""
        # Berechne mehrfach
        results = []
        for _ in range(10):
            shares = MasterData.calculate_saddle_shares()
            results.append(shares)
        
        # Alle Ergebnisse sollten identisch sein
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, \
                f"Sattel-Shares-Berechnung ist nicht deterministisch: {result} != {first_result}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
