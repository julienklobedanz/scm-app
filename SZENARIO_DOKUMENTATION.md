# Szenario-Dokumentation: Was man wo sehen kann

**Datum:** 27.01.2026  
**Ziel:** Dokumentation aller Szenarien mit konkreten Prüfpunkten und erwarteten Ergebnissen

---

## 📋 Übersicht

Diese Dokumentation beschreibt:
- **Was** man bei jedem Szenario sehen sollte
- **Wo** man es prüfen kann (welche Seite/Ansicht)
- **Wie** die Werte aussehen sollten
- **Welche Folgen** in nachfolgenden Ansichten sichtbar sind

---

## 🎯 Szenario 1: Marketing-Kampagne

### Konfiguration:
- **Start-Datum:** 19.02.2027 (Tag 50)
- **End-Datum:** 01.03.2027 (Tag 60)
- **Faktor:** 1.5 (50% Erhöhung)

---

### 1. "8 Stammdaten" - Konvergenz-Check

**Was prüfen:**
- Grüne Info-Box oben auf der Seite

**Erwartetes Ergebnis:**
- ✅ "Konvergenz-Check: 2 Iteration(en) durchgeführt, Konvergenz erreicht!"
- ✅ Max. 3 Iterationen (meist 2)

**Was bedeutet das:**
- System hat iterativ berechnet und konvergiert
- Marketing-Effekt wurde korrekt verarbeitet

---

### 2. "2 Volumenplanung" - Nachfrage-Erhöhung

**Was prüfen:**
- Tabelle "Volumenplanung täglich"
- Suche nach Tag 22.02.2027 (Tag 52, innerhalb Marketing-Zeitraum)
- Prüfe für "MTB Downhill" (oder andere Produkte)

**Erwartetes Ergebnis:**
- **Ohne Marketing:** "Nachfrage" = z.B. 111
- **Mit Marketing:** "Nachfrage" = z.B. 166 (1.5x)
- ✅ Tag 50-60 sollten **1.5x höher** sein als Tag 49

**Wo genau:**
- Spalte "Nachfrage" in der Tabelle
- Vergleich Tag 49 (vor Marketing) vs. Tag 50-60 (mit Marketing)

**Folgen:**
- Erhöhte Nachfrage führt zu erhöhter Produktion (siehe "6 Produktion")

---

### 3. "6 Produktion" - Produktions-Erhöhung

**Was prüfen:**
- Tabelle für "MTB Downhill" (oder andere Produkte)
- Suche nach Tag 22.02.2027 (Tag 52)
- Prüfe "geplante PM" und "tatsächliche PM"

**Erwartetes Ergebnis:**
- **Ohne Marketing:** "geplante PM" = z.B. 1500, "tatsächliche PM" = z.B. 166
- **Mit Marketing:** "geplante PM" = z.B. 2291, "tatsächliche PM" = z.B. 166
- ✅ "geplante PM" sollte erhöht sein (1.5x)
- ⚠️ "tatsächliche PM" kann begrenzt sein durch Materialverfügbarkeit

**Wo genau:**
- Spalten "geplante PM" und "tatsächliche PM"
- Material-Spalte (z.B. "Fizik Tundra") zeigt benötigtes Material

**Folgen:**
- Erhöhte Produktion führt zu erhöhtem Materialverbrauch (siehe "5 Materiallager")
- Backlog kann entstehen wenn Material knapp ist

---

### 4. "3 Lieferant China" - Bestellungen

**Was prüfen:**
- Tabelle für "Fizik Tundra" (oder andere Sattel-Typen)
- Suche nach Bestellungen erstellt um 01.01.2027 - 02.01.2027
- Prüfe "Bestelleingang" und "Freigegebene Bestellungen"

**Erwartetes Ergebnis:**
- ⚠️ **Wahrscheinlich KEINE Erhöhung** (weil Bestellungen vor Marketing erstellt wurden)
- Bestellungen werden am Tag 0-1 erstellt (vor Marketing am Tag 50)
- Vorlaufzeit: 49 Tage

**Wo genau:**
- Spalten "Bestelleingang" und "Freigegebene Bestellungen"
- Datum-Spalte zeigt Bestelltag

**Folgen:**
- Wenn keine Erhöhung: Materialmangel möglich (siehe "5 Materiallager")

---

### 5. "4 Inbound" - Ankünfte

**Was prüfen:**
- Tabelle zeigt alle Ankünfte
- Suche nach Ankünften ab 11.01.2027
- Prüfe "Menge Gesamt" und Spalten für einzelne Sattel-Typen

**Erwartetes Ergebnis:**
- **Ohne Marketing:** Tag 11.01: 2000, Tag 12.01: 1500, Tag 13.01: 1000...
- **Mit Marketing:** Tag 11.01: 2500 (+500), Tag 12.01: 2000 (+500), Tag 13.01: 1500 (+500)...
- ✅ **Gesamt zusätzlich:** +4500 auf 374000

**Wo genau:**
- Spalte "Menge Gesamt" zeigt Gesamtmenge pro Ankunft
- Spalten für einzelne Sattel-Typen (z.B. "Fizik Tundra") zeigen Verteilung

**Warum erhöht:**
- Bestellungen wurden erhöht (wenn Marketing früh genug aktiviert)
- Oder: System reagiert auf erhöhte Nachfrage

**Folgen:**
- Erhöhte Ankünfte führen zu erhöhtem Lagerzugang (siehe "5 Materiallager")

---

### 6. "5 Materiallager" - Materialbestände

**Was prüfen:**
- Tabelle für "Fizik Tundra" (oder andere Sattel-Typen)
- Suche nach Tag 22.02.2027 (Tag 52)
- Prüfe "Lagerzugang", "Lagerabgang", "Bestand morgens", "Bestand abends"

**Erwartetes Ergebnis:**
- **Ohne Marketing:** 
  - Lagerzugang: z.B. 1620
  - Lagerabgang: z.B. 421
- **Mit Marketing:**
  - Lagerzugang: z.B. 2291 (1.41x)
  - Lagerabgang: z.B. 583 (1.38x)
- ⚠️ **Nicht genau 1.5x** wegen kumulierter Effekte (Tag 1-49 ohne Marketing)

**Wo genau:**
- Spalten "Lagerzugang" und "Lagerabgang"
- Spalten "Bestand morgens" und "Bestand abends"

**Erklärung:**
- Materiallager summiert alle Tage seit Jahresbeginn
- Marketing wirkt nur an Tag 50-60 (11 Tage)
- Verhältnis ist daher nicht genau 1.5x

**Folgen:**
- Erhöhter Materialverbrauch führt zu schnellerem Bestandsabbau
- Materialmangel möglich wenn keine zusätzlichen Bestellungen

---

### 7. "7 Fertigproduktelager" - Endprodukt-Bestände

**Was prüfen:**
- Tabelle für "MTB Downhill" (oder andere Produkte)
- Suche nach Tag 22.02.2027 (Tag 52)
- Prüfe "Lagerzugang", "Lagerabgang", "Bestand"

**Erwartetes Ergebnis:**
- ✅ Lagerzugang sollte erhöht sein (mehr Produktion)
- ✅ Lagerabgang sollte erhöht sein (mehr Nachfrage)
- Bestand kann steigen oder sinken (je nach Verhältnis)

**Wo genau:**
- Spalten "Lagerzugang" und "Lagerabgang"
- Spalte "Bestand" zeigt aktuellen Bestand

**Folgen:**
- Erhöhte Produktion führt zu erhöhtem Lagerzugang
- Erhöhte Nachfrage führt zu erhöhtem Lagerabgang

---

## 🎯 Szenario 2: Wasserschaden im Materiallager

### Konfiguration:
- **Datum:** 22.02.2027 (Tag 52)
- **Betroffene Komponente:** Sättel (alle Typen)

---

### 1. "8 Stammdaten" - Konvergenz-Check

**Was prüfen:**
- Grüne Info-Box oben auf der Seite

**Erwartetes Ergebnis:**
- ✅ "Konvergenz-Check: 2 Iteration(en) durchgeführt, Konvergenz erreicht!"
- ✅ Max. 3 Iterationen (meist 2)

**Was bedeutet das:**
- System hat iterativ berechnet und konvergiert
- Wasserschaden wurde korrekt verarbeitet

---

### 2. "5 Materiallager" - Materialverlust

**Was prüfen:**
- Tabelle für "Fizik Tundra" (oder andere Sattel-Typen)
- Suche nach Tag 22.02.2027 (Tag 52, Wasserschaden-Tag)
- Prüfe "Lagerzugang", "Lagerabgang", "Verlustmenge", "Bestand morgens", "Bestand abends"

**Erwartetes Ergebnis:**
- **Tag 21.02.2027 (vor Wasserschaden):**
  - Bestand morgens: z.B. 3145
  - Bestand abends: z.B. 2724
- **Tag 22.02.2027 (Wasserschaden):**
  - Lagerzugang: z.B. 421 (normal)
  - **Verlustmenge:** z.B. 3145 (entspricht Bestand morgens vor Schaden)
  - **Lagerabgang:** 0 (keine Produktion möglich)
  - **Bestand morgens:** 0 (nach Wasserschaden)
  - **Bestand abends:** 0 (nach Wasserschaden)
- **Tag 23.02.2027 (nach Wasserschaden):**
  - Bestand morgens: 0 (startet bei 0)
  - Bestand abends: kann wieder steigen durch neue Ankünfte

**Wo genau:**
- Spalte "Verlustmenge" zeigt verlorene Menge
- Spalten "Bestand morgens" und "Bestand abends" zeigen Bestand
- Spalte "Lagerabgang" zeigt Verbrauch (sollte 0 sein)

**Kumulierte Berechnung:**
- **Verlustmenge:** = Bestand morgens vor Wasserschaden
- **Kumulierter Bestand abends:** = Summe aller Zugänge - Summe aller Abgänge - Verlustmenge
- Beispiel: 245154 (ohne Verlust) - 3145 (Verlust) = 242009 ✅

**Folgen:**
- Materialmangel führt zu Produktionsstopp (siehe "6 Produktion")

---

### 3. "6 Produktion" - Produktionsstopp

**Was prüfen:**
- Tabelle für "MTB Extreme" (verwendet "Spark" Sattel)
- Suche nach Tag 22.02.2027 (Tag 52, Wasserschaden-Tag)
- Prüfe "geplante PM" und "tatsächliche PM"

**Erwartetes Ergebnis:**
- **Tag 21.02.2027 (vor Wasserschaden):**
  - geplante PM: z.B. 1723
  - tatsächliche PM: z.B. 1723
- **Tag 22.02.2027 (Wasserschaden):**
  - geplante PM: z.B. 1723 (gleich, Nachfrage ändert sich nicht)
  - **tatsächliche PM:** 0 (keine Produktion wegen Materialmangel)
- **Tag 23.02.2027 (nach Wasserschaden):**
  - geplante PM: z.B. 1723
  - tatsächliche PM: kann wieder steigen (wenn Material wieder verfügbar)

**Wo genau:**
- Spalten "geplante PM" und "tatsächliche PM"
- Material-Spalte (z.B. "Spark") zeigt verfügbares Material (sollte 0 sein)

**Was bedeutet das:**
- ✅ **System reagiert dynamisch:** Produktion wird auf 0 reduziert wenn Material fehlt
- ✅ **Keine "Geisterproduktion":** System produziert nicht ohne Material
- ✅ **Plan bleibt gleich:** Geplante PM ändert sich nicht (Nachfrage bleibt gleich)

**Folgen:**
- Produktionsstopp führt zu Backlog (siehe "6 Produktion" - Backlog-Spalte)
- Keine neuen Endprodukte (siehe "7 Fertigproduktelager")

---

### 4. "7 Fertigproduktelager" - Endprodukt-Bestände

**Was prüfen:**
- Tabelle für "MTB Extreme" (oder andere Produkte)
- Suche nach Tag 22.02.2027 (Tag 52, Wasserschaden-Tag)
- Prüfe "Lagerzugang", "Lagerabgang", "Bestand"

**Erwartetes Ergebnis:**
- **Tag 22.02.2027 (Wasserschaden):**
  - **Lagerzugang:** 0 (keine Produktion)
  - **Lagerabgang:** kann > 0 sein (Nachfrage bleibt bestehen)
  - **Bestand:** sinkt (mehr Abgang als Zugang)
- **Tag 23.02.2027 (nach Wasserschaden):**
  - Lagerzugang: kann wieder steigen (wenn Produktion wieder läuft)

**Wo genau:**
- Spalten "Lagerzugang" und "Lagerabgang"
- Spalte "Bestand" zeigt aktuellen Bestand

**Was bedeutet das:**
- ✅ **0er-Zeile bei Lagerzugang:** Keine neuen Endprodukte produziert
- ✅ **Lagerabgang kann > 0 sein:** Nachfrage wird weiterhin bedient (aus Bestand)
- ✅ **Bestand sinkt:** Mehr Abgang als Zugang

**Folgen:**
- Bestand kann auf 0 fallen (wenn keine Produktion mehr möglich)

---

### 5. "3 Lieferant China" - Bestellungen

**Was prüfen:**
- Tabelle für "Fizik Tundra" (oder andere Sattel-Typen)
- Prüfe ob Bestellungen nach Wasserschaden erhöht werden

**Erwartetes Ergebnis:**
- ⚠️ **Wahrscheinlich KEINE automatische Erhöhung**
- Bestellungen werden basierend auf prognostizierter Nachfrage erstellt
- Wasserschaden ist unvorhersehbar → keine automatische Reaktion

**Wo genau:**
- Spalten "Bestelleingang" und "Freigegebene Bestellungen"
- Datum-Spalte zeigt Bestelltag

**Was bedeutet das:**
- System reagiert **nicht proaktiv** auf Wasserschaden
- Bestellungen werden **nicht automatisch erhöht**
- System reagiert **reaktiv** durch reduzierte Produktion

---

### 6. "4 Inbound" - Ankünfte

**Was prüfen:**
- Tabelle zeigt alle Ankünfte
- Prüfe ob Ankünfte nach Wasserschaden erhöht werden

**Erwartetes Ergebnis:**
- ⚠️ **Wahrscheinlich KEINE Erhöhung**
- Ankünfte basieren auf Bestellungen (die nicht erhöht wurden)
- Wasserschaden führt nicht zu zusätzlichen Bestellungen

**Wo genau:**
- Spalte "Menge Gesamt" zeigt Gesamtmenge pro Ankunft
- Spalten für einzelne Sattel-Typen zeigen Verteilung

**Was bedeutet das:**
- System reagiert **nicht proaktiv** auf Wasserschaden
- Ankünfte bleiben normal
- System reagiert **reaktiv** durch reduzierte Produktion

---

## 🔍 Dynamische Reaktion: Ist das implementiert?

### ✅ **JA - System reagiert dynamisch!**

**Wie funktioniert es:**

1. **Wasserschaden setzt Bestand auf 0:**
   - `ui/production_calculations.py` Zeile 449-451: `running_stock[s] = 0.0`
   - `ui/material_calculations.py` Zeile 184-185: `stock_morning[s] = 0.0`

2. **Produktion prüft Materialverfügbarkeit:**
   - `ui/production_calculations.py` Zeile 164: `minimal = max(0.0, saddle_available)`
   - `simulation/production_planner.py` Zeile 237: `minimal = max(0.0, saddle_available)`

3. **Produktion wird auf verfügbares Material begrenzt:**
   - `ui/production_calculations.py` Zeile 169-170: `scheduled_qty = min(demand, proportional, minimal)`
   - Wenn `minimal = 0` → `scheduled_qty = 0`

4. **Backlog entsteht:**
   - `ui/production_calculations.py` Zeile 516-519: Backlog wird erhöht wenn Produktion < Nachfrage

**Ergebnis:**
- ✅ **System produziert nicht ohne Material** (keine "Geisterproduktion")
- ✅ **Produktion wird auf verfügbares Material begrenzt** (Clamping)
- ✅ **Backlog entsteht** wenn Material fehlt
- ✅ **System reagiert automatisch** auf Materialmangel

---

## 📊 Zusammenfassung: Was man wo sehen kann

### Marketing-Kampagne:

| Seite | Was prüfen | Erwartetes Ergebnis |
|-------|------------|---------------------|
| **8 Stammdaten** | Konvergenz-Check | 2-3 Iterationen, Konvergenz erreicht |
| **2 Volumenplanung** | Nachfrage Tag 50-60 | 1.5x höher als Tag 49 |
| **6 Produktion** | geplante PM Tag 50-60 | Erhöht (1.5x) |
| **4 Inbound** | Ankünfte ab 11.01.2027 | +500 pro Tag, +4500 gesamt |
| **5 Materiallager** | Lagerzugang/Abgang Tag 52 | Erhöht (1.41x, 1.38x) |
| **7 Fertigproduktelager** | Lagerzugang Tag 50-60 | Erhöht |

### Wasserschaden:

| Seite | Was prüfen | Erwartetes Ergebnis |
|-------|------------|---------------------|
| **8 Stammdaten** | Konvergenz-Check | 2-3 Iterationen, Konvergenz erreicht |
| **5 Materiallager** | Tag 22.02.2027 | Verlustmenge = Bestand morgens, Bestand = 0 |
| **6 Produktion** | tatsächliche PM Tag 22.02.2027 | 0 (keine Produktion) |
| **7 Fertigproduktelager** | Lagerzugang Tag 22.02.2027 | 0 (keine neuen Endprodukte) |
| **6 Produktion** | Backlog Tag 22.02.2027+ | Erhöht (Nachfrage bleibt, Produktion = 0) |

---

## 🎯 Test-Anleitung für Wasserschaden

### Schritt 1: Wasserschaden aktivieren
1. **Sidebar öffnen**
2. **Wähle "Wasserschaden im Materiallager"**
3. **Setze Datum:** 22.02.2027
4. **Klicke "Wasserschaden hinzufügen"**

### Schritt 2: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "Fizik Tundra" (oder andere Sattel-Typen):**
   - Verlustmenge = Bestand morgens vor Schaden ✅
   - Bestand morgens = 0 ✅
   - Bestand abends = 0 ✅
   - Lagerabgang = 0 ✅

### Schritt 3: Produktion prüfen
1. **Navigiere zu "6 Produktion"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "MTB Extreme" (verwendet "Spark" Sattel):**
   - geplante PM = gleich (Nachfrage ändert sich nicht) ✅
   - tatsächliche PM = 0 (keine Produktion) ✅
   - Backlog = erhöht (Nachfrage bleibt, Produktion = 0) ✅

### Schritt 4: Fertigproduktelager prüfen
1. **Navigiere zu "7 Fertigproduktelager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "MTB Extreme":**
   - Lagerzugang = 0 (keine neuen Endprodukte) ✅
   - Lagerabgang = kann > 0 sein (Nachfrage wird bedient) ✅
   - Bestand = sinkt ✅

---

**Status:** ✅ **DOKUMENTATION ERSTELLT**  
**Nächster Schritt:** Tests durchführen und Ergebnisse dokumentieren
