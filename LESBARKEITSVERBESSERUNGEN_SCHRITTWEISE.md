# Lesbarkeitsverbesserungen - Schrittweise Umsetzung

**Datum:** 31.01.2026  
**Status:** Schrittweise Implementierung mit Testmöglichkeiten

---

## 📋 Übersicht

Dieses Dokument beschreibt die schrittweise Umsetzung von Lesbarkeitsverbesserungen mit Testmöglichkeiten nach jedem Schritt.

---

## 🎯 Schritt 1: Fokus-Indikatoren bei Eingabefeldern

**Ziel:** Bessere Sichtbarkeit, welches Feld aktiv ist

**Änderungen:**
- Blaue Border beim Fokus (`#3b82f6`)
- Blauer Box-Shadow (Ring-Effekt)
- Smooth Transitions

**Betroffene Elemente:**
- Text-Inputs
- Number-Inputs
- Date-Inputs
- Select-Boxen
- In Sidebar und Hauptbereich

**Test:**
- Öffne eine Seite mit Eingabefeldern (z.B. Stammdaten)
- Klicke in verschiedene Felder
- Prüfe, ob der blaue Fokus-Ring sichtbar ist

**Nächster Schritt:** Nach Bestätigung → Schritt 2

---

## 🎯 Schritt 2: Hover-Effekte bei Buttons

**Ziel:** Bessere Interaktivität und Feedback

**Änderungen:**
- Leichte Bewegung nach oben beim Hover (`translateY(-1px)`)
- Schatten beim Hover
- Smooth Transitions
- Gilt für alle Button-Typen

**Betroffene Elemente:**
- Standard Buttons
- Primary Buttons
- Sidebar Buttons
- Baseweb Buttons

**Test:**
- Fahre mit der Maus über verschiedene Buttons
- Prüfe, ob der Hover-Effekt sichtbar ist
- Prüfe, ob die Animation smooth ist

**Nächster Schritt:** Nach Bestätigung → Schritt 3

---

## 🎯 Schritt 3: Verbesserte Alert-Boxen

**Ziel:** Bessere Unterscheidung zwischen Info/Warning/Error/Success

**Änderungen:**
- Farbige linke Border je nach Typ
  - Info: Blau (`#3b82f6`)
  - Success: Grün (`#10b981`)
  - Warning: Orange (`#f59e0b`)
  - Error: Rot (`#ef4444`)
- Verbesserte Padding und Border-Radius
- Leichter Hover-Effekt

**Betroffene Elemente:**
- `st.info()`
- `st.success()`
- `st.warning()`
- `st.error()`

**Test:**
- Öffne Seiten mit verschiedenen Alert-Typen
- Prüfe, ob die Farben korrekt sind
- Prüfe, ob die Boxen gut lesbar sind

**Nächster Schritt:** Nach Bestätigung → Schritt 4

---

## 🎯 Schritt 4: Verbesserte Tooltips/Help-Icons

**Ziel:** Bessere Sichtbarkeit von Hilfe-Informationen

**Änderungen:**
- Help-Icons ändern Farbe beim Hover (grau → blau)
- `help`-Cursor für bessere Erkennbarkeit
- Smooth Transition

**Betroffene Elemente:**
- Alle Elemente mit `help`-Parameter
- Tooltip-Icons

**Test:**
- Fahre mit der Maus über Help-Icons
- Prüfe, ob die Farbe sich ändert
- Prüfe, ob der Cursor korrekt ist

**Nächster Schritt:** Nach Bestätigung → Schritt 5

---

## 🎯 Schritt 5: Verbesserte Tabellen-Lesbarkeit

**Ziel:** Bessere Lesbarkeit von Tabellen

**Änderungen:**
- Größeres Padding in Zellen (0.75rem × 1rem)
- Größeres Padding in Headern (0.875rem × 1rem)
- Fettere Header (font-weight: 600)
- Verbesserte Zeilenhöhe (1.5)

**Betroffene Elemente:**
- Alle DataFrames/Tabellen
- Tabellen-Header
- Tabellen-Zellen

**Test:**
- Öffne Seiten mit Tabellen (z.B. Reporting, Inbound)
- Prüfe, ob die Tabellen besser lesbar sind
- Prüfe, ob das Padding angemessen ist

**Nächster Schritt:** Nach Bestätigung → Schritt 6

---

## 🎯 Schritt 6: Verbesserte Metriken-Darstellung

**Ziel:** Größere und klarere Metriken

**Änderungen:**
- Größere Werte (2rem)
- Fettere Werte (font-weight: 600)
- Verbesserte Label-Größe (0.95rem)
- Leichter Hover-Effekt

**Betroffene Elemente:**
- Alle `st.metric()` Aufrufe
- KPI-Kacheln

**Test:**
- Öffne Seiten mit Metriken (z.B. Reporting, App)
- Prüfe, ob die Metriken besser lesbar sind
- Prüfe, ob die Größen angemessen sind

**Nächster Schritt:** Nach Bestätigung → Schritt 7

---

## 🎯 Schritt 7: Verbesserte Typografie

**Ziel:** Bessere Lesbarkeit von Überschriften und Text

**Änderungen:**
- Größere Überschriften (H1: 2.25rem, H2: 1.75rem, H3: 1.5rem)
- Verbesserte Zeilenhöhe (1.4-1.6)
- Mehr Abstand zwischen Absätzen
- Fettere Überschriften (font-weight: 600)

**Betroffene Elemente:**
- Alle Überschriften (h1, h2, h3)
- Absätze (p)
- Labels

**Test:**
- Öffne verschiedene Seiten
- Prüfe, ob die Überschriften besser lesbar sind
- Prüfe, ob der Text besser strukturiert ist

**Nächster Schritt:** Nach Bestätigung → Schritt 8

---

## 🎯 Schritt 8: Verbesserte Sidebar-Labels

**Ziel:** Klarere Labels in der Sidebar

**Änderungen:**
- Fettere Labels (font-weight: 500)
- Größere Schriftgröße (0.95rem)
- Mehr Abstand unter Labels (0.5rem)

**Betroffene Elemente:**
- Sidebar Input-Labels
- Sidebar Select-Labels
- Sidebar MultiSelect-Labels

**Test:**
- Öffne die Sidebar auf verschiedenen Seiten
- Prüfe, ob die Labels besser lesbar sind
- Prüfe, ob der Abstand angemessen ist

**Nächster Schritt:** Nach Bestätigung → Schritt 9

---

## 🎯 Schritt 9: Verbesserte Links

**Ziel:** Bessere Erkennbarkeit von Links

**Änderungen:**
- Blaue Farbe (`#3b82f6`)
- Unterstreichung beim Hover
- Smooth Transition

**Betroffene Elemente:**
- Alle Links (`<a>` Tags)
- Markdown-Links

**Test:**
- Prüfe, ob Links gut erkennbar sind
- Fahre mit der Maus über Links
- Prüfe, ob der Hover-Effekt funktioniert

**Nächster Schritt:** Nach Bestätigung → Schritt 10

---

## 🎯 Schritt 10: Verbesserte Captions

**Ziel:** Bessere Lesbarkeit von Captions

**Änderungen:**
- Graue Farbe (`#6b7280`)
- Größere Schriftgröße (0.875rem)
- Verbesserte Zeilenhöhe (1.5)
- Mehr Abstand oben (0.25rem)

**Betroffene Elemente:**
- Alle `st.caption()` Aufrufe

**Test:**
- Öffne Seiten mit Captions
- Prüfe, ob die Captions besser lesbar sind
- Prüfe, ob die Farben angemessen sind

**Nächster Schritt:** Nach Bestätigung → Fertig

---

## ✅ Abschluss

Nach erfolgreicher Umsetzung aller Schritte sind alle Lesbarkeitsverbesserungen implementiert.

**Zusammenfassung:**
- ✅ Fokus-Indikatoren
- ✅ Hover-Effekte bei Buttons
- ✅ Verbesserte Alert-Boxen
- ✅ Verbesserte Tooltips
- ✅ Verbesserte Tabellen
- ✅ Verbesserte Metriken
- ✅ Verbesserte Typografie
- ✅ Verbesserte Sidebar-Labels
- ✅ Verbesserte Links
- ✅ Verbesserte Captions
