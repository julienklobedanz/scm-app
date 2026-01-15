# Page: Fertigproduktelager (7_fertigproduktelager.py)

## Übersicht

Die Fertigproduktelager-Seite zeigt die Fertigproduktbestände nach Produkten. Sie visualisiert den kompletten Fertigproduktfluss von der Produktion bis zur Auslieferung.

## Zweck und Funktionalität

Die Seite dient zur Überwachung des Fertigproduktelagers. Sie zeigt für jedes Produkt:
- **Lagerzugang**: Wann und wie viel wurde eingelagert
- **Bestand (morgens)**: Bestand zu Beginn des Tages
- **Lagerabgang**: Wann und wie viel wurde ausgeliefert
- **Bestand (abends)**: Bestand am Ende des Tages

## Detaillierte Berechnungslogik

### 1. Datenberechnung

Die Seite nutzt die Funktion `create_finished_goods_log()`, die die Fertigproduktelager-Daten berechnet:

**Wie funktioniert `create_finished_goods_log()`?**

Die Funktion erstellt ein Log für jedes Produkt über das gesamte Jahr:

1. **Produktion**: Die Funktion liest die tatsächliche Produktion aus den Simulationsergebnissen:
   ```python
   actual_build = results_df.iloc[day]['Actual_Build']
   ```

2. **Produkt-Verteilung**: Die Produktion wird basierend auf den Verkaufsanteilen auf die einzelnen Produkte verteilt:
   ```python
   product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
   production_qty = actual_build * product_share
   ```

3. **Markt-Verteilung**: Die Produktion wird dann basierend auf den Marktanteilen auf die einzelnen Märkte verteilt:
   ```python
   for market_code, market_params in MasterData.MARKETS.items():
       market_share = market_params['share']
       receipt = production_qty * market_share
       dispatch = receipt  # Sofort versendet (Just-in-Time)
   ```

4. **Bestandsberechnung**: Die Funktion berechnet den Bestand:
   ```python
   stock_morning = 0  # Vereinfacht: 0, da Just-in-Time
   stock_evening = 0  # Vereinfacht: 0, da Just-in-Time
   ```

### 2. Just-in-Time-System

Die Seite geht von einem Just-in-Time-System aus, bei dem die Produktion sofort versendet wird. Daher ist der Bestand normalerweise 0, es sei denn, es gibt Verzögerungen.

**Warum Just-in-Time?**

Die Simulation geht davon aus, dass die Produktion sofort an die Kunden ausgeliefert wird. Dies vereinfacht die Berechnung und entspricht einem idealen Supply Chain Management.

### 3. Visualisierung

Die Seite zeigt für jedes Produkt:
- **Tabelle**: Alle Fertigproduktelager-Daten in tabellarischer Form
- **Liniendiagramm**: Bestandsentwicklung über das Jahr (normalerweise 0)

## Abhängigkeiten

- `results_df`: Für tatsächliche Produktionsmengen
- `MasterData`: Für Stammdaten (Verkaufsanteile, Märkte)
- `WorkdayCalculator`: Für Arbeitstagsberechnungen

## Besonderheiten

### Float-Werte für Lagerzugang/Lagerabgang

Die Seite speichert `Lagerzugang` und `Lagerabgang` als Float-Werte (1 Dezimalstelle). Dies ist wichtig, da die Produktion und Auslieferung nicht immer ganzzahlig sein müssen.

**Warum Float-Werte?**

Die Produktion wird basierend auf Verkaufsanteilen und Marktanteilen berechnet, was zu Dezimalstellen führen kann. Diese Dezimalstellen müssen erhalten bleiben, um die Genauigkeit zu gewährleisten.

### Just-in-Time-Logik

Die Seite implementiert eine Just-in-Time-Logik, bei der die Produktion sofort versendet wird. Dies bedeutet, dass der Bestand normalerweise 0 ist.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Just-in-Time-Logik (Zeile 80-89)
- Float-Werte (Zeile 97-100)

## Zusammenfassung

Die Fertigproduktelager-Seite zeigt den kompletten Fertigproduktfluss von der Produktion bis zur Auslieferung. Sie geht von einem Just-in-Time-System aus und speichert Lagerzugang und Lagerabgang als Float-Werte.


