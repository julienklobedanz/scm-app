# Fehler-Status - Aktualisierte Analyse

**Datum:** 27.01.2026  
**Status:** Prüfung nach Hinweis des Kollegen

---

## ✅ Was der Kollege richtig sagt

### Neue Material ↔ Produktion Verbindung

**Status:** ✅ **TATSÄCHLICH NEstU IMPLEMENTIERT**

**Neue Logik in `ui/material_calculations.py`:**

1. **Source of Truth:** Nutzt jetzt `get_inbound_log_dataframe()` als einzige Quelle für Inbound-Daten
   ```python
   # Zeile 19-21: Kommentar dokumentiert neue Logik
   # WICHTIG: Nutzt jetzt die Inbound-Tabelle (`get_inbound_log_dataframe`) als Source of Truth
   # für den Wareneingang. Das garantiert, dass Materiallager und Produktion dieselben
   # (bereits berechneten) Ankunftsdaten und Mengen sehen – inkl. Vorlauf (z.B. Nov/Dez 2026).
   ```

2. **Materialverbrauch:** Liest aus `production_logs_cache` (Zeile 85-100)
   ```python
   # Zeile 105: Nutzt 'material_verbrauch' Spalte, Fallback auf 'tatsächliche PM'
   col_name = 'material_verbrauch' if 'material_verbrauch' in df.columns else 'tatsächliche PM'
   ```

3. **Konsistenz:** Garantiert dass Materiallager und Produktion dieselben Daten sehen

**Das ist tatsächlich eine Verbesserung!** ✅

---

## ❌ Was NOCH IMMER ein Problem ist

### 🔴 FEHLER-003: Nicht-deterministische Produktreihenfolge

**Status:** ❌ **NOCH IMMER NICHT BEHOBEN**

**Das Problem ist real:**

**Zeile 119 in `ui/production_calculations.py`:**
```python
products_list = list(MasterData.BOM.keys())  # ❌ NICHT SORTIERT
```

**Zeile 132-137:**
```python
for idx, product in enumerate(products_list):
    row_number = idx + 1  # ❌ Hängt von Reihenfolge ab!
    proportional = proportional_production_by_product.get(product, 0)
    rank_support = (row_number / 1000000.0) + proportional  # ❌ row_number macht Unterschied!
```

**Warum ist das ein Problem?**

Wenn zwei Produkte die **gleiche** `proportional` haben:
- Produkt A hat `proportional = 100`, `row_number = 1` → `rank_support = 100.000001`
- Produkt B hat `proportional = 100`, `row_number = 2` → `rank_support = 100.000002`

Produkt A bekommt Rang 1, Produkt B Rang 2.

**Wenn die Reihenfolge variiert:**
- Produkt B hat `proportional = 100`, `row_number = 1` → `rank_support = 100.000001`
- Produkt A hat `proportional = 100`, `row_number = 2` → `rank_support = 100.000002`

Jetzt bekommt Produkt B Rang 1, Produkt A Rang 2!

**Auswirkung:**
- Unterschiedliche Produktionsmengen bei Neuladen
- MTB Extreme kann 1799 oder 1760 haben

**Lösung:**
```python
products_list = sorted(MasterData.BOM.keys())  # ✅ Sortiert!
```

---

### 🔴 FEHLER-004: Kein Konvergenz-Check

**Status:** ❌ **NOCH IMMER NICHT BEHOBEN**

**Aktueller Code (`ui/page_initialization.py` Zeile 39-63):**
```python
# ITERATION 1
calculate_production_logs()
calculate_material_inventory()

# ITERATION 2
calculate_production_logs()
calculate_material_inventory()
# ❌ KEIN CHECK OB WERTE KONVERGIERT SIND
```

**Problem:**
- Genau 2 Iterationen werden durchgeführt
- Kein Check ob `production_logs_cache` sich zwischen Iterationen ändert
- Werte könnten oszillieren

**Auch wenn die neue Material-Logik besser ist**, ohne Konvergenz-Check können Werte immer noch oszillieren.

---

## 📊 Zusammenfassung

### ✅ Was NEU/VERBESSERT ist:
1. **Material ↔ Produktion Verbindung:** Nutzt jetzt Inbound-Tabelle als Source of Truth
2. **Materialverbrauch:** Wird explizit aus `production_logs_cache` gelesen
3. **Konsistenz:** Materiallager und Produktion sehen dieselben Daten

### ❌ Was NOCH IMMER ein Problem ist:
1. **FEHLER-003:** Produktreihenfolge nicht stabilisiert (5 Stellen)
2. **FEHLER-004:** Kein Konvergenz-Check für iterative Berechnung
3. **FEHLER-001:** Parameter-Synchronisation fehlt
4. **FEHLER-002:** Cache-Invalidierung fehlt

---

## 🎯 Fazit

**Der Kollege hat Recht:** Die Material ↔ Produktion Verbindung wurde tatsächlich neu implementiert und ist besser!

**ABER:** Die Produktreihenfolge ist immer noch ein Problem, das zu nicht-deterministischen Ergebnissen führt.

**Empfehlung:**
1. ✅ Die neue Material-Logik ist gut - behalten!
2. ❌ Produktreihenfolge stabilisieren (`sorted()`)
3. ❌ Konvergenz-Check hinzufügen
4. ❌ Parameter-Synchronisation implementieren

---

**Status:** ⚠️ **TEILWEISE BEHOBEN**  
**Neue Material-Logik:** ✅ Gut  
**Produktreihenfolge:** ❌ Noch Problem  
**Konvergenz-Check:** ❌ Noch Problem
