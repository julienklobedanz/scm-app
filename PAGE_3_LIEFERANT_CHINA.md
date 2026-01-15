# Page: Lieferant China (3_lieferant_china.py)

## Übersicht

Die Lieferant China-Seite zeigt die Produktion und den Transport zum Hafen Dengwong für jeden Sattel-Typ separat. Sie visualisiert den gesamten Prozess von der Bestellung bis zur Ankunft im Hafen.

## Zweck und Funktionalität

Die Seite dient zur Überwachung der Produktion und des Transports in China. Sie zeigt für jeden Sattel-Typ eine separate Tabelle mit folgenden Informationen:
- **Bestelleingang**: Wann wurde die Bestellung aufgegeben
- **Freigabedatum**: Wann wurde die Bestellung freigegeben
- **Freigegebene Bestellungen**: Menge der freigegebenen Bestellungen
- **Störung**: Gibt es Störungen (Maschinenausfall, etc.)
- **Produktionsdatum**: Wann wurde produziert
- **Produktionsmenge**: Wie viel wurde produziert
- **Warenausgang**: Wann und wie viel wurde versendet
- **Warenbestand**: Aktueller Bestand im chinesischen Lager

## Detaillierte Berechnungslogik

### 1. Datenbeschaffung

Die Seite nutzt den `ChinaTransportManager` des Simulators, um die Daten zu erhalten:

```python
manager = st.session_state.simulator.china_transport_manager
df = manager.get_supplier_log_dataframe(saddle_type, saddle_shares[saddle_type])
```

**Wie funktioniert `get_supplier_log_dataframe()`?**

Die Methode im `ChinaTransportManager` erstellt eine Tabelle mit allen relevanten Daten für einen bestimmten Sattel-Typ:

1. **Bestelleingang**: Wann wurde die Bestellung aufgegeben (basierend auf Nachfrage)
2. **Freigabedatum**: Wann wurde die Bestellung freigegeben (5 chinesische Arbeitstage nach Bestelleingang)
3. **Freigegebene Bestellungen**: Menge der freigegebenen Bestellungen
4. **Störung**: Gibt es aktive Störungs-Szenarien (z.B. Maschinenausfall)
5. **Produktionsdatum**: Wann wurde produziert (5 chinesische Arbeitstage nach Freigabe)
6. **Produktionsmenge**: Wie viel wurde produziert (kann durch Störungen reduziert sein)
7. **Warenausgang**: Wann und wie viel wurde zum Hafen versendet
8. **Warenbestand**: Aktueller Bestand im chinesischen Lager

### 2. Sattel-Anteile

Die Seite berechnet die Sattel-Anteile basierend auf der BOM:

```python
saddle_shares = MasterData.calculate_saddle_shares()
```

Diese Methode berechnet, welcher Anteil der Gesamtnachfrage auf jeden Sattel-Typ entfällt, basierend auf den Verkaufsanteilen der Produkte und deren BOM.

### 3. Visualisierung

Für jeden Sattel-Typ wird eine separate Tabelle angezeigt. Wochenenden werden rot hinterlegt, um sie visuell hervorzuheben.

## Abhängigkeiten

- `ChinaTransportManager`: Für Produktions- und Transport-Daten
- `MasterData`: Für Sattel-Anteile und Stammdaten
- `WorkdayCalculator`: Für Arbeitstagsberechnungen

## Besonderheiten

### Separate Tabellen pro Sattel-Typ

Die Seite zeigt für jeden Sattel-Typ eine separate Tabelle, da jeder Sattel-Typ unterschiedliche Produktions- und Transport-Zyklen haben kann.

### Wochenenden-Hervorhebung

Wochenenden werden rot hinterlegt, um zu zeigen, dass an diesen Tagen keine Produktion oder Transport stattfindet.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Sattel-Anteile-Berechnung (Zeile 51-52)
- Tabellen-Anzeige (Zeile 56-92)

## Zusammenfassung

Die Lieferant China-Seite zeigt die Produktion und den Transport zum Hafen für jeden Sattel-Typ separat. Sie nutzt den `ChinaTransportManager`, um die Daten zu erhalten und visualisiert sie in übersichtlichen Tabellen.

