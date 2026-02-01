# SCOR-Metriken - Datenverfügbarkeit und Realisierbarkeit

**Datum:** 2026-01-31

## Verfügbare Datenquellen

### 1. Inbound-Tabelle (`get_inbound_log_dataframe()`)

**Verfügbare Spalten:**
- `Wochentag`, `Datum`
- `Verspätung` (ja/nein)
- `Ladungsverlust` (Menge)
- `Abfahrt LKW 🇨🇳` (Datum)
- `Ankunft LKW 🇨🇳` (Datum)
- `Abfahrt Schiff 🇨🇳` (Datum)
- `Ankunft Schiff 🇩🇪` (Datum)
- `Abfahrt LKW 🇩🇪` (Datum)
- `Geplante Ankunft LKW 🇩🇪` (Datum)
- `Tatsächliche Ankunft LKW 🇩🇪` (Datum)
- `Menge Gesamt`
- Sattel-Typen (Spalten mit Mengen pro Sattel)

**Was kann gemessen werden:**
- ✅ Materiallieferzeiten (Source Cycle Time)
- ✅ Verspätungen bei Materiallieferungen
- ✅ Ladungsverluste
- ✅ Perfect Order Fulfillment (Inbound)
- ❌ **KEINE** Bestelldaten (nur Abfahrt LKW China)
- ❌ **KEINE** Zahlungsdaten

---

### 2. Production Logs (`production_logs_cache`)

**Verfügbare Spalten:**
- `Wochentag`, `Datum`
- `Schichtanzahl`
- `Auslastung (%)`
- Sattel-Name (spezifisch pro Produkt)
- `geplante PM` (geplante Produktionsmenge)
- `tatsächliche PM` (tatsächliche Produktionsmenge)
- `fertiggestellte PM` (fertiggestellte Produktionsmenge, 1 Tag Verzögerung)
- `Backlog`
- `Is_Weekend`, `Is_Holiday`

**Was kann gemessen werden:**
- ✅ Produktionsmengen (geplant vs. tatsächlich)
- ✅ Produktionsauslastung
- ✅ Backlog
- ✅ Produktionstage (Datum)
- ❌ **KEINE** Produktionsstart-/Endzeiten (nur Datum)
- ❌ **KEINE** Produktionsqualität
- ❌ **KEINE** Rüstzeiten

---

### 3. Fertigproduktelager (`create_finished_goods_log()`)

**Verfügbare Spalten:**
- `Wochentag`, `Datum`
- `Lagerzugang` (Menge)
- `Bestand (morgens)` (Menge)
- `Lagerabgang` (Menge)
- `Bestand (abends)` (Menge)
- `Is_Weekend`, `Is_Holiday`

**Was kann gemessen werden:**
- ✅ Lagerbestände (täglich)
- ✅ Lagerzugänge (Produktion)
- ✅ Lagerabgänge (Auslieferung an Märkte)
- ❌ **KEINE** Auslieferungsdaten an Kunden (nur Verteilung auf Märkte)
- ❌ **KEINE** tatsächlichen Kundenbestelldaten
- ❌ **KEINE** Auslieferungstermine

---

### 4. Materiallager (`calculate_material_inventory()`)

**Verfügbare Spalten:**
- `Wochentag`, `Datum`
- `Lagerzugang` (Menge)
- `Bestand morgens` (Menge)
- `Lagerabgang` (Menge)
- `Verlustmenge` (Menge, z.B. Wasserschaden)
- `Bestand abends` (Menge)
- `Is_Weekend`, `Is_Holiday`

**Was kann gemessen werden:**
- ✅ Materialbestände (täglich)
- ✅ Materialzugänge (aus Inbound)
- ✅ Materialabgänge (an Produktion)
- ✅ Verluste (z.B. Wasserschaden)
- ❌ **KEINE** Materialqualität
- ❌ **KEINE** Lagerkosten

---

## Überarbeitete SCOR-Metriken-Vorschläge

### ✅ REALISIERBAR (Daten verfügbar)

#### 1. Make Cycle Time (MCT) - Teilweise realisierbar
**Beschreibung:** Zeit von Produktionsstart bis Produktionsende

**Verfügbare Daten:**
- ✅ Produktionstage (Datum) aus Production Logs
- ✅ `fertiggestellte PM` (1 Tag Verzögerung)

**Berechnung:**
- Produktionsstart: Erster Tag mit `fertiggestellte PM` > 0 für ein Produkt
- Produktionsende: Letzter Tag mit `fertiggestellte PM` > 0 für ein Produkt
- MCT = Produktionsende - Produktionsstart (in Tagen)

**⚠️ Einschränkung:**
- Nur auf Tagesbasis, nicht auf Stundenbasis
- Berücksichtigt nicht die tatsächliche Produktionsdauer innerhalb eines Tages

**Integrationsaufwand:** 🟢 NIEDRIG (~2-3 Stunden)

---

#### 2. Inventory Days of Supply (IDS) - Vollständig realisierbar
**Beschreibung:** Durchschnittliche Anzahl von Tagen, die Material im Lager liegt

**Verfügbare Daten:**
- ✅ Materialbestände (täglich) aus Materiallager
- ✅ Materialzugänge (täglich) aus Materiallager
- ✅ Materialabgänge (täglich) aus Materiallager

**Berechnung:**
- Durchschnittlicher Bestand = Summe(Bestand morgens) / Anzahl Tage
- Durchschnittlicher täglicher Verbrauch = Summe(Lagerabgang) / Anzahl Tage
- IDS = Durchschnittlicher Bestand / Durchschnittlicher täglicher Verbrauch

**Integrationsaufwand:** 🟢 NIEDRIG (~2-3 Stunden)

---

#### 3. Asset Management Efficiency (AME) - Vollständig realisierbar
**Beschreibung:** Effizienz der Lagerbestandsnutzung

**Verfügbare Daten:**
- ✅ Materiallager-Bestände (täglich)
- ✅ Materiallager-Verbräuche (täglich)
- ✅ Fertigproduktelager-Bestände (täglich)
- ✅ Fertigproduktelager-Abgänge (täglich)

**Berechnung:**
- Lagerumschlagshäufigkeit = Summe(Verbrauch) / Durchschnittlicher Bestand
- Durchschnittlicher Lagerbestand = Summe(Bestand morgens) / Anzahl Tage

**Integrationsaufwand:** 🟢 NIEDRIG (~2-3 Stunden)

---

### ⚠️ TEILWEISE REALISIERBAR (Daten teilweise verfügbar)

#### 4. Delivery Performance to Customer Commit Date - Nicht realisierbar
**Beschreibung:** % der Lieferungen, die pünktlich beim Kunden ankommen

**Verfügbare Daten:**
- ✅ Fertigproduktelager-Abgänge (Verteilung auf Märkte)
- ❌ **FEHLT:** Geplante Auslieferungsdaten an Kunden
- ❌ **FEHLT:** Tatsächliche Auslieferungsdaten an Kunden
- ❌ **FEHLT:** Kundenbestelldaten

**Problem:**
- Die App simuliert keine individuellen Kundenbestellungen
- Auslieferungen werden nur auf Märkte verteilt (prozentual), nicht an konkrete Kunden
- Es gibt keine Commit Dates für Kundenlieferungen

**Integrationsaufwand:** 🔴 HOCH (~12-16 Stunden, benötigt neue Datenstruktur)

---

#### 5. Perfect Order Fulfillment (Outbound) - Nicht realisierbar
**Beschreibung:** % perfekter Auslieferungen an Kunden

**Verfügbare Daten:**
- ✅ Fertigproduktelager-Abgänge (Mengen)
- ❌ **FEHLT:** Kundenbestelldaten
- ❌ **FEHLT:** Auslieferungsqualität (Schäden, Dokumentation)
- ❌ **FEHLT:** Termintreue bei Kundenlieferungen

**Problem:**
- Keine individuellen Kundenbestellungen
- Keine Qualitätsprüfung bei Auslieferung
- Keine Dokumentationsprüfung

**Integrationsaufwand:** 🔴 HOCH (~16-20 Stunden, benötigt neue Datenstruktur)

---

### ❌ NICHT REALISIERBAR (Daten fehlen)

#### 6. Cash-to-Cash Cycle Time (C2C) - Nicht realisierbar
**Beschreibung:** Zeit von Zahlung an Lieferanten bis Zahlungseingang von Kunden

**Verfügbare Daten:**
- ✅ Bestelldatum (Abfahrt LKW China) aus Inbound-Tabelle
- ❌ **FEHLT:** Zahlungsdatum an Lieferanten
- ❌ **FEHLT:** Zahlungsdatum von Kunden
- ❌ **FEHLT:** Zahlungsbedingungen (z.B. Zahlungsziel)

**Problem:**
- Die App simuliert keine Finanzströme
- Keine Zahlungsdaten verfügbar

**Integrationsaufwand:** 🔴 SEHR HOCH (~20+ Stunden, benötigt komplett neue Finanzmodellierung)

---

## Empfohlene Priorisierung (überarbeitet)

### Phase 1 (Schnell umsetzbar, Daten vollständig verfügbar):
1. **Inventory Days of Supply (IDS)** - 🟢 NIEDRIG, hoher Nutzen
2. **Asset Management Efficiency (AME)** - 🟢 NIEDRIG, mittlerer Nutzen
3. **Make Cycle Time (MCT)** - 🟢 NIEDRIG, mittlerer Nutzen (mit Einschränkung)

### Phase 2 (Nicht realisierbar ohne neue Datenstruktur):
4. **Delivery Performance to Customer Commit Date** - 🔴 HOCH, benötigt Kundenbestellungen
5. **Perfect Order Fulfillment (Outbound)** - 🔴 HOCH, benötigt Kundenbestellungen + Qualitätsprüfung

### Phase 3 (Nicht realisierbar ohne Finanzmodellierung):
6. **Cash-to-Cash Cycle Time** - 🔴 SEHR HOCH, benötigt komplett neue Finanzmodellierung

---

## Zusätzliche realisierbare Metriken

### 7. Production Efficiency (PE) - Vollständig realisierbar
**Beschreibung:** Verhältnis von tatsächlicher zu geplanter Produktion

**Verfügbare Daten:**
- ✅ `geplante PM` aus Production Logs
- ✅ `tatsächliche PM` aus Production Logs

**Berechnung:**
- PE = Summe(tatsächliche PM) / Summe(geplante PM) × 100%

**Integrationsaufwand:** 🟢 NIEDRIG (~1-2 Stunden)

---

### 8. Capacity Utilization (CU) - Vollständig realisierbar
**Beschreibung:** Durchschnittliche Auslastung der Produktionskapazität

**Verfügbare Daten:**
- ✅ `Auslastung (%)` aus Production Logs
- ✅ `Schichtanzahl` aus Production Logs

**Berechnung:**
- CU = Durchschnitt(Auslastung %) über alle Arbeitstage

**Integrationsaufwand:** 🟢 NIEDRIG (~1-2 Stunden)

---

### 9. Material Loss Rate (MLR) - Vollständig realisierbar
**Beschreibung:** % des Materialverlusts (z.B. durch Wasserschaden)

**Verfügbare Daten:**
- ✅ `Verlustmenge` aus Materiallager
- ✅ `Lagerzugang` aus Materiallager

**Berechnung:**
- MLR = Summe(Verlustmenge) / Summe(Lagerzugang) × 100%

**Integrationsaufwand:** 🟢 NIEDRIG (~1-2 Stunden)

---

### 10. Backlog Days (BD) - Vollständig realisierbar
**Beschreibung:** Durchschnittliche Anzahl von Tagen, die Aufträge im Backlog liegen

**Verfügbare Daten:**
- ✅ `Backlog` aus Production Logs (täglich)

**Berechnung:**
- Durchschnittlicher Backlog = Summe(Backlog) / Anzahl Tage
- Tägliche Nachfrage = Summe(geplante PM) / Anzahl Arbeitstage
- BD = Durchschnittlicher Backlog / Tägliche Nachfrage

**Integrationsaufwand:** 🟢 NIEDRIG (~2-3 Stunden)

---

## Zusammenfassung

### ✅ Realisierbar (Daten vollständig verfügbar):
1. Inventory Days of Supply (IDS)
2. Asset Management Efficiency (AME)
3. Make Cycle Time (MCT) - mit Einschränkung
4. Production Efficiency (PE)
5. Capacity Utilization (CU)
6. Material Loss Rate (MLR)
7. Backlog Days (BD)

### ❌ Nicht realisierbar (Daten fehlen):
1. Delivery Performance to Customer Commit Date
2. Perfect Order Fulfillment (Outbound)
3. Cash-to-Cash Cycle Time

**Empfehlung:** Fokus auf die realisierbaren Metriken, die mit den vorhandenen Daten berechnet werden können.
