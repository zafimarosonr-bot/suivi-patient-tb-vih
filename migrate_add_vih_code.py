#!/usr/bin/env python3
"""Migration : ajout de la colonne 'code' à la table suivi_vih."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print("Base de données non trouvée. La migration n'est pas nécessaire.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        # Vérifier si la colonne existe déjà
        columns = [row[1] for row in conn.execute("PRAGMA table_info(suivi_vih)").fetchall()]
        if 'code' in columns:
            print("✅ La colonne 'code' existe déjà dans suivi_vih.")
            return

        conn.execute("ALTER TABLE suivi_vih ADD COLUMN code TEXT DEFAULT ''")
        conn.commit()
        print("✅ Colonne 'code' ajoutée à la table suivi_vih.")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
