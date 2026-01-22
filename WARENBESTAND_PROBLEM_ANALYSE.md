# Warenbestand-Problem Analyse - Lieferant China

**Datum:** 2026-01-22  
**Problem:** 4177 Fizik Tundra Sättel bleiben im Warenbestand, obwohl sie produziert wurden  
**Beobachtung:** Produktionsmenge (99900) > Warenausgang (95723) = 4177 verbleibend

---

## 📊 Daten aus CSV (Fizik Tundra)

- **Summe Bestelleingang:** 99.900
- **Summe Freigegebene Bestellungen:** 99.900
- **Summe Produktionsmenge:** 99.900
- **Summe Warenausgang:** 95.723
- **Warenbestand (Ende):** 4.177

**Differenz:** 99.900 - 95.723 = 4.177 ✓ (passt mathematisch)

---

## 🔍 Aktuelle Logik in `simulation/china_transport.py`

### 1. Produktionsmenge-Berechnung (Zeilen 628-632)

```python
# Berechne Produktionsmenge: Summe aller freigegebenen Bestellungen mit Produktionsdatum gleich Datum
for production_end_day_idx, order_quantities in release_production_map.items():
    if 0 <= production_end_day_idx < total_days:
        total_production = sum(order_quantities)
        raw_data_map[production_end_day_idx]['prod'] = total_production
```

**✅ Korrekt:** Produktionsmenge wird korrekt berechnet.

---

### 2. Pool-Logik & Versand-Planung (Zeilen 671-714)

```python
# Tägliche Pool-Berechnung
for day_idx in range(total_days):
    # 1. Gesamt-Verfügbarkeit prüfen
    total_accumulated = 0.0
    accumulated_by_saddle = {}
    
    for s in all_saddles:
        prod = daily_prod_all[day_idx][s]
        co = carry_over[s]
        acc = prod + co
        accumulated_by_saddle[s] = acc
        total_accumulated += acc
    
    # 2. Losgröße berechnen
    current_lot_size = int(total_accumulated / lot_size) * lot_size
    
    # 3. Wenn Versand möglich -> Verteilen (proportional nach Shares)
    if current_lot_size > 0:
        # ... Largest Remainder Method ...
        shipments_today = rounded  # Geplante Versandmenge pro Sattel
    
    # 4. Carry-Over aktualisieren
    for s in all_saddles:
        carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]
        if s == saddle_name:
            shipment_results[day_idx] = shipments_today[s]  # Geplante Versandmenge
```

**✅ Korrekt:** Pool-Logik berechnet die geplante Versandmenge (`shipment_results[day_idx]`).

---

### 3. Warenausgang-Berechnung (Zeilen 747-784)

```python
# WARENBESTAND: Vorheriger Bestand + Produziert - Ausgangsmenge
# WICHTIG: Berechne Warenbestand VOR Warenausgang
current_stock = previous_stock + production_qty

# WARENAUSGANG: Berechnung
planned_shipment_qty = shipment_results[day_idx]  # Geplante Versandmenge aus Pool-Logik

# Formel: Wenn Warenbestand - bereits verschickt >= 0: 
#   Warenbestand - bereits verschickt, sonst Warenbestand
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)

# Aktualisiere kumulierte verschickte Menge
cumulative_shipped += shipment_qty

# Aktualisiere Warenbestand nach Versand
current_stock = current_stock - shipment_qty
previous_stock = current_stock
```

**❌ PROBLEM IDENTIFIZIERT:**

Die Logik hat einen **konzeptionellen Fehler**:

1. **`cumulative_shipped`** wird verwendet, um zu prüfen, ob noch genug Bestand vorhanden ist
2. Aber **`cumulative_shipped`** ist die **kumulierte bereits verschickte Menge** (nicht die geplante)
3. Die Formel `current_stock - cumulative_shipped` prüft, ob der **verbleibende Bestand** ausreicht
4. **ABER:** Die Pool-Logik plant bereits Versandmengen, die möglicherweise **nicht mit dem tatsächlichen Bestand übereinstimmen**

---

## 🐛 Root Cause Analysis

### Problem 1: Inkonsistenz zwischen Pool-Logik und Bestandslogik

**Pool-Logik (Zeilen 671-714):**
- Berechnet Versandmengen basierend auf **täglicher Produktion + Carry-Over**
- Verteilt proportional nach Shares
- **Ignoriert den tatsächlichen Warenbestand**

**Bestandslogik (Zeilen 747-784):**
- Berechnet Warenbestand als `previous_stock + production_qty`
- Begrenzt Versand durch `current_stock - cumulative_shipped`
- **Kann weniger verschicken als geplant**, wenn Bestand nicht ausreicht

**Ergebnis:** 
- Pool-Logik plant z.B. 500 Stück zu verschicken
- Aber Bestandslogik stellt fest: `current_stock - cumulative_shipped = 300`
- Tatsächlicher Versand: `min(500, 300) = 300`
- **200 Stück bleiben im Bestand**

### Problem 2: `cumulative_shipped` wird inkorrekt verwendet

Die Variable `cumulative_shipped` wird verwendet, um zu prüfen, ob noch genug Bestand vorhanden ist. Aber:

- `cumulative_shipped` ist die **Summe aller bereits verschickten Mengen**
- `current_stock` ist der **aktuelle Bestand** (vorheriger Bestand + Produktion)
- Die Formel `current_stock - cumulative_shipped` sollte eigentlich prüfen: **"Wie viel Bestand ist noch verfügbar?"**

**ABER:** Wenn `cumulative_shipped` größer ist als `current_stock`, bedeutet das, dass **mehr verschickt wurde als produziert wurde**. Das sollte nicht passieren, wenn die Logik korrekt ist.

### Problem 3: Timing-Problem

Die Pool-Logik berechnet Versandmengen **täglich**, aber:
- Produktion kann an einem Tag stattfinden
- Versand kann an einem anderen Tag stattfinden
- Wenn Versand **vor** Produktion geplant wird, kann der Bestand nicht ausreichen

---

## 💡 Erste Einschätzung

### Hauptproblem: **Inkonsistenz zwischen Pool-Logik und Bestandslogik**

Die Pool-Logik plant Versandmengen basierend auf:
- Täglicher Produktion
- Carry-Over vom Vortag
- Proportionaler Verteilung nach Shares

Aber die Bestandslogik prüft:
- Tatsächlichen Warenbestand (`previous_stock + production_qty`)
- Bereits verschickte Menge (`cumulative_shipped`)

**Wenn die geplante Versandmenge (`planned_shipment_qty`) größer ist als der verfügbare Bestand (`current_stock - cumulative_shipped`), wird weniger verschickt als geplant.**

### Warum bleiben 4177 Stück im Bestand?

Die 4177 Stück sind die **kumulierte Differenz** zwischen:
- **Geplanter Versandmenge** (aus Pool-Logik): z.B. 99.630
- **Tatsächlicher Versandmenge** (begrenzt durch Bestand): 95.723
- **Differenz:** 99.630 - 95.723 = 3.907 (nahe an 4.177)

**Mögliche Ursachen:**
1. **Timing-Problem:** Versand wird geplant, bevor Produktion stattfindet
2. **Bestandsbegrenzung:** Bestand reicht nicht aus, um geplante Versandmenge zu decken
3. **Rundungsfehler:** Durch Largest Remainder Method können kleine Differenzen entstehen
4. **Carry-Over-Problem:** Carry-Over wird in Pool-Logik berücksichtigt, aber nicht korrekt in Bestandslogik

---

## 🔧 Mögliche Lösungsansätze

### Ansatz 1: Bestandslogik an Pool-Logik anpassen

**Idee:** Die Bestandslogik sollte die **gleiche Logik** wie die Pool-Logik verwenden.

```python
# Statt: current_stock = previous_stock + production_qty
# Verwende: current_stock = accumulated_by_saddle[saddle_name]
```

**Problem:** Dies würde die Bestandslogik komplett umschreiben.

### Ansatz 2: Pool-Logik an Bestandslogik anpassen

**Idee:** Die Pool-Logik sollte den **tatsächlichen Bestand** berücksichtigen.

```python
# In Pool-Logik: Prüfe tatsächlichen Bestand
for s in all_saddles:
    actual_stock = previous_stock_by_saddle[s] + daily_prod_all[day_idx][s]
    available_for_shipment = actual_stock - cumulative_shipped_by_saddle[s]
    # Begrenze Versandmenge durch verfügbaren Bestand
```

**Problem:** Dies würde die Pool-Logik komplexer machen.

### Ansatz 3: Bestandslogik vereinfachen

**Idee:** Entferne die `cumulative_shipped`-Prüfung und verwende direkt den Bestand.

```python
# Vereinfachte Logik:
shipment_qty = min(planned_shipment_qty, current_stock)
current_stock = current_stock - shipment_qty
```

**Problem:** Dies ignoriert mögliche Szenarien mit Verlusten.

### Ansatz 4: Korrektur der `cumulative_shipped`-Logik

**Idee:** `cumulative_shipped` sollte nur die **tatsächlich verschickte Menge** kumulieren, nicht die geplante.

**Aktuell:**
```python
cumulative_shipped += shipment_qty  # Korrekt
```

**Aber die Prüfung:**
```python
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
```

**Sollte sein:**
```python
available_stock = current_stock  # Verfügbarer Bestand
shipment_qty = min(planned_shipment_qty, available_stock)
```

---

## 📋 Nächste Schritte

1. **Validierung:** Prüfe, ob `cumulative_shipped` korrekt verwendet wird
2. **Debugging:** Füge Logging hinzu, um zu sehen, wann `current_stock - cumulative_shipped < planned_shipment_qty`
3. **Korrektur:** Passe die Bestandslogik an, um konsistent mit Pool-Logik zu sein
4. **Test:** Validiere, dass nach Korrektur `Warenbestand (Ende) = 0` (oder erwarteter Wert)

---

## 🎯 Empfohlener Fix

**Vereinfachte Bestandslogik ohne `cumulative_shipped`:**

```python
# WARENBESTAND: Vorheriger Bestand + Produziert
current_stock = previous_stock + production_qty

# WARENAUSGANG: Min(Geplante Versandmenge, Verfügbarer Bestand)
planned_shipment_qty = shipment_results[day_idx]
shipment_qty = min(planned_shipment_qty, current_stock)

# Aktualisiere Warenbestand nach Versand
current_stock = current_stock - shipment_qty
previous_stock = current_stock
```

**Begründung:**
- Einfacher und klarer
- Konsistent mit Pool-Logik (die bereits die Versandmenge plant)
- Keine komplexe `cumulative_shipped`-Prüfung nötig
- Sollte die 4177 Differenz beheben
