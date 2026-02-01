# Plan: Status-Indikatoren für bessere Lesbarkeit

**Datum:** 31.01.2026  
**Status:** Planungsphase

---

## 🎯 Ziel

Implementierung von visuellen Status-Indikatoren, die wichtige Informationen auf einen Blick erkennbar machen und die Lesbarkeit der App verbessern.

---

## 📊 Anwendungsbereiche

### 1. SCOR-Metriken (`app.py`)

**Aktuelle Situation:**
- Perfect Order Fulfillment wird als Prozentwert angezeigt
- Source Cycle Time wird als Durchschnitt angezeigt
- Keine visuelle Hervorhebung von kritischen Werten

**Vorschlag:**
- **Farbcodierung für Perfect Order Fulfillment:**
  - 🟢 Grün: ≥ 99% (Exzellent)
  - 🟡 Gelb: 95-98% (Gut)
  - 🟠 Orange: 80-94% (Akzeptabel)
  - 🔴 Rot: < 80% (Kritisch)

- **Farbcodierung für Source Cycle Time:**
  - 🟢 Grün: ≤ Durchschnitt (Gut)
  - 🟡 Gelb: +10% über Durchschnitt (Akzeptabel)
  - 🔴 Rot: > +20% über Durchschnitt (Kritisch)

**Implementierung:**
```python
# In app.py, bei st.metric():
if perfect_order_fulfillment >= 99:
    delta_color = "normal"  # Grün
    status_icon = "🟢"
elif perfect_order_fulfillment >= 95:
    delta_color = "off"  # Gelb (müsste custom CSS sein)
    status_icon = "🟡"
elif perfect_order_fulfillment >= 80:
    delta_color = "off"  # Orange
    status_icon = "🟠"
else:
    delta_color = "inverse"  # Rot
    status_icon = "🔴"
```

---

### 2. Service Level (`pages/1_reporting.py`)

**Aktuelle Situation:**
- Service Level wird bereits mit Delta-Text angezeigt (⭐ Ausgezeichnet, ✅ Sehr gut, etc.)
- Farbcodierung ist bereits teilweise implementiert

**Vorschlag:**
- **Visuelle Indikatoren ergänzen:**
  - Status-Badge neben dem Wert
  - Farbiger Hintergrund für die Metrik-Kachel
  - Progress-Bar für visuelle Darstellung

**Implementierung:**
```python
# Erweitere bestehende Logik:
service_level_color_map = {
    "excellent": {"bg": "#d1fae5", "border": "#10b981", "icon": "🟢"},
    "very_good": {"bg": "#dbeafe", "border": "#3b82f6", "icon": "🔵"},
    "good": {"bg": "#fef3c7", "border": "#f59e0b", "icon": "🟡"},
    "ok": {"bg": "#fed7aa", "border": "#f97316", "icon": "🟠"},
    "poor": {"bg": "#fee2e2", "border": "#ef4444", "icon": "🔴"}
}
```

---

### 3. Materiallager-Bestände (`pages/5_materiallager.py`)

**Aktuelle Situation:**
- Bestände werden als Zahlen angezeigt
- Keine visuelle Warnung bei niedrigen Beständen

**Vorschlag:**
- **Ampel-System für Bestände:**
  - 🟢 Grün: Bestand > Sicherheitsbestand + 50%
  - 🟡 Gelb: Bestand zwischen Sicherheitsbestand und Sicherheitsbestand + 50%
  - 🔴 Rot: Bestand < Sicherheitsbestand (Nachbestellung erforderlich)

- **Visuelle Darstellung:**
  - Farbiger Punkt/Badge neben dem Bestandswert
  - Hintergrundfarbe der Zeile bei kritischen Beständen
  - Tooltip mit Erklärung

**Implementierung:**
```python
# In der Tabelle:
def get_stock_status_color(current_stock, safety_stock):
    if current_stock < safety_stock:
        return {"bg": "#fee2e2", "icon": "🔴", "text": "Kritisch"}
    elif current_stock < safety_stock * 1.5:
        return {"bg": "#fef3c7", "icon": "🟡", "text": "Niedrig"}
    else:
        return {"bg": "#d1fae5", "icon": "🟢", "text": "OK"}
```

---

### 4. Produktions-Backlog (`pages/6_produktion.py`)

**Aktuelle Situation:**
- Backlog wird als Zahl angezeigt
- Keine visuelle Hervorhebung bei hohem Backlog

**Vorschlag:**
- **Status-Indikatoren für Backlog:**
  - 🟢 Grün: Backlog = 0 (Kein Backlog)
  - 🟡 Gelb: Backlog < 1000 Stück (Gering)
  - 🟠 Orange: Backlog 1000-5000 Stück (Moderat)
  - 🔴 Rot: Backlog > 5000 Stück (Hoch)

- **Visuelle Darstellung:**
  - Farbiger Badge mit Backlog-Wert
  - Progress-Bar für Backlog-Anteil am Gesamtbedarf

---

### 5. Inbound-Verspätungen (`pages/4_inbound.py`)

**Aktuelle Situation:**
- Verspätungen werden in Tabellen angezeigt
- Keine visuelle Hervorhebung

**Vorschlag:**
- **Status-Indikatoren für Verspätungen:**
  - 🟢 Grün: Keine Verspätung (0 Tage)
  - 🟡 Gelb: Verspätung 1-3 Tage (Akzeptabel)
  - 🟠 Orange: Verspätung 4-7 Tage (Moderat)
  - 🔴 Rot: Verspätung > 7 Tage (Kritisch)

- **Visuelle Darstellung:**
  - Farbige Spalte "Status" in der Tabelle
  - Icon + Text-Kombination
  - Tooltip mit Details

---

## 🎨 Design-Richtlinien

### Farbpalette

**Grün (Erfolg/OK):**
- Hintergrund: `#d1fae5`
- Border: `#10b981`
- Text: `#065f46`
- Icon: 🟢

**Blau (Information):**
- Hintergrund: `#dbeafe`
- Border: `#3b82f6`
- Text: `#1e40af`
- Icon: 🔵

**Gelb (Warnung):**
- Hintergrund: `#fef3c7`
- Border: `#f59e0b`
- Text: `#92400e`
- Icon: 🟡

**Orange (Mäßig kritisch):**
- Hintergrund: `#fed7aa`
- Border: `#f97316`
- Text: `#9a3412`
- Icon: 🟠

**Rot (Kritisch):**
- Hintergrund: `#fee2e2`
- Border: `#ef4444`
- Text: `#991b1b`
- Icon: 🔴

---

## 🔧 Implementierungs-Strategie

### Phase 1: Basis-Implementierung
1. CSS-Klassen für Status-Indikatoren erstellen
2. Helper-Funktion für Status-Bestimmung
3. Erste Anwendung bei SCOR-Metriken

### Phase 2: Erweiterte Anwendung
1. Materiallager-Bestände
2. Produktions-Backlog
3. Inbound-Verspätungen

### Phase 3: Verfeinerung
1. Tooltips mit Details
2. Progress-Bars für visuelle Darstellung
3. Animationen bei Status-Änderungen

---

## 📝 Code-Struktur

### Helper-Funktion (`ui/status_indicators.py`)

```python
from typing import Dict, Literal

StatusLevel = Literal["excellent", "good", "warning", "critical"]

def get_status_indicator(
    value: float,
    thresholds: Dict[StatusLevel, float],
    reverse: bool = False
) -> Dict[str, str]:
    """
    Bestimmt Status-Indikator basierend auf Wert und Schwellenwerten.
    
    Args:
        value: Der zu bewertende Wert
        thresholds: Dictionary mit Schwellenwerten
        reverse: Wenn True, sind niedrigere Werte besser
    
    Returns:
        Dictionary mit Status-Informationen (color, icon, label)
    """
    # Implementierung...
```

### CSS-Klassen (`ui/theme_toggle.py`)

```css
.status-indicator-excellent {
    background-color: #d1fae5;
    border-left: 4px solid #10b981;
    color: #065f46;
}

.status-indicator-good {
    background-color: #dbeafe;
    border-left: 4px solid #3b82f6;
    color: #1e40af;
}

.status-indicator-warning {
    background-color: #fef3c7;
    border-left: 4px solid #f59e0b;
    color: #92400e;
}

.status-indicator-critical {
    background-color: #fee2e2;
    border-left: 4px solid #ef4444;
    color: #991b1b;
}
```

---

## ⚠️ Wichtige Überlegungen

1. **Konsistenz:** Gleiche Schwellenwerte sollten überall verwendet werden
2. **Barrierefreiheit:** Farben sollten nicht die einzige Information sein (Icons + Text)
3. **Performance:** Status-Berechnungen sollten gecacht werden
4. **Konfigurierbarkeit:** Schwellenwerte sollten anpassbar sein (z.B. in Stammdaten)

---

## 📋 Checkliste für Implementierung

- [ ] Helper-Funktion `get_status_indicator()` erstellen
- [ ] CSS-Klassen für Status-Indikatoren hinzufügen
- [ ] SCOR-Metriken mit Status-Indikatoren erweitern
- [ ] Materiallager-Bestände mit Status-Indikatoren erweitern
- [ ] Produktions-Backlog mit Status-Indikatoren erweitern
- [ ] Inbound-Verspätungen mit Status-Indikatoren erweitern
- [ ] Tooltips mit Details hinzufügen
- [ ] Tests für Status-Berechnungen schreiben
- [ ] Dokumentation aktualisieren

---

## 🎯 Erwartete Verbesserungen

1. **Schnellere Erkennung:** Kritische Werte sind sofort sichtbar
2. **Bessere Lesbarkeit:** Farbcodierung hilft bei der Orientierung
3. **Professionelleres Aussehen:** Moderne UI-Elemente
4. **Reduzierte Fehler:** Warnungen werden nicht übersehen
