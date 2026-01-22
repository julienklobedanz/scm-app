# Datenfluss-Inkonsistenzen - Umfassende Analyse

**Datum:** 2026-01-22  
**Ziel:** Identifikation aller Inkonsistenzen im Datenfluss für Grundlage der Datenkonsistenz

---

## 📊 Übersicht: Gefundene Inkonsistenzen

| # | Bereich | Problem | Schweregrad | Betroffene Komponenten |
|---|---------|---------|-------------|----------------------|
| 1 | Transport/Versand | Supplier-Log vs Inbound-Log: Unterschiedliche Versandmengen | 🔴 Hoch | `china_transport.py` |
| 2 | Materialbestände | Mehrfachberechnung: Simulator vs Materiallager vs ProductionPlanner | 🟡 Mittel | `simulator.py`, `materiallager.py`, `production_planner.py` |
| 3 | Produktionsverteilung | Proportional vs Exakt: Unterschiedliche Berechnungen | 🟡 Mittel | `materiallager.py`, `fertigproduktelager.py`, `production_planner.py` |
| 4 | Backlog | Zwei verschiedene Backlog-Systeme: ProductionPlanner vs MarketBacklog | 🟡 Mittel | `production_planner.py`, `models/backlog.py` |
| 5 | Initialbestände | Berechnung aus transport_status vs Materiallager | 🟢 Niedrig | `simulator.py`, `materiallager.py` |
| 6 | Produktionsmengen | Actual_Build vs tatsächliche PM: Potenzielle Rundungsfehler | 🟢 Niedrig | `simulator.py`, `production_planner.py` |

---

## 🔴 KRITISCH: Transport/Versand-Inkonsistenz

### Problem 1.1: Supplier-Log vs Inbound-Log Versandmengen

**Beschreibung:**
- **Supplier-Log** (`get_supplier_log_dataframe`): Berechnet Warenausgang mit Bestandsbegrenzung
- **Inbound-Log** (`get_inbound_log_dataframe`): Berechnet Versandmengen ohne Bestandsbegrenzung
- **Ergebnis:** Unterschiedliche Versandmengen (z.B. 95.723 vs 99.630)

**Aktuelle Logik:**

**Supplier-Log (Zeilen 747-784):**
```python
current_stock = previous_stock + production_qty
planned_shipment_qty = shipment_results[day_idx]  # Aus Pool-Logik
# Bestandsbegrenzung:
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
```

**Inbound-Log (Zeilen 906-963):**
```python
# Pool-Logik (GLEICHE Logik wie Supplier-Log)
shipments_today = rounded  # Volle geplante Versandmenge
# KEINE Bestandsbegrenzung!
```

**Auswirkung:**
- Supplier-Log zeigt: 95.723 verschickt
- Inbound-Log zeigt: 99.630 verschickt
- **Differenz:** 3.907 Stück "verloren"

**Empfohlener Fix:**
- Vereinfachte Bestandslogik in Supplier-Log (wie bereits vorgeschlagen)
- Oder: Bestandsbegrenzung auch in Inbound-Log anwenden

---

## 🟡 MITTEL: Materialbestands-Inkonsistenzen

### Problem 2.1: Mehrfachberechnung von Materialbeständen

**Beschreibung:**
Materialbestände werden an **drei verschiedenen Stellen** berechnet:

1. **Simulator** (`simulator.py`):
   - `inventory.stock_saddles`: Globaler Pool-Bestand
   - Wird durch `inventory.add_stock()` und `inventory.consume_components()` aktualisiert

2. **Materiallager** (`pages/5_materiallager.py`):
   - `create_saddle_inventory_log()`: Berechnet Bestände pro Satteltyp
   - Liest aus Inbound-Tabelle: `get_inbound_log_dataframe()`
   - Berechnet Verbrauch aus `results_df['Actual_Build']`

3. **ProductionPlanner** (`simulation/production_planner.py`):
   - `_get_all_stocks_from_inbound_table()`: Liest aus Inbound-Tabelle
   - Berechnet Bestand pro Satteltyp: `inbound_stock - consumption`
   - Verwendet `_consumption_by_saddle` für Verbrauch

**Aktuelle Logik:**

**Simulator (Zeile 223):**
```python
arrived_qty = self.china_transport_manager.get_daily_arrival_qty(day)
if arrived_qty > 0:
    self.inventory.add_stock('saddles', arrived_qty)
# Verbrauch:
self.production_planner.consume_components(consumed)
```

**Materiallager (Zeilen 144-254):**
```python
# Zugang aus Inbound-Tabelle
receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {})
# Verbrauch aus results_df
actual_build = results_df.iloc[day]['Actual_Build']
# Berechnet Produktionsverteilung NEU (proportional)
production_by_product = {...}  # Neu berechnet
# Bestand: stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
```

**ProductionPlanner (Zeilen 507-572):**
```python
# Liest aus Inbound-Tabelle
inbound_df = self.china_transport_manager.get_inbound_log_dataframe(saddle_shares)
# Berechnet Bestand morgens für ALLE Sattel-Typen
for saddle_name in saddle_shares.keys():
    stock_morning = 0.0
    for _, row in inbound_df.iterrows():
        if avail_date <= target_date:
            stock_morning += float(qty_val)
# Reduziert um Verbrauch
stock_by_saddle_type[s_type] = max(0.0, inbound_stock - consumption)
```

**Probleme:**
1. **Materiallager** berechnet Produktionsverteilung **neu** (proportional)
2. **ProductionPlanner** verwendet **eigene Verbrauchsberechnung** (`_consumption_by_saddle`)
3. **Simulator** verwendet **globalen Pool** (`inventory.stock_saddles`)
4. **Keine Single Source of Truth** für Materialbestände

**Auswirkung:**
- Inkonsistente Bestände zwischen Materiallager-Seite und ProductionPlanner
- Potenzielle Rundungsfehler durch mehrfache Berechnungen

**Empfohlener Fix:**
- **Single Source of Truth:** Materiallager-Berechnung als Basis
- ProductionPlanner sollte Bestände aus Materiallager lesen (nicht neu berechnen)
- Simulator sollte Bestände aus Materiallager synchronisieren

---

### Problem 2.2: Materialbestand-Berechnung: Pool vs Typ-spezifisch

**Beschreibung:**
- **Simulator** verwendet: `inventory.stock_saddles` (globaler Pool)
- **ProductionPlanner** verwendet: Bestände pro Satteltyp (aus Inbound-Tabelle)
- **Materiallager** verwendet: Bestände pro Satteltyp (aus Inbound-Tabelle)

**Aktuelle Logik:**

**Simulator (Zeile 143):**
```python
current_saddle_stock = max(0.0, self.inventory.stock_saddles)  # Globaler Pool
```

**ProductionPlanner (Zeilen 149-156):**
```python
# Hole tatsächlichen Bestand pro Sattel-Typ aus Inbound-Tabelle
stock_by_saddle_type = {}
inbound_stocks = self._get_all_stocks_from_inbound_table(day, saddle_shares)
for s_type in saddle_shares.keys():
    inbound_stock = inbound_stocks.get(s_type, 0.0) or 0.0
    consumption = self._consumption_by_saddle.get(s_type, 0.0)
    stock_by_saddle_type[s_type] = max(0.0, inbound_stock - consumption)
```

**Problem:**
- Simulator verwendet **globalen Pool**, aber ProductionPlanner benötigt **typ-spezifische Bestände**
- **Inkonsistenz:** Globaler Pool kann nicht mit typ-spezifischen Beständen übereinstimmen

**Auswirkung:**
- ProductionPlanner sieht andere Bestände als Simulator
- Potenzielle Materialmangel-Fehlerkennung

**Empfohlener Fix:**
- Simulator sollte auch typ-spezifische Bestände verwenden
- Oder: ProductionPlanner sollte globalen Pool verwenden (mit proportionaler Verteilung)

---

## 🟡 MITTEL: Produktionsverteilung-Inkonsistenzen

### Problem 3.1: Proportional vs Exakte Verteilung

**Beschreibung:**
Produktionsmengen werden an **drei verschiedenen Stellen** unterschiedlich verteilt:

1. **ProductionPlanner** (`production_planner.py`):
   - Verwendet **exakte Nachfrage** aus `daily_demands_actual`
   - Produziert **pro Produkt** basierend auf Nachfrage + Backlog

2. **Materiallager** (`pages/5_materiallager.py`):
   - Berechnet Produktionsverteilung **neu** (Zeilen 196-227)
   - Verwendet `DemandCalculator` oder **proportionale Verteilung** nach `PRODUCT_SALES_SHARES`
   - **Problem:** Kann von ProductionPlanner abweichen

3. **Fertigproduktelager** (`pages/7_fertigproduktelager.py`):
   - Verwendet **proportionale Verteilung** nach `PRODUCT_SALES_SHARES` (Zeile 84)
   - **Problem:** Kann von ProductionPlanner abweichen

**Aktuelle Logik:**

**ProductionPlanner (Zeile 325):**
```python
production_by_product = self.production_planner.plan_daily_production(...)
# Exakte Produktion pro Produkt basierend auf Nachfrage + Backlog
```

**Materiallager (Zeilen 196-227):**
```python
# Berechnet Nachfrage pro Produkt NEU
product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
# Oder Fallback: Proportional nach PRODUCT_SALES_SHARES
share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share
production_by_product[product] = int(actual_build * share)
# Verteilt actual_build proportional zur Nachfrage
```

**Fertigproduktelager (Zeile 84):**
```python
product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
production_qty = actual_build * product_share  # Proportional
```

**Probleme:**
1. **Materiallager** berechnet Produktionsverteilung **neu** (kann abweichen)
2. **Fertigproduktelager** verwendet **proportionale Verteilung** (kann abweichen)
3. **ProductionPlanner** verwendet **exakte Nachfrage** (Single Source of Truth)

**Auswirkung:**
- Inkonsistente Produktionsverteilung zwischen Seiten
- Materiallager zeigt falschen Verbrauch pro Satteltyp
- Fertigproduktelager zeigt falsche Produktionsmengen

**Empfohlener Fix:**
- **Single Source of Truth:** ProductionPlanner-Produktion
- Materiallager sollte Produktion aus `production_logs` lesen (nicht neu berechnen)
- Fertigproduktelager sollte Produktion aus `production_logs` lesen (nicht proportional verteilen)

---

## 🟡 MITTEL: Backlog-Inkonsistenzen

### Problem 4.1: Zwei verschiedene Backlog-Systeme

**Beschreibung:**
Es gibt **zwei verschiedene Backlog-Systeme**, die unterschiedliche Dinge tracken:

1. **ProductionPlanner.backlog** (`production_planner.py`):
   - Backlog **pro Produkt** (nicht pro Markt)
   - Berechnung: `planned_pm - actual_pm + old_backlog`
   - Wird in Produktionsplanung verwendet

2. **MarketBacklog** (`models/backlog.py`):
   - Backlog **pro Markt** (DE, USA, FR, etc.)
   - Berechnung: `qty - market_demand` (bei Auslieferung)
   - Wird für Kunden-Backlog verwendet

**Aktuelle Logik:**

**ProductionPlanner (Zeilen 299-310):**
```python
# Backlog pro Produkt
for product in self.master_data.BOM.keys():
    planned_pm = product_demands.get(product, 0)  # Tagesbedarf OHNE Backlog
    actual_pm = production_by_product.get(product, 0)
    old_backlog = self.backlog.get(product, 0.0)
    self.backlog[product] = max(0.0, planned_pm - actual_pm + old_backlog)
```

**MarketBacklog (Zeilen 31-37):**
```python
# Backlog pro Markt
def receive_shipments(self, day: int, daily_target: float, markets: Dict[str, Dict]) -> None:
    if day in self.in_transit:
        for market, qty in self.in_transit[day].items():
            market_demand = daily_target * markets[market]['share']
            self.backlog[market] += (qty - market_demand)  # Kann negativ werden
```

**Probleme:**
1. **Zwei verschiedene Backlog-Berechnungen** für unterschiedliche Zwecke
2. **Keine Konsistenz** zwischen ProductionPlanner-Backlog und MarketBacklog
3. **MarketBacklog** kann negativ werden (Überbestand), **ProductionPlanner.backlog** nicht

**Auswirkung:**
- Verwirrung: Welcher Backlog ist der "richtige"?
- Inkonsistente Backlog-Anzeige in verschiedenen Seiten

**Empfohlener Fix:**
- **Klarstellung:** ProductionPlanner-Backlog = Produktions-Backlog, MarketBacklog = Kunden-Backlog
- **Dokumentation:** Beide Backlogs haben unterschiedliche Zwecke
- **Oder:** MarketBacklog aus ProductionPlanner-Backlog ableiten (konsistenter)

---

## 🟢 NIEDRIG: Initialbestands-Inkonsistenzen

### Problem 5.1: Initialbestand-Berechnung

**Beschreibung:**
Initialbestand wird an **zwei verschiedenen Stellen** berechnet:

1. **Simulator** (`simulator.py`, Zeilen 88-127):
   - `_initialize_stock_from_inbound()`: Berechnet aus `transport_status`
   - Summiert `actual_quantity` für alle Transporte bis Vorjahr

2. **Materiallager** (`pages/5_materiallager.py`):
   - Beginnt mit `stock_by_saddle = {s: 0.0 for s in saddle_types}`
   - Baut Bestand über Zeit auf (ab November Vorjahr)

**Aktuelle Logik:**

**Simulator (Zeilen 104-127):**
```python
cutoff_date = date(self.workday_calculator.year - 1, 12, 31)
initial_stock = 0.0
for (order_day, order_id), status in self.transport_status.items():
    avail_date = self.workday_calculator.get_date_from_day(available_day)
    if avail_date <= cutoff_date:
        qty = status.get('actual_quantity', status.get('quantity', 0.0))
        initial_stock += qty
self.inventory.stock_saddles = initial_stock
```

**Materiallager (Zeilen 125-254):**
```python
stock_by_saddle = {saddle_type: 0.0 for saddle_type in saddle_types}
start_date_log = date(planning_year - 1, 11, 1)
# Baut Bestand über Zeit auf
for day_offset in range(total_days):
    receipt_by_saddle = receipts_by_date_and_saddle.get(current_date, {})
    stock_morning[s] = stock_by_saddle[s] + receipt_by_saddle.get(s, 0.0)
    stock_evening[s] = stock_morning[s] - actual_issue
    stock_by_saddle[s] = stock_evening[s]
```

**Probleme:**
1. **Simulator** summiert nur bis Vorjahr (31.12.)
2. **Materiallager** beginnt ab November und baut Bestand auf
3. **Potenzielle Inkonsistenz:** Wenn Materiallager am 01.01. einen anderen Bestand zeigt als Simulator

**Auswirkung:**
- Minimale Inkonsistenz (nur am Jahresanfang)
- Kann zu kleinen Differenzen führen

**Empfohlener Fix:**
- Beide sollten **gleiche Logik** verwenden
- Oder: Simulator sollte Initialbestand aus Materiallager lesen

---

## 🟢 NIEDRIG: Produktionsmengen-Rundungsfehler

### Problem 6.1: Actual_Build vs tatsächliche PM

**Beschreibung:**
- **Simulator** berechnet: `actual_build = sum(production_by_product.values())`
- **ProductionPlanner** speichert: `tatsächliche PM` pro Produkt
- **Potenzielle Inkonsistenz:** Rundungsfehler bei Summierung

**Aktuelle Logik:**

**Simulator (Zeile 332):**
```python
production_by_product = self.production_planner.plan_daily_production(...)
actual_build = sum(production_by_product.values())  # Summe aller Produkte
```

**ProductionPlanner (Zeile 494):**
```python
'tatsächliche PM': int(round(actual_qty)),  # Pro Produkt
```

**Problem:**
- Wenn `sum(tatsächliche PM)` != `Actual_Build`, entstehen Inkonsistenzen
- Rundungsfehler können sich summieren

**Auswirkung:**
- Minimale Inkonsistenzen (nur durch Rundungsfehler)
- Kann zu kleinen Differenzen in Summen führen

**Empfohlener Fix:**
- `Actual_Build` sollte aus `sum(tatsächliche PM)` berechnet werden (nicht umgekehrt)
- Oder: Beide sollten aus gleicher Quelle kommen

---

## 📋 Zusammenfassung: Alle gefundenen Inkonsistenzen

### 🔴 KRITISCH (Sofort beheben)

1. **Transport/Versand:** Supplier-Log vs Inbound-Log unterschiedliche Versandmengen
   - **Fix:** Vereinfachte Bestandslogik in Supplier-Log
   - **Oder:** Bestandsbegrenzung auch in Inbound-Log

### 🟡 MITTEL (Sollte behoben werden)

2. **Materialbestände:** Mehrfachberechnung an drei Stellen
   - **Fix:** Single Source of Truth (Materiallager-Berechnung)
   - ProductionPlanner und Simulator sollten aus Materiallager lesen

3. **Produktionsverteilung:** Proportional vs Exakt
   - **Fix:** Single Source of Truth (ProductionPlanner-Produktion)
   - Materiallager und Fertigproduktelager sollten aus `production_logs` lesen

4. **Backlog:** Zwei verschiedene Systeme
   - **Fix:** Klarstellung der Zwecke oder Konsolidierung

### 🟢 NIEDRIG (Kann später behoben werden)

5. **Initialbestände:** Zwei verschiedene Berechnungen
   - **Fix:** Gleiche Logik verwenden

6. **Produktionsmengen:** Rundungsfehler
   - **Fix:** Konsistente Berechnung

---

## 🎯 Empfohlene Architektur: Single Source of Truth

### Datenquellen-Hierarchie

```
1. VOLUMENPLANUNG (Single Source of Truth für Nachfrage)
   └─→ daily_demands_actual / daily_demands_planned
       └─→ Wird verwendet von: Simulator, ChinaTransportManager

2. PRODUKTION (Single Source of Truth für Produktion)
   └─→ production_logs (ProductionPlanner)
       └─→ Wird verwendet von: Materiallager, Fertigproduktelager, Reporting

3. TRANSPORT (Single Source of Truth für Transport)
   └─→ transport_status (ChinaTransportManager)
       └─→ Wird verwendet von: Supplier-Log, Inbound-Log, Materiallager

4. MATERIALBESTÄNDE (Single Source of Truth für Material)
   └─→ Materiallager-Berechnung (create_saddle_inventory_log)
       └─→ Wird verwendet von: ProductionPlanner, Reporting

5. BACKLOG (Single Source of Truth für Backlog)
   └─→ ProductionPlanner.backlog (Produktions-Backlog)
   └─→ MarketBacklog (Kunden-Backlog)
       └─→ Wird verwendet von: Reporting, Produktion
```

### Empfohlene Änderungen

1. **Materiallager als Single Source of Truth für Materialbestände**
   - ProductionPlanner liest Bestände aus Materiallager (nicht neu berechnen)
   - Simulator synchronisiert `inventory.stock_saddles` mit Materiallager

2. **ProductionPlanner als Single Source of Truth für Produktion**
   - Materiallager liest Produktion aus `production_logs` (nicht neu berechnen)
   - Fertigproduktelager liest Produktion aus `production_logs` (nicht proportional verteilen)

3. **transport_status als Single Source of Truth für Transport**
   - Supplier-Log und Inbound-Log lesen aus `transport_status` (nicht neu berechnen)
   - Beide wenden Szenarien konsistent an

4. **Konsistente Szenarien-Anwendung**
   - Szenarien werden zentral in `process_shipments()` angewendet
   - Tabellen lesen `actual_quantity` aus `transport_status` (nicht neu berechnen)

---

## 🔧 Nächste Schritte

### Phase 1: Kritische Fixes (Sofort)

1. ✅ Warenbestand-Problem beheben (vereinfachte Bestandslogik)
2. ⏳ Materiallager als Single Source of Truth etablieren
3. ⏳ ProductionPlanner-Produktion als Single Source of Truth etablieren

### Phase 2: Konsistenz-Verbesserungen (Mittel)

4. ⏳ Transport-Status als Single Source of Truth etablieren
5. ⏳ Szenarien konsistent anwenden
6. ⏳ Backlog-Systeme klarstellen

### Phase 3: Optimierungen (Niedrig)

7. ⏳ Initialbestände konsistent berechnen
8. ⏳ Rundungsfehler minimieren

---

## 📊 Priorisierung

**Höchste Priorität:**
- 🔴 Transport/Versand-Inkonsistenz (bereits identifiziert)
- 🟡 Materialbestands-Mehrfachberechnung
- 🟡 Produktionsverteilung-Inkonsistenz

**Mittlere Priorität:**
- 🟡 Backlog-Systeme klarstellen
- 🟢 Initialbestände konsistent berechnen

**Niedrige Priorität:**
- 🟢 Rundungsfehler minimieren
