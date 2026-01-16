# Page: Inbound (4_inbound.py)

## Übersicht

Die Inbound-Seite zeigt Ware, die das chinesische Festland verlassen hat und auf dem Weg zum Lager Dortmund ist. Sie visualisiert alle Verschiffungen und Zuläufe zum Lager.

## Zweck und Funktionalität

Die Seite dient zur Überwachung der Inbound-Logistik. Sie zeigt:
- **Verschiffungen**: Wann wurde verschifft und wie viel
- **Zuläufe**: Wann kommt die Ware im Lager Dortmund an
- **Menge Gesamt**: Gesamtmenge pro Tag
- **Individuelle Sattel-Mengen**: Menge pro Sattel-Typ

## Detaillierte Berechnungslogik

### 1. Datenbeschaffung

Die Seite nutzt den `ChinaTransportManager` des Simulators, um die Daten zu erhalten:

```python
manager = st.session_state.simulator.china_transport_manager
df = manager.get_inbound_log_dataframe(saddle_shares)
```

**Wie funktioniert `get_inbound_log_dataframe()`?**

Die Methode im `ChinaTransportManager` erstellt eine Tabelle mit allen Inbound-Daten:

1. **Port-Buckets**: Die Methode verwaltet Port-Buckets, die Bestände im Hafen zwischenlagern, bevor sie verschifft werden.

2. **Losgröße**: Verschiffung erfolgt nur, wenn die Losgröße erreicht ist (500 Einheiten).

3. **Transportzeit**: Die Transportzeit per Schiff beträgt mehrere Tage.
   - **KRITISCH: Excel-Formel korrigiert**: `=WENN(P57<>"";WENN(Lieferketten!$J$27="AT";ARBEITSTAG(P59;Lieferketten!$I$27-1;$E$56:$NU$56);P59+Lieferketten!$I$27-1);"")`
   - **$I$27** = 30 (Schiffsdauer in KT)
   - **$J$27** = "AT" (Arbeitstage)
   - **Berechnung**: ARBEITSTAG(Abfahrt Schiff; 30-1; Feiertage) = ARBEITSTAG(Abfahrt Schiff; 29; Feiertage)
   - **NICHT**: +30 Kalendertage, sondern 29 Arbeitstage!

4. **Ankunft**: Die Ware kommt an deutschen Arbeitstagen im Lager Dortmund an.
   - **KRITISCH: Excel-Formel korrigiert**: `=WENN(P57<>"";WENN(Lieferketten!$J$28="AT";ARBEITSTAG(P61;Lieferketten!$I$28-1;$E$13:$NU$13);P61+Lieferketten!$I$28-1);"")`
   - **$I$28** = 2 (LKW DE Dauer in AT)
   - **$J$28** = "AT" (Arbeitstage)
   - **Berechnung**: ARBEITSTAG(Ankunft Schiff; 2-1; Feiertage) = ARBEITSTAG(Ankunft Schiff; 1; Feiertage)
   - **NICHT**: +2 Arbeitstage, sondern 1 Arbeitstag!

5. **Verfügbar im Lager**: Das Datum, an dem die Ware im Lager verfügbar ist.

6. **Menge Gesamt**: Gesamtmenge pro Tag
   - **KRITISCH**: Wird aus Summe der Einzelpositionen berechnet (nicht direkt aus ship_qty_total)
   - **Berechnung**: Summe aller Sattel-Mengen pro Tag

### 2. Optimierungen

Die Methode `get_inbound_log_dataframe()` wurde optimiert, um die Performance zu verbessern:

- **Early-Exit**: Wenn keine weiteren Transporte erwartet werden, wird die Schleife früh beendet.
- **Last Relevant Day**: Die Schleife wird auf den letzten relevanten Tag begrenzt.

### 3. Visualisierung

Die Seite zeigt eine große Tabelle (Höhe: 800px) mit allen Inbound-Daten. Wochenenden werden rot hinterlegt, um sie visuell hervorzuheben.

**Summenzeile**: Am Ende der Tabelle wird eine Summenzeile angezeigt, die die Gesamtsummen aller numerischen Spalten (Menge Gesamt, individuelle Sattel-Mengen) zeigt.

## Abhängigkeiten

- `ChinaTransportManager`: Für Inbound-Daten
- `MasterData`: Für Sattel-Anteile
- `WorkdayCalculator`: Für Arbeitstagsberechnungen

## Besonderheiten

### Port-Buckets

Die Seite zeigt Daten, die aus Port-Buckets stammen. Port-Buckets sind Zwischenlager im Hafen, die Bestände zwischenlagern, bevor sie verschifft werden.

### Losgröße

Verschiffung erfolgt nur, wenn die Losgröße erreicht ist. Dies kann dazu führen, dass Bestände mehrere Tage im Hafen liegen, bevor sie verschifft werden.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Datenbeschaffung (Zeile 47-54)
- Visualisierung (Zeile 56-69)

## Zusammenfassung

Die Inbound-Seite zeigt alle Verschiffungen und Zuläufe zum Lager Dortmund. Sie nutzt den `ChinaTransportManager`, um die Daten zu erhalten und visualisiert sie in einer großen, übersichtlichen Tabelle.


