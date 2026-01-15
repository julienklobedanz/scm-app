# Page: Reporting (1_reporting.py)

## Übersicht

Die Reporting-Seite bietet eine Übersicht über Lagerbestände und Produktionsleistung. Sie visualisiert sowohl Sattel-Bestände als auch Fahrrad-Bestände über das gesamte Jahr 2026.

## Zweck und Funktionalität

Die Seite dient als Dashboard für die wichtigsten Lagerbestände. Sie zeigt:
- **Sattel-Bestände**: Bestände für alle Sattel-Typen (Spark, Speedline, Fizik Tundra, Raceline) über das Jahr
- **Fahrrad-Bestände**: Kumulative Bestände für alle Fahrrad-Modelle über das Jahr
- **Produktionsleistung**: Visualisierung der Produktionsmengen pro Produkt

## Detaillierte Berechnungslogik

### 1. Sattel-Bestände

Die Sattel-Bestände werden aus dem Materiallager geladen. Die Seite nutzt die Funktion `get_saddle_inventory_data()`, die die Daten aus der Materiallager-Seite (`5_materiallager.py`) importiert.

**Wie funktioniert die Datenbeschaffung?**

1. **Prüfung auf vorhandene Daten**: Die Funktion prüft zuerst, ob die Daten bereits im Session State vorhanden sind (`material_inventory_data`).

2. **Dynamischer Import**: Wenn die Daten nicht vorhanden sind, wird das Materiallager-Modul dynamisch importiert. Dies ist notwendig, weil der Dateiname `5_materiallager.py` eine Zahl enthält und nicht direkt als Python-Modul importiert werden kann.

3. **Funktionsaufruf**: Die Funktion `create_saddle_inventory_log()` wird aufgerufen, die die Sattel-Bestände berechnet.

4. **Datenstruktur**: Die Daten werden als Dictionary gespeichert: `{date: {saddle_type: stock}}`

**Visualisierung**: Die Sattel-Bestände werden als Liniendiagramm dargestellt, wobei jede Sattel-Typ eine eigene Linie hat.

### 2. Fahrrad-Bestände

Die Fahrrad-Bestände werden kumulativ berechnet. Die Seite iteriert über alle 365 Tage und berechnet für jeden Tag:

1. **Produktion**: Die tatsächliche Produktion (`Actual_Build`) wird aus den Simulationsergebnissen gelesen.

2. **Produkt-Verteilung**: Die Produktion wird basierend auf den Verkaufsanteilen (`PRODUCT_SALES_SHARES`) auf die einzelnen Produkte verteilt:
   ```python
   product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
   production_qty = actual_build * product_share
   ```

3. **Markt-Verteilung**: Die Produktion wird dann basierend auf den Marktanteilen (`MARKETS`) auf die einzelnen Märkte verteilt:
   ```python
   for market_code, market_params in MasterData.MARKETS.items():
       market_share = market_params['share']
       receipt = production_qty * market_share
       dispatch = receipt  # Sofort versendet (Just-in-Time)
   ```

4. **Kumulativer Bestand**: Der Bestand wird kumulativ berechnet:
   ```python
   stock_by_product[product] = stock_by_product[product] + total_receipt - total_dispatch
   stock_by_product[product] = max(0.0, stock_by_product[product])  # Kein negativer Bestand
   ```

**Wichtig**: Die Seite geht von einem Just-in-Time-System aus, bei dem die Produktion sofort versendet wird. Daher ist der Bestand normalerweise 0, es sei denn, es gibt Verzögerungen.

**Visualisierung**: Die Fahrrad-Bestände werden als gestapeltes Balkendiagramm dargestellt, wobei jedes Produkt eine eigene Farbe hat.

### 3. Produktionsleistung

Die Produktionsleistung wird aus den Produktionslogs des `ProductionPlanner` gelesen. Die Seite zeigt für jedes Produkt:
- Geplante Produktionsmenge (PM)
- Tatsächliche Produktionsmenge (PM)
- Fertiggestellte Produktionsmenge (PM)
- Backlog

**Visualisierung**: Die Produktionsleistung wird als Liniendiagramm dargestellt, wobei geplante, tatsächliche und fertiggestellte PM als separate Linien dargestellt werden.

## Abhängigkeiten

- `5_materiallager.py`: Für Sattel-Bestandsdaten
- `Simulator.production_planner.production_logs`: Für Produktionslogs
- `results_df`: Für tatsächliche Produktionsmengen
- `MasterData`: Für Stammdaten (BOM, Verkaufsanteile, Märkte)

## Besonderheiten

### Dynamischer Import

Die Seite nutzt einen dynamischen Import für das Materiallager-Modul, da der Dateiname `5_materiallager.py` eine Zahl enthält und nicht direkt als Python-Modul importiert werden kann:

```python
import importlib.util
module_path = os.path.join(os.path.dirname(__file__), "5_materiallager.py")
spec = importlib.util.spec_from_file_location("materiallager_module", module_path)
materiallager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materiallager_module)
```

### Session State

Die Seite nutzt den Session State, um Daten zwischen Seitenaufrufen zu speichern. Dies verbessert die Performance, da die Daten nicht bei jedem Seitenaufruf neu berechnet werden müssen.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Dynamischem Import (Zeile 63-76)
- Kumulativer Bestandsberechnung (Zeile 112-114)
- Just-in-Time-Logik (Zeile 108)

## Zusammenfassung

Die Reporting-Seite ist ein Dashboard, das die wichtigsten Lagerbestände und Produktionsleistungen visualisiert. Sie nutzt dynamische Imports und Session State, um Daten effizient zu laden und zu speichern.


