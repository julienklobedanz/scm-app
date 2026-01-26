"""
Szenarien-Modell
Definiert verschiedene Störungsszenarien für die Simulation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Scenario:
    """Basisklasse für Szenarien"""
    name: str
    start_day: int
    end_day: int
    active: bool = True


@dataclass
class MarketingCampaignScenario(Scenario):
    """Marketingaktion: Erhöht die Nachfrage für einen Zeitraum"""
    demand_increase_factor: float = 1.5  # 50% mehr Nachfrage
    affected_products: Optional[List[str]] = None  # Liste von Produktnamen, None = alle Produkte (Rückwärtskompatibilität)


@dataclass
class WarehouseDamageScenario(Scenario):
    """Wasserschaden im Lager: Reduziert Lagerbestand (z.B. Sättel werden beschädigt)"""
    stock_loss_percentage: float = 0.5  # 50% Verlust des Lagerbestands
    affected_component: str = "saddles"  # Welche Komponente ist betroffen


@dataclass
class SupplierBreakdownScenario(Scenario):
    """Maschinenausfall beim Lieferanten in China: Stoppt Lieferungen"""
    component_type: str = "all"  # "frames", "saddles", "all"


@dataclass
class DeliveryProblemScenario(Scenario):
    """Lieferprobleme beim Lieferanten: Verlust und/oder Verspätung (nur Sättel)"""
    loss_percentage: float = 0.0  # 0.0 = kein Verlust, 1.0 = 100% Verlust
    delay_days: int = 0  # Zusätzliche Verspätung in Tagen
    component_type: str = "saddles"  # Immer Sättel (keine Wahlmöglichkeit mehr)


@dataclass
class StandardScenario(Scenario):
    """Standard-Szenario: Keine Probleme, alles läuft normal"""
    name: str = "Standard (Keine Probleme)"
    start_day: int = 0
    end_day: int = 364
    active: bool = True


@dataclass
class ScenarioManager:
    """Verwaltet alle aktiven Szenarien"""
    scenarios: list[Scenario] = field(default_factory=list)
    standard_scenario: StandardScenario = field(default_factory=lambda: StandardScenario())
    
    def __post_init__(self):
        """Standard-Szenario ist immer aktiv"""
        if not any(isinstance(s, StandardScenario) for s in self.scenarios):
            self.scenarios.insert(0, self.standard_scenario)
    
    def add_scenario(self, scenario: Scenario) -> None:
        """Fügt ein Szenario hinzu"""
        self.scenarios.append(scenario)
    
    def get_active_scenarios(self, day: int) -> list[Scenario]:
        """Gibt alle aktiven Szenarien für einen bestimmten Tag zurück (ohne Standard-Szenario)"""
        return [
            s for s in self.scenarios
            if s.active and s.start_day <= day <= s.end_day and not isinstance(s, StandardScenario)
        ]
    
    def get_marketing_scenarios(self, day: int) -> list[MarketingCampaignScenario]:
        """Gibt aktive Marketing-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, MarketingCampaignScenario)
        ]
    
    def get_warehouse_damage_scenarios(self, day: int) -> list[WarehouseDamageScenario]:
        """Gibt aktive Wasserschaden-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, WarehouseDamageScenario)
        ]
    
    def get_supplier_breakdown_scenarios(self, day: int) -> list[SupplierBreakdownScenario]:
        """Gibt aktive Lieferantenausfall-Szenarien zurück (nur Sättel)"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, SupplierBreakdownScenario)
            and s.component_type in ['saddles', 'all']  # Nur Sättel sind relevant
        ]
    
    def get_delivery_problem_scenarios(self, day: int) -> list[DeliveryProblemScenario]:
        """Gibt aktive Lieferproblem-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, DeliveryProblemScenario)
        ]

