# Rückverfolgung: Marketing-Mengen → Lieferant China → Inbound

**Datum:** 27.01.2026  
**Ziel:** Nachvollziehen wie zusätzliche Marketing-Mengen in Bestellungen und Inbound sichtbar werden

---

## 📊 Deine Beobachtungen (Marketing aktiviert)

### Volumenplanung:
- **MTB Downhill wöchentlich:** Geplant 555 → Tatsächlich 881 (+326, +58.7%)
- **MTB Downhill täglich (22.02.2027):** Geplant 111 → Tatsächlich 166 (+55, +49.5%)

### Produktion:
- **MTB Downhill (22.02.2027):** 
  - "geplante PM" = 2291
  - "tatsächliche PM" = 166
  - "Fizik Tundra" (Material) = 2291

---

## 🔍 Rückverfolgung: Wo finde ich die zusätzlichen Mengen?

### Schritt 1: Materialbedarf berechnen

**MTB Downhill verwendet:** "Fizik Tundra" Sattel (1:1 Verhältnis)

**Ohne Marketing (Referenz):**
- Geplante Nachfrage Tag 22.02.2027: **111**
- Benötigtes Material (Fizik Tundra): **111**

**Mit Marketing (1.5x Faktor):**
- Tatsächliche Nachfrage Tag 22.02.2027: **166**
- Benötigtes Material (Fizik Tundra): **166**
- **Zusätzliche Menge:** 166 - 111 = **+55 Fizik Tundra**

---

### Schritt 2: In "Lieferant China" prüfen

**Wo schauen:**
1. **Navigiere zu "3 Lieferant China"**
2. **Suche nach Bestellungen für "Fizik Tundra"** (oder allgemein "Sättel")
3. **Prüfe Bestellungen um Tag 22.02.2027:**

**Was du finden solltest:**
- Bestellungen die **nach** Aktivierung des Marketings erstellt wurden
- Diese Bestellungen sollten **höhere Mengen** enthalten als ohne Marketing

**Konkrete Prüfung:**
- **Bestelltag:** Suche Bestellungen die ca. **49 Tage VOR 22.02.2027** erstellt wurden
  - 22.02.2027 - 49 Tage = ca. **04.01.2027** (Bestelltag)
- **Bestellmenge:** Sollte die erhöhte Nachfrage reflektieren
- **Vergleich:** 
  - Ohne Marketing: Bestellung für ~111 Fizik Tundra
  - Mit Marketing: Bestellung für ~166 Fizik Tundra (oder mehr, je nach Vorlaufzeit)

**Zu dokumentieren:**
- Bestelltag = _______
- Bestellmenge Fizik Tundra = _______
- Erwartete Menge ohne Marketing = _______
- Differenz = _______

---

### Schritt 3: In "Inbound" prüfen

**Wo schauen:**
1. **Navigiere zu "4 Inbound"**
2. **Suche nach Ankünften für "Fizik Tundra"**
3. **Prüfe Ankünfte um Tag 22.02.2027:**

**Was du finden solltest:**
- Ankünfte die **am oder vor 22.02.2027** stattfinden
- Diese sollten die erhöhten Mengen enthalten

**Konkrete Prüfung:**
- **Ankunftsdatum:** Suche nach "Tatsächliche Ankunft LKW 🇩🇪" = **22.02.2027** (oder früher)
- **Menge Fizik Tundra:** Sollte erhöht sein
- **Vergleich:**
  - Ohne Marketing: ~111 Fizik Tundra
  - Mit Marketing: ~166 Fizik Tundra (oder mehr)

**Zu dokumentieren:**
- Ankunftsdatum = _______
- Menge Fizik Tundra = _______
- Erwartete Menge ohne Marketing = _______
- Differenz = _______

---

## ⚠️ WICHTIG: Timing-Verständnis

### Bestellzyklus:
1. **Tag 0 (z.B. 04.01.2027):** Bestellung wird erstellt
   - Basierend auf **prognostizierter Nachfrage** (inkl. Marketing)
2. **Tag 49 (z.B. 22.02.2027):** Ware kommt an (Inbound)
   - **Vorlaufzeit:** 49 Tage (Standard für China)
3. **Tag 49+:** Ware wird für Produktion verwendet

### Marketing-Effekt:
- **Marketing aktiviert:** Tag 50-60 (19.02.2027 - 01.03.2027)
- **Bestellung erstellt:** Muss **vor** Tag 50 sein (ca. Tag 0-1, also 01.01.2027 - 02.01.2027)
- **Ware kommt an:** Tag 49+ (ca. 19.02.2027+)

**Problem:** Wenn Marketing erst am Tag 50 aktiviert wird, aber Bestellungen bereits am Tag 0-1 erstellt wurden, dann:
- Bestellungen enthalten **KEINE** Marketing-Mengen (weil Marketing noch nicht aktiv war)
- Inbound enthält **KEINE** zusätzlichen Mengen
- **ABER:** Produktion versucht trotzdem mehr zu produzieren → Materialmangel möglich

---

## 🔍 Alternative Prüfung: Materiallager

**Wenn Bestellungen/Inbound keine zusätzlichen Mengen zeigen:**

1. **Navigiere zu "5 Materiallager"**
2. **Prüfe "Fizik Tundra" Bestand:**
   - **Tag 22.02.2027:** Bestand morgens = _______
   - **Tag 22.02.2027:** Bestand abends = _______
   - **Tag 23.02.2027:** Bestand morgens = _______

**Erwartetes Ergebnis:**
- Wenn keine zusätzlichen Bestellungen: Bestand sollte **schneller sinken**
- Produktion verbraucht mehr Material als nachgeliefert wird
- Bestand geht gegen 0 (Materialmangel)

**Zu dokumentieren:**
- Bestand Tag 22.02.2027 morgens = _______
- Bestand Tag 22.02.2027 abends = _______
- Bestand Tag 23.02.2027 morgens = _______
- Tendenz: Steigend / Fallend / Konstant

---

## 📋 Zusammenfassung: Was du prüfen solltest

### Option 1: Bestellungen enthalten Marketing-Mengen
1. ✅ "3 Lieferant China" → Bestellungen für Fizik Tundra → Höhere Mengen
2. ✅ "4 Inbound" → Ankünfte → Höhere Mengen
3. ✅ "5 Materiallager" → Bestand bleibt stabil/steigt

### Option 2: Bestellungen enthalten KEINE Marketing-Mengen (erwartet)
1. ⚠️ "3 Lieferant China" → Bestellungen → Normale Mengen (ohne Marketing)
2. ⚠️ "4 Inbound" → Ankünfte → Normale Mengen (ohne Marketing)
3. ⚠️ "5 Materiallager" → Bestand sinkt schnell (Materialmangel)
4. ⚠️ "6 Produktion" → Produktion reduziert wegen Materialmangel

---

## 🎯 Konkrete Test-Schritte

### Test 1: Bestellungen prüfen
1. **Navigiere zu "3 Lieferant China"**
2. **Suche nach Bestellungen für "Fizik Tundra"**
3. **Prüfe Bestellungen erstellt um 01.01.2027 - 02.01.2027**
4. **Notiere:** Bestellmenge = _______

### Test 2: Inbound prüfen
1. **Navigiere zu "4 Inbound"**
2. **Suche nach Ankünften für "Fizik Tundra"**
3. **Prüfe Ankünfte am 22.02.2027 (oder früher)**
4. **Notiere:** Ankunftsmenge = _______

### Test 3: Materiallager prüfen
1. **Navigiere zu "5 Materiallager"**
2. **Suche nach "Fizik Tundra"**
3. **Prüfe Bestand Tag 22.02.2027**
4. **Notiere:** Bestand morgens = _______, Bestand abends = _______

### Test 4: Vergleich ohne Marketing
1. **Deaktiviere Marketing** in Sidebar
2. **Warte bis Seite neu geladen ist**
3. **Wiederhole Test 1-3**
4. **Vergleiche Werte**

---

## 💡 Erwartetes Ergebnis

**Wahrscheinlich:** Bestellungen und Inbound enthalten **KEINE** zusätzlichen Marketing-Mengen, weil:
- Marketing wird erst am Tag 50 aktiviert
- Bestellungen werden bereits am Tag 0-1 erstellt (vor Marketing)
- System reagiert auf Materialmangel durch reduzierte Produktion

**Das ist korrekt!** Das System zeigt realistisch, dass:
- Spontane Marketing-Kampagnen nicht sofort zu mehr Material führen
- Produktion wird durch Materialmangel begrenzt
- Backlog entsteht (wie du siehst: Backlog = 166 am 22.02.2027)

---

**Status:** ✅ **RÜCKVERFOLGUNG ERKLÄRT**  
**Nächster Schritt:** Führe die Tests durch und dokumentiere die Ergebnisse
