# Dynamische Reaktion: Wo man sie sieht

**Datum:** 27.01.2026  
**Ziel:** Übersicht wo man die dynamische Reaktion auf Wasserschaden sieht

---

## 📊 Übersicht: Sattel-Typen und verwendete Produkte

### Sattel-Typen in der BOM:
1. **Spark** → MTB Allrounder, MTB Extreme
2. **Speed line** → MTB Competition, MTB Trail
3. **Fizik Tundra** → MTB Downhill, MTB Freeride, MTB Performance
4. **Race line** → MTB Marathon

**Hinweis:** "Raceline" existiert nicht in der BOM. Möglicherweise meinst du **"Race line"** (mit Leerzeichen)?

---

## 🎯 Wo sehe ich die dynamische Reaktion?

### 1. "5 Materiallager" - Bestand wird auf 0 gesetzt

**Was prüfen:**
- Navigiere zu **"5 Materiallager"**
- Suche nach **Tag 22.02.2027** (Wasserschaden-Tag)
- Prüfe für **alle Sattel-Typen** (Spark, Speed line, Fizik Tundra, Race line)

**Erwartetes Ergebnis:**
- ✅ **Verlustmenge:** = Bestand morgens vor Schaden (z.B. 480 für Race line)
- ✅ **Bestand morgens:** 0 (nach Wasserschaden)
- ✅ **Lagerabgang:** 0 (keine Produktion möglich)
- ✅ **Bestand abends:** 0 (nach Wasserschaden)

**Was bedeutet das:**
- System hat Bestand auf 0 gesetzt ✅
- Produktion kann nicht laufen (kein Material) ✅

**Konkrete Prüfung:**
- **Race line:** Verlustmenge = 480 → Bestand morgens = 0 → Lagerabgang = 0 ✅
- **Fizik Tundra:** Verlustmenge = 3145 → Bestand morgens = 0 → Lagerabgang = 0 ✅

---

### 2. "6 Produktion" - Produktion wird auf 0 reduziert

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Suche nach **Tag 22.02.2027**
- Prüfe für **Produkte die betroffene Sattel-Typen verwenden**

**Welche Produkte sind betroffen?**

**Wenn Race line betroffen:**
- **MTB Marathon** verwendet "Race line"
- Prüfe: **MTB Marathon** → tatsächliche PM = 0 ✅

**Wenn Fizik Tundra betroffen:**
- **MTB Downhill** verwendet "Fizik Tundra"
- **MTB Freeride** verwendet "Fizik Tundra"
- **MTB Performance** verwendet "Fizik Tundra"
- Prüfe: Diese Produkte → tatsächliche PM = 0 ✅

**Wenn Spark betroffen:**
- **MTB Allrounder** verwendet "Spark"
- **MTB Extreme** verwendet "Spark"
- Prüfe: Diese Produkte → tatsächliche PM = 0 ✅

**Wenn Speed line betroffen:**
- **MTB Competition** verwendet "Speed line"
- **MTB Trail** verwendet "Speed line"
- Prüfe: Diese Produkte → tatsächliche PM = 0 ✅

**Erwartetes Ergebnis:**
- ✅ **geplante PM:** Gleich (Nachfrage ändert sich nicht)
- ✅ **tatsächliche PM:** 0 (keine Produktion wegen Materialmangel)
- ✅ **Material-Spalte (z.B. Race line):** 0 (kein Material verfügbar)
- ✅ **Backlog:** Erhöht (Nachfrage bleibt, Produktion = 0)

**Was bedeutet das:**
- System hat Produktion auf 0 reduziert ✅
- System reagiert dynamisch auf Materialmangel ✅
- Backlog entsteht automatisch ✅

---

### 3. "7 Fertigproduktelager" - Keine neuen Endprodukte

**Was prüfen:**
- Navigiere zu **"7 Fertigproduktelager"**
- Suche nach **Tag 22.02.2027**
- Prüfe für **betroffene Produkte**

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
- Suche nach **Tag 21-23.02.2027**
- Prüfe **Backlog-Spalte** für betroffene Produkte

**Erwartetes Ergebnis:**
- ✅ **Tag 21.02.2027:** Backlog = z.B. 50
- ✅ **Tag 22.02.2027:** Backlog = z.B. 150 (erhöht, weil Produktion = 0)
- ✅ **Tag 23.02.2027:** Backlog = z.B. 250 (weiter erhöht, wenn Produktion noch = 0)

**Was bedeutet das:**
- Backlog entsteht automatisch wenn Produktion < Nachfrage ✅
- System reagiert dynamisch auf Materialmangel ✅

---

## 📋 Konkrete Prüfung: Race line (Verlustmenge 480)

### Schritt 1: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach "Race line"**
3. **Prüfe Tag 22.02.2027:**
   - Verlustmenge = 480 ✅
   - Bestand morgens = 0 ✅
   - Lagerabgang = 0 ✅
   - Bestand abends = 0 ✅

### Schritt 2: Produktion prüfen
1. **Navigiere zu "6 Produktion"**
2. **Suche nach "MTB Marathon"** (verwendet Race line)
3. **Prüfe Tag 22.02.2027:**
   - tatsächliche PM = 0 ✅
   - Race line (Material-Spalte) = 0 ✅
   - Backlog = erhöht ✅

### Schritt 3: Backlog-Verlauf prüfen
1. **Navigiere zu "6 Produktion"**
2. **Prüfe Backlog für "MTB Marathon" Tag 21-23.02.2027:**
   - Tag 21: Backlog = _______
   - Tag 22: Backlog = _______ (erhöht) ✅
   - Tag 23: Backlog = _______ (weiter erhöht wenn Produktion noch = 0) ✅

### Schritt 4: Fertigproduktelager prüfen
1. **Navigiere zu "7 Fertigproduktelager"**
2. **Suche nach "MTB Marathon"**
3. **Prüfe Tag 22.02.2027:**
   - Lagerzugang = 0 ✅
   - Lagerabgang = kann > 0 sein ✅
   - Bestand = sinkt ✅

---

## 📋 Konkrete Prüfung: Fizik Tundra (Verlustmenge 3145)

### Schritt 1: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach "Fizik Tundra"**
3. **Prüfe Tag 22.02.2027:**
   - Verlustmenge = 3145 ✅
   - Bestand morgens = 0 ✅
   - Lagerabgang = 0 ✅
   - Bestand abends = 0 ✅

### Schritt 2: Produktion prüfen
1. **Navigiere zu "6 Produktion"**
2. **Prüfe für "MTB Downhill", "MTB Freeride", "MTB Performance"** (verwenden Fizik Tundra)
3. **Prüfe Tag 22.02.2027:**
   - tatsächliche PM = 0 ✅
   - Fizik Tundra (Material-Spalte) = 0 ✅
   - Backlog = erhöht ✅

### Schritt 3: Backlog-Verlauf prüfen
1. **Navigiere zu "6 Produktion"**
2. **Prüfe Backlog für betroffene Produkte Tag 21-23.02.2027:**
   - Tag 21: Backlog = _______
   - Tag 22: Backlog = _______ (erhöht) ✅
   - Tag 23: Backlog = _______ (weiter erhöht wenn Produktion noch = 0) ✅

---

## ✅ Zusammenfassung: Dynamische Reaktion sichtbar

### Materiallager (5 Materiallager):
- ✅ **Bestand morgens = 0** (nach Wasserschaden)
- ✅ **Lagerabgang = 0** (keine Produktion möglich)
- ✅ **Verlustmenge = Bestand morgens vor Schaden**

### Produktion (6 Produktion):
- ✅ **tatsächliche PM = 0** (keine Produktion wegen Materialmangel)
- ✅ **Material-Spalte = 0** (kein Material verfügbar)
- ✅ **Backlog erhöht** (Nachfrage bleibt, Produktion = 0)

### Fertigproduktelager (7 Fertigproduktelager):
- ✅ **Lagerzugang = 0** (keine neuen Endprodukte)
- ✅ **Lagerabgang kann > 0 sein** (Nachfrage wird aus Bestand bedient)
- ✅ **Bestand sinkt** (mehr Abgang als Zugang)

---

**Status:** ✅ **DYNAMISCHE REAKTION DOKUMENTIERT**  
**Nächster Schritt:** Tests durchführen um dynamische Reaktion zu verifizieren
