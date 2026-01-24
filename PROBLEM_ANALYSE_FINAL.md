# Finale Problem-Analyse: Warum wird mehr produziert als geplant?

## Problem

**63 Tage** gefunden, an denen "Tatsächliche PM" > Produktionsbedarf ist (wenn Backlog = 0).

**Beispiel: 06.08.2027**
- Geplante PM = 454 (mit Marketing bereits berücksichtigt)
- Backlog = 0
- Produktionsbedarf = 454 + 0 = 454
- **Tatsächliche PM = 1103** (2.43x mehr!)

## Implementierte Korrekturen

### ✅ Korrektur 1: Prüfung nach Berechnung
```python
scheduled_qty = min(max(0.0, scheduled_qty), demand)
```

### ✅ Korrektur 2: Finale Prüfung
```python
if scheduled_qty > demand:
    scheduled_production_by_product[product] = demand
```

### ✅ Korrektur 3: Prüfung auf falsche statische Werte
```python
if base_tatsaechliche_pm_float > production_demand_expected:
    static_values_incorrect = True
```

### ✅ Korrektur 4: Sicherheitsprüfung 2
```python
if total_scheduled > total_production_demand:
    # Proportionale Reduktion
```

## Warum funktionieren die Korrekturen nicht?

### Mögliche Ursache 1: Statische Werte werden verwendet

**Problem:** Die dynamische Neuberechnung wird nur ausgeführt, wenn:
- `inputs_changed = True` ODER
- `static_values_incorrect = True`

**Wenn beide False sind:**
- Statische Werte werden verwendet
- Diese stammen von einer Simulation VOR den Korrekturen
- Die statischen Werte sind falsch (1103 statt 454)

**Lösung:** Die Prüfung auf falsche statische Werte sollte das erkennen und `static_values_incorrect = True` setzen.

**ABER:** Die Prüfung funktioniert möglicherweise nicht, weil:
- Der Backlog aus falschen statischen Logs geholt wird
- Die Prüfung wird nicht für alle Produkte ausgeführt (wegen `break`)
- Die Prüfung wird ausgeführt, aber die dynamische Neuberechnung produziert immer noch falsche Werte

### Mögliche Ursache 2: Die dynamische Neuberechnung produziert falsche Werte

**Problem:** Auch wenn die dynamische Neuberechnung ausgeführt wird, produziert sie möglicherweise immer noch falsche Werte.

**Warum?**
- Die dynamische Neuberechnung verwendet Backlog aus statischen Logs
- Diese Backlog-Werte sind möglicherweise falsch (basierend auf falschen Produktionswerten)
- Die Rang-Logik produziert mehr als erlaubt, trotz der Prüfungen

### Mögliche Ursache 3: Die Prüfungen greifen nicht

**Problem:** Die Prüfungen werden ausgeführt, aber sie greifen nicht, weil:
- `demand` ist falsch (z.B. Backlog ist falsch)
- Die Prüfung wird zu spät ausgeführt (nach Material-Reduktion)
- Die Prüfung wird überschrieben

## Die wahre Ursache

**Ich vermute:** Die statischen Werte werden verwendet, weil die Prüfung auf falsche statische Werte nicht greift. Warum?

**Mögliche Gründe:**
1. Die Prüfung wird nicht für alle Produkte ausgeführt (wegen `break` in der Schleife)
2. Die Prüfung verwendet falsche Backlog-Werte aus statischen Logs
3. Die Prüfung wird ausgeführt, aber die dynamische Neuberechnung produziert immer noch falsche Werte

## Lösung

### Option 1: Dynamische Neuberechnung IMMER ausführen

**Ändere die Bedingung:**
```python
# ALT:
if (inputs_changed or static_values_incorrect) and daily_capacity > 0:

# NEU:
if daily_capacity > 0:
    # Führe IMMER dynamische Neuberechnung aus
    # (Optimierung: Nur wenn sich Inputs geändert haben ODER statische Werte falsch sind)
    if inputs_changed or static_values_incorrect:
        # Neuberechnung
    else:
        # Verwende statische Werte (nur wenn sie korrekt sind)
        # Prüfe nochmal, ob sie korrekt sind
        ...
```

### Option 2: Explizite Begrenzung auf Geplante PM

**Die einfachste Lösung:** Stelle sicher, dass `scheduled_qty` niemals größer ist als die "Geplante PM" (ohne Backlog):

```python
# Nach der Berechnung
planned_pm = product_demands_new.get(product, 0)  # Geplante PM (mit Marketing)
production_demand = planned_pm + backlog  # Produktionsbedarf

# Begrenze auf Produktionsbedarf
scheduled_qty = min(scheduled_qty, production_demand)

# ZUSÄTZLICH: Begrenze auf Geplante PM (wenn Backlog = 0)
if backlog == 0:
    scheduled_qty = min(scheduled_qty, planned_pm)
```

**ABER:** Das ist nicht korrekt, weil wenn Backlog > 0, sollte mehr produziert werden.

### Option 3: Debug-Ausgabe hinzufügen

**Füge Debug-Ausgabe hinzu, um zu sehen, was passiert:**
```python
if base_tatsaechliche_pm_float > production_demand_expected:
    static_values_incorrect = True
    print(f"DEBUG: Statische Werte falsch für {product} am {row_date}: "
          f"Tatsächliche PM={base_tatsaechliche_pm_float}, "
          f"Produktionsbedarf={production_demand_expected}")
```

## Empfehlung

**Implementiere Option 1:** Führe die dynamische Neuberechnung IMMER aus, wenn statische Werte falsch sind, auch wenn sich Inputs nicht geändert haben. Dies stellt sicher, dass falsche statische Werte korrigiert werden.

**Zusätzlich:** Füge eine explizite Begrenzung hinzu, die sicherstellt, dass `scheduled_qty <= demand` ist, auch nach allen anderen Prüfungen.
