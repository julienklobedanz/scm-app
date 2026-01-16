#!/usr/bin/env python3
"""
Zählt Lines of Code (LOC) ohne Kommentare und leere Zeilen.
Ignoriert Markdown-Dateien.
"""
import os
import re
from pathlib import Path

def count_lines_in_file(file_path):
    """Zählt Code-Zeilen in einer Datei (ohne Kommentare und leere Zeilen)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Fehler beim Lesen von {file_path}: {e}")
        return 0
    
    code_lines = 0
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        
        # Leere Zeilen überspringen
        if not stripped:
            continue
        
        # Multi-line Kommentare (""" oder ''')
        if '"""' in stripped or "'''" in stripped:
            # Einfache Heuristik: wenn ungerade Anzahl, dann wechselt der Status
            if stripped.count('"""') % 2 == 1 or stripped.count("'''") % 2 == 1:
                in_multiline_comment = not in_multiline_comment
            continue
        
        if in_multiline_comment:
            continue
        
        # Einzeilige Kommentare (#)
        if stripped.startswith('#'):
            continue
        
        # Inline-Kommentare entfernen (alles nach #)
        # Aber Vorsicht bei Strings
        if '#' in stripped:
            # Einfache Heuristik: wenn # in Anführungszeichen ist, ignorieren
            # Für genauere Analyse müsste man einen Parser verwenden
            parts = stripped.split('#')
            if len(parts) > 1:
                # Prüfe ob # in String ist (vereinfacht)
                before_hash = parts[0]
                if before_hash.count('"') % 2 == 0 and before_hash.count("'") % 2 == 0:
                    stripped = parts[0].strip()
                    if not stripped:
                        continue
        
        # Wenn nach Kommentar-Entfernung noch etwas da ist, ist es Code
        if stripped:
            code_lines += 1
    
    return code_lines

def count_loc_in_directory(directory, exclude_dirs=None, exclude_files=None):
    """Zählt LOC in einem Verzeichnis rekursiv."""
    if exclude_dirs is None:
        exclude_dirs = {'.git', 'venv', '__pycache__', '.idea', 'node_modules'}
    
    if exclude_files is None:
        exclude_files = {'.md', '.txt', '.iml', '.xml', '.puml'}
    
    total_lines = 0
    file_count = 0
    file_details = []
    
    directory = Path(directory)
    
    for file_path in directory.rglob('*'):
        # Verzeichnisse überspringen
        if file_path.is_dir():
            continue
        
        # Ausgeschlossene Verzeichnisse
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue
        
        # Ausgeschlossene Dateitypen
        if file_path.suffix in exclude_files:
            continue
        
        # Nur Python-Dateien (außer diesem Skript selbst und Test-Dateien)
        if file_path.suffix == '.py' and file_path.name != 'count_loc.py' and not file_path.name.startswith('test_'):
            lines = count_lines_in_file(file_path)
            if lines > 0:
                total_lines += lines
                file_count += 1
                file_details.append((file_path, lines))
    
    return total_lines, file_count, file_details

if __name__ == '__main__':
    project_dir = Path(__file__).parent
    
    total_loc, file_count, file_details = count_loc_in_directory(project_dir)
    
    print(f"\n{'='*60}")
    print(f"Lines of Code (LOC) Analyse")
    print(f"{'='*60}\n")
    print(f"Gesamt LOC (ohne Kommentare, ohne leere Zeilen): {total_loc:,}")
    print(f"Anzahl Python-Dateien: {file_count}\n")
    
    print(f"{'Datei':<50} {'LOC':>10}")
    print(f"{'-'*60}")
    
    # Sortiere nach LOC (absteigend)
    file_details.sort(key=lambda x: x[1], reverse=True)
    
    for file_path, lines in file_details:
        rel_path = file_path.relative_to(project_dir)
        print(f"{str(rel_path):<50} {lines:>10,}")
    
    print(f"{'-'*60}")
    print(f"{'GESAMT':<50} {total_loc:>10,}")
    print(f"{'='*60}\n")

