# Offene Arbeitspakete nach Pages

**Erstellt:** 2026-01-22  
**Basis:** `ARBEITSPAKETE_STATUS.md`  
**Status:** Nur ausstehende Arbeitspakete

---

## 📊 Gesamtübersicht

**Ausstehend:** 5 Arbeitspakete  
**Abgeschlossen:** 13 Arbeitspakete (inkl. AP 13 und AP 14)

---

## 📄 Offene Arbeitspakete nach Pages

### 📊 **pages/1_reporting.py** (Reporting)

#### ✅ Abgeschlossen
- **AP 13: Reporting - KPI-Dashboard Produktion** ✅
- **AP 14: Reporting - KPI-Dashboard Materiallager** ✅

---

### 🏭 **pages/3_lieferant_china.py** (Lieferant China)

#### ⏳ Ausstehend
- **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️ KRITISCH
  - Problem analysieren: Zu hoher Bestandsaufbau
  - Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
  - Fehler in "Lieferant China" identifizieren
  - Logik korrigieren
  - Tests: Bestände müssen abbaubar sein
  - **⚠️ WICHTIG:** Nach Änderung ausführlich testen!
  - **Dateien:** `pages/3_lieferant_china.py`, `simulation/china_transport.py`

---

### 🎭 **ui/scenario_sidebar.py** + **models/scenarios.py** (Szenarien)

#### ⏳ Ausstehend
- **AP 15: Szenarien - Marketingaktion**
  - Um Produktauswahl ergänzen
  - Erhöhungsfaktor überdenken (lieber prozentual bis 100%? Dadurch feiner einstellbar — derzeit hohe 10%-Schritte)
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)
  - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`

- **AP 16: Szenarien - Wasserschaden im Lager**
  - Konkretes Lager benennen
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)
  - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`

- **AP 17: Szenarien - Maschinenausfall beim Lieferanten**
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Betroffene Komponente auswählbar machen
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)
  - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`

- **AP 18: Szenarien - Lieferprobleme beim Lieferanten**
  - Konkrete Datenfelder identifizieren, die das Szenario betrifft
  - Blauer Hinweis "Betroffene Komponente" entfernen
  - Warenverlust-Konfiguration überdenken (Lieber ganz oder gar nicht, teilweise Verluste würden uns zwingen, mit Rundungen korrekt zu verarbeiten)
  - Implementierung des Szenarios (auf korrekten Datenfluss achten)
  - **Dateien:** `ui/scenario_sidebar.py`, `models/scenarios.py`

---

## 📋 Zusammenfassung nach Priorität

### 🔴 SCHWER (Kritische Logik-Änderungen) - 0/5 abgeschlossen

1. **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️ KRITISCH ⏳
   - **Priorität:** Höchste (kritischer Fehler)
   - **Betrifft:** `pages/3_lieferant_china.py`, `simulation/china_transport.py`
   - **Status:** Ausstehend

2. **AP 15: Szenarien - Marketingaktion** ⏳
   - **Priorität:** Mittel
   - **Betrifft:** `ui/scenario_sidebar.py`, `models/scenarios.py`
   - **Status:** Ausstehend

3. **AP 16: Szenarien - Wasserschaden im Lager** ⏳
   - **Priorität:** Mittel
   - **Betrifft:** `ui/scenario_sidebar.py`, `models/scenarios.py`
   - **Status:** Ausstehend

4. **AP 17: Szenarien - Maschinenausfall beim Lieferanten** ⏳
   - **Priorität:** Mittel
   - **Betrifft:** `ui/scenario_sidebar.py`, `models/scenarios.py`
   - **Status:** Ausstehend

5. **AP 18: Szenarien - Lieferprobleme beim Lieferanten** ⏳
   - **Priorität:** Mittel
   - **Betrifft:** `ui/scenario_sidebar.py`, `models/scenarios.py`
   - **Status:** Ausstehend

---

## 🎯 Nächste Schritte (Priorisiert)

1. **AP 12: Lieferant China - Warenbestandslogik korrigieren** ⚠️ KRITISCH
   - Höchste Priorität, da kritischer Fehler
   - Problem: Zu hoher Bestandsaufbau
   - Problem: Es gehen weniger beim Chinesen raus, als bei uns in Inbound ankommen
   - Nach Änderung ausführlich testen!

2. **AP 15-18: Szenarien**
   - Können parallel oder nacheinander bearbeitet werden
   - Alle betreffen: `ui/scenario_sidebar.py`, `models/scenarios.py`
   - Benötigen: Identifikation der betroffenen Datenfelder und Implementierung

---

## 📝 Hinweise

- **AP 12** ist als kritisch markiert und sollte zuerst bearbeitet werden
- **AP 15-18** sind Szenarien-Implementierungen und können unabhängig voneinander bearbeitet werden
- Alle Szenarien benötigen eine sorgfältige Analyse der betroffenen Datenfelder
- Nach jeder Implementierung sollten ausführliche Tests durchgeführt werden
