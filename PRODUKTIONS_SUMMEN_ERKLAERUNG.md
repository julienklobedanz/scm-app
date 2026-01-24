# Erklärung: Warum ist "Tatsächliche PM" höher als "Geplante PM"?

## Die Logik im Detail

### 1. Geplante PM (Nachfrage)
- **Definition:** Tagesbedarf (Nachfrage) OHNE Backlog
- **Berechnung:** Direkt aus `daily_demands_actual[day]` (mit Marketing)
- **Summe über Jahr:** Gesamtnachfrage = **111000**

### 2. Tatsächliche PM (Produktion)
- **Definition:** Produktion, die heute geplant wird
- **Berechnung:** 
  ```
  Produktionsbedarf = Nachfrage + Backlog vom Vortag
  Tatsächliche PM = MIN(Produktionsbedarf, Kapazität, Material)
  ```
- **Summe über Jahr:** Gesamtproduktion = **132678**

### 3. Fertiggestellte PM (Fertigstellung)
- **Definition:** Produktion vom vorherigen Arbeitstag, die heute fertiggestellt wird
- **Berechnung:** `fertiggestellte PM[Tag X] = tatsächliche PM[Tag X-1]` (nur an Arbeitstagen)
- **Summe über Jahr:** Sollte = Gesamtproduktion sein (wenn alles fertiggestellt wird)

---

## Warum ist "Tatsächliche PM" höher als "Geplante PM"?

### Die Antwort: **Backlog-Aufarbeitung**

**Beispiel:**
- **Tag 1:** Geplante PM = 222, Backlog = 0 → Produktionsbedarf = 222 + 0 = 222
- **Tag 2:** Geplante PM = 222, Backlog = 222 (weil Tag 1 nicht produziert wurde) → Produktionsbedarf = 222 + 222 = 444
- **Tag 3:** Geplante PM = 222, Backlog = 444 (weil Tag 2 nicht produziert wurde) → Produktionsbedarf = 222 + 444 = 666

**Problem:** Wenn Material fehlt, kann nicht produziert werden. Der Backlog wächst, und wenn Material wieder verfügbar ist, wird mehr produziert als die heutige Nachfrage, um den Backlog abzuarbeiten.

### Mathematische Beziehung

```
Summe(Tatsächliche PM) = Summe(Geplante PM) + Endbacklog - Anfangsbacklog
```

**In deinem Fall:**
- Summe(Geplante PM) = 111000
- Summe(Tatsächliche PM) = 132678
- Differenz = 21678

**Das bedeutet:**
- Am Ende des Jahres gibt es einen **Endbacklog von 21678** (oder mehr, wenn Anfangsbacklog vorhanden war)
- Oder: Es wurde insgesamt **21678 mehr produziert als nachgefragt** (was nicht sein sollte, außer es gibt einen Endbacklog)

---

## Das eigentliche Problem

**Die Summe der "Tatsächlichen PM" sollte NICHT höher sein als die Summe der "Geplanten PM", es sei denn:**
1. Es gibt einen Endbacklog (nicht abgearbeitete Nachfrage)
2. Es gibt einen Anfangsbacklog (nicht abgearbeitete Nachfrage vom Vorjahr)

**Aber:** Wenn die Summe der "Tatsächlichen PM" höher ist, bedeutet das, dass **mehr produziert wurde als nachgefragt wurde**. Das sollte nur passieren, wenn:
- Der Endbacklog > 0 ist (dann wurde nicht genug produziert, um alle Nachfrage zu decken)
- Oder es gibt einen Fehler in der Logik

**Warte - das ist widersprüchlich!**

Wenn `Summe(Tatsächliche PM) > Summe(Geplante PM)`, dann wurde **mehr produziert als nachgefragt**. Das bedeutet, dass der Endbacklog **negativ** sein sollte (was nicht möglich ist, da Backlog >= 0).

**Oder:** Die Logik ist falsch. Lass mich prüfen...

---

## Korrekte Beziehung

**Eigentlich sollte gelten:**
```
Summe(Tatsächliche PM) = Summe(Geplante PM) - Endbacklog + Anfangsbacklog
```

**Wenn Endbacklog = 0:**
```
Summe(Tatsächliche PM) = Summe(Geplante PM) + Anfangsbacklog
```

**Wenn Anfangsbacklog = 0 und Endbacklog > 0:**
```
Summe(Tatsächliche PM) = Summe(Geplante PM) - Endbacklog
```

**Das bedeutet:**
- Wenn `Summe(Tatsächliche PM) > Summe(Geplante PM)`, dann gibt es einen **Anfangsbacklog** (vom Vorjahr)
- Wenn `Summe(Tatsächliche PM) < Summe(Geplante PM)`, dann gibt es einen **Endbacklog** (nicht abgearbeitete Nachfrage)

---

## Die korrekte Erklärung

### Warum ist "Tatsächliche PM" höher als "Geplante PM"?

**Die Antwort:** Die "Tatsächliche PM" basiert auf dem **Produktionsbedarf**, nicht nur auf der Nachfrage.

**Produktionsbedarf = Nachfrage + Backlog vom Vortag**

**Beispiel aus deiner CSV:**
- **04.01.2027:** Geplante PM = 222, Backlog = 0 → Produktionsbedarf = 222 + 0 = 222, aber Tatsächliche PM = 0 (kein Material)
- **05.01.2027:** Geplante PM = 222, Backlog = 222 → Produktionsbedarf = 222 + 222 = 444, aber Tatsächliche PM = 0 (kein Material)
- **11.01.2027:** Geplante PM = 222, Backlog = 1110 → Produktionsbedarf = 222 + 1110 = 1332, Tatsächliche PM = 854 (Material verfügbar, aber nicht genug Kapazität)

**Das Problem:**
- Wenn Material fehlt, kann nicht produziert werden → Backlog wächst
- Wenn Material wieder verfügbar ist, wird versucht, den Backlog abzuarbeiten
- Die "Tatsächliche PM" ist dann höher als die "Geplante PM" (weil Backlog mit einbezogen wird)

### Mathematische Beziehung

**Über das Jahr hinweg:**
```
Summe(Tatsächliche PM) = Summe(Geplante PM) + Summe(Backlog-Aufarbeitung)
```

**Aber:** Die Summe der "Tatsächlichen PM" sollte eigentlich **nicht** höher sein als die Summe der "Geplanten PM", es sei denn:
1. Es gibt einen **Anfangsbacklog** (vom Vorjahr) → dann wird mehr produziert
2. Es gibt einen **Endbacklog** (nicht abgearbeitete Nachfrage) → dann wird weniger produziert

**In deinem Fall:**
- Anfangsbacklog (01.01.2027) = 0
- Endbacklog (31.12.2027) = 435
- Summe(Tatsächliche PM) = 132678
- Summe(Geplante PM) = 111000
- Differenz = 21678

**Das bedeutet:**
- Es wurde **21678 mehr produziert als nachgefragt wurde**
- Das ist **nicht korrekt**, es sei denn, es gibt einen Anfangsbacklog (den es nicht gibt)

### Das eigentliche Problem

**Die "Tatsächliche PM" sollte NICHT höher sein als die "Geplante PM" in der Summe, weil:**
- Die "Tatsächliche PM" basiert auf `Produktionsbedarf = Nachfrage + Backlog`
- Wenn der Backlog am Ende = 0 ist, sollte `Summe(Tatsächliche PM) = Summe(Geplante PM)` sein
- Wenn der Backlog am Ende > 0 ist, sollte `Summe(Tatsächliche PM) < Summe(Geplante PM)` sein

**Aber:** In deinem Fall ist `Summe(Tatsächliche PM) > Summe(Geplante PM)`, obwohl der Endbacklog > 0 ist. Das ist **widersprüchlich**.

### Mögliche Ursachen

1. **Fehler in der Backlog-Berechnung:** Der Backlog wird nicht korrekt reduziert, wenn produziert wird
2. **Fehler in der Produktionslogik:** Es wird mehr produziert als der Produktionsbedarf
3. **Fehler in der Summenberechnung:** Die Summen werden falsch berechnet

**Prüfe:**
- Wird der Backlog korrekt reduziert, wenn "Fertiggestellte PM" > 0 ist?
- Wird die "Tatsächliche PM" korrekt auf Basis des Produktionsbedarfs berechnet?
- Gibt es Tage, an denen mehr produziert wird als der Produktionsbedarf?
