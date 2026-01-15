# Page: Stammdaten (8_stammdaten.py)

## Übersicht

Die Stammdaten-Seite zeigt alle Stammdaten der Supply Chain Simulation logisch gruppiert in 6 Tabs. Sie dient als Referenz für alle konfigurierbaren Parameter der Simulation.

## Zweck und Funktionalität

Die Seite dient als zentrale Referenz für alle Stammdaten. Sie zeigt:
- **Stückliste (BOM)**: Produktstruktur aller Bike-Modelle
- **Planung**: Planungsparameter (Volumen, Kapazität, etc.)
- **Märkte & Kunden**: Marktverteilung und Transitzeiten
- **Auslieferung**: Auslieferungsparameter
- **Beschaffung**: Beschaffungsparameter (China)
- **Feiertage**: Feiertagskonfiguration (DE, CN, etc.)

## Detaillierte Berechnungslogik

### 1. Stückliste (BOM)

Die Seite zeigt die Bill of Materials (BOM) für alle Produkte:

```python
for product, components in MasterData.BOM.items():
    bom_data.append({
        'Endprodukt': product,
        'Rahmen': components['frame'],
        'Sattel': components['saddle'],
        'Gabel': components['fork']
    })
```

**Was zeigt die BOM?**

Die BOM zeigt, welche Komponenten für jedes Fahrrad-Modell benötigt werden:
- **Rahmen**: Aluminium oder Carbon
- **Sattel**: Spark, Speedline, Fizik Tundra, etc.
- **Gabel**: Fox32 F100, Fox Talas140, etc.

### 2. Planung

Die Seite zeigt Planungsparameter:
- **Globale Konfiguration**: Volumen, Kapazität, Schichten, etc.
- **Tägliche Arbeitslast**: Arbeitslast pro Wochentag
- **Verkaufsanteile**: Verkaufsanteile pro Produkt
- **Saisonalität**: Saisonalitätsfaktoren pro Monat

**Visualisierung**: Die Saisonalität wird als Balkendiagramm dargestellt.

### 3. Märkte & Kunden

Die Seite zeigt Marktverteilung und Transitzeiten:

```python
for market_code, market_params in MasterData.MARKETS.items():
    market_data.append({
        'Markt': market_code,
        'Anteil': f"{market_params['share'] * 100:.1f}%",
        'Transitzeit (Tage)': market_params['transit_days']
    })
```

**Visualisierung**: Die Marktverteilung wird als Kreisdiagramm dargestellt.

### 4. Auslieferung

Die Seite zeigt Auslieferungsparameter:
- Transitzeiten pro Markt
- Auslieferungslogik

### 5. Beschaffung

Die Seite zeigt Beschaffungsparameter für China:
- Losgröße
- Transportzeiten
- Produktionszeiten

### 6. Feiertage

Die Seite zeigt alle Feiertage für alle relevanten Länder:

```python
all_holidays = HolidaysConfig.get_all_holidays(2026)
```

**Länder**:
- Deutschland (DE)
- China (CN)
- USA
- Frankreich (FR)
- Schweiz (CH)
- Österreich (AT)

## Abhängigkeiten

- `MasterData`: Für alle Stammdaten
- `HolidaysConfig`: Für Feiertagskonfiguration

## Besonderheiten

### Statische Daten

Die Seite zeigt nur statische Daten. Es werden keine Berechnungen durchgeführt, sondern nur die konfigurierten Werte angezeigt.

### Visualisierungen

Die Seite nutzt Visualisierungen (Balkendiagramme, Kreisdiagramme), um die Daten anschaulich darzustellen.

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Tab-Struktur (Zeile 38-45)
- Datenstruktur (Zeile 52-60)

## Zusammenfassung

Die Stammdaten-Seite dient als zentrale Referenz für alle konfigurierbaren Parameter der Simulation. Sie zeigt die Daten logisch gruppiert in 6 Tabs und nutzt Visualisierungen, um die Daten anschaulich darzustellen.

