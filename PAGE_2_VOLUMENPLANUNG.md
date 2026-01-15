# Page: Volumenplanung (2_volumenplanung.py)

## Übersicht

Die Volumenplanung-Seite ist eine der komplexesten Seiten der Anwendung. Sie berechnet und visualisiert die wöchentliche und tägliche Nachfrage für alle Produkte basierend auf Saisonalität, Verkaufsanteilen und einer speziellen Carry-Over-Logik. Die Seite ist in zwei Tabs unterteilt: "Wöchentliche Planung" und "Tägliche Planung".

## Zweck und Funktionalität

Die Seite dient dazu, die geplante und tatsächliche Nachfrage für alle Fahrrad-Modelle zu visualisieren. Die "geplante Nachfrage" zeigt die Nachfrage ohne Marketing-Szenarien, während die "tatsächliche Nachfrage" Marketing-Add-ons berücksichtigt. Die Seite berechnet auch die benötigten Schichten pro Woche basierend auf der Nachfrage und der Produktionskapazität.

## Wichtige Konzepte

### Carry-Over-Logik

Die Carry-Over-Logik ist ein zentrales Konzept, das sicherstellt, dass Reste vom vorherigen Tag zum nächsten Tag übertragen werden. Dies ist notwendig, um eine präzise Ganzzahl-Produktion zu gewährleisten, da die monatliche Nachfrage durch die Anzahl der Arbeitstage geteilt wird und dabei Dezimalstellen entstehen können.

**Wie funktioniert die Carry-Over-Logik?**

1. **Monatliche Base-Daily-Float Berechnung**: Für jeden Monat wird zunächst die monatliche Nachfrage berechnet (Jahresvolumen × Saisonalitätsfaktor × Verkaufsanteil). Diese wird dann durch die Anzahl der Arbeitstage im Monat geteilt, um die tägliche Nachfrage zu erhalten. Das Ergebnis ist ein Float-Wert (z.B. 60.54545454545455).

2. **Rest-Übertragung**: Wenn die tägliche Nachfrage nicht ganzzahlig ist, wird der Rest (z.B. 0.45454545454545) gespeichert und zum nächsten Arbeitstag addiert. An Feiertagen und Wochenenden bleibt der Rest unverändert, da an diesen Tagen keine Nachfrage berechnet wird.

3. **Rundung mit Floating-Point-Korrektur**: 
   - Base + Rest wird auf 12 Dezimalstellen gerundet, um Floating-Point-Fehler zu vermeiden.
   - Wenn Base + Rest sehr nahe an einer ganzen Zahl ist (< 1e-10), wird direkt auf diese ganze Zahl gerundet.
   - Ansonsten wird `math.floor()` verwendet, um abzurunden (wie Excel `ABRUNDEN`).
   - Der Rest wird für den nächsten Tag gespeichert (auf 12 Dezimalstellen gerundet).

4. **Reste am letzten Arbeitstag**: Am letzten Arbeitstag des Jahres werden alle Reste aufsummiert, um sicherzustellen, dass die Jahresgesamtsumme exakt dem Jahresvolumen entspricht.

5. **Marketing-Add-ons**: Marketing-Add-ons werden nach der Rundung addiert und gehen nicht in den Rest ein. Das bedeutet, dass Marketing-Add-ons immer zusätzlich zur Basis-Nachfrage kommen.

### Sequenzielle Berechnung

**KRITISCH**: Die Nachfrage für alle 365 Tage muss sequenziell berechnet werden, damit die Carry-Over-Logik korrekt funktioniert. Die `DemandCalculator`-Instanzen haben einen internen Zustand (`product_remainders`), der bei jeder Berechnung aktualisiert wird. Wenn die Tage nicht in der richtigen Reihenfolge berechnet werden, wird der Rest nicht korrekt übertragen.

## Detaillierte Berechnungslogik

### 1. Initialisierung

Die Seite erstellt zwei separate `DemandCalculator`-Instanzen:
- `demand_calculator_planned`: Für geplante Nachfrage (ohne Marketing)
- `demand_calculator_actual`: Für tatsächliche Nachfrage (mit Marketing)

Diese Trennung ist notwendig, damit die Carry-Over-Logik für beide Fälle unabhängig funktioniert.

### 2. Wöchentliche Planung

#### Schritt 1: Sequenzielle Berechnung aller täglichen Nachfragen

Die Seite berechnet zunächst die Nachfrage für alle 365 Tage sequenziell. Dies ist kritisch für die korrekte Carry-Over-Logik.

```python
# Für jeden Tag (0-364)
for day in range(365):
    is_workday = workday_calc.is_workday(day)
    
    if is_workday:
        # Berechne Marketing-Add-ons (wenn vorhanden)
        marketing_add_ons = {}
        # ... Marketing-Add-on Berechnung ...
        
        # Berechne Nachfrage für alle Produkte gleichzeitig
        planned_demands = demand_calculator_planned.calculate_daily_demand_per_product_dict(day, {})
        actual_demands = demand_calculator_actual.calculate_daily_demand_per_product_dict(day, marketing_add_ons)
    else:
        # An Feiertagen/Wochenenden: Alle Nachfragen sind 0
        # Rest bleibt unverändert (wird nicht aktualisiert)
        planned_demands = {product: 0 for product in MasterData.BOM.keys()}
        actual_demands = {product: 0 for product in MasterData.BOM.keys()}
```

**Warum sequenziell?** Die `DemandCalculator`-Instanzen haben einen internen Zustand (`product_remainders`), der bei jeder Berechnung aktualisiert wird. Wenn die Tage nicht in der richtigen Reihenfolge berechnet werden, wird der Rest nicht korrekt übertragen.

#### Schritt 2: ISO-Kalenderwochen-Berechnung

Die Seite berechnet die ISO-Kalenderwochen für das Jahr 2026. ISO-Woche 1 beginnt am ersten Montag des Jahres oder früher (wenn der 1. Januar ein Montag bis Donnerstag ist).

```python
# Berechne Start der ersten ISO-Woche
jan_1 = date(2026, 1, 1)
jan_1_weekday = jan_1.weekday()  # 0=Montag, 6=Sonntag

if jan_1_weekday <= 3:  # Mo-Do: Woche beginnt am Montag dieser Woche
    first_monday = jan_1 - timedelta(days=jan_1_weekday)
else:  # Fr-So: Woche beginnt am nächsten Montag
    first_monday = jan_1 + timedelta(days=7 - jan_1_weekday)
```

#### Schritt 3: Wöchentliche Aggregation

Für jede Kalenderwoche werden die täglichen Nachfragen aggregiert:

```python
for week_num in range(1, last_week + 1):
    week_start = first_monday + timedelta(weeks=week_num - 1)
    
    # Aggregiere Nachfrage für alle 7 Tage der Woche
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        if current_date.year == 2026:
            day_of_year = (current_date - start_date).days
            # Nutze bereits berechnete Nachfragen (sequenziell berechnet)
            day_planned = daily_demands_planned.get(day_of_year, {})
            day_actual = daily_demands_actual.get(day_of_year, {})
            
            # Summiere für jedes Produkt
            for product in MasterData.BOM.keys():
                week_demand_planned[product] += day_planned.get(product, 0)
                week_demand_actual[product] += day_actual.get(product, 0)
```

**Wichtig**: Die wöchentliche Aggregation nutzt die bereits sequenziell berechneten täglichen Nachfragen. Dies stellt sicher, dass die Carry-Over-Logik korrekt funktioniert.

#### Schritt 4: Schichten-Berechnung

Die Seite berechnet die benötigten Schichten pro Woche basierend auf der wöchentlichen Nachfrage und der Produktionskapazität.

**Excel-Formel-Logik**:
```
AUFRUNDEN(N8/H105/(Basisdaten!$E$9*Basisdaten!$E$13*Basisdaten!$E$10);0)
```

**Wo**:
- `N8` = Gesamtvolumen der Woche (total_week_demand_actual)
- `H105` = Anzahl Arbeitstage in der Woche (num_workdays)
- `Basisdaten!$E$9` = CAPACITY_PER_HOUR (130)
- `Basisdaten!$E$13` = HOURS_PER_SHIFT (8)
- `Basisdaten!$E$10` = PRODUCTION_LINES (1)

**Berechnungsschritte**:

1. **Täglicher Bedarf**: `daily_demand = total_week_demand_actual / num_workdays`
   - Die wöchentliche Nachfrage wird durch die Anzahl der Arbeitstage in der Woche geteilt, um den täglichen Bedarf zu erhalten.

2. **Kapazität pro Schicht**: `CAPACITY_PER_SHIFT = HOURS_PER_SHIFT * CAPACITY_PER_HOUR * PRODUCTION_LINES`
   - Eine Schicht hat 8 Stunden, pro Stunde können 130 Einheiten produziert werden, und es gibt 1 Produktionslinie.
   - `CAPACITY_PER_SHIFT = 8 * 130 * 1 = 1040`

3. **Benötigte Schichten**: `required_shifts_float = daily_demand / CAPACITY_PER_SHIFT`
   - Der tägliche Bedarf wird durch die Kapazität pro Schicht geteilt, um die benötigten Schichten zu erhalten.

4. **Aufrunden**: `required_shifts_int = ceil(required_shifts_float)`
   - Die benötigten Schichten werden aufgerundet, da nur ganze Schichten möglich sind.

5. **Begrenzung**: `actual_shifts = max(MIN_SHIFTS, min(MAX_SHIFTS, required_shifts_int))`
   - Die Schichten werden auf einen Bereich von 1-3 begrenzt (MIN_SHIFTS=1, MAX_SHIFTS=3).

**Sonderfälle**:
- Wenn `total_week_demand_actual == 0`: `actual_shifts = MIN_SHIFTS` (1 Schicht)
- Wenn `num_workdays == 0`: `actual_shifts = MIN_SHIFTS` (1 Schicht)

### 3. Tägliche Planung

#### Schritt 1: Datumsfilter

Die Seite bietet Datumsfilter, um einen bestimmten Zeitraum anzuzeigen:

```python
start_date_filter = st.date_input("Start-Datum", value=date(2026, 1, 1), ...)
end_date_filter = st.date_input("End-Datum", value=date(2026, 12, 31), ...)
```

#### Schritt 2: Tägliche Nachfrage-Berechnung

Für jeden Tag im gefilterten Zeitraum wird die Nachfrage berechnet:

```python
for day in range(start_day, min(end_day + 1, 365)):
    current_date = start_date + timedelta(days=day)
    is_workday = workday_calc.is_workday(day)
    
    if is_workday:
        # Berechne geplante und tatsächliche Nachfrage
        for product in MasterData.BOM.keys():
            planned_demand = calculate_product_demand(day, product, include_marketing=False)
            actual_demand = calculate_product_demand(day, product, include_marketing=True)
    else:
        # An Feiertagen/Wochenenden: Alle Nachfragen sind 0
        planned_demand = 0
        actual_demand = 0
```

**Wichtig**: An Feiertagen und Wochenenden ist die Nachfrage immer 0, unabhängig von der Carry-Over-Logik. Der Rest bleibt unverändert und wird zum nächsten Arbeitstag übertragen.

#### Schritt 3: Visualisierung

Die Seite markiert Feiertage und Wochenenden rot in der Tabelle, um sie visuell hervorzuheben.

## Marketing-Add-ons Berechnung

Marketing-Add-ons werden wie folgt berechnet:

1. **Aktive Marketing-Szenarien abrufen**: Für jeden Tag werden alle aktiven Marketing-Szenarien abgerufen.

2. **Base-Daily-Float berechnen**: Die monatliche Base-Daily-Float wird für den aktuellen Monat berechnet.

3. **Add-on berechnen**: Für jedes Marketing-Szenario wird der Add-on berechnet:
   ```python
   factor = scenario.demand_increase_factor  # z.B. 1.5 (50% mehr)
   base_float = base_daily_floats.get(product, 0.0)
   add_on = base_float * (factor - 1.0)  # z.B. 0.5 * base_float
   ```

4. **Add-ons summieren**: Wenn mehrere Marketing-Szenarien aktiv sind, werden die Add-ons summiert.

5. **Nach Rundung addieren**: Die Marketing-Add-ons werden nach der Rundung der Basis-Nachfrage addiert und gehen nicht in den Rest ein.

## Summenzeilen

Beide Tabs (wöchentlich und täglich) haben eine Summenzeile am Ende der Tabelle. Diese wird grau hinterlegt und fett dargestellt, um sie visuell hervorzuheben.

**Berechnung**:
```python
sum_row[(product, 'Geplanter Bedarf')] = display_df[(product, 'Geplanter Bedarf')].sum()
sum_row[(product, 'Tatsächlicher Bedarf')] = display_df[(product, 'Tatsächlicher Bedarf')].sum()
```

## Visualisierungen

### Wöchentliche Planung

1. **Schichten-Visualisierung**: Ein Balkendiagramm zeigt die Anzahl der Schichten pro Kalenderwoche.

2. **Fahrrad-Vergleich über Kalenderwochen**: Ein Liniendiagramm zeigt die Nachfrage für jedes Produkt über die Kalenderwochen.

3. **Fahrrad-Vergleich (Gestapelt)**: Ein gestapeltes Balkendiagramm zeigt die Nachfrage für alle Produkte pro Kalenderwoche.

### Tägliche Planung

1. **Tägliche Entwicklung (Tatsächlicher Bedarf)**: Ein gestapeltes Balkendiagramm zeigt die tägliche Nachfrage für alle Produkte.

2. **Statistiken**: Metriken wie Durchschnitt, Gesamt, Maximum und Minimum für geplante und tatsächliche Nachfrage.

## Behobene Probleme

### Floating-Point-Fehler in der Carry-Over-Logik (BEHOBEN)

**Initialer Fehler**: Die Berechnung ergab 369.999 statt 370.000 als Jahresgesamtsumme. Einzelne Produkte wie MTB Performance zeigten 44.399 statt 44.400.

**Ursache**: 
1. **Floating-Point-Arithmetik**: Durch die Division der monatlichen Nachfrage durch die Anzahl der Arbeitstage entstanden Dezimalstellen (z.B. 60.54545454545455). Beim Addieren des Rests vom Vortag (z.B. 0.45454545454543904) ergab sich durch Floating-Point-Ungenauigkeiten ein Wert wie 60.999999999999986 statt exakt 61.0. Dies führte dazu, dass `math.floor(60.999999999999986)` = 60 statt 61 ergab.

2. **Reste am letzten Arbeitstag**: Die Reste wurden am letzten Arbeitstag des Jahres nicht korrekt aufsummiert, da `is_last_workday_of_year` nicht gesetzt wurde.

3. **Verkaufsanteile-Berechnung**: Die Division durch `total_share` (≈0.9999999999999999) verursachte zusätzliche Abweichungen.

**Lösung**:
1. **Präzisions-Rundung**: Base + Rest wird auf 12 Dezimalstellen gerundet, um Floating-Point-Fehler zu minimieren.
2. **Ganzzahl-Erkennung**: Wenn `base_with_remainder` sehr nahe an einer ganzen Zahl ist (< 1e-10), wird direkt auf diese ganze Zahl gerundet, anstatt `math.floor()` zu verwenden.
3. **Reste-Rundung**: Reste werden auf 12 Dezimalstellen gerundet, um Konsistenz zu gewährleisten.
4. **Letzter Arbeitstag**: `is_last_workday_of_year` wird jetzt korrekt in der Volumenplanung gesetzt, sodass Reste am Jahresende aufsummiert werden.
5. **Direkte Verkaufsanteile**: Verkaufsanteile werden direkt verwendet, ohne durch `total_share` zu teilen (entspricht Excel-Formel).

**Ergebnis**: Die Jahresgesamtsumme beträgt jetzt exakt 370.000 für beide Planungen (wöchentlich und täglich).

### KW 5 Problem

In Kalenderwoche 5 wird für "MTB Allrounder" 1057 statt 1058 angezeigt. Dies ist ein bekanntes Problem mit der Carry-Over-Logik, das noch nicht vollständig gelöst wurde.

**Mögliche Ursachen**:
- Die Carry-Over-Logik funktioniert nicht korrekt bei bestimmten Kombinationen von Feiertagen und Wochenenden.
- Die Rundung könnte an einer Stelle falsch sein.

## Code-Kommentare

### Ausreichende Kommentare vorhanden

Die Seite hat bereits gute Kommentare, besonders bei kritischen Stellen:

1. **Sequenzielle Berechnung**: Zeile 136-138 erklärt, warum die sequenzielle Berechnung kritisch ist.

2. **Carry-Over-Logik**: Zeile 168 erklärt, dass die Berechnung für alle Produkte gleichzeitig erfolgen muss.

3. **Feiertags-Behandlung**: Zeile 178-181 erklärt, dass an Feiertagen/Wochenenden die Nachfrage 0 ist.

4. **Schichten-Berechnung**: Zeile 245-283 erklärt die Excel-Formel-Logik detailliert.

5. **ISO-Wochen-Berechnung**: Zeile 189-201 erklärt die ISO-Wochen-Logik.

### Verbesserungsvorschläge

1. **Marketing-Add-ons Berechnung**: Die Berechnung der Marketing-Add-ons (Zeile 150-166) könnte detaillierter kommentiert werden, insbesondere warum der Add-on nach der Rundung addiert wird.

2. **Summenzeilen-Berechnung**: Die Berechnung der Summenzeilen (Zeile 336-350) könnte erklärt werden, warum sie separat berechnet wird.

3. **Visualisierungen**: Die Visualisierungen könnten Kommentare haben, die erklären, welche Daten dargestellt werden.

## Abhängigkeiten

- `DemandCalculator`: Berechnet die tägliche Nachfrage mit Carry-Over-Logik
- `WorkdayCalculator`: Prüft, ob ein Tag ein Arbeitstag ist
- `MasterData`: Stammdaten (BOM, Saisonalität, Verkaufsanteile, etc.)
- `ScenarioManager`: Verwaltet Marketing-Szenarien
- `HolidaysConfig`: Feiertags-Konfiguration

## Performance-Überlegungen

Die sequenzielle Berechnung aller 365 Tage kann bei vielen Produkten und Marketing-Szenarien langsam sein. Die Seite optimiert dies, indem sie die Berechnung nur einmal durchführt und die Ergebnisse in Dictionaries speichert, die dann für die wöchentliche Aggregation verwendet werden.

## Zusammenfassung

Die Volumenplanung-Seite ist eine komplexe Seite, die die Nachfrage für alle Produkte berechnet und visualisiert. Die wichtigsten Konzepte sind die Carry-Over-Logik, die sequenzielle Berechnung und die Schichten-Berechnung. Die Seite hat bereits gute Kommentare, könnte aber an einigen Stellen noch detaillierter sein.

