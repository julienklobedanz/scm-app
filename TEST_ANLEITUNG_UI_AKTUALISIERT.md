# Test-Anleitung UI - Aktualisiert für Defensive Fixes

**Datum:** 27.01.2026  
**Status:** Nach Kollegen-Feedback - System funktioniert aktuell stabil  
**Ziel:** Tests für defensive Fixes und langfristige Stabilität

---

## ⚠️ WICHTIG: Aktueller Status

**Kollege hat bestätigt:**
- ✅ System funktioniert aktuell stabil
- ✅ Keine Unterschiede bei Neuladen (getestet)
- ✅ Neue Material-Logik funktioniert

**Warum funktioniert es aktuell:**
- Python 3.7+ garantiert stabile Dict-Reihenfolge
- `MasterData.BOM` ist statisch definiert → immer dieselbe Reihenfolge
- Neue Material-Logik eliminiert Inkonsistenzen

**Warum defensive Fixes trotzdem sinnvoll sind:**
- Langfristige Stabilität auch bei Code-Änderungen
- Garantiert deterministisches Verhalten
- Verhindert Probleme bei dynamischem Laden oder Refactoring

---

## 📋 Test-Reihenfolge

### PHASE 0: Basis-Tests (Vor Fixes - Bestätigung aktueller Stabilität)

#### Test 0.1: Aktuelle Stabilität bestätigen
**Ziel:** Bestätigen dass System aktuell stabil funktioniert (wie Kollege sagt)

**Schritte:**
1. App starten (Streamlit)
2. Navigiere zu **"6 Produktion"**
3. Notiere für **"MTB Extreme"** die Werte für:
   - **03.04.2027** - "in Produktion" (tatsächliche PM)
   - **04.04.2027** - "in Produktion" (tatsächliche PM)
4. **Seite 5x neu laden** (F5)
5. Prüfe ob Werte identisch bleiben

**Erwartetes Ergebnis:**
- ✅ **AKTUELL:** Werte sollten identisch sein (Kollege hat es bestätigt)
- ✅ **NACH FIXES:** Werte sollten weiterhin identisch sein

**Zu dokumentieren:**
- Liste aller Werte bei jedem Neuladen
- Bestätigung dass alle identisch sind

---

#### Test 0.2: Produktreihenfolge prüfen
**Ziel:** Bestätigen dass Produktreihenfolge aktuell stabil ist

**Schritte:**
1. App starten
2. Öffne Browser-Konsole (F12)
3. Führe aus (oder prüfe in Python-Code):
   ```python
   # Prüfe ob Reihenfolge stabil ist
   from config.master_data import MasterData
   products_1 = list(MasterData.BOM.keys())
   products_2 = list(MasterData.BOM.keys())
   products_3 = list(MasterData.BOM.keys())
   print(products_1 == products_2 == products_3)  # Sollte True sein
   ```

**Erwartetes Ergebnis:**
- ✅ **AKTUELL:** Alle drei Listen sollten identisch sein
- ✅ **NACH FIXES:** Sollte weiterhin identisch sein (aber jetzt garantiert durch `sorted()`)

**Zu dokumentieren:**
- Aktuelle Reihenfolge
- Bestätigung dass stabil

---

### PHASE 1: Tests nach defensiven Fixes

#### Test 1.1: Produktreihenfolge ist garantiert sortiert
**Ziel:** Prüfen ob `sorted()` verwendet wird

**Schritte:**
1. **NACH FIXES:** App starten
2. Prüfe Code-Stellen:
   - `ui/production_calculations.py` Zeile 119: Sollte `sorted(MasterData.BOM.keys())` sein
   - `simulation/production_planner.py` Zeile 180: Sollte `sorted(...)` sein
3. Prüfe ob Reihenfolge alphabetisch sortiert ist:
   ```python
   from config.master_data import MasterData
   products = sorted(MasterData.BOM.keys())
   # Sollte sein: ['MTB Allrounder', 'MTB Competition', 'MTB Downhill', 
   #               'MTB Extreme', 'MTB Freeride', 'MTB Marathon', 
   #               'MTB Performance', 'MTB Trail']
   ```

**Erwartetes Ergebnis:**
- ✅ Produkte sollten alphabetisch sortiert sein
- ✅ Reihenfolge sollte garantiert deterministisch sein

**Zu dokumentieren:**
- Aktuelle Reihenfolge (sollte alphabetisch sein)
- Bestätigung dass `sorted()` verwendet wird

---

#### Test 1.2: Determinismus nach Fixes
**Ziel:** Prüfen ob Werte nach Fixes weiterhin stabil sind

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"6 Produktion"**
3. Notiere für **"MTB Extreme"** am **03.04.2027**:
   - "in Produktion" (tatsächliche PM)
4. **10x hintereinander neu laden** (F5)
5. Prüfe ob alle Werte identisch sind

**Erwartetes Ergebnis:**
- ✅ Alle 10 Werte sollten **exakt identisch** sein
- ✅ Keine Variationen

**Zu dokumentieren:**
- Liste aller 10 Werte
- Bestätigung dass alle identisch sind

---

#### Test 1.3: Konvergenz-Check funktioniert
**Ziel:** Prüfen ob Konvergenz-Check implementiert ist

**Schritte:**
1. **NACH FIXES:** App starten
2. Prüfe Code in `ui/page_initialization.py`:
   - Sollte Konvergenz-Check enthalten
   - Sollte max_iterations haben (z.B. 5)
   - Sollte prüfen ob Werte sich ändern
3. Aktiviere Debug-Logging (falls vorhanden) um Iterationen zu sehen

**Erwartetes Ergebnis:**
- ✅ Konvergenz-Check sollte vorhanden sein
- ✅ Iterationen sollten stoppen wenn Werte stabil sind
- ✅ Max. 5 Iterationen sollten ausreichen

**Zu dokumentieren:**
- Anzahl der Iterationen die durchgeführt wurden
- Bestätigung dass Konvergenz erreicht wurde

---

#### Test 1.4: Konvergenz bei verschiedenen Szenarien
**Ziel:** Prüfen ob Konvergenz auch bei verschiedenen Szenarien funktioniert

**Schritte:**
1. **NACH FIXES:** App starten
2. Teste verschiedene Szenarien:
   - **Szenario 1:** Standard (keine Szenarien aktiv)
   - **Szenario 2:** Marketing-Kampagne aktiviert
   - **Szenario 3:** Wasserschaden aktiviert
   - **Szenario 4:** Mehrere Szenarien gleichzeitig
3. Prüfe für jedes Szenario ob Konvergenz erreicht wird

**Erwartetes Ergebnis:**
- ✅ Alle Szenarien sollten konvergieren
- ✅ Max. 5 Iterationen sollten ausreichen
- ✅ Werte sollten stabil sein

**Zu dokumentieren:**
- Anzahl Iterationen pro Szenario
- Bestätigung dass alle konvergieren

---

### PHASE 2: Parameter-Tests (Nach Fixes)

#### Test 2.1: `total_volume` Änderung mit Cache-Invalidierung
**Ziel:** Prüfen ob Cache invalidiert wird

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"8 Stammdaten"**
3. Notiere aktuellen Wert von **"Gesamtvolumen"** (sollte 370000 sein)
4. Notiere Produktionswerte auf **"6 Produktion"** für **"MTB Extreme"** am **03.04.2027**
5. Gehe zurück zu **"8 Stammdaten"**
6. Ändere **"Gesamtvolumen"** auf **400000**
7. Navigiere zu **"6 Produktion"**
8. Prüfe ob Werte sich geändert haben

**Erwartetes Ergebnis:**
- ✅ **NACH FIXES:** Werte sollten sich **sofort** ändern
- ✅ Cache sollte invalidiert werden
- ✅ `yearly_volume` sollte synchronisiert sein

**Zu prüfen:**
- Werte auf "6 Produktion"
- Werte auf "2 Volumenplanung"
- Werte auf "1 Reporting"
- `st.session_state.yearly_volume` sollte 400000 sein

**Zu dokumentieren:**
- Werte vor Änderung
- Werte nach Änderung
- Bestätigung dass Cache invalidiert wurde

---

#### Test 2.2: `yearly_volume` Synchronisation
**Ziel:** Prüfen ob `yearly_volume` mit `total_volume` synchronisiert ist

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"8 Stammdaten"**
3. Ändere **"Gesamtvolumen"** auf **450000**
4. Prüfe ob `st.session_state.yearly_volume` auch 450000 ist

**Erwartetes Ergebnis:**
- ✅ `yearly_volume` sollte automatisch auf 450000 gesetzt werden
- ✅ Beide Werte sollten identisch sein

**Zu dokumentieren:**
- Wert von `total_volume`
- Wert von `yearly_volume`
- Bestätigung dass synchronisiert

---

#### Test 2.3: Cache-Invalidierung bei verschiedenen Parametern
**Ziel:** Prüfen ob Cache bei verschiedenen Parameteränderungen invalidiert wird

**Schritte:**
1. **NACH FIXES:** App starten
2. Teste verschiedene Parameter:
   - **Test 1:** `total_volume` ändern
   - **Test 2:** `capacity_per_hour` ändern
   - **Test 3:** `working_hours_per_shift` ändern
3. Für jeden Parameter:
   - Notiere Werte vor Änderung
   - Ändere Parameter
   - Prüfe ob Werte sich ändern

**Erwartetes Ergebnis:**
- ✅ Alle Parameteränderungen sollten Cache invalidierten
- ✅ Werte sollten sich sofort ändern

**Zu dokumentieren:**
- Welche Parameter getestet wurden
- Ob Cache invalidiert wurde
- Ob Werte sich geändert haben

---

### PHASE 3: Robustheit-Tests (Nach Fixes)

#### Test 3.1: Extreme Parameterwerte
**Ziel:** Prüfen ob System bei extremen Werten stabil bleibt

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"8 Stammdaten"**
3. Teste verschiedene extreme Werte:
   - **Test 1:** `total_volume` = 1000000 (sehr hoch)
   - **Test 2:** `total_volume` = 100000 (sehr niedrig)
   - **Test 3:** `capacity_per_hour` = 500 (sehr hoch)
   - **Test 4:** `capacity_per_hour` = 10 (sehr niedrig)
4. Für jeden Wert:
   - Prüfe ob Berechnungen funktionieren
   - Prüfe ob keine Fehler auftreten
   - Prüfe ob Werte plausibel sind

**Erwartetes Ergebnis:**
- ✅ System sollte nicht abstürzen
- ✅ Werte sollten plausibel sein
- ✅ Keine Division durch Null

**Zu dokumentieren:**
- Welche Werte getestet wurden
- Ob Fehler aufgetreten sind
- Ob Werte plausibel sind

---

#### Test 3.2: Mehrfache Parameteränderungen
**Ziel:** Prüfen ob System bei mehrfachen Änderungen stabil bleibt

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"8 Stammdaten"**
3. Ändere Parameter mehrfach hintereinander:
   - `total_volume`: 370000 → 400000 → 350000 → 370000
   - `capacity_per_hour`: 130 → 150 → 120 → 130
4. Nach jeder Änderung:
   - Prüfe ob Werte korrekt sind
   - Prüfe ob Cache invalidiert wurde

**Erwartetes Ergebnis:**
- ✅ System sollte stabil bleiben
- ✅ Werte sollten korrekt sein
- ✅ Cache sollte immer invalidiert werden

**Zu dokumentieren:**
- Sequenz der Änderungen
- Werte nach jeder Änderung
- Bestätigung dass stabil

---

### PHASE 4: Konsistenz-Tests (Nach Fixes)

#### Test 4.1: Produktion ↔ Material Konsistenz
**Ziel:** Prüfen ob Produktionswerte und Materialbestände konsistent sind

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"6 Produktion"**
3. Notiere für **"MTB Extreme"** am **03.04.2027**:
   - "tatsächliche PM"
   - "material_verbrauch" (falls sichtbar)
4. Navigiere zu **"5 Materiallager"**
5. Prüfe ob Materialverbrauch konsistent ist

**Erwartetes Ergebnis:**
- ✅ Materialverbrauch sollte mit Produktionsmenge übereinstimmen
- ✅ Bestand sollte korrekt reduziert werden

**Zu prüfen:**
- Sattel-Verbrauch pro Produkt
- Bestand morgens vs. abends
- Inbound vs. Verbrauch

---

#### Test 4.2: Inbound ↔ Material Konsistenz
**Ziel:** Prüfen ob Inbound-Tabelle und Materiallager konsistent sind

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"4 Inbound"**
3. Notiere Ankunftsmenge für **"Spark"** am **15.03.2027**
4. Navigiere zu **"5 Materiallager"**
5. Prüfe ob Bestand korrekt erhöht wurde

**Erwartetes Ergebnis:**
- ✅ Inbound-Menge sollte im Materiallager sichtbar sein
- ✅ Bestand sollte korrekt erhöht werden

**Zu prüfen:**
- Ankunftsdatum
- Ankunftsmenge
- Bestand nach Ankunft

---

#### Test 4.3: Volumenplanung ↔ Produktion Konsistenz
**Ziel:** Prüfen ob Nachfrage und Produktion konsistent sind

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu **"2 Volumenplanung"**
3. Notiere Nachfrage für **"MTB Extreme"** am **03.04.2027**
4. Navigiere zu **"6 Produktion"**
5. Prüfe ob Produktion mit Nachfrage übereinstimmt

**Erwartetes Ergebnis:**
- ✅ Produktion sollte Nachfrage erfüllen (wenn Material verfügbar)
- ✅ Backlog sollte korrekt berechnet werden

**Zu prüfen:**
- Nachfrage vs. Produktion
- Backlog-Entwicklung
- Service Level

---

### PHASE 5: Szenario-Tests (Nach Fixes)

#### Test 5.1: Marketing-Szenario mit Konvergenz
**Ziel:** Prüfen ob Marketing-Szenario korrekt angewendet wird und konvergiert

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu Sidebar (Szenarien)
3. Aktiviere **"Marketing-Kampagne"**
4. Setze Start-Tag: **50**, End-Tag: **60**, Faktor: **1.5**
5. Navigiere zu **"2 Volumenplanung"**
6. Prüfe ob Nachfrage erhöht wurde (Tag 50-60)
7. Navigiere zu **"6 Produktion"**
8. Prüfe ob Produktion erhöht wurde
9. Prüfe ob Konvergenz erreicht wurde

**Erwartetes Ergebnis:**
- ✅ Nachfrage sollte um 50% erhöht sein (Tag 50-60)
- ✅ Produktion sollte entsprechend erhöht sein
- ✅ Cache sollte invalidiert werden
- ✅ Konvergenz sollte erreicht werden

**Zu prüfen:**
- Nachfrage-Werte Tag 50-60
- Produktions-Werte Tag 50-60
- Cache-Invalidierung
- Anzahl Iterationen

---

#### Test 5.2: Wasserschaden-Szenario mit Konvergenz
**Ziel:** Prüfen ob Wasserschaden korrekt angewendet wird und konvergiert

**Schritte:**
1. **NACH FIXES:** App starten
2. Navigiere zu Sidebar (Szenarien)
3. Aktiviere **"Wasserschaden im Materiallager"**
4. Setze Datum: **100** (Tag 100)
5. Navigiere zu **"5 Materiallager"**
6. Prüfe ob Bestand am Tag 100 auf 0 gesetzt wurde
7. Navigiere zu **"6 Produktion"**
8. Prüfe ob Produktion beeinflusst wurde
9. Prüfe ob Konvergenz erreicht wurde

**Erwartetes Ergebnis:**
- ✅ Bestand sollte am Tag 100 auf 0 gesetzt werden
- ✅ Produktion sollte beeinflusst werden
- ✅ Konvergenz sollte erreicht werden

**Zu prüfen:**
- Bestand morgens Tag 100
- Bestand abends Tag 100
- Produktion Tag 100
- Anzahl Iterationen

---

## 📊 Test-Protokoll

### Für jeden Test dokumentieren:

1. **Test-ID:** (z.B. TEST-1.1)
2. **Datum/Zeit:** 
3. **Tester:**
4. **Status:** Vor Fixes / Nach Fixes
5. **Erwartetes Ergebnis:**
6. **Tatsächliches Ergebnis:**
7. **Unterschiede:**
8. **Screenshots:** (falls relevant)
9. **Fehler-Logs:** (falls vorhanden)
10. **Bestätigung:** ✅ Bestanden / ❌ Fehlgeschlagen

### Beispiel-Protokoll:

```
TEST-0.1: Aktuelle Stabilität bestätigen
Datum: 27.01.2026, 15:00
Tester: [Name]
Status: Vor Fixes

Erwartetes Ergebnis: Werte sollten bei Neuladen identisch sein (Kollege bestätigt)
Tatsächliches Ergebnis: 
- 1. Neuladen: MTB Extreme 03.04.2027 = 1799
- 2. Neuladen: MTB Extreme 03.04.2027 = 1799
- 3. Neuladen: MTB Extreme 03.04.2027 = 1799
- 4. Neuladen: MTB Extreme 03.04.2027 = 1799
- 5. Neuladen: MTB Extreme 03.04.2027 = 1799

Unterschiede: Keine - alle Werte identisch
Fehler-Logs: Keine
Bestätigung: ✅ Bestanden - System ist stabil
```

---

## 🎯 Prioritäten

### Sofort testen (🔴) - Vor Fixes:
1. **TEST-0.1:** Aktuelle Stabilität bestätigen
2. **TEST-0.2:** Produktreihenfolge prüfen

### Sofort testen (🔴) - Nach Fixes:
3. **TEST-1.1:** Produktreihenfolge ist garantiert sortiert
4. **TEST-1.2:** Determinismus nach Fixes
5. **TEST-1.3:** Konvergenz-Check funktioniert
6. **TEST-2.1:** `total_volume` Änderung mit Cache-Invalidierung

### Bald testen (🟡) - Nach Fixes:
7. **TEST-1.4:** Konvergenz bei verschiedenen Szenarien
8. **TEST-2.2:** `yearly_volume` Synchronisation
9. **TEST-2.3:** Cache-Invalidierung bei verschiedenen Parametern
10. **TEST-4.1:** Produktion ↔ Material Konsistenz

### Später testen (🟢) - Nach Fixes:
11. **TEST-3.1:** Extreme Parameterwerte
12. **TEST-3.2:** Mehrfache Parameteränderungen
13. **TEST-4.2:** Inbound ↔ Material Konsistenz
14. **TEST-4.3:** Volumenplanung ↔ Produktion Konsistenz
15. **TEST-5.1:** Marketing-Szenario mit Konvergenz
16. **TEST-5.2:** Wasserschaden-Szenario mit Konvergenz

---

## 📝 Zusammenfassung der zu testenden Bereiche

### Kritische Bereiche (Nach Fixes):
1. ✅ **Determinismus:** Werte sollten bei Neuladen identisch sein (garantiert durch `sorted()`)
2. ✅ **Konvergenz:** Iterative Berechnung sollte konvergieren
3. ✅ **Parameter-Synchronisation:** `yearly_volume` und `total_volume` sollten synchronisiert sein
4. ✅ **Cache-Invalidierung:** Parameteränderungen sollten Cache invalidierten
5. ✅ **Konsistenz:** Produktion, Material, Inbound sollten konsistent sein

### Zu prüfende Seiten:
1. **"1 Reporting"** - SCOR-Metriken
2. **"2 Volumenplanung"** - Nachfrage-Berechnung
3. **"3 Lieferant China"** - Bestellungen
4. **"4 Inbound"** - Ankunfts-Tabelle
5. **"5 Materiallager"** - Materialbestände
6. **"6 Produktion"** - Produktions-Logs
7. **"7 Fertigproduktelager"** - Endprodukt-Bestände
8. **"8 Stammdaten"** - Parameter-Einstellungen

---

## ⚠️ Wichtige Hinweise

### Vor Fixes:
- System funktioniert aktuell stabil (Kollege bestätigt)
- Tests sollten zeigen dass es bereits funktioniert

### Nach Fixes:
- Tests sollten zeigen dass es weiterhin funktioniert
- Tests sollten zeigen dass defensive Fixes greifen
- Tests sollten zeigen dass System robuster ist

### Was zu dokumentieren ist:
- Alle Werte bei jedem Neuladen
- Anzahl Iterationen bei Konvergenz-Check
- Cache-Invalidierung bei Parameteränderungen
- Synchronisation von `yearly_volume` und `total_volume`

---

**Status:** ✅ Test-Anleitung aktualisiert  
**Nächster Schritt:** Tests durchführen, dann Fixes implementieren
