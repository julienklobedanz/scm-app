# Arbeitspakete - Status nach Pages

**Erstellt:** 2026-01-22  
**Basis:** `AENDERUNGEN_ARBEITSPAKETE.md`

---

## 📊 Gesamtübersicht

**Gesamt:** 18 Arbeitspakete  
**Abgeschlossen:** 11  
**Ausstehend:** 7

---

## 📄 Status nach Pages

### 🏠 **app.py** (Haupt-App)

#### ✅ Abgeschlossen
- **AP 1: App - Metriken entfernen**
  - Perfect Order Fulfillment (Outbound) entfernt
  - Delivery Cycle Time entfernt
  - Order Fulfillment Cycle Time entfernt
  - Länder Spanien und Deutschland entfernt (nur China behalten)
  - Produktionsmetriken hinzugefügt

---

### 📊 **pages/1_reporting.py** (Reporting)

#### ⏳ Ausstehend
- **AP 13: Reporting - KPI-Dashboard Produktion**
  - Service Level: Gesamtproduktion / Gesamtnachfrage x 100
  - Gesamtnachfrage: Summe aller Nachfragen im Zeitraum
  - Gesamtproduktion: Summe aller produzierten Einheiten im Zeitraum
  - Darstellung: 3 KPI-Kacheln oben
  - Optional: Farblogik (grün/gelb/rot nach Schwellwerten)
  - Optional: Zeitraumfilter (Jahr/Monat/KW)

- **AP 14: Reporting - KPI-Dashboard Materiallager**
  - Durchschnittlicher Lagerbestand: Durchschnitt über den Zeitraum (getrennt nach Satteltypen + optional Gesamt)
  - Tage mit 0 Bestand: Anzahl Tage, an denen Bestand = 0 (je Materialtyp + optional "irgendein Material = 0")
  - Minimum / Maximum Lagerbestand: zeigt Volatilität und Extremwerte
  - Durchschnittlicher Tagesverbrauch: hilft, Bestände in "Tage Reichweite" zu übersetzen
  - Durchschnittliche Reichweite: Bestand / Durchschnittlicher Tagesverbrauch
  - Darstellung: KPI-Kacheln oben
  - Optional: Zeitreihe "Bestand über Zeit" (Linie)
  - Optional: Engpass-Zusammenfassung pro Materialtyp

---

### 📅 **pages/2_volumenplanung.py** (Volumenplanung)

#### ✅ Abgeschlossen
- **AP 8: Volumenplanung - Visualisierungen entfernen**
  - Visualisierungen entfernt (gehören in Reporting)
  - Tabelle verlängert (Höhe vergrößert auf 800px)

---

### 🏭 **pages/3_lieferant_china.py** (Lieferant China)

#### ✅ Abgeschlossen
- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - Korrekte Farbmarkierung sichergestellt (Feiertage hinzugefügt)
  - Farblegende hinzugefügt

#### ⏳ Ausstehend
- **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️ KRITISCH
  - Problem analysieren: Zu hoher Bestandsaufbau
  - Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
  - Fehler in "Lieferant China" identifizieren
  - Logik korrigieren
  - Tests: Bestände müssen abbaubar sein
  - **⚠️ WICHTIG:** Nach Änderung ausführlich testen!

---

### 🚢 **pages/4_inbound.py** (Inbound)

#### ✅ Abgeschlossen
- **AP 3: Inbound - Landesflaggen**
  - Ländercodes durch Landesflaggen in Spaltenbezeichnung ersetzt
  - 'Abfahrt LKW (Port)' → 'Ankunft LKW 🇨🇳'
  - 'Abfahrt Schiff' → 'Abfahrt Schiff 🇨🇳'
  - 'Ankunft Schiff' → 'Ankunft Schiff 🇩🇪'
  - 'Geplante Ankunft LKW' → 'Geplante Ankunft LKW 🇩🇪'
  - 'Tatsächliche Ankunft LKW' → 'Tatsächliche Ankunft LKW 🇩🇪'
  - 'Verfügbar im Lager' → 'Verfügbar im Lager 🇩🇪'

- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - Korrekte Farbmarkierung sichergestellt (Feiertage hinzugefügt)
  - Farblegende hinzugefügt

---

### 📦 **pages/5_materiallager.py** (Materiallager)

#### ✅ Abgeschlossen
- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - Prüfung: Korrekt (bereits OK)

---

### 🏭 **pages/6_produktion.py** (Produktion)

#### ✅ Abgeschlossen
- **AP 2: Nachkommastellen entfernen/kürzen**
  - Produktion: Auslastung auf 2 Dezimalstellen kürzen
  - Formatierung in `pages/6_produktion.py` implementiert

- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - Prüfung: Korrekt (bereits OK)

- **AP 9: Produktion - Tabelle erweitern**
  - Tabelle erweitert, damit die ersten Tage von 2028 angezeigt werden
  - Zeigt jetzt Daten bis 10.01.2028

---

### 📦 **pages/7_fertigproduktelager.py** (Fertigproduktelager)

#### ✅ Abgeschlossen
- **AP 2: Nachkommastellen entfernen/kürzen**
  - Fertigproduktelager: Nachkommastellen bei Lagerzugang und Lagerabgang entfernt

- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - Prüfung: Korrekt (bereits OK)

---

### 📋 **pages/8_stammdaten.py** (Stammdaten)

#### ✅ Abgeschlossen
- **AP 4: Stammdaten - UI-Anpassungen (Teil 1)**
  - Reiter Stückliste: Titel an Reiterbezeichnung angepasst ("Bill of Materials (BOM)" → "Stückliste")
  - Englische Bezeichnungen auf Deutsch umgestellt
  - Kreisdiagramm entfernt
  - Produktionsanteil-Diagramm entfernt

- **AP 5: Stammdaten - UI-Anpassungen (Teil 2)**
  - Verkaufsanteile pro Produkt: Nur noch prozentual (Dezimalwert entfernt)
  - Saisonaler Produktionsverlauf: Nur noch mit prozentualem Wert (Dezimalwert entfernt)

- **AP 6: Sidebar - Planungsbeginn verschieben**
  - Planungsbeginn entfernt aus Sidebar
  - In globale Konfigurationsparameter verschoben

- **AP 10: Stammdaten - Anpassbarkeit**
  - Reiter Stückliste: Fahrrad-Zusammensetzung anpassbar gemacht (st.data_editor mit Dropdowns)
  - Reiter Planung: Globale Konfiguration anpassbar gemacht (st.number_input)
  - Reiter Planung: Tägliche Arbeitslast anpassbar gemacht (st.number_input pro Wochentag)
  - Reiter Planung: Verkaufsanteile pro Produkt anpassbar gemacht (st.data_editor mit Normalisierung)
  - Reiter Planung: Saisonaler Produktionsverlauf anpassbar gemacht (st.data_editor mit Normalisierung)

- **AP 11: Stammdaten - Reiter überdenken**
  - Reiter "Beschaffung": Länder Deutschland und Spanien entfernt (nur China)
  - Reiter "Beschaffung": "Beschaffung nach Lieferant" entfernt
  - Reiter "Beschaffung": Lieferanten-Parameter und Standorte hierher verschoben
  - Reiter "Auslieferung": "Auslieferung nach Ziel" entfernt
  - Reiter "Feiertage": Länderflaggen hinzugefügt
  - Reiter "Feiertage": Zusammenfassung nach ganz oben verschoben
  - Reiter "Feiertage": Länderauswahl angepasst (nur Deutschland und China)

---

### 🎭 **ui/scenario_sidebar.py** (Szenarien-Sidebar)

#### ✅ Abgeschlossen
- **AP 6: Sidebar - Planungsbeginn verschieben**
  - Planungsbeginn entfernt aus Sidebar
  - Funktionalität (Jahr-Änderung, Cache-Logik) beibehalten

#### ⏳ Ausstehend
- **AP 15: Szenarien - Marketingaktion**
  - Um Produktauswahl ergänzen
  - Erhöhungsfaktor überdenken (lieber prozentual bis 100%? Dadurch feiner einstellbar — derzeit hohe 10%-Schritte)
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)

- **AP 16: Szenarien - Wasserschaden im Lager**
  - Konkretes Lager benennen
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)

- **AP 17: Szenarien - Maschinenausfall beim Lieferanten**
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Betroffene Komponente auswählbar machen
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)

- **AP 18: Szenarien - Lieferprobleme beim Lieferanten**
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Blauer Hinweis "Betroffene Komponente" entfernen
  - Warenverlust-Konfiguration überdenken (Lieber ganz oder gar nicht, teilweise Verluste würden uns zwingen, mit Rundungen korrekt zu verarbeiten)
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)

---

### 🔧 **simulation/** (Simulations-Logik)

#### ✅ Abgeschlossen
- **AP 2: Nachkommastellen entfernen/kürzen**
  - `simulation/production_planner.py`: Auslastung auf 2 Dezimalstellen geändert

- **AP 3: Inbound - Landesflaggen**
  - `simulation/china_transport.py`: Alle Spaltennamen mit Flaggen aktualisiert

- **AP 7: Farbmarkierung Wochenenden/Feiertage**
  - `simulation/china_transport.py`: Is_Weekend und Is_Holiday Flags zu DataFrames hinzugefügt

---

## 📋 Zusammenfassung nach Priorität

### ✅ EINFACH (UI/Formatierung) - 11/11 abgeschlossen
- AP 1: App - Metriken entfernen ✅
- AP 2: Nachkommastellen entfernen/kürzen ✅
- AP 3: Inbound - Landesflaggen ✅
- AP 4: Stammdaten - UI-Anpassungen (Teil 1) ✅
- AP 5: Stammdaten - UI-Anpassungen (Teil 2) ✅
- AP 6: Sidebar - Planungsbeginn verschieben ✅
- AP 7: Farbmarkierung Wochenenden/Feiertage ✅
- AP 8: Volumenplanung - Visualisierungen entfernen ✅
- AP 9: Produktion - Tabelle erweitern ✅
- AP 10: Stammdaten - Anpassbarkeit ✅
- AP 11: Stammdaten - Reiter überdenken ✅

### 🔶 MITTEL (Logik/Formatierung) - 0/0 abgeschlossen
- (Keine mittleren Pakete mehr ausstehend)

### 🔴 SCHWER (Kritische Logik-Änderungen) - 0/7 abgeschlossen
- AP 12: Lieferant China - Warenbestandslogik korrigieren ⚠️ KRITISCH ⏳
- AP 13: Reporting - KPI-Dashboard Produktion ⏳
- AP 14: Reporting - KPI-Dashboard Materiallager ⏳
- AP 15: Szenarien - Marketingaktion ⏳
- AP 16: Szenarien - Wasserschaden im Lager ⏳
- AP 17: Szenarien - Maschinenausfall beim Lieferanten ⏳
- AP 18: Szenarien - Lieferprobleme beim Lieferanten ⏳

---

## 🎯 Nächste Schritte (Priorisiert)

1. **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️ KRITISCH
   - Höchste Priorität, da kritischer Fehler
   - Betrifft: `pages/3_lieferant_china.py`, `simulation/china_transport.py`

2. **AP 13: Reporting - KPI-Dashboard Produktion**
   - Wurde bereits diskutiert und spezifiziert
   - Betrifft: `pages/1_reporting.py`

3. **AP 14: Reporting - KPI-Dashboard Materiallager**
   - Wurde bereits diskutiert und spezifiziert
   - Betrifft: `pages/1_reporting.py`

4. **AP 15-18: Szenarien**
   - Können parallel oder nacheinander bearbeitet werden
   - Betrifft: `ui/scenario_sidebar.py`, `models/scenarios.py`
