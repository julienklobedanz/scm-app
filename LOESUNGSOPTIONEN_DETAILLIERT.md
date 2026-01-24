# Lösungsoptionen für Materialverbrauch-Problem - Detaillierte Analyse

## Problem-Zusammenfassung

**Aktuelles Problem:**
- Statische Simulation verbraucht Material basierend auf `production_by_product` (z.B. 811)
- Dynamische Neuberechnung produziert andere Werte (z.B. 786)
- Materiallager liest "tatsächliche PM" aus `production_logs_cache` (786)
- **Ergebnis:** Materialabgang (811) ≠ Tatsächliche PM (786)

**Betroffene Stellen:**
- `simulation/simulator.py`: Verbraucht Material über `consume_components()`
- `ui/production_calculations.py`: Dynamische Neuberechnung produziert andere Werte
- `ui/material_calculations.py`: Liest "tatsächliche PM" aus `production_logs_cache`

---

## Option 1: Materiallager verwendet statische Werte

### Technische Umsetzung

**Änderungen:**
1. `ui/material_calculations.py`: Liest "tatsächliche PM" aus statischen `production_logs` statt `production_logs_cache`
2. Keine Änderungen in `simulation/simulator.py` oder `ui/production_calculations.py`

**Code-Änderung:**
```python
# ALT (ui/material_calculations.py, Zeile 106):
if product_name in production_logs_cache:
    df = production_logs_cache[product_name]

# NEU:
# Verwende statische production_logs direkt
planner = st.session_state.simulator.production_planner
if product_name in planner.production_logs:
    logs = planner.production_logs[product_name]
    df = pd.DataFrame(logs)
```

### Auswirkungen auf Datenfluss

**✅ Vorteile:**
- Materialverbrauch = Statische Produktion (konsistent)
- Keine Änderungen an bestehender Logik
- Einfache Implementierung

**❌ Nachteile:**
- **Materiallager reagiert NICHT auf Marketing-Szenarien**
- **Materiallager reagiert NICHT auf Materialverfügbarkeits-Änderungen**
- Inkonsistenz zwischen Produktionstabelle (dynamisch) und Materiallager (statisch)
- Benutzer sieht unterschiedliche Werte in verschiedenen Tabellen

### Auswirkungen auf Szenarien

**❌ KRITISCH:**
- Marketing-Szenarien: **KEINE Auswirkung** auf Materiallager
- Warehouse Damage: **KEINE Auswirkung** auf Materiallager
- Supplier Breakdown: **KEINE Auswirkung** auf Materiallager (Material wird bereits verbraucht)
- Delivery Problems: **KEINE Auswirkung** auf Materiallager

**Beispiel:**
- Marketing-Szenario erhöht Nachfrage → Produktionstabelle zeigt erhöhte Produktion
- Materiallager zeigt **alte, statische Werte** → Inkonsistenz

### Risiken

- **Hoch:** Dateninkonsistenz zwischen Produktionstabelle und Materiallager
- **Hoch:** Szenarien funktionieren nicht korrekt im Materiallager
- **Mittel:** Benutzer-Verwirrung durch unterschiedliche Werte

### Implementierungsaufwand

- **Niedrig:** Nur eine Datei ändern
- **Zeit:** ~15 Minuten

---

## Option 2: Dynamische Neuberechnung verbraucht Material

### Technische Umsetzung

**Änderungen:**
1. `ui/production_calculations.py`: `_recalculate_all_products_with_rank_logic()` gibt auch Materialverbrauch zurück
2. `ui/material_calculations.py`: Verwendet Materialverbrauch aus dynamischer Neuberechnung
3. `simulation/simulator.py`: Verbraucht Material weiterhin (für Backward-Kompatibilität)

**Code-Änderung:**
```python
# NEU: _recalculate_all_products_with_rank_logic() gibt auch Materialverbrauch zurück
def _recalculate_all_products_with_rank_logic(...) -> Tuple[Dict[str, int], Dict[str, float]]:
    # ... bestehende Logik ...
    
    # Berechne Materialverbrauch
    material_consumption = {}
    for product in products_list:
        scheduled_qty = scheduled_production_by_product.get(product, 0.0)
        required_saddle = MasterData.BOM[product]['saddle']
        if required_saddle not in material_consumption:
            material_consumption[required_saddle] = 0.0
        material_consumption[required_saddle] += scheduled_qty
    
    return result, material_consumption

# ui/material_calculations.py: Verwende Materialverbrauch aus dynamischer Neuberechnung
# Problem: Wie bekommen wir diese Werte?
```

**Problem:** Die dynamische Neuberechnung wird in `calculate_production_logs()` aufgerufen, aber `calculate_material_inventory()` läuft separat. Wir müssen den Materialverbrauch zwischen diesen Funktionen teilen.

### Auswirkungen auf Datenfluss

**✅ Vorteile:**
- Materialverbrauch = Dynamische Produktion (konsistent)
- Materiallager reagiert auf Marketing-Szenarien
- Materiallager reagiert auf Materialverfügbarkeits-Änderungen

**❌ Nachteile:**
- **Material wird möglicherweise doppelt verbraucht** (statisch + dynamisch)
- Komplexere Implementierung (Materialverbrauch muss zwischen Funktionen geteilt werden)
- Risiko von Race Conditions zwischen statischer und dynamischer Berechnung

### Auswirkungen auf Szenarien

**✅ Vorteile:**
- Marketing-Szenarien: **Funktionieren korrekt** im Materiallager
- Warehouse Damage: **Funktionieren korrekt** im Materiallager
- Supplier Breakdown: **Funktionieren korrekt** im Materiallager
- Delivery Problems: **Funktionieren korrekt** im Materiallager

**❌ Nachteile:**
- **Material wird möglicherweise doppelt verbraucht:**
  - Statische Simulation verbraucht Material (z.B. 811)
  - Dynamische Neuberechnung verbraucht Material (z.B. 786)
  - **Ergebnis:** Material wird 811 + 786 = 1597 verbraucht (falsch!)

### Risiken

- **Hoch:** Material wird doppelt verbraucht
- **Hoch:** Statische Simulation und dynamische Neuberechnung müssen synchronisiert werden
- **Mittel:** Komplexere Architektur (Materialverbrauch muss geteilt werden)

### Implementierungsaufwand

- **Hoch:** Mehrere Dateien ändern, Synchronisation notwendig
- **Zeit:** ~2-3 Stunden + Testing

---

## Option 3: Statische Simulation verbraucht kein Material mehr

### Technische Umsetzung

**Änderungen:**
1. `simulation/simulator.py`: Entferne `consume_components()` Aufruf
2. `simulation/production_planner.py`: Entferne Materialverbrauch aus `plan_daily_production()`
3. `ui/production_calculations.py`: Materialverbrauch nur in dynamischer Neuberechnung
4. `ui/material_calculations.py`: Verwendet Materialverbrauch aus dynamischer Neuberechnung

**Code-Änderung:**
```python
# simulation/simulator.py (Zeile 320-323):
# ALT:
consumed = self.production_planner.get_consumed_components(production_by_product)
self.production_planner.consume_components(consumed)

# NEU:
# Material wird nur in dynamischer Neuberechnung verbraucht
# (entfernt)

# simulation/production_planner.py:
# Entferne Materialverbrauch aus plan_daily_production()
# (nur für Planung, nicht für tatsächlichen Verbrauch)
```

### Auswirkungen auf Datenfluss

**✅ Vorteile:**
- Materialverbrauch = Dynamische Produktion (konsistent)
- Kein doppelter Materialverbrauch
- Klare Trennung: Statische Simulation = Planung, Dynamische Neuberechnung = Ausführung

**❌ Nachteile:**
- **Größere Refaktorierung** notwendig
- Statische Simulation muss angepasst werden (Materialverbrauch entfernen)
- Mögliche Auswirkungen auf andere Teile des Systems, die Materialverbrauch erwarten

### Auswirkungen auf Szenarien

**✅ Vorteile:**
- Marketing-Szenarien: **Funktionieren korrekt** im Materiallager
- Warehouse Damage: **Funktionieren korrekt** im Materiallager
- Supplier Breakdown: **Funktionieren korrekt** im Materiallager
- Delivery Problems: **Funktionieren korrekt** im Materiallager
- **Keine doppelte Materialverbrauch**

**❌ Nachteile:**
- Statische Simulation plant Produktion, verbraucht aber kein Material
- Mögliche Auswirkungen auf andere Systeme, die Materialverbrauch aus statischer Simulation erwarten

### Risiken

- **Hoch:** Größere Refaktorierung notwendig
- **Hoch:** Mögliche Auswirkungen auf andere Teile des Systems
- **Mittel:** Statische Simulation muss angepasst werden
- **Niedrig:** Testing notwendig für alle betroffenen Stellen

### Implementierungsaufwand

- **Sehr hoch:** Mehrere Dateien ändern, größere Refaktorierung
- **Zeit:** ~4-6 Stunden + umfangreiches Testing

---

## Option 4: Hybrid-Ansatz (Empfohlen)

### Technische Umsetzung

**Konzept:**
- Statische Simulation verbraucht Material weiterhin (für Backward-Kompatibilität)
- Dynamische Neuberechnung berechnet Materialverbrauch separat
- Materiallager verwendet Materialverbrauch aus dynamischer Neuberechnung
- **Aber:** Materialverbrauch wird nur einmal verbraucht (aus dynamischer Neuberechnung)

**Änderungen:**
1. `ui/production_calculations.py`: Speichere Materialverbrauch in `production_logs_cache`
2. `ui/material_calculations.py`: Verwende Materialverbrauch aus `production_logs_cache` (neue Spalte)
3. `simulation/simulator.py`: Verbraucht Material weiterhin (wird aber von dynamischer Neuberechnung überschrieben)

**Code-Änderung:**
```python
# ui/production_calculations.py:
# Speichere Materialverbrauch in production_logs_cache
df.at[idx, 'tatsächliche PM'] = new_tatsaechliche_pm
df.at[idx, 'material_verbrauch'] = new_tatsaechliche_pm  # NEU

# ui/material_calculations.py:
# Verwende Materialverbrauch aus production_logs_cache
material_consumption = matching_rows.iloc[0].get('material_verbrauch', actual_pm)
# Falls nicht vorhanden, verwende actual_pm (Fallback)
```

### Auswirkungen auf Datenfluss

**✅ Vorteile:**
- Materialverbrauch = Dynamische Produktion (konsistent)
- Materiallager reagiert auf Marketing-Szenarien
- Materiallager reagiert auf Materialverfügbarkeits-Änderungen
- **Kein doppelter Materialverbrauch** (Materialverbrauch wird explizit gespeichert)
- Backward-Kompatibilität (statische Simulation funktioniert weiterhin)

**❌ Nachteile:**
- Zusätzliche Spalte in `production_logs_cache`
- Materialverbrauch muss explizit gespeichert werden

### Auswirkungen auf Szenarien

**✅ Vorteile:**
- Marketing-Szenarien: **Funktionieren korrekt** im Materiallager
- Warehouse Damage: **Funktionieren korrekt** im Materiallager
- Supplier Breakdown: **Funktionieren korrekt** im Materiallager
- Delivery Problems: **Funktionieren korrekt** im Materiallager
- **Keine doppelte Materialverbrauch**

**❌ Nachteile:**
- Zusätzliche Spalte in `production_logs_cache` (minimal)

### Risiken

- **Niedrig:** Zusätzliche Spalte in `production_logs_cache`
- **Niedrig:** Materialverbrauch muss explizit gespeichert werden
- **Niedrig:** Fallback auf `actual_pm` wenn `material_verbrauch` nicht vorhanden

### Implementierungsaufwand

- **Mittel:** Zwei Dateien ändern, neue Spalte hinzufügen
- **Zeit:** ~1-2 Stunden + Testing

---

## Empfehlung

### Option 4 (Hybrid-Ansatz) ist die beste Lösung

**Begründung:**
1. **Konsistenz:** Materialverbrauch = Dynamische Produktion
2. **Szenarien:** Alle Szenarien funktionieren korrekt
3. **Kein doppelter Verbrauch:** Materialverbrauch wird explizit gespeichert
4. **Backward-Kompatibilität:** Statische Simulation funktioniert weiterhin
5. **Moderate Implementierung:** Nicht zu komplex, nicht zu einfach

### Vergleichstabelle

| Kriterium | Option 1 | Option 2 | Option 3 | Option 4 |
|-----------|----------|----------|----------|----------|
| Konsistenz | ❌ | ⚠️ | ✅ | ✅ |
| Szenarien | ❌ | ✅ | ✅ | ✅ |
| Doppelter Verbrauch | ❌ | ❌ | ✅ | ✅ |
| Implementierungsaufwand | ✅ Niedrig | ❌ Hoch | ❌ Sehr hoch | ⚠️ Mittel |
| Backward-Kompatibilität | ✅ | ⚠️ | ❌ | ✅ |
| Risiko | ❌ Hoch | ❌ Hoch | ❌ Hoch | ✅ Niedrig |

---

---

## Detaillierte Auswirkungen auf Datenfluss und Szenarien

### Option 1: Materiallager verwendet statische Werte

#### Datenfluss

**Aktueller Datenfluss:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch)
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert)
                  └─→ Materiallager (liest aus production_logs_cache) ✅
```

**Mit Option 1:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch)
          └─→ production_logs (statisch)
              ├─→ production_logs_cache (dynamisch aktualisiert) → Produktionstabelle
              └─→ Materiallager (liest aus production_logs) ❌
```

**Problem:**
- Materiallager verwendet statische Werte (ohne Marketing)
- Produktionstabelle verwendet dynamische Werte (mit Marketing)
- **Inkonsistenz:** Materiallager zeigt andere Werte als Produktionstabelle

#### Szenarien-Auswirkungen

**Marketing-Szenarien:**
- ❌ **KEINE Auswirkung** auf Materiallager
- ✅ Auswirkung auf Produktionstabelle
- **Ergebnis:** Inkonsistenz zwischen Materiallager und Produktionstabelle

**Warehouse Damage:**
- ⚠️ **Teilweise:** Statische Simulation berücksichtigt Warehouse Damage
- ❌ Materiallager zeigt statische Werte (könnte Warehouse Damage nicht berücksichtigen)
- **Ergebnis:** Inkonsistenz möglich

**Supplier Breakdown:**
- ✅ Statische Simulation berücksichtigt Supplier Breakdown
- ⚠️ Materiallager zeigt statische Werte (könnte Supplier Breakdown nicht berücksichtigen)
- **Ergebnis:** Inkonsistenz möglich

**Delivery Problems:**
- ✅ Statische Simulation berücksichtigt Delivery Problems
- ⚠️ Materiallager zeigt statische Werte (könnte Delivery Problems nicht berücksichtigen)
- **Ergebnis:** Inkonsistenz möglich

---

### Option 2: Dynamische Neuberechnung verbraucht Material

#### Datenfluss

**Aktueller Datenfluss:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht Material
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert)
                  └─→ Materiallager (liest aus production_logs_cache) ✅
```

**Mit Option 2:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht Material (z.B. 811)
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert) → verbraucht Material (z.B. 786)
                  └─→ Materiallager (liest Materialverbrauch aus dynamischer Neuberechnung) ❌
```

**Problem:**
- Material wird **doppelt verbraucht**: 811 (statisch) + 786 (dynamisch) = 1597
- **Ergebnis:** Materialbestand wird falsch berechnet

#### Szenarien-Auswirkungen

**Marketing-Szenarien:**
- ✅ Auswirkung auf Produktionstabelle
- ✅ Auswirkung auf Materiallager (dynamische Neuberechnung)
- ❌ **Material wird doppelt verbraucht** (statisch + dynamisch)

**Warehouse Damage:**
- ✅ Statische Simulation berücksichtigt Warehouse Damage
- ✅ Dynamische Neuberechnung berücksichtigt Warehouse Damage
- ❌ **Material wird doppelt verbraucht**

**Supplier Breakdown:**
- ✅ Statische Simulation berücksichtigt Supplier Breakdown
- ✅ Dynamische Neuberechnung berücksichtigt Supplier Breakdown
- ❌ **Material wird doppelt verbraucht**

**Delivery Problems:**
- ✅ Statische Simulation berücksichtigt Delivery Problems
- ✅ Dynamische Neuberechnung berücksichtigt Delivery Problems
- ❌ **Material wird doppelt verbraucht**

---

### Option 3: Statische Simulation verbraucht kein Material mehr

#### Datenfluss

**Aktueller Datenfluss:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht Material
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert)
                  └─→ Materiallager (liest aus production_logs_cache) ✅
```

**Mit Option 3:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht KEIN Material mehr
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert) → verbraucht Material
                  └─→ Materiallager (liest Materialverbrauch aus dynamischer Neuberechnung) ✅
```

**Vorteil:**
- Material wird nur einmal verbraucht (in dynamischer Neuberechnung)
- Konsistenz: Materialverbrauch = Dynamische Produktion

**Problem:**
- Statische Simulation plant Produktion, verbraucht aber kein Material
- Mögliche Auswirkungen auf andere Systeme, die Materialverbrauch aus statischer Simulation erwarten

#### Szenarien-Auswirkungen

**Marketing-Szenarien:**
- ✅ Auswirkung auf Produktionstabelle
- ✅ Auswirkung auf Materiallager (dynamische Neuberechnung)
- ✅ **Kein doppelter Materialverbrauch**

**Warehouse Damage:**
- ⚠️ Statische Simulation berücksichtigt Warehouse Damage (aber verbraucht kein Material)
- ✅ Dynamische Neuberechnung berücksichtigt Warehouse Damage
- ✅ **Kein doppelter Materialverbrauch**

**Supplier Breakdown:**
- ⚠️ Statische Simulation berücksichtigt Supplier Breakdown (aber verbraucht kein Material)
- ✅ Dynamische Neuberechnung berücksichtigt Supplier Breakdown
- ✅ **Kein doppelter Materialverbrauch**

**Delivery Problems:**
- ⚠️ Statische Simulation berücksichtigt Delivery Problems (aber verbraucht kein Material)
- ✅ Dynamische Neuberechnung berücksichtigt Delivery Problems
- ✅ **Kein doppelter Materialverbrauch**

**Risiko:**
- Andere Systeme, die Materialverbrauch aus statischer Simulation erwarten, müssen angepasst werden

---

### Option 4: Hybrid-Ansatz (Materialverbrauch explizit speichern)

#### Datenfluss

**Aktueller Datenfluss:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht Material
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert)
                  └─→ Materiallager (liest "tatsächliche PM" aus production_logs_cache) ✅
```

**Mit Option 4:**
```
Volumenplanung (mit Marketing)
  └─→ daily_demands_actual
      └─→ ProductionPlanner (statisch) → verbraucht Material (für Backward-Kompatibilität)
          └─→ production_logs (statisch)
              └─→ production_logs_cache (dynamisch aktualisiert)
                  ├─→ "tatsächliche PM" (für Produktionstabelle)
                  └─→ "material_verbrauch" (NEU, für Materiallager) ✅
                      └─→ Materiallager (liest "material_verbrauch" aus production_logs_cache) ✅
```

**Vorteil:**
- Materialverbrauch wird explizit gespeichert (konsistent mit dynamischer Produktion)
- Statische Simulation funktioniert weiterhin (Backward-Kompatibilität)
- Kein doppelter Materialverbrauch (Materiallager verwendet expliziten Wert)

#### Szenarien-Auswirkungen

**Marketing-Szenarien:**
- ✅ Auswirkung auf Produktionstabelle
- ✅ Auswirkung auf Materiallager (dynamische Neuberechnung)
- ✅ **Kein doppelter Materialverbrauch** (Materiallager verwendet expliziten Wert)

**Warehouse Damage:**
- ✅ Statische Simulation berücksichtigt Warehouse Damage
- ✅ Dynamische Neuberechnung berücksichtigt Warehouse Damage
- ✅ Materiallager verwendet Materialverbrauch aus dynamischer Neuberechnung
- ✅ **Kein doppelter Materialverbrauch**

**Supplier Breakdown:**
- ✅ Statische Simulation berücksichtigt Supplier Breakdown
- ✅ Dynamische Neuberechnung berücksichtigt Supplier Breakdown
- ✅ Materiallager verwendet Materialverbrauch aus dynamischer Neuberechnung
- ✅ **Kein doppelter Materialverbrauch**

**Delivery Problems:**
- ✅ Statische Simulation berücksichtigt Delivery Problems
- ✅ Dynamische Neuberechnung berücksichtigt Delivery Problems
- ✅ Materiallager verwendet Materialverbrauch aus dynamischer Neuberechnung
- ✅ **Kein doppelter Materialverbrauch**

**Vorteil:**
- Alle Szenarien funktionieren korrekt
- Keine Inkonsistenzen
- Backward-Kompatibilität erhalten

---

## Vergleich: Auswirkungen auf Datenfluss

| Aspekt | Option 1 | Option 2 | Option 3 | Option 4 |
|--------|----------|----------|----------|----------|
| **Konsistenz Materiallager ↔ Produktion** | ❌ Nein | ⚠️ Teilweise | ✅ Ja | ✅ Ja |
| **Materialverbrauch = Produktion** | ❌ Nein | ❌ Nein (doppelt) | ✅ Ja | ✅ Ja |
| **Reagiert auf Marketing** | ❌ Nein | ✅ Ja | ✅ Ja | ✅ Ja |
| **Reagiert auf Warehouse Damage** | ⚠️ Teilweise | ✅ Ja | ✅ Ja | ✅ Ja |
| **Reagiert auf Supplier Breakdown** | ⚠️ Teilweise | ✅ Ja | ✅ Ja | ✅ Ja |
| **Reagiert auf Delivery Problems** | ⚠️ Teilweise | ✅ Ja | ✅ Ja | ✅ Ja |
| **Backward-Kompatibilität** | ✅ Ja | ⚠️ Teilweise | ❌ Nein | ✅ Ja |
| **Doppelter Materialverbrauch** | ❌ Nein | ❌ Ja | ✅ Nein | ✅ Nein |

---

## Vergleich: Auswirkungen auf Szenarien

| Szenario | Option 1 | Option 2 | Option 3 | Option 4 |
|----------|----------|----------|----------|----------|
| **Marketing** | ❌ Funktioniert nicht | ⚠️ Doppelter Verbrauch | ✅ Funktioniert | ✅ Funktioniert |
| **Warehouse Damage** | ⚠️ Teilweise | ⚠️ Doppelter Verbrauch | ✅ Funktioniert | ✅ Funktioniert |
| **Supplier Breakdown** | ⚠️ Teilweise | ⚠️ Doppelter Verbrauch | ✅ Funktioniert | ✅ Funktioniert |
| **Delivery Problems** | ⚠️ Teilweise | ⚠️ Doppelter Verbrauch | ✅ Funktioniert | ✅ Funktioniert |

---

## Empfehlung: Option 4 (Hybrid-Ansatz)

### Begründung

1. **Konsistenz:** Materialverbrauch = Dynamische Produktion
2. **Szenarien:** Alle Szenarien funktionieren korrekt
3. **Kein doppelter Verbrauch:** Materialverbrauch wird explizit gespeichert
4. **Backward-Kompatibilität:** Statische Simulation funktioniert weiterhin
5. **Moderate Implementierung:** Nicht zu komplex, nicht zu einfach

### Konkrete Umsetzung

**Schritt 1:** Speichere Materialverbrauch in `production_logs_cache`
```python
# ui/production_calculations.py (nach Zeile 501):
df.at[idx, 'tatsächliche PM'] = new_tatsaechliche_pm
df.at[idx, 'material_verbrauch'] = new_tatsaechliche_pm  # NEU
```

**Schritt 2:** Verwende Materialverbrauch im Materiallager
```python
# ui/material_calculations.py (Zeile 112):
actual_pm = matching_rows.iloc[0].get('tatsächliche PM', 0)
material_verbrauch = matching_rows.iloc[0].get('material_verbrauch', None)

# Verwende material_verbrauch wenn vorhanden, sonst actual_pm (Fallback)
if material_verbrauch is not None:
    production_by_product_from_logs[product_name] = int(material_verbrauch) if material_verbrauch > 0 else 0
else:
    production_by_product_from_logs[product_name] = int(actual_pm) if actual_pm > 0 else 0
```

**Schritt 3:** Fallback für statische Werte
- Wenn keine dynamische Neuberechnung ausgeführt wurde, verwende `actual_pm` (statischer Wert)
- Wenn dynamische Neuberechnung ausgeführt wurde, verwende `material_verbrauch` (dynamischer Wert)

### Risiken

- **Niedrig:** Zusätzliche Spalte in `production_logs_cache`
- **Niedrig:** Fallback-Logik notwendig
- **Niedrig:** Testing notwendig

### Vorteile

- ✅ **Konsistenz:** Materialverbrauch = Dynamische Produktion
- ✅ **Szenarien:** Alle Szenarien funktionieren korrekt
- ✅ **Kein doppelter Verbrauch:** Materialverbrauch wird explizit gespeichert
- ✅ **Backward-Kompatibilität:** Statische Simulation funktioniert weiterhin
- ✅ **Datenfluss:** Keine Störung des bestehenden Datenflusses

---

## Nächste Schritte

Wenn Option 4 gewählt wird:
1. `ui/production_calculations.py`: Speichere Materialverbrauch in `production_logs_cache`
2. `ui/material_calculations.py`: Verwende Materialverbrauch aus `production_logs_cache`
3. Testing: Prüfe Konsistenz zwischen Materiallager und Produktion
4. Testing: Prüfe alle Szenarien (Marketing, Warehouse Damage, Supplier Breakdown, Delivery Problems)
