# TEST-1.4: Konvergenz bei verschiedenen Szenarien - Detaillierte Anleitung

**Datum:** 27.01.2026  
**Ziel:** Prüfen ob Konvergenz auch bei verschiedenen Szenarien funktioniert

---

## 📋 Vorbereitung

1. **App starten** (Streamlit)
2. **Navigiere zu "8 Stammdaten"** - Notiere die Konvergenz-Info (sollte 2 Iterationen zeigen)
3. **Navigiere zu "6 Produktion"** - Notiere einen Referenzwert für späteren Vergleich

---

## 🎯 SZENARIO 1: Marketing-Kampagne

### Schritt 1: Szenario aktivieren

1. **Sidebar öffnen** (links im Streamlit-UI)
2. **Klicke auf "+ Szenarien hinzufügen"** (falls noch kein Szenario aktiv ist)
3. **Wähle "Marketingaktion"** aus dem Dropdown "Szenario-Typ"
4. **Setze folgende Werte:**
   - **Start-Datum:** `50` (Tag 50 = ca. 19.02.2027)
   - **End-Datum:** `60` (Tag 60 = ca. 01.03.2027)
   - **Faktor:** `1.5` (50% Erhöhung)
5. **Szenario sollte jetzt aktiv sein** (Haken gesetzt)

### Schritt 2: Konvergenz-Check prüfen

1. **Navigiere zu "8 Stammdaten"**
2. **Prüfe die grüne Info-Box oben:**
   - **Erwartetes Ergebnis:** 
     - ✅ Sollte zeigen: "Konvergenz-Check: X Iteration(en) durchgeführt, Konvergenz erreicht!"
     - ✅ X sollte 2-3 sein (max. 5)
   - **Zu dokumentieren:** Anzahl Iterationen = _______

### Schritt 3: Nachfrage prüfen (Volumenplanung)

1. **Navigiere zu "2 Volumenplanung"**
2. **Suche in der Tabelle nach Tag 50-60** (ca. 19.02.2027 - 01.03.2027)
3. **Prüfe für "MTB Extreme":**
   - **Tag 50:** Notiere "Nachfrage" = _______
   - **Tag 55:** Notiere "Nachfrage" = _______
   - **Tag 60:** Notiere "Nachfrage" = _______
4. **Vergleiche mit Tag 49 (vor Marketing):**
   - **Tag 49:** Notiere "Nachfrage" = _______
   - **Erwartetes Ergebnis:**
     - ✅ Tag 50-60 sollten **1.5x höher** sein als Tag 49
     - ✅ Beispiel: Wenn Tag 49 = 100, dann Tag 50-60 = 150
   - **Zu dokumentieren:** 
     - Nachfrage Tag 49 = _______
     - Nachfrage Tag 50 = _______ (sollte 1.5x sein)
     - Nachfrage Tag 55 = _______ (sollte 1.5x sein)
     - Nachfrage Tag 60 = _______ (sollte 1.5x sein)

### Schritt 4: Produktion prüfen

1. **Navigiere zu "6 Produktion"**
2. **Suche in der Tabelle nach Tag 50-60** (ca. 19.02.2027 - 01.03.2027)
3. **Prüfe für "MTB Extreme":**
   - **Tag 50:** Notiere "tatsächliche PM" = _______
   - **Tag 55:** Notiere "tatsächliche PM" = _______
   - **Tag 60:** Notiere "tatsächliche PM" = _______
4. **Vergleiche mit Tag 49 (vor Marketing):**
   - **Tag 49:** Notiere "tatsächliche PM" = _______
   - **Erwartetes Ergebnis:**
     - ✅ Produktion sollte **erhöht** sein (wenn Material verfügbar)
     - ✅ Sollte der erhöhten Nachfrage entsprechen
   - **Zu dokumentieren:**
     - Produktion Tag 49 = _______
     - Produktion Tag 50 = _______
     - Produktion Tag 55 = _______
     - Produktion Tag 60 = _______

### Schritt 5: Dokumentation Szenario 1

- ✅ Konvergenz erreicht: Ja / Nein
- ✅ Anzahl Iterationen: _______
- ✅ Nachfrage erhöht (Tag 50-60): Ja / Nein
- ✅ Produktion erhöht (Tag 50-60): Ja / Nein

---

## 🎯 SZENARIO 2: Wasserschaden im Materiallager

### Schritt 1: Marketing deaktivieren

1. **Sidebar öffnen**
2. **Deaktiviere "Marketingaktion"** (Haken entfernen)
3. **Warte kurz** (Seite lädt neu)

### Schritt 2: Wasserschaden aktivieren

1. **Klicke auf "+ Szenarien hinzufügen"** (falls nötig)
2. **Wähle "Wasserschaden im Materiallager"** aus dem Dropdown
3. **Setze folgende Werte:**
   - **Datum (Tag):** `100` (Tag 100 = ca. 11.04.2027)
4. **Szenario sollte jetzt aktiv sein** (Haken gesetzt)

### Schritt 3: Konvergenz-Check prüfen

1. **Navigiere zu "8 Stammdaten"**
2. **Prüfe die grüne Info-Box oben:**
   - **Erwartetes Ergebnis:**
     - ✅ Sollte zeigen: "Konvergenz-Check: X Iteration(en) durchgeführt, Konvergenz erreicht!"
     - ✅ X sollte 2-3 sein (max. 5)
   - **Zu dokumentieren:** Anzahl Iterationen = _______

### Schritt 4: Materiallager prüfen

1. **Navigiere zu "5 Materiallager"**
2. **Suche in der Tabelle nach Tag 100** (ca. 11.04.2027)
3. **Prüfe für "Spark" (Sattel):**
   - **Tag 99 (vor Wasserschaden):**
     - Notiere "Bestand morgens" = _______
     - Notiere "Bestand abends" = _______
   - **Tag 100 (Wasserschaden):**
     - Notiere "Bestand morgens" = _______
     - Notiere "Bestand abends" = _______
   - **Tag 101 (nach Wasserschaden):**
     - Notiere "Bestand morgens" = _______
   - **Erwartetes Ergebnis:**
     - ✅ Tag 100: Bestand sollte auf **0** gesetzt sein
     - ✅ Tag 101: Bestand sollte weiterhin **0** sein (oder wieder steigen durch neue Lieferungen)
   - **Zu dokumentieren:**
     - Bestand Tag 99 morgens = _______
     - Bestand Tag 100 morgens = _______ (sollte 0 sein)
     - Bestand Tag 100 abends = _______ (sollte 0 sein)
     - Bestand Tag 101 morgens = _______

### Schritt 5: Produktion prüfen

1. **Navigiere zu "6 Produktion"**
2. **Suche in der Tabelle nach Tag 100-105** (ca. 11.04.2027 - 16.04.2027)
3. **Prüfe für "MTB Extreme"** (verwendet "Spark" Sattel):
   - **Tag 99:** Notiere "tatsächliche PM" = _______
   - **Tag 100:** Notiere "tatsächliche PM" = _______
   - **Tag 101:** Notiere "tatsächliche PM" = _______
   - **Tag 102:** Notiere "tatsächliche PM" = _______
   - **Erwartetes Ergebnis:**
     - ✅ Produktion sollte am Tag 100 oder kurz danach **reduziert** sein
     - ✅ Sollte auf 0 fallen, wenn kein Material mehr verfügbar ist
   - **Zu dokumentieren:**
     - Produktion Tag 99 = _______
     - Produktion Tag 100 = _______ (sollte reduziert/0 sein)
     - Produktion Tag 101 = _______ (sollte reduziert/0 sein)
     - Produktion Tag 102 = _______

### Schritt 6: Dokumentation Szenario 2

- ✅ Konvergenz erreicht: Ja / Nein
- ✅ Anzahl Iterationen: _______
- ✅ Materialbestand Tag 100 auf 0: Ja / Nein
- ✅ Produktion beeinflusst (Tag 100+): Ja / Nein

---

## 📊 Zusammenfassung TEST-1.4

### Szenario 1: Marketing-Kampagne
- Konvergenz erreicht: _______
- Anzahl Iterationen: _______
- Nachfrage erhöht: _______
- Produktion erhöht: _______

### Szenario 2: Wasserschaden
- Konvergenz erreicht: _______
- Anzahl Iterationen: _______
- Materialbestand auf 0: _______
- Produktion beeinflusst: _______

### Gesamtbewertung:
- ✅ Alle Szenarien konvergieren: Ja / Nein
- ✅ Max. 5 Iterationen ausreichend: Ja / Nein
- ✅ Werte sind stabil: Ja / Nein

---

## 🎯 Erwartete Ergebnisse (Zusammenfassung)

### Konvergenz:
- ✅ Sollte immer erreicht werden (max. 5 Iterationen)
- ✅ Typischerweise 2-3 Iterationen

### Marketing-Kampagne:
- ✅ Nachfrage Tag 50-60 sollte 1.5x höher sein als Tag 49
- ✅ Produktion sollte entsprechend erhöht sein

### Wasserschaden:
- ✅ Materialbestand Tag 100 sollte 0 sein
- ✅ Produktion sollte reduziert/0 sein (wenn Material fehlt)

---

**Status:** ⏳ **BEREIT FÜR TEST**  
**Nächster Schritt:** Führe die Tests durch und dokumentiere die Ergebnisse
