# Ursachen-Analyse: Ergebnis

## Prüfung der möglichen Ursachen

### 1. ✅ Backlog-Berechnung: KORREKT

**Logik:**
```python
Backlog = geplante PM - fertiggestellte PM + Backlog gestern
```

**Prüfung an Beispiel:**
- 12.01.2027: Backlog = 222 - 854 + 1332 = 700 ✅

**Ergebnis:** Die Backlog-Berechnung ist korrekt.

---

### 2. ✅ Produktionslogik (Rang 5-8): KORREKT

**Logik:**
```python
base_qty = min(demand, proportional, minimal)
remaining_demand = demand - base_qty
rest_production = min(remaining_capacity, minimal, remaining_demand)
scheduled_qty = base_qty + rest_production
```

**Mathematische Prüfung:**
- `base_qty <= demand` ✅
- `remaining_demand = demand - base_qty` ✅
- `rest_production <= remaining_demand` ✅
- Also: `scheduled_qty = base_qty + rest_production <= base_qty + remaining_demand = demand` ✅

**Ergebnis:** Die Produktionslogik stellt sicher, dass `scheduled_qty <= demand` ist.

---

### 3. ⚠️ Sicherheitsprüfung: NUR KAPAZITÄT, NICHT PRODUKTIONSBEDARF

**Aktuelle Logik:**
```python
if total_scheduled > daily_capacity:
    # Proportionale Reduktion
```

**Problem:** Die Prüfung stellt sicher, dass die Summe nicht die **Kapazität** überschreitet, aber sie prüft NICHT, ob die Summe den **Produktionsbedarf** überschreitet.

**Beispiel:**
- Produktionsbedarf (gesamt) = 1000
- Kapazität = 3120
- Summe(scheduled_production) = 1500
- Prüfung: 1500 < 3120 ✅ (keine Reduktion)
- ABER: 1500 > 1000 ❌ (mehr produziert als benötigt)

**ABER:** Das sollte nicht passieren, weil `scheduled_qty <= demand` für jedes Produkt gilt, also sollte auch `Summe(scheduled_qty) <= Summe(demand)` gelten.

**Ergebnis:** Die Sicherheitsprüfung ist ausreichend, weil die Produktionslogik bereits sicherstellt, dass `scheduled_qty <= demand` ist.

---

### 4. 🔍 DAS EIGENTLICHE PROBLEM: Backlog wird mehrfach berücksichtigt

**Problem:** Die "Tatsächliche PM" wird mit `Produktionsbedarf = Nachfrage + Backlog` berechnet. Aber wenn der Backlog über mehrere Tage aufgebaut wird und dann abgearbeitet wird, wird er mehrfach in der Summe berücksichtigt.

**Beispiel:**
- **Tag 1:** Geplante PM = 222, Backlog = 0 → Produktionsbedarf = 222, Tatsächliche PM = 0 (kein Material) → Backlog = 222
- **Tag 2:** Geplante PM = 222, Backlog = 222 → Produktionsbedarf = 444, Tatsächliche PM = 0 (kein Material) → Backlog = 444
- **Tag 3:** Geplante PM = 222, Backlog = 444 → Produktionsbedarf = 666, Tatsächliche PM = 0 (kein Material) → Backlog = 666
- **Tag 4:** Geplante PM = 222, Backlog = 666 → Produktionsbedarf = 888, Tatsächliche PM = 0 (kein Material) → Backlog = 888
- **Tag 5:** Geplante PM = 222, Backlog = 888 → Produktionsbedarf = 1110, Tatsächliche PM = 854 (Material verfügbar) → Backlog = 1332

**Summe:**
- Geplante PM: 222 * 5 = 1110
- Tatsächliche PM: 0 + 0 + 0 + 0 + 854 = 854
- Backlog am Ende: 1332

**Problem:** Der Backlog von 1332 wurde durch die "Tatsächliche PM" von 854 reduziert, aber die "Tatsächliche PM" wurde mit einem Produktionsbedarf von 1110 berechnet (222 + 888). Das bedeutet, dass der Backlog von 888 in der "Tatsächlichen PM" berücksichtigt wurde, aber er wurde nicht vollständig abgearbeitet.

**Aber:** Das ist korrekt! Die "Tatsächliche PM" sollte auf Basis des Backlogs berechnet werden, um den Backlog abzuarbeiten.

---

## Die wahre Ursache: Backlog-Aufarbeitung über mehrere Tage

**Das Problem ist nicht die Logik, sondern die Natur der Backlog-Aufarbeitung:**

1. Wenn Material fehlt, kann nicht produziert werden → Backlog wächst
2. Wenn Material wieder verfügbar ist, wird versucht, den Backlog abzuarbeiten
3. Die "Tatsächliche PM" ist dann höher als die "Geplante PM" (weil Backlog mit einbezogen wird)
4. Über das Jahr hinweg summiert sich das zu einer höheren Gesamtproduktion

**Mathematisch:**
```
Summe(Tatsächliche PM) = Summe(Geplante PM) + Summe(Backlog-Aufarbeitung) - Endbacklog
```

**In deinem Fall:**
- Summe(Geplante PM) = 111000
- Summe(Tatsächliche PM) = 132678
- Differenz = 21678
- Endbacklog = 435

**Das bedeutet:**
- Es wurde 21678 mehr produziert als nachgefragt wurde
- ABER: Es gibt einen Endbacklog von 435, also wurde nicht genug produziert, um alle Nachfrage zu decken

**Das ist widersprüchlich!**

---

## Die Lösung: Prüfe die Backlog-Berechnung genauer

**Verdacht:** Der Backlog wird nicht korrekt reduziert, wenn "Fertiggestellte PM" > "Geplante PM" ist.

**Beispiel:**
- Geplante PM = 222
- Fertiggestellte PM = 854 (vom Vortag)
- Backlog gestern = 1332
- Neuer Backlog = 222 - 854 + 1332 = 700 ✅

**Das ist korrekt!** Der Backlog wird korrekt reduziert.

**ABER:** Wenn die "Fertiggestellte PM" höher ist als die "Geplante PM", wird mehr "fertiggestellt" als "nachgefragt" wurde. Das bedeutet, dass der Backlog reduziert wird, aber die "Tatsächliche PM" wurde bereits mit dem höheren Backlog berechnet.

**Das Problem:** Die "Tatsächliche PM" wird einmal berechnet (mit Backlog), aber wenn der Backlog später reduziert wird (durch "Fertiggestellte PM"), wird die "Tatsächliche PM" nicht neu berechnet.

**ABER:** Das ist korrekt! Die "Tatsächliche PM" sollte auf Basis des Backlogs vom Vortag berechnet werden, nicht auf Basis des reduzierten Backlogs.

---

## Fazit

**Die Ursache ist NICHT ein Fehler in der Logik, sondern die Natur der Backlog-Aufarbeitung:**

1. Wenn Material fehlt, wächst der Backlog
2. Wenn Material wieder verfügbar ist, wird versucht, den Backlog abzuarbeiten
3. Die "Tatsächliche PM" ist dann höher als die "Geplante PM" (weil Backlog mit einbezogen wird)
4. Über das Jahr hinweg summiert sich das zu einer höheren Gesamtproduktion

**ABER:** Die Summe der "Tatsächlichen PM" sollte eigentlich nicht höher sein als die Summe der "Geplanten PM", es sei denn, es gibt einen Anfangsbacklog (den es nicht gibt).

**Das bedeutet:** Es gibt einen Fehler, aber er liegt nicht in der Produktionslogik, sondern möglicherweise in der Backlog-Berechnung oder in der Art, wie die "Tatsächliche PM" mit dem Backlog verknüpft ist.

**Nächster Schritt:** Prüfe, ob die "Tatsächliche PM" korrekt auf Basis des Produktionsbedarfs (Nachfrage + Backlog) berechnet wird, und ob der Backlog korrekt reduziert wird, wenn "Fertiggestellte PM" > "Geplante PM" ist.
