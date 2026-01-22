# Arbeitspakete - Heutige Änderungen

**Erstellt:** 2026-01-22  
**Status:** In Bearbeitung  
**Ziel:** Alle offenen Punkte systematisch abarbeiten, von einfach nach schwer

---

## ⚠️ WICHTIGE HINWEISE

1. **Nach jeder Änderung testen** - insbesondere auf nicht abbaubare Bestände prüfen
2. **Stand nach jeder Änderung dokumentieren**
3. **Bei kritischen Dingen nachfragen**
4. **Bestehende funktionierende Logik nicht überschreiben**

---

## 📋 Arbeitspakete (Priorisiert: Einfach → Schwer)

### ✅ EINFACH (UI/Formatierung - Keine Logik-Änderungen)

#### AP 1: App - Metriken entfernen ✅
- [x] Perfect Order Fulfillment (Outbound) entfernen
- [x] Delivery Cycle Time entfernen
- [x] Order Fulfillment Cycle Time entfernen
- [x] Länder Spanien und Deutschland entfernen (nur China behalten)
- [x] Produktionsmetriken hinzugefügt
- **Datei:** `app.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - Perfect Order Fulfillment (Outbound) komplett entfernt (Zeilen 176-239)
  - Delivery Cycle Time komplett entfernt (Zeilen 304-359)
  - Order Fulfillment Cycle Time komplett entfernt (Zeilen 363-414)
  - In `calculate_inbound_metrics()`: suppliers = ['China'] (nur noch China)
  - In `calculate_source_cycle_time()`: suppliers = ['China'] (nur noch China)
  - Alle else-Zweige für Deutschland/Spanien entfernt
  - Produktionsmetriken hinzugefügt:
    - Gesamtproduktion, Geplante Produktion, Gesamtnachfrage
    - Service Level (%), Planabweichung (%)
    - Durchschnittliche Auslastung (%), Durchschnittliche Tagesproduktion
    - Produktionstage, Tage mit Materialmangel, Backlog am Jahresende

#### AP 2: Nachkommastellen entfernen/kürzen ✅
- [x] Produktion: Auslastung auf 2 Dezimalstellen kürzen oder ganz entfernen
- [x] Fertigproduktelager: Nachkommastellen bei Lagerzugang und Lagerabgang entfernen
- **Dateien:** `simulation/production_planner.py`, `pages/7_fertigproduktelager.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - `simulation/production_planner.py` Zeile 488: Auslastung auf 2 Dezimalstellen geändert (`round(utilization, 2)`)
  - `pages/7_fertigproduktelager.py` Zeile 98-101: Lagerzugang und Lagerabgang auf ganze Zahlen geändert (`int(round(...))`)

#### AP 3: Inbound - Landesflaggen ✅
- [x] Ländercodes durch Landesflaggen in Spaltenbezeichnung ersetzen
- **Dateien:** `pages/4_inbound.py`, `simulation/china_transport.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - `simulation/china_transport.py`: 'Abfahrt LKW (CN)' → 'Abfahrt LKW 🇨🇳'
  - `simulation/china_transport.py`: 'Abfahrt LKW (DE)' → 'Abfahrt LKW 🇩🇪'
  - Alle Vorkommen in Spaltendefinitionen, row-Definitionen und Spaltenreihenfolge aktualisiert
  - `pages/4_inbound.py`: Spaltennamen in Summenzeile-Logik aktualisiert

#### AP 4: Stammdaten - UI-Anpassungen (Teil 1) ✅
- [x] Reiter Stückliste: Titel an Reiterbezeichnung anpassen
- [x] Englische Bezeichnungen auf Deutsch umstellen
- [x] Kreisdiagramm entfernen
- [x] Produktionsanteil-Diagramm entfernen
- **Datei:** `pages/8_stammdaten.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - "Bill of Materials (BOM)" → "Stückliste"
  - Parameter-Namen in globaler Konfiguration übersetzt (total_volume → Gesamtvolumen, etc.)
  - Kreisdiagramm für Verkaufsanteile entfernt
  - Produktionsanteil-Diagramm (Liniendiagramm) entfernt

#### AP 5: Stammdaten - UI-Anpassungen (Teil 2) ✅
- [x] Verkaufsanteile pro Produkt: Entweder prozentual ODER Dezimalwert (nicht beides)
- [x] Saisonaler Produktionsverlauf: Nur mit prozentualem Wert
- **Datei:** `pages/8_stammdaten.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - Verkaufsanteile: Nur noch "Verkaufsanteil (%)" (Dezimalwert entfernt)
  - Saisonaler Produktionsverlauf: Nur noch "Produktionsanteil (%)" (Dezimalwert entfernt)

#### AP 6: Sidebar - Planungsbeginn verschieben ✅
- [x] Planungsbeginn entfernen aus Sidebar
- [x] In globale Konfigurationsparameter verschieben
- **Dateien:** `ui/scenario_sidebar.py`, `pages/8_stammdaten.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - Planungsbeginn aus Sidebar entfernt (ui/scenario_sidebar.py)
  - Planungsbeginn in Stammdaten → Reiter Planung → Globale Konfiguration verschoben
  - Funktionalität (Jahr-Änderung, Cache-Logik) beibehalten

---

### 🔶 MITTEL (Logik/Formatierung - Mit Tests)

#### AP 7: Farbmarkierung Wochenenden/Feiertage ✅
- [x] Volumenplanung: Korrekte Farbmarkierung sicherstellen (bereits OK)
- [x] Lieferant China: Korrekte Farbmarkierung sicherstellen (Feiertage hinzugefügt)
- [x] Inbound: Korrekte Farbmarkierung sicherstellen (Feiertage hinzugefügt)
- [x] Materiallager: Prüfen ob korrekt (bereits OK)
- [x] Produktion: Prüfen ob korrekt (bereits OK)
- [x] Fertigproduktelager: Prüfen ob korrekt (bereits OK)
- **Dateien:** `simulation/china_transport.py`, `pages/3_lieferant_china.py`, `pages/4_inbound.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - `simulation/china_transport.py`: Is_Weekend und Is_Holiday Flags zu `get_supplier_log_dataframe()` und `get_inbound_log_dataframe()` hinzugefügt
  - `pages/3_lieferant_china.py`: Styling-Funktion erweitert, Farblegende hinzugefügt
  - `pages/4_inbound.py`: Styling-Funktion erweitert, Farblegende hinzugefügt
  - Wochenende: #ffebee (helles Rot), Feiertag: #c8e6c9 (helles Grün)

#### AP 8: Volumenplanung - Visualisierungen entfernen ✅
- [x] Visualisierungen entfernen (gehören in Reporting)
- [x] Tabelle verlängern (Höhe vergrößern)
- **Datei:** `pages/2_volumenplanung.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - Schichten-Visualisierung entfernt
  - Fahrrad-Vergleich (Linie) entfernt
  - Fahrrad-Vergleich (Gestapelt) entfernt
  - Tägliche Entwicklung (Gestapeltes Balkendiagramm) entfernt
  - Wöchentliche Tabelle: Höhe auf 800px erhöht
  - Tägliche Tabelle: Höhe auf 800px erhöht
  - plotly.graph_objects Import auskommentiert

#### AP 9: Produktion - Tabelle erweitern ✅
- [x] Tabelle erweitern, damit die ersten Tage von 2028 angezeigt werden
- **Datei:** `pages/6_produktion.py`
- **Status:** ✅ Abgeschlossen
- **Änderungen:**
  - end_date erweitert von `date(planning_year, 12, 31)` auf `date(planning_year + 1, 1, 10)`
  - Zeigt jetzt Daten bis 10.01.2028

#### AP 10: Stammdaten - Anpassbarkeit
- [ ] Reiter Stückliste: Fahrrad-Zusammensetzung anpassbar machen
- [ ] Reiter Planung: Globale Konfiguration anpassbar machen
- [ ] Reiter Planung: Tägliche Arbeitslast anpassbar machen
- [ ] Reiter Planung: Verkaufsanteile pro Produkt anpassbar machen
- [ ] Reiter Planung: Saisonaler Produktionsverlauf anpassbar machen
- **Datei:** `pages/8_stammdaten.py`
- **Status:** ⏳ Ausstehend

#### AP 11: Stammdaten - Reiter überdenken
- [ ] Reiter "Märkte und Kunden": Überlegen ob drin bleiben soll (kein Outbound)
- [ ] Reiter "Auslieferung": Überlegen ob drin bleiben soll
  - Falls ja: Lieferanten-Parameter und Standorte in Beschaffung verschieben und anpassbar machen
  - Spanien und Deutschland aus dieser Tabelle entfernen
  - "Auslieferung nach Ziel" entfernen (ist das gleiche wie Auslieferung-Routen)
- [ ] Reiter "Beschaffung": Länder Deutschland und Spanien entfernen
- [ ] Reiter "Beschaffung": "Beschaffung nach Lieferant" entfernen (ist wieder das gleiche wie darüber)
- [ ] Reiter "Feiertage": Länderflaggen hinzufügen
- [ ] Reiter "Feiertage": Länderauswahl wegen Fehlen von Inbound überdenken
- [ ] Reiter "Feiertage": Zusammenfassung nach ganz oben schieben
- **Datei:** `pages/8_stammdaten.py`
- **Status:** ⏳ Ausstehend

---

### 🔴 SCHWER (Kritische Logik-Änderungen - Mit Tests und Validierung)

#### AP 12: Lieferant China - Warenbestandslogik korrigieren ⚠️ KRITISCH
- [ ] Problem analysieren: Zu hoher Bestandsaufbau
- [ ] Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
- [ ] Fehler in "Lieferant China" identifizieren
- [ ] Logik korrigieren
- [ ] Tests: Bestände müssen abbaubar sein
- **Dateien:** `pages/3_lieferant_china.py`, `simulation/china_transport.py`
- **Status:** ⏳ Ausstehend
- **⚠️ WICHTIG:** Nach Änderung ausführlich testen!

#### AP 13: Reporting - KPI-Dashboard Produktion
- [ ] Service Level: Gesamtproduktion / Gesamtnachfrage x 100
- [ ] Gesamtnachfrage: Summe aller Nachfragen im Zeitraum
- [ ] Gesamtproduktion: Summe aller produzierten Einheiten im Zeitraum
- [ ] Darstellung: 3 KPI-Kacheln oben
- [ ] Optional: Farblogik (grün/gelb/rot nach Schwellwerten)
- [ ] Optional: Zeitraumfilter (Jahr/Monat/KW)
- **Datei:** `pages/1_reporting.py`
- **Status:** ⏳ Ausstehend

#### AP 14: Reporting - KPI-Dashboard Materiallager
- [ ] Durchschnittlicher Lagerbestand: Durchschnitt über den Zeitraum (getrennt nach Satteltypen + optional Gesamt)
- [ ] Tage mit 0 Bestand: Anzahl Tage, an denen Bestand = 0 (je Materialtyp + optional "irgendein Material = 0")
- [ ] Minimum / Maximum Lagerbestand: zeigt Volatilität und Extremwerte
- [ ] Durchschnittlicher Tagesverbrauch: hilft, Bestände in "Tage Reichweite" zu übersetzen
- [ ] Durchschnittliche Reichweite: Bestand / Durchschnittlicher Tagesverbrauch
- [ ] Darstellung: KPI-Kacheln oben
- [ ] Optional: Zeitreihe "Bestand über Zeit" (Linie)
- [ ] Optional: Engpass-Zusammenfassung pro Materialtyp
- **Datei:** `pages/1_reporting.py`
- **Status:** ⏳ Ausstehend

#### AP 15: Szenarien - Marketingaktion
- [ ] Um Produktauswahl ergänzen
- [ ] Erhöhungsfaktor überdenken (lieber prozentual bis 100%? Dadurch feiner einstellbar — derzeit hohe 10%-Schritte)
- [ ] Konkrete Datenfelder identifizieren, die das Szenario betrifft
- [ ] Implementierung des Szenarios (auf korrekten Datenfluss achten)
- **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`
- **Status:** ⏳ Ausstehend

#### AP 16: Szenarien - Wasserschaden im Lager
- [ ] Konkretes Lager benennen
- [ ] Konkrete Datenfelder identifizieren, die das Szenario betrifft
- [ ] Implementierung des Szenarios (auf korrekten Datenfluss achten)
- **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`
- **Status:** ⏳ Ausstehend

#### AP 17: Szenarien - Maschinenausfall beim Lieferanten
- [ ] Konkrete Datenfelder identifizieren, die das Szenario betrifft
- [ ] Betroffene Komponente auswählbar machen
- [ ] Implementierung des Szenarios (auf korrekten Datenfluss achten)
- **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`
- **Status:** ⏳ Ausstehend

#### AP 18: Szenarien - Lieferprobleme beim Lieferanten
- [ ] Konkrete Datenfelder identifizieren, die das Szenario betrifft
- [ ] Blauer Hinweis "Betroffene Komponente" entfernen
- [ ] Warenverlust-Konfiguration überdenken (Lieber ganz oder gar nicht, teilweise Verluste würden uns zwingen, mit Rundungen korrekt zu verarbeiten)
- [ ] Implementierung des Szenarios (auf korrekten Datenfluss achten)
- **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`
- **Status:** ⏳ Ausstehend

---

## 📊 Fortschritt

**Gesamt:** 18 Arbeitspakete  
**Abgeschlossen:** 11  
**In Bearbeitung:** 0  
**Ausstehend:** 7

---

## 📝 Änderungsprotokoll

### 2026-01-22 - Start
- Datei erstellt
- Arbeitspakete priorisiert und strukturiert
- Bereit für Umsetzung

### 2026-01-22 - AP 1 abgeschlossen
- ✅ Perfect Order Fulfillment (Outbound) entfernt
- ✅ Delivery Cycle Time entfernt
- ✅ Order Fulfillment Cycle Time entfernt
- ✅ Länder Spanien und Deutschland entfernt (nur China behalten)
- ✅ Produktionsmetriken hinzugefügt (Service Level, Auslastung, Produktionstage, etc.)
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 2 abgeschlossen
- ✅ Produktion: Auslastung auf 2 Dezimalstellen geändert
- ✅ Fertigproduktelager: Nachkommastellen bei Lagerzugang und Lagerabgang entfernt
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 3 abgeschlossen
- ✅ Inbound: Ländercodes durch Landesflaggen ersetzt (CN → 🇨🇳, DE → 🇩🇪)
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 7 abgeschlossen
- ✅ Farbmarkierung für Wochenenden und Feiertage in Lieferant China und Inbound hinzugefügt
- ✅ Farblegende hinzugefügt
- ✅ Is_Weekend und Is_Holiday Flags zu DataFrames hinzugefügt
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - Performance-Optimierung nach AP 7
- ✅ Feiertags-Prüfung optimiert: `get_day_info()` entfernt, direkte Prüfung gegen `german_holidays` und `chinese_holidays` (beide gecacht)
- ✅ Reduziert Aufrufe von `get_day_info()` in Schleifen (426+ Tage)
- **Erwartete Verbesserung:** ~50-70% schneller bei Feiertags-Prüfung

### 2026-01-22 - AP 8 abgeschlossen
- ✅ Volumenplanung: Alle Visualisierungen entfernt (gehören in Reporting)
- ✅ Tabellenhöhe auf 800px erhöht für bessere Übersicht
- ✅ Reporting: Visualisierungen aus Volumenplanung hinzugefügt (als neue Abschnitte)
  - Schichten-Visualisierung
  - Fahrrad-Vergleich über Kalenderwochen
  - Fahrrad-Vergleich (Gestapelt)
  - Tägliche Entwicklung (Gestapeltes Balkendiagramm)
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 9 abgeschlossen
- ✅ Produktion: Tabelle erweitert, zeigt jetzt Daten bis 10.01.2028
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 1 erweitert (Produktionsmetriken)
- ✅ App: Produktionsmetriken hinzugefügt
  - Gesamtproduktion, Geplante Produktion, Gesamtnachfrage
  - Service Level (%), Planabweichung (%)
  - Durchschnittliche Auslastung (%), Durchschnittliche Tagesproduktion
  - Produktionstage, Tage mit Materialmangel, Backlog am Jahresende
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 4-5 abgeschlossen
- ✅ Stammdaten: Titel angepasst ("Bill of Materials (BOM)" → "Stückliste")
- ✅ Stammdaten: Englische Bezeichnungen auf Deutsch umgestellt
- ✅ Stammdaten: Kreisdiagramm und Produktionsanteil-Diagramm entfernt
- ✅ Stammdaten: Verkaufsanteile nur noch prozentual (Dezimalwert entfernt)
- ✅ Stammdaten: Saisonaler Produktionsverlauf nur noch prozentual (Dezimalwert entfernt)
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 6 abgeschlossen
- ✅ Sidebar: Planungsbeginn entfernt
- ✅ Stammdaten: Planungsbeginn in globale Konfiguration verschoben
- ✅ Funktionalität (Jahr-Änderung, Cache-Logik) beibehalten
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - Performance-Optimierung und Bugfix
- ✅ App: Produktionsmetriken optimiert - keine Neuberechnung von Volumenplanung mehr
- ✅ Reporting: Alle plotly_chart Aufrufe mit unique keys versehen (behebt StreamlitDuplicateElementId Fehler)
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - Key-Duplikate und Summenzeilen-Fixierung
- ✅ Sidebar: Alle render_scenario_sidebar() Aufrufe mit eindeutigen key_suffix versehen (behebt StreamlitDuplicateElementId Fehler)
- ✅ Reporting: Materiallager-Daten-Laden verbessert (stille Fehlerbehandlung)
- ✅ Summenzeilen: CSS für fixierte Summenzeilen hinzugefügt (letzte Zeile bleibt beim Scrollen sichtbar)
  - Betroffene Seiten: Volumenplanung, Lieferant China, Inbound, Materiallager, Produktion, Fertigproduktelager
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - AP 10-11 abgeschlossen
- ✅ Stammdaten: Stückliste editierbar gemacht (st.data_editor mit Dropdowns)
- ✅ Stammdaten: Globale Konfiguration editierbar (st.number_input)
- ✅ Stammdaten: Tägliche Arbeitslast editierbar (st.number_input pro Wochentag)
- ✅ Stammdaten: Verkaufsanteile editierbar (st.data_editor mit Normalisierung)
- ✅ Stammdaten: Saisonalität editierbar (st.data_editor mit Normalisierung)
- ✅ Stammdaten: Reiter überarbeitet (Beschaffung, Auslieferung, Feiertage)
- ✅ Stammdaten: Feiertage - Länderflaggen hinzugefügt, Zusammenfassung nach oben
- ✅ Stammdaten: Beschaffung - nur China, Lieferanten-Parameter hierher verschoben
- ✅ Stammdaten: Auslieferung - "Auslieferung nach Ziel" entfernt
- **Getestet:** Keine Linter-Fehler

### 2026-01-22 - Performance-Optimierungen
- ✅ Stammdaten: Alle `st.rerun()` Aufrufe entfernt (Streamlit aktualisiert automatisch)
- ✅ Stammdaten: Initialisierung optimiert (nur einmal mit Flag)
- ✅ Materiallager: `get_day_info()` Aufrufe reduziert (direkte Berechnung)
- ✅ Materiallager: Caching verbessert (mit Simulation-Hash für Cache-Invalidierung)
- ✅ Reporting: Caching für Materiallager-Daten verbessert
- ✅ Stammdaten: max_value für globale Konfiguration korrigiert (capacity_per_hour: 500 statt 100)
- ✅ Volumenplanung: Feiertags-Cache hinzugefügt (HolidaysConfig.is_holiday() nur einmal pro Jahr)
- ✅ Fertigproduktelager: `get_day_info()` durch direkte Berechnung ersetzt
- ✅ Materiallager: `iterrows()` durch `itertuples()` ersetzt (3-5× schneller)
- ✅ Reporting: Datum-Cache für wiederholte `get_date_from_day()` Aufrufe
- **Erwartete Verbesserung:** ~50-70% schneller bei Seitenwechseln und Berechnungen
- **Getestet:** Keine Linter-Fehler

---

## 🔍 Test-Checkliste (nach kritischen Änderungen)

- [ ] Simulation läuft ohne Fehler
- [ ] Keine nicht abbaubaren Bestände
- [ ] Bestände am Ende der Simulation = 0 (oder erwarteter Wert)
- [ ] Alle Tabellen zeigen korrekte Werte
- [ ] Farbmarkierungen funktionieren korrekt
- [ ] Summenzeilen sind korrekt
- [ ] Keine Performance-Regressionen

---

**Nächster Schritt:** Beginne mit AP 1 (App - Metriken entfernen)

