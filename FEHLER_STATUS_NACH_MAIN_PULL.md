# Fehler-Status nach Main-Pull

**Datum:** 27.01.2026  
**Status:** Prüfung nach Main-Pull

---

## ✅ Was wurde bereits behoben (vermutlich)

Nach dem Pull von `main` sollten folgende Fixes enthalten sein:
- Optimierte Produktion (Commit `b2cd290`)
- Verbesserte Material-Berechnungen
- Inbound-Mengen-Korrektur

---

## ❌ Was NOCH NICHT behoben ist

### 🔴 KRITISCH: FEHLER-003 - Nicht-deterministische Produktreihenfolge

**Status:** ❌ **NOCH NICHT BEHOBEN**

**Betroffene Stellen:**

1. **`ui/production_calculations.py` Zeile 104:**
   ```python
   for product in MasterData.BOM.keys():  # ❌ NICHT SORTIERT
   ```

2. **`ui/production_calculations.py` Zeile 111:**
   ```python
   for product in MasterData.BOM.keys():  # ❌ NICHT SORTIERT
   ```

3. **`ui/production_calculations.py` Zeile 119:**
   ```python
   products_list = list(MasterData.BOM.keys())  # ❌ NICHT SORTIERT
   ```

4. **`ui/production_calculations.py` Zeile 423:**
   ```python
   current_backlog = {p: 0.0 for p in MasterData.BOM.keys()}  # ❌ NICHT SORTIERT
   ```

5. **`simulation/production_planner.py` Zeile 180:**
   ```python
   products_list = list(self.master_data.BOM.keys())  # ❌ NICHT SORTIERT
   ```

**Problem:**
- Rang-Berechnung hängt von `idx` ab (Zeile 195 in `production_planner.py`: `row_number = idx + 1`)
- Wenn `products_list` unterschiedliche Reihenfolge hat, bekommen Produkte unterschiedliche Ränge
- Dies führt zu unterschiedlichen Produktionsmengen bei Neuladen

**Auswirkung:**
- MTB Extreme kann 1799 oder 1760 haben (je nach Reihenfolge)
- Nicht-deterministische Ergebnisse

**Lösung:**
```python
# Statt:
products_list = list(MasterData.BOM.keys())

# Sollte sein:
products_list = sorted(MasterData.BOM.keys())
```

---

### 🔴 KRITISCH: FEHLER-004 - Kein Konvergenz-Check

**Status:** ❌ **NOCH NICHT BEHOBEN**

**Betroffene Stelle:**
- `ui/page_initialization.py` Zeile 39-63

**Problem:**
- Genau 2 Iterationen werden durchgeführt
- Kein Check ob `production_logs_cache` sich zwischen Iterationen ändert
- Werte könnten oszillieren

**Aktueller Code:**
```python
# ITERATION 1
calculate_production_logs()
calculate_material_inventory()

# ITERATION 2
calculate_production_logs()
calculate_material_inventory()
# ❌ KEIN CHECK OB WERTE KONVERGIERT SIND
```

**Lösung:**
```python
max_iterations = 5
for iteration in range(max_iterations):
    old_cache = copy.deepcopy(st.session_state.get('production_logs_cache'))
    calculate_production_logs()
    calculate_material_inventory()
    new_cache = st.session_state.get('production_logs_cache')
    
    # Prüfe Konvergenz
    if old_cache == new_cache:
        break  # Konvergiert!
```

---

### 🔴 KRITISCH: FEHLER-001 - Parameter-Inkonsistenz

**Status:** ❌ **NOCH NICHT BEHOBEN**

**Betroffene Stelle:**
- `pages/8_stammdaten.py` Zeile 210

**Problem:**
- Wenn `editable_global_config['total_volume']` geändert wird, wird `yearly_volume` NICHT aktualisiert
- Cache wird NICHT invalidiert

**Aktueller Code:**
```python
if new_value != value:
    st.session_state.editable_global_config[key] = new_value
    config_changed = True
    # ❌ yearly_volume wird NICHT aktualisiert
    # ❌ Cache wird NICHT invalidiert
```

**Lösung:**
```python
if new_value != value:
    st.session_state.editable_global_config[key] = new_value
    config_changed = True
    
    # Synchronisiere yearly_volume
    if key == 'total_volume':
        st.session_state.yearly_volume = new_value
        
        # Invalidiere Cache
        st.session_state.volume_planning_calculated = False
        if 'production_logs_cache' in st.session_state:
            del st.session_state.production_logs_cache
        if 'material_inventory_data' in st.session_state:
            del st.session_state.material_inventory_data
```

---

### 🔴 KRITISCH: FEHLER-002 - Cache-Invalidierung

**Status:** ❌ **NOCH NICHT BEHOBEN**

**Betroffene Stelle:**
- `pages/8_stammdaten.py` Zeile 229-231

**Problem:**
- Wenn Parameter geändert werden, wird Cache nicht invalidiert
- Änderungen haben keine sofortige Auswirkung

**Aktueller Code:**
```python
if config_changed:
    st.success("✅ Globale Konfiguration aktualisiert!")
    # ❌ KEINE CACHE-INVALIDIERUNG
```

---

## 📊 Zusammenfassung

### Behoben: ✅
- (Vermutlich) Optimierte Produktion
- (Vermutlich) Material-Berechnungen
- (Vermutlich) Inbound-Mengen

### Nicht behoben: ❌
1. **FEHLER-003:** Produktreihenfolge nicht stabilisiert (5 Stellen)
2. **FEHLER-004:** Kein Konvergenz-Check
3. **FEHLER-001:** Parameter-Synchronisation fehlt
4. **FEHLER-002:** Cache-Invalidierung fehlt

---

## 🎯 Test-Empfehlung

### Sofort testen:
1. **TEST-1.1:** Produktionswerte Determinismus
   - Erwartung: Werte sollten identisch sein
   - Realität: Werte werden wahrscheinlich variieren (FEHLER-003)

2. **TEST-2.1:** `total_volume` Änderung
   - Erwartung: Werte sollten sich ändern
   - Realität: Werte ändern sich NICHT (FEHLER-001, FEHLER-002)

### Nach Fixes testen:
3. Alle anderen Tests aus `TEST_ANLEITUNG_UI.md`

---

**Status:** ⚠️ **KRITISCHE FEHLER NOCH VORHANDEN**  
**Empfehlung:** Fixes implementieren bevor umfassende Tests durchgeführt werden
