"""
Tests für Parameter-Konsistenz

Prüft ob Parameteränderungen korrekt synchronisiert werden und Caches invalidiert werden.
"""

import pytest
import sys
from pathlib import Path

# Füge Projekt-Root zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.master_data import MasterData


class TestParameterConsistency:
    """Tests für Parameter-Konsistenz"""
    
    def test_yearly_volume_default_value(self):
        """Test: Standardwert für yearly_volume sollte 370000 sein"""
        # Prüfe ob Standardwert konsistent ist
        assert MasterData.GLOBAL_CONFIG['total_volume'] == 370000
    
    def test_product_sales_shares_sum(self):
        """Test: Summe der PRODUCT_SALES_SHARES sollte 1.0 sein"""
        total_share = sum(MasterData.PRODUCT_SALES_SHARES.values())
        assert abs(total_share - 1.0) < 0.001, f"Summe der Verkaufsanteile ist {total_share}, sollte 1.0 sein"
    
    def test_seasonality_sum(self):
        """Test: Summe der SEASONALITY sollte 1.0 sein"""
        total_seasonality = sum(MasterData.SEASONALITY.values())
        assert abs(total_seasonality - 1.0) < 0.001, f"Summe der Saisonalität ist {total_seasonality}, sollte 1.0 sein"
    
    def test_daily_workload_sum(self):
        """Test: Summe der DAILY_WORKLOAD für Mo-Fr sollte 1.0 sein"""
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
        total_workload = sum(MasterData.DAILY_WORKLOAD[day] for day in weekdays)
        assert abs(total_workload - 1.0) < 0.001, f"Summe der Arbeitslast Mo-Fr ist {total_workload}, sollte 1.0 sein"
    
    def test_bom_products_exist(self):
        """Test: Alle Produkte in PRODUCT_SALES_SHARES sollten in BOM existieren"""
        for product in MasterData.PRODUCT_SALES_SHARES.keys():
            assert product in MasterData.BOM, f"Produkt {product} existiert nicht in BOM"
    
    def test_bom_components_exist(self):
        """Test: Alle Komponenten in BOM sollten existieren"""
        all_frames = set()
        all_saddles = set()
        all_forks = set()
        
        for product, bom in MasterData.BOM.items():
            assert 'frame' in bom, f"Produkt {product} hat kein 'frame'"
            assert 'saddle' in bom, f"Produkt {product} hat kein 'saddle'"
            assert 'fork' in bom, f"Produkt {product} hat kein 'fork'"
            
            all_frames.add(bom['frame'])
            all_saddles.add(bom['saddle'])
            all_forks.add(bom['fork'])
        
        # Prüfe ob Komponenten nicht leer sind
        assert len(all_frames) > 0, "Keine Rahmen-Typen gefunden"
        assert len(all_saddles) > 0, "Keine Sattel-Typen gefunden"
        assert len(all_forks) > 0, "Keine Gabel-Typen gefunden"
    
    def test_saddle_shares_calculation(self):
        """Test: calculate_saddle_shares() sollte konsistente Werte liefern"""
        saddle_shares = MasterData.calculate_saddle_shares()
        
        # Prüfe ob alle Shares zwischen 0 und 1 sind
        for saddle, share in saddle_shares.items():
            assert 0.0 <= share <= 1.0, f"Sattel {saddle} hat ungültigen Share {share}"
        
        # Prüfe ob Summe = 1.0 ist
        total_share = sum(saddle_shares.values())
        assert abs(total_share - 1.0) < 0.001, f"Summe der Sattel-Shares ist {total_share}, sollte 1.0 sein"
    
    def test_global_config_values_positive(self):
        """Test: Alle Werte in GLOBAL_CONFIG sollten positiv sein"""
        assert MasterData.GLOBAL_CONFIG['total_volume'] > 0
        assert MasterData.GLOBAL_CONFIG['capacity_per_hour'] > 0
        assert MasterData.GLOBAL_CONFIG['assembly_lines'] > 0
        assert MasterData.GLOBAL_CONFIG['min_shifts_per_day'] > 0
        assert MasterData.GLOBAL_CONFIG['max_shifts_per_day'] > 0
        assert MasterData.GLOBAL_CONFIG['working_hours_per_shift'] > 0
        assert MasterData.GLOBAL_CONFIG['batch_size'] > 0
    
    def test_min_max_shifts_consistency(self):
        """Test: min_shifts_per_day sollte <= max_shifts_per_day sein"""
        min_shifts = MasterData.GLOBAL_CONFIG['min_shifts_per_day']
        max_shifts = MasterData.GLOBAL_CONFIG['max_shifts_per_day']
        assert min_shifts <= max_shifts, f"min_shifts ({min_shifts}) > max_shifts ({max_shifts})"
    
    def test_supplier_lead_times_positive(self):
        """Test: Alle Lead Times sollten positiv sein"""
        for supplier, params in MasterData.SUPPLIERS.items():
            assert params['lead_time'] > 0, f"Lieferant {supplier} hat ungültige Lead Time"
            assert params['production_time'] > 0, f"Lieferant {supplier} hat ungültige Produktionszeit"
            assert params['lot_size'] > 0, f"Lieferant {supplier} hat ungültige Losgröße"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
