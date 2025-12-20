"""
China Transport Manager
Simuliert den detaillierten Transport von China nach Deutschland
"""

from typing import Dict, List, Tuple, Optional
from datetime import date, timedelta
from models.inventory import Inventory
from simulation.workday_calculator import WorkdayCalculator
from config.master_data import MasterData
from models.scenarios import ScenarioManager, DeliveryProblemScenario


class ChinaTransportManager:
    """
    Verwaltet den Transport von China nach Deutschland mit detaillierter Logik:
    1. Produktion in China: 5 AT (Tag der Bestellung zählt NICHT)
    2. LKW zum Hafen (China): 2 AT
    3. Warten auf Mittwoch (Schiff fährt nur Mittwochs ab)
    4. Schiff: 30 KT (Kalendertage)
    5. LKW zum Werk (Deutschland): 2 AT
    6. Wareneingang: +1 Tag zwischen physischer Ankunft und Verfügbarkeit
    """
    
    def __init__(self, inventory: Inventory, workday_calculator: WorkdayCalculator, scenario_manager: Optional[ScenarioManager] = None):
        self.inventory = inventory
        self.workday_calculator = workday_calculator
        self.master_data = MasterData
        self.scenario_manager = scenario_manager
        
        # Transport-Status pro Bestellung
        # Key: (order_day, order_id), Value: Transport-Status
        self.transport_status: Dict[Tuple[int, int], Dict] = {}
        self.order_counter = 0
        
        # Kumulierte Bestellungen am Hafen (für Versandlogik: >= 500)
        # Key: arrival_at_port_day, Value: kumulierte Menge
        self.pending_shipments: Dict[int, float] = {}  # {arrival_at_port_day: cumulative_quantity}
    
    def place_order(self, order_day: int, quantity: float) -> int:
        """
        Platziert eine Bestellung in China
        
        Args:
            order_day: Tag der Bestellung (0-basiert)
            quantity: Bestellmenge
            
        Returns:
            order_id: Eindeutige Bestell-ID
        """
        self.order_counter += 1
        order_id = self.order_counter
        
        # Prüfe Produktionsprobleme beim Lieferanten (z.B. SupplierBreakdownScenario)
        # HINWEIS: Transportprobleme (DeliveryProblemScenario) werden erst beim Versand angewendet!
        # Hier nur Produktionsverluste berücksichtigen (falls vorhanden)
        production_loss_percentage = 0.0
        
        # Status initialisieren
        order_date = self.workday_calculator.get_date_from_day(order_day)
        
        # Schritt 1: Produktion in China (5 AT, Tag der Bestellung zählt NICHT)
        production_start_day = order_day
        production_end_day = self._add_workdays(production_start_day, 5, exclude_start=True)
        
        # Schritt 2: LKW zum Hafen (China) - 2 AT
        # HINWEIS: Verspätungen werden erst beim Versand (in process_shipments) angewendet
        truck_china_start_day = production_end_day
        truck_china_duration = 2
        truck_china_end_day = self._add_workdays(truck_china_start_day, truck_china_duration)
        
        # Schritt 3: Ankunft im Hafen
        arrival_at_port_day = truck_china_end_day
        
        # Speichere Bestellung für Versandlogik
        # Die Versandlogik sammelt alle Bestellungen, die im Hafen ankommen
        # und versendet, sobald kumulierte Menge >= 500 erreicht
        if arrival_at_port_day not in self.pending_shipments:
            self.pending_shipments[arrival_at_port_day] = 0.0
        self.pending_shipments[arrival_at_port_day] += quantity
        
        # Versandlogik wird später in process_shipments() behandelt
        # Hier speichern wir nur die Bestellung
        # ship_departure_day wird später berechnet, wenn >= 500 erreicht ist
        
        # Berechne tatsächliche Menge nach Produktionsverlusten (nicht Transportverluste!)
        # Transportverluste werden erst beim Versand in process_shipments() angewendet
        actual_quantity = quantity * (1.0 - production_loss_percentage)
        
        self.transport_status[(order_day, order_id)] = {
            'order_day': order_day,
            'order_id': order_id,
            'quantity': quantity,  # Ursprüngliche Menge
            'actual_quantity': actual_quantity,  # Menge nach Produktionsverlusten (vor Transportverlusten)
            'production_loss_percentage': production_loss_percentage,
            'production_start_day': production_start_day,
            'production_end_day': production_end_day,
            'truck_china_start_day': truck_china_start_day,
            'truck_china_end_day': truck_china_end_day,
            'arrival_at_port_day': arrival_at_port_day,
            'ship_departure_day': None,  # Wird später gesetzt, wenn Versand ausgelöst wird
            'ship_arrival_day': None,  # Wird später gesetzt
            'truck_de_start_day': None,  # Wird später gesetzt
            'truck_de_end_day': None,  # Wird später gesetzt
            'physical_arrival_day': None,  # Wird später gesetzt
            'available_day': None,  # Wird später gesetzt
            'received': False,
            'shipped': False  # Wurde bereits versandt?
        }
        
        return order_id
    
    def process_shipments(self, current_day: int) -> None:
        """
        Verarbeitet Versände: Sammelt ALLE Waren im Hafen (kumuliert) und verschifft, 
        sobald >= 500 erreicht sind. Es werden immer exakt 500 Stück verschickt (unabhängig vom Typ),
        sodass ein Restbestand beim Lieferanten übrig bleiben kann.
        Wird nur Mittwochs ausgeführt.
        
        Args:
            current_day: Aktueller Tag (0-basiert)
        """
        current_date = self.workday_calculator.get_date_from_day(current_day)
        
        # Prüfe nur an Mittwochen (Schiff fährt nur Mittwochs ab)
        if current_date.weekday() != 2:  # Mittwoch ist 2
            return
        
        lot_size = self.master_data.CHINA_SUPPLIER['Saddles']['lot_size']
        
        # 1. Sammle ALLES, was im Hafen liegt und wartet (Ankunft <= heute)
        # Sortiere nach Ankunftstag (älteste zuerst) für FIFO-Logik
        ready_to_ship_orders = []  # Liste von status-Objekten
        total_quantity_at_port = 0.0
        
        for (order_day, order_id), status in self.transport_status.items():
            if (status['arrival_at_port_day'] is not None and 
                status['arrival_at_port_day'] <= current_day and 
                not status['shipped']):
                ready_to_ship_orders.append(status)
                total_quantity_at_port += status['quantity']
        
        # Sortiere nach Ankunftstag (älteste zuerst) für FIFO-Logik
        ready_to_ship_orders.sort(key=lambda s: s['arrival_at_port_day'])
        
        # 2. Prüfe, ob die GESAMTSUMME für einen Container reicht (>= 500)
        if total_quantity_at_port >= lot_size:
            # Wir verschiffen immer exakt 500 Stück (nicht die gesamte Menge)
            ship_departure_day = current_day
            
            # Wende Lieferprobleme-Szenarien an (Transportprobleme: Container über Bord, Verspätung)
            delivery_problems = []
            if self.scenario_manager:
                delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(ship_departure_day)
            
            # Berechne Verspätung und Verlust aus Szenarien
            delay_days = 0
            loss_factor = 1.0
            for scenario in delivery_problems:
                if scenario.component_type == 'saddles':
                    delay_days = max(delay_days, scenario.delay_days)
                    loss_factor *= (1.0 - scenario.loss_percentage)
            
            # Schiffsdauer + LKW DE
            ship_arrival_day = ship_departure_day + 30 + delay_days
            truck_de_start_day = ship_arrival_day
            truck_de_end_day = self._add_workdays(truck_de_start_day, 2)
            physical_arrival_day = truck_de_end_day
            available_day = physical_arrival_day + 1
            
            # Verschiffe exakt 500 Stück (FIFO: älteste Bestellungen zuerst)
            remaining_to_ship = lot_size  # Exakt 500 Stück
            
            for status in ready_to_ship_orders:
                if remaining_to_ship <= 0:
                    break
                
                # Berechne, wie viel von dieser Bestellung verschickt wird
                quantity_to_ship_from_order = min(remaining_to_ship, status['quantity'])
                
                # Wenn die gesamte Bestellung verschickt wird
                if quantity_to_ship_from_order >= status['quantity']:
                    # Update Status - gesamte Bestellung wird verschickt
                    status['ship_departure_day'] = ship_departure_day
                    status['ship_arrival_day'] = ship_arrival_day
                    status['truck_de_start_day'] = truck_de_start_day
                    status['truck_de_end_day'] = truck_de_end_day
                    status['physical_arrival_day'] = physical_arrival_day
                    status['available_day'] = available_day
                    status['shipped'] = True
                    status['shipped_quantity'] = status['quantity']  # Gesamte Menge
                    
                    # Verlust anwenden (Container-Verlust passiert auf See)
                    status['actual_quantity'] = status['actual_quantity'] * loss_factor
                    
                    remaining_to_ship -= status['quantity']
                else:
                    # Nur ein Teil der Bestellung wird verschickt
                    # Erstelle einen neuen Status für den verschickten Teil
                    # Der Rest bleibt im Hafen
                    shipped_status = status.copy()
                    shipped_status['shipped_quantity'] = quantity_to_ship_from_order
                    shipped_status['ship_departure_day'] = ship_departure_day
                    shipped_status['ship_arrival_day'] = ship_arrival_day
                    shipped_status['truck_de_start_day'] = truck_de_start_day
                    shipped_status['truck_de_end_day'] = truck_de_end_day
                    shipped_status['physical_arrival_day'] = physical_arrival_day
                    shipped_status['available_day'] = available_day
                    shipped_status['shipped'] = True
                    
                    # Verlust anwenden
                    # Anteilig: nur der verschickte Teil hat Verlust
                    shipped_ratio = quantity_to_ship_from_order / status['quantity']
                    shipped_status['actual_quantity'] = status['actual_quantity'] * shipped_ratio * loss_factor
                    
                    # Aktualisiere die ursprüngliche Bestellung: Reduziere Menge um verschickten Teil
                    status['quantity'] -= quantity_to_ship_from_order
                    status['actual_quantity'] = status['actual_quantity'] * (1.0 - shipped_ratio)
                    # Diese Bestellung bleibt im Hafen (shipped = False)
                    
                    # Speichere den verschickten Teil als neue Bestellung
                    new_order_id = self.order_counter + 1
                    self.order_counter += 1
                    self.transport_status[(status['order_day'], new_order_id)] = shipped_status
                    
                    remaining_to_ship -= quantity_to_ship_from_order
            
            # Aktualisiere pending_shipments: Reduziere um 500
            # Finde alle betroffenen arrival_days und reduziere entsprechend
            shipped_quantity_total = lot_size  # Exakt 500
            for arrival_day in sorted(set(s['arrival_at_port_day'] for s in ready_to_ship_orders)):
                if arrival_day in self.pending_shipments and shipped_quantity_total > 0:
                    reduction = min(self.pending_shipments[arrival_day], shipped_quantity_total)
                    self.pending_shipments[arrival_day] -= reduction
                    shipped_quantity_total -= reduction
                    if self.pending_shipments[arrival_day] <= 0:
                        del self.pending_shipments[arrival_day]
    
    def receive_orders(self, current_day: int) -> float:
        """
        Empfängt Bestellungen, die heute verfügbar werden
        
        Args:
            current_day: Aktueller Tag (0-basiert)
            
        Returns:
            Gesamtmenge der heute verfügbaren Bestellungen (nach Verlust)
        """
        # Zuerst Versände verarbeiten (falls Mittwoch)
        self.process_shipments(current_day)
        
        total_received = 0.0
        
        for key, status in list(self.transport_status.items()):
            if not status['received'] and status['available_day'] == current_day:
                # Verwende actual_quantity (bereits Verlust angewendet)
                # Wenn shipped_quantity vorhanden, bedeutet das, dass nur ein Teil verschickt wurde
                # In diesem Fall ist actual_quantity bereits der verschickte Teil (nach Verlust)
                if 'shipped_quantity' in status and status['shipped_quantity'] is not None:
                    # Nur der verschickte Teil kommt an
                    # actual_quantity ist bereits der verschickte Teil nach Verlust
                    received_qty = status['actual_quantity']
                else:
                    # Gesamte Bestellung wurde verschickt
                    received_qty = status['actual_quantity']
                
                total_received += received_qty
                status['received'] = True
        
        return total_received
    
    def _add_workdays(self, start_day: int, num_workdays: int, exclude_start: bool = False) -> int:
        """
        Fügt Arbeitstage hinzu (Mo-Fr)
        
        Args:
            start_day: Start-Tag (0-basiert)
            num_workdays: Anzahl Arbeitstage
            exclude_start: Wenn True, zählt der Start-Tag nicht mit
            
        Returns:
            End-Tag (0-basiert)
        """
        current_day = start_day
        if exclude_start:
            current_day += 1
        
        workdays_added = 0
        
        while workdays_added < num_workdays:
            if self.workday_calculator.is_workday(current_day):
                workdays_added += 1
            current_day += 1
        
        return current_day - 1  # -1 weil wir am Ende des letzten Arbeitstages sind
    
    def _get_next_wednesday(self, arrival_day: int) -> int:
        """
        Findet den nächsten Mittwoch für Schiffsabfahrt.
        Regel: Ware muss VOR Mittwoch im Hafen sein. Kommt sie am Mittwoch oder früher an, 
        fährt das Schiff am selben Mittwoch. Kommt sie später an, muss sie bis zum nächsten Mittwoch warten.
        
        Args:
            arrival_day: Tag der Ankunft im Hafen (0-basiert)
            
        Returns:
            Tag der Schiffsabfahrt (0-basiert)
        """
        arrival_date = self.workday_calculator.get_date_from_day(arrival_day)
        arrival_weekday = arrival_date.weekday()  # 0=Montag, 2=Mittwoch, 6=Sonntag
        
        # Wenn Ankunft am Mittwoch oder früher (Mo, Di, Mi): Schiff fährt am selben Mittwoch
        if arrival_weekday <= 2:  # Montag, Dienstag oder Mittwoch
            # Finde den Mittwoch dieser Woche
            days_to_wednesday = 2 - arrival_weekday
            departure_date = arrival_date + timedelta(days=days_to_wednesday)
        else:  # Donnerstag, Freitag, Samstag, Sonntag
            # Finde den nächsten Mittwoch
            days_until_next_wednesday = (9 - arrival_weekday) % 7  # Tage bis nächster Mittwoch
            if days_until_next_wednesday == 0:
                days_until_next_wednesday = 7
            departure_date = arrival_date + timedelta(days=days_until_next_wednesday)
        
        departure_day = (departure_date - date(2027, 1, 1)).days
        return departure_day
    
    def get_transport_status_for_day(self, day: int) -> List[Dict]:
        """
        Gibt alle Transport-Status für einen bestimmten Tag zurück
        
        Args:
            day: Tag (0-basiert)
            
        Returns:
            Liste von Transport-Status-Dictionaries
        """
        result = []
        for key, status in self.transport_status.items():
            if status['available_day'] is not None and status['order_day'] <= day <= status['available_day']:
                result.append(status.copy())
        return result
    
    def get_pipeline_inventory(self) -> float:
        """
        Gibt die Summe aller Sättel zurück, die bestellt, aber noch nicht empfangen wurden.
        Dies ist der "Pipeline-Bestand" (Ware unterwegs).
        
        Returns:
            Gesamtmenge der unterwegs befindlichen Sättel
        """
        total_pipeline = 0.0
        for status in self.transport_status.values():
            if not status['received']:
                # Zähle alles, was noch nicht als 'received' markiert ist
                # Verwende actual_quantity (nach Produktionsverlusten, aber vor Transportverlusten)
                total_pipeline += status.get('actual_quantity', status.get('quantity', 0.0))
        return total_pipeline

