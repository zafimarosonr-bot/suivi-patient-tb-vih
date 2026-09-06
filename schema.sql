-- ============================================================
-- Schéma : Application de suivi patient — TB & VIH
-- Maison Centrale de Mahajanga
-- ============================================================

CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    prenoms TEXT NOT NULL DEFAULT '',
    date_naissance TEXT,
    age INTEGER,
    sexe TEXT NOT NULL CHECK (sexe IN ('M', 'F')),
    statut TEXT NOT NULL DEFAULT 'incarcere'
        CHECK (statut IN ('incarcere', 'libere', 'transfere', 'decede')),
    quartier TEXT NOT NULL DEFAULT '',
    situation_penale TEXT DEFAULT ''
        CHECK (situation_penale IN ('', 'Condamné', 'Prévenu')),
    telephone TEXT NOT NULL DEFAULT '',
    adresse TEXT NOT NULL DEFAULT '',
    contact_nom TEXT NOT NULL DEFAULT '',
    contact_tel TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    created_by TEXT NOT NULL DEFAULT 'système'
);

-- Index pour la recherche
CREATE INDEX IF NOT EXISTS idx_patients_nom ON patients(nom);
CREATE INDEX IF NOT EXISTS idx_patients_statut ON patients(statut);

-- Historique des changements de statut
CREATE TABLE IF NOT EXISTS historique_statut (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    ancien_statut TEXT NOT NULL,
    nouveau_statut TEXT NOT NULL,
    date TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    motif TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_historique_patient ON historique_statut(patient_id);

-- Suivi Tuberculose (une ligne par patient dans le programme TB)
CREATE TABLE IF NOT EXISTS suivi_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL UNIQUE,
    numero_registre TEXT DEFAULT '',
    lab_id TEXT DEFAULT '',
    date_debut_traitement TEXT,
    forme_clinique TEXT DEFAULT ''
        CHECK (forme_clinique IN ('', 'TPB+', 'TPB-', 'TEP')),
    type_cas TEXT DEFAULT ''
        CHECK (type_cas IN ('', 'Nouveau', 'Echec', 'Rechute', 'Reprise', 'Transfert entrant')),
    poids_m0 REAL,
    poids_m2 REAL,
    poids_m5 REAL,
    poids_m6 REAL,
    ctrl_m2_date TEXT,
    ctrl_m2_fait INTEGER NOT NULL DEFAULT 0,
    ctrl_m2_resultat TEXT DEFAULT '',
    ctrl_m5_date TEXT,
    ctrl_m5_fait INTEGER NOT NULL DEFAULT 0,
    ctrl_m5_resultat TEXT DEFAULT '',
    ctrl_m6_date TEXT,
    ctrl_m6_fait INTEGER NOT NULL DEFAULT 0,
    ctrl_m6_resultat TEXT DEFAULT '',
    decision TEXT DEFAULT ''
        CHECK (decision IN ('', 'Guéri', 'Traitement terminé', 'Echec', 'Perdu de vue', 'Décédé', 'Transféré')),
    date_decision TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Suivi VIH (une ligne par patient dans le programme VIH)
CREATE TABLE IF NOT EXISTS suivi_vih (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL UNIQUE,
    numero_registre TEXT DEFAULT '',
    code TEXT DEFAULT '',
    date_debut_suivi TEXT,
    observation TEXT DEFAULT ''
        CHECK (observation IN ('', 'Nouveau', 'Transfert', 'Libéré', 'Décédé')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Index pour les numéros de registre
CREATE INDEX IF NOT EXISTS idx_tb_registre ON suivi_tb(numero_registre);
CREATE INDEX IF NOT EXISTS idx_vih_registre ON suivi_vih(numero_registre);

-- Journal d'audit
CREATE TABLE IF NOT EXISTS journal_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_ciblee TEXT NOT NULL,
    id_cible TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    ancien_contenu TEXT,
    nouveau_contenu TEXT,
    auteur TEXT NOT NULL DEFAULT 'système',
    date TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_cible ON journal_audit(table_ciblee, id_cible);

-- Utilisateurs (authentification)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nom_complet TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'user'
        CHECK (role IN ('admin', 'user', 'readonly')),
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Paramètres de l'application (clé-valeur)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
