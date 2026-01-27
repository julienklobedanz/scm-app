# Detaillierte Test-Anleitung für UI

**Datum:** 27.01.2026  
**Basierend auf:** Vollständige Fehleranalyse  
**Ziel:** Systematisches Testen aller kritischen Bereiche in der Oberfläche

---

## ⚠️ WICHTIG: Bekannte Probleme (noch nicht behoben)

Vor dem Testen bitte beachten:

1. **FEHLER-001:** `yearly_volume` und `total_volume` sind NICHT synchronisiert
2. **FEHLER-002:** Cache wird NICHT invalidiert bei Parameteränderungen
3. **FEHLER-003:** Produktreihenfolge ist NICHT stabilisiert (kann zu unterschiedlichen Werten führen)
4. **FEHLER-004:** Kein Konvergenz-Check (2 Iterationen ohne Prüfung)

**Erwartetes Verhalten:**
- Unterschiedliche Werte bei Neuladen möglich (z.B. 1799 vs 1760 für Extreme)
- Parameteränderungen haben keine sofortige Auswirkung
- App-Neustart erforderlich für Parameteränderungen

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
- ⚠️ **AKTUELL:** Werte können unterschiedlich sein (1799 vs 1760)
- ✅ **ZIEL:** Werte sollten identisch sein

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
- ⚠️ **AKTUELL:** Werte können variieren
- ✅ **ZIEL:** Alle 5 Werte sollten identisch sein

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
- ⚠️ **AKTUELL:** Werte ändern sich NICHT (Cache wird nicht invalidiert)
- ✅ **ZIEL:** Werte sollten sich ändern

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
- ⚠️ **AKTUELL:** Werte sind NICHT synchronisiert
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
- ⚠️ **AKTUELL:** Werte ändern sich NICHT (Cache wird nicht invalidiert)
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
- Materialverbrauch sollte mit Produktionsmenge übereinstimmen
- Bestand sollte korrekt reduziert werden

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
- Inbound-Menge sollte im Materiallager sichtbar sein
- Bestand sollte korrekt erhöht werden

**Zu prüfen:**
- Ankunftsdatum
- Ankunftsmenge
- Bestand nach Ankunft

---

#### Test 3.3: Volumenplanung ↔ Produktion Konsistenz
**Ziel:** Prüfen ob Nachfrage und Produktion konsistent sind

**Schritte:**
1. App starten
2. Navigiere zu **"2 Volumenplanung"**
3. Notiere Nachfrage für **"MTB Extreme"** am **03.04.2027**
4. Navigiere zu **"6 Produktion"**
5. Prüfe ob Produktion mit Nachfrage übereinstimmt

**Erwartetes Ergebnis:**
- Produktion sollte Nachfrage erfüllen (wenn Material verfügbar)
- Backlog sollte korrekt berechnet werden

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
- Bestand sollte am Tag 100 auf 0 gesetzt werden
- Produktion sollte beeinflusst werden

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
- 1. Neuladen: MTB Extreme 03.04.2027 = 1799
- 2. Neuladen: MTB Extreme 03.04.2027 = 1760
- 3. Neuladen: MTB Extreme 03.04.2027 = 1799

Unterschiede: Werte variieren zwischen 1760 und 1799
Fehler-Logs: Keine
Status: ❌ FEHLER - Nicht-deterministisch
```

---

## 🎯 Prioritäten

### Sofort testen (🔴):
1. **TEST-1.1:** Produktionswerte Determinismus
2. **TEST-1.2:** Mehrfaches Neuladen
3. **TEST-2.1:** `total_volume` Änderung

### Bald testen (🟡):
4. **TEST-2.2:** `yearly_volume` vs `total_volume` Konsistenz
5. **TEST-2.3:** Cache-Invalidierung
6. **TEST-3.1:** Produktion ↔ Material Konsistenz

### Später testen (🟢):
7. **TEST-3.2:** Inbound ↔ Material Konsistenz
8. **TEST-3.3:** Volumenplanung ↔ Produktion Konsistenz
9. **TEST-4.1:** Extreme Parameterwerte
10. **TEST-4.2:** Jahr-Wechsel
11. **TEST-5.1:** Marketing-Szenario
12. **TEST-5.2:** Wasserschaden-Szenario

---

## 📝 Zusammenfassung der zu testenden Bereiche

### Kritische Bereiche:
1. ✅ **Determinismus:** Werte sollten bei Neuladen identisch sein
2. ✅ **Parameter-Synchronisation:** `yearly_volume` und `total_volume` sollten synchronisiert sein
3. ✅ **Cache-Invalidierung:** Parameteränderungen sollten Cache invalidierten
4. ✅ **Konsistenz:** Produktion, Material, Inbound sollten konsistent sein

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

## ⚠️ Bekannte Probleme (vor Test beachten)

1. **Nicht-Determinismus:** Werte können bei Neuladen variieren
2. **Parameter-Synchronisation:** `yearly_volume` und `total_volume` sind nicht synchronisiert
3. **Cache-Invalidierung:** Parameteränderungen haben keine sofortige Auswirkung
4. **Konvergenz-Check:** Fehlt für iterative Berechnung

**Empfehlung:** Nach jedem Parameter-Änderung App neu starten!

---

**Status:** ✅ Test-Anleitung erstellt  
**Nächster Schritt:** Tests durchführen und Ergebnisse dokumentieren
