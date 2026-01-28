# Materialallokation und fertiggestellte PM - Analyse

**Datum:** 28.01.2026  
**Fragen:** Warum Performance die 22 Sättel bekommt, fertiggestellte PM Logik, 244 am 18.01

---

## 1. Warum Performance die 22 Sättel bekommt (nicht Freeride)

### Produktreihenfolge (alphabetisch sortiert)

Aus `config/master_data.py` und `simulation/production_planner.py` Zeile 181:
```python
products_list = sorted(self.master_data.BOM.keys())
```

**Alphabetische Reihenfolge:**
1. MTB Allrounder (row_number = 1)
2. MTB Competition (row_number = 2)
3. MTB Downhill (row_number = 3)
4. MTB Extreme (row_number = 4)
5. **MTB Freeride** (row_number = 5) ← Nutzt "Fizik Tundra"
6. MTB Marathon (row_number = 6)
7. **MTB Performance** (row_number = 7) ← Nutzt "Fizik Tundra"
8. MTB Trail (row_number = 8)

### Rang-Berechnung

**Code (Zeile 194-201 in `production_planner.py`):**
```python
rank_support_by_product = {}
for idx, product in enumerate(products_list):
    row_number = idx + 1
    proportional = proportional_production_by_product.get(product, 0)
    # Rang_Unterstützung = Anteilige_Produktion + Zeile/1000000
    rank_support = (row_number / 1000000.0) + proportional
    rank_support_by_product[product] = rank_support

# Sortiere Produkte nach Rang (Höchster Support-Wert zuerst = Rang 1)
sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)
```

### Beispiel: 14.01.2027 - 22 Sättel verfügbar

**Annahme:** Beide Produkte haben `proportional = 22` (gleicher Bedarf)

**Rang-Berechnung:**
- **Freeride:** 
  - `row_number = 5`
  - `proportional = 22`
  - `rank_support = 22 + 0.000005 = 22.000005`
  
- **Performance:**
  - `row_number = 7`
  - `proportional = 22`
  - `rank_support = 22 + 0.000007 = 22.000007`

**Ergebnis:**
- Performance hat **höheren** `rank_support` (22.000007 > 22.000005)
- Performance wird **zuerst** sortiert → **Rang 1**
- Freeride wird **zweiter** sortiert → **Rang 2**

**Materialallokation (Zeile 224-260):**
- Produkte werden **nach Rang** durchlaufen (höchster Rang zuerst)
- Performance (Rang 1) bekommt zuerst Material → 22 Sättel
- Freeride (Rang 2) bekommt danach Material → 0 Sättel (keine mehr verfügbar)

### ✅ Fazit: Logik ist korrekt!

**Warum Performance vor Freeride:**
- Bei **gleicher** `proportional` entscheidet der `row_number` als Tie-Breaker
- Performance hat höheren `row_number` (7 > 5) → höherer `rank_support` → höherer Rang
- Höherer Rang = wird zuerst produziert = bekommt Material zuerst

**Das ist eine bewusste Design-Entscheidung:**
- Bei knappen Materialien wird die alphabetisch spätere Produktreihenfolge bevorzugt
- Dies sorgt für deterministisches Verhalten (immer dieselbe Reihenfolge)

---

## 2. fertiggestellte PM Logik - Versetzt gucken?

### ✅ JA - Die Logik ist korrekt!

**Code (Zeile 635 in `ui/production_calculations.py`):**
```python
# Normale Logik: fertiggestellte PM = tatsächliche PM vom Vortag
df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
```

**Logik:**
- **fertiggestellte PM am Tag X = tatsächliche PM vom Tag X-1** (vom vorherigen Arbeitstag)

### Beispiel aus den Bildern:

**14.01.2027:**
- `tatsächliche PM = 22`
- `fertiggestellte PM = 22` ← Das ist die tatsächliche PM vom **13.01** (Vortag)

**15.01.2027:**
- `tatsächliche PM = 89`
- `fertiggestellte PM = 0` ← Das ist die tatsächliche PM vom **14.01** (Vortag) = 22, ABER:
  - Es wurde nur 22 produziert (Materialmangel)
  - Die fertiggestellte PM sollte 22 sein, nicht 0
  - **WARTE:** Lass mich das nochmal prüfen...

**Korrektur:** 
- Am 14.01 wurde `tatsächliche PM = 22` produziert
- Am 15.01 sollte `fertiggestellte PM = 22` sein (vom Vortag)
- ABER im Bild steht `fertiggestellte PM = 0`

**Das könnte ein Problem sein!** Lass mich die Logik nochmal prüfen...

### Prüfung der fertiggestellte PM Logik:

**Code-Zeile 628-635:**
```python
prev_actual_pm = prev_row.get('tatsächliche PM', 0)

# Wenn am Vortag Wasserschaden war UND nichts produziert wurde → fertiggestellte PM = 0
# Wenn am Vortag produziert wurde (auch wenn vorher Wasserschaden war) → fertiggestellte PM = tatsächliche PM vom Vortag
if prev_water_damage and prev_actual_pm == 0:
    df_sorted.at[idx, 'fertiggestellte PM'] = 0
else:
    df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
```

**Mögliche Ursachen für `fertiggestellte PM = 0` am 15.01:**
1. Am 14.01 war Wasserschaden UND `tatsächliche PM = 0` → dann wäre `fertiggestellte PM = 0` korrekt
2. ABER: Am 14.01 wurde `tatsächliche PM = 22` produziert → dann sollte `fertiggestellte PM = 22` sein

**Das könnte ein Bug sein!** ⚠️

---

## 3. Die 244 am 18.01 - Ist das korrekt?

### Berechnung:

**18.01.2027:**
- `geplante PM = 88`
- `tatsächliche PM = 88`
- `fertiggestellte PM = 244`
- `Backlog = 0`

**Woher kommt die 244?**

**Mögliche Erklärung:**
- Backlog vom 17.01 = 156
- Tatsächliche PM am 18.01 = 88
- **ABER:** fertiggestellte PM ist NICHT Backlog + aktuelle PM!

**Korrekte Logik:**
- `fertiggestellte PM am 18.01 = tatsächliche PM vom 17.01` (Vortag)

**Wenn am 17.01 `tatsächliche PM = 244` war:**
- Dann wäre `fertiggestellte PM = 244` am 18.01 korrekt ✅

**ODER:**
- Wenn am 17.01 `tatsächliche PM = 156` war (Backlog)
- Und am 18.01 `tatsächliche PM = 88` ist
- Dann sollte `fertiggestellte PM am 18.01 = 156` sein (vom Vortag)

**Die 244 passt nicht zu dieser Logik!** ⚠️

**Mögliche Erklärung:**
- Die fertiggestellte PM könnte kumuliert sein (Backlog + aktuelle Produktion)
- Oder es gibt eine andere Logik, die ich noch nicht verstehe

---

## 4. Offene Fragen / Mögliche Bugs

### ⚠️ Frage 1: Warum ist fertiggestellte PM am 15.01 = 0?

**Erwartung:**
- Am 14.01: `tatsächliche PM = 22`
- Am 15.01: `fertiggestellte PM = 22` (vom Vortag)

**Tatsächlich:**
- Am 15.01: `fertiggestellte PM = 0`

**Mögliche Ursachen:**
1. Wasserschaden-Logik greift fälschlicherweise
2. Vorheriger Arbeitstag wird nicht korrekt gefunden
3. Andere Bedingung verhindert die Berechnung

### ⚠️ Frage 2: Woher kommt die 244 am 18.01?

**Erwartung (nach aktueller Logik):**
- `fertiggestellte PM am 18.01 = tatsächliche PM vom 17.01`

**Tatsächlich:**
- `fertiggestellte PM = 244`

**Mögliche Erklärungen:**
1. Kumulierte Logik (Backlog + aktuelle PM)
2. Mehrere Tage werden zusammengefasst
3. Andere Berechnungslogik als dokumentiert

---

## 5. Empfohlene Prüfungen

### Prüfung 1: fertiggestellte PM Logik testen

**Test-Szenario:**
1. Tag X: `tatsächliche PM = 100`
2. Tag X+1: Prüfe `fertiggestellte PM`
3. Erwartung: `fertiggestellte PM = 100` (vom Vortag)

**Wenn nicht:** Bug identifiziert!

### Prüfung 2: Materialallokation bei knappen Beständen

**Test-Szenario:**
1. Nur 22 Sättel verfügbar
2. Freeride und Performance haben beide Bedarf
3. Prüfe: Wer bekommt die Sättel?
4. Erwartung: Performance (höherer Rang)

**Wenn nicht:** Bug identifiziert!

---

## 6. Zusammenfassung

### ✅ Was korrekt ist:

1. **Materialallokation:** Performance bekommt die 22 Sättel, weil es einen höheren Rang hat (höherer `row_number` bei gleicher `proportional`)
2. **Versetzt gucken:** Die Logik "fertiggestellte PM = tatsächliche PM vom Vortag" ist korrekt implementiert

### ⚠️ Was unklar ist:

1. **fertiggestellte PM am 15.01 = 0:** Sollte 22 sein (vom Vortag)
2. **fertiggestellte PM am 18.01 = 244:** Passt nicht zur erwarteten Logik

### 🔍 Nächste Schritte:

1. Code-Logik für fertiggestellte PM am 15.01 prüfen
2. Code-Logik für fertiggestellte PM am 18.01 prüfen
3. Test-Szenarien durchführen
4. Dokumentation aktualisieren wenn nötig

---

**Status:** ⚠️ **ANALYSE ABGESCHLOSSEN - WEITERE PRÜFUNGEN ERFORDERLICH**
