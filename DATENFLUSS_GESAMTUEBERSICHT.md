# Datenfluss Gesamtübersicht: Aktueller Stand, Probleme und Lösungen

**Datum:** 2026-01-22  
**Ziel:** Vollständige Übersicht über Datenfluss, Mehrfachberechnungen, Szenarien-Probleme und Lösungsansätze

---

## 📊 AKTUELLER DATENFLUSS (Visualisierung)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: STAMMDATEN & SZENARIEN                                             │
│  • MasterData (BOM, Verkaufsanteile, Saisonalität)                         │
│  • ScenarioManager (Marketing, Wasserschaden, Lieferantenausfall, etc.)     │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE                                                        │
│  └─→ calculate_volume_planning_demand()                                     │
│      ├─→ daily_demands_planned[day][product] (ohne Marketing)            │
│      └─→ daily_demands_actual[day][product] (mit Marketing)                │
│      └─→ Gespeichert in: st.session_state.daily_demands_*                  │
│                                                                              │
│  ✅ SINGLE SOURCE OF TRUTH                                                  │
│  Verwendet von:                                                              │
│  • Page 2: Volumenplanung (Anzeige)                                         │
│  • Simulator (Produktionsplanung)                                           │
│  • Page 3: Lieferant China (Bestelleingang)                                 │
│                                                                              │
│  ⚠️ PROBLEM: Materiallager berechnet Nachfrage NEU (statt zu lesen)         │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: SIMULATION (Simulator.run())                                     │
│  └─→ Verwendet daily_demands_actual für Produktionsplanung                  │
│  └─→ Erstellt:                                                               │
│      ├─→ results_df (Daily_Target, Actual_Build, etc.)                     │
│      ├─→ kpis (service_level, total_demand, total_produced)                 │
│      └─→ simulator (ProductionPlanner, ChinaTransportManager, etc.)          │
│      └─→ Gespeichert in: st.session_state.results_df, kpis, simulator    │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: PRODUKTION (Deutschland)                                         │
│  └─→ ProductionPlanner.plan_daily_production()                            │
│      └─→ production_logs[product][day]                                     │
│          ├─→ geplante PM                                                   │
│          ├─→ tatsächliche PM                                               │
│          ├─→ fertiggestellte PM                                            │
│          ├─→ Backlog                                                        │
│          └─→ Materialverbrauch                                              │
│      └─→ Gespeichert in: simulator.production_planner.production_logs      │
│                                                                              │
│  ✅ SINGLE SOURCE OF TRUTH (für deutsche Produktion)                        │
│  Verwendet von:                                                              │
│  • Page 6: Produktion (Anzeige) ✅                                          │
│                                                                              │
│  ⚠️ PROBLEM: Materiallager berechnet Produktion NEU (statt zu lesen)      │
│  ⚠️ PROBLEM: Fertigproduktelager verteilt proportional (statt zu lesen)    │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: TRANSPORT (China → Deutschland)                                  │
│  └─→ ChinaTransportManager.process_shipments()                            │
│      └─→ transport_status[(order_day, order_id)]                            │
│          ├─→ quantity (ursprünglich)                                       │
│          ├─→ actual_quantity (nach Szenarien)                              │
│          ├─→ ship_departure_day                                            │
│          ├─→ ship_arrival_day                                              │
│          ├─→ available_day                                                 │
│          └─→ shipped (verschickt?)                                          │
│      └─→ Gespeichert in: simulator.china_transport_manager.transport_status│
│                                                                              │
│  ✅ SINGLE SOURCE OF TRUTH (für Transport)                                  │
│  Verwendet von:                                                              │
│  • Simulator (Wareneingang) ✅                                              │
│  • Page 5: Materiallager (Lagerzugang) ✅                                   │
│                                                                              │
│  ⚠️ PROBLEM: Supplier-Log berechnet Versandmengen NEU (statt zu lesen)      │
│  ⚠️ PROBLEM: Inbound-Log berechnet Versandmengen NEU (statt zu lesen)    │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 5: MATERIALBESTÄNDE                                                 │
│  └─→ Materiallager.create_saddle_inventory_log()                            │
│      └─→ material_inventory_data[date][saddle_type]                        │
│          ├─→ Bestand morgens                                               │
│          ├─→ Bestand abends                                                 │
│          ├─→ Lagerzugang                                                    │
│          └─→ Lagerabgang                                                    │
│      └─→ Gespeichert in: st.session_state.material_inventory_data           │
│                                                                              │
│  ✅ SINGLE SOURCE OF TRUTH (für Materialbestände)                           │
│  Verwendet von:                                                              │
│  • Page 5: Materiallager (Anzeige) ✅                                      │
│  • Page 1: Reporting (Material-KPIs) ✅                                    │
│                                                                              │
│  ⚠️ PROBLEM: ProductionPlanner berechnet Bestände NEU (statt zu lesen)    │
│  ⚠️ PROBLEM: Simulator initialisiert Bestand NEU (statt zu lesen)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 MEHRFACHBERECHNUNGEN (Detailliert)

### **1. Nachfrage-Berechnung**

**Wo wird Nachfrage berechnet?**

| Komponente | Berechnet? | Quelle | Problem |
|------------|------------|--------|---------|
| **Volumenplanung** | ✅ Ja | `calculate_volume_planning_demand()` | ✅ Single Source of Truth |
| **Simulator** | ❌ Nein | Liest aus `daily_demands_actual` | ✅ Korrekt |
| **Lieferant China** | ❌ Nein | Liest aus `daily_demands_actual` | ✅ Korrekt |
| **Materiallager** | ⚠️ **JA** | Berechnet NEU mit `DemandCalculator` | ❌ **Mehrfachberechnung** |

**Problem:**
- Materiallager berechnet Nachfrage **neu** (Zeilen 159-198 in `pages/5_materiallager.py`)
- Verwendet `DemandCalculator` und `calculate_daily_demand_per_product_dict()`
- **Risiko:** Kann von Volumenplanung abweichen (z.B. durch unterschiedliche Carry-Over-Logik)

**Auswirkung:**
- Inkonsistente Nachfrage zwischen Materiallager und Volumenplanung
- Marketingaktion könnte unterschiedlich angewendet werden

---

### **2. Produktions-Berechnung**

**Wo wird Produktion berechnet?**

| Komponente | Berechnet? | Quelle | Problem |
|------------|------------|--------|---------|
| **ProductionPlanner** | ✅ Ja | `plan_daily_production()` | ✅ Single Source of Truth |
| **Produktion-Seite** | ❌ Nein | Liest aus `production_logs` | ✅ Korrekt |
| **Materiallager** | ⚠️ **JA** | Berechnet NEU (proportional) | ❌ **Mehrfachberechnung** |
| **Fertigproduktelager** | ⚠️ **JA** | Verteilt proportional | ❌ **Mehrfachberechnung** |

**Problem:**
- Materiallager berechnet Produktionsverteilung **neu** (Zeilen 152-239 in `pages/5_materiallager.py`)
  - Verwendet `DemandCalculator` oder proportionale Verteilung
  - **Risiko:** Kann von ProductionPlanner abweichen (z.B. durch Priorisierung, Backlog)
- Fertigproduktelager verteilt Produktion **proportional** (Zeile 84 in `pages/7_fertigproduktelager.py`)
  - Verwendet `actual_build * product_share`
  - **Risiko:** Kann von ProductionPlanner abweichen

**Auswirkung:**
- Inkonsistente Produktionsverteilung zwischen Seiten
- Materiallager zeigt falschen Verbrauch pro Satteltyp
- Fertigproduktelager zeigt falsche Produktionsmengen

---

### **3. Transport/Versand-Berechnung**

**Wo werden Versandmengen berechnet?**

| Komponente | Berechnet? | Quelle | Problem |
|------------|------------|--------|---------|
| **process_shipments()** | ✅ Ja | Erstellt `transport_status` | ✅ Single Source of Truth |
| **Supplier-Log** | ⚠️ **JA** | Berechnet NEU (Pool-Logik) | ❌ **Mehrfachberechnung** |
| **Inbound-Log** | ⚠️ **JA** | Berechnet NEU (Pool-Logik) | ❌ **Mehrfachberechnung** |

**Problem:**
- Supplier-Log berechnet Versandmengen **neu** (Zeilen 661-724 in `simulation/china_transport.py`)
  - Verwendet Pool-Logik (tägliche Berechnung von Gesamtpool, Losgröße, Verteilung)
  - **Risiko:** Kann von `transport_status` abweichen
- Inbound-Log berechnet Versandmengen **neu** (Zeilen 892-963 in `simulation/china_transport.py`)
  - Verwendet Pool-Logik (gleiche Logik wie Supplier-Log)
  - **Risiko:** Kann von `transport_status` abweichen

**Auswirkung:**
- Inkonsistente Versandmengen zwischen Supplier-Log und Inbound-Log
- Szenarien (Lieferprobleme) werden möglicherweise unterschiedlich angewendet

---

### **4. Materialbestands-Berechnung**

**Wo werden Materialbestände berechnet?**

| Komponente | Berechnet? | Quelle | Problem |
|------------|------------|--------|---------|
| **Materiallager** | ✅ Ja | `create_saddle_inventory_log()` | ✅ Single Source of Truth |
| **ProductionPlanner** | ⚠️ **JA** | Berechnet NEU (aus Inbound-Tabelle) | ❌ **Mehrfachberechnung** |
| **Simulator** | ⚠️ **JA** | Initialisiert NEU (aus transport_status) | ❌ **Mehrfachberechnung** |

**Problem:**
- ProductionPlanner berechnet Bestände **neu** (Zeilen 507-577 in `simulation/production_planner.py`)
  - Liest aus Inbound-Tabelle und reduziert um Verbrauch
  - Verwendet `_consumption_by_saddle` für Verbrauch
  - **Risiko:** Kann von Materiallager abweichen (z.B. durch unterschiedliche Verbrauchsberechnung)
- Simulator initialisiert Bestand **neu** (Zeilen 88-127 in `simulation/simulator.py`)
  - Berechnet aus `transport_status` (summiert `actual_quantity` bis Vorjahr)
  - **Risiko:** Kann von Materiallager abweichen

**Auswirkung:**
- Inkonsistente Bestände zwischen ProductionPlanner und Materiallager
- ProductionPlanner sieht andere Bestände als Materiallager-Seite

---

## 🎯 SZENARIEN-PROBLEME

### **Problem 1: Inkonsistente Szenarien-Anwendung**

**Aktuelle Situation:**

| Szenario | Wo angewendet? | Konsistent? | Problem |
|----------|----------------|------------|---------|
| **Marketingaktion** | Volumenplanung, Simulator | ✅ Ja | ✅ Korrekt (Single Source of Truth) |
| **Wasserschaden** | Simulator, Materiallager | ⚠️ **Teilweise** | ⚠️ Wird an verschiedenen Stellen angewendet |
| **Lieferantenausfall** | process_shipments() | ✅ Ja | ✅ Korrekt |
| **Lieferprobleme** | process_shipments() | ✅ Ja | ✅ Korrekt (in `actual_quantity`) |

**Problem:**
- Marketingaktion wird **zentral** in Volumenplanung angewendet → ✅ Korrekt
- Lieferprobleme werden **zentral** in `process_shipments()` angewendet → ✅ Korrekt
- Wasserschaden wird **an mehreren Stellen** angewendet:
  - Simulator (Zeile 202-207): Reduziert `inventory.stock_saddles`
  - Materiallager: Müsste auch berücksichtigt werden (wird derzeit nicht getestet)

**Auswirkung:**
- Inkonsistente Szenarien-Anwendung
- Szenarien werden möglicherweise mehrfach angewendet oder übersehen

---

### **Problem 2: Szenarien werden nicht weitergegeben**

**Aktuelle Situation:**

```
Marketingaktion
└─→ daily_demands_actual (mit Marketing) ✅
    └─→ ProductionPlanner ✅
        └─→ production_logs ✅
            └─→ Materiallager ⚠️ (berechnet NEU, Marketing könnte verloren gehen)
            └─→ Fertigproduktelager ⚠️ (verteilt proportional, Marketing könnte verloren gehen)

Lieferprobleme
└─→ transport_status.actual_quantity (mit Verlusten) ✅
    └─→ Supplier-Log ⚠️ (berechnet NEU, Szenarien könnten verloren gehen)
    └─→ Inbound-Log ⚠️ (berechnet NEU, Szenarien könnten verloren gehen)
    └─→ Materiallager ✅ (verwendet transport_status)

Wasserschaden
└─→ inventory.stock_saddles (reduziert) ✅
    └─→ ProductionPlanner ⚠️ (berechnet Bestände NEU, Wasserschaden könnte verloren gehen)
```

**Problem:**
- Szenarien werden **zentral** angewendet (z.B. Marketing in Volumenplanung, Lieferprobleme in `process_shipments()`)
- Aber: Komponenten, die Daten **neu berechnen**, sehen Szenarien **nicht**
- **Risiko:** Szenarien werden "überschrieben" durch Neuberechnung

**Auswirkung:**
- Inkonsistente Szenarien-Anwendung
- Szenarien werden möglicherweise ignoriert

---

### **Problem 3: Zirkuläre Abhängigkeiten bei Szenarien**

**Aktuelle Situation:**

```
ProductionPlanner benötigt Materialbestände
└─→ Berechnet Bestände aus Inbound-Tabelle
    └─→ Inbound-Tabelle benötigt transport_status
        └─→ transport_status wird in process_shipments() erstellt
            └─→ process_shipments() benötigt ProductionPlanner (für Bestellungen?)
```

**Problem:**
- ProductionPlanner benötigt Materialbestände **während** der Simulation
- Materiallager berechnet Bestände **nach** der Simulation
- **Zirkuläre Abhängigkeit:** ProductionPlanner kann nicht auf Materiallager-Bestände zugreifen

**Auswirkung:**
- ProductionPlanner muss Bestände **neu berechnen** (aus Inbound-Tabelle)
- Inkonsistenz: ProductionPlanner sieht andere Bestände als Materiallager

---

## 💡 LÖSUNGSANSÄTZE

### **Lösung 1: Single Source of Truth etablieren**

**Prinzip:** Jede Information wird **einmal berechnet** und dann **weitergegeben**, nicht neu berechnet.

**Konkrete Umsetzung:**

1. **Nachfrage:**
   - ✅ Bereits Single Source of Truth (`daily_demands_actual`)
   - ⚠️ Materiallager sollte aus Session State lesen (statt neu berechnen)

2. **Produktion:**
   - ✅ Bereits Single Source of Truth (`production_logs`)
   - ⚠️ Materiallager sollte aus `production_logs` lesen (statt neu berechnen)
   - ⚠️ Fertigproduktelager sollte aus `production_logs` lesen (statt proportional verteilen)

3. **Transport:**
   - ✅ Bereits Single Source of Truth (`transport_status`)
   - ⚠️ Supplier-Log sollte aus `transport_status` lesen (statt neu berechnen)
   - ⚠️ Inbound-Log sollte aus `transport_status` lesen (statt neu berechnen)

4. **Materialbestände:**
   - ✅ Bereits Single Source of Truth (`material_inventory_data`)
   - ⚠️ ProductionPlanner sollte aus `material_inventory_data` lesen (wenn verfügbar, sonst Fallback)
   - ⚠️ Simulator sollte Initialbestand aus `material_inventory_data` lesen (wenn verfügbar, sonst Fallback)

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Daten
- ✅ Szenarien-ready: Szenarien werden automatisch weitergegeben
- ✅ Performance: Keine Mehrfachberechnungen

---

### **Lösung 2: Zwei-Phasen-Ansatz (für Zirkuläre Abhängigkeiten)**

**Problem:** ProductionPlanner benötigt Materialbestände **während** Simulation, Materiallager berechnet **nach** Simulation.

**Lösung:**

**Phase A: Simulation (ohne Materiallager)**
1. Simulator läuft (365 Tage)
2. ProductionPlanner berechnet Produktion (verwendet Inbound-Tabelle für Bestände)
3. ChinaTransportManager verarbeitet Versand (erstellt `transport_status`)
4. `production_logs` wird erstellt

**Phase B: Materiallager-Berechnung (nach Simulation)**
1. Materiallager liest Produktion aus `production_logs`
2. Materiallager berechnet Bestände
3. `material_inventory_data` wird erstellt

**Phase C: Optimierung (optional, für nächste Simulation)**
1. ProductionPlanner verwendet `material_inventory_data` (wenn verfügbar)
2. Sonst: Fallback auf Inbound-Tabelle

**Vorteile:**
- ✅ Keine Zirkulären Abhängigkeiten
- ✅ Konsistenz: Materiallager verwendet Produktion aus `production_logs`
- ✅ Flexibel: ProductionPlanner kann Fallback verwenden

---

### **Lösung 3: Konsistente Szenarien-Anwendung**

**Prinzip:** Szenarien werden **zentral** angewendet und dann **automatisch weitergegeben**.

**Konkrete Umsetzung:**

1. **Marketingaktion:**
   - ✅ Wird zentral in Volumenplanung angewendet → `daily_demands_actual`
   - ✅ Wird automatisch weitergegeben an: Simulator, ProductionPlanner
   - ⚠️ Materiallager sollte aus `daily_demands_actual` lesen (statt neu berechnen)

2. **Lieferprobleme:**
   - ✅ Werden zentral in `process_shipments()` angewendet → `transport_status.actual_quantity`
   - ⚠️ Supplier-Log sollte aus `transport_status` lesen (statt neu berechnen)
   - ⚠️ Inbound-Log sollte aus `transport_status` lesen (statt neu berechnen)

3. **Wasserschaden:**
   - ✅ Wird zentral im Simulator angewendet → `inventory.stock_saddles`
   - ⚠️ Materiallager sollte Wasserschaden berücksichtigen (wenn verfügbar)
   - ⚠️ ProductionPlanner sollte aus `material_inventory_data` lesen (Wasserschaden bereits berücksichtigt)

**Vorteile:**
- ✅ Konsistenz: Szenarien werden zentral angewendet
- ✅ Automatisch: Szenarien werden weitergegeben (nicht überschrieben)
- ✅ Einfach: Keine Szenarien-Logik in jeder Komponente

---

## 🎯 OPTIMALER DATENFLUSS

### **Ziel-Architektur:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: STAMMDATEN & SZENARIEN                                             │
│  • MasterData                                                               │
│  • ScenarioManager                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE (SSoT)                                                  │
│  calculate_volume_planning_demand()                                         │
│  └─→ daily_demands_actual (mit Marketing)                                  │
│      ↓                                                                       │
│      • Simulator (Produktionsplanung)                                       │
│      • Lieferant China (Bestelleingang)                                     │
│      • Materiallager (für Verbrauch) ← NEU: Liest statt neu zu berechnen    │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: PRODUKTION (SSoT)                                                 │
│  ProductionPlanner.plan_daily_production()                                  │
│  └─→ production_logs (mit Marketing)                                       │
│      ↓                                                                       │
│      • Produktion-Seite (Anzeige)                                           │
│      • Materiallager (Lagerabgang) ← NEU: Liest statt neu zu berechnen     │
│      • Fertigproduktelager (Lagerzugang) ← NEU: Liest statt proportional  │
│      • Reporting (KPIs)                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: TRANSPORT (SSoT)                                                   │
│  ChinaTransportManager.process_shipments()                                  │
│  └─→ transport_status (mit Lieferproblemen)                                 │
│      ↓                                                                       │
│      • Supplier-Log (Warenausgang) ← NEU: Liest statt neu zu berechnen     │
│      • Inbound-Log (Versandmengen) ← NEU: Liest statt neu zu berechnen     │
│      • Materiallager (Lagerzugang)                                          │
│      • Simulator (Wareneingang)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: MATERIALBESTÄNDE (SSoT)                                            │
│  Materiallager.create_saddle_inventory_log()                                │
│  └─→ material_inventory_data (mit Wasserschaden)                            │
│      ↓                                                                       │
│      • Materiallager-Seite (Anzeige)                                        │
│      • Reporting (Material-KPIs)                                            │
│      • ProductionPlanner (Materialverfügbarkeit) ← NEU: Liest (wenn verfügbar)│
│      • Simulator (Initialbestand) ← NEU: Liest (wenn verfügbar)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 KONKRETE UMSETZUNGSSCHRITTE

### **Schritt 1: Nachfrage als SSoT (Einfach)**

**Problem:** Materiallager berechnet Nachfrage neu

**Lösung:**
- Materiallager liest aus `st.session_state.daily_demands_actual`
- Fallback: Alte Logik (wenn nicht verfügbar)

**Aufwand:** Niedrig  
**Risiko:** Niedrig  
**Nutzen:** Hoch (Grundlage für alles weitere)

---

### **Schritt 2: Produktion als SSoT (Mittel)**

**Problem:** Materiallager und Fertigproduktelager berechnen Produktion neu

**Lösung:**
- Helper-Funktion in ProductionPlanner: `get_production_by_product_for_day()`
- Materiallager liest aus `production_logs`
- Fertigproduktelager liest aus `production_logs`
- Fallback: Alte Logik (wenn nicht verfügbar)

**Aufwand:** Mittel  
**Risiko:** Niedrig  
**Nutzen:** Hoch (Konsistenz zwischen Materiallager, Fertigproduktelager, Produktion)

**WICHTIG:** Diese Schritte erfolgen **NACH** der Simulation, da `production_logs` erst dann verfügbar ist.

---

### **Schritt 3: Transport als SSoT (Mittel)**

**Problem:** Supplier-Log und Inbound-Log berechnen Versandmengen neu

**Lösung:**
- Helper-Funktion in ChinaTransportManager: `get_shipment_quantities_by_day()`
- Supplier-Log liest aus `transport_status`
- Inbound-Log liest aus `transport_status`
- Fallback: Alte Pool-Logik (wenn keine Versanddaten vorhanden)

**Aufwand:** Mittel  
**Risiko:** Niedrig  
**Nutzen:** Hoch (Konsistenz zwischen Supplier-Log und Inbound-Log)

**WICHTIG:** Diese Schritte erfolgen **NACH** der Simulation, da `transport_status` erst dann vollständig ist.

---

### **Schritt 4: Materialbestände als SSoT (Komplex - Zirkuläre Abhängigkeit)**

**Problem:** ProductionPlanner und Simulator berechnen Bestände neu

**Lösung:**
- **Zwei-Phasen-Ansatz:**
  1. **Erste Simulation:** ProductionPlanner verwendet Inbound-Tabelle (wie bisher)
  2. **Materiallager-Berechnung:** Materiallager liest Produktion aus `production_logs`
  3. **Nächste Simulation:** ProductionPlanner verwendet `material_inventory_data` (wenn verfügbar, sonst Fallback)

**Aufwand:** Hoch  
**Risiko:** Mittel (Zirkuläre Abhängigkeit muss gelöst werden)  
**Nutzen:** Hoch (Konsistenz zwischen ProductionPlanner und Materiallager)

---

## ⚠️ POTENZIELLE PROBLEME BEI SZENARIEN-IMPLEMENTIERUNG

### **Problem 1: Szenarien werden überschrieben**

**Szenario:** Marketingaktion erhöht Nachfrage um 50%

**Aktuell:**
1. Volumenplanung: `daily_demands_actual = 15` (mit Marketing) ✅
2. ProductionPlanner: Verwendet `daily_demands_actual = 15` ✅
3. Materiallager: Berechnet Nachfrage **neu** → könnte `daily_demands_actual` ignorieren ❌

**Risiko:**
- Materiallager sieht andere Nachfrage als Volumenplanung
- Marketingaktion wird möglicherweise ignoriert

**Lösung:**
- Materiallager liest aus `daily_demands_actual` (statt neu zu berechnen)

---

### **Problem 2: Szenarien werden mehrfach angewendet**

**Szenario:** Lieferprobleme reduzieren Versandmenge um 10%

**Aktuell:**
1. `process_shipments()`: `actual_quantity = 90` (nach Verlusten) ✅
2. Supplier-Log: Berechnet Versandmengen **neu** → könnte `actual_quantity` ignorieren ❌
3. Inbound-Log: Berechnet Versandmengen **neu** → könnte `actual_quantity` ignorieren ❌

**Risiko:**
- Supplier-Log und Inbound-Log sehen andere Versandmengen als `transport_status`
- Lieferprobleme werden möglicherweise ignoriert

**Lösung:**
- Supplier-Log und Inbound-Log lesen aus `transport_status` (statt neu zu berechnen)

---

### **Problem 3: Szenarien werden zu spät angewendet**

**Szenario:** Wasserschaden reduziert Bestand um 50%

**Aktuell:**
1. Simulator: Reduziert `inventory.stock_saddles` ✅
2. ProductionPlanner: Berechnet Bestände **neu** (aus Inbound-Tabelle) → sieht Wasserschaden nicht ❌
3. Materiallager: Berechnet Bestände **nach** Simulation → sieht Wasserschaden nicht ❌

**Risiko:**
- ProductionPlanner sieht andere Bestände als Simulator
- Wasserschaden wird möglicherweise ignoriert

**Lösung:**
- ProductionPlanner liest aus `material_inventory_data` (wenn verfügbar, sonst Fallback)
- Materiallager berücksichtigt Wasserschaden (wenn verfügbar)

---

### **Problem 4: Zirkuläre Abhängigkeiten bei Szenarien**

**Szenario:** Marketingaktion + Wasserschaden

**Aktuell:**
1. Marketingaktion: Erhöht Nachfrage → `daily_demands_actual` ✅
2. ProductionPlanner: Verwendet `daily_demands_actual` → produziert mehr ✅
3. Materiallager: Berechnet Produktion **neu** → könnte Marketing ignorieren ❌
4. Wasserschaden: Reduziert Bestand → `inventory.stock_saddles` ✅
5. ProductionPlanner: Berechnet Bestände **neu** → sieht Wasserschaden nicht ❌

**Risiko:**
- Szenarien werden inkonsistent angewendet
- Zirkuläre Abhängigkeiten verhindern korrekte Anwendung

**Lösung:**
- Zwei-Phasen-Ansatz: Simulation läuft zuerst, Materiallager danach
- Alle Komponenten lesen aus Single Source of Truth (statt neu zu berechnen)

---

## 🎯 OPTIMALER DATENFLUSS (Ziel-Architektur)

### **Prinzipien:**

1. **Single Source of Truth:** Jede Information wird einmal berechnet und weitergegeben
2. **Konsistente Szenarien-Anwendung:** Szenarien werden zentral angewendet und automatisch weitergegeben
3. **Klare Datenfluss-Hierarchie:** Von vorne nach hinten (Nachfrage → Produktion → Transport → Materialbestände)
4. **Zwei-Phasen-Ansatz:** Simulation läuft zuerst, Materiallager danach (löst Zirkuläre Abhängigkeiten)

---

### **Datenfluss-Diagramm (Optimal):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: STAMMDATEN & SZENARIEN                                             │
│  • MasterData                                                               │
│  • ScenarioManager                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE (SSoT)                                                  │
│  calculate_volume_planning_demand()                                         │
│  └─→ daily_demands_actual (mit Marketing)                                  │
│      ↓                                                                       │
│      • Simulator (Produktionsplanung)                                       │
│      • Lieferant China (Bestelleingang)                                     │
│      • Materiallager (für Verbrauch) ✅ Liest aus Session State             │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: PRODUKTION (SSoT)                                                 │
│  ProductionPlanner.plan_daily_production()                                  │
│  └─→ production_logs (mit Marketing)                                       │
│      ↓                                                                       │
│      • Produktion-Seite (Anzeige)                                           │
│      • Materiallager (Lagerabgang) ✅ Liest aus production_logs            │
│      • Fertigproduktelager (Lagerzugang) ✅ Liest aus production_logs       │
│      • Reporting (KPIs)                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: TRANSPORT (SSoT)                                                   │
│  ChinaTransportManager.process_shipments()                                  │
│  └─→ transport_status (mit Lieferproblemen)                                 │
│      ↓                                                                       │
│      • Supplier-Log (Warenausgang) ✅ Liest aus transport_status            │
│      • Inbound-Log (Versandmengen) ✅ Liest aus transport_status            │
│      • Materiallager (Lagerzugang)                                          │
│      • Simulator (Wareneingang)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: MATERIALBESTÄNDE (SSoT)                                           │
│  Materiallager.create_saddle_inventory_log()                                │
│  └─→ material_inventory_data (mit Wasserschaden)                            │
│      ↓                                                                       │
│      • Materiallager-Seite (Anzeige)                                        │
│      • Reporting (Material-KPIs)                                            │
│      • ProductionPlanner (Materialverfügbarkeit) ✅ Liest (wenn verfügbar) │
│      • Simulator (Initialbestand) ✅ Liest (wenn verfügbar)                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 ZUSAMMENFASSUNG: MEHRFACHBERECHNUNGEN

### **Aktuelle Mehrfachberechnungen:**

| Bereich | Komponente | Berechnet? | Sollte lesen aus: | Status |
|---------|------------|------------|-------------------|--------|
| **Nachfrage** | Materiallager | ⚠️ Ja | `daily_demands_actual` | ❌ Mehrfachberechnung |
| **Produktion** | Materiallager | ⚠️ Ja | `production_logs` | ❌ Mehrfachberechnung |
| **Produktion** | Fertigproduktelager | ⚠️ Ja | `production_logs` | ❌ Mehrfachberechnung |
| **Transport** | Supplier-Log | ⚠️ Ja | `transport_status` | ❌ Mehrfachberechnung |
| **Transport** | Inbound-Log | ⚠️ Ja | `transport_status` | ❌ Mehrfachberechnung |
| **Materialbestände** | ProductionPlanner | ⚠️ Ja | `material_inventory_data` | ❌ Mehrfachberechnung |
| **Materialbestände** | Simulator | ⚠️ Ja | `material_inventory_data` | ❌ Mehrfachberechnung |

---

## 🎯 SZENARIEN-PROBLEME (Detailliert)

### **Problem 1: Marketingaktion**

**Aktuell:**
- ✅ Wird zentral in Volumenplanung angewendet → `daily_demands_actual`
- ✅ Wird automatisch weitergegeben an: Simulator, ProductionPlanner
- ⚠️ Materiallager berechnet Nachfrage **neu** → Marketing könnte verloren gehen

**Risiko:**
- Materiallager sieht andere Nachfrage als Volumenplanung
- Marketingaktion wird möglicherweise ignoriert

**Lösung:**
- Materiallager liest aus `daily_demands_actual` (statt neu zu berechnen)

---

### **Problem 2: Lieferprobleme**

**Aktuell:**
- ✅ Werden zentral in `process_shipments()` angewendet → `transport_status.actual_quantity`
- ⚠️ Supplier-Log berechnet Versandmengen **neu** → Lieferprobleme könnten verloren gehen
- ⚠️ Inbound-Log berechnet Versandmengen **neu** → Lieferprobleme könnten verloren gehen

**Risiko:**
- Supplier-Log und Inbound-Log sehen andere Versandmengen als `transport_status`
- Lieferprobleme werden möglicherweise ignoriert

**Lösung:**
- Supplier-Log und Inbound-Log lesen aus `transport_status` (statt neu zu berechnen)

---

### **Problem 3: Wasserschaden**

**Aktuell:**
- ✅ Wird zentral im Simulator angewendet → `inventory.stock_saddles`
- ⚠️ ProductionPlanner berechnet Bestände **neu** → Wasserschaden könnte verloren gehen
- ⚠️ Materiallager berechnet Bestände **nach** Simulation → Wasserschaden könnte verloren gehen

**Risiko:**
- ProductionPlanner sieht andere Bestände als Simulator
- Wasserschaden wird möglicherweise ignoriert

**Lösung:**
- ProductionPlanner liest aus `material_inventory_data` (wenn verfügbar, sonst Fallback)
- Materiallager berücksichtigt Wasserschaden (wenn verfügbar)

---

### **Problem 4: Lieferantenausfall**

**Aktuell:**
- ✅ Wird zentral in `process_shipments()` geprüft → blockiert neue Bestellungen
- ✅ Bereits unterwegs befindliche Ware wird weiter transportiert
- ✅ Funktioniert korrekt

**Risiko:**
- Keine (funktioniert bereits korrekt)

---

## 💡 LÖSUNGSANSÄTZE (Detailliert)

### **Ansatz 1: Single Source of Truth etablieren**

**Prinzip:** Jede Information wird einmal berechnet und dann weitergegeben, nicht neu berechnet.

**Konkrete Umsetzung:**

1. **Nachfrage:**
   ```python
   # Materiallager (pages/5_materiallager.py)
   # VORHER: Berechnet neu
   product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
   
   # NACHHER: Liest aus Session State
   daily_demands_actual = st.session_state.get('daily_demands_actual', {})
   if day in daily_demands_actual:
       product_demands = daily_demands_actual[day]
   else:
       # Fallback: Alte Logik
       product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
   ```

2. **Produktion:**
   ```python
   # Materiallager (pages/5_materiallager.py)
   # VORHER: Berechnet neu
   production_by_product = {...}  # Neu berechnet
   
   # NACHHER: Liest aus production_logs
   planner = st.session_state.simulator.production_planner
   production_by_product = planner.get_production_by_product_for_day(day)
   ```

3. **Transport:**
   ```python
   # Supplier-Log (simulation/china_transport.py)
   # VORHER: Berechnet neu (Pool-Logik)
   # ... komplexe Pool-Berechnung ...
   
   # NACHHER: Liest aus transport_status
   shipments_by_day = self.get_shipment_quantities_by_day(...)
   shipment_results[day_idx] = shipments_by_day[day_idx].get(saddle_name, 0.0)
   ```

4. **Materialbestände:**
   ```python
   # ProductionPlanner (simulation/production_planner.py)
   # VORHER: Berechnet neu (aus Inbound-Tabelle)
   inbound_df = self.china_transport_manager.get_inbound_log_dataframe(...)
   # ... komplexe Berechnung ...
   
   # NACHHER: Liest aus material_inventory_data (wenn verfügbar)
   material_inventory_data = st.session_state.get('material_inventory_data', {})
   if material_inventory_data:
       stock_by_saddle = material_inventory_data[target_date]
   else:
       # Fallback: Alte Logik (Inbound-Tabelle)
       inbound_df = self.china_transport_manager.get_inbound_log_dataframe(...)
   ```

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Daten
- ✅ Szenarien-ready: Szenarien werden automatisch weitergegeben
- ✅ Performance: Keine Mehrfachberechnungen

---

### **Ansatz 2: Zwei-Phasen-Ansatz (für Zirkuläre Abhängigkeiten)**

**Problem:** ProductionPlanner benötigt Materialbestände während Simulation, Materiallager berechnet nach Simulation.

**Lösung:**

**Phase A: Simulation (ohne Materiallager)**
```python
# Simulator läuft (365 Tage)
for day in range(365):
    # ProductionPlanner verwendet Inbound-Tabelle für Bestände (wie bisher)
    production_by_product = self.production_planner.plan_daily_production(day, ...)
    # ... Rest der Simulation ...
```

**Phase B: Materiallager-Berechnung (nach Simulation)**
```python
# Materiallager liest Produktion aus production_logs
planner = st.session_state.simulator.production_planner
for day in range(365):
    production_by_product = planner.get_production_by_product_for_day(day)
    # ... Berechne Bestände ...
    material_inventory_data[current_date] = stock_morning.copy()
```

**Phase C: Optimierung (optional, für nächste Simulation)**
```python
# ProductionPlanner verwendet material_inventory_data (wenn verfügbar)
material_inventory_data = st.session_state.get('material_inventory_data', {})
if material_inventory_data:
    stock_by_saddle = material_inventory_data[target_date]
else:
    # Fallback: Inbound-Tabelle (wie bisher)
    inbound_df = self.china_transport_manager.get_inbound_log_dataframe(...)
```

**Vorteile:**
- ✅ Keine Zirkulären Abhängigkeiten
- ✅ Konsistenz: Materiallager verwendet Produktion aus `production_logs`
- ✅ Flexibel: ProductionPlanner kann Fallback verwenden

---

### **Ansatz 3: Konsistente Szenarien-Anwendung**

**Prinzip:** Szenarien werden zentral angewendet und dann automatisch weitergegeben.

**Konkrete Umsetzung:**

1. **Marketingaktion:**
   ```
   Marketingaktion
   └─→ Volumenplanung (zentral angewendet)
       └─→ daily_demands_actual (mit Marketing)
           └─→ Simulator (automatisch weitergegeben)
               └─→ ProductionPlanner (automatisch weitergegeben)
                   └─→ production_logs (mit Marketing)
                       └─→ Materiallager (automatisch weitergegeben) ✅
                       └─→ Fertigproduktelager (automatisch weitergegeben) ✅
   ```

2. **Lieferprobleme:**
   ```
   Lieferprobleme
   └─→ process_shipments() (zentral angewendet)
       └─→ transport_status.actual_quantity (mit Verlusten)
           └─→ Supplier-Log (automatisch weitergegeben) ✅
           └─→ Inbound-Log (automatisch weitergegeben) ✅
           └─→ Materiallager (automatisch weitergegeben) ✅
   ```

3. **Wasserschaden:**
   ```
   Wasserschaden
   └─→ Simulator (zentral angewendet)
       └─→ inventory.stock_saddles (reduziert)
           └─→ Materiallager (berücksichtigt Wasserschaden)
               └─→ material_inventory_data (mit Wasserschaden)
                   └─→ ProductionPlanner (automatisch weitergegeben) ✅
   ```

**Vorteile:**
- ✅ Konsistenz: Szenarien werden zentral angewendet
- ✅ Automatisch: Szenarien werden weitergegeben (nicht überschrieben)
- ✅ Einfach: Keine Szenarien-Logik in jeder Komponente

---

## 📋 PRIORISIERUNG DER LÖSUNGEN

### **Höchste Priorität (Sofort beheben):**

1. **Nachfrage als SSoT** (Schritt 1)
   - Materiallager liest aus `daily_demands_actual`
   - **Aufwand:** Niedrig
   - **Risiko:** Niedrig
   - **Nutzen:** Hoch (Grundlage für alles weitere)

2. **Produktion als SSoT** (Schritt 2)
   - Materiallager und Fertigproduktelager lesen aus `production_logs`
   - **Aufwand:** Mittel
   - **Risiko:** Niedrig
   - **Nutzen:** Hoch (Konsistenz zwischen Seiten)

3. **Transport als SSoT** (Schritt 3)
   - Supplier-Log und Inbound-Log lesen aus `transport_status`
   - **Aufwand:** Mittel
   - **Risiko:** Niedrig
   - **Nutzen:** Hoch (Konsistenz zwischen Tabellen)

---

### **Mittlere Priorität (Sollte behoben werden):**

4. **Materialbestände als SSoT** (Schritt 4)
   - ProductionPlanner liest aus `material_inventory_data` (wenn verfügbar)
   - Simulator liest Initialbestand aus `material_inventory_data` (wenn verfügbar)
   - **Aufwand:** Hoch (Zirkuläre Abhängigkeit)
   - **Risiko:** Mittel
   - **Nutzen:** Hoch (Konsistenz zwischen ProductionPlanner und Materiallager)

---

## ✅ ERGEBNIS: OPTIMALER DATENFLUSS

### **Nach Umsetzung:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INPUT: STAMMDATEN & SZENARIEN                                             │
│  • MasterData                                                               │
│  • ScenarioManager                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: NACHFRAGE (SSoT) ✅                                               │
│  daily_demands_actual (mit Marketing)                                       │
│  └─→ Simulator, Lieferant China, Materiallager ✅                          │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: PRODUKTION (SSoT) ✅                                              │
│  production_logs (mit Marketing)                                            │
│  └─→ Produktion, Materiallager, Fertigproduktelager, Reporting ✅          │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: TRANSPORT (SSoT) ✅                                               │
│  transport_status (mit Lieferproblemen)                                     │
│  └─→ Supplier-Log, Inbound-Log, Materiallager, Simulator ✅                 │
└─────────────────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: MATERIALBESTÄNDE (SSoT) ✅                                         │
│  material_inventory_data (mit Wasserschaden)                                │
│  └─→ Materiallager, Reporting, ProductionPlanner, Simulator ✅             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Daten
- ✅ Szenarien-ready: Szenarien werden automatisch weitergegeben
- ✅ Performance: Keine Mehrfachberechnungen
- ✅ Wartbarkeit: Änderungen nur an einer Stelle

---

## 📊 ZUSAMMENFASSUNG

### **Aktuelle Probleme:**

1. **Mehrfachberechnungen:**
   - Nachfrage: Materiallager berechnet neu
   - Produktion: Materiallager und Fertigproduktelager berechnen neu
   - Transport: Supplier-Log und Inbound-Log berechnen neu
   - Materialbestände: ProductionPlanner und Simulator berechnen neu

2. **Szenarien-Probleme:**
   - Szenarien werden möglicherweise überschrieben (durch Neuberechnung)
   - Szenarien werden möglicherweise mehrfach angewendet
   - Zirkuläre Abhängigkeiten verhindern korrekte Anwendung

3. **Inkonsistenzen:**
   - Verschiedene Komponenten sehen unterschiedliche Daten
   - Keine Garantie für Konsistenz

---

### **Lösungen:**

1. **Single Source of Truth etablieren:**
   - Jede Information wird einmal berechnet und weitergegeben
   - Alle Komponenten lesen aus Single Source of Truth

2. **Zwei-Phasen-Ansatz:**
   - Simulation läuft zuerst, Materiallager danach
   - Löst Zirkuläre Abhängigkeiten

3. **Konsistente Szenarien-Anwendung:**
   - Szenarien werden zentral angewendet
   - Automatisch weitergegeben (nicht überschrieben)

---

### **Empfohlene Reihenfolge:**

1. **Schritt 1:** Nachfrage als SSoT (einfach, keine Abhängigkeiten)
2. **Schritt 2:** Produktion als SSoT (abhängig von Nachfrage, keine Zirkulären Abhängigkeiten)
3. **Schritt 3:** Transport als SSoT (abhängig von Produktion, keine Zirkulären Abhängigkeiten)
4. **Schritt 4:** Materialbestände als SSoT (abhängig von Produktion, Zirkuläre Abhängigkeit → Zwei-Phasen-Ansatz)

---

**Die vollständige Übersicht wurde in `DATENFLUSS_GESAMTUEBERSICHT.md` gespeichert.**
