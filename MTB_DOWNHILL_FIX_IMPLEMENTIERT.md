# MTB Downhill Fix - Implementiert

**Datum:** 28.01.2026  
**Problem:** MTB Downhill hat ein Rad zu wenig (36999 statt 37000)  
**Status:** ✅ **FIX IMPLEMENTIERT**

---

## 🔴 Problem

### Symptome:
- **Nur bei MTB Downhill** tritt das Problem auf
- Gesamtvolumen erreicht nur 369.500 statt 370.000 (fehlt 500)
- In der wöchentlichen Volumenplanung steht für MTB Downhill: **36999** statt **37000**

### Ursache:
Am letzten Arbeitstag des Jahres werden Reste aufsummiert, aber dann wird nochmal `math.floor()` aufgerufen, wodurch Reste verloren gehen.

**Beispiel:**
- `rounded_base = 100`
- `remainder_to_add = 0.9`
- `daily_target_float = 100 + 0.9 = 100.9`
- `daily_target_int = math.floor(100.9) = 100` ❌ **Rest geht verloren!**

---

## ✅ Lösung

### Code-Änderung in `simulation/demand_calculator.py`:

**Vorher:**
```python
if is_last_workday_of_year:
    remainder_to_add = base_with_remainder - rounded_base
    daily_target_float = rounded_base + remainder_to_add + marketing_add_on

# 6. Ergebnis abrunden (da wir Integer zurückgeben müssen)
daily_target_int = math.floor(daily_target_float)  # ❌ Verliert Reste!
```

**Nachher:**
```python
if is_last_workday_of_year:
    remainder_to_add = base_with_remainder - rounded_base
    daily_target_float = rounded_base + remainder_to_add + marketing_add_on
    # KRITISCH: Am letzten Arbeitstag RUNDEN statt ABRUNDEN, um Reste nicht zu verlieren
    # Die Excel-Formel zeigt: Reste werden aufsummiert, dann gerundet (nicht abgerundet)
    daily_target_int = round(daily_target_float)  # ✅ Behält Reste!
else:
    # Normale Tage: Abrunden (ABRUNDEN in Excel)
    daily_target_int = math.floor(daily_target_float)
```

---

## 🎯 Erwartetes Ergebnis

Nach diesem Fix:
- ✅ Reste werden am letzten Arbeitstag korrekt aufsummiert
- ✅ Kein Verlust durch `floor()` nach dem Aufsummieren
- ✅ MTB Downhill sollte jetzt genau **37000** erreichen
- ✅ Gesamtvolumen sollte genau **370000** erreichen

---

## 📋 Nächste Schritte

1. **Testen:** Prüfe ob MTB Downhill jetzt genau 37000 erreicht
2. **Validieren:** Prüfe ob Gesamtvolumen genau 370000 erreicht
3. **Performance:** Prüfe ob Performance-Probleme weiterhin bestehen

---

**Status:** ✅ **IMPLEMENTIERT**  
**Geänderte Dateien:**
- `simulation/demand_calculator.py` (Zeile 152-161)
