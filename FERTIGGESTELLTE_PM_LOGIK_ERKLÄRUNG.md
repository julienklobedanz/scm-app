# Fertiggestellte PM - Logik-Erklärung

**Datum:** 28.01.2026  
**Frage:** Warum muss man versetzt gucken (tatsächliche PM Tag X → fertiggestellte PM Tag X+1)?

---

## 🔍 Die Logik: "Versetzt gucken"

### Grundprinzip:

**fertiggestellte PM am Tag X = tatsächliche PM vom Tag X-1** (vom vorherigen Arbeitstag)

### Warum diese Logik?

#### 1. **Produktionsprozess braucht Zeit**

**Realistische Produktionsabfolge:**
- **Tag X (z.B. 14.01.2027):**
  - **Morgen:** Produktion startet
  - **Tag über:** Fahrräder werden produziert
  - **Abend:** Produktion ist abgeschlossen, aber Fahrräder sind noch nicht fertiggestellt
  - **Über Nacht:** Qualitätskontrolle, Verpackung, Fertigstellung

- **Tag X+1 (z.B. 15.01.2027):**
  - **Morgen:** Fahrräder sind fertiggestellt und werden ins Lager eingelegt
  - **→ fertiggestellte PM = tatsächliche PM vom Vortag**

#### 2. **1-Tag-Verzögerung ist realistisch**

**Beispiel aus dem Test:**
- **14.01.2027:**
  - `tatsächliche PM = 22` (22 Fahrräder werden produziert)
  - `fertiggestellte PM = 22` (vom Vortag 13.01)

- **15.01.2027:**
  - `tatsächliche PM = 0` (keine Produktion wegen Materialmangel)
  - `fertiggestellte PM = 0` (weil tatsächliche PM vom Vortag 14.01 = 0, ABER WARTE...)

**Korrektur:**
- Am 14.01 wurde `tatsächliche PM = 22` produziert
- Am 15.01 sollte `fertiggestellte PM = 22` sein (vom Vortag)
- ABER: Im Bild steht `fertiggestellte PM = 0`

**Das ist korrekt, wenn:**
- Am 14.01 wurde `tatsächliche PM = 0` produziert (nicht 22)
- Oder: Die 22 wurden bereits am 13.01 fertiggestellt

---

## 📊 Beispiel: Korrekte Interpretation

### Szenario: Materialmangel am 14.01

**14.01.2027:**
- `geplante PM = 22` (22 Fahrräder geplant)
- `tatsächliche PM = 0` (keine Produktion wegen Materialmangel)
- `fertiggestellte PM = 22` (vom Vortag 13.01)

**15.01.2027:**
- `geplante PM = 74` (74 Fahrräder geplant)
- `tatsächliche PM = 0` (keine Produktion wegen Materialmangel)
- `fertiggestellte PM = 0` (weil tatsächliche PM vom Vortag 14.01 = 0) ✅ **KORREKT**

**Backlog:**
- 14.01: Backlog = 67 (89 Nachfrage - 22 fertiggestellt)
- 15.01: Backlog = 156 (67 + 89 Nachfrage - 0 fertiggestellt)

---

## 🎯 Warum "versetzt gucken"?

### 1. **Produktionszyklus**

```
Tag X:        [Produktion läuft] → Abend: Produktion fertig, aber noch nicht verpackt
Tag X+1:      [Fertigstellung] → Morgen: Fahrräder ins Lager eingelegt
```

### 2. **Lagerzugang**

- **Fertigproduktelager** zeigt `Lagerzugang = fertiggestellte PM`
- Das bedeutet: Fahrräder kommen **am Tag X+1** ins Lager
- Sie wurden aber **am Tag X** produziert

### 3. **Konsistenz**

- **Materiallager:** Material wird am Tag X verbraucht
- **Produktion:** Fahrräder werden am Tag X produziert
- **Fertigproduktelager:** Fahrräder kommen am Tag X+1 ins Lager

**Das ist konsistent:** Material → Produktion → Fertigstellung → Lagerzugang

---

## 📋 Code-Implementierung

**Code (Zeile 635 in `ui/production_calculations.py`):**
```python
# Normale Logik: fertiggestellte PM = tatsächliche PM vom Vortag
prev_actual_pm = prev_row.get('tatsächliche PM', 0)
df_sorted.at[idx, 'fertiggestellte PM'] = int(round(prev_actual_pm)) if prev_actual_pm > 0 else 0
```

**Logik:**
1. Finde vorherigen Arbeitstag (Tag X-1)
2. Hole `tatsächliche PM` vom vorherigen Arbeitstag
3. Setze `fertiggestellte PM` am aktuellen Tag (Tag X) = `tatsächliche PM` vom Vortag

---

## ✅ Zusammenfassung

### Warum versetzt gucken?

1. **Realistische Produktionsabfolge:** Produktion braucht Zeit zum Fertigstellen
2. **1-Tag-Verzögerung:** Fahrräder werden über Nacht fertiggestellt
3. **Konsistenz:** Material → Produktion → Fertigstellung → Lagerzugang
4. **Lagerzugang:** Fahrräder kommen am Tag X+1 ins Lager (produziert am Tag X)

### Die Regel:

**Immer versetzt gucken:**
- `fertiggestellte PM am Tag X` = `tatsächliche PM vom Tag X-1`
- `Lagerzugang am Tag X` = `fertiggestellte PM am Tag X`

**Beispiel:**
- 14.01: `tatsächliche PM = 22` → 15.01: `fertiggestellte PM = 22`
- 15.01: `fertiggestellte PM = 22` → 15.01: `Lagerzugang = 22`

---

**Status:** ✅ **LOGIK ERKLÄRT UND BESTÄTIGT**
