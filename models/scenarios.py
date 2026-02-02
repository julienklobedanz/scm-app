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
    """Marketingaktion: Erhöht die Nachfrage um einen absoluten Gesamtbedarf für den Zeitraum (wird auf Arbeitstage verteilt)"""
    additional_demand_total: float = 0.0  # Zusätzlicher Bedarf gesamt für den Zeitraum (Stück)
    workdays_in_period: int = 1  # Anzahl Arbeitstage im Zeitraum (für Verteilung: pro Tag = total / workdays_in_period)
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
class DelayScenario(Scenario):
    """Verspätung bei einem Logistik-Zwischenstopp: Verschiebt alle nachfolgenden Schritte"""
    delay_days: int = 0  # Verspätung in Tagen
    delay_stage: str = "truck_china_arrival"  # Zwischenstopp: "truck_china_arrival", "ship_arrival", "truck_de_arrival"
    component_type: str = "saddles"  # Immer Sättel


@dataclass
class WaterDamageScenario(Scenario):
    """Wasserschaden im Materiallager: Reduziert Bestand abends pro Satteltyp (optional absoluter Verlust)"""
    damage_date: int = -1  # Exaktes Datum (start_day = end_day = damage_date), -1 = nicht gesetzt
    affected_component: str = "saddles"  # Immer Sättel
    loss_quantity_absolute: float = 0.0  # Verlustmenge pro betroffener Satteltyp (für Rückwärtskompatibilität). 0 = kein Abzug. >0: Verlust = min(Eingabe, Bestand abends)
    affected_saddles: Optional[List[str]] = None  # None oder leer = alle 4 Satteltypen; sonst nur diese Satteltypen
    loss_by_saddle: Optional[Dict[str, int]] = None  # Pro-Satteltyp Verlustmengen (Stück, Integer). Wenn gesetzt, wird dies verwendet statt loss_quantity_absolute


@dataclass
class CargoLossScenario(Scenario):
    """Ladungsverlust auf See: Verliert die gesamte Ladung einer Lieferung"""
    loss_date: int = -1  # Exaktes Datum (start_day = end_day = loss_date), -1 = nicht gesetzt
    component_type: str = "saddles"  # Immer Sättel


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
    
    def get_delay_scenarios(self, day: int) -> list[DelayScenario]:
        """Gibt aktive Verspätungs-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, DelayScenario)
        ]
    
    def get_water_damage_scenarios(self, day: int) -> list[WaterDamageScenario]:
        """Gibt aktive Wasserschaden-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, WaterDamageScenario)
        ]
    
    def get_cargo_loss_scenarios(self, day: int) -> list[CargoLossScenario]:
        """Gibt aktive Ladungsverlust-Szenarien zurück"""
        return [
            s for s in self.get_active_scenarios(day)
            if isinstance(s, CargoLossScenario)
        ]

    def get_is_last_workday_of_marketing_period(self, day: int, workday_calculator) -> bool:
        """
        Prüft, ob day der letzte Arbeitstag mindestens eines aktiven Marketing-Zeitraums ist.
        Wird für Carry-Over des Marketing-Zusatzbedarfs benötigt (Rest am letzten Kampagnentag aufrunden).
        """
        for s in self.scenarios:
            if not isinstance(s, MarketingCampaignScenario) or not s.active:
                continue
            if day < s.start_day or day > s.end_day:
                continue
            # Letzter Arbeitstag im Zeitraum [start_day, end_day]
            last_workday = s.end_day
            while last_workday >= s.start_day and not workday_calculator.is_workday(last_workday):
                last_workday -= 1
            if last_workday >= s.start_day and day == last_workday:
                return True
        return False

