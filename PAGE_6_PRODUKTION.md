# Page: Produktion (6_produktion.py)

## Übersicht

Die Produktion-Seite zeigt die Produktionsplanung, tatsächliche Produktion und Materialverfügbarkeit für jedes Produkt separat. Sie visualisiert den kompletten Produktionsprozess.

## Zweck und Funktionalität

Die Seite dient zur Überwachung der Produktion. Sie zeigt für jedes Produkt:
- **Geplante PM**: Geplante Produktionsmenge
- **Tatsächliche PM**: Tatsächliche Produktionsmenge
- **Fertiggestellte PM**: Fertiggestellte Produktionsmenge
- **Backlog**: Unerfüllte Nachfrage
- **Auslastung (%)**: Auslastung der Produktionskapazität
- **Material-Bestände**: Bestände für Frames (Alu/Carbon), Sättel und Gabeln

## Detaillierte Berechnungslogik

### 1. Datenbeschaffung

Die Seite nutzt die Funktion `get_production_logs()`, die die Produktionslogs direkt aus dem `ProductionPlanner` liest:

```python
planner = st.session_state.simulator.production_planner
production_logs = planner.production_logs
```

**Warum direkt aus dem ProductionPlanner?**

Die Produktionslogs sind die "Single Source of Truth" für alle Produktionsdaten. Sie werden während der Simulation vom `ProductionPlanner` erstellt und enthalten alle relevanten Informationen.

### 2. Produktionslogs-Struktur

Die Produktionslogs sind als Dictionary organisiert: `{product: [log_entries]}`

Jeder Log-Eintrag enthält:
- **Datum**: Tag der Produktion
- **Geplante PM**: Geplante Produktionsmenge
- **Tatsächliche PM**: Tatsächliche Produktionsmenge (kann durch Materialmangel reduziert sein)
- **Fertiggestellte PM**: Fertiggestellte Produktionsmenge
- **Backlog**: Unerfüllte Nachfrage
- **Auslastung (%)**: Auslastung der Produktionskapazität
- **Material-Bestände**: Bestände für Frames, Sättel und Gabeln

### 3. Auslastungsberechnung

Die Auslastung wird wie folgt berechnet:

```python
utilization = (actual_qty / planned_pm * 100) if planned_pm > 0 else 0
```

**Interpretation**:
- `utilization = 100%`: Die geplante Produktion wurde vollständig erreicht
- `utilization < 100%`: Die Produktion wurde durch Materialmangel reduziert
- `utilization > 100%`: Sollte nicht vorkommen (kann durch Rundungsfehler entstehen)

### 4. Material-Bestände

Die Seite zeigt die Material-Bestände für:
- **Frames (Alu)**: Aluminium-Rahmen
- **Frames (Carbon)**: Carbon-Rahmen
- **Sättel**: Sattel-Bestände (pro Sattel-Typ)
- **Gabeln**: Gabel-Bestände

Diese Bestände werden aus dem `Inventory` des Simulators gelesen.

### 5. Visualisierung

Die Seite zeigt für jedes Produkt:
- **Tabelle**: Alle Produktionsdaten in tabellarischer Form
- **Liniendiagramm**: Geplante, tatsächliche und fertiggestellte PM über das Jahr
- **Auslastungs-Diagramm**: Auslastung über das Jahr

## Abhängigkeiten

- `ProductionPlanner`: Für Produktionslogs
- `Inventory`: Für Material-Bestände
- `MasterData`: Für Stammdaten (BOM, etc.)

## Besonderheiten

### Single Source of Truth

Die Seite nutzt die Produktionslogs als "Single Source of Truth". Dies stellt sicher, dass die Daten konsistent sind und nicht mehrfach berechnet werden müssen.

### Formatierung

Die Seite formatiert die Daten für die Anzeige:
- **Auslastung (%)**: Wird auf 1 Dezimalstelle gerundet, oder 0 wenn < 0.05
- **Material-Bestände**: Werden auf ganze Zahlen gerundet

## Code-Kommentare

Die Seite hat ausreichende Kommentare, besonders bei:
- Datenbeschaffung (Zeile 54-74)
- Formatierung (Zeile 100-120)

## Zusammenfassung

Die Produktion-Seite zeigt den kompletten Produktionsprozess für jedes Produkt. Sie nutzt die Produktionslogs als "Single Source of Truth" und visualisiert die Daten in übersichtlichen Tabellen und Diagrammen.

