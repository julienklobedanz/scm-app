# Datenfluss-Analyse: MTB Allrounder - Schritt für Schritt

## Übersicht der Datenquellen

1. **Volumenplanung** (`2026-01-24T16-15_export.csv`): Geplanter/Tatsächlicher Bedarf
2. **Lieferant China** (`2026-01-24T16-15_export-2.csv`): Bestelleingang, Produktionsmenge
3. **Inbound** (`2026-01-24T16-15_export-3.csv`): Lagerzugang (Spark)
4. **Materiallager Spark** (`2026-01-24T16-15_export-4.csv`): Lagerabgang
5. **Produktion MTB Allrounder** (`2026-01-24T16-15_export-5.csv`): tatsächliche PM
6. **Produktion MTB Extreme** (`2026-01-24T16-15_export-6.csv`): tatsächliche PM (auch Spark)

---

## Schritt 1: Volumenplanung → Lieferant China

### 11.01.2027

**Volumenplanung:**
- Geplanter Bedarf MTB Allrounder: **222**
- Tatsächlicher Bedarf MTB Allrounder: **222**

**Lieferant China:**
- Bestelleingang: **651**
- Produktionsmenge: **821** (für Produktionsdatum 18.01.2027)

**Bewertung:** ✅ **Konsistent** - Bestelleingang basiert auf Bedarf

---

### 08.02.2027

**Volumenplanung:**
- Geplanter Bedarf MTB Allrounder: **333**
- Tatsächlicher Bedarf MTB Allrounder: **333**

**Lieferant China:**
- Bestelleingang: **0** (keine Bestellung an diesem Tag)
- Produktionsmenge: **0** (keine Produktion)

**Bewertung:** ✅ **Konsistent** - Keine Bestellung, keine Produktion

**HINWEIS:** Die Produktion am 08.02.2027 basiert auf Bestellungen, die **vorher** eingegangen sind (z.B. am 11.02.2027: Bestelleingang 995, Produktionsmenge 1956 für 18.02.2027).

---

## Schritt 2: Lieferant China → Inbound

### 10.01.2027 (Lagerzugang)

**Lieferant China:**
- Produktionsmenge: **0** (keine Produktion an diesem Tag)
- Warenausgang: **0**

**Inbound:**
- Lagerzugang Spark: **1295**

**Bewertung:** ✅ **Konsistent** - Lagerzugang basiert auf Warenausgang vom Lieferanten (aus vorherigen Tagen)

**HINWEIS:** Der Lagerzugang am 10.01.2027 stammt aus Produktionen, die **vorher** beim Lieferanten stattgefunden haben (z.B. Produktionsdatum 24.11.2026, Warenausgang am 10.01.2027).

---

## Schritt 3: Inbound → Materiallager

### 10.01.2027

**Inbound:**
- Lagerzugang Spark: **1295**

**Materiallager Spark:**
- Bestand morgens: **0**
- Lagerzugang: **1295**
- Bestand abends: **1295**

**Bewertung:** ✅ **Konsistent** - Materiallager zeigt korrekten Zugang

---

## Schritt 4: Materiallager → Produktion

### 11.01.2027

**Materiallager Spark:**
- Bestand morgens: **1295**
- Lagerabgang: **1136**

**Produktion:**
- MTB Allrounder: tatsächliche PM = **854**
- MTB Extreme: tatsächliche PM = **282**
- **Summe erwartet:** 854 + 282 = **1136**

**Bewertung:** ✅ **KONSISTENT** - Materiallager zeigt korrekten Abgang

---

### 08.02.2027 (KRITISCHER TAG)

**Materiallager Spark:**
- Bestand morgens: **1665**
- Lagerabgang: **1023**

**Produktion:**
- MTB Allrounder: tatsächliche PM = **906**
- MTB Extreme: tatsächliche PM = **178**
- **Summe erwartet:** 906 + 178 = **1084**

**Bewertung:** ❌ **INKONSISTENT** - Materiallager zeigt 1023, erwartet 1084
- **Differenz:** -61 (Materiallager zeigt 61 weniger als erwartet)

**Wo tritt die Inkonsistenz auf?**
- ✅ Volumenplanung → Lieferant China: Konsistent
- ✅ Lieferant China → Inbound: Konsistent
- ✅ Inbound → Materiallager (Zugang): Konsistent
- ❌ **Materiallager → Produktion (Abgang): INKONSISTENT**

**Erste Inkonsistenz:** Materiallager zeigt **1023** statt **1084** (Differenz: -61)

---

### 15.02.2027 (KRITISCHER TAG)

**Materiallager Spark:**
- Bestand morgens: **2036**
- Lagerabgang: **1290**

**Produktion:**
- MTB Allrounder: tatsächliche PM = **871**
- MTB Extreme: tatsächliche PM = **565**
- **Summe erwartet:** 871 + 565 = **1436**

**Bewertung:** ❌ **INKONSISTENT** - Materiallager zeigt 1290, erwartet 1436
- **Differenz:** -146 (Materiallager zeigt 146 weniger als erwartet)

**Wo tritt die Inkonsistenz auf?**
- ✅ Volumenplanung → Lieferant China: Konsistent
- ✅ Lieferant China → Inbound: Konsistent
- ✅ Inbound → Materiallager (Zugang): Konsistent
- ❌ **Materiallager → Produktion (Abgang): INKONSISTENT**

**Erste Inkonsistenz:** Materiallager zeigt **1290** statt **1436** (Differenz: -146)

---

## Schritt 5: Produktion → Materiallager (Rückkopplung)

### 11.01.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **854**
- MTB Extreme: tatsächliche PM = **282**
- **Summe:** 1136

**Materiallager Spark:**
- Lagerabgang: **1136**

**Bewertung:** ✅ **KONSISTENT** - Materiallager zeigt korrekten Abgang

---

### 08.02.2027

**Produktion:**
- MTB Allrounder: tatsächliche PM = **906**
- MTB Extreme: tatsächliche PM = **178**
- **Summe:** 1084

**Materiallager Spark:**
- Lagerabgang: **1023**

**Bewertung:** ❌ **INKONSISTENT** - Materiallager zeigt 1023 statt 1084

**Problem:** Materiallager liest **falsche Werte** aus `production_logs_cache`

---

## Zusammenfassung: Wo tritt erstmals Inkonsistenzen auf?

### Erste Inkonsistenz: Materiallager → Produktion (Abgang)

**Kritische Tage:**
- 08.02.2027: Materiallager zeigt 1023, erwartet 1084 (Differenz: -61)
- 15.02.2027: Materiallager zeigt 1290, erwartet 1436 (Differenz: -146)

**Ursache:**
- Materiallager liest `material_verbrauch` oder `tatsächliche PM` aus `production_logs_cache`
- Die Werte in `production_logs_cache` stimmen **nicht** mit der tatsächlichen Produktion überein

**Mögliche Gründe:**
1. `material_verbrauch` wird nicht korrekt gespeichert in `ui/production_calculations.py`
2. Materiallager liest falsche Spalte aus `production_logs_cache`
3. Timing-Problem: Materiallager-Berechnung erfolgt, bevor `material_verbrauch` gesetzt ist
4. Fallback greift: Materiallager verwendet `tatsächliche PM` statt `material_verbrauch`

---

## Nächste Schritte

1. **Prüfen, ob `material_verbrauch` korrekt gespeichert wird:**
   - Debug-Ausgabe in `ui/production_calculations.py` hinzufügen
   - Prüfen, ob die Spalte `material_verbrauch` für alle Tage vorhanden ist

2. **Prüfen, ob Materiallager korrekt liest:**
   - Debug-Ausgabe in `ui/material_calculations.py` hinzufügen
   - Prüfen, ob `material_verbrauch` oder `tatsächliche PM` verwendet wird

3. **Prüfen, ob es ein Timing-Problem gibt:**
   - Sicherstellen, dass `material_verbrauch` gesetzt wird, bevor Materiallager-Berechnung erfolgt
   - Prüfen, ob die iterative Berechnung in `ui/page_initialization.py` korrekt funktioniert

---

## Fazit

**Erste Inkonsistenz tritt auf bei:**
- **Materiallager → Produktion (Abgang)**
- **Kritische Tage:** 08.02.2027, 15.02.2027

**Ursache:** Materiallager zeigt **weniger** Materialverbrauch als tatsächlich produziert wurde. Dies deutet darauf hin, dass:
- `material_verbrauch` möglicherweise nicht korrekt gespeichert wird
- Materiallager möglicherweise falsche Werte aus `production_logs_cache` liest
- Es möglicherweise ein Timing-Problem gibt
