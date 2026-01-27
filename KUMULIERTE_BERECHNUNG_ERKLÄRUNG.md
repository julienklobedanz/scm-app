# Kumulierte Berechnung: Materiallager mit Verlustmenge

**Datum:** 27.01.2026  
**Ziel:** Erklären wie kumulierte Bestände mit Verlustmenge berechnet werden

---

## 📊 Deine Beobachtungen

**Mit Wasserschaden:**
- Verlustmenge: **3145**
- Kumulierter Bestand abends: **23909**

**Ohne Wasserschaden:**
- Kumulierter Bestand abends: **245154**

**Frage:** Wie rechnet man das nach?

---

## 🔢 Erklärung: Kumulierte Berechnung

### Grundformel:

**Kumulierter Bestand abends = Summe aller Zugänge - Summe aller Abgänge - Summe aller Verlustmengen**

### Schritt-für-Schritt:

**1. Summe aller Zugänge:**
- Alle Inbound-Ankünfte seit Jahresbeginn
- Beispiel: 300000

**2. Summe aller Abgänge:**
- Alle Produktions-Verbräuche seit Jahresbeginn
- Beispiel: 55091

**3. Summe aller Verlustmengen:**
- Alle Wasserschäden seit Jahresbeginn
- Beispiel: 3145

**4. Kumulierter Bestand:**
- Mit Verlust: 300000 - 55091 - 3145 = **241764**
- Ohne Verlust: 300000 - 55091 - 0 = **244909**

**Differenz:** 244909 - 241764 = **3145** ✅

---

## 🔍 Deine Werte analysieren

### Problem:
- Mit Verlust: **23909**
- Ohne Verlust: **245154**
- Differenz: 245154 - 23909 = **221245** (nicht 3145!)

### Mögliche Erklärungen:

**1. Verschiedene Zeitpunkte:**
- Mit Verlust: Bestand **nach** Wasserschaden (Tag 22.02.2027)
- Ohne Verlust: Bestand **vor** Wasserschaden (Tag 21.02.2027)
- Oder: Bestand **am Jahresende** (Tag 365)

**2. Verschiedene Sattel-Typen:**
- Mit Verlust: "Fizik Tundra" (verloren: 3145)
- Ohne Verlust: Gesamt aller Sattel-Typen (kein Verlust)

**3. Verschiedene Berechnungsmethoden:**
- Mit Verlust: Berechnung **mit** Wasserschaden-Szenario
- Ohne Verlust: Berechnung **ohne** Wasserschaden-Szenario

---

## 📋 So prüfst du es richtig

### Test 1: Summenzeile prüfen

1. **Navigiere zu "5 Materiallager"**
2. **Scrolle zur Summenzeile** (unten in der Tabelle)
3. **Prüfe für "Fizik Tundra":**
   - Summe Lagerzugang = _______
   - Summe Lagerabgang = _______
   - Summe Verlustmenge = _______ (sollte 3145 sein)
   - Kumulierter Bestand abends = _______

**Berechnung:**
- Kumulierter Bestand = Summe Zugang - Summe Abgang - Summe Verlust ✅

### Test 2: Tag-für-Tag prüfen

1. **Navigiere zu "5 Materiallager"**
2. **Prüfe Tag 21.02.2027 (vor Wasserschaden):**
   - Bestand abends = _______
3. **Prüfe Tag 22.02.2027 (Wasserschaden):**
   - Verlustmenge = _______ (sollte = Bestand morgens sein)
   - Bestand abends = 0 ✅
4. **Prüfe Tag 23.02.2027 (nach Wasserschaden):**
   - Bestand morgens = 0 ✅
   - Bestand abends = _______ (kann wieder steigen durch neue Ankünfte)

**Berechnung:**
- Tag 22.02.2027: Bestand abends = Bestand morgens - Lagerabgang - Verlustmenge
- Wenn Bestand morgens = 3145, Verlustmenge = 3145 → Bestand abends = 0 ✅

### Test 3: Vergleich ohne Wasserschaden

1. **Deaktiviere Wasserschaden** in Sidebar
2. **Warte bis Seite neu geladen ist**
3. **Navigiere zu "5 Materiallager"**
4. **Prüfe Tag 22.02.2027:**
   - Bestand morgens = _______ (sollte > 0 sein)
   - Bestand abends = _______ (sollte > 0 sein)
   - Verlustmenge = 0 ✅

**Vergleich:**
- Mit Wasserschaden: Bestand = 0, Verlustmenge = 3145
- Ohne Wasserschaden: Bestand > 0, Verlustmenge = 0
- Differenz = Verlustmenge ✅

---

## 💡 Erklärung: Warum verschiedene Produkte unterschiedlich reagieren

### MTB Extreme (0er-Zeile):

**Warum:**
- Verwendet "Spark" Sattel
- Wenn "Spark" Bestand = 0 → keine Produktion möglich
- Wenn keine Produktion → keine neuen Endprodukte
- Wenn keine Nachfrage an diesem Tag → keine Abgänge
- **Ergebnis:** 0er-Zeile ✅

### MTB Downhill (Zu- und Abgänge):

**Warum:**
- Verwendet "Fizik Tundra" Sattel
- Wenn "Fizik Tundra" Bestand > 0 → Produktion möglich
- Wenn Produktion > 0 → neue Endprodukte
- Wenn Nachfrage > 0 → Abgänge
- **Ergebnis:** Zu- und Abgänge ✅

**Wichtig:**
- Wasserschaden betrifft **alle Sattel-Typen**
- Aber: Verschiedene Produkte verwenden verschiedene Sattel-Typen
- Wenn ein Sattel-Typ = 0, können nur Produkte die diesen Typ verwenden nicht produzieren
- Produkte die andere Sattel-Typen verwenden können weiterhin produzieren (wenn deren Sattel-Typ verfügbar ist)

---

## 🎯 Zusammenfassung: Kumulierte Berechnung

### Formel:

**Kumulierter Bestand abends = Summe Zugänge - Summe Abgänge - Summe Verlustmengen**

### Beispiel:

**Ohne Wasserschaden:**
- Summe Zugänge: 300000
- Summe Abgänge: 55091
- Summe Verlustmengen: 0
- **Kumulierter Bestand:** 300000 - 55091 - 0 = **244909**

**Mit Wasserschaden:**
- Summe Zugänge: 300000
- Summe Abgänge: 55091
- Summe Verlustmengen: 3145
- **Kumulierter Bestand:** 300000 - 55091 - 3145 = **241764**

**Differenz:** 244909 - 241764 = **3145** ✅ (entspricht Verlustmenge)

---

## ✅ Prüfung: Ist die Berechnung korrekt?

### Test:

1. **Navigiere zu "5 Materiallager"**
2. **Scrolle zur Summenzeile**
3. **Prüfe für "Fizik Tundra":**
   - Summe Lagerzugang = A
   - Summe Lagerabgang = B
   - Summe Verlustmenge = C
   - Kumulierter Bestand abends = D

**Berechnung:**
- D sollte = A - B - C sein ✅
- Wenn nicht: Prüfe ob alle Tage berücksichtigt wurden

---

**Status:** ✅ **KUMULIERTE BERECHNUNG ERKLÄRT**  
**Nächster Schritt:** Prüfe Summenzeile in "5 Materiallager" um Berechnung zu verifizieren
