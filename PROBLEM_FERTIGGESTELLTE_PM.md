# Problem: Fertiggestellte PM am Wasserschaden-Tag

**Datum:** 27.01.2026  
**Problem:** Lagerzugang im Fertigproduktelager zeigt 53 statt 0 am Wasserschaden-Tag

---

## 🔍 Problem-Analyse

### Aktuelle Logik:

**"fertiggestellte PM" am Tag X = tatsächliche PM vom Tag X-1 (vom Vortag)**

**Beispiel am 22.02.2027 (Wasserschaden-Tag):**
- **21.02.2027:** tatsächliche PM = 53 (Produktion läuft normal)
- **22.02.2027:** 
  - tatsächliche PM = 0 ✅ (korrekt, kein Material wegen Wasserschaden)
  - fertiggestellte PM = 53 ❌ (vom Vortag!)
  - Lagerzugang im Fertigproduktelager = 53 ❌ (sollte 0 sein?)

---

## 🤔 Ist das ein Problem?

### Logische Interpretation:

**Szenario 1: Produktion wird über Nacht fertiggestellt**
- Am 21.02.2027: Produktion läuft (53 Stück)
- Am Abend 21.02.2027: Produktion ist fertig
- Über Nacht: Produkte werden ins Lager eingelegt
- Am Morgen 22.02.2027: Lagerzugang = 53 (vom Vortag)
- Dann: Wasserschaden passiert

**In diesem Fall:** Lagerzugang = 53 ist **korrekt** ✅

**Szenario 2: Wasserschaden verhindert Fertigstellung**
- Am 21.02.2027: Produktion läuft (53 Stück)
- Am Morgen 22.02.2027: Wasserschaden passiert
- Produktion vom Vortag kann nicht fertiggestellt werden
- Am 22.02.2027: Lagerzugang = 0

**In diesem Fall:** Lagerzugang = 53 ist **falsch** ❌

---

## ✅ Erwartung des Benutzers

Der Benutzer erwartet:
- **Am Wasserschaden-Tag:** Lagerzugang = 0
- **Begründung:** Wenn kein Material da ist, sollte auch keine Produktion fertiggestellt werden

---

## 🔧 Lösung: Wasserschaden berücksichtigen

**Option 1: Fertiggestellte PM = 0 wenn Wasserschaden am Vortag**
- Wenn am Tag X-1 Wasserschaden war → fertiggestellte PM am Tag X = 0

**Option 2: Fertiggestellte PM = 0 wenn Wasserschaden am aktuellen Tag**
- Wenn am Tag X Wasserschaden ist → fertiggestellte PM am Tag X = 0

**Option 3: Fertiggestellte PM = tatsächliche PM vom Vortag nur wenn keine Störung**
- Wenn am Tag X-1 oder X Wasserschaden war → fertiggestellte PM = 0

---

## 📋 Empfehlung

**Option 3 ist am sinnvollsten:**
- Wenn am Tag X Wasserschaden ist → fertiggestellte PM = 0
- Begründung: Wenn Wasserschaden morgens passiert, kann die Produktion vom Vortag nicht fertiggestellt werden

**Code-Änderung:**
```python
# In ui/production_calculations.py, Zeile 558-590
# Prüfe ob Wasserschaden am aktuellen Tag oder Vortag war
water_damage_today = False
water_damage_yesterday = False

if scenario_manager:
    water_damage_today = len(scenario_manager.get_water_damage_scenarios(day)) > 0
    if prev_day >= 0:
        water_damage_yesterday = len(scenario_manager.get_water_damage_scenarios(prev_day)) > 0

if water_damage_today or water_damage_yesterday:
    df_sorted.at[idx, 'fertiggestellte PM'] = 0
else:
    # Normale Logik: fertiggestellte PM = tatsächliche PM vom Vortag
    prev_actual_pm = prev_row.get('tatsächliche PM', 0)
    df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
```

---

**Status:** ⚠️ **PROBLEM IDENTIFIZIERT**  
**Nächster Schritt:** Code anpassen um Wasserschaden zu berücksichtigen
