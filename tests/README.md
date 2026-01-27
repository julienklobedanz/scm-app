# Test-Dokumentation

## Übersicht

Diese Tests prüfen die Robustheit und Konsistenz der SCM App. Sie decken folgende Bereiche ab:

1. **Parameter-Konsistenz** (`test_parameter_consistency.py`)
   - Prüft ob Parameter konsistent sind
   - Validiert Summen (PRODUCT_SALES_SHARES, SEASONALITY, etc.)
   - Prüft ob Werte in gültigen Bereichen sind

2. **Zirkuläre Abhängigkeiten** (`test_circular_dependencies.py`)
   - Prüft ob Berechnungen deterministisch sind
   - Dokumentiert Anforderungen für Konvergenz-Check

3. **Edge Cases** (`test_edge_cases.py`)
   - Prüft Behandlung von extremen Werten
   - Division durch Null
   - Negative Tage, Tage > 365
   - Leere Collections

4. **Datenkonsistenz** (`test_data_consistency.py`)
   - Prüft Konsistenz zwischen verschiedenen Datenquellen
   - BOM vs PRODUCT_SALES_SHARES
   - SUPPLIERS vs CHINA_SUPPLIER

5. **Robustheit** (`test_robustness.py`)
   - Prüft Widerstandsfähigkeit unter verschiedenen Bedingungen
   - Mehrfache Berechnungen
   - Extreme Parameterkombinationen

## Ausführung

### Alle Tests ausführen:
```bash
pytest tests/ -v
```

### Spezifische Test-Datei:
```bash
pytest tests/test_parameter_consistency.py -v
```

### Mit Coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Bekannte Probleme

Die Tests dokumentieren auch bekannte Probleme, die behoben werden müssen:

1. **Parameter-Synchronisation:** `yearly_volume` und `total_volume` sind nicht synchronisiert
2. **Cache-Invalidierung:** Parameteränderungen invalidierten Cache nicht
3. **Nicht-Determinismus:** Produktreihenfolge ist nicht stabilisiert
4. **Konvergenz-Check:** Fehlt für iterative Berechnung

## Erweiterte Tests

Für umfassendere Tests sollten zusätzlich implementiert werden:

1. **Integrationstests:** Vollständige Simulation durchführen
2. **Performance-Tests:** Prüfen ob Berechnungen in akzeptabler Zeit laufen
3. **Stress-Tests:** Extrem viele Szenarien gleichzeitig
4. **Regression-Tests:** Prüfen ob bekannte Bugs nicht wieder auftreten
