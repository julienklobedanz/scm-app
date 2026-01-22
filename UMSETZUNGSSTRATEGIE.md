# Umsetzungsstrategie: Optimale Datenfluss-Architektur

**Datum:** 2026-01-22  
**Ziel:** Schrittweise Umsetzung der Single Source of Truth Architektur

---

## 🎯 Strategie-Übersicht

### **Prinzipien:**

1. **Schrittweise Migration:** Eine Komponente nach der anderen
2. **Fallback-Mechanismen:** Alte Logik bleibt als Fallback erhalten
3. **Validierung:** Nach jeder Änderung Vergleich mit alter Logik
4. **Rückwärtskompatibilität:** Bestehende Funktionalität bleibt erhalten
5. **Testbarkeit:** Jede Änderung kann isoliert getestet werden

---

## 📋 Umsetzungsplan (3 Phasen)

### **Phase 1: ProductionPlanner als SSoT für Produktion** 🔴 HOCH

**Ziel:** Materiallager und Fertigproduktelager lesen Produktion aus `production_logs`

**Betroffene Dateien:**
- `pages/5_materiallager.py` (Lagerabgang)
- `pages/7_fertigproduktelager.py` (Lagerzugang)

**Vorteile:**
- ✅ Konsistenz: Alle Seiten zeigen gleiche Produktionsmengen
- ✅ Szenarien-ready: Marketing wird automatisch berücksichtigt
- ✅ Performance: Keine Neuberechnung

---

### **Phase 2: transport_status als SSoT für Transport** 🟡 MITTEL

**Ziel:** Supplier-Log und Inbound-Log lesen Versandmengen aus `transport_status`

**Betroffene Dateien:**
- `simulation/china_transport.py` (`get_supplier_log_dataframe`, `get_inbound_log_dataframe`)

**Vorteile:**
- ✅ Konsistenz: Beide Tabellen zeigen gleiche Versandmengen
- ✅ Szenarien-ready: Lieferprobleme werden automatisch berücksichtigt

---

### **Phase 3: Materiallager als SSoT für Materialbestände** 🟢 NIEDRIG

**Ziel:** ProductionPlanner liest Bestände aus Materiallager

**Betroffene Dateien:**
- `simulation/production_planner.py` (`_get_all_stocks_from_inbound_table`)

**Vorteile:**
- ✅ Konsistenz: Alle Komponenten sehen gleiche Bestände
- ✅ Szenarien-ready: Wasserschaden wird automatisch berücksichtigt

---

## 🔧 Phase 1: Detaillierte Umsetzung

### **Schritt 1.1: Materiallager - Lagerabgang aus production_logs**

**Datei:** `pages/5_materiallager.py`  
**Methode:** `create_saddle_inventory_log()`  
**Zeilen:** 152-239 (aktuell: Neuberechnung)

#### **Aktuelle Logik (Zeilen 152-239):**

```python
# Verbrauch (Produktion DE) - Exakte Stücklisten-Logik
if 0 <= day < len(results_df):
    actual_build = results_df.iloc[day]['Actual_Build']
    
    # NEUE (exakte) Logik: Rekonstruiere Produktionsmengen pro Produkt
    # Wir nutzen den DemandCalculator des Simulators, um die Nachfrage pro Produkt zu erhalten
    # und verteilen dann die tatsächliche Produktion proportional
    product_demands = {}
    if st.session_state.simulator and hasattr(st.session_state.simulator, 'demand_calculator'):
        demand_calc = st.session_state.simulator.demand_calculator
        # ... komplexe Neuberechnung mit Marketing-Add-ons ...
        product_demands = demand_calc.calculate_daily_demand_per_product_dict(...)
    
    # Verteile die tatsächliche Produktion proportional zur Nachfrage
    production_by_product = {...}  # Neu berechnet
    
    # Für jedes produzierte Produkt den entsprechenden Sattel aus der BOM abziehen
    for product_name, qty in production_by_product.items():
        if qty > 0 and product_name in MasterData.BOM:
            required_saddle = MasterData.BOM[product_name]['saddle']
            issue_by_saddle[required_saddle] += qty
```

#### **Neue Logik (aus production_logs lesen):**

```python
# Verbrauch (Produktion DE) - Aus production_logs lesen (Single Source of Truth)
production_by_product = {}
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    if hasattr(planner, 'production_logs') and planner.production_logs:
        # Liest aus production_logs (bereits berechnet, mit Marketing!)
        for product in MasterData.BOM.keys():
            if product in planner.production_logs:
                # Finde Log-Eintrag für diesen Tag
                log_entry = None
                for entry in planner.production_logs[product]:
                    entry_date_str = entry.get('Datum', '')
                    if entry_date_str:
                        try:
                            from datetime import datetime
                            entry_date = datetime.strptime(entry_date_str, MasterData.DATE_FORMAT).date()
                            if entry_date == current_date:
                                log_entry = entry
                                break
                        except (ValueError, TypeError):
                            continue
                
                if log_entry:
                    production_by_product[product] = log_entry.get('tatsächliche PM', 0)
                else:
                    production_by_product[product] = 0
            else:
                production_by_product[product] = 0
    else:
        # FALLBACK: Alte Logik (wenn production_logs nicht verfügbar)
        # ... alte Logik hier ...
        pass
else:
    # FALLBACK: Kein Simulator verfügbar
    production_by_product = {product: 0 for product in MasterData.BOM.keys()}

# Für jedes produzierte Produkt den entsprechenden Sattel aus der BOM abziehen
for product_name, qty in production_by_product.items():
    if qty > 0 and product_name in MasterData.BOM:
        required_saddle = MasterData.BOM[product_name]['saddle']
        issue_by_saddle[required_saddle] += qty
```

#### **Optimierung: Tag-Index statt Datum-Vergleich**

**Problem:** Datum-Vergleich ist langsam (365 Iterationen pro Tag)

**Lösung:** Direkter Zugriff über Tag-Index

```python
# OPTIMIERUNG: Direkter Zugriff über Tag-Index (schneller)
production_by_product = {}
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    if hasattr(planner, 'production_logs') and planner.production_logs:
        # production_logs ist als Liste organisiert: [log_entry_day_0, log_entry_day_1, ...]
        # WICHTIG: production_logs wird nur an Arbeitstagen gefüllt!
        # Daher müssen wir den Tag-Index finden, der diesem Datum entspricht
        
        # Finde Tag-Index für current_date
        day_index = None
        for d in range(365):
            if workday_calc.get_date_from_day(d) == current_date:
                day_index = d
                break
        
        if day_index is not None:
            # Zähle Arbeitstage bis zu diesem Tag (production_logs-Index)
            workday_count = 0
            for d in range(day_index + 1):
                if workday_calc.is_workday(d):
                    workday_count += 1
            
            # production_logs-Index = workday_count - 1 (0-basiert)
            log_index = workday_count - 1
            
            for product in MasterData.BOM.keys():
                if product in planner.production_logs:
                    logs = planner.production_logs[product]
                    if 0 <= log_index < len(logs):
                        log_entry = logs[log_index]
                        production_by_product[product] = log_entry.get('tatsächliche PM', 0)
                    else:
                        production_by_product[product] = 0
                else:
                    production_by_product[product] = 0
        else:
            # Datum nicht gefunden
            production_by_product = {product: 0 for product in MasterData.BOM.keys()}
    else:
        # FALLBACK: Alte Logik
        # ... alte Logik hier ...
        pass
else:
    # FALLBACK: Kein Simulator verfügbar
    production_by_product = {product: 0 for product in MasterData.BOM.keys()}
```

#### **Noch bessere Lösung: Helper-Funktion**

**Problem:** Tag-Index-Berechnung ist komplex und wird mehrfach benötigt

**Lösung:** Helper-Funktion erstellen

```python
def get_production_from_logs(day: int, current_date: date, planner, workday_calc) -> Dict[str, int]:
    """
    Liest Produktionsmengen aus production_logs für einen bestimmten Tag.
    
    Args:
        day: Tag-Index (0-basiert)
        current_date: Datum
        planner: ProductionPlanner-Instanz
        workday_calc: WorkdayCalculator-Instanz
    
    Returns:
        Dictionary: {product: production_qty}
    """
    production_by_product = {}
    
    if not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {product: 0 for product in MasterData.BOM.keys()}
    
    # Zähle Arbeitstage bis zu diesem Tag (production_logs-Index)
    workday_count = 0
    for d in range(day + 1):
        if workday_calc.is_workday(d):
            workday_count += 1
    
    # production_logs-Index = workday_count - 1 (0-basiert)
    log_index = workday_count - 1
    
    for product in MasterData.BOM.keys():
        if product in planner.production_logs:
            logs = planner.production_logs[product]
            if 0 <= log_index < len(logs):
                log_entry = logs[log_index]
                production_by_product[product] = log_entry.get('tatsächliche PM', 0)
            else:
                production_by_product[product] = 0
        else:
            production_by_product[product] = 0
    
    return production_by_product

# Verwendung:
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    production_by_product = get_production_from_logs(day, current_date, planner, workday_calc)
else:
    # FALLBACK: Alte Logik
    production_by_product = {product: 0 for product in MasterData.BOM.keys()}
```

---

### **Schritt 1.2: Fertigproduktelager - Lagerzugang aus production_logs**

**Datei:** `pages/7_fertigproduktelager.py`  
**Methode:** `create_finished_goods_log()`  
**Zeilen:** 78-84 (aktuell: Proportional)

#### **Aktuelle Logik (Zeilen 78-84):**

```python
# Produktion und Versand
actual_build = results_df.iloc[day]['Actual_Build']

# Für jedes Produkt
for product in MasterData.BOM.keys():
    product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
    production_qty = actual_build * product_share  # Proportional verteilt
```

#### **Neue Logik (aus production_logs lesen):**

```python
# Produktion und Versand - Aus production_logs lesen (Single Source of Truth)
def get_production_from_logs(day: int, current_date: date, planner, workday_calc) -> Dict[str, int]:
    """Helper-Funktion (wie oben)"""
    # ... (siehe oben) ...

# Für jedes Produkt
if 'simulator' in st.session_state and st.session_state.simulator:
    planner = st.session_state.simulator.production_planner
    production_by_product = get_production_from_logs(day, current_date, planner, workday_calc)
else:
    # FALLBACK: Proportional (wenn production_logs nicht verfügbar)
    actual_build = results_df.iloc[day]['Actual_Build']
    production_by_product = {}
    for product in MasterData.BOM.keys():
        product_share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0)
        production_by_product[product] = int(round(actual_build * product_share))

for product in MasterData.BOM.keys():
    production_qty = production_by_product.get(product, 0)
    
    # Aggregiere über alle Länder
    total_receipt = 0
    total_dispatch = 0
    
    for market_code, market_params in MasterData.MARKETS.items():
        market_share = market_params['share']
        receipt = production_qty * market_share
        dispatch = receipt  # Sofort versendet (Just-in-Time)
        total_receipt += receipt
        total_dispatch += dispatch
```

---

## 🧪 Teststrategie

### **Schritt 1: Validierung vor Änderung**

**Ziel:** Vergleich alte vs. neue Logik

```python
# In create_saddle_inventory_log() oder create_finished_goods_log()
# TEMPORÄR: Berechne beide Varianten und vergleiche

# Alte Logik
production_by_product_old = {...}  # Alte Berechnung

# Neue Logik
production_by_product_new = get_production_from_logs(...)

# Vergleich
if production_by_product_old != production_by_product_new:
    # Logge Unterschiede (für Debugging)
    st.warning(f"⚠️ Unterschiede gefunden für Tag {day}:")
    for product in MasterData.BOM.keys():
        old_qty = production_by_product_old.get(product, 0)
        new_qty = production_by_product_new.get(product, 0)
        if old_qty != new_qty:
            st.write(f"  {product}: Alt={old_qty}, Neu={new_qty}")
```

### **Schritt 2: Stufenweise Aktivierung**

**Ziel:** Neue Logik schrittweise aktivieren

```python
# Feature-Flag in Session State
USE_PRODUCTION_LOGS = st.session_state.get('use_production_logs', False)

if USE_PRODUCTION_LOGS:
    # Neue Logik
    production_by_product = get_production_from_logs(...)
else:
    # Alte Logik
    production_by_product = {...}  # Alte Berechnung
```

**Aktivierung:**
1. **Test:** Feature-Flag aktivieren, beide Varianten berechnen, vergleichen
2. **Validierung:** Manuelle Prüfung der Ergebnisse
3. **Produktion:** Feature-Flag dauerhaft aktivieren, alte Logik entfernen

---

## 🔍 Validierungs-Checkliste

### **Nach jeder Änderung prüfen:**

1. **Konsistenz:**
   - ✅ Materiallager zeigt gleiche Produktionsmengen wie Produktion-Seite
   - ✅ Fertigproduktelager zeigt gleiche Produktionsmengen wie Produktion-Seite
   - ✅ Summen stimmen überein (Materiallager: Summe aller Produkte = Actual_Build)

2. **Szenarien:**
   - ✅ Marketingaktion wird in Materiallager berücksichtigt
   - ✅ Marketingaktion wird in Fertigproduktelager berücksichtigt

3. **Performance:**
   - ✅ Seiten laden schnell (keine Performance-Regression)
   - ✅ Keine Timeouts

4. **Fehlerbehandlung:**
   - ✅ Fallback funktioniert (wenn production_logs nicht verfügbar)
   - ✅ Keine Crashes bei fehlenden Daten

---

## 📝 Konkrete Umsetzungsschritte

### **Phase 1.1: Materiallager (Lagerabgang)**

1. **Helper-Funktion erstellen:**
   - `get_production_from_logs()` in `pages/5_materiallager.py`

2. **Alte Logik als Fallback behalten:**
   - Kommentar: `# FALLBACK: Alte Logik (wenn production_logs nicht verfügbar)`
   - Code bleibt erhalten (für Rückfall)

3. **Neue Logik implementieren:**
   - Ersetze Zeilen 152-239 durch neuen Code
   - Verwende Helper-Funktion

4. **Testen:**
   - Feature-Flag aktivieren
   - Vergleich alte vs. neue Logik
   - Manuelle Validierung

5. **Aktivieren:**
   - Feature-Flag dauerhaft aktivieren
   - Alte Logik entfernen (nach erfolgreicher Validierung)

---

### **Phase 1.2: Fertigproduktelager (Lagerzugang)**

1. **Helper-Funktion wiederverwenden:**
   - Importiere `get_production_from_logs()` aus `pages/5_materiallager.py`
   - Oder: Erstelle gemeinsame Helper-Funktion in `ui/utils.py`

2. **Alte Logik als Fallback behalten:**
   - Kommentar: `# FALLBACK: Proportional (wenn production_logs nicht verfügbar)`
   - Code bleibt erhalten

3. **Neue Logik implementieren:**
   - Ersetze Zeilen 78-84 durch neuen Code
   - Verwende Helper-Funktion

4. **Testen:**
   - Feature-Flag aktivieren
   - Vergleich alte vs. neue Logik
   - Manuelle Validierung

5. **Aktivieren:**
   - Feature-Flag dauerhaft aktivieren
   - Alte Logik entfernen

---

## 🚨 Risiken und Mitigation

### **Risiko 1: production_logs nicht verfügbar**

**Problem:** Wenn Simulator nicht gelaufen ist, sind `production_logs` leer

**Mitigation:**
- ✅ Fallback auf alte Logik
- ✅ Warnung anzeigen: "Simulator nicht verfügbar, verwende Fallback"

### **Risiko 2: Tag-Index-Berechnung falsch**

**Problem:** `production_logs` wird nur an Arbeitstagen gefüllt, Tag-Index-Berechnung könnte falsch sein

**Mitigation:**
- ✅ Validierung: Vergleich mit alter Logik
- ✅ Debug-Logging: Zeige berechneten Tag-Index
- ✅ Test mit verschiedenen Tagen (Wochenende, Feiertage)

### **Risiko 3: Performance-Regression**

**Problem:** Neue Logik könnte langsamer sein

**Mitigation:**
- ✅ Optimierung: Direkter Zugriff über Tag-Index (statt Datum-Vergleich)
- ✅ Caching: Helper-Funktion cacht Ergebnisse
- ✅ Performance-Test: Vergleich alte vs. neue Logik

### **Risiko 4: Inkonsistenzen bei Rundung**

**Problem:** Alte Logik verwendet andere Rundung als neue Logik

**Mitigation:**
- ✅ Validierung: Vergleich Summen (sollten identisch sein)
- ✅ Toleranz: Kleine Unterschiede akzeptieren (< 1 Einheit)

---

## 🎯 Erfolgskriterien

### **Phase 1 erfolgreich, wenn:**

1. ✅ Materiallager zeigt gleiche Produktionsmengen wie Produktion-Seite
2. ✅ Fertigproduktelager zeigt gleiche Produktionsmengen wie Produktion-Seite
3. ✅ Marketingaktion wird automatisch berücksichtigt
4. ✅ Keine Performance-Regression
5. ✅ Fallback funktioniert (wenn production_logs nicht verfügbar)

---

## 📋 Nächste Schritte

### **Sofort starten:**

1. **Helper-Funktion erstellen:**
   - `get_production_from_logs()` in `ui/utils.py` (gemeinsam nutzbar)

2. **Phase 1.1 umsetzen:**
   - Materiallager auf `production_logs` umstellen
   - Mit Feature-Flag testen

3. **Validierung:**
   - Vergleich alte vs. neue Logik
   - Manuelle Prüfung

4. **Phase 1.2 umsetzen:**
   - Fertigproduktelager auf `production_logs` umstellen
   - Mit Feature-Flag testen

5. **Aktivierung:**
   - Feature-Flags dauerhaft aktivieren
   - Alte Logik entfernen

---

## 💡 Empfehlung: Gemeinsame Helper-Funktion

**Datei:** `ui/utils.py`

```python
def get_production_from_logs(
    day: int, 
    current_date: date, 
    planner, 
    workday_calc
) -> Dict[str, int]:
    """
    Liest Produktionsmengen aus production_logs für einen bestimmten Tag.
    
    Args:
        day: Tag-Index (0-basiert)
        current_date: Datum
        planner: ProductionPlanner-Instanz
        workday_calc: WorkdayCalculator-Instanz
    
    Returns:
        Dictionary: {product: production_qty}
    """
    from config.master_data import MasterData
    
    production_by_product = {}
    
    if not planner or not hasattr(planner, 'production_logs') or not planner.production_logs:
        return {product: 0 for product in MasterData.BOM.keys()}
    
    # Zähle Arbeitstage bis zu diesem Tag (production_logs-Index)
    workday_count = 0
    for d in range(day + 1):
        if workday_calc.is_workday(d):
            workday_count += 1
    
    # production_logs-Index = workday_count - 1 (0-basiert)
    log_index = workday_count - 1
    
    for product in MasterData.BOM.keys():
        if product in planner.production_logs:
            logs = planner.production_logs[product]
            if 0 <= log_index < len(logs):
                log_entry = logs[log_index]
                production_by_product[product] = log_entry.get('tatsächliche PM', 0)
            else:
                production_by_product[product] = 0
        else:
            production_by_product[product] = 0
    
    return production_by_product
```

**Vorteile:**
- ✅ Wiederverwendbar (Materiallager, Fertigproduktelager)
- ✅ Zentrale Wartung
- ✅ Einheitliche Logik

---

## ✅ Zusammenfassung

### **Umsetzungsstrategie:**

1. **Schrittweise Migration:** Eine Komponente nach der anderen
2. **Fallback-Mechanismen:** Alte Logik bleibt als Fallback
3. **Validierung:** Vergleich alte vs. neue Logik
4. **Feature-Flags:** Stufenweise Aktivierung
5. **Gemeinsame Helper-Funktion:** Wiederverwendbar, zentral gewartet

### **Nächste Schritte:**

1. Helper-Funktion erstellen (`ui/utils.py`)
2. Phase 1.1 umsetzen (Materiallager)
3. Validierung
4. Phase 1.2 umsetzen (Fertigproduktelager)
5. Aktivierung

**Ergebnis:**
- ✅ Konsistenz: Alle Seiten zeigen gleiche Produktionsmengen
- ✅ Szenarien-ready: Marketing wird automatisch berücksichtigt
- ✅ Performance: Keine Mehrfachberechnungen
