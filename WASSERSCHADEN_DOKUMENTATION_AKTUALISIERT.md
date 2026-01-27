# Wasserschaden: Vollständige Dokumentation - Aktualisiert

**Datum:** 27.01.2026  
**Status:** Nach Fix für fertiggestellte PM

---

## 📊 Was passiert bei Wasserschaden?

### Timing-Ablauf:

**Tag X-1 (z.B. 21.02.2027):**
- Produktion läuft normal (z.B. 53 Stück MTB Marathon)
- tatsächliche PM = 53

**Tag X (z.B. 22.02.2027) - Wasserschaden-Tag:**
- **Morgens:** Wasserschaden passiert → Bestand aller Sättel = 0
- **Produktion:** tatsächliche PM = 0 (kein Material verfügbar)
- **Fertigstellung:** fertiggestellte PM = 0 ✅ (FIX: auch wenn am Vortag produziert wurde)
- **Lagerzugang:** 0 ✅ (keine fertiggestellten Produkte)

**Tag X+1 (z.B. 23.02.2027):**
- **Produktion:** Kann wieder laufen (wenn Material wieder verfügbar)
- **Fertigstellung:** fertiggestellte PM = tatsächliche PM vom Vortag (Tag X) = 0

---

## 🎯 Was man wo sehen kann

### 1. "5 Materiallager" - Bestand wird auf 0 gesetzt

**Was prüfen:**
- Navigiere zu **"5 Materiallager"**
- Suche nach **Tag 22.02.2027** (Wasserschaden-Tag)
- Prüfe für **alle Sattel-Typen** (Race line, Fizik Tundra, etc.)

**Erwartetes Ergebnis:**
- ✅ **Verlustmenge:** = Bestand morgens vor Schaden (z.B. 480 für Race line)
- ✅ **Bestand morgens:** 0 (nach Wasserschaden)
- ✅ **Lagerabgang:** 0 (keine Produktion möglich)
- ✅ **Bestand abends:** 0 (nach Wasserschaden)

**Was bedeutet das:**
- System hat Bestand auf 0 gesetzt ✅
- Produktion kann nicht laufen (kein Material) ✅

---

### 2. "6 Produktion" - Produktion wird auf 0 reduziert

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Suche nach **Tag 22.02.2027**
- Prüfe für **betroffene Produkte** (z.B. MTB Marathon für Race line)

**Erwartetes Ergebnis:**
- ✅ **geplante PM:** Gleich (Nachfrage ändert sich nicht, z.B. 88)
- ✅ **tatsächliche PM:** 0 (keine Produktion wegen Materialmangel)
- ✅ **Material-Spalte (z.B. Race line):** 0 (kein Material verfügbar)
- ✅ **Backlog:** Erhöht (36 → 124, weil Nachfrage 88 bleibt, Produktion = 0)

**Was bedeutet das:**
- System hat Produktion auf 0 reduziert ✅
- System reagiert dynamisch auf Materialmangel ✅
- Backlog entsteht automatisch ✅

**Frage:** Fertiggestellte PM kommt vom Vortag aus dem Feld tatsächliche PM, richtig?
- ✅ **JA** - Normalerweise: fertiggestellte PM am Tag X = tatsächliche PM vom Tag X-1
- ✅ **ABER:** Wenn Wasserschaden am Tag X oder X-1 → fertiggestellte PM = 0

---

### 3. "7 Fertigproduktelager" - Keine neuen Endprodukte

**Was prüfen:**
- Navigiere zu **"7 Fertigproduktelager"**
- Suche nach **Tag 22.02.2027**
- Prüfe für **betroffene Produkte** (z.B. MTB Marathon)

**Erwartetes Ergebnis:**
- ✅ **Lagerzugang:** 0 ✅ (FIX: auch wenn am Vortag produziert wurde)
- ✅ **Lagerabgang:** Kann > 0 sein (Nachfrage wird aus Bestand bedient)
- ✅ **Bestand:** Sinkt (mehr Abgang als Zugang)

**Was bedeutet das:**
- Keine neuen Endprodukte produziert ✅
- Bestand wird abgebaut (Nachfrage wird bedient) ✅

**Vorher (BUG):**
- ❌ Lagerzugang = 53 (vom Vortag, obwohl Wasserschaden)

**Nachher (FIX):**
- ✅ Lagerzugang = 0 (Wasserschaden verhindert Fertigstellung)

---

### 4. "6 Produktion" - Backlog erhöht sich

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Suche nach **Tag 21-23.02.2027**
- Prüfe **Backlog-Spalte** für betroffene Produkte

**Erwartetes Ergebnis:**
- ✅ **Tag 21.02.2027:** Backlog = z.B. 36
- ✅ **Tag 22.02.2027:** Backlog = z.B. 124 (erhöht: 36 + 88 Nachfrage - 0 Produktion)
- ✅ **Tag 23.02.2027:** Backlog = weiter erhöht (wenn Produktion noch = 0)

**Was bedeutet das:**
- Backlog entsteht automatisch wenn Produktion < Nachfrage ✅
- System reagiert dynamisch auf Materialmangel ✅

---

## 📋 Zusammenfassung: Dynamische Reaktion sichtbar

### Materiallager (5 Materiallager):
- ✅ **Bestand morgens = 0** (nach Wasserschaden)
- ✅ **Lagerabgang = 0** (keine Produktion möglich)
- ✅ **Verlustmenge = Bestand morgens vor Schaden**

### Produktion (6 Produktion):
- ✅ **tatsächliche PM = 0** (keine Produktion wegen Materialmangel)
- ✅ **Material-Spalte = 0** (kein Material verfügbar)
- ✅ **Backlog erhöht** (Nachfrage bleibt, Produktion = 0)
- ✅ **fertiggestellte PM = 0** (FIX: auch wenn am Vortag produziert wurde)

### Fertigproduktelager (7 Fertigproduktelager):
- ✅ **Lagerzugang = 0** ✅ (FIX: keine fertiggestellten Produkte am Wasserschaden-Tag)
- ✅ **Lagerabgang kann > 0 sein** (Nachfrage wird aus Bestand bedient)
- ✅ **Bestand sinkt** (mehr Abgang als Zugang)

---

## 🔧 Fix: Fertiggestellte PM am Wasserschaden-Tag

### Problem:
- Am 22.02.2027 (Wasserschaden-Tag): fertiggestellte PM = 53 (vom Vortag)
- Lagerzugang im Fertigproduktelager = 53 (sollte 0 sein)

### Lösung:
- Wenn Wasserschaden am Tag X oder X-1 → fertiggestellte PM am Tag X = 0
- Begründung: Wenn Wasserschaden morgens passiert, kann Produktion vom Vortag nicht fertiggestellt werden

### Code-Änderung:
```python
# In ui/production_calculations.py, Zeile 569-604
# Prüfe ob Wasserschaden am aktuellen Tag oder Vortag war
water_damage_today = False
water_damage_yesterday = False

if scenario_manager:
    water_damage_today = len(scenario_manager.get_water_damage_scenarios(day)) > 0
    # Prüfe auch Vortag
    prev_day_check = day - 1
    while prev_day_check >= 0:
        if workday_calc.is_workday(prev_day_check):
            water_damage_yesterday = len(scenario_manager.get_water_damage_scenarios(prev_day_check)) > 0
            break
        prev_day_check -= 1

# Wenn Wasserschaden heute oder gestern: fertiggestellte PM = 0
if water_damage_today or water_damage_yesterday:
    df_sorted.at[idx, 'fertiggestellte PM'] = 0
else:
    # Normale Logik: fertiggestellte PM = tatsächliche PM vom Vortag
    ...
```

---

## ✅ Test-Anleitung: Wasserschaden nachvollziehen

### Test 1: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "Race line":**
   - Verlustmenge = 480 ✅
   - Bestand morgens = 0 ✅
   - Lagerabgang = 0 ✅
   - Bestand abends = 0 ✅

### Test 2: Produktion prüfen
1. **Navigiere zu "6 Produktion"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "MTB Marathon":**
   - geplante PM = 88 ✅
   - tatsächliche PM = 0 ✅
   - Race line (Material-Spalte) = 0 ✅
   - Backlog = 124 (36 + 88) ✅
   - fertiggestellte PM = 0 ✅ (FIX)

### Test 3: Fertigproduktelager prüfen
1. **Navigiere zu "7 Fertigproduktelager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "MTB Marathon":**
   - Lagerzugang = 0 ✅ (FIX: war vorher 53)
   - Lagerabgang = kann > 0 sein ✅
   - Bestand = sinkt ✅

### Test 4: Backlog-Verlauf prüfen
1. **Navigiere zu "6 Produktion"**
2. **Prüfe Backlog für "MTB Marathon" Tag 21-23.02.2027:**
   - Tag 21: Backlog = 36 ✅
   - Tag 22: Backlog = 124 (36 + 88) ✅
   - Tag 23: Backlog = weiter erhöht wenn Produktion noch = 0 ✅

---

**Status:** ✅ **FIX IMPLEMENTIERT**  
**Nächster Schritt:** Tests durchführen um Fix zu verifizieren
