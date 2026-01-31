# Rollback-Analyse und Implementierungsplan

**Datum:** 2026-01-30

## 🔴 Probleme identifiziert

### Daten-Diskrepanzen nach den Änderungen:

1. **Fizik Tundra Materiallager:**
   - Summe Lagerzugang: **36,787** (sollte ~99,900 sein)
   - Summe Lagerabgang: **36,787**
   - **Problem:** Viel zu wenig Material wurde bestellt/geliefert

2. **MTB Downhill Produktion:**
   - Summe tatsächliche PM: **37,000** ✅
   - Summe fertiggestellte PM: **36,787** ❌ (fehlen 213)
   - Backlog am Ende: **213** ❌

3. **Fizik Tundra Fertigproduktelager:**
   - Summe Lagerzugang: **98,549**
   - Summe Lagerabgang: **98,549**
   - Bestand abends: **101,934** ❌ (sollte 0 sein!)

---

## 🔍 Ursachen-Analyse

### Problem 1: Dynamische Vorlaufzeit-Berechnung

**Was wurde geändert:**
- Vorlaufzeit wurde von hardcodiert `49` auf dynamische Berechnung aus `PROCUREMENT_ROUTES` geändert
- Änderungen in: `simulator.py`, `procurement_manager.py`, `china_transport.py`, `app.py`

**Warum das Probleme verursacht:**
1. **Timing-Problem:** Wenn `PROCUREMENT_ROUTES` geändert werden, ändert sich die Vorlaufzeit
2. **Initial Orders:** `_place_initial_orders()` verwendet jetzt dynamische Vorlaufzeit
   - Wenn Vorlaufzeit z.B. 43 statt 49 ist, werden weniger Tage vorbestellt
   - Dies führt zu Materialmangel am Jahresanfang
3. **Bestellungen:** Tägliche Bestellungen verwenden jetzt dynamische Vorlaufzeit
   - Wenn sich die Vorlaufzeit ändert, werden Bestellungen für falsche Tage platziert
   - Dies führt zu Timing-Fehlern in der gesamten Supply Chain

**Kritischer Fehler:**
- Die dynamische Berechnung wird **jedes Mal** ausgeführt, wenn sie aufgerufen wird
- Wenn `PROCUREMENT_ROUTES` während der Simulation geändert werden, ändert sich die Vorlaufzeit
- Dies führt zu Inkonsistenzen zwischen bereits platzierten Bestellungen und neuen Berechnungen

### Problem 2: PROCUREMENT_ROUTES Lookups statt hardcodierte Werte

**Was wurde geändert:**
- Hardcodierte Transportzeiten (2, 30, 2) wurden durch `_get_route_duration()` Lookups ersetzt
- Änderungen in: `china_transport.py` (mehrere Stellen)

**Warum das Probleme verursacht:**
1. **Cache-Invalidierung:** Wenn `PROCUREMENT_ROUTES` geändert werden, müssen alle Caches invalidiert werden
2. **Timing-Konsistenz:** Bereits berechnete Transportzeiten werden nicht aktualisiert
3. **Lookup-Fehler:** Wenn Route nicht gefunden wird, wird Fallback-Wert verwendet (2 oder 30)
   - Dies kann zu falschen Berechnungen führen, wenn Route-Struktur nicht exakt passt

**Kritischer Fehler:**
- Die `_get_route_duration()` Methode sucht nach `supplier == 'China'` und `component == 'Sattel'`
- Wenn die Route-Struktur nicht exakt passt, wird Fallback verwendet
- Dies kann zu falschen Transportzeiten führen

### Problem 3: Mapping-Fehler in Beschaffungs-Routen

**Was wurde geändert:**
- Synchronisierung prüft jetzt auch `departure` und `arrival`
- Änderungen in: `pages/8_stammdaten.py`

**Warum das Probleme verursacht:**
- Wenn Mapping falsch ist, werden falsche Routen aktualisiert
- Dies führt zu falschen Transportzeiten in Berechnungen

---

## ✅ Rollback durchgeführt

Alle Änderungen wurden rückgängig gemacht:
- `app.py` - Source Cycle Time Berechnung
- `pages/1_reporting.py` - Service Level Labels
- `pages/8_stammdaten.py` - Beschaffungs-Routen Editierbarkeit, Vorlaufzeit-Label
- `simulation/china_transport.py` - `_get_route_duration()` Methode, hardcodierte Werte
- `simulation/procurement_manager.py` - Dynamische Vorlaufzeit
- `simulation/simulator.py` - Dynamische Vorlaufzeit

---

## 📋 Sicherer Implementierungsplan

### Phase 1: Vorlaufzeit als variabler, aber fester Wert

**Anforderung:** "Nehmen Sie die Vorlaufzeit als variablen, aber festen Wert."

**Sichere Implementierung:**
1. **Vorlaufzeit bleibt editierbar** in Stammdaten → Beschaffung
2. **Vorlaufzeit wird NICHT dynamisch berechnet** während der Simulation
3. **Vorlaufzeit wird einmal beim Start geladen** und bleibt konstant
4. **Änderungen an Vorlaufzeit invalidieren Caches** und erfordern Neustart der Simulation

**Code-Änderungen:**
- Vorlaufzeit bleibt in `MasterData.SUPPLIERS['China']['lead_time']` (editierbar)
- Alle Berechnungen verwenden diesen Wert direkt (nicht dynamisch berechnet)
- Label: "Vorlaufzeit (Tage)" - kann geändert werden, aber nicht dynamisch berechnet

### Phase 2: Beschaffungs-Routen Dauer editierbar machen

**Sichere Implementierung:**
1. **Routen-Dauer wird editierbar** in Stammdaten → Beschaffung
2. **Änderungen werden in `MasterData.PROCUREMENT_ROUTES` gespeichert**
3. **Änderungen invalidieren ALLE Caches** und erfordern Neustart der Simulation
4. **Warnung anzeigen:** "⚠️ Änderungen erfordern Neustart der Simulation"

**Code-Änderungen:**
- Routen-Dauer editierbar in `pages/8_stammdaten.py`
- Synchronisierung mit `MasterData.PROCUREMENT_ROUTES`
- **ABER:** Hardcodierte Werte bleiben in `china_transport.py` (werden nicht durch Lookups ersetzt)
- **ODER:** Lookups werden verwendet, aber nur wenn Simulation neu gestartet wird

### Phase 3: Transportzeiten aus PROCUREMENT_ROUTES lesen (optional)

**Nur wenn Phase 2 erfolgreich ist:**
1. **Ersetze hardcodierte Werte durch Lookups**
2. **Aber:** Nur wenn Simulation neu gestartet wird (nicht während laufender Simulation)
3. **Cache-Invalidierung:** Alle Caches werden invalidiert bei Änderungen

**Code-Änderungen:**
- `_get_route_duration()` Methode verwenden
- **ABER:** Nur wenn `PROCUREMENT_ROUTES` nicht während Simulation geändert werden

---

## 🎯 Empfohlener Ansatz

### Option A: Konservativ (empfohlen)
1. **Vorlaufzeit bleibt editierbar** (wie vorher)
2. **Beschaffungs-Routen bleiben NICHT editierbar** (nur Anzeige)
3. **Hardcodierte Transportzeiten bleiben** (2, 30, 2)
4. **Keine dynamische Berechnung**

**Vorteile:**
- Keine Seiteneffekte
- Berechnungen bleiben konsistent
- Keine Timing-Probleme

**Nachteile:**
- Routen-Dauer nicht editierbar
- Transportzeiten nicht dynamisch

### Option B: Vorsichtig (wenn Option A nicht ausreicht)
1. **Vorlaufzeit bleibt editierbar** (wie vorher)
2. **Beschaffungs-Routen Dauer editierbar** mit Warnung
3. **Hardcodierte Transportzeiten bleiben** (werden nicht durch Lookups ersetzt)
4. **Änderungen erfordern Neustart der Simulation**

**Vorteile:**
- Routen-Dauer editierbar
- Keine Timing-Probleme während Simulation
- Konsistenz gewährleistet

**Nachteile:**
- Transportzeiten müssen manuell in Code geändert werden
- Änderungen erfordern Neustart

### Option C: Vollständig (nur wenn Option B erfolgreich)
1. **Vorlaufzeit bleibt editierbar**
2. **Beschaffungs-Routen Dauer editierbar**
3. **Transportzeiten werden aus PROCUREMENT_ROUTES gelesen**
4. **Aber:** Nur wenn Simulation neu gestartet wird

**Vorteile:**
- Vollständig dynamisch
- Alle Werte editierbar

**Nachteile:**
- Komplexer
- Risiko von Timing-Problemen
- Erfordert sorgfältige Cache-Invalidierung

---

## 🔧 Konkrete Implementierungsschritte (Option B)

### Schritt 1: Vorlaufzeit-Label anpassen
- Ändere Label zu "Berechnete Vorlaufzeit (Worst Case/Standard: 49 Tage)"
- Hole 49 aus `MasterData.SUPPLIERS['China']['lead_time']` (ursprünglicher Wert)
- Vorlaufzeit bleibt editierbar, aber nicht dynamisch berechnet

### Schritt 2: Beschaffungs-Routen editierbar machen
- Mache `duration` in `PROCUREMENT_ROUTES` editierbar
- Synchronisiere mit `MasterData.PROCUREMENT_ROUTES`
- Zeige Warnung: "⚠️ Änderungen erfordern Neustart der Simulation"
- Invalidiere ALLE Caches bei Änderungen

### Schritt 3: Transportzeiten NICHT ändern
- **Lasse hardcodierte Werte (2, 30, 2) in `china_transport.py`**
- **Ersetze NICHT durch Lookups**
- **Grund:** Vermeidet Timing-Probleme während laufender Simulation

### Schritt 4: Auslieferungs-Routen editierbar machen
- Mache `duration` in `DELIVERY_ROUTES` editierbar (nur China)
- Synchronisiere mit `MasterData.DELIVERY_ROUTES`
- Verstecke andere Tabellen (Deutschland, Frankreich, etc.)

### Schritt 5: Verkaufsanteile Validierung verbessern
- Prüfe auf negative Werte
- Prüfe ob Summe = 100%
- Zeige Warnung wenn nicht 100%
- Option zur automatischen Normalisierung

---

## ⚠️ Kritische Erkenntnisse

1. **Dynamische Berechnung während Simulation ist gefährlich:**
   - Führt zu Timing-Inkonsistenzen
   - Bereits platzierten Bestellungen werden nicht aktualisiert
   - Transportzeiten werden falsch berechnet

2. **Cache-Invalidierung allein reicht nicht:**
   - Bereits berechnete Transportzeiten bleiben falsch
   - Simulation muss komplett neu gestartet werden

3. **Lookups statt hardcodierte Werte:**
   - Können zu Fallback-Werten führen
   - Können falsche Routen finden
   - Erfordern sorgfältige Validierung

4. **Vorlaufzeit sollte NICHT dynamisch berechnet werden:**
   - Sollte editierbar sein, aber fest bleiben
   - Dynamische Berechnung führt zu Timing-Problemen
   - Bereits platzierten Bestellungen werden nicht aktualisiert

---

## ✅ Empfehlung

**Implementiere Option B:**
1. Vorlaufzeit bleibt editierbar (wie vorher)
2. Beschaffungs-Routen Dauer editierbar mit Warnung
3. Hardcodierte Transportzeiten bleiben (werden nicht durch Lookups ersetzt)
4. Änderungen erfordern Neustart der Simulation

**Dies vermeidet:**
- Timing-Probleme während Simulation
- Inkonsistenzen zwischen Bestellungen und Berechnungen
- Falsche Transportzeiten

**Dies ermöglicht:**
- Editierbare Routen-Dauer
- Konsistente Berechnungen
- Vorhersagbares Verhalten
