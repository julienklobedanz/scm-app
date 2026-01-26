# SupplierBreakdownScenario - Status Quo & Fehlende Implementierung

## Status Quo

### ✅ Bereits implementiert:

1. **Klasse existiert** (`models/scenarios.py`)
   - `component_type: str = "all"` - "frames", "saddles", "all"
   - Wird im `ScenarioManager` verwaltet

2. **Simulator-Integration** (`simulation/simulator.py`, Zeile 230-234)
   - Prüft aktive SupplierBreakdownScenario
   - Setzt `supplier_blocked_saddles` Flag
   - Blockiert Bestellungen wenn aktiv (Zeile 345: `if not supplier_blocked_saddles`)

3. **UI existiert** (`ui/scenario_sidebar.py`, Zeile 113-130)
   - Erlaubt Start-/Enddatum
   - **ABER:** Nur "saddles" als Option (keine Auswahl)

4. **Cache-Key berücksichtigt** (`ui/volume_planning_utils.py`, Zeile 64)
   - `component_type` ist im Fingerprint

### ⚠️ Teilweise implementiert / Probleme:

1. **`place_order()` prüft SupplierBreakdownScenario NICHT direkt**
   - Aktuell: Nur Kommentar "Prüfe Produktionsprobleme beim Lieferanten"
   - `production_loss_percentage = 0.0` wird gesetzt, aber nie verwendet
   - **FEHLT:** Prüfung ob SupplierBreakdownScenario aktiv ist → Bestellung blockieren

2. **Störung wird nur angezeigt wenn `production_loss_percentage > 0`**
   - `get_supplier_log_dataframe()` (Zeile 725): `if status.get('production_loss_percentage', 0.0) > 0`
   - **PROBLEM:** SupplierBreakdownScenario setzt `production_loss_percentage` nicht
   - **FEHLT:** Störung muss auch bei SupplierBreakdownScenario angezeigt werden

3. **Bestelleingang wird nicht auf 0 gesetzt**
   - `get_supplier_log_dataframe()` berechnet Bestelleingang aus Volumenplanung
   - **FEHLT:** Wenn SupplierBreakdownScenario aktiv → Bestelleingang = 0

4. **Produktionsmenge wird nicht auf 0 gesetzt**
   - `get_supplier_log_dataframe()` berechnet Produktionsmenge aus freigegebenen Bestellungen
   - **FEHLT:** Wenn SupplierBreakdownScenario aktiv → Produktionsmenge = 0

5. **Nicht sattelspezifisch**
   - Aktuell: Nur "saddles" oder "all"
   - **FEHLT:** Multi-Select für spezifische Satteltypen (wie bei Marketingaktion)

## Datenfluss-Analyse

### Aktueller Datenfluss:

```
Simulator.run()
  ↓
supplier_blocked_saddles = any(...)  ✅ Prüft Szenario
  ↓
if not supplier_blocked_saddles:     ✅ Blockiert Bestellungen
    procurement_manager.check_and_order()
        ↓
        china_transport_manager.place_order()  ❌ Prüft Szenario NICHT
```

### Problem:

1. **`place_order()` wird auch direkt aufgerufen** (z.B. aus `ProcurementManager`)
   - Keine Prüfung ob SupplierBreakdownScenario aktiv ist
   - Bestellung wird trotzdem platziert

2. **`get_supplier_log_dataframe()` berechnet Bestelleingang unabhängig**
   - Verwendet `_calculate_order_quantity_from_volume_planning()`
   - Berücksichtigt SupplierBreakdownScenario nicht
   - **Ergebnis:** Bestelleingang wird angezeigt, obwohl Störung aktiv ist

## Fehlende Implementierung

### 1. Sattelspezifische Auswahl (wie Marketingaktion)

**Änderungen:**
- `SupplierBreakdownScenario.affected_saddles: Optional[List[str]]`
- UI: Multi-Select für Satteltypen
- Prüfung: Nur betroffene Sättel blockieren

### 2. `place_order()` erweitern

**Aktuell:**
```python
def place_order(self, order_day: int, quantity: float) -> int:
    # Prüfe Produktionsprobleme beim Lieferanten (z.B. SupplierBreakdownScenario)
    production_loss_percentage = 0.0  # ❌ Wird nie gesetzt
```

**Benötigt:**
```python
def place_order(self, order_day: int, quantity: float) -> int:
    # Prüfe SupplierBreakdownScenario
    if self.scenario_manager:
        breakdowns = self.scenario_manager.get_supplier_breakdown_scenarios(order_day)
        if breakdowns:
            # Blockiere Bestellung (return None oder 0)
            return None  # oder raise Exception
```

### 3. `get_supplier_log_dataframe()` anpassen

**Aktuell:**
- Bestelleingang: Berechnet aus Volumenplanung (ignoriert Störung)
- Produktionsmenge: Berechnet aus freigegebenen Bestellungen (ignoriert Störung)
- Störung: Nur wenn `production_loss_percentage > 0`

**Benötigt:**
- Bestelleingang: Wenn SupplierBreakdownScenario aktiv → 0
- Produktionsmenge: Wenn SupplierBreakdownScenario aktiv → 0
- Störung: Wenn SupplierBreakdownScenario aktiv → "Ja"

### 4. `_calculate_order_quantity_from_volume_planning()` anpassen

**Aktuell:**
- Berechnet Bestellmenge aus Volumenplanung
- Ignoriert SupplierBreakdownScenario

**Benötigt:**
- Prüfe SupplierBreakdownScenario für den Sattel
- Wenn aktiv → return 0.0

### 5. Cache-Key erweitern

**Aktuell:**
```python
elif isinstance(s, SupplierBreakdownScenario):
    extra = (getattr(s, "component_type", None),)
```

**Benötigt:**
```python
elif isinstance(s, SupplierBreakdownScenario):
    affected_saddles = getattr(s, "affected_saddles", None)
    affected_saddles_tuple = tuple(sorted(affected_saddles)) if affected_saddles else None
    extra = (getattr(s, "component_type", None), affected_saddles_tuple)
```

## Implementierungsreihenfolge

1. **Erweitere SupplierBreakdownScenario** (`models/scenarios.py`)
   - `affected_saddles: Optional[List[str]]` hinzufügen

2. **UI erweitern** (`ui/scenario_sidebar.py`)
   - Multi-Select für Satteltypen (wie Marketingaktion)

3. **`place_order()` anpassen** (`simulation/china_transport.py`)
   - Prüfe SupplierBreakdownScenario
   - Blockiere Bestellung wenn aktiv

4. **`get_supplier_log_dataframe()` anpassen** (`simulation/china_transport.py`)
   - Bestelleingang: Prüfe SupplierBreakdownScenario → 0 wenn aktiv
   - Produktionsmenge: Prüfe SupplierBreakdownScenario → 0 wenn aktiv
   - Störung: Zeige "Ja" wenn SupplierBreakdownScenario aktiv

5. **`_calculate_order_quantity_from_volume_planning()` anpassen** (`simulation/china_transport.py`)
   - Prüfe SupplierBreakdownScenario für den Sattel
   - Return 0.0 wenn aktiv

6. **Cache-Key erweitern** (`ui/volume_planning_utils.py`, `simulation/china_transport.py`)
   - `affected_saddles` in Fingerprint aufnehmen

7. **Simulator anpassen** (`simulation/simulator.py`)
   - Prüfe `affected_saddles` statt nur `component_type`

## Kritische Aspekte

### ⚠️ WICHTIG:

1. **Rückwärtskompatibilität:**
   - Bestehende Szenarien mit `component_type="saddles"` müssen weiter funktionieren
   - Wenn `affected_saddles=None` → alle Sättel betroffen (wie bisher)

2. **Konsistenz:**
   - Bestelleingang = 0 → Freigegebene Bestellungen = 0 → Produktionsmenge = 0
   - Störung muss in allen betroffenen Zeilen angezeigt werden

3. **Cache-Invalidierung:**
   - `affected_saddles` muss im Cache-Key sein
   - Änderung der Sattelauswahl muss Cache invalidierten

4. **Datenfluss:**
   - SupplierBreakdownScenario muss in **allen** Stellen geprüft werden:
     - `place_order()` - Blockiert Bestellung
     - `get_supplier_log_dataframe()` - Zeigt Störung, setzt Mengen auf 0
     - `_calculate_order_quantity_from_volume_planning()` - Return 0.0
     - `simulator.py` - Blockiert Bestellungen (bereits implementiert)

## Zusammenfassung

**Status:** ⚠️ Teilweise implementiert
- Simulator blockiert Bestellungen ✅
- Aber: `place_order()` prüft nicht direkt ❌
- Aber: Bestelleingang/Produktionsmenge werden nicht auf 0 gesetzt ❌
- Aber: Störung wird nicht korrekt angezeigt ❌
- Aber: Nicht sattelspezifisch ❌

**Nächste Schritte:**
1. Sattelspezifische Auswahl (wie Marketingaktion)
2. Vollständige Integration in Datenfluss
3. Korrekte Anzeige in Lieferant China Tabelle
