# Fizik Tundra Diskrepanz-Analyse

**Datum:** 29.01.2026  
**Status:** 🔍 **IN ANALYSE**

---

## 📊 Daten aus CSV-Exporten

### Materiallager Fizik Tundra

**Summen (Zeile 368):**
- **Lagerzugang:** 99,900
- **Lagerabgang:** 99,090
- **Verlustmenge:** 0
- **Restbestand am 31.12.2027:** 810

**Berechnung:**
- Erwarteter Restbestand = 99,900 - 99,090 - 0 = **810** ✅ (passt)

---

### Produktion - MTB Downhill (verwendet Fizik Tundra)

**Summen (Zeile 367):**
- **geplante PM:** 37,000
- **tatsächliche PM:** 37,000
- **fertiggestellte PM:** 36,951
- **Backlog:** 2,575

**Differenz:**
- fehlende fertiggestellte PM = 37,000 - 36,951 = **49**

---

### Produktion - MTB Freeride (verwendet Fizik Tundra)

**Summen (Zeile 367):**
- **geplante PM:** 18,500
- **tatsächliche PM:** 18,500
- **fertiggestellte PM:** 18,475
- **Backlog:** 2,995

**Differenz:**
- fehlende fertiggestellte PM = 18,500 - 18,475 = **25**

---

### Produktion - MTB Performance (verwendet Fizik Tundra)

**Summen (Zeile 367):**
- **geplante PM:** 55,500
- **tatsächliche PM:** 55,500
- **fertiggestellte PM:** 55,427
- **Backlog:** 2,995

**Differenz:**
- fehlende fertiggestellte PM = 55,500 - 55,427 = **73**

---

## 🔍 Analyse

### Problem 1: Fehlende fertiggestellte PM

**Gesamt fehlende fertiggestellte PM:**
- MTB Downhill: 49
- MTB Freeride: 25
- MTB Performance: 73
- **Summe: 147**

**Ursache:**
- `fertiggestellte PM` wird als `tatsächliche PM vom Vortag` berechnet
- Wenn am letzten Tag des Jahres produziert wurde, gibt es keinen nächsten Tag
- Die `tatsächliche PM` vom letzten Tag (31.12.2027) wird nicht als `fertiggestellte PM` gezählt

**Erwartung:**
- Die fehlenden 147 sollten durch die `tatsächliche PM` vom letzten Tag erklärt werden können

---

### Problem 2: Restbestand vs. fehlende fertiggestellte PM

**Beobachtung:**
- Restbestand Materiallager: **810**
- Fehlende fertiggestellte PM: **147**
- **Differenz: 810 - 147 = 663**

**Das bedeutet:**
- 147 Einheiten wurden produziert, aber nicht als fertiggestellt gezählt (Problem 1)
- **663 Einheiten Material wurden nie produziert** (Problem 2)

**Mögliche Ursachen für Problem 2:**
1. Material wurde verbraucht, aber nicht produziert (unmöglich)
2. Material wurde nicht verbraucht, obwohl produziert wurde (unmöglich)
3. **Materialverbrauch wird nicht korrekt erfasst** (wahrscheinlich)
4. **Material wurde produziert, aber nicht als `material_verbrauch` gesetzt** (wahrscheinlich)

---

### Problem 3: Materialverbrauch vs. Produktion

**Erwartung:**
- Materialverbrauch = Summe aller `tatsächliche PM` für Produkte die Fizik Tundra verwenden
- Materialverbrauch = 37,000 (Downhill) + 18,500 (Freeride) + 55,500 (Performance) = **111,000**

**Tatsächlich:**
- Materialverbrauch (Lagerabgang): **99,090**
- **Differenz: 111,000 - 99,090 = 1,910**

**Das bedeutet:**
- Es wurden **111,000** Fahrräder produziert (tatsächliche PM)
- Aber nur **99,090** Material wurde verbraucht
- **1,910** Material wurde nicht verbraucht, obwohl produziert wurde

**ABER:** Der Restbestand ist nur **810**, nicht 1,910!

**Das bedeutet:**
- Materialverbrauch (99,090) + Restbestand (810) = **99,900** ✅ (passt zu Lagerzugang)
- Aber: Produktion (111,000) > Materialverbrauch (99,090) + Restbestand (810) = 99,900
- **Differenz: 111,000 - 99,900 = 1,100**

**Mögliche Erklärung:**
- Material wurde produziert, aber `material_verbrauch` wurde nicht korrekt gesetzt
- Oder: Material wurde mehrfach verbraucht (unmöglich)
- Oder: **Materialverbrauch wird nicht für alle Tage erfasst** (wahrscheinlich)

---

## 🎯 Zusammenfassung der Probleme

### Problem A: Fehlende fertiggestellte PM (147 Einheiten)

**Ursache:** Die `tatsächliche PM` vom letzten Tag (31.12.2027) wird nicht als `fertiggestellte PM` gezählt, weil es keinen nächsten Tag gibt.

**Lösung:** Bereits implementiert in `pages/1_reporting.py` und `pages/7_fertigproduktelager.py` - die `tatsächliche PM` vom letzten Tag wird explizit addiert.

**ABER:** Die Summe in der Produktionstabelle zeigt immer noch 36,951 statt 37,000 für Downhill.

**Mögliche Ursache:** Die Summe wird nur über die angezeigten Daten berechnet, nicht über das gesamte Jahr.

---

### Problem B: Materialverbrauch wird nicht korrekt erfasst (810 Restbestand)

**Ursache:** `material_verbrauch` wird nicht für alle Tage gesetzt, obwohl Material verbraucht wurde.

**Mögliche Gründe:**
1. Tage die nicht in `day_row_map` sind werden nicht erfasst
2. `material_verbrauch` wird nur gesetzt wenn `qty_to_book > 0`, aber Material könnte auch bei `qty_to_book = 0` verbraucht worden sein
3. Material wurde produziert, aber `material_verbrauch` wurde nicht im DataFrame gesetzt

**Lösung:** Bereits implementiert - `material_verbrauch` wird jetzt für alle Tage gesetzt, auch wenn `qty_to_book = 0`.

**ABER:** Das Problem besteht immer noch!

---

## 🔧 Nächste Schritte

1. **Prüfe ob `material_verbrauch` wirklich für alle Tage gesetzt wird**
   - Prüfe ob alle Tage in `production_logs` vorhanden sind
   - Prüfe ob `material_verbrauch` für alle Tage gesetzt ist

2. **Prüfe ob die Summe in der Produktionstabelle korrekt berechnet wird**
   - Prüfe ob die Summe über das gesamte Jahr berechnet wird, nicht nur über die angezeigten Daten

3. **Prüfe ob Materialverbrauch korrekt aus `production_logs` gelesen wird**
   - Prüfe ob `material_calculations.py` die `material_verbrauch` Spalte korrekt verwendet

4. **Prüfe ob es Tage gibt, die nicht erfasst werden**
   - Prüfe ob alle 365 Tage in `production_logs` vorhanden sind
   - Prüfe ob Wochenenden/Feiertage erfasst werden

---

**Status:** 🔍 **ANALYSE LÄUFT**
