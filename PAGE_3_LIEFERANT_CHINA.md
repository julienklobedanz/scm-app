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

**WICHTIG: Datenfluss**
- Die Seite verwendet Daten aus dem Simulator, der wiederum die Volumenplanung als Basis verwendet
- Die Volumenplanung ist die "Single Source of Truth" für Nachfrageberechnungen
- Bestelleingang wird direkt aus der Volumenplanung berechnet (nicht aus transport_status)

**Wie funktioniert `get_supplier_log_dataframe()`?**

Die Methode im `ChinaTransportManager` erstellt eine Tabelle mit allen relevanten Daten für einen bestimmten Sattel-Typ:

1. **Bestelleingang**: Wird direkt aus Volumenplanung berechnet (Excel-Formel nachgebildet)
   - Summiert Nachfrage aller Produkte, die den gleichen Sattel verwenden
   - Für den Tag: order_date + lead_time_days (49 Tage)
   - Entspricht Excel-Formel: `=WENN((F12+'Lieferanten und Markt'!$F$10)>'Volumenplanung (Wochenbasis)'!$NE$82;0;...)`

2. **Freigabedatum**: Wann wurde die Bestellung freigegeben (nächster chinesischer Arbeitstag nach Bestelleingang)
   - Wird aus `transport_status` gelesen
   - Angezeigt in der Zeile des Bestelleingangs

3. **Freigegebene Bestellungen**: Menge der freigegebenen Bestellungen
   - Wird aus `transport_status` gelesen
   - Originalmenge (vor Produktionsverlusten)

4. **Störung**: Gibt es aktive Störungs-Szenarien (z.B. Maschinenausfall)
   - "Ja" wenn `production_loss_percentage > 0`
   - "Nein" sonst

5. **Produktionsdatum**: Wann wurde produziert
   - **Excel-Formel**: `=ARBEITSTAG(KU16;'Lieferanten und Markt'!$H$10-1;$E$14:$NU$14)`
   - **Berechnung**: Freigabedatum + (Produktionszeit - 1) Arbeitstage
   - **Produktionszeit**: 5 AT, daher: Freigabedatum + 4 Arbeitstage
   - **WICHTIG**: Wird in der Zeile des Freigabedatums angezeigt (nicht in der Zeile des Produktionsdatums)
   - Berücksichtigt chinesische Feiertage

6. **Produktionsmenge**: Wie viel wurde produziert
   - **Excel-Formel**: `=WENN(ODER(KU11="Sa.";KU11="So.";KU13<>"");0;SUMMENPRODUKT((($E$19:$NU$19)=KU12)*($E$17:$NU$17)))`
   - **Berechnung**: 
     - Wenn Wochenende oder Störung: 0
     - Sonst: Freigegebene Bestellungen für das Produktionsdatum
   - **WICHTIG**: Produktionsmenge = Freigegebene Bestellungen (vom Freigabedatum)
   - Wird in der Zeile des Produktionsdatums angezeigt

7. **Warenausgang**: Wann und wie viel wurde zum Hafen versendet
   - **Excel-Formel**: `=WENN(ODER('Inbound (Material)'!KU68="Ausgefallen";'Inbound (Material)'!KU68="");0;KU172)`
   - **Berechnung**:
     - Wenn DeliveryProblemScenario mit 100% Verlust ("Ausgefallen"): 0
     - Sonst: Normale Ausgangsmenge (basierend auf Pool-Logik, >= 500)
   - Pool-Logik: Alle Sättel werden gesammelt, wenn Pool >= 500, wird verschifft (anteilig verteilt)

8. **Warenbestand**: Aktueller Bestand im chinesischen Lager
   - **Excel-Formel**: `Produziert + Warenbestand - Ausgangsmenge`
   - **Berechnung**: Vorheriger Bestand + Produziert - Ausgangsmenge
   - **Kumulativ**: Wird täglich aktualisiert

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


