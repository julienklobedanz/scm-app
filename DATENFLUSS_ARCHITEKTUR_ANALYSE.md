# Datenfluss-Architektur Analyse - Szenarien & Konsistenz

**Datum:** 2026-01-22  
**Problem:** Inkonsistente Szenarien-Anwendung und unklarer Datenfluss zwischen Pages

---

## 🔍 Aktuelle Architektur-Probleme

### Problem 1: Inkonsistente Szenarien-Anwendung

#### Supplier-Log (`get_supplier_log_dataframe`)

**Aktuell:**
- ✅ DeliveryProblemScenario wird geprüft (Zeile 755-764)
- ❌ **Nur bei 100% Verlust** wird berücksichtigt (`loss_percentage >= 1.0`)
- ❌ **Teilweise Verluste werden IGNORIERT**
- ❌ SupplierBreakdownScenario wird **NICHT** berücksichtigt

**Code:**
```python
# Zeile 755-764
delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(day_index)
for scenario in delivery_problems:
    if scenario.component_type == 'saddles' and scenario.loss_percentage >= 1.0:
        shipment_qty = 0  # Nur 100% Verlust
        break
# Teilweise Verluste werden IGNORIERT!
```

#### Inbound-Log (`get_inbound_log_dataframe`)

**Aktuell:**
- ❌ **KEINE Szenarien-Berücksichtigung**
- ❌ Berechnet Versandmengen ohne Verluste/Verspätungen
- ❌ Zeigt immer die volle geplante Versandmenge

**Code:**
```python
# Zeilen 906-963: Pool-Logik
# KEINE Prüfung auf delivery_problems oder supplier_breakdowns
shipments_today = rounded  # Volle geplante Menge
```

#### `process_shipments()` (tatsächlicher Versand)

**Aktuell:**
- ✅ DeliveryProblemScenario wird **korrekt** angewendet (Zeile 185-193)
- ✅ Verluste und Verspätungen werden berücksichtigt
- ✅ `actual_quantity` wird korrekt reduziert

**Code:**
```python
# Zeile 185-193
delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(ship_departure_day)
for scenario in delivery_problems:
    if scenario.component_type == 'saddles':
        delay_days = max(delay_days, scenario.delay_days)
        loss_factor *= (1.0 - scenario.loss_percentage)
```

**Problem:** Diese Logik wird nur in `process_shipments()` angewendet, **NICHT** in den Tabellen!

---

### Problem 2: Unklarer Datenfluss

#### Aktueller Datenfluss

```
transport_status (Single Source of Truth)
    ↓
    ├─→ get_supplier_log_dataframe()
    │   └─→ Pool-Logik (eigene Berechnung)
    │   └─→ Bestandslogik (eigene Berechnung)
    │   └─→ Szenarien: NUR 100% Verlust
    │
    ├─→ get_inbound_log_dataframe()
    │   └─→ Pool-Logik (eigene Berechnung, GLEICHE Logik)
    │   └─→ Szenarien: KEINE
    │
    └─→ process_shipments() (während Simulation)
        └─→ Szenarien: VOLLSTÄNDIG (Verluste + Verspätungen)
        └─→ Aktualisiert transport_status mit actual_quantity
```

**Probleme:**
1. **Drei verschiedene Berechnungen** für Versandmengen
2. **Szenarien werden inkonsistent** angewendet
3. **Keine Single Source of Truth** für Versandmengen
4. **Inbound-Log zeigt falsche Mengen** (ohne Verluste)

---

## 🎯 Empfohlene Architektur

### Single Source of Truth: `transport_status`

**Idee:** `transport_status` sollte die **einzige Quelle** für Versandmengen sein.

**Aktuell:**
- `transport_status` enthält: `quantity` (ursprünglich), `actual_quantity` (nach Verlusten)
- Aber Tabellen berechnen Versandmengen **neu** (Pool-Logik)

**Empfehlung:**
- `transport_status` sollte **bereits die finalen Versandmengen** enthalten
- Tabellen sollten **nur noch lesen**, nicht neu berechnen

### Konsistente Szenarien-Anwendung

**Idee:** Szenarien sollten **zentral** in `process_shipments()` angewendet werden.

**Aktuell:**
- Szenarien werden in `process_shipments()` angewendet ✅
- Aber Tabellen ignorieren diese Anwendung ❌

**Empfehlung:**
- Tabellen sollten `actual_quantity` aus `transport_status` verwenden
- **NICHT** eigene Pool-Logik mit Szenarien-Prüfung

---

## 🔧 Konkrete Lösungsvorschläge

### Lösung 1: Transport-Status als Single Source of Truth

**Änderung:**
1. `process_shipments()` berechnet Versandmengen **einmalig** mit Pool-Logik
2. Szenarien werden **sofort** angewendet (Verluste, Verspätungen)
3. `transport_status` wird mit **finalen Mengen** aktualisiert
4. Tabellen lesen **nur noch** aus `transport_status`

**Vorteile:**
- ✅ Konsistenz: Alle Tabellen zeigen gleiche Mengen
- ✅ Szenarien werden zentral angewendet
- ✅ Einfacher zu warten

**Nachteile:**
- ⚠️ Größere Refaktorierung nötig
- ⚠️ Pool-Logik muss in `process_shipments()` verschoben werden

### Lösung 2: Zentrale Versandmengen-Berechnung

**Änderung:**
1. Neue Methode: `calculate_shipment_quantities(day, scenarios)`
2. Berechnet Versandmengen **einmalig** mit Pool-Logik
3. Wendet Szenarien **sofort** an
4. Gibt finale Versandmengen zurück
5. Beide Tabellen verwenden diese Methode

**Vorteile:**
- ✅ Konsistenz: Beide Tabellen verwenden gleiche Logik
- ✅ Szenarien werden zentral angewendet
- ✅ Kleinere Refaktorierung

**Nachteile:**
- ⚠️ Pool-Logik muss extrahiert werden
- ⚠️ Bestandslogik muss angepasst werden

### Lösung 3: Szenarien in Tabellen konsistent anwenden

**Änderung:**
1. Beide Tabellen wenden Szenarien **gleich** an
2. Pool-Logik bleibt in beiden Tabellen
3. Szenarien-Prüfung wird **konsistent** implementiert

**Vorteile:**
- ✅ Minimale Änderungen
- ✅ Schnell umsetzbar

**Nachteile:**
- ⚠️ Code-Duplikation (Szenarien-Logik in beiden Tabellen)
- ⚠️ Wartungsaufwand (Änderungen an zwei Stellen)

---

## 📋 Empfohlene Lösung: Hybrid-Ansatz

### Phase 1: Sofort-Fix (Lösung 3)

**Ziel:** Konsistenz herstellen, ohne große Refaktorierung

**Änderungen:**
1. **Supplier-Log:** Szenarien vollständig anwenden (nicht nur 100% Verlust)
2. **Inbound-Log:** Szenarien hinzufügen (aktuell fehlen komplett)
3. **Beide Tabellen:** Gleiche Szenarien-Logik verwenden

**Code-Änderungen:**

```python
# In get_supplier_log_dataframe():
# VORHER: Nur 100% Verlust
if scenario.loss_percentage >= 1.0:
    shipment_qty = 0

# NACHHER: Alle Verluste
loss_factor = 1.0
for scenario in delivery_problems:
    if scenario.component_type == 'saddles':
        loss_factor *= (1.0 - scenario.loss_percentage)
shipment_qty = int(round(planned_shipment_qty * loss_factor))
```

```python
# In get_inbound_log_dataframe():
# NEU: Szenarien anwenden
if self.scenario_manager:
    delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(day_index)
    loss_factor = 1.0
    for scenario in delivery_problems:
        if scenario.component_type == 'saddles':
            loss_factor *= (1.0 - scenario.loss_percentage)
    # Reduziere Versandmengen
    for s in all_saddles:
        shipments_today[s] = int(round(shipments_today[s] * loss_factor))
```

### Phase 2: Langfristige Refaktorierung (Lösung 1)

**Ziel:** Single Source of Truth etablieren

**Änderungen:**
1. Pool-Logik in `process_shipments()` verschieben
2. Szenarien zentral anwenden
3. Tabellen lesen nur noch aus `transport_status`

**Vorteile:**
- ✅ Konsistenz garantiert
- ✅ Einfacher zu warten
- ✅ Szenarien zentral verwaltet

---

## 🎯 Konkrete Empfehlung

### Für den empfohlenen Fix (Warenbestand-Problem)

**Kurzfristig:**
- ✅ Fix implementieren (vereinfachte Bestandslogik)
- ✅ Szenarien in beiden Tabellen **konsistent** anwenden (Phase 1)

**Langfristig:**
- 🔄 Refaktorierung zu Single Source of Truth (Phase 2)
- 🔄 Pool-Logik zentralisieren
- 🔄 Szenarien zentral verwalten

### Datenfluss nach Fix + Phase 1

```
transport_status (Single Source of Truth für Bestellungen)
    ↓
    ├─→ get_supplier_log_dataframe()
    │   └─→ Pool-Logik (eigene Berechnung)
    │   └─→ Bestandslogik (vereinfacht)
    │   └─→ Szenarien: VOLLSTÄNDIG (alle Verluste)
    │
    ├─→ get_inbound_log_dataframe()
    │   └─→ Pool-Logik (eigene Berechnung, GLEICHE Logik)
    │   └─→ Szenarien: VOLLSTÄNDIG (alle Verluste) ✅ NEU
    │
    └─→ process_shipments() (während Simulation)
        └─→ Szenarien: VOLLSTÄNDIG (Verluste + Verspätungen)
```

**Konsistenz:**
- ✅ Beide Tabellen wenden Szenarien **gleich** an
- ✅ Beide Tabellen verwenden **gleiche** Pool-Logik
- ✅ Unterschiede nur durch Bestandslogik (erwartet)

---

## ⚠️ Wichtige Erkenntnisse

### 1. Szenarien werden aktuell inkonsistent angewendet

- Supplier-Log: Nur 100% Verlust
- Inbound-Log: Keine Szenarien
- `process_shipments()`: Vollständig

**Problem:** Tabellen zeigen falsche Mengen, wenn Szenarien aktiv sind.

### 2. Datenfluss ist unklar

- Drei verschiedene Berechnungen für Versandmengen
- Keine Single Source of Truth
- Inkonsistenzen zwischen Tabellen

**Problem:** Schwer zu warten, Fehleranfällig.

### 3. Bestandslogik ist komplex

- `cumulative_shipped` wird inkorrekt verwendet
- Bestandsbegrenzung führt zu Inkonsistenzen
- Pool-Logik und Bestandslogik sind getrennt

**Problem:** 4.177 Stück "verloren".

---

## 🎯 Nächste Schritte

1. **Sofort:** Fix für Warenbestand-Problem implementieren
2. **Sofort:** Szenarien in Inbound-Log hinzufügen (Phase 1)
3. **Sofort:** Szenarien in Supplier-Log vollständig anwenden (Phase 1)
4. **Langfristig:** Refaktorierung zu Single Source of Truth (Phase 2)

**Priorität:**
- 🔴 Hoch: Fix für Warenbestand-Problem
- 🟡 Mittel: Szenarien konsistent anwenden (Phase 1)
- 🟢 Niedrig: Refaktorierung (Phase 2)
