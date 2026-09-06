#!/usr/bin/env python3
"""Initialise la base de données SQLite avec le schéma et les données de démonstration."""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')


def init_db():
    """Crée les tables et insère les données de démonstration."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Lecture et exécution du schéma
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        cur.executescript(f.read())

    # Insertion des données de démonstration
    seed_path = os.path.join(os.path.dirname(__file__), 'seed_data.sql')
    with open(seed_path, 'r', encoding='utf-8') as f:
        cur.executescript(f.read())

    # Créer un admin par défaut si la table users est vide
    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""
            INSERT INTO users (username, password_hash, nom_complet, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'admin',
            generate_password_hash('admin123'),
            'Administrateur',
            'admin',
            now
        ))

    conn.commit()
    conn.close()
    print(f"✅ Base de données initialisée : {DB_PATH}")
    print(f"   → {count_records('patients')} patients")
    print(f"   → {count_records('suivi_tb')} suivis TB")
    print(f"   → {count_records('suivi_vih')} suivis VIH")
    print(f"   → {count_records('users')} utilisateur(s)")
    print(f"   → Connexion par défaut : admin / admin123")


def count_records(table):
    """Compte le nombre d'enregistrements dans une table."""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return count


if __name__ == '__main__':
    init_db()
