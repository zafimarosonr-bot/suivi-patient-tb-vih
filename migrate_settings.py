#!/usr/bin/env python3
"""Migration : ajout de la table settings avec valeurs par défaut."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')

DEFAULTS = {
    # Organization
    'org_name': 'Maison Centrale de Mahajanga',
    'org_drapp': 'DRAP BOENY',
    'org_destinator': 'DHDPRS/SSPD',
    'org_service': 'Infirmerie — Service de soins',
    # Clinical defaults
    'tb_control_months': 'M2,M5,M6',
    'overdue_days': '7',
    # Report settings
    'report_signature': 'true',
    'report_header_note': '',
    # Data management
    'audit_retention_months': '24',
    'archive_inactive_months': '0',
    'items_per_page': '20',
}

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )''')

    # Insert defaults (only if not already set)
    for key, value in DEFAULTS.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

    conn.commit()
    conn.close()
    print(f"Migration settings OK — {len(DEFAULTS)} paramètres par défaut insérés.")

if __name__ == '__main__':
    migrate()
