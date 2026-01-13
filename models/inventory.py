"""
Inventory Model
Verwaltet Lagerbestände und Bestellungen
"""

from dataclasses import dataclass


@dataclass
class Inventory:
    """Lagerbestand für eine Komponente"""
    stock_alu: float = 0.0
    stock_carbon: float = 0.0
    stock_saddles: float = 0.0
    
    def add_stock(self, component_type: str, quantity: float) -> None:
        """
        Fügt Bestand hinzu
        
        Args:
            component_type: 'saddles', 'frames_alu', 'frames_carbon'
            quantity: Menge die hinzugefügt werden soll
        """
        if component_type == 'saddles':
            self.stock_saddles += quantity
        elif component_type == 'frames_alu':
            self.stock_alu += quantity
        elif component_type == 'frames_carbon':
            self.stock_carbon += quantity

