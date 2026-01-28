# Detaillierte Test-Anleitung für UI

**Datum:** 28.01.2026 (aktualisiert nach Session 27.01.2026)  
**Basierend auf:** Vollständige Fehleranalyse + Session-Zusammenfassung  
**Ziel:** Systematisches Testen aller kritischen Bereiche in der Oberfläche

---

## ✅ AKTUELLER STATUS (Stand: 27.01.2026)

**Nach gestriger Session wurden folgende Probleme behoben:**

1. ✅ **BEHOBEN:** Determinismus gewährleistet - `sorted()` für Produktreihenfolge implementiert
2. ✅ **BEHOBEN:** Konvergenz-Check implementiert - 2 Iterationen mit Prüfung
3. ✅ **BEHOBEN:** Wasserschaden-Logik korrigiert - `fertiggestellte PM` wird korrekt auf 0 gesetzt
4. ✅ **BEHOBEN:** Alle Konsistenz-Tests bestanden (TEST-3.1, TEST-3.2, TEST-3.3)

**Aktuelles Verhalten:**
- ✅ Werte sind bei Neuladen identisch (deterministisch)
- ✅ Produktreihenfolge ist garantiert alphabetisch sortiert
- ✅ Konvergenz-Check funktioniert (2 Iterationen)
- ✅ Konsistenz zwischen Produktion, Material, Inbound bestätigt

**Siehe auch:**
- `SESSION_ZUSAMMENFASSUNG_CHAT.md` - Vollständige Übersicht der gestrigen Session
- `TEST_ERGEBNISSE.md` - Alle Test-Ergebnisse (9/9 Tests bestanden)

---

## 📋 Test-Reihenfolge

### PHASE 1: Basis-Tests (Determinismus)

#### Test 1.1: Produktionswerte Determinismus
**Ziel:** Prüfen ob Produktionswerte bei Neuladen identisch sind

**Schritte:**
1. App starten (Streamlit)
2. Navigiere zu **"6 Produktion"**
3. Notiere für **"MTB Extreme"** die Werte für:
   - **03.04.2027** - "in Produktion" (tatsächliche PM)
   - **04.04.2027** - "in Produktion" (tatsächliche PM)
4. **Seite neu laden** (F5 oder Browser-Reload)
5. Prüfe ob Werte identisch sind

**Erwartetes Ergebnis:**
- ✅ **AKTUELL:** Werte sollten identisch sein (nach Fixes vom 27.01.2026)
- ✅ **BESTÄTIGT:** System ist deterministisch (siehe TEST_ERGEBNISSE.md)

**Zu prüfende Produkte:**
- MTB Extreme (03.04. und 04.04.)
- MTB Allrounder (verschiedene Tage)
- MTB Competition (verschiedene Tage)

**Dokumentation:**
- Notiere alle Unterschiede
- Notiere welche Produkte betroffen sind
- Notiere welche Tage betroffen sind

---

#### Test 1.2: Mehrfaches Neuladen
**Ziel:** Prüfen ob Werte nach mehrfachem Neuladen stabil bleiben

**Schritte:**
1. App starten
2. Navigiere zu **"6 Produktion"**
3. Notiere Werte für **"MTB Extreme"** am **03.04.2027**
4. **5x hintereinander neu laden** (F5)
5. Prüfe ob Werte identisch bleiben

**Erwartetes Ergebnis:**
- ✅ **AKTUELL:** Alle Werte sollten identisch sein (nach Fixes vom 27.01.2026)
- ✅ **BESTÄTIGT:** System ist stabil bei mehrfachem Neuladen (siehe TEST_ERGEBNISSE.md)

**Zu dokumentieren:**
- Liste aller unterschiedlichen Werte
- Anzahl der unterschiedlichen Werte
- Muster (oskillieren, zufällig, etc.)

---

### PHASE 2: Parameter-Tests

#### Test 2.1: `total_volume` Änderung
**Ziel:** Prüfen ob Änderung von `total_volume` Auswirkung hat

**Schritte:**
1. App starten
2. Navigiere zu **"8 Stammdaten"**
3. Notiere aktuellen Wert von **"Gesamtvolumen"** (sollte 370000 sein)
4. Notiere Produktionswerte auf **"6 Produktion"** für **"MTB Extreme"** am **03.04.2027**
5. Gehe zurück zu **"8 Stammdaten"**
6. Ändere **"Gesamtvolumen"** auf **400000**
7. Navigiere zu **"6 Produktion"**
8. Prüfe ob Werte sich geändert haben

**Erwartetes Ergebnis:**
- ⚠️ **ZU PRÜFEN:** Cache-Invalidierung bei Parameteränderungen (noch nicht getestet)
- ✅ **ZIEL:** Werte sollten sich sofort ändern

**Zu prüfen:**
- Werte auf "6 Produktion"
- Werte auf "2 Volumenplanung"
- Werte auf "1 Reporting"

**Nach Test:**
- App neu starten
- Prüfe ob Werte dann korrekt sind

---

#### Test 2.2: `yearly_volume` vs `total_volume` Konsistenz
**Ziel:** Prüfen ob beide Parameter synchronisiert sind

**Schritte:**
1. App starten
2. Navigiere zu **"8 Stammdaten"**
3. Notiere **"Gesamtvolumen"** Wert (aus `editable_global_config`)
4. Öffne Browser-Konsole (F12)
5. Führe aus: `window.parent.postMessage({type: 'streamlit:setComponentValue', value: null}, '*')`
6. Oder: Prüfe in Python-Code ob `st.session_state.yearly_volume` == `st.session_state.editable_global_config['total_volume']`

**Erwartetes Ergebnis:**
- ⚠️ **ZU PRÜFEN:** Synchronisation zwischen `yearly_volume` und `total_volume` (noch nicht getestet)
- ✅ **ZIEL:** Werte sollten identisch sein

**Zu dokumentieren:**
- Aktueller Wert von `yearly_volume`
- Aktueller Wert von `total_volume`
- Unterschied

---

#### Test 2.3: Cache-Invalidierung bei Parameteränderung
**Ziel:** Prüfen ob Cache invalidiert wird

**Schritte:**
1. App starten
2. Navigiere zu **"2 Volumenplanung"**
3. Notiere Nachfrage-Werte für **"MTB Extreme"** am **03.04.2027**
4. Navigiere zu **"8 Stammdaten"**
5. Ändere **"Gesamtvolumen"** auf **400000**
6. Navigiere zurück zu **"2 Volumenplanung"**
7. Prüfe ob Nachfrage-Werte sich geändert haben

**Erwartetes Ergebnis:**
- ⚠️ **ZU PRÜFEN:** Cache-Invalidierung bei Parameteränderungen (noch nicht getestet)
- ✅ **ZIEL:** Werte sollten sich sofort ändern

**Zu prüfen:**
- `volume_planning_cache_key` sollte sich ändern
- `production_logs_cache` sollte gelöscht werden
- `material_inventory_data` sollte gelöscht werden

---

### PHASE 3: Konsistenz-Tests

#### Test 3.1: Produktion ↔ Material Konsistenz
**Ziel:** Prüfen ob Produktionswerte und Materialbestände konsistent sind

**Schritte:**
1. App starten
2. Navigiere zu **"6 Produktion"**
3. Notiere für **"MTB Extreme"** am **03.04.2027**:
   - "tatsächliche PM"
   - "material_verbrauch" (falls sichtbar)
4. Navigiere zu **"5 Materiallager"**
5. Prüfe ob Materialverbrauch konsistent ist

**Erwartetes Ergebnis:**
- ✅ Materialverbrauch sollte mit Produktionsmenge übereinstimmen
- ✅ Bestand sollte korrekt reduziert werden
- ✅ **BESTÄTIGT:** TEST-3.1 bestanden (siehe TEST_ERGEBNISSE.md)

**Zu prüfen:**
- Sattel-Verbrauch pro Produkt
- Bestand morgens vs. abends
- Inbound vs. Verbrauch

---

#### Test 3.2: Inbound ↔ Material Konsistenz
**Ziel:** Prüfen ob Inbound-Tabelle und Materiallager konsistent sind

**Schritte:**
1. App starten
2. Navigiere zu **"4 Inbound"**
3. Notiere Ankunftsmenge für **"Spark"** am **15.03.2027**
4. Navigiere zu **"5 Materiallager"**
5. Prüfe ob Bestand korrekt erhöht wurde

**Erwartetes Ergebnis:**
- ✅ Inbound-Menge sollte im Materiallager sichtbar sein
- ✅ Bestand sollte korrekt erhöht werden
- ✅ **BESTÄTIGT:** TEST-3.2 bestanden (siehe TEST_ERGEBNISSE.md)

**Zu prüfen:**
- Ankunftsdatum
- Ankunftsmenge
- Bestand nach Ankunft

---

#### Test 3.3: Fertigproduktelager ↔ Produktion Konsistenz
**Ziel:** Prüfen ob fertiggestellte PM und Fertigproduktelager konsistent sind

**Schritte:**
1. App starten
2. Navigiere zu **"6 Produktion"**
3. Notiere `fertiggestellte PM` für **"MTB Marathon"** am **22.02.2027**
4. Navigiere zu **"7 Fertigproduktelager"**
5. Prüfe ob `Lagerzugang` am nächsten Tag mit `fertiggestellte PM` übereinstimmt

**Erwartetes Ergebnis:**
- ✅ Lagerzugang sollte mit fertiggestellte PM übereinstimmen
- ✅ Timing sollte korrekt sein (fertiggestellte PM vom Tag X → Lagerzugang am Tag X+1)
- ✅ **BESTÄTIGT:** TEST-3.3 bestanden (siehe TEST_ERGEBNISSE.md)

**Zu prüfen:**
- Nachfrage vs. Produktion
- Backlog-Entwicklung
- Service Level

---

### PHASE 4: Edge Case Tests

#### Test 4.1: Extreme Parameterwerte
**Ziel:** Prüfen ob System bei extremen Werten stabil bleibt

**Schritte:**
1. App starten
2. Navigiere zu **"8 Stammdaten"**
3. Ändere **"Gesamtvolumen"** auf **1000000** (sehr hoch)
4. Navigiere zu **"6 Produktion"**
5. Prüfe ob Berechnungen funktionieren
6. Ändere zurück auf **100000** (sehr niedrig)
7. Prüfe ob Berechnungen funktionieren

**Erwartetes Ergebnis:**
- System sollte nicht abstürzen
- Werte sollten plausibel sein
- Keine Division durch Null

**Zu prüfen:**
- Fehlermeldungen
- Abstürze
- Plausibilität der Werte

---

#### Test 4.2: Jahr-Wechsel
**Ziel:** Prüfen ob Jahr-Wechsel korrekt funktioniert

**Schritte:**
1. App starten
2. Navigiere zu **"8 Stammdaten"**
3. Ändere **"Planungsjahr"** auf **2028**
4. Prüfe ob alle Berechnungen neu durchgeführt werden
5. Ändere zurück auf **2027**
6. Prüfe ob Cache geladen wird

**Erwartetes Ergebnis:**
- Berechnungen sollten für neues Jahr durchgeführt werden
- Cache sollte für bekanntes Jahr geladen werden

**Zu prüfen:**
- Feiertage korrekt
- Arbeitstage korrekt
- Berechnungen korrekt

---

### PHASE 5: Szenario-Tests

#### Test 5.1: Marketing-Szenario
**Ziel:** Prüfen ob Marketing-Szenario korrekt angewendet wird

**Schritte:**
1. App starten
2. Navigiere zu Sidebar (Szenarien)
3. Aktiviere **"Marketing-Kampagne"**
4. Setze Start-Tag: **50**, End-Tag: **60**, Faktor: **1.5**
5. Navigiere zu **"2 Volumenplanung"**
6. Prüfe ob Nachfrage erhöht wurde (Tag 50-60)
7. Navigiere zu **"6 Produktion"**
8. Prüfe ob Produktion erhöht wurde

**Erwartetes Ergebnis:**
- Nachfrage sollte um 50% erhöht sein (Tag 50-60)
- Produktion sollte entsprechend erhöht sein
- Cache sollte invalidiert werden

**Zu prüfen:**
- Nachfrage-Werte Tag 50-60
- Produktions-Werte Tag 50-60
- Cache-Invalidierung

---

#### Test 5.2: Wasserschaden-Szenario
**Ziel:** Prüfen ob Wasserschaden korrekt angewendet wird

**Schritte:**
1. App starten
2. Navigiere zu Sidebar (Szenarien)
3. Aktiviere **"Wasserschaden im Materiallager"**
4. Setze Datum: **100** (Tag 100)
5. Navigiere zu **"5 Materiallager"**
6. Prüfe ob Bestand am Tag 100 auf 0 gesetzt wurde

**Erwartetes Ergebnis:**
- ✅ Bestand sollte am Tag 100 auf 0 gesetzt werden
- ✅ Produktion sollte beeinflusst werden
- ✅ `fertiggestellte PM` sollte auf 0 gesetzt werden wenn Wasserschaden am aktuellen Tag oder Vortag war
- ✅ **BESTÄTIGT:** Wasserschaden-Logik korrigiert (siehe SESSION_ZUSAMMENFASSUNG_CHAT.md)

**Zu prüfen:**
- Bestand morgens Tag 100
- Bestand abends Tag 100
- Produktion Tag 100

---

## 📊 Test-Protokoll

### Für jeden Test dokumentieren:

1. **Test-ID:** (z.B. TEST-1.1)
2. **Datum/Zeit:** 
3. **Tester:**
4. **Erwartetes Ergebnis:**
5. **Tatsächliches Ergebnis:**
6. **Unterschiede:**
7. **Screenshots:** (falls relevant)
8. **Fehler-Logs:** (falls vorhanden)

### Beispiel-Protokoll:

```
TEST-1.1: Produktionswerte Determinismus
Datum: 27.01.2026, 14:30
Tester: [Name]

Erwartetes Ergebnis: Werte sollten bei Neuladen identisch sein
Tatsächliches Ergebnis: 
- 1. Neuladen: MTB Extreme 03.04.2027 = 1723
- 2. Neuladen: MTB Extreme 03.04.2027 = 1723
- 3. Neuladen: MTB Extreme 03.04.2027 = 1723

Unterschiede: Keine - alle Werte identisch
Fehler-Logs: Keine
Status: ✅ BESTANDEN - Determinismus bestätigt
```

---

## 🎯 Prioritäten

### ✅ Bereits bestanden (keine weitere Aktion nötig):
1. ✅ **TEST-1.1:** Produktionswerte Determinismus
2. ✅ **TEST-1.2:** Mehrfaches Neuladen
3. ✅ **TEST-3.1:** Produktion ↔ Material Konsistenz
4. ✅ **TEST-3.2:** Inbound ↔ Material Konsistenz
5. ✅ **TEST-3.3:** Fertigproduktelager ↔ Produktion Konsistenz

### Sofort testen (🔴):
1. **TEST-2.1:** `total_volume` Änderung mit Cache-Invalidierung
2. **TEST-2.2:** `yearly_volume` Synchronisation

### Bald testen (🟡):
3. **TEST-2.3:** Cache-Invalidierung bei verschiedenen Parametern
4. **TEST-4.1:** Extreme Parameterwerte
5. **TEST-4.2:** Jahr-Wechsel

### Später testen (🟢):
6. **TEST-5.1:** Marketing-Szenario (vollständig)
7. **TEST-5.2:** Wasserschaden-Szenario (vollständig)

---

## 📝 Zusammenfassung der zu testenden Bereiche

### Kritische Bereiche:
1. ✅ **Determinismus:** Werte sollten bei Neuladen identisch sein - **BEHOBEN** (sorted() implementiert)
2. ⚠️ **Parameter-Synchronisation:** `yearly_volume` und `total_volume` sollten synchronisiert sein - **ZU PRÜFEN**
3. ⚠️ **Cache-Invalidierung:** Parameteränderungen sollten Cache invalidierten - **ZU PRÜFEN**
4. ✅ **Konsistenz:** Produktion, Material, Inbound sollten konsistent sein - **BESTÄTIGT** (alle Tests bestanden)
5. ✅ **Konvergenz-Check:** Iterative Berechnung sollte konvergieren - **BEHOBEN** (2 Iterationen mit Prüfung)

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

## 📊 Test-Status Übersicht

### ✅ Bereits getestet und bestanden (Stand: 27.01.2026):
1. ✅ **TEST-0.1:** System-Stabilität (3x Neuladen, identische Werte)
2. ✅ **TEST-0.2:** Produktreihenfolge (stabil)
3. ✅ **TEST-1.1:** Produktreihenfolge ist garantiert sortiert (`sorted()` implementiert)
4. ✅ **TEST-1.2:** Determinismus nach Fixes (3x Neuladen, identische Werte)
5. ✅ **TEST-1.3:** Konvergenz-Check funktioniert (2 Iterationen, Konvergenz erreicht)
6. ✅ **TEST-1.4:** Konvergenz bei verschiedenen Szenarien (Marketing + Wasserschaden)
7. ✅ **TEST-3.1:** Produktion ↔ Material Konsistenz
8. ✅ **TEST-3.2:** Inbound ↔ Material Konsistenz
9. ✅ **TEST-3.3:** Fertigproduktelager ↔ Produktion Konsistenz

**Siehe:** `TEST_ERGEBNISSE.md` für detaillierte Ergebnisse

### ⚠️ Noch zu testen:
- **TEST-2.1:** `total_volume` Änderung mit Cache-Invalidierung
- **TEST-2.2:** `yearly_volume` Synchronisation
- **TEST-2.3:** Cache-Invalidierung bei verschiedenen Parametern
- **TEST-4.1:** Extreme Parameterwerte
- **TEST-4.2:** Jahr-Wechsel
- **TEST-5.1:** Marketing-Szenario (teilweise getestet, vollständig zu prüfen)
- **TEST-5.2:** Wasserschaden-Szenario (teilweise getestet, vollständig zu prüfen)

---

**Status:** ✅ Test-Anleitung aktualisiert (28.01.2026)  
**Nächster Schritt:** Verbleibende Tests durchführen (siehe `NÄCHSTE_TESTS_UND_IMPLEMENTIERUNGEN.md`)
