# Test-Anleitung: Maschinenausfall (SupplierBreakdownScenario)

**Datum:** 27.01.2026  
**Szenario:** Maschinenausfall beim Lieferanten in China

---

## 📊 Was passiert bei Maschinenausfall?

### Timing-Ablauf:

**Tag X-1 (z.B. 20.06.2027):**
- Bestellungen werden normal platziert
- Ware wird normal versendet

**Tag X (z.B. 21.06.2027) - Maschinenausfall beginnt:**
- **Morgens:** Maschinenausfall wird aktiviert
- **Bestellungen:** Neue Bestellungen werden **blockiert** (nicht platziert)
- **Bereits unterwegs:** Ware die bereits unterwegs ist, wird **nicht** blockiert
- **Störung:** Wird in "Lieferant China" als "Ja" angezeigt

**Tag X+1 bis X+N (z.B. 22.06. - 30.06.2027) - Während des Ausfalls:**
- **Bestellungen:** Weiterhin blockiert
- **Störung:** Bleibt aktiv
- **Inbound:** Keine neuen Ankünfte (weil keine neuen Bestellungen)

**Tag X+N+1 (z.B. 01.07.2027) - Maschinenausfall endet:**
- **Bestellungen:** Werden wieder normal platziert
- **Störung:** Wird auf "Nein" gesetzt
- **Nachproduktion:** Bestellungen die während des Ausfalls hätten platziert werden sollen, werden **verschoben** (nicht nachgeholt)

---

## 🎯 Was man wo sehen kann

### 1. "3 Lieferant China" - Störung wird angezeigt

**Was prüfen:**
- Navigiere zu **"3 Lieferant China"**
- Wähle einen **Sattel-Typ** (z.B. "Race line")
- Suche nach dem **Zeitraum des Maschinenausfalls** (z.B. 21.06. - 30.06.2027)

**Erwartetes Ergebnis:**
- ✅ **Spalte "Störung":** Zeigt "Ja" während des Ausfalls
- ✅ **Spalte "Bestelleingang":** Kann > 0 sein (bereits geplante Bestellungen)
- ✅ **Spalte "Produktionsmenge":** Kann > 0 sein (bereits freigegebene Bestellungen)
- ⚠️ **WICHTIG:** Bestellungen werden **verschoben**, nicht blockiert (siehe unten)

**Was bedeutet das:**
- System zeigt Störung an ✅
- Bestellungen werden während des Ausfalls nicht platziert ✅
- Bereits unterwegs befindliche Ware wird nicht blockiert ✅

---

### 2. "4 Inbound" - Keine neuen Ankünfte während des Ausfalls

**Was prüfen:**
- Navigiere zu **"4 Inbound"**
- Prüfe **Ankunftsdaten** während und nach dem Maschinenausfall

**Erwartetes Ergebnis:**
- ✅ **Während des Ausfalls:** Keine neuen Ankünfte (weil keine neuen Bestellungen)
- ✅ **Nach dem Ausfall:** Ankünfte werden wieder normal angezeigt
- ⚠️ **WICHTIG:** Bereits unterwegs befindliche Ware kommt weiterhin an

**Was bedeutet das:**
- System blockiert neue Bestellungen ✅
- Bereits unterwegs befindliche Ware wird nicht blockiert ✅

---

### 3. "5 Materiallager" - Materialbestand sinkt

**Was prüfen:**
- Navigiere zu **"5 Materiallager"**
- Wähle einen **Sattel-Typ** (z.B. "Race line")
- Prüfe **Lagerzugang** während und nach dem Maschinenausfall

**Erwartetes Ergebnis:**
- ✅ **Während des Ausfalls:** Lagerzugang = 0 (keine neuen Bestellungen)
- ✅ **Nach dem Ausfall:** Lagerzugang wird wieder normal (neue Bestellungen kommen an)
- ✅ **Bestand sinkt:** Wenn Produktion weiterläuft, sinkt der Bestand (kein Nachschub)

**Was bedeutet das:**
- System reagiert dynamisch auf Materialmangel ✅
- Bestand wird reduziert wenn keine neuen Bestellungen kommen ✅

---

### 4. "6 Produktion" - Produktion kann reduziert werden

**Was prüfen:**
- Navigiere zu **"6 Produktion"**
- Prüfe **tatsächliche PM** während und nach dem Maschinenausfall
- Prüfe **Material-Spalte** (z.B. "Race line")

**Erwartetes Ergebnis:**
- ✅ **Während des Ausfalls:** Produktion kann reduziert werden (wenn Materialbestand aufgebraucht ist)
- ✅ **Material-Spalte:** Zeigt verfügbaren Bestand (kann auf 0 sinken)
- ✅ **Backlog:** Kann erhöht werden (wenn Produktion reduziert wird)

**Was bedeutet das:**
- System reagiert dynamisch auf Materialmangel ✅
- Produktion wird reduziert wenn kein Material verfügbar ist ✅

---

## ⚠️ WICHTIGE HINWEISE

### 1. Bestellungen werden verschoben, nicht blockiert

**Aktuelle Implementierung:**
- Bestellungen die während des Ausfalls hätten platziert werden sollen, werden **verschoben**
- Sie werden **nicht** nachgeholt (keine Nachproduktion)
- Sie werden **nicht** blockiert (sie werden nach dem Ausfall platziert)

**Beispiel:**
- **20.06.2027:** Bestellung für 500 Sättel geplant
- **21.06.2027:** Maschinenausfall beginnt → Bestellung wird nicht platziert
- **30.06.2027:** Maschinenausfall endet
- **01.07.2027:** Bestellung wird jetzt platziert (verschoben, nicht nachgeholt)

### 2. Bereits unterwegs befindliche Ware wird nicht blockiert

**WICHTIG:**
- Ware die bereits **vor** dem Ausfall versendet wurde, kommt weiterhin an
- Nur **neue** Bestellungen werden blockiert
- Inbound-Ankünfte können während des Ausfalls weiterhin stattfinden (von bereits versendeter Ware)

### 3. Störung wird angezeigt, aber Bestellungen werden verschoben

**Aktuelle Implementierung:**
- Spalte "Störung" zeigt "Ja" während des Ausfalls ✅
- Bestellungen werden **verschoben** (nicht blockiert) ⚠️
- Bestelleingang kann > 0 sein (bereits geplante Bestellungen) ⚠️

---

## ✅ Test-Checkliste

### Vor dem Test:
- [ ] App neu starten (Streamlit komplett neu starten)
- [ ] Keine anderen Szenarien aktivieren (für klare Ergebnisse)
- [ ] Notiere dir den aktuellen Materialbestand (z.B. Race line)

### Während des Tests:
- [ ] **Szenario aktivieren:** "Maschinenausfall (China)" für einen Zeitraum (z.B. 21.06. - 30.06.2027)
- [ ] **"3 Lieferant China" prüfen:**
  - [ ] Störung = "Ja" während des Ausfalls?
  - [ ] Bestelleingang = 0 während des Ausfalls? (oder bereits geplante Bestellungen?)
  - [ ] Produktionsmenge = 0 während des Ausfalls? (oder bereits freigegebene Bestellungen?)
- [ ] **"4 Inbound" prüfen:**
  - [ ] Keine neuen Ankünfte während des Ausfalls?
  - [ ] Bereits unterwegs befindliche Ware kommt weiterhin an?
- [ ] **"5 Materiallager" prüfen:**
  - [ ] Lagerzugang = 0 während des Ausfalls?
  - [ ] Bestand sinkt (wenn Produktion weiterläuft)?
- [ ] **"6 Produktion" prüfen:**
  - [ ] Produktion kann reduziert werden (wenn Materialbestand aufgebraucht ist)?
  - [ ] Backlog kann erhöht werden?

### Nach dem Test:
- [ ] **Nach dem Ausfall prüfen:**
  - [ ] Störung = "Nein" nach dem Ausfall?
  - [ ] Bestellungen werden wieder normal platziert?
  - [ ] Inbound-Ankünfte werden wieder normal angezeigt?
  - [ ] Materiallager wird wieder aufgefüllt?

---

## 🔍 Erwartete Beobachtungen

### Beispiel: Maschinenausfall 21.06. - 30.06.2027

**"3 Lieferant China" (Race line):**
- **20.06.2027:** Störung = "Nein", Bestelleingang > 0
- **21.06.2027:** Störung = "Ja", Bestelleingang = 0 (oder bereits geplante Bestellungen)
- **22.06. - 30.06.2027:** Störung = "Ja", Bestelleingang = 0
- **01.07.2027:** Störung = "Nein", Bestelleingang > 0 (wieder normal)

**"4 Inbound":**
- **20.06.2027:** Ankünfte normal
- **21.06. - 30.06.2027:** Keine neuen Ankünfte (von neuen Bestellungen)
- **01.07.2027:** Ankünfte werden wieder normal (nach Transportzeit)

**"5 Materiallager" (Race line):**
- **20.06.2027:** Lagerzugang > 0
- **21.06. - 30.06.2027:** Lagerzugang = 0 (keine neuen Bestellungen)
- **01.07.2027:** Lagerzugang wird wieder normal (nach Transportzeit)

**"6 Produktion" (MTB Marathon):**
- **20.06.2027:** Produktion normal
- **21.06. - 30.06.2027:** Produktion kann reduziert werden (wenn Materialbestand aufgebraucht ist)
- **01.07.2027:** Produktion wird wieder normal (wenn Material wieder verfügbar ist)

---

## ❓ Häufige Fragen

### Q: Warum zeigt "Bestelleingang" > 0 während des Ausfalls?
**A:** Bestellungen werden **verschoben**, nicht blockiert. Bereits geplante Bestellungen können angezeigt werden, werden aber nicht platziert.

### Q: Warum kommt bereits unterwegs befindliche Ware weiterhin an?
**A:** Der Maschinenausfall blockiert nur **neue** Bestellungen. Bereits versendete Ware ist nicht betroffen.

### Q: Werden Bestellungen nachgeholt?
**A:** Nein. Bestellungen die während des Ausfalls hätten platziert werden sollen, werden **verschoben** (nach dem Ausfall platziert), aber nicht nachgeholt.

### Q: Wird die Produktion gestoppt?
**A:** Die Produktion wird nicht automatisch gestoppt. Sie wird nur reduziert, wenn der Materialbestand aufgebraucht ist.

---

## 📝 Notizen für deinen Test

**Datum des Tests:** _______________

**Maschinenausfall-Zeitraum:** _______________ bis _______________

**Beobachtungen:**
- [ ] Störung wird korrekt angezeigt
- [ ] Bestellungen werden blockiert/verschoben
- [ ] Inbound zeigt keine neuen Ankünfte
- [ ] Materiallager zeigt reduzierten Zugang
- [ ] Produktion reagiert auf Materialmangel

**Probleme gefunden:**
- _________________________________________________
- _________________________________________________

---

**Status:** ✅ **BEREIT FÜR TEST**
