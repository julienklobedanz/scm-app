# MTB Downhill Problem - Detaillierte Analyse

**Datum:** 28.01.2026  
**Problem:** MTB Downhill hat ein Rad zu wenig (36999 statt 37000?)  
**Status:** 🔍 **IN ANALYSE**

---

## 🔴 Problem-Beschreibung

### Symptome:
- **Nur bei MTB Downhill** tritt das Problem auf
- Gesamtvolumen erreicht nur 369.500 statt 370.000 (fehlt 500)
- Backlog bleibt bestehen
- In der wöchentlichen Volumenplanung steht für MTB Downhill: **36999** statt **37000**

### Excel-Formel-Analyse:
Die Excel-Formel zeigt:
```
ABRUNDEN((Base * Share / AT) + Rest_Vortag; 0)
```

**Wichtig:** Am letzten Arbeitstag werden alle Reste aufsummiert.

---

## 🔍 Mögliche Ursachen

### 1. Carry-Over-Logik am letzten Arbeitstag

**Problem in `demand_calculator.py` Zeile 152-161:**
```python
if is_last_workday_of_year:
    remainder_to_add = base_with_remainder - rounded_base
    daily_target_float = rounded_base + remainder_to_add + marketing_add_on

# 6. Ergebnis abrunden (da wir Integer zurückgeben müssen)
daily_target_int = math.floor(daily_target_float)
```

**Problem:** Nach dem Aufsummieren der Reste wird nochmal `math.floor()` aufgerufen!

**Beispiel:**
- `rounded_base = 100`
- `remainder_to_add = 0.9`
- `daily_target_float = 100 + 0.9 = 100.9`
- `daily_target_int = math.floor(100.9) = 100` ❌ **Rest geht verloren!**

**Lösung:** Am letzten Arbeitstag sollte `daily_target_float` bereits ganzzahlig sein, oder wir sollten `round()` statt `floor()` verwenden.

---

### 2. Monatliche Base_Daily_Float Berechnung

**Problem:** Die monatliche Base_Daily_Float wird berechnet als:
```python
monthly_target_product = monthly_target_global * sales_share
base_daily_float[product] = monthly_target_product / num_workdays
```

**Für MTB Downhill:**
- `yearly_volume = 370000`
- `sales_share = 0.10`
- `monthly_target_product = 370000 * monthly_factor * 0.10`
- `base_daily_float = monthly_target_product / num_workdays`

**Problem:** Wenn die Summe aller `base_daily_float * num_workdays` über alle Monate nicht genau `370000 * 0.10 = 37000` ergibt, geht ein Rad verloren.

---

### 3. Korrektur-Logik in `volume_planning_utils.py`

**Aktuell:** Die Korrektur wird am letzten Arbeitstag angewendet:
```python
if difference != 0:
    demands_dict[last_workday_of_year][product] = (
        demands_dict[last_workday_of_year].get(product, 0) + difference
    )
```

**Problem:** Wenn die Korrektur zu spät kommt oder nicht korrekt angewendet wird, geht ein Rad verloren.

---

## 💡 Lösungsansätze

### Ansatz 1: Fix Carry-Over-Logik am letzten Arbeitstag

**Problem:** `math.floor()` wird nach dem Aufsummieren der Reste aufgerufen.

**Lösung:** Am letzten Arbeitstag sollte `round()` statt `floor()` verwendet werden, oder die Reste sollten so aufsummiert werden, dass das Ergebnis ganzzahlig ist.

**Code-Änderung:**
```python
if is_last_workday_of_year:
    remainder_to_add = base_with_remainder - rounded_base
    daily_target_float = rounded_base + remainder_to_add + marketing_add_on
    # Am letzten Arbeitstag: Runde statt abrunden, um Reste nicht zu verlieren
    daily_target_int = round(daily_target_float)  # Statt math.floor()
else:
    daily_target_int = math.floor(daily_target_float)
```

---

### Ansatz 2: Korrektur direkt in Carry-Over-Logik

**Problem:** Die Korrektur kommt zu spät (nach der Berechnung).

**Lösung:** Stelle sicher, dass die Summe bereits während der Carry-Over-Logik korrekt ist.

---

## 🎯 Empfohlener Ansatz

**Ansatz 1:** Fix Carry-Over-Logik am letzten Arbeitstag

**Vorteile:**
- Direkter Fix des Problems
- Keine zusätzliche Schleife
- Keine Performance-Probleme
- Entspricht Excel-Logik (Reste werden aufsummiert, nicht abgerundet)

**Implementierung:**
- In `demand_calculator.py`: Am letzten Arbeitstag `round()` statt `floor()` verwenden

---

---

## ✅ Implementierte Lösung

### Fix Carry-Over-Logik am letzten Arbeitstag

**Code-Änderung in `demand_calculator.py`:**
```python
if is_last_workday_of_year:
    remainder_to_add = base_with_remainder - rounded_base
    daily_target_float = rounded_base + remainder_to_add + marketing_add_on
    # KRITISCH: Am letzten Arbeitstag RUNDEN statt ABRUNDEN, um Reste nicht zu verlieren
    daily_target_int = round(daily_target_float)  # Statt math.floor()
else:
    # Normale Tage: Abrunden (ABRUNDEN in Excel)
    daily_target_int = math.floor(daily_target_float)
```

**Erwartetes Ergebnis:**
- Reste werden am letzten Arbeitstag korrekt aufsummiert
- Kein Verlust durch `floor()` nach dem Aufsummieren
- MTB Downhill sollte jetzt genau 37000 erreichen

---

**Status:** ✅ **IMPLEMENTIERT**  
**Nächster Schritt:** Testen ob MTB Downhill jetzt genau 37000 erreicht
