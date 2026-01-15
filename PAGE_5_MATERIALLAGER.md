# Page: Materiallager (5_materiallager.py)

## Übersicht

Die Materiallager-Seite zeigt Sattelzugänge, Bestände und Verluste für jeden Sattel-Typ separat. Sie visualisiert den kompletten Materialfluss vom Wareneingang bis zum Verbrauch in der Produktion.

## Zweck und Funktionalität

Die Seite dient zur Überwachung des Materiallagers. Sie zeigt für jeden Sattel-Typ:
- **Lagerzugang**: Wann und wie viel wurde eingelagert
- **Bestand morgens**: Bestand zu Beginn des Tages
- **Lagerabgang**: Wann und wie viel wurde für die Produktion entnommen
- **Verlustmenge**: Verluste durch Störungen (z.B. Wasserschaden)
- **Bestand abends**: Bestand am Ende des Tages

## Detaillierte Berechnungslogik

### 1. Datenbeschaffung

Die Seite nutzt die Funktion `create_saddle_inventory_log()`, die die Materiallager-Daten berechnet:

**Wie funktioniert `create_saddle_inventory_log()`?**

Die Funktion erstellt ein Log für jeden Sattel-Typ über das gesamte Jahr:

1. **Inbound-Daten**: Die Funktion holt die "Wahrheit" von der Inbound-Logik:
   ```python
   inbound_df = manager.get_inbound_log_dataframe(saddle_shares)
   ```
   Die Inbound-Tabelle enthält die korrekte 500er Logik und Termine.

2. **Wareneingänge**: Die Funktion scannt die Inbound-Tabelle nach Wareneingängen:
   ```python
   for _, row in inbound_df.iterrows():
       avail_str = row.get('Verfügbar im Lager')
       if avail_str:
           avail_date = datetime.strptime(avail_str, MasterData.DATE_FORMAT).date()
           # Mengen pro Sattel auslesen und addieren
   ```

3. **Verbrauch**: Die Funktion berechnet den Verbrauch basierend auf der tatsächlichen Produktion:
   ```python
   if 0 <= day < len(results_df):
       actual_build = results_df.iloc[day]['Actual_Build']
       # Rekonstruiere Produktionsmengen pro Produkt
       # Verteile dann die tatsächliche Produktion proportional
   ```

4. **Bestandsberechnung**: Die Funktion berechnet den Bestand kumulativ:
   ```python
   stock_morning[s] = stock_evening.get(s, 0.0)  # Bestand vom Vortag
   stock_evening[s] = stock_morning[s] + receipt_by_saddle.get(s, 0.0) - actual_issue
   ```

### 2. Stücklisten-Logik

Die Funktion nutzt die exakte Stücklisten-Logik, um den Verbrauch zu berechnen:

1. **Nachfrage pro Produkt**: Die Funktion nutzt den `DemandCalculator`, um die Nachfrage pro Produkt zu erhalten.

2. **Produktionsverteilung**: Die tatsächliche Produktion wird proportional auf die Produkte verteilt:
   ```python
   product_demands = demand_calc.calculate_daily_demand_per_product_dict(day, marketing_add_ons)
   total_demand = sum(product_demands.values())
   if total_demand > 0:
       for product, demand in product_demands.items():
           product_production = actual_build * (demand / total_demand)
   ```

3. **Sattel-Verbrauch**: Basierend auf der BOM wird der Sattel-Verbrauch berechnet:
   ```python
   for product, production_qty in product_productions.items():
       components = MasterData.BOM.get(product, {})
       saddle_type = components.get('saddle', '')
       issue_by_saddle[saddle_type] += production_qty
   ```

### 3. Vorlauf-Berechnung

Die Funktion beginnt ab November 2025, um den Vorlauf (Initial Stock) mitzunehmen:

```python
start_date_log = date(2025, 11, 1)
```

Dies stellt sicher, dass die ersten Lieferungen erfasst werden und der Bestand am 01.01.2026 korrekt ist.

### 4. Visualisierung

Für jeden Sattel-Typ wird eine separate Tabelle angezeigt. Die Seite zeigt auch ein Liniendiagramm, das die Bestandsentwicklung über das Jahr visualisiert.

## Abhängigkeiten

- `ChinaTransportManager`: Für Inbound-Daten
- `DemandCalculator`: Für Nachfrage-Berechnung
- `MasterData`: Für BOM und Stammdaten
- `results_df`: Für tatsächliche Produktionsmengen

## Besonderheiten

### Synchronisation mit Inbound-Daten

Die Seite synchronisiert sich mit den Inbound-Daten, um sicherzustellen, dass die Wareneingänge korrekt erfasst werden.

### Exakte Stücklisten-Logik

Die Seite nutzt die exakte Stücklisten-Logik, um den Verbrauch zu berechnen. Dies stellt sicher, dass der Verbrauch korrekt auf die Sattel-Typen verteilt wird.

### Vorlauf-Berechnung

Die Seite beginnt ab November 2025, um den Vorlauf mitzunehmen. Dies stellt sicher, dass der Initialbestand korrekt berechnet wird.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Inbound-Daten-Beschaffung (Zeile 62-95)
- Stücklisten-Logik (Zeile 132-180)
- Vorlauf-Berechnung (Zeile 98-103)

## Zusammenfassung

Die Materiallager-Seite zeigt den kompletten Materialfluss vom Wareneingang bis zum Verbrauch. Sie synchronisiert sich mit den Inbound-Daten und nutzt die exakte Stücklisten-Logik, um den Verbrauch korrekt zu berechnen.


