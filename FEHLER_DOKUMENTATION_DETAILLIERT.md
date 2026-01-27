# Detaillierte Fehler-Dokumentation

**Datum:** 27.01.2026  
**Analysemethode:** Systematische Code-Analyse von hinten nach vorne

---

## 🔴 KRITISCHE FEHLER (Sofort beheben)

### FEHLER-001: Parameter-Inkonsistenz `yearly_volume` vs `total_volume`

**Beschreibung:**
Es existieren zwei verschiedene Parameter für dasselbe Konzept:
- `st.session_state.yearly_volume` (Standard: 370000)
- `MasterData.GLOBAL_CONFIG['total_volume']` (Standard: 370000)
- `st.session_state.editable_global_config['total_volume']` (editierbar)

**Betroffene Dateien:**
- `ui/utils.py` Zeile 27, 55
- `ui/volume_planning_utils.py` Zeile 34
- `config/master_data.py` Zeile 100
- `pages/8_stammdaten.py` Zeile 38, 210, 226
- `simulation/production_planner.py` Zeile 124

**Problem:**
1. Wenn `editable_global_config['total_volume']` geändert wird, wird `yearly_volume` NICHT aktualisiert
2. `ProductionPlanner` verwendet `GLOBAL_CONFIG.get('total_volume', 370000)` als Fallback statt `yearly_volume`
3. Cache wird nicht invalidiert wenn `total_volume` geändert wird

**Auswirkung:**
- Inkonsistente Berechnungen zwischen Volumenplanung und Produktion
- Cache zeigt veraltete Werte
- Unterschiedliche Ergebnisse je nachdem welche Quelle verwendet wird

**Lösung:**
1. Synchronisiere `yearly_volume` mit `editable_global_config['total_volume']`
2. Verwende `yearly_volume` überall statt `GLOBAL_CONFIG['total_volume']`
3. Invalidiere Cache wenn `total_volume` geändert wird

**Test:** `tests/test_parameter_consistency.py::test_yearly_volume_sync`

---

### FEHLER-002: Cache wird nicht invalidiert bei Parameteränderungen

**Beschreibung:**
Wenn Parameter geändert werden (`yearly_volume`, `editable_global_config`, etc.), werden Caches nicht invalidiert.

**Betroffene Caches:**
- `volume_planning_cache_key`
- `production_logs_cache`
- `material_inventory_data`
- `simulation_cache`

**Betroffene Dateien:**
- `pages/8_stammdaten.py` Zeile 229-231 (keine Cache-Invalidierung)
- `ui/volume_planning_utils.py` (Cache-Key enthält `yearly_volume`, aber wird nicht aktualisiert)
- `ui/production_calculations.py` (Cache-Key enthält `volume_planning_cache_key`)

**Problem:**
- Änderungen haben keine sofortige Auswirkung
- Benutzer muss App neu starten um Änderungen zu sehen
- Inkonsistente Werte zwischen verschiedenen Berechnungen

**Lösung:**
1. Implementiere Cache-Invalidierung wenn Parameter geändert werden
2. Setze `volume_planning_calculated = False` wenn `yearly_volume` geändert wird
3. Lösche alle abhängigen Caches

**Test:** `tests/test_parameter_consistency.py::test_parameter_change_invalidates_cache`

---

### FEHLER-003: Nicht-deterministische Produktreihenfolge

**Beschreibung:**
`MasterData.BOM.keys()` wird ohne Sortierung verwendet, was zu unterschiedlichen Rang-Berechnungen führen kann.

**Betroffene Dateien:**
- `ui/production_calculations.py` Zeile 118, 358, 409, 492, 516
- `simulation/production_planner.py` (verwendet auch `BOM.keys()`)

**Problem:**
- Python-Dict-Reihenfolge ist zwar stabil (ab 3.7), aber nicht garantiert deterministisch
- Rang-Berechnung hängt von Reihenfolge ab
- Unterschiedliche Ergebnisse bei Neuladen (z.B. 1799 vs 1760 für Extreme)

**Auswirkung:**
- Nicht-deterministische Produktionsmengen
- Unterschiedliche Werte bei Neuladen
- Inkonsistente Ergebnisse zwischen verschiedenen Ausführungen

**Lösung:**
1. Verwende `sorted(MasterData.BOM.keys())` überall
2. Stelle sicher dass alle Iterationen über Produkte sortiert sind

**Test:** `tests/test_circular_dependencies.py::test_product_order_deterministic`

---

### FEHLER-004: Kein Konvergenz-Check für iterative Berechnung

**Beschreibung:**
Production ↔ Material Zirkelbezug wird durch genau 2 Iterationen gelöst, aber ohne Prüfung ob Werte konvergiert sind.

**Betroffene Dateien:**
- `ui/page_initialization.py` Zeile 39-63
- `ui/production_calculations.py`
- `ui/material_calculations.py`

**Problem:**
- Werte könnten oszillieren
- Nicht-deterministische Ergebnisse
- Unterschiedliche Werte bei Neuladen

**Auswirkung:**
- Inkonsistente Produktionsmengen
- Unterschiedliche Materialbestände
- Unvorhersagbare Ergebnisse

**Lösung:**
1. Implementiere Konvergenz-Check
2. Prüfe ob `production_logs_cache` sich zwischen Iterationen ändert
3. Stoppe wenn Konvergenz erreicht ist (max. 5 Iterationen)

**Test:** `tests/test_circular_dependencies.py::test_convergence_required`

---

### FEHLER-005: Division durch Null möglich

**Beschreibung:**
Mehrere Stellen wo Division durch Null auftreten könnte ohne Prüfung.

**Betroffene Stellen:**

1. **`demand_calculator.py` Zeile 70:**
   ```python
   base_daily_float[product] = monthly_target_product / num_workdays
   ```
   - `num_workdays` könnte 0 sein (Fallback auf 1 vorhanden, aber unsicher)

2. **`production_calculations.py` Zeile 116:**
   ```python
   proportional = math.floor(demand * daily_capacity / total_production_demand)
   ```
   - `total_production_demand` könnte 0 sein (Prüfung vorhanden, aber `daily_capacity` könnte 0 sein)

3. **`volume_planning_utils.py` Zeile 186:**
   ```python
   target_sum = int(yearly_volume * sales_share)
   ```
   - `yearly_volume` könnte 0 sein (keine Prüfung)

**Lösung:**
1. Füge Prüfungen für Division durch Null hinzu
2. Verwende Fallback-Werte wenn Division nicht möglich
3. Validiere Parameter bevor Berechnung

**Test:** `tests/test_edge_cases.py::test_division_by_zero_protection`

---

## 🟡 MITTLERE FEHLER (Bald beheben)

### FEHLER-006: `GLOBAL_CONFIG` wird nicht aus `editable_global_config` aktualisiert

**Beschreibung:**
Änderungen in `editable_global_config` werden nicht zurück in `MasterData.GLOBAL_CONFIG` geschrieben.

**Betroffene Dateien:**
- `pages/8_stammdaten.py` Zeile 38, 210, 226
- `simulation/production_planner.py` Zeile 137-138 (verwendet `GLOBAL_CONFIG` direkt)

**Problem:**
- Code verwendet `MasterData.GLOBAL_CONFIG` direkt
- Änderungen haben keine Auswirkung auf Berechnungen

**Lösung:**
1. Verwende `editable_global_config` statt `GLOBAL_CONFIG` in Berechnungen
2. Oder: Synchronisiere `GLOBAL_CONFIG` mit `editable_global_config`

---

### FEHLER-007: Exception-Handling zu breit

**Beschreibung:**
`page_initialization.py` verwendet `except Exception: pass`, was Fehler stillschweigend ignoriert.

**Betroffene Dateien:**
- `ui/page_initialization.py` Zeile 42, 49, 62

**Problem:**
- Fehler werden nicht geloggt
- Schwer zu debuggen
- Probleme werden nicht erkannt

**Lösung:**
1. Spezifischere Exception-Typen
2. Logging hinzufügen
3. Fehler anzeigen statt ignorieren

---

### FEHLER-008: Keine Validierung für Parameter-Bereiche

**Beschreibung:**
Parameter können ungültige Werte haben (negativ, 0, außerhalb gültiger Bereiche).

**Betroffene Parameter:**
- `yearly_volume` (könnte negativ sein)
- `capacity_per_hour` (könnte 0 sein)
- `max_shifts_per_day` (könnte < `min_shifts_per_day` sein)
- `PRODUCT_SALES_SHARES` (Summe könnte != 1.0 sein)

**Lösung:**
1. Validierung beim Setzen von Parametern
2. Prüfung auf gültige Bereiche
3. Fehlermeldungen wenn ungültig

**Test:** `tests/test_parameter_consistency.py::test_global_config_values_positive`

---

## 🟢 NIEDRIGE FEHLER (Verbesserung)

### FEHLER-009: Code-Duplikation

**Beschreibung:**
Ähnliche Logik ist mehrfach vorhanden (z.B. Rang-Berechnung in `production_planner.py` und `production_calculations.py`).

**Lösung:**
1. Gemeinsame Funktionen extrahieren
2. Code-Wiederverwendung

---

### FEHLER-010: Fehlende Dokumentation

**Beschreibung:**
Einige Funktionen haben keine oder unvollständige Docstrings.

**Lösung:**
1. Docstrings hinzufügen
2. Parameter dokumentieren
3. Rückgabewerte dokumentieren

---

## Zusammenfassung: Prioritäten

### Sofort beheben (🔴):
1. Parameter-Inkonsistenz `yearly_volume` vs `total_volume`
2. Cache-Invalidierung bei Parameteränderungen
3. Nicht-deterministische Produktreihenfolge
4. Konvergenz-Check für iterative Berechnung
5. Division durch Null

### Bald beheben (🟡):
1. `GLOBAL_CONFIG` Synchronisation
2. Exception-Handling verbessern
3. Parameter-Validierung

### Später verbessern (🟢):
1. Code-Duplikation reduzieren
2. Dokumentation ergänzen

---

## Test-Abdeckung

Die Tests decken folgende Bereiche ab:

- ✅ Parameter-Konsistenz
- ✅ Zirkuläre Abhängigkeiten
- ✅ Edge Cases
- ✅ Datenkonsistenz
- ✅ Robustheit

**Ausführung:**
```bash
pytest tests/ -v
```
