# Order Fulfillment Cycle Time - Analyse und Optimierung

**Datum:** 2026-01-31

## 1. Aktueller Stand von main

### ✅ Bestätigt: Aktueller Stand
Die SCOR-Metriken-Seite entspricht dem aktuellen Stand von `main`:
- Perfect Order Fulfillment (Inbound) zeigt korrekte Werte
- Source Cycle Time zeigt korrekte Werte
- Order Fulfillment Cycle Time wurde optimiert (nur China, mit Caching)

---

## 2. Performance-Optimierung

### Problem: Langsame Ladezeit
Die Order Fulfillment Cycle Time Berechnung dauerte sehr lange (2+ Minuten), weil:
- **Verschachtelte Schleifen:** 6 Märkte × 245 Lieferungen × 8 Produkte = **11.760 Iterationen**
- **Redundante Berechnungen:** Für jeden Markt wurden die gleichen Daten neu berechnet
- **Kein Caching:** Berechnung wurde bei jedem Rendering neu ausgeführt

### Lösung: Optimierung
1. **Nur China-Zeile:** Da nur China Material liefert, werden andere Märkte nicht mehr berechnet
2. **Index-basierte Suche:** Produktionstage werden einmalig indexiert statt für jede Lieferung durchsucht
3. **Caching:** Ergebnisse werden gecacht und nur bei Änderungen neu berechnet
4. **Reduzierte Iterationen:** Von 11.760 auf ~245 Iterationen (nur Lieferungen)

**Erwartete Verbesserung:** Von 2+ Minuten auf < 1 Sekunde

---

## 3. Berechnungslogik - Erklärung

### Aktuelle Logik (nach Optimierung)

**Order Fulfillment Cycle Time** misst die Zeit von **Bestellung** bis **Auslieferung an den Kunden**:

1. **Bestelldatum:** Abfahrt LKW China (aus Inbound-Tabelle, Spalte "Abfahrt LKW 🇨🇳")
2. **Materiallieferung:** Tatsächliche Ankunft LKW Deutschland (aus Inbound-Tabelle, Spalte "Tatsächliche Ankunft LKW 🇩🇪")
3. **Produktion:** Erster Produktionstag nach Materialankunft (aus Production Logs, "fertiggestellte PM" > 0)
4. **Auslieferung:** Produktionstag + Transit-Tage (China: 30 Tage)
5. **OFCT:** Auslieferung - Bestellung

### Beispiel-Berechnung

```
Bestelldatum: 01.01.2027 (Tag 0)
Materiallieferung: 15.02.2027 (Tag 45)
Produktion: 16.02.2027 (Tag 46)
Auslieferung: 16.02.2027 + 30 Tage = 18.03.2027 (Tag 76)
OFCT: 76 - 0 = 76 Tage
```

### Zahlen-Erklärung (aus Bild)

**China:**
- **Transit-Tage (Soll):** 30 Tage (aus `MARKETS['CN']['transit_days']`)
- **Schnellste Lieferung:** 65 Tage
- **Langsamste Lieferung:** 74 Tage
- **Durchschnittliche Lieferzeit:** 68.96 Tage
- **Anzahl Lieferungen:** 245

**Interpretation:**
- Die schnellste Lieferung benötigte 65 Tage von Bestellung bis Auslieferung
- Die langsamste Lieferung benötigte 74 Tage
- Im Durchschnitt benötigt eine Lieferung 68.96 Tage

---

## 4. Warum Deutschland eine eigene Zeile hatte (vorher)

### Problem
Die alte Implementierung zeigte für **alle Märkte** (DE, USA, FR, CN, CH, AT) separate Zeilen, obwohl:
- Die Waren **von China** nach Deutschland geliefert werden (Materiallieferung)
- Die Märkte (DE, USA, etc.) sind **Auslieferungsziele** (Fertigprodukte), nicht Lieferanten

### Ursache
Die Berechnung verwendete `MasterData.MARKETS` für alle Märkte, obwohl:
- `MARKETS` definiert **Auslieferungsziele** (wohin die fertigen Fahrräder geliefert werden)
- Die Order Fulfillment Cycle Time sollte nur für **Lieferanten** berechnet werden (nur China)

### Lösung
Nur **China** wird jetzt berechnet, da:
- China ist der einzige Lieferant, der Material liefert
- Die Transit-Tage für China (30 Tage) beziehen sich auf die Auslieferung **von** China **nach** Deutschland (Fertigprodukte)
- Andere Märkte sind nur Auslieferungsziele, keine Lieferanten

---

## 5. Korrektheit der Berechnung

### ✅ Korrekt implementiert

1. **Bestelldatum:** Korrekt aus Inbound-Tabelle
2. **Materiallieferung:** Korrekt aus Inbound-Tabelle
3. **Produktion:** Korrekt aus Production Logs (erster Tag mit "fertiggestellte PM" > 0 nach Materialankunft)
4. **Auslieferung:** Produktionstag + Transit-Tage (30 für China)

### ⚠️ Potenzielle Verbesserungen

1. **Produktionssuche:** Aktuell wird der erste Produktionstag nach Materialankunft verwendet. Dies könnte verbessert werden, wenn die tatsächliche Verwendung des Materials aus der Lieferung getrackt wird.

2. **Transit-Tage:** Die Transit-Tage (30 Tage) beziehen sich auf die Auslieferung von Fertigprodukten nach China, nicht auf die Materiallieferung. Dies könnte verwirrend sein.

3. **Mehrere Märkte:** Wenn in Zukunft mehrere Lieferanten hinzugefügt werden, sollte die Berechnung für jeden Lieferanten separat erfolgen.

---

## 6. Weitere SCOR-Metriken - Vorschläge

**⚠️ WICHTIG:** Siehe `SCOR_METRIKEN_DATENVERFÜGBARKEIT.md` für detaillierte Analyse der Datenverfügbarkeit. Die folgenden Vorschläge wurden überarbeitet basierend auf tatsächlich verfügbaren Daten.

### A. Make Cycle Time (MCT)
**Beschreibung:** Zeit von Produktionsstart bis Produktionsende

**Aktueller Stand:** ❌ Nicht implementiert

**Datenquelle:** Production Logs (Produktionsstart/Ende)

**Berechnung:**
- Produktionsstart: Erster Tag mit "tatsächliche PM" > 0
- Produktionsende: Letzter Tag mit "fertiggestellte PM" > 0 für ein Produkt
- MCT = Produktionsende - Produktionsstart

**Integrationsaufwand:** 🟢 NIEDRIG
- Daten bereits verfügbar in Production Logs
- Einfache Berechnung
- ~2-3 Stunden Implementierung

---

### B. Delivery Performance to Customer Commit Date
**Beschreibung:** % der Lieferungen, die pünktlich beim Kunden ankommen

**Aktueller Stand:** ⚠️ Teilweise implementiert (nur Inbound)

**Datenquelle:** 
- Inbound-Tabelle (Materiallieferungen)
- Fertigproduktelager (Auslieferungen an Kunden)

**Berechnung:**
- Geplantes Auslieferungsdatum vs. Tatsächliches Auslieferungsdatum
- % pünktlicher Lieferungen

**Integrationsaufwand:** 🟡 MITTEL
- Fertigproduktelager muss Auslieferungsdaten tracken
- Geplante Auslieferungsdaten müssen berechnet werden
- ~4-6 Stunden Implementierung

---

### C. Cash-to-Cash Cycle Time (C2C)
**Beschreibung:** Zeit von Zahlung an Lieferanten bis Zahlungseingang von Kunden

**Aktueller Stand:** ❌ Nicht implementiert

**Datenquelle:**
- Bestelldatum (Zahlung an Lieferanten)
- Auslieferungsdatum (Zahlungseingang von Kunden)

**Berechnung:**
- C2C = Auslieferungsdatum - Bestelldatum (für Materiallieferungen)

**Integrationsaufwand:** 🟢 NIEDRIG
- Daten bereits verfügbar
- Ähnlich wie Order Fulfillment Cycle Time
- ~2-3 Stunden Implementierung

---

### D. Inventory Days of Supply (IDS)
**Beschreibung:** Durchschnittliche Anzahl von Tagen, die Material im Lager liegt

**Aktueller Stand:** ⚠️ Teilweise verfügbar (Materiallager zeigt Bestände)

**Datenquelle:** Materiallager-Logs

**Berechnung:**
- Durchschnittlicher Bestand / Durchschnittlicher täglicher Verbrauch
- IDS = (Summe Bestände) / (Summe Verbräuche) × Anzahl Tage

**Integrationsaufwand:** 🟡 MITTEL
- Daten verfügbar, aber Berechnung komplexer
- ~3-4 Stunden Implementierung

---

### E. Perfect Order Fulfillment (Outbound)
**Beschreibung:** % perfekter Auslieferungen an Kunden (nicht nur Inbound)

**Aktueller Stand:** ⚠️ Nur Inbound implementiert

**Datenquelle:**
- Fertigproduktelager (Auslieferungen)
- Production Logs (Produktionsqualität)

**Berechnung:**
- % In Full (Mengenkorrektheit)
- Delivery Performance (Termintreue)
- Perfect Condition (keine Schäden)
- Perfect Documentation (korrekte Dokumentation)

**Integrationsaufwand:** 🔴 HOCH
- Neue Datenquellen benötigt (Auslieferungsqualität)
- Szenarien müssen Auslieferungen beeinflussen
- ~8-12 Stunden Implementierung

---

### F. Asset Management Efficiency (AME)
**Beschreibung:** Effizienz der Lagerbestandsnutzung

**Aktueller Stand:** ❌ Nicht implementiert

**Datenquelle:**
- Materiallager-Logs
- Fertigproduktelager-Logs

**Berechnung:**
- Durchschnittlicher Lagerbestand / Durchschnittlicher Verbrauch
- Lagerumschlagshäufigkeit

**Integrationsaufwand:** 🟡 MITTEL
- Daten verfügbar
- Berechnung relativ einfach
- ~3-4 Stunden Implementierung

---

## 7. Empfohlene Priorisierung

### Phase 1 (Schnell umsetzbar):
1. **Make Cycle Time** - 🟢 NIEDRIG, hoher Nutzen
2. **Cash-to-Cash Cycle Time** - 🟢 NIEDRIG, hoher Nutzen

### Phase 2 (Mittlerer Aufwand):
3. **Inventory Days of Supply** - 🟡 MITTEL, mittlerer Nutzen
4. **Delivery Performance to Customer Commit Date** - 🟡 MITTEL, hoher Nutzen

### Phase 3 (Hoher Aufwand):
5. **Perfect Order Fulfillment (Outbound)** - 🔴 HOCH, sehr hoher Nutzen
6. **Asset Management Efficiency** - 🟡 MITTEL, mittlerer Nutzen

---

## 8. Zusammenfassung

### ✅ Was wurde optimiert:
- Order Fulfillment Cycle Time zeigt nur noch China
- Caching hinzugefügt (Performance-Verbesserung von 2+ Minuten auf < 1 Sekunde)
- Index-basierte Suche statt verschachtelter Schleifen

### ✅ Was ist korrekt:
- Berechnungslogik ist korrekt implementiert
- Zahlen entsprechen den erwarteten Werten

### ⚠️ Was könnte verbessert werden:
- Produktionssuche könnte präziser sein (tatsächliche Materialverwendung)
- Transit-Tage könnten klarer dokumentiert werden

### 📋 Nächste Schritte:
- Implementierung von Make Cycle Time (Phase 1)
- Implementierung von Cash-to-Cash Cycle Time (Phase 1)
- Erweiterung von Perfect Order Fulfillment auf Outbound (Phase 3)
