# UML-Klassendiagramm - Mermaid Version

Diese Datei kann direkt auf GitHub angezeigt werden (Mermaid wird nativ unterstützt).

```mermaid
classDiagram
    %% Simulation Package
    class Simulator {
        -float yearly_volume
        -MasterData master_data
        -ScenarioManager scenario_manager
        -Inventory inventory
        -MarketBacklog backlog
        -WorkdayCalculator workday_calculator
        -DemandCalculator demand_calculator
        -ChinaTransportManager china_transport_manager
        -ProductionPlanner production_planner
        -ProcurementManager procurement_manager
        +__init__(yearly_volume, initial_stock_*, scenario_manager)
        +run() DataFrame, Dict
        -_place_initial_orders()
        -_warmup_logistics()
        -_calculate_scor_metrics()
    }
    
    class DemandCalculator {
        -float yearly_volume
        -WorkdayCalculator workday_calculator
        -Dict product_remainders
        -Dict monthly_base_daily_float
        +__init__(yearly_volume, workday_calculator)
        +calculate_daily_demand_per_product() int
        +calculate_daily_demand_per_product_dict() Dict
        +aggregate_bom_demand() Tuple
    }
    
    class ProductionPlanner {
        -Inventory inventory
        -DemandCalculator demand_calculator
        -WorkdayCalculator workday_calculator
        -ChinaTransportManager china_transport_manager
        -Dict backlog
        -Dict production_plan
        -Dict production_logs
        +__init__(inventory, demand_calculator, workday_calculator, china_transport_manager)
        +plan_daily_production() Dict
        +get_production_logs() Dict
    }
    
    class ProcurementManager {
        -Inventory inventory
        -ChinaTransportManager china_transport_manager
        -WorkdayCalculator workday_calculator
        +__init__(inventory, china_transport_manager, workday_calculator)
        +process_procurement(day)
    }
    
    class ChinaTransportManager {
        -Inventory inventory
        -WorkdayCalculator workday_calculator
        -ScenarioManager scenario_manager
        -Dict port_buckets
        +__init__(inventory, workday_calculator, scenario_manager)
        +process_shipments(day)
        +get_supplier_log_dataframe() DataFrame
        +get_inbound_log_dataframe() DataFrame
    }
    
    class WorkdayCalculator {
        -int year
        -Dict holidays_de
        -Dict holidays_cn
        +__init__(year)
        +is_workday(day) bool
        +is_weekend(day) bool
        +get_date_from_day(day) date
    }
    
    %% Models Package
    class Inventory {
        +float stock_alu
        +float stock_carbon
        +float stock_saddles
        +add_stock(component_type, quantity)
        +remove_stock(component_type, quantity)
        +get_stock(component_type) float
    }
    
    class MarketBacklog {
        -Dict backlog
        -Dict in_transit
        +__init__()
        +initialize_markets(markets)
        +add_demand(day, market, product, quantity)
        +fulfill_demand(day, market, product, quantity)
        +get_backlog(day, market, product) float
    }
    
    class Scenario {
        <<abstract>>
        +str name
        +int start_day
        +int end_day
        +bool active
    }
    
    class MarketingCampaignScenario {
        +float demand_increase_factor
    }
    
    class WarehouseDamageScenario {
        +float stock_loss_percentage
        +str affected_component
    }
    
    class SupplierBreakdownScenario {
        +str component_type
    }
    
    class DeliveryProblemScenario {
        +float loss_percentage
        +int delay_days
        +str component_type
    }
    
    class StandardScenario {
        +str name
        +int start_day
        +int end_day
        +bool active
    }
    
    class ScenarioManager {
        -list scenarios
        -StandardScenario standard_scenario
        +__init__()
        +add_scenario(scenario)
        +get_active_scenarios(day) list
        +get_marketing_scenarios(day) list
        +get_warehouse_damage_scenarios(day) list
        +get_supplier_breakdown_scenarios(day) list
        +get_delivery_problem_scenarios(day) list
    }
    
    %% Config Package
    class MasterData {
        <<static>>
        +str DATE_FORMAT
        +Dict SEASONALITY
        +Dict MARKETS
        +Dict BOM
        +Dict PRODUCT_SALES_SHARES
        +Dict GLOBAL_CONFIG
        +Dict SADDLE_SHARES
        +get_month_from_day(day) int
        +get_frame_category(frame_type) str
    }
    
    class HolidaysConfig {
        <<static>>
        +Dict COUNTRY_CODES
        +get_holidays_for_year(year, country_code) Dict
        +get_all_holidays(year) Dict
        +is_holiday(date_obj, country_code) bool
    }
    
    %% UI Package
    class Utils {
        <<utility>>
        +initialize_session_state()
        +create_simulator() Simulator
        +run_happy_path_simulation()
        +ensure_simulator_available()
    }
    
    class ScenarioSidebar {
        <<utility>>
        +render_scenario_sidebar()
    }
    
    %% Beziehungen - Komposition (Simulator besitzt)
    Simulator *-- Inventory : "komponiert"
    Simulator *-- MarketBacklog : "komponiert"
    Simulator *-- ScenarioManager : "komponiert"
    Simulator *-- WorkdayCalculator : "komponiert"
    Simulator *-- DemandCalculator : "komponiert"
    Simulator *-- ChinaTransportManager : "komponiert"
    Simulator *-- ProductionPlanner : "komponiert"
    Simulator *-- ProcurementManager : "komponiert"
    
    %% Beziehungen - Dependency (nutzt)
    ProductionPlanner --> Inventory : "nutzt"
    ProductionPlanner --> DemandCalculator : "nutzt"
    ProductionPlanner --> WorkdayCalculator : "nutzt"
    ProductionPlanner --> ChinaTransportManager : "nutzt"
    
    ProcurementManager --> Inventory : "nutzt"
    ProcurementManager --> ChinaTransportManager : "nutzt"
    ProcurementManager --> WorkdayCalculator : "nutzt"
    
    ChinaTransportManager --> Inventory : "nutzt"
    ChinaTransportManager --> WorkdayCalculator : "nutzt"
    ChinaTransportManager --> ScenarioManager : "nutzt"
    
    DemandCalculator --> WorkdayCalculator : "nutzt"
    
    %% Beziehungen - Assoziation (nutzt statisch)
    Simulator ..> MasterData : "nutzt"
    ProductionPlanner ..> MasterData : "nutzt"
    DemandCalculator ..> MasterData : "nutzt"
    MarketBacklog ..> MasterData : "nutzt"
    
    WorkdayCalculator ..> HolidaysConfig : "nutzt"
    
    %% Beziehungen - Vererbung
    Scenario <|-- MarketingCampaignScenario : "erbt von"
    Scenario <|-- WarehouseDamageScenario : "erbt von"
    Scenario <|-- SupplierBreakdownScenario : "erbt von"
    Scenario <|-- DeliveryProblemScenario : "erbt von"
    Scenario <|-- StandardScenario : "erbt von"
    
    %% Beziehungen - Verwaltung
    ScenarioManager *-- Scenario : "verwaltet"
    ScenarioManager *-- StandardScenario : "verwaltet"
    
    %% UI Beziehungen
    Utils ..> Simulator : "erstellt"
    Utils ..> ScenarioManager : "nutzt"
    ScenarioSidebar ..> ScenarioManager : "nutzt"
```

## Legende

- **Komposition** (`*--`): Starke Beziehung, Lebensdauer gekoppelt
- **Dependency** (`-->`): Nutzt, aber besitzt nicht
- **Assoziation** (`..>`): Nutzt statische Methoden/Konstanten
- **Vererbung** (`<|--`): "erbt von"

## Verwendung

1. **Auf GitHub**: Diese Datei wird automatisch als Diagramm gerendert
2. **Lokal**: Nutze Mermaid Live Editor (https://mermaid.live/)
3. **VS Code**: Installiere "Markdown Preview Mermaid Support" Extension

