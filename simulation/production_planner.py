"""
Production Planner
Intelligenter Produktionsplaner mit Backlog-Tracking und Priorisierung
"""

import math
from typing import Dict, Tuple, Optional
from datetime import datetime
from models.inventory import Inventory
from config.master_data import MasterData
from simulation.demand_calculator import DemandCalculator
from simulation.workday_calculator import WorkdayCalculator


class ProductionPlanner:
    """Plant Produktion basierend auf Bottleneck-Logik, Priorisierung und Backlog-Tracking"""
    
    def __init__(
        self, 
        inventory: Inventory,
        demand_calculator: Optional[DemandCalculator] = None,
        workday_calculator: Optional[WorkdayCalculator] = None,
        china_transport_manager = None
    ):
        self.inventory = inventory
        self.master_data = MasterData
        self.demand_calculator = demand_calculator
        self.workday_calculator = workday_calculator
        self.china_transport_manager = china_transport_manager  # Für Inbound-Tabelle-Zugriff
        
        # Gedächtnis: Backlog pro Produkt
        self.backlog: Dict[str, float] = {product: 0.0 for product in self.master_data.BOM.keys()}
        
        # Produktionsplan: Dict[day, Dict[product, quantity]]
        self.production_plan: Dict[int, Dict[str, int]] = {}
        
        # Produktionslogs für UI: Dict[product, List[Dict]]
        self.production_logs: Dict[str, list] = {product: [] for product in self.master_data.BOM.keys()}
        
        # Cache für Inbound-Tabelle (Performance-Optimierung)
        # Key: day, Value: Dict[saddle_name, stock_morning]
        self._inbound_stock_cache: Dict[int, Dict[str, float]] = {}
        
        # Kumulierter Verbrauch pro Sattel-Typ (für Bestandsreduktion in UI)
        # Key: saddle_name, Value: kumulierter Verbrauch bis Tag X
        self._consumption_by_saddle: Dict[str, float] = {}
    
    def plan_daily_production(
        self, 
        day: int,
        marketing_add_ons: Dict[str, float] = None,
        scenario_manager = None
    ) -> Dict[str, int]:
        """
        Plant die tägliche Produktion mit intelligenter Priorisierung.
        
        Args:
            day: Tag (0-basiert)
            marketing_add_ons: Optional dict mit Marketing-Add-ons pro Produkt
            scenario_manager: Optional ScenarioManager für Marketing-Szenarien
        
        Returns:
            Dict[product_name, quantity] - Produktionsplan für diesen Tag
        """
        if marketing_add_ons is None:
            marketing_add_ons = {}
        
        # Prüfe ob Arbeitstag (nicht Wochenende und nicht Feiertag)
        is_workday = False
        if self.workday_calculator:
            is_workday = self.workday_calculator.is_workday(day)
        
        if not is_workday:
            # Keine Produktion an Wochenenden oder Feiertagen
            production_by_product = {product: 0 for product in self.master_data.BOM.keys()}
            self.production_plan[day] = production_by_product
            # Logge mit leeren Werten für Wochenende/Feiertag
            empty_zeros = {product: 0 for product in self.master_data.BOM.keys()}
            empty_floats = {product: 0.0 for product in self.master_data.BOM.keys()}
            self._log_production(day, production_by_product, empty_zeros, empty_floats, empty_floats, empty_zeros, 0, 0.0)
            return production_by_product
        
        # 1. Hole Tagesbedarf pro Produkt vom DemandCalculator
        product_demands = {}
        if self.demand_calculator:
            is_last_workday_of_year = False
            if self.workday_calculator.is_workday(day):
                has_future_workdays = False
                for future_day in range(day + 1, 365):
                    if self.workday_calculator.is_workday(future_day):
                        has_future_workdays = True
                        break
                is_last_workday_of_year = not has_future_workdays
            
            product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
                day, marketing_add_ons, is_last_workday_of_year
            )
        else:
            # Fallback
            total_share = sum(self.master_data.PRODUCT_SALES_SHARES.values())
            estimated_daily_target = self.master_data.GLOBAL_CONFIG.get('total_volume', 370000) / 365
            for product in self.master_data.BOM.keys():
                share = self.master_data.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share if total_share > 0 else 0
                product_demands[product] = int(estimated_daily_target * share)
        
        # 2. Addiere Backlog zum Bedarf
        production_demand_by_product = {}
        for product in self.master_data.BOM.keys():
            planned_demand = product_demands.get(product, 0)
            backlog = self.backlog.get(product, 0.0)
            production_demand_by_product[product] = planned_demand + backlog
        
        # 3. Berechne verfügbare Kapazität
        working_hours = self.master_data.GLOBAL_CONFIG.get('working_hours_per_shift', 8)
        capacity_per_hour = self.master_data.GLOBAL_CONFIG.get('capacity_per_hour', 130)
        capacity_per_shift = working_hours * capacity_per_hour
        
        # AGGRESSIVE BACKLOG-RECOVERY: Berechne benötigte Schichten basierend auf Gesamtbedarf (inkl. Backlog!)
        total_demand = sum(production_demand_by_product.values())
        total_backlog = sum(self.backlog.values())
        
        if total_demand > 0:
            # AGGRESSIVE BACKLOG-RECOVERY: Wenn Backlog vorhanden ist, nutze IMMER MAXIMALE Kapazität (3 Schichten)
            if total_backlog > 0:
                # Aggressive Strategie: Fahre IMMER 3 Schichten, wenn Backlog vorhanden ist
                # Dies stellt sicher, dass der Backlog so schnell wie möglich abgearbeitet wird
                shifts = 3  # Maximale Kapazität für Backlog-Aufholung
            else:
                # Normal: Berechne Schichten basierend auf Bedarf
                shifts_needed = math.ceil(total_demand / capacity_per_shift)
                shifts = min(3, max(1, shifts_needed))
        else:
            shifts = 0
        
        daily_capacity = shifts * capacity_per_shift
        
        # 4. Initialisiere Materialverfügbarkeit: VOLLER POOL-BESTAND (nicht aufgeteilt!)
        # Der Simulator führt alle Sättel als einen Pool 'stock_saddles'
        # Wir verwenden den vollen Bestand und ziehen dynamisch ab (First Come, First Served nach Priorität)
        current_saddle_stock = max(0.0, self.inventory.stock_saddles)  # Stelle sicher, dass nie negativ
        stock_saddles_morning = current_saddle_stock  # Speichere für Anzeige (Bestand zu Beginn des Tages)
        
        # KRITISCH: Berechne tatsächlichen Bestand pro Sattel-Typ (für Materialprüfung)
        # Dies ist wichtig, damit die Produktion nur stattfindet, wenn genug Material des spezifischen Typs vorhanden ist
        saddle_shares = self.master_data.calculate_saddle_shares()
        
        # Hole tatsächlichen Bestand pro Sattel-Typ aus Inbound-Tabelle (mit Verbrauch)
        stock_by_saddle_type = {}
        if self.china_transport_manager and self.workday_calculator:
            # Hole Bestand aus Inbound-Tabelle
            inbound_stocks = self._get_all_stocks_from_inbound_table(day, saddle_shares)
            # Ziehe kumulierten Verbrauch ab
            for s_type in saddle_shares.keys():
                inbound_stock = inbound_stocks.get(s_type, 0.0) or 0.0
                consumption = self._consumption_by_saddle.get(s_type, 0.0)
                stock_by_saddle_type[s_type] = max(0.0, inbound_stock - consumption)
        else:
            # Fallback: Proportionale Aufteilung des Pool-Bestands
            for s_type, share in saddle_shares.items():
                stock_by_saddle_type[s_type] = current_saddle_stock * share
        
        # Geschätzter Bestand pro Sattel-Typ (für Priorisierung)
        estimated_saddles_by_type = stock_by_saddle_type.copy()

        # 5. Priorisierung (Excel-Logik)
        products_list = list(self.master_data.BOM.keys())
        rank_support_by_product = {}
        for idx, product in enumerate(products_list):
            row_number = idx + 1
            # Materialverfügbarkeit (geschätzter Wert für Priorisierung)
            s_type = self.master_data.BOM[product]['saddle']
            material_avail = estimated_saddles_by_type.get(s_type, 0.0)
            
            # Excel: =ZEILE()/1000000 + Verfügbarkeit
            # Höhere Verfügbarkeit -> Höherer Wert -> Besserer Rang?
            # RANG.GLEICH in Excel (Standard ist absteigend): Höchster Wert = Rang 1.
            rank_support = (row_number / 1000000.0) + material_avail
            rank_support_by_product[product] = rank_support
        
        # Sortiere Produkte nach Rang (Höchster Support-Wert zuerst)
        # Wir simulieren RANG.GLEICH absteigend -> Sortierung: High to Low
        sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
        
        # Berechne Rangnummer für Reporting
        rank_by_product = {}
        for i, p in enumerate(sorted_products):
            rank_by_product[p] = i + 1

        # 6. Produktion verteilen (Water-Filling Algorithmus mit dynamischem Pool)
        production_by_product = {product: 0 for product in products_list}
        remaining_capacity = daily_capacity
        
        # Speichere Bestand pro Produkt für Anzeige (zu Beginn der Iteration)
        material_availability_report = {}
        
        # Iteriere nach Priorität
        for product in sorted_products:
            if remaining_capacity <= 0:
                # Keine Kapazität mehr, aber speichere trotzdem den Bestand für Anzeige
                material_availability_report[product] = current_saddle_stock
                continue
                
            demand = production_demand_by_product[product]
            if demand <= 0:
                # Kein Bedarf, aber speichere trotzdem den Bestand für Anzeige
                material_availability_report[product] = current_saddle_stock
                continue
            
            # KRITISCH: Material-Check für spezifischen Sattel-Typ!
            # Jedes Produkt benötigt einen spezifischen Satteltyp, nicht den Pool-Bestand
            required_saddle_type = self.master_data.BOM[product]['saddle']
            available_stock_for_saddle = stock_by_saddle_type.get(required_saddle_type, 0.0)
            
            # Material-Limit: Verfügbarer Bestand des spezifischen Satteltyps
            # WICHTIG: Wenn kein Material des spezifischen Typs vorhanden ist, kann nichts produziert werden!
            material_limit = max(0.0, available_stock_for_saddle)
            
            # Wieviel können wir bauen? (Minimum aus Bedarf, Kapazität, Material)
            # Wir runden Material ab, da man keine halben Sättel verbauen kann
            can_produce = min(demand, remaining_capacity, int(material_limit))
            
            # KRITISCH: Stelle sicher, dass can_produce nie negativ ist
            can_produce = max(0, can_produce)
            
            # KRITISCH: Aktualisiere Bestand pro Sattel-Typ (nicht nur Pool-Bestand!)
            # Ziehe verbrauchtes Material vom spezifischen Satteltyp ab
            if can_produce > 0:
                stock_by_saddle_type[required_saddle_type] = max(0.0, stock_by_saddle_type[required_saddle_type] - can_produce)
            
            # Produziere
            production_by_product[product] = int(can_produce)
            
            # Ziehe Ressourcen ab (dynamisch aus dem Pool)
            # WICHTIG: Nur abziehen, wenn tatsächlich produziert wurde
            remaining_capacity -= can_produce
            # Aktualisiere Pool-Bestand (für nachfolgende Produkte)
            current_saddle_stock = max(0.0, current_saddle_stock - can_produce)  # Stelle sicher, dass nie negativ wird
            
            # Speichere Bestand für Anzeige (zu Beginn der Iteration, VOR Produktion)
            material_availability_report[product] = material_limit
        
        # Stelle sicher, dass alle Produkte einen Eintrag haben (auch wenn sie nicht produziert wurden)
        for product in products_list:
            if product not in material_availability_report:
                material_availability_report[product] = current_saddle_stock
        
        # 7. Aktualisiere Backlog (AGGRESSIVE BACKLOG-RECOVERY)
        # Backlog = (Tagesbedarf + Alter Backlog) - Tatsächlich Produziert
        # Dies stellt sicher, dass der Backlog korrekt nachgehalten wird
        for product in self.master_data.BOM.keys():
            # Tagesbedarf (ohne Backlog)
            daily_target = product_demands.get(product, 0)
            # Alter Backlog
            old_backlog = self.backlog.get(product, 0.0)
            # Gesamtziel (Tagesbedarf + Backlog)
            total_target = daily_target + old_backlog
            # Tatsächlich produziert
            produced = production_by_product.get(product, 0)
            # Neuer Backlog = Gesamtziel - Produziert
            self.backlog[product] = max(0.0, total_target - produced)
        
        # 8. Speichere Produktionsplan
        self.production_plan[day] = production_by_product
        
        # 9. Logge für UI
        self._log_production(
            day, 
            production_by_product,
            product_demands,
            production_demand_by_product,
            material_availability_report, # Start-Verfügbarkeit
            rank_by_product,
            shifts,
            daily_capacity,
            stock_saddles_morning  # Bestand zu Beginn des Tages (für proportionale Anzeige)
        )
        
        return production_by_product
    
    def _log_production(
        self,
        day: int,
        production_by_product: Dict[str, int],
        product_demands: Dict[str, int],
        production_demand_by_product: Dict[str, float],
        material_availability_by_product: Dict[str, float],
        rank_by_product: Dict[str, int],
        shifts: int,
        daily_capacity: float,
        stock_saddles_morning: float = None
    ) -> None:
        """Loggt Produktionsdaten für UI-Anzeige"""
        if not self.workday_calculator:
            return
        
        current_date = self.workday_calculator.get_date_from_day(day)
        # Hole alle Tag-Informationen auf einmal
        day_info = self.workday_calculator.get_day_info(day) if self.workday_calculator else {
            'weekday_name': 'Unbekannt',
            'weekday_abbr': '??',
            'is_workday': False,
            'is_weekend': False,
            'is_holiday': False
        }
        weekday_name = day_info['weekday_name']
        is_workday = day_info['is_workday']
        is_holiday = day_info['is_holiday']
        is_weekend = day_info['is_weekend']
        
        actual_build_total = sum(production_by_product.values())
        utilization = (actual_build_total / daily_capacity * 100) if daily_capacity > 0 else 0
        
        # Berechne Sattel-Shares für proportionale Anzeige (konsistent mit Materiallager)
        saddle_shares = self.master_data.calculate_saddle_shares()
        
        # OPTIMIERUNG: Berechne Bestände für alle Sattel-Typen auf einmal (Caching)
        # Dies vermeidet mehrfache Berechnung der Inbound-Tabelle
        stock_by_saddle = self._get_all_stocks_from_inbound_table(day, saddle_shares)
        
        # Hole fertiggestellte PM vom vorherigen ARBEITSTAG (für alle Produkte)
        # WICHTIG: Dies muss VOR der Aktualisierung des Verbrauchs passieren,
        # damit wir die fertiggestellte PM vom vorherigen Tag haben
        # WICHTIG: Fertiggestellte PM wird nur angezeigt, wenn der vorherige Tag ein Arbeitstag war
        finished_pm_by_product = {}
        if day > 0 and self.workday_calculator:
            prev_day = day - 1
            # Prüfe, ob der vorherige Tag ein Arbeitstag war
            if self.workday_calculator.is_workday(prev_day):
                # Vorheriger Tag war ein Arbeitstag: Hole tatsächliche PM vom vorherigen Tag
                for product in self.master_data.BOM.keys():
                    prev_logs = self.production_logs.get(product, [])
                    if prev_logs and len(prev_logs) > 0:
                        # Letzter Eintrag = vorheriger Tag (da wir täglich loggen)
                        finished_pm_by_product[product] = prev_logs[-1].get('tatsächliche PM', 0)
                    else:
                        finished_pm_by_product[product] = 0
            else:
                # Vorheriger Tag war kein Arbeitstag: Finde den letzten Arbeitstag
                prev_workday = prev_day
                while prev_workday >= 0 and not self.workday_calculator.is_workday(prev_workday):
                    prev_workday -= 1
                
                if prev_workday >= 0:
                    # Suche den Log-Eintrag für den letzten Arbeitstag
                    for product in self.master_data.BOM.keys():
                        prev_logs = self.production_logs.get(product, [])
                        # Durchsuche Logs rückwärts, um den Eintrag für prev_workday zu finden
                        found = False
                        for log_entry in reversed(prev_logs):
                            log_date_str = log_entry.get('Datum', '')
                            if log_date_str:
                                try:
                                    from datetime import datetime
                                    log_date = datetime.strptime(log_date_str, self.master_data.DATE_FORMAT).date()
                                    log_day = (log_date - self.workday_calculator.get_date_from_day(0)).days
                                    if log_day == prev_workday:
                                        finished_pm_by_product[product] = log_entry.get('tatsächliche PM', 0)
                                        found = True
                                        break
                                except (ValueError, TypeError):
                                    pass
                        if not found:
                            finished_pm_by_product[product] = 0
                else:
                    # Kein vorheriger Arbeitstag gefunden
                    for product in self.master_data.BOM.keys():
                        finished_pm_by_product[product] = 0
        else:
            # Tag 0 oder kein WorkdayCalculator: keine fertiggestellte PM (noch nichts produziert)
            for product in self.master_data.BOM.keys():
                finished_pm_by_product[product] = 0
        
        # Berechne Bestand morgens (vor der Produktion)
        # Bestand morgens = Inbound-Bestand - kumulierter Verbrauch bis zum VORHERIGEN Tag
        # (Der Verbrauch des aktuellen Tages wird später hinzugefügt)
        stock_morning_by_saddle = {}
        for saddle_name in saddle_shares.keys():
            inbound_stock = stock_by_saddle.get(saddle_name, 0.0) or 0.0
            # Verbrauch bis zum VORHERIGEN Tag (noch ohne heutige Produktion)
            consumption_before_today = self._consumption_by_saddle.get(saddle_name, 0.0)
            stock_morning_by_saddle[saddle_name] = max(0.0, inbound_stock - consumption_before_today)
        
        # Aktualisiere kumulierten Verbrauch pro Sattel-Typ (NACH der Bestandsberechnung)
        # WICHTIG: Dies passiert NACH dem Berechnen des Bestands morgens,
        # damit der Bestand morgens den Verbrauch bis zum VORHERIGEN Tag zeigt
        for product, qty in production_by_product.items():
            if qty > 0:
                saddle_name = self.master_data.BOM[product]['saddle']
                self._consumption_by_saddle[saddle_name] = self._consumption_by_saddle.get(saddle_name, 0.0) + float(qty)
        
        for product in self.master_data.BOM.keys():
            frame_name = self.master_data.BOM[product]['frame']
            saddle_name = self.master_data.BOM[product]['saddle']
            fork_name = self.master_data.BOM[product]['fork']
            
            # Verfügbarkeit für Anzeige: Hole Bestand morgens (vor der Produktion)
            stock_saddle_specific = stock_morning_by_saddle.get(saddle_name)
            
            # Fallback: Wenn Inbound-Tabelle nicht verfügbar, verwende proportionale Aufteilung
            if stock_saddle_specific is None:
                if stock_saddles_morning is None:
                    stock_saddles_morning = 0.0
                    for p in self.master_data.BOM.keys():
                        if p in material_availability_by_product:
                            stock_saddles_morning = material_availability_by_product[p]
                            break
                saddle_share = saddle_shares.get(saddle_name, 0.0)
                stock_saddle_specific = stock_saddles_morning * saddle_share
                # Ziehe auch hier den Verbrauch bis zum VORHERIGEN Tag ab
                consumption_before_today = self._consumption_by_saddle.get(saddle_name, 0.0)
                stock_saddle_specific = max(0.0, stock_saddle_specific - consumption_before_today)
            
            materials_complete = 'Ja' if stock_saddle_specific > 0 else 'Nein'
            
            planned_pm = product_demands.get(product, 0)
            actual_qty = production_by_product.get(product, 0)
            # WICHTIG: Fertiggestellte PM nur anzeigen, wenn der aktuelle Tag ein Arbeitstag ist
            # An Wochenenden/Feiertagen wird keine fertiggestellte PM angezeigt
            if is_workday:
                finished_pm = finished_pm_by_product.get(product, 0)
            else:
                finished_pm = 0
            backlog = self.backlog.get(product, 0.0)
            
            log_entry = {
                'Wochentag': day_info['weekday_abbr'],
                'Datum': current_date.strftime(self.master_data.DATE_FORMAT),
                'Schichtanzahl': shifts,
                'Auslastung (%)': int(round(utilization)) if abs(utilization) < 0.05 else round(utilization, 1),
                'Materialien vollständig?': materials_complete,
                frame_name: '∞',
                saddle_name: int(round(stock_saddle_specific)) if stock_saddle_specific > 0 else 0,
                fork_name: '∞',
                'geplante PM': int(round(planned_pm)),
                'tatsächliche PM': int(round(actual_qty)),
                'fertiggestellte PM': int(round(finished_pm, 0)),
                'Backlog': int(round(backlog, 0)),
                '_Produktionsbedarf': production_demand_by_product.get(product, 0),
                '_Rang': rank_by_product.get(product, 0),
                'Is_Weekend': is_weekend,
                'Is_Holiday': is_holiday
            }
            
            self.production_logs[product].append(log_entry)
    
    def _get_all_stocks_from_inbound_table(self, day: int, saddle_shares: Dict[str, float]) -> Dict[str, float]:
        """
        Holt die Bestände für ALLE Sattel-Typen für einen bestimmten Tag aus der Inbound-Tabelle.
        
        OPTIMIERUNG: Berechnet die Inbound-Tabelle nur einmal pro Tag und cached das Ergebnis.
        Dies vermeidet mehrfache Berechnung (8 Produkte = 8x Aufruf).
        
        Args:
            day: Tag-Index (0-basiert, 0 = 01.01.2026)
            saddle_shares: Dictionary mit Sattel-Shares (für get_inbound_log_dataframe)
            
        Returns:
            Dictionary mit Beständen pro Sattel-Typ: {saddle_name: stock_morning}
        """
        # Prüfe Cache
        if day in self._inbound_stock_cache:
            return self._inbound_stock_cache[day]
        
        # Initialisiere Ergebnis-Dictionary
        stock_by_saddle = {saddle_name: None for saddle_name in saddle_shares.keys()}
        
        if not self.china_transport_manager or not self.workday_calculator:
            # Cache leeres Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
        
        try:
            # Hole Inbound-Tabelle (NUR EINMAL pro Tag!)
            inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
            
            if inbound_df.empty:
                # Cache leeres Ergebnis
                self._inbound_stock_cache[day] = stock_by_saddle
                return stock_by_saddle
            
            # Konvertiere Tag-Index zu Datum
            target_date = self.workday_calculator.get_date_from_day(day)
            
            # Berechne Bestand morgens für ALLE Sattel-Typen auf einmal
            # Bestand morgens = Summe aller Verfügbar <= target_date
            for saddle_name in saddle_shares.keys():
                stock_morning = 0.0
                
                for _, row in inbound_df.iterrows():
                    avail_str = row.get('Verfügbar im Lager', '')
                    if avail_str and isinstance(avail_str, str) and len(avail_str.strip()) > 0:
                        try:
                            avail_date = datetime.strptime(avail_str, self.master_data.DATE_FORMAT).date()
                            
                            if avail_date <= target_date:
                                qty_val = row.get(saddle_name, 0)
                                if qty_val and str(qty_val).strip() != '':
                                    try:
                                        stock_morning += float(qty_val)
                                    except (ValueError, TypeError):
                                        pass
                        except (ValueError, TypeError):
                            continue
                
                stock_by_saddle[saddle_name] = stock_morning if stock_morning > 0 else None
            
            # Cache Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
            
        except Exception:
            # Bei Fehler: Cache leeres Ergebnis
            self._inbound_stock_cache[day] = stock_by_saddle
            return stock_by_saddle
    
    def get_consumed_components(self, production_by_product: Dict[str, int]) -> Dict[str, float]:
        consumed = {'frames_alu': 0.0, 'frames_carbon': 0.0, 'saddles': 0.0}
        for product, qty in production_by_product.items():
            if qty > 0 and product in self.master_data.BOM:
                consumed['saddles'] += float(qty)
                frame_type = self.master_data.BOM[product]['frame']
                frame_category = self.master_data.get_frame_category(frame_type)
                consumed[f'frames_{frame_category.lower()}'] += float(qty)
        return consumed
    
    def consume_components(self, consumed: Dict[str, float]) -> None:
        """Verbraucht Komponenten aus dem Lager"""
        self.inventory.stock_alu -= consumed['frames_alu']
        self.inventory.stock_carbon -= consumed['frames_carbon']
        # WICHTIG: Stelle sicher, dass stock_saddles nie negativ wird
        # Wenn mehr verbraucht wird als vorhanden, setze auf 0
        # Dies verhindert "Geisterproduktion" ohne Material
        self.inventory.stock_saddles = max(0.0, self.inventory.stock_saddles - consumed['saddles'])
    
    def check_stoppage(
        self,
        daily_target: float,
        frame_demand: Dict[str, float],
        saddle_demand: float
    ) -> Tuple[bool, bool]:
        """
        Prüft ob Produktion wegen fehlender Komponenten gestoppt ist
        
        Returns:
            (stopped_frames, stopped_saddles)
        """
        if daily_target == 0:
            return False, False
        
        # WICHTIG: Rahmen sind unbegrenzt verfügbar, daher nie gestoppt
        stopped_frames = False
        
        # Prüfe ob genug Sättel vorhanden sind
        needed_saddles = saddle_demand
        available_saddles = self.inventory.stock_saddles
        
        stopped_saddles = available_saddles < needed_saddles
        
        return stopped_frames, stopped_saddles
