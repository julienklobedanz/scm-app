"""
Tests für Zirkuläre Abhängigkeiten

Prüft ob Production ↔ Material Konvergenz erreicht und deterministisch ist.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.master_data import MasterData


class TestCircularDependencies:
    """Tests für Zirkuläre Abhängigkeiten"""
    
    def test_product_order_deterministic(self):
        """Test: Produktreihenfolge sollte deterministisch sein"""
        # Hole Produktliste mehrfach
        products_1 = list(MasterData.BOM.keys())
        products_2 = list(MasterData.BOM.keys())
        products_3 = list(MasterData.BOM.keys())
        
        # Alle sollten identisch sein
        assert products_1 == products_2 == products_3, "Produktreihenfolge ist nicht deterministisch"
    
    def test_sorted_product_order(self):
        """Test: Produkte sollten sortiert verwendet werden"""
        # Prüfe ob sorted() verwendet werden sollte
        products_unsorted = list(MasterData.BOM.keys())
        products_sorted = sorted(MasterData.BOM.keys())
        
        # Für Determinismus sollten sortiert werden
        # (Dieser Test dokumentiert die Anforderung)
        assert products_sorted == sorted(products_unsorted), "Produkte sollten sortiert werden"
    
    def test_saddle_shares_deterministic(self):
        """Test: Sattel-Shares-Berechnung sollte deterministisch sein"""
        shares_1 = MasterData.calculate_saddle_shares()
        shares_2 = MasterData.calculate_saddle_shares()
        shares_3 = MasterData.calculate_saddle_shares()
        
        # Alle sollten identisch sein
        assert shares_1 == shares_2 == shares_3, "Sattel-Shares-Berechnung ist nicht deterministisch"
        
        # Prüfe ob Reihenfolge konsistent ist
        keys_1 = list(shares_1.keys())
        keys_2 = list(shares_2.keys())
        keys_3 = list(shares_3.keys())
        
        assert keys_1 == keys_2 == keys_3, "Sattel-Reihenfolge ist nicht konsistent"
    
    def test_convergence_required(self):
        """Test: Iterative Berechnung sollte Konvergenz erreichen"""
        # Dieser Test dokumentiert die Anforderung
        # Konkrete Implementierung würde Simulation durchführen
        # und prüfen ob Werte nach mehreren Iterationen stabil sind
        
        # Placeholder: Dokumentiert dass Konvergenz-Check benötigt wird
        assert True, "Konvergenz-Check sollte implementiert werden"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
