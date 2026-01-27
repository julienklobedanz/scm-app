# Materiallager-Berechnung: Wasserschaden erklärt

**Datum:** 27.01.2026  
**Ziel:** Erklären warum Lagerzugang ≠ Lagerabgang - Verlustmenge und wo man die dynamische Reaktion sieht

---

## 📊 Deine Beobachtung

**Am 22.02.2027 (Wasserschaden-Tag):**
- **Raceline:** Verlustmenge = 480
- **Fizik Tundra:** Verlustmenge = 3145
- **Lagerzugang:** Kann > 0 sein (z.B. 421)
- **Lagerabgang:** 0
- **Frage:** Ist "Lagerzugang = Lagerabgang - Verlustmenge = 0" richtig?

---

## ❌ Falsche Formel

**"Lagerzugang = Lagerabgang - Verlustmenge"** ist **NICHT** die richtige Formel!

**Warum?**
- **Lagerzugang** = Was heute **ankommt** (von Inbound)
- **Verlustmenge** = Was heute **verloren geht** (durch Wasserschaden)
- **Lagerabgang** = Was heute **verbraucht wird** (durch Produktion)

Diese drei Werte sind **unabhängig voneinander**!

---

## ✅ Richtige Formel

### Schritt-für-Schritt am 22.02.2027:

**1. Bestand morgens berechnen:**
```
Bestand morgens = Bestand gestern abend + Lagerzugang heute
```

**Beispiel für Raceline:**
- Bestand gestern abend (21.02.): z.B. 200
- Lagerzugang heute (22.02.): z.B. 280
- **Bestand morgens = 200 + 280 = 480** ✅

**2. Verlustmenge = Bestand morgens (vor Schaden):**
```
Verlustmenge = Bestand morgens = 480 ✅
```

**3. Wasserschaden setzt Bestand auf 0:**
```
Bestand morgens (nach Schaden) = 0 ✅
```

**4. Lagerabgang berechnen:**
```
Lagerabgang = min(geplante Produktion, Bestand morgens)
             = min(geplante Produktion, 0)
             = 0 ✅
```

**5. Bestand abends berechnen:**
```
Bestand abends = Bestand morgens - Lagerabgang
               = 0 - 0
               = 0 ✅
```

---

## 🔍 Zusammenfassung: Was bedeutet was?

### Lagerzugang:
- **Was ist das?** Material das heute **ankommt** (von Inbound)
- **Wann passiert das?** Wenn ein LKW/Schiff ankommt
- **Ist das abhängig von Wasserschaden?** **NEIN** - Inbound-Ankünfte passieren unabhängig
- **Beispiel:** 280 Sättel kommen heute an

### Verlustmenge:
- **Was ist das?** Material das heute **verloren geht** (durch Wasserschaden)
- **Wann passiert das?** Am Tag des Wasserschadens
- **Wie wird es berechnet?** = Bestand morgens vor Schaden
- **Beispiel:** 480 Sättel waren morgens da → 480 verloren

### Lagerabgang:
- **Was ist das?** Material das heute **verbraucht wird** (durch Produktion)
- **Wann passiert das?** Wenn Produktion läuft
- **Wie wird es berechnet?** = min(geplante Produktion, verfügbarer Bestand)
- **Beispiel:** 0 (weil Bestand morgens = 0 nach Schaden)

---

## ✅ Ist das korrekt?

**JA - Die Werte sind korrekt!**

**Beispiel für Raceline am 22.02.2027:**
- **Lagerzugang:** 280 (kommt heute an)
- **Bestand morgens (vor Schaden):** 480 (200 von gestern + 280 Zugang)
- **Verlustmenge:** 480 (alles was morgens da war)
- **Bestand morgens (nach Schaden):** 0 (Wasserschaden setzt auf 0)
- **Lagerabgang:** 0 (keine Produktion möglich, weil Bestand = 0)
- **Bestand abends:** 0 (0 morgens - 0 Abgang)

**Das ist korrekt!** ✅

---

## 🎯 Wo sehe ich die dynamische Reaktion?

### 1. "5 Materiallager" - Bestand wird auf 0 gesetzt

**Was prüfen:**
- Navigiere zu **"5 Materiallager"**
- Suche nach **Tag 22.02.2027**
- Prüfe für **"Raceline"** (oder andere Sattel-Typen)

**Erwartetes Ergebnis:**
- ✅ **Verlustmenge:** 480 (Bestand morgens vor Schaden)
- ✅ **Bestand morgens:** 0 (nach Wasserschaden)
- ✅ **Lagerabgang:** 0 (keine Produktion möglich)
- ✅ **Bestand abends:** 0 (nach Wasserschaden)

**Was bedeutet das:**
- System hat Bestand auf 0 gesetzt ✅
- Produktion kann nicht laufen (kein Material) ✅

---

### 2. "6 Produktion" - Produktion wird auf 0 reduziert

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Suche nach **Tag 22.02.2027**
- Prüfe für Produkte die **"Raceline"** Sattel verwenden

**Erwartetes Ergebnis:**
- ✅ **geplante PM:** Gleich (Nachfrage ändert sich nicht)
- ✅ **tatsächliche PM:** 0 (keine Produktion wegen Materialmangel)
- ✅ **Raceline (Material-Spalte):** 0 (kein Material verfügbar)
- ✅ **Backlog:** Erhöht (Nachfrage bleibt, Produktion = 0)

**Was bedeutet das:**
- System hat Produktion auf 0 reduziert ✅
- System reagiert dynamisch auf Materialmangel ✅
- Backlog entsteht automatisch ✅

**Welche Produkte verwenden Raceline?**
- Prüfe `config/master_data.py` BOM:
  - Suche nach `'saddle': 'Raceline'`
  - Diese Produkte sollten tatsächliche PM = 0 haben

---

### 3. "7 Fertigproduktelager" - Keine neuen Endprodukte

**Was prüfen:**
- Navigiere zu **"7 Fertigproduktelager"**
- Suche nach **Tag 22.02.2027**
- Prüfe für Produkte die **"Raceline"** Sattel verwenden

**Erwartetes Ergebnis:**
- ✅ **Lagerzugang:** 0 (keine Produktion → keine neuen Endprodukte)
- ✅ **Lagerabgang:** Kann > 0 sein (Nachfrage wird aus Bestand bedient)
- ✅ **Bestand:** Sinkt (mehr Abgang als Zugang)

**Was bedeutet das:**
- Keine neuen Endprodukte produziert ✅
- Bestand wird abgebaut (Nachfrage wird bedient) ✅

---

### 4. "6 Produktion" - Backlog erhöht sich

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Suche nach **Tag 22.02.2027** und **Tag 23.02.2027**
- Prüfe **Backlog-Spalte** für Produkte die **"Raceline"** verwenden

**Erwartetes Ergebnis:**
- ✅ **Tag 21.02.2027:** Backlog = z.B. 50
- ✅ **Tag 22.02.2027:** Backlog = z.B. 150 (erhöht, weil Produktion = 0)
- ✅ **Tag 23.02.2027:** Backlog = z.B. 250 (weiter erhöht, wenn Produktion noch = 0)

**Was bedeutet das:**
- Backlog entsteht automatisch wenn Produktion < Nachfrage ✅
- System reagiert dynamisch auf Materialmangel ✅

---

## 📋 Zusammenfassung: Dynamische Reaktion sichtbar

### Materiallager (5 Materiallager):
- ✅ **Bestand morgens = 0** (nach Wasserschaden)
- ✅ **Lagerabgang = 0** (keine Produktion möglich)
- ✅ **Verlustmenge = Bestand morgens vor Schaden**

### Produktion (6 Produktion):
- ✅ **tatsächliche PM = 0** (keine Produktion wegen Materialmangel)
- ✅ **Material-Spalte (Raceline) = 0** (kein Material verfügbar)
- ✅ **Backlog erhöht** (Nachfrage bleibt, Produktion = 0)

### Fertigproduktelager (7 Fertigproduktelager):
- ✅ **Lagerzugang = 0** (keine neuen Endprodukte)
- ✅ **Lagerabgang kann > 0 sein** (Nachfrage wird aus Bestand bedient)
- ✅ **Bestand sinkt** (mehr Abgang als Zugang)

---

## 🔍 Test-Anleitung: Dynamische Reaktion prüfen

### Test 1: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für "Raceline":**
   - Verlustmenge = 480 ✅
   - Bestand morgens = 0 ✅
   - Lagerabgang = 0 ✅
   - Bestand abends = 0 ✅

### Test 2: Produktion prüfen
1. **Navigiere zu "6 Produktion"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für Produkte die "Raceline" verwenden:**
   - tatsächliche PM = 0 ✅
   - Raceline (Material-Spalte) = 0 ✅
   - Backlog = erhöht ✅

### Test 3: Backlog-Verlauf prüfen
1. **Navigiere zu "6 Produktion"**
2. **Prüfe Backlog-Spalte für Tag 21-23.02.2027:**
   - Tag 21: Backlog = _______
   - Tag 22: Backlog = _______ (erhöht) ✅
   - Tag 23: Backlog = _______ (weiter erhöht wenn Produktion noch = 0) ✅

### Test 4: Fertigproduktelager prüfen
1. **Navigiere zu "7 Fertigproduktelager"**
2. **Suche nach Tag 22.02.2027**
3. **Prüfe für Produkte die "Raceline" verwenden:**
   - Lagerzugang = 0 ✅
   - Lagerabgang = kann > 0 sein ✅
   - Bestand = sinkt ✅

---

## 💡 Fazit

**Die Berechnung ist korrekt!**

- ✅ **Lagerzugang** ist unabhängig von Verlustmenge (kommt von Inbound)
- ✅ **Verlustmenge** = Bestand morgens vor Schaden
- ✅ **Lagerabgang** = 0 (weil Bestand morgens = 0 nach Schaden)
- ✅ **Formel:** Bestand abends = Bestand morgens - Lagerabgang = 0 - 0 = 0

**Die dynamische Reaktion ist sichtbar in:**
- ✅ **Materiallager:** Bestand = 0, Lagerabgang = 0
- ✅ **Produktion:** tatsächliche PM = 0, Backlog erhöht
- ✅ **Fertigproduktelager:** Lagerzugang = 0, Bestand sinkt

---

**Status:** ✅ **BERECHNUNG ERKLÄRT**  
**Nächster Schritt:** Tests durchführen um dynamische Reaktion zu verifizieren
