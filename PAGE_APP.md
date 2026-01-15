# Page: App (app.py)

## Übersicht

Die App-Seite ist die Hauptseite der Anwendung und zeigt die SCOR-Metriken (Supply Chain Operations Reference). Sie dient als Dashboard für die wichtigsten Performance-Indikatoren.

## Zweck und Funktionalität

Die Seite dient als zentrales Dashboard für die SCOR-Metriken. Sie zeigt:
- **Perfect Order Fulfillment (Inbound)**: Lieferanten-Performance
- **Perfect Order Fulfillment (Outbound)**: Kunden-Performance
- **Source Performance**: Beschaffungs-Performance
- **Delivery Performance**: Auslieferungs-Performance
- **Fulfillment Performance**: Gesamt-Performance

## Detaillierte Berechnungslogik

### 1. Automatische Simulation

Die Seite führt beim ersten Laden automatisch eine "Happy Path" Simulation aus:

```python
if not st.session_state.happy_path_run and st.session_state.results_df is None:
    simulator = create_simulator()
    results_df, kpis = simulator.run()
    st.session_state.results_df = results_df
    st.session_state.kpis = kpis
    st.session_state.simulator = simulator
    st.session_state.happy_path_run = True
    st.rerun()
```

**Was ist "Happy Path"?**

Der "Happy Path" ist die Standard-Simulation ohne Störungen. Sie wird automatisch ausgeführt, damit die Seite sofort Ergebnisse anzeigen kann.

### 2. SCOR-Metriken-Berechnung

Die Seite berechnet alle SCOR-Metriken:

#### Perfect Order Fulfillment (Inbound)

Die Inbound-Metriken werden für alle Lieferanten berechnet:

1. **China**: Die Metriken werden aus dem `ChinaTransportManager` gelesen:
   ```python
   transport_manager = simulator.china_transport_manager
   transport_status = transport_manager.transport_status
   ```

2. **Metriken**:
   - **Anzahl Lieferungen**: Gesamtanzahl der Lieferungen
   - **Anzahl Lieferungen mit Totalausfall**: Lieferungen mit 100% Verlust
   - **Anzahl Lieferungen mit Mengenverlust**: Lieferungen mit teilweisem Verlust
   - **Verspätete Lieferungen**: Anzahl verspäteter Lieferungen
   - **Perfekte Lieferungen in %**: Prozentsatz perfekter Lieferungen
   - **Durchschnittliche Anzahl von Tagen der verspäteten Lieferungen**: Durchschnittliche Verspätung

3. **Berechnung**:
   ```python
   perfect_deliveries_pct = ((total_deliveries - total_failures - quantity_losses - late_deliveries) / total_deliveries * 100) if total_deliveries > 0 else 100.0
   ```

#### Perfect Order Fulfillment (Outbound)

Die Outbound-Metriken werden für alle Märkte berechnet:

1. **Markt-spezifische Metriken**: Für jeden Markt werden separate Metriken berechnet.

2. **Metriken**:
   - **Anzahl Bestellungen**: Gesamtanzahl der Bestellungen
   - **Anzahl perfekter Bestellungen**: Bestellungen ohne Probleme
   - **Perfekte Bestellungen in %**: Prozentsatz perfekter Bestellungen
   - **Durchschnittliche Durchlaufzeit**: Durchschnittliche Durchlaufzeit

#### Source Performance

Die Source-Metriken werden für die Beschaffung berechnet:

1. **Bestelltreue**: Wie viele Bestellungen wurden korrekt ausgeführt
2. **Durchlaufzeit**: Durchschnittliche Durchlaufzeit für Beschaffung

#### Delivery Performance

Die Delivery-Metriken werden für die Auslieferung berechnet:

1. **Liefertreue**: Wie viele Lieferungen wurden korrekt ausgeführt
2. **Durchlaufzeit**: Durchschnittliche Durchlaufzeit für Auslieferung

#### Fulfillment Performance

Die Fulfillment-Metriken werden für die Gesamt-Performance berechnet:

1. **Perfect Order Fulfillment**: Gesamt-Performance über alle Bereiche
2. **Durchschnittliche Durchlaufzeit**: Durchschnittliche Durchlaufzeit über alle Bereiche

### 3. Visualisierung

Die Seite zeigt die Metriken in Tabellen und Balkendiagrammen:

1. **Tabellen**: Alle Metriken werden in übersichtlichen Tabellen dargestellt.

2. **Balkendiagramme**: Wichtige Metriken werden als Balkendiagramme visualisiert.

### 4. Formatierung

Die Seite formatiert die Daten für die Anzeige:
- **Ganzzahlen**: Werden auf ganze Zahlen gerundet
- **Prozente**: Werden auf 2 Dezimalstellen gerundet
- **Durchschnittliche Tage**: Werden auf 2 Dezimalstellen gerundet

## Abhängigkeiten

- `Simulator`: Für Simulationsergebnisse
- `ChinaTransportManager`: Für Inbound-Metriken
- `MarketBacklog`: Für Outbound-Metriken
- `MasterData`: Für Stammdaten

## Besonderheiten

### Automatische Simulation

Die Seite führt beim ersten Laden automatisch eine Simulation aus. Dies stellt sicher, dass die Seite sofort Ergebnisse anzeigen kann.

### Session State

Die Seite nutzt den Session State, um Simulationsergebnisse zwischen Seitenaufrufen zu speichern. Dies verbessert die Performance, da die Simulation nicht bei jedem Seitenaufruf neu ausgeführt werden muss.

### SCOR-Metriken

Die Seite berechnet alle SCOR-Metriken, die ein Standard für Supply Chain Performance Measurement sind.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Automatische Simulation (Zeile 38-50)
- SCOR-Metriken-Berechnung (Zeile 75-420)

## Zusammenfassung

Die App-Seite ist das zentrale Dashboard für die SCOR-Metriken. Sie führt beim ersten Laden automatisch eine Simulation aus und zeigt alle wichtigen Performance-Indikatoren in übersichtlichen Tabellen und Diagrammen.

