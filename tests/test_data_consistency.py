"""
Tests für Datenkonsistenz

Prüft ob Daten zwischen verschiedenen Komponenten konsistent sind.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.master_data import MasterData


class TestDataConsistency:
    """Tests für Datenkonsistenz"""
    
    def test_bom_product_sales_shares_match(self):
        """Test: Alle Produkte in BOM sollten in PRODUCT_SALES_SHARES existieren"""
        bom_products = set(MasterData.BOM.keys())
        sales_products = set(MasterData.PRODUCT_SALES_SHARES.keys())
        
        assert bom_products == sales_products, \
            f"BOM und PRODUCT_SALES_SHARES haben unterschiedliche Produkte. " \
            f"BOM: {bom_products - sales_products}, Sales: {sales_products - bom_products}"
    
    def test_saddle_types_consistent(self):
        """Test: Sattel-Typen sollten konsistent sein"""
        # Sammle alle Sattel-Typen aus BOM
        saddles_from_bom = set()
        for product, bom in MasterData.BOM.items():
            saddles_from_bom.add(bom['saddle'])
        
        # Berechne Sattel-Shares
        saddle_shares = MasterData.calculate_saddle_shares()
        saddles_from_shares = set(saddle_shares.keys())
        
        # Sollten übereinstimmen
        assert saddles_from_bom == saddles_from_shares, \
            f"Sattel-Typen stimmen nicht überein. BOM: {saddles_from_bom}, Shares: {saddles_from_shares}"
    
    def test_frame_types_consistent(self):
        """Test: Rahmen-Typen sollten konsistent sein"""
        # Sammle alle Rahmen-Typen aus BOM
        frames_from_bom = set()
        for product, bom in MasterData.BOM.items():
            frames_from_bom.add(bom['frame'])
        
        # Prüfe ob Rahmen-Typen erwartete Werte haben
        expected_frames = {'Aluminium 7005DB', 'Aluminium 7005TB', 'Carbon Monocoque'}
        assert frames_from_bom.issubset(expected_frames), \
            f"Unerwartete Rahmen-Typen gefunden: {frames_from_bom - expected_frames}"
    
    def test_fork_types_consistent(self):
        """Test: Gabel-Typen sollten konsistent sein"""
        # Sammle alle Gabel-Typen aus BOM
        forks_from_bom = set()
        for product, bom in MasterData.BOM.items():
            forks_from_bom.add(bom['fork'])
        
        # Prüfe ob Gabel-Typen nicht leer sind
        assert len(forks_from_bom) > 0, "Keine Gabel-Typen gefunden"
    
    def test_supplier_parameters_consistent(self):
        """Test: Supplier-Parameter sollten konsistent sein"""
        # Prüfe ob alle Supplier-Parameter vorhanden sind
        required_params = ['lead_time', 'order_entry_duration', 'production_time', 'lot_size']
        
        for supplier, params in MasterData.SUPPLIERS.items():
            for param in required_params:
                assert param in params, \
                    f"Lieferant {supplier} hat keinen Parameter {param}"
    
    def test_china_supplier_consistent(self):
        """Test: CHINA_SUPPLIER sollte konsistent mit SUPPLIERS sein"""
        china_supplier = MasterData.SUPPLIERS.get('China')
        china_config = MasterData.CHINA_SUPPLIER
        
        if china_supplier:
            # Prüfe ob Lead Time übereinstimmt
            assert china_supplier['lead_time'] == china_config['Saddles']['lead_time'], \
                f"Lead Time stimmt nicht überein: SUPPLIERS={china_supplier['lead_time']}, " \
                f"CHINA_SUPPLIER={china_config['Saddles']['lead_time']}"
            
            # Prüfe ob Lot Size übereinstimmt
            assert china_supplier['lot_size'] == china_config['Saddles']['lot_size'], \
                f"Lot Size stimmt nicht überein: SUPPLIERS={china_supplier['lot_size']}, " \
                f"CHINA_SUPPLIER={china_config['Saddles']['lot_size']}"
    
    def test_market_shares_sum(self):
        """Test: Summe der Marktanteile sollte 1.0 sein"""
        total_share = sum(market['share'] for market in MasterData.MARKETS.values())
        assert abs(total_share - 1.0) < 0.001, \
            f"Summe der Marktanteile ist {total_share}, sollte 1.0 sein"
    
    def test_days_per_month_sum(self):
        """Test: Summe der DAYS_PER_MONTH sollte 365 sein (2027 ist kein Schaltjahr)"""
        total_days = sum(MasterData.DAYS_PER_MONTH.values())
        assert total_days == 365, \
            f"Summe der Tage pro Monat ist {total_days}, sollte 365 sein (2027 ist kein Schaltjahr)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
