# Vollständige Liste aller Fallbacks

## Zusammenfassung

**Gesamtanzahl Fallbacks, die entfernt werden können: 7**

---

## 1. Fallbacks für `daily_demands_actual` (Nachfrageberechnung)

### ✅ Fallback #1: `simulation/simulator.py` (Zeile 294-300)

**Datei:** `simulation/simulator.py`  
**Zeile:** 294-300  
**Kontext:** Innerhalb `simulator.run()` Loop

```python
if day in daily_demands_actual and daily_demands_actual[day]:
    product_demands = daily_demands_actual[day].copy()
else:
    # Fallback: Berechne Nachfrage selbst (wenn Volumenplanung noch nicht ausgeführt wurde)
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
        day, 
        marketing_add_ons,
        is_last_workday_of_year
    )
```

**Problem:**
- Fallback wird praktisch nie erreicht (Cache ist immer vorhanden)
- Fallback kann inkonsistente Werte produzieren (Marketing-Add-ons)

**Empfehlung:** Entfernen, Exception werfen

---

### ✅ Fallback #2: `simulation/simulator.py` (Zeile 301-307)

**Datei:** `simulation/simulator.py`  
**Zeile:** 301-307  
**Kontext:** Exception-Handler innerhalb `simulator.run()` Loop

```python
except Exception:
    # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar oder Fehler)
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
        day, 
        marketing_add_ons,
        is_last_workday_of_year
    )
```

**Problem:**
- Exception sollte weitergegeben werden, nicht verschluckt
- Fallback kann inkonsistente Werte produzieren

**Empfehlung:** Exception weitergeben, nicht verschlucken

---

### ✅ Fallback #3: `simulation/simulator.py` (Zeile 308-314)

**Datei:** `simulation/simulator.py`  
**Zeile:** 308-314  
**Kontext:** Wenn Streamlit nicht verfügbar (`STREAMLIT_AVAILABLE = False`)

```python
else:
    # Fallback: Berechne Nachfrage selbst (wenn Streamlit nicht verfügbar)
    product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
        day, 
        marketing_add_ons,
        is_last_workday_of_year
    )
```

**Problem:**
- App läuft nur in Streamlit-Umgebung
- Fallback wird praktisch nie erreicht

**Empfehlung:** Entfernen (nur für Unit-Tests relevant, dann sollte Exception geworfen werden)

---

### ✅ Fallback #4: `simulation/production_planner.py` (Zeile 100-102)

**Datei:** `simulation/production_planner.py`  
**Zeile:** 100-102  
**Kontext:** Innerhalb `plan_daily_production()`

```python
product_demands = self.demand_calculator.calculate_daily_demand_per_product_dict(
    day, marketing_add_ons, is_last_workday_of_year
)
```

**Problem:**
- **Berechnet IMMER Nachfrage neu, auch wenn Cache vorhanden ist!**
- **Keine Prüfung auf Cache!**
- **Definitiv eine Redundanz!**

**Empfehlung:** Umstellen auf Cache-Lesen (aus `daily_demands_actual`)

---

### ✅ Fallback #5: `pages/5_materiallager.py` (Zeile 196-231)

**Datei:** `pages/5_materiallager.py`  
**Zeile:** 196-231  
**Kontext:** Innerhalb `create_saddle_inventory_log()`

```python
if day in daily_demands_actual:
    product_demands = daily_demands_actual[day]
else:
    # Fallback: Berechne Marketing-Add-ons manuell (wie vorher)
    marketing_add_ons = {}
    # ... manuelle Berechnung ...
    product_demands = demand_calc.calculate_daily_demand_per_product_dict(
        day, marketing_add_ons, is_last_workday_of_year
    )
```

**Problem:**
- Fallback wird praktisch nie erreicht (Cache ist immer vorhanden)
- Fallback berechnet Marketing-Add-ons manuell, möglicherweise inkonsistent

**Empfehlung:** Entfernen, Exception werfen

---

### ✅ Fallback #6: `pages/5_materiallager.py` (Zeile 232-240)

**Datei:** `pages/5_materiallager.py`  
**Zeile:** 232-240  
**Kontext:** Innerhalb `create_saddle_inventory_log()`, wenn `demand_calculator` nicht verfügbar

```python
else:
    # Fallback: Verwende PRODUCT_SALES_SHARES (alte Logik)
    total_share = sum(MasterData.PRODUCT_SALES_SHARES.values())
    for product in MasterData.BOM.keys():
        if total_share > 0:
            share = MasterData.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share
            product_demands[product] = int(actual_build * share) if actual_build > 0 else 0
        else:
            product_demands[product] = 0
```

**Problem:**
- `demand_calculator` sollte immer verfügbar sein (wird in `run_happy_path_simulation()` erstellt)
- Fallback verwendet veraltete Logik (ignoriert Marketing)

**Empfehlung:** Entfernen, Exception werfen

---

## 2. Fallbacks für `production_logs_cache` (Produktionsberechnung)

### ✅ Fallback #7: `pages/5_materiallager.py` (Zeile 291-293)

**Datei:** `pages/5_materiallager.py`  
**Zeile:** 291-293  
**Kontext:** Innerhalb `create_saddle_inventory_log()`

```python
if 'production_logs_cache' in st.session_state:
    # ... Lese aus Cache ...
else:
    # Fallback: Verwende production_by_product (alte Logik)
    production_by_product_from_logs = production_by_product
```

**Problem:**
- `production_logs_cache` sollte immer vorhanden sein (wird in `pages/6_produktion.py` erstellt)
- Fallback verwendet `production_by_product`, der möglicherweise falsche Werte enthält

**Empfehlung:** Entfernen, Exception werfen (oder zirkuläre Abhängigkeit auflösen)

---

## 3. Andere Fallbacks (NICHT entfernen - berechtigt)

### ⚠️ Fallback #8: `simulation/production_planner.py` (Zeile 103-109)

**Datei:** `simulation/production_planner.py`  
**Zeile:** 103-109  
**Kontext:** Innerhalb `plan_daily_production()`, wenn `demand_calculator` nicht verfügbar

```python
else:
    # Fallback
    total_share = sum(self.master_data.PRODUCT_SALES_SHARES.values())
    estimated_daily_target = self.master_data.GLOBAL_CONFIG.get('total_volume', 370000) / 365
    for product in self.master_data.BOM.keys():
        share = self.master_data.PRODUCT_SALES_SHARES.get(product, 0.0) / total_share if total_share > 0 else 0
        product_demands[product] = int(estimated_daily_target * share)
```

**Status:** ⚠️ **Berechtigt** (für Unit-Tests ohne vollständige Initialisierung)

**Empfehlung:** Behalten, aber dokumentieren

---

### ⚠️ Fallback #9: `simulation/production_planner.py` (Zeile 430-434)

**Datei:** `simulation/production_planner.py`  
**Zeile:** 430-434  
**Kontext:** Innerhalb `_log_production()`, wenn `finished_pm_by_product` nicht übergeben wurde

```python
# Falls nicht übergeben, berechne es hier (Fallback)
if finished_pm_by_product is None:
    finished_pm_by_product = {}
    for product in self.master_data.BOM.keys():
        finished_pm_by_product[product] = 0
```

**Status:** ⚠️ **Berechtigt** (für Rückwärtskompatibilität)

**Empfehlung:** Behalten, aber dokumentieren

---

### ⚠️ Fallback #10: `simulation/production_planner.py` (Zeile 463-472)

**Datei:** `simulation/production_planner.py`  
**Zeile:** 463-472  
**Kontext:** Innerhalb `_log_production()`, wenn Inbound-Tabelle nicht verfügbar

```python
# Fallback: Wenn Inbound-Tabelle nicht verfügbar, verwende proportionale Aufteilung
if stock_saddle_specific is None:
    if stock_saddles_morning is None:
        stock_saddles_morning = 0.0
        for p in self.master_data.BOM.keys():
            if p in material_availability_by_product:
                stock_saddles_morning = material_availability_by_product[p]
                break
    saddle_share = saddle_shares.get(saddle_name, 0.0)
    stock_saddle_specific = stock_saddles_morning * saddle_share
```

**Status:** ⚠️ **Berechtigt** (für Edge-Cases, wenn Inbound-Tabelle leer ist)

**Empfehlung:** Behalten, aber dokumentieren

---

### ⚠️ Fallback #11: `simulation/china_transport.py` (Zeile 543-544)

**Datei:** `simulation/china_transport.py`  
**Zeile:** 543-544  
**Kontext:** Innerhalb `get_supplier_log_dataframe()`, wenn Streamlit nicht verfügbar

```python
except (ImportError, AttributeError):
    # Fallback: Wenn Streamlit nicht verfügbar, verwende einfachen Key
    cache_key = (saddle_name, saddle_share)
```

**Status:** ⚠️ **Berechtigt** (für Unit-Tests ohne Streamlit)

**Empfehlung:** Behalten, aber dokumentieren

---

### ⚠️ Fallback #12: `simulation/china_transport.py` (Zeile 934-935)

**Datei:** `simulation/china_transport.py`  
**Zeile:** 934-935  
**Kontext:** Innerhalb `get_inbound_log_dataframe()`, wenn Streamlit nicht verfügbar

```python
except (ImportError, AttributeError):
    # Fallback: Wenn Streamlit nicht verfügbar, verwende einfachen Key
    cache_key = tuple(sorted(saddle_shares_dict.items()))
```

**Status:** ⚠️ **Berechtigt** (für Unit-Tests ohne Streamlit)

**Empfehlung:** Behalten, aber dokumentieren

---

## Zusammenfassung

### ✅ Fallbacks, die entfernt werden können: **7**

| # | Datei | Zeile | Typ | Problem |
|---|-------|-------|-----|---------|
| 1 | `simulation/simulator.py` | 294-300 | `daily_demands_actual` | Fallback wird nie erreicht |
| 2 | `simulation/simulator.py` | 301-307 | `daily_demands_actual` | Exception wird verschluckt |
| 3 | `simulation/simulator.py` | 308-314 | `daily_demands_actual` | Streamlit immer verfügbar |
| 4 | `simulation/production_planner.py` | 100-102 | `daily_demands_actual` | Berechnet IMMER neu (Redundanz!) |
| 5 | `pages/5_materiallager.py` | 196-231 | `daily_demands_actual` | Fallback wird nie erreicht |
| 6 | `pages/5_materiallager.py` | 232-240 | `daily_demands_actual` | `demand_calculator` immer verfügbar |
| 7 | `pages/5_materiallager.py` | 291-293 | `production_logs_cache` | Fallback wird nie erreicht |

### ⚠️ Fallbacks, die beibehalten werden sollten: **5**

| # | Datei | Zeile | Typ | Grund |
|---|-------|-------|-----|-------|
| 8 | `simulation/production_planner.py` | 103-109 | `demand_calculator` | Für Unit-Tests |
| 9 | `simulation/production_planner.py` | 430-434 | `finished_pm_by_product` | Rückwärtskompatibilität |
| 10 | `simulation/production_planner.py` | 463-472 | Inbound-Tabelle | Edge-Cases |
| 11 | `simulation/china_transport.py` | 543-544 | Streamlit | Für Unit-Tests |
| 12 | `simulation/china_transport.py` | 934-935 | Streamlit | Für Unit-Tests |

---

## Empfohlene Vorgehensweise

### Schritt 1: Fallbacks für `daily_demands_actual` entfernen (6 Fallbacks)

1. **`simulation/simulator.py` (3 Fallbacks):**
   - Zeile 294-300: Entfernen, Exception werfen
   - Zeile 301-307: Exception weitergeben, nicht verschlucken
   - Zeile 308-314: Entfernen (nur für Unit-Tests relevant)

2. **`simulation/production_planner.py` (1 Fallback):**
   - Zeile 100-102: Umstellen auf Cache-Lesen (aus `daily_demands_actual`)

3. **`pages/5_materiallager.py` (2 Fallbacks):**
   - Zeile 196-231: Entfernen, Exception werfen
   - Zeile 232-240: Entfernen, Exception werfen

### Schritt 2: Fallback für `production_logs_cache` entfernen (1 Fallback)

1. **`pages/5_materiallager.py` (1 Fallback):**
   - Zeile 291-293: Entfernen, Exception werfen (oder zirkuläre Abhängigkeit auflösen)

---

## Erwartete Verbesserungen

1. **Konsistenz:** Alle Stellen verwenden dieselbe Quelle (SSoT)
2. **Einfachheit:** Keine redundanten Berechnungen
3. **Fehlererkennung:** Fehlende Cache wird sofort erkannt (Exception)
4. **Wartbarkeit:** Weniger Code, weniger Fehlerquellen
5. **Performance:** Keine unnötigen Neuberechnungen

---

## Risiken

1. **Unit-Tests:** Müssen angepasst werden (müssen `daily_demands_actual` initialisieren)
2. **Zirkuläre Abhängigkeit:** `production_logs_cache` Fallback muss aufgelöst werden
3. **Exception-Handling:** Muss korrekt implementiert werden

---

## Nächste Schritte

1. ✅ Fallbacks identifiziert (7 Fallbacks)
2. ⏳ Fallbacks entfernen (Code-Änderungen)
3. ⏳ Unit-Tests anpassen
4. ⏳ Zirkuläre Abhängigkeit auflösen
5. ⏳ Exception-Handling implementieren
