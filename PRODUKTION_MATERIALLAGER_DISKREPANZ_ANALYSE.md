# Produktion & Materiallager Diskrepanz-Analyse

**Datum:** 28.01.2026  
**Status:** 🔍 **IN ANALYSE**

---

## 🔴 Identifizierte Probleme

### Problem 1: fertiggestellte PM > tatsächliche PM (MATHEMATISCH UNMÖGLICH!)

**Beobachtung:**
- **MTB Allrounder:** `fertiggestellte PM` Summe = **110,855**, `tatsächliche PM` Summe = **111,000**
- **MTB Downhill:** `fertiggestellte PM` Summe = **36,951**, `tatsächliche PM` Summe = **37,000**

**Problem:** `fertiggestellte PM` sollte **NIEMALS** größer als `tatsächliche PM` sein!

**Mögliche Ursachen:**
1. **Berechnungsfehler:** Die Summe von `fertiggestellte PM` wird falsch berechnet
2. **Doppelzählung:** Einige Werte werden mehrfach gezählt
3. **Logikfehler:** Die Logik "fertiggestellte PM am Tag X = tatsächliche PM vom Tag X-1" wird falsch angewendet

---

### Problem 2: Restbestand im Materiallager am Jahresende

**Beobachtung:**
- **Fizik Tundra:** Bestand abends am 31.12.2027 = **810**
- **Frage:** Wenn noch Material da ist, wie konnten dann alle Fertigprodukte produziert werden?

**Mögliche Ursachen:**
1. **Kapazitätsgrenze:** Die Produktion konnte nicht alles Material verwenden (tägliche Kapazität begrenzt)
2. **Materialüberschuss:** Es wurde mehr Material bestellt/geliefert als benötigt
3. **Berechnungsdiskrepanz:** Materialverbrauch wird nicht korrekt berechnet/abgebucht

---

### Problem 3: Materialverbrauch vs. Produktion

**Beobachtung:**
- Materiallager zeigt Restbestand am Jahresende
- Produktion zeigt, dass alle Fertigprodukte produziert wurden
- **Frage:** Wie passt das zusammen?

**Mögliche Ursachen:**
1. **Materialverbrauch wird nicht korrekt berechnet:** Der Verbrauch basiert auf `material_verbrauch` oder `tatsächliche PM`, aber es gibt eine Diskrepanz
2. **Material wird nicht vollständig abgebucht:** Der Bestand wird nicht korrekt reduziert
3. **Inbound-Mengen sind höher als benötigt:** Es wurde mehr Material geliefert als für die Produktion benötigt

---

## 🔍 Analyse der Berechnungslogik

### 1. fertiggestellte PM Berechnung

**Code:** `ui/production_calculations.py` Zeilen 681-800

**Logik:**
- `fertiggestellte PM am Tag X = tatsächliche PM vom Tag X-1` (vom vorherigen Arbeitstag)
- Am ersten Tag: `fertiggestellte PM = tatsächliche PM` (Sonderfall)

**Problem:** Die Summe könnte falsch sein, wenn:
- Einige Tage doppelt gezählt werden
- Die Logik für den letzten Tag falsch ist
- Die Summe wird nicht korrekt berechnet

### 2. Materialverbrauch Berechnung

**Code:** `ui/material_calculations.py` Zeilen 137-172

**Logik:**
- Materialverbrauch wird aus `production_logs_cache` berechnet
- Verwendet `material_verbrauch` Spalte oder `tatsächliche PM` als Fallback
- Summiert Verbrauch pro Tag und Sattel-Typ

**Problem:** Der Verbrauch könnte falsch sein, wenn:
- `material_verbrauch` nicht korrekt gesetzt wird
- Die Summierung falsch ist
- Es Rundungsfehler gibt

### 3. Materialbestand Berechnung

**Code:** `ui/material_calculations.py` Zeilen 221-243

**Logik:**
- Bestand morgens = Bestand gestern abend + Zugang heute
- Bestand abends = Bestand morgens - Lagerabgang
- Lagerabgang = min(geplante Produktion, verfügbarer Bestand)

**Problem:** Der Bestand könnte falsch sein, wenn:
- Der Lagerabgang nicht korrekt berechnet wird
- Der Zugang nicht korrekt erfasst wird
- Es Rundungsfehler gibt

---

## 🎯 Nächste Schritte zur Fehlerbehebung

### Schritt 1: Prüfe fertiggestellte PM Summe

**Zu prüfen:**
1. Wie wird die Summe von `fertiggestellte PM` berechnet?
2. Werden alle Tage korrekt gezählt?
3. Gibt es Doppelzählungen?

**Code-Stellen:**
- `ui/production_calculations.py` Zeilen 681-800 (Berechnung)
- `pages/6_produktion.py` (Anzeige/Summierung)

### Schritt 2: Prüfe Materialverbrauch

**Zu prüfen:**
1. Wird `material_verbrauch` korrekt gesetzt?
2. Entspricht der Verbrauch der `tatsächlichen PM`?
3. Gibt es Rundungsfehler?

**Code-Stellen:**
- `ui/production_calculations.py` Zeilen 664-667 (Setzen von material_verbrauch)
- `ui/material_calculations.py` Zeilen 137-172 (Berechnung des Verbrauchs)

### Schritt 3: Prüfe Materialbestand

**Zu prüfen:**
1. Wird der Bestand korrekt reduziert?
2. Entspricht der Lagerabgang dem Materialverbrauch?
3. Gibt es Diskrepanzen zwischen Materiallager und Produktion?

**Code-Stellen:**
- `ui/material_calculations.py` Zeilen 221-243 (Bestandsberechnung)
- `ui/production_calculations.py` Zeilen 650-652 (Materialabbuchung)

---

## 📊 Erwartete Korrekturen

### 1. fertiggestellte PM Summe korrigieren

**Erwartung:**
- `fertiggestellte PM` Summe sollte ≤ `tatsächliche PM` Summe sein
- Die Differenz sollte genau der `tatsächlichen PM` vom letzten Tag entsprechen (wenn nicht explizit addiert)

### 2. Materialverbrauch korrigieren

**Erwartung:**
- Materialverbrauch sollte genau der `tatsächlichen PM` entsprechen
- Keine Diskrepanzen zwischen Materiallager und Produktion

### 3. Materialbestand korrigieren

**Erwartung:**
- Wenn alle Fertigprodukte produziert wurden, sollte der Materialbestand am Jahresende = 0 sein (oder minimal durch Rundung)
- Oder: Der Restbestand sollte erklärbar sein (z.B. durch Kapazitätsgrenzen)

---

**Status:** 🔍 **ANALYSE LÄUFT**
