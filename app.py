#!/usr/bin/env python3
"""Application de suivi patient — TB & VIH
Maison Centrale de Mahajanga
Flask + SQLite — 100% local
"""

import sqlite3
import json
import os
import csv
import io
import calendar
import glob
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')


# ── Helpers ──────────────────────────────────────────────────────

def get_db():
    """Ouvre une connexion SQLite avec dict-row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def format_date_fr(date_str):
    """Convertit AAAA-MM-JJ en JJ-MM-AAAA."""
    if not date_str:
        return '—'
    try:
        parts = date_str.split('-')
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except (IndexError, AttributeError):
        return date_str


@app.template_filter('date_fr')
def date_fr_filter(date_str):
    return format_date_fr(date_str)


MOIS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
           'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


@app.context_processor
def inject_last_backup():
    """Injecte la date de la dernière sauvegarde (fichier suivi_patients_*.json/csv du dossier projet)."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    files = (glob.glob(os.path.join(project_dir, 'suivi_patients_*.json'))
             + glob.glob(os.path.join(project_dir, 'suivi_patients_*.csv')))
    if files:
        newest = max(files, key=os.path.getmtime)
        mtime = datetime.fromtimestamp(os.path.getmtime(newest))
        return {'derniere_sauvegarde': mtime.strftime('%d/%m/%Y %H:%M')}
    return {'derniere_sauvegarde': None}


def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_str():
    return datetime.now().strftime('%Y-%m-%d')


def add_months(date_str, months):
    """Ajoute des mois calendaires à une date 'AAAA-MM-JJ' (gère les fins de mois)."""
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    total = d.year * 12 + (d.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def tb_control_dates(date_debut_traitement):
    """Calcule les dates prévues des contrôles TB (M2/M5/M6)
    à partir de la date de début de traitement.
    """
    return {
        'ctrl_m2_date': add_months(date_debut_traitement, 2),
        'ctrl_m5_date': add_months(date_debut_traitement, 5),
        'ctrl_m6_date': add_months(date_debut_traitement, 6),
    }


def next_patient_id(db):
    """Génère le prochain identifiant patient."""
    year = datetime.now().year
    row = db.execute(
        "SELECT id FROM patients WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f'PAT-{year}-%',)
    ).fetchone()
    if row:
        num = int(row['id'].split('-')[-1]) + 1
    else:
        num = 1
    return f"PAT-{year}-{num:03d}"


def generate_vih_code(nom, prenoms, date_naissance=None, age=None):
    """Génère le code VIH : DDMMYY + 3 lettres NOM + 2 lettres PRÉNOMS.
    
    Exemples :
    - Florence, pas de prénoms, né le 04/11/2005 → 041105FLOXX
    - Rakoto Jean, né le 12/03/1990 → 120390RAKJA
    - Dupont, pas de prénoms, âge=30 (année=1996) → 010196DUPXX
    """
    # Extraire DDMMYY
    ddmm = '0101'  # défaut si pas de date
    yy = '00'
    if date_naissance:
        try:
            parts = date_naissance.split('-')
            ddmm = parts[2] + parts[1]  # JJ + MM
            yy = parts[0][2:]  # 2 derniers chiffres de l'année
        except (IndexError, ValueError):
            pass
    elif age:
        try:
            year = datetime.now().year - int(age)
            yy = str(year)[2:]
        except (ValueError, TypeError):
            pass

    # 3 premières lettres du NOM (en majuscules, sans accents)
    import unicodedata
    nom_clean = ''.join(
        c for c in unicodedata.normalize('NFD', nom.upper())
        if unicodedata.category(c) != 'Mn'
    ) if nom else 'XXX'
    nom_part = (nom_clean[:3]).ljust(3, 'X')

    # 2 premières lettres du PRÉNOMS (en majuscules, sans accents)
    prenoms_clean = ''.join(
        c for c in unicodedata.normalize('NFD', prenoms.upper())
        if unicodedata.category(c) != 'Mn'
    ) if prenoms else 'XX'
    prenoms_part = (prenoms_clean[:2]).ljust(2, 'X')

    return f"{ddmm}{yy}{nom_part}{prenoms_part}"


def next_registre(db, prefix):
    """Génère le prochain numéro de registre (TB-2026-001 ou VIH-2026-001).
    Compteur indépendant par préfixe, remis à zéro chaque année civile.
    """
    year = datetime.now().year
    # Chercher le dernier numéro pour ce préfixe ET cette année
    row = db.execute(
        "SELECT numero_registre FROM suivi_tb WHERE numero_registre LIKE ? "
        "UNION ALL "
        "SELECT numero_registre FROM suivi_vih WHERE numero_registre LIKE ? "
        "ORDER BY numero_registre DESC LIMIT 1",
        (f'{prefix}-{year}-%', f'{prefix}-{year}-%')
    ).fetchone()
    if row:
        num = int(row['numero_registre'].split('-')[-1]) + 1
    else:
        num = 1
    return f"{prefix}-{year}-{num:03d}"


def compute_overdue_tb(db):
    """Retourne les suivis TB en cours (pour retards/échéances), avec le flag VIH (confidentialité)."""
    today = today_str()
    return db.execute("""
        SELECT p.id, p.nom, p.prenoms, t.numero_registre AS tb_registre,
               t.ctrl_m2_date, t.ctrl_m2_fait,
               t.ctrl_m5_date, t.ctrl_m5_fait, t.ctrl_m6_date, t.ctrl_m6_fait,
               EXISTS(SELECT 1 FROM suivi_vih v
                      WHERE v.patient_id = p.id
                        AND (v.observation != 'Décédé' OR v.observation = '')) AS has_vih
        FROM patients p
        JOIN suivi_tb t ON t.patient_id = p.id
        WHERE t.decision = ''
    """).fetchall()


def compute_overdue_controls(db):
    """Calcule les contrôles TB en retard."""
    today = today_str()
    rows = compute_overdue_tb(db)
    overdue = []
    checks = [
        ('ctrl_m2', 'M2'),
        ('ctrl_m5', 'M5'),
        ('ctrl_m6', 'M6'),
    ]
    for r in rows:
        for key, label in checks:
            date_val = r[f'{key}_date']
            fait = r[f'{key}_fait']
            if date_val and not fait and date_val < today:
                overdue.append({
                    'patient_id': r['id'],
                    'nom': r['nom'],
                    'prenoms': r['prenoms'],
                    'controle': label,
                    'date_prevue': date_val,
                    'has_vih': r['has_vih'],
                })
    return overdue


def compute_upcoming_controls(db):
    """Calcule les contrôles TB à venir (7 prochains jours)."""
    today = today_str()
    in7 = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    rows = compute_overdue_tb(db)
    upcoming = []
    checks = [
        ('ctrl_m2', 'M2'),
        ('ctrl_m5', 'M5'),
        ('ctrl_m6', 'M6'),
    ]
    for r in rows:
        for key, label in checks:
            date_val = r[f'{key}_date']
            fait = r[f'{key}_fait']
            if date_val and not fait and today <= date_val <= in7:
                upcoming.append({
                    'patient_id': r['id'],
                    'nom': r['nom'],
                    'prenoms': r['prenoms'],
                    'controle': label,
                    'date_prevue': date_val,
                    'has_vih': r['has_vih'],
                })
    upcoming.sort(key=lambda x: x['date_prevue'])
    return upcoming


def get_patient_programs(db, patient_id):
    """Retourne les programmes actifs d'un patient."""
    programs = []
    if db.execute("SELECT 1 FROM suivi_tb WHERE patient_id = ? AND (decision = '' OR decision IS NULL)", (patient_id,)).fetchone():
        programs.append('TB')
    if db.execute("SELECT 1 FROM suivi_vih WHERE patient_id = ? AND (observation != 'Décédé' OR observation = '')", (patient_id,)).fetchone():
        programs.append('VIH')
    return programs


def login_required(f):
    """Décorateur : vérifie que l'utilisateur est connecté."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Décorateur : vérifie que l'utilisateur a le bon rôle."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                return jsonify({'success': False, 'error': 'Accès refusé — droits insuffisants'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def current_user():
    """Retourne le nom complet de l'utilisateur connecté."""
    return session.get('nom_complet', session.get('username', 'utilisateur'))


def get_setting(key, default=''):
    """Lit un paramètre depuis la table settings."""
    db = get_db()
    try:
        row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else default
    finally:
        db.close()


def set_setting(key, value):
    """Écrit un paramètre dans la table settings."""
    db = get_db()
    try:
        db.execute('INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime("now","localtime"))', (key, value))
        db.commit()
    finally:
        db.close()


def get_all_settings():
    """Retourne tous les paramètres en dict."""
    db = get_db()
    try:
        rows = db.execute('SELECT key, value FROM settings').fetchall()
        return {r['key']: r['value'] for r in rows}
    finally:
        db.close()


# ── Authentification ─────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Veuillez remplir tous les champs.'
        else:
            db = get_db()
            try:
                user = db.execute(
                    'SELECT * FROM users WHERE username = ? AND actif = 1',
                    (username,)
                ).fetchone()

                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['nom_complet'] = user['nom_complet']
                    session['role'] = user['role']
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Identifiant ou mot de passe incorrect.'
            finally:
                db.close()

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Déconnexion."""
    session.clear()
    return redirect(url_for('login'))


# ── Routes ───────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    """Page d'accueil — tableau de bord."""
    db = get_db()
    try:
        # Statistiques
        stats = {}
        stats['actifs'] = db.execute(
            "SELECT COUNT(*) FROM patients WHERE statut = 'incarcere'"
        ).fetchone()[0]
        stats['tb'] = db.execute(
            "SELECT COUNT(*) FROM suivi_tb WHERE decision = '' OR decision IS NULL"
        ).fetchone()[0]
        stats['vih'] = db.execute(
            "SELECT COUNT(*) FROM suivi_vih WHERE observation != 'Décédé' OR observation = ''"
        ).fetchone()[0]
        stats['overdue'] = len(compute_overdue_controls(db))

        # Alertes
        overdue = compute_overdue_controls(db)
        upcoming = compute_upcoming_controls(db)

        # Lien vers le rapport du mois courant
        now = datetime.now()
        rapport_mois = MOIS_FR[now.month - 1]
        rapport_url = url_for('rapports', mois=now.month, annee=now.year)

        return render_template('dashboard.html',
                               stats=stats,
                               overdue=overdue,
                               upcoming=upcoming,
                               rapport_mois=rapport_mois,
                               rapport_url=rapport_url)
    finally:
        db.close()


@app.route('/api/search')
@login_required
def api_search():
    """API de recherche pour autocomplétion — retourne les suggestions."""
    db = get_db()
    try:
        q = request.args.get('q', '').strip()
        if len(q) < 1:
            return jsonify([])

        rows = db.execute("""
            SELECT p.id, p.nom, p.prenoms, p.sexe, p.statut,
                   t.numero_registre AS tb_registre, t.lab_id,
                   v.numero_registre AS vih_registre, v.code AS vih_code
            FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            WHERE p.nom LIKE ? OR p.prenoms LIKE ?
               OR t.numero_registre LIKE ? OR t.lab_id LIKE ?
               OR v.numero_registre LIKE ? OR v.code LIKE ?
               OR p.id LIKE ?
            ORDER BY p.nom, p.prenoms
            LIMIT 8
        """, (f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()

        suggestions = []
        for r in rows:
            # Construire le texte d'affichage
            display_parts = []
            if r['tb_registre']:
                display_parts.append(r['tb_registre'])
            if r['vih_registre']:
                display_parts.append(r['vih_registre'])
            if r['vih_code']:
                display_parts.append(r['vih_code'])
            registres = ' · '.join(display_parts) if display_parts else r['id']

            suggestions.append({
                'id': r['id'],
                'nom': r['nom'],
                'prenoms': r['prenoms'],
                'sexe': r['sexe'],
                'statut': r['statut'],
                'registres': registres,
                'vih_code': r['vih_code'] or '',
            })

        return jsonify(suggestions)
    finally:
        db.close()


@app.route('/api/verify-password', methods=['POST'])
@login_required
def api_verify_password():
    """Vérifie le mot de passe de l'utilisateur connecté (pour confidentialité VIH)."""
    # Readonly users cannot reveal VIH names
    if session.get('role') == 'readonly':
        return jsonify({'valid': False, 'error': 'Accès refusé'}), 403

    data = request.get_json()
    password = data.get('password', '') if data else ''
    if not password:
        return jsonify({'valid': False}), 400

    db = get_db()
    try:
        user = db.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            return jsonify({'valid': True})
        return jsonify({'valid': False})
    finally:
        db.close()


@app.route('/patients')
@login_required
def patients_list():
    """Liste des patients avec recherche et filtres."""
    db = get_db()
    try:
        q = request.args.get('q', '').strip()
        statut = request.args.get('statut', '')
        programme = request.args.get('programme', '')
        age_range = request.args.get('age', '')
        sexe = request.args.get('sexe', '')
        quartier = request.args.get('quartier', '')
        decision_tb = request.args.get('decision_tb', '')
        overdue_only = request.args.get('overdue', '') == '1'
        sort_by = request.args.get('sort', '')
        sort_dir = request.args.get('dir', 'asc')

        # Dynamic quartier list for filter dropdown
        quartiers = [r[0] for r in db.execute(
            "SELECT DISTINCT quartier FROM patients WHERE quartier IS NOT NULL AND quartier != '' ORDER BY quartier"
        ).fetchall()]


        query = """
            SELECT DISTINCT p.*, t.lab_id, t.numero_registre AS tb_registre,
                v.numero_registre AS vih_registre, v.code AS vih_code,
                (SELECT GROUP_CONCAT(
                    CASE
                        WHEN t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL) THEN 'TB'
                        WHEN v.patient_id IS NOT NULL AND (v.observation != 'Décédé' OR v.observation = '') THEN 'VIH'
                    END
                )
                FROM patients p2
                LEFT JOIN suivi_tb t ON t.patient_id = p2.id
                LEFT JOIN suivi_vih v ON v.patient_id = p2.id
                WHERE p2.id = p.id
            ) AS programmes
            FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            WHERE 1=1
        """
        params = []

        if q:
            query += " AND (p.nom LIKE ? OR p.prenoms LIKE ? OR p.id LIKE ? OR t.lab_id LIKE ? OR t.numero_registre LIKE ? OR v.numero_registre LIKE ? OR v.code LIKE ?)"
            params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])

        if statut:
            query += " AND p.statut = ?"
            params.append(statut)

        if programme == 'TB':
            query += " AND t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL)"
        elif programme == 'VIH':
            query += " AND v.patient_id IS NOT NULL AND (v.observation != 'Décédé' OR v.observation = '')"
        elif programme == 'both':
            query += " AND t.patient_id IS NOT NULL AND v.patient_id IS NOT NULL"

        # Sexe filter
        if sexe:
            query += " AND p.sexe = ?"
            params.append(sexe)

        # Quartier filter
        if quartier:
            query += " AND p.quartier = ?"
            params.append(quartier)

        # Age range filter
        if age_range:
            age_expr = """(CASE
                WHEN p.date_naissance IS NOT NULL AND p.date_naissance != ''
                THEN CAST((julianday('now') - julianday(p.date_naissance)) / 365.25 AS INTEGER)
                WHEN p.age IS NOT NULL THEN p.age
                ELSE NULL END)"""
            if age_range == '<18':
                query += f" AND {age_expr} < 18"
            elif age_range == '18-35':
                query += f" AND {age_expr} BETWEEN 18 AND 35"
            elif age_range == '35-60':
                query += f" AND {age_expr} > 35 AND {age_expr} <= 60"
            elif age_range == '60+':
                query += f" AND {age_expr} > 60"

        # TB Decision filter
        if decision_tb:
            if decision_tb == 'en_cours':
                query += " AND t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL)"
            else:
                query += " AND t.patient_id IS NOT NULL AND t.decision = ?"
                params.append(decision_tb)

        # Date range filter (by treatment/follow-up start date)
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        if date_from or date_to:
            date_conditions = []
            if date_from and date_to:
                date_conditions.append("(t.date_debut_traitement BETWEEN ? AND ?)")
                date_conditions.append("(v.date_debut_suivi BETWEEN ? AND ?)")
                params.extend([date_from, date_to, date_from, date_to])
            elif date_from:
                date_conditions.append("(t.date_debut_traitement >= ?)")
                date_conditions.append("(v.date_debut_suivi >= ?)")
                params.extend([date_from, date_from])
            elif date_to:
                date_conditions.append("(t.date_debut_traitement <= ?)")
                date_conditions.append("(v.date_debut_suivi <= ?)")
                params.extend([date_to, date_to])
            query += f" AND ({' OR '.join(date_conditions)})"

        # Sorting: text columns sorted at SQL level, age/ctrl at Python level
        _sql_sort_map = {
            'registre': 'tb_registre', 'labo': 'lab_id',
            'code_vih': 'vih_code', 'nom': 'p.nom',
            'sexe': 'p.sexe', 'statut': 'p.statut', 'programme': 'programmes',
        }
        if sort_by in _sql_sort_map:
            _dir = 'DESC' if sort_dir == 'desc' else 'ASC'
            query += f" ORDER BY {_sql_sort_map[sort_by]} {_dir}, p.nom, p.prenoms"
        elif sort_by not in ('age', 'ctrl'):
            query += " ORDER BY p.nom, p.prenoms"

        patients = db.execute(query, params).fetchall()

        # Calculer le prochain contrôle pour chaque patient
        today = today_str()
        patient_list = []
        for p in patients:
            patient_dict = dict(p)
            programmes = get_patient_programs(db, p['id'])
            patient_dict['programmes'] = programmes

            # Prochain contrôle TB
            next_ctrl = None
            ctrl_overdue = False
            if 'TB' in programmes:
                tb = db.execute("SELECT * FROM suivi_tb WHERE patient_id = ?", (p['id'],)).fetchone()
                if tb:
                    checks = [
                        ('ctrl_m2_date', 'ctrl_m2_fait', 'M2'),
                        ('ctrl_m5_date', 'ctrl_m5_fait', 'M5'),
                        ('ctrl_m6_date', 'ctrl_m6_fait', 'M6'),
                    ]
                    for date_key, fait_key, label in checks:
                        if tb[date_key] and not tb[fait_key]:
                            if next_ctrl is None or tb[date_key] < next_ctrl:
                                next_ctrl = tb[date_key]
                                ctrl_overdue = tb[date_key] < today

            patient_dict['next_ctrl'] = next_ctrl
            patient_dict['ctrl_overdue'] = ctrl_overdue

            # Computed age for sorting and display
            if p['date_naissance']:
                try:
                    born = datetime.strptime(p['date_naissance'], '%Y-%m-%d').date()
                    patient_dict['computed_age'] = (datetime.now().date() - born).days // 365
                except Exception:
                    patient_dict['computed_age'] = p['age'] or 999
            else:
                patient_dict['computed_age'] = p['age'] or 999
            patient_dict['display_age'] = patient_dict['computed_age'] if patient_dict['computed_age'] != 999 else None

            patient_list.append(patient_dict)

        # Overdue-only filter (post-computation)
        if overdue_only:
            patient_list = [p for p in patient_list if p.get('ctrl_overdue')]

        # Python-side sorting for computed fields (age, prochain contrôle)
        if sort_by == 'age':
            patient_list.sort(key=lambda p: p.get('computed_age') or 999, reverse=(sort_dir == 'desc'))
        elif sort_by == 'ctrl':
            patient_list.sort(key=lambda p: p.get('next_ctrl') or '9999-99-99', reverse=(sort_dir == 'desc'))

        # ── Pagination ──
        try:
            per_page = max(5, min(int(request.args.get('per_page', 10)), 100))
        except ValueError:
            per_page = 10
        total_count = len(patient_list)
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        try:
            page = int(request.args.get('page', 1))
        except ValueError:
            page = 1
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * per_page
        page_patients = patient_list[start:start + per_page]

        return render_template('patients.html',
                               patients=page_patients,
                               page=page,
                               total_pages=total_pages,
                               total_count=total_count,
                               per_page=per_page,
                               start_index=start,
                               q=q,
                               statut=statut,
                               programme=programme,
                               age_range=age_range,
                               sexe=sexe,
                               quartier=quartier,
                               quartiers=quartiers,
                               decision_tb=decision_tb,
                               overdue_only=overdue_only,
                               sort_by=sort_by,
                               sort_dir=sort_dir,
                               date_from=date_from,
                               date_to=date_to,
                               vih_revealed=False)
    finally:
        db.close()


@app.route('/patients/print')
@login_required
def patients_print():
    """Version imprimable de la liste patients (même filtres que /patients)."""
    db = get_db()
    try:
        # Reuse the same filter logic as /patients_list
        q = request.args.get('q', '').strip()
        statut = request.args.get('statut', '')
        programme = request.args.get('programme', '')
        age_range = request.args.get('age', '')
        sexe = request.args.get('sexe', '')
        quartier = request.args.get('quartier', '')
        decision_tb = request.args.get('decision_tb', '')
        overdue_only = request.args.get('overdue', '') == '1'
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        query = """
            SELECT DISTINCT p.*, t.lab_id, t.numero_registre AS tb_registre,
                t.date_debut_traitement, t.forme_clinique, t.type_cas, t.decision,
                v.numero_registre AS vih_registre, v.code AS vih_code,
                v.date_debut_suivi,
                (SELECT GROUP_CONCAT(
                    CASE
                        WHEN t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL) THEN 'TB'
                        WHEN v.patient_id IS NOT NULL AND (v.observation != 'Décédé' OR v.observation = '') THEN 'VIH'
                    END
                ) FROM patients p2
                LEFT JOIN suivi_tb t ON t.patient_id = p2.id
                LEFT JOIN suivi_vih v ON v.patient_id = p2.id
                WHERE p2.id = p.id
            ) AS programmes
            FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            WHERE 1=1
        """
        params = []

        if q:
            query += " AND (p.nom LIKE ? OR p.prenoms LIKE ? OR p.id LIKE ? OR t.numero_registre LIKE ? OR v.numero_registre LIKE ? OR v.code LIKE ?)"
            params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])
        if statut:
            query += " AND p.statut = ?"
            params.append(statut)
        if programme == 'TB':
            query += " AND t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL)"
        elif programme == 'VIH':
            query += " AND v.patient_id IS NOT NULL AND (v.observation != 'Décédé' OR v.observation = '')"
        elif programme == 'both':
            query += " AND t.patient_id IS NOT NULL AND v.patient_id IS NOT NULL"
        if sexe:
            query += " AND p.sexe = ?"
            params.append(sexe)
        if quartier:
            query += " AND p.quartier = ?"
            params.append(quartier)
        if decision_tb:
            if decision_tb == 'en_cours':
                query += " AND t.patient_id IS NOT NULL AND (t.decision = '' OR t.decision IS NULL)"
            else:
                query += " AND t.patient_id IS NOT NULL AND t.decision = ?"
                params.append(decision_tb)
        if date_from or date_to:
            date_conditions = []
            if date_from and date_to:
                date_conditions.append("(t.date_debut_traitement BETWEEN ? AND ?)")
                date_conditions.append("(v.date_debut_suivi BETWEEN ? AND ?)")
                params.extend([date_from, date_to, date_from, date_to])
            elif date_from:
                date_conditions.append("(t.date_debut_traitement >= ?)")
                date_conditions.append("(v.date_debut_suivi >= ?)")
                params.extend([date_from, date_from])
            elif date_to:
                date_conditions.append("(t.date_debut_traitement <= ?)")
                date_conditions.append("(v.date_debut_suivi <= ?)")
                params.extend([date_to, date_to])
            query += f" AND ({' OR '.join(date_conditions)})"

        query += " ORDER BY p.nom, p.prenoms"
        patients = db.execute(query, params).fetchall()

        # Build filter description for the title
        filter_parts = []
        if programme: filter_parts.append(f'Programme: {programme}')
        if statut: filter_parts.append(f'Statut: {statut}')
        if sexe: filter_parts.append(f'Sexe: {sexe}')
        if quartier: filter_parts.append(f'Quartier: {quartier}')
        if age_range: filter_parts.append(f'Âge: {age_range}')
        if decision_tb: filter_parts.append(f'Décision TB: {decision_tb}')
        if date_from or date_to: filter_parts.append(f'Période: {date_from or "…"} → {date_to or "…"}')
        if overdue_only: filter_parts.append('Retards uniquement')
        filter_desc = ' · '.join(filter_parts) if filter_parts else 'Tous les patients'

        # Check for VIH patients (confidentiality)
        has_vih = False
        for p in patients:
            if p['vih_registre'] or p['vih_code'] or p['date_debut_suivi']:
                has_vih = True
                break

        return render_template('patients_print.html',
                               patients=patients,
                               filter_desc=filter_desc,
                               utilisateur=session.get('nom_complet', 'Utilisateur'),
                               has_vih=has_vih)
    finally:
        db.close()


@app.route('/patient/<patient_id>')
@login_required
def patient_detail(patient_id):
    """Fiche patient détaillée (page complète)."""
    db = get_db()
    try:
        patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return 'Patient non trouvé', 404

        tb = db.execute("SELECT * FROM suivi_tb WHERE patient_id = ?", (patient_id,)).fetchone()
        vih = db.execute("SELECT * FROM suivi_vih WHERE patient_id = ?", (patient_id,)).fetchone()
        historique = db.execute(
            "SELECT * FROM historique_statut WHERE patient_id = ? ORDER BY date DESC",
            (patient_id,)
        ).fetchall()

        # Calculer la durée TB si applicable
        duree_tb = None
        if tb and tb['date_debut_traitement']:
            try:
                debut = datetime.strptime(tb['date_debut_traitement'], '%Y-%m-%d')
                delta = datetime.now() - debut
                years = delta.days // 365
                months = (delta.days % 365) // 30
                if years > 0:
                    duree_tb = f"{years} an{'s' if years > 1 else ''}"
                    if months > 0:
                        duree_tb += f" {months} mois"
                elif months > 0:
                    duree_tb = f"{months} mois"
                else:
                    duree_tb = f"{delta.days} jour{'s' if delta.days > 1 else ''}"
            except ValueError:
                pass

        # Vérifier si le patient a un suivi TB/VIH actif
        has_tb_active = db.execute(
            "SELECT 1 FROM suivi_tb WHERE patient_id = ? AND (decision = '' OR decision IS NULL)",
            (patient_id,)
        ).fetchone() is not None
        has_vih_active = db.execute(
            "SELECT 1 FROM suivi_vih WHERE patient_id = ? AND (observation != 'Décédé' OR observation = '')",
            (patient_id,)
        ).fetchone() is not None

        # Compute display age
        display_age = None
        if patient['date_naissance']:
            try:
                born = datetime.strptime(patient['date_naissance'], '%Y-%m-%d').date()
                display_age = (datetime.now().date() - born).days // 365
            except Exception:
                display_age = patient['age']
        else:
            display_age = patient['age']

        return render_template('patient_detail.html',
                               patient=patient,
                               tb=tb,
                               vih=vih,
                               historique=historique,
                               duree_tb=duree_tb,
                               has_tb_active=has_tb_active,
                               has_vih_active=has_vih_active,
                               display_age=display_age)
    finally:
        db.close()


@app.route('/patient/<patient_id>/print')
@login_required
def patient_print(patient_id):
    """Version imprimable de la fiche patient (A4, noir & blanc, formelle)."""
    db = get_db()
    try:
        patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return 'Patient non trouvé', 404

        tb = db.execute("SELECT * FROM suivi_tb WHERE patient_id = ?", (patient_id,)).fetchone()
        vih = db.execute("SELECT * FROM suivi_vih WHERE patient_id = ?", (patient_id,)).fetchone()
        historique = db.execute(
            "SELECT * FROM historique_statut WHERE patient_id = ? ORDER BY date DESC",
            (patient_id,)
        ).fetchall()

        # Calculer la durée TB si applicable
        duree_tb = None
        if tb and tb['date_debut_traitement']:
            try:
                debut = datetime.strptime(tb['date_debut_traitement'], '%Y-%m-%d')
                delta = datetime.now() - debut
                years = delta.days // 365
                months = (delta.days % 365) // 30
                if years > 0:
                    duree_tb = f"{years} an{'s' if years > 1 else ''}"
                    if months > 0:
                        duree_tb += f" {months} mois"
                elif months > 0:
                    duree_tb = f"{months} mois"
                else:
                    duree_tb = f"{delta.days} jour{'s' if delta.days > 1 else ''}"
            except ValueError:
                pass

        # Compute display age
        display_age = None
        if patient['date_naissance']:
            try:
                born = datetime.strptime(patient['date_naissance'], '%Y-%m-%d').date()
                display_age = (datetime.now().date() - born).days // 365
            except Exception:
                display_age = patient['age']
        else:
            display_age = patient['age']

        # Organisation settings
        settings = get_all_settings()

        return render_template('patient_print.html',
                               patient=patient,
                               tb=tb,
                               vih=vih,
                               historique=historique,
                               duree_tb=duree_tb,
                               display_age=display_age,
                               utilisateur=session.get('nom_complet', 'Utilisateur'),
                               today_fr=datetime.now().strftime('%d/%m/%Y'),
                               org_name=settings.get('org_name', ''),
                               org_drapp=settings.get('org_drapp', ''),
                               org_destinator=settings.get('org_destinator', ''),
                               org_service=settings.get('org_service', ''))
    finally:
        db.close()


@app.route('/patient/<patient_id>/json')
@login_required
def patient_detail_json(patient_id):
    """Détail patient en JSON (pour API)."""
    db = get_db()
    try:
        patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return jsonify({'error': 'Patient non trouvé'}), 404

        tb = db.execute("SELECT * FROM suivi_tb WHERE patient_id = ?", (patient_id,)).fetchone()
        vih = db.execute("SELECT * FROM suivi_vih WHERE patient_id = ?", (patient_id,)).fetchone()
        historique = db.execute(
            "SELECT * FROM historique_statut WHERE patient_id = ? ORDER BY date DESC",
            (patient_id,)
        ).fetchall()

        duree_tb = None
        if tb and tb['date_debut_traitement']:
            try:
                debut = datetime.strptime(tb['date_debut_traitement'], '%Y-%m-%d')
                delta = datetime.now() - debut
                years = delta.days // 365
                months = (delta.days % 365) // 30
                if years > 0:
                    duree_tb = f"{years} an{'s' if years > 1 else ''}"
                    if months > 0:
                        duree_tb += f" {months} mois"
                elif months > 0:
                    duree_tb = f"{months} mois"
                else:
                    duree_tb = f"{delta.days} jour{'s' if delta.days > 1 else ''}"
            except ValueError:
                pass

        return jsonify({
            'patient': dict(patient),
            'tb': dict(tb) if tb else None,
            'vih': dict(vih) if vih else None,
            'historique': [dict(h) for h in historique],
            'duree_tb': duree_tb,
        })
    finally:
        db.close()


@app.route('/patient/<patient_id>/ctrl', methods=['POST'])
@role_required('admin', 'user')
def mark_control_done(patient_id):
    """Marquer un contrôle TB comme effectué."""
    db = get_db()
    try:
        data = request.json
        ctrl_key = data.get('controle')  # M2, M5, M6
        resultat = data.get('resultat', '')

        if ctrl_key not in ('M2', 'M5', 'M6'):
            return jsonify({'success': False, 'error': 'Clé contrôle invalide'}), 400

        col_date = f'ctrl_{ctrl_key.lower()}_date'
        col_fait = f'ctrl_{ctrl_key.lower()}_fait'
        col_resultat = f'ctrl_{ctrl_key.lower()}_resultat'

        db.execute(f"""
            UPDATE suivi_tb SET {col_fait} = 1, {col_resultat} = ?
            WHERE patient_id = ?
        """, (resultat, patient_id))

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?)
        """, ('suivi_tb', patient_id, json.dumps({'controle': ctrl_key, 'resultat': resultat}, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/poids', methods=['POST'])
@role_required('admin', 'user')
def update_poids(patient_id):
    """Mettre à jour les poids d\'un patient TB."""
    db = get_db()
    try:
        data = request.json
        db.execute("""
            UPDATE suivi_tb SET poids_m0 = ?, poids_m2 = ?, poids_m5 = ?, poids_m6 = ?
            WHERE patient_id = ?
        """, (
            data.get('poids_m0') or None,
            data.get('poids_m2') or None,
            data.get('poids_m5') or None,
            data.get('poids_m6') or None,
            patient_id
        ))

        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?)
        """, ('suivi_tb', patient_id, json.dumps(data, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/tb/update', methods=['POST'])
@role_required('admin', 'user')
def update_tb_ctrl(patient_id):
    """Mettre à jour les dates et résultats des contrôles TB."""
    db = get_db()
    try:
        data = request.json
        db.execute("""
            UPDATE suivi_tb SET
                ctrl_m2_date = ?, ctrl_m2_fait = ?, ctrl_m2_resultat = ?,
                ctrl_m5_date = ?, ctrl_m5_fait = ?, ctrl_m5_resultat = ?,
                ctrl_m6_date = ?, ctrl_m6_fait = ?, ctrl_m6_resultat = ?
            WHERE patient_id = ?
        """, (
            data.get('ctrl_m2_date') or None, data.get('ctrl_m2_fait', 0), data.get('ctrl_m2_resultat', ''),
            data.get('ctrl_m5_date') or None, data.get('ctrl_m5_fait', 0), data.get('ctrl_m5_resultat', ''),
            data.get('ctrl_m6_date') or None, data.get('ctrl_m6_fait', 0), data.get('ctrl_m6_resultat', ''),
            patient_id
        ))

        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?)
        """, ('suivi_tb', patient_id, json.dumps(data, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/tb/lab', methods=['POST'])
@role_required('admin', 'user')
def update_tb_lab_id(patient_id):
    """Mettre à jour le N° laboratoire TB."""
    db = get_db()
    try:
        data = request.json
        lab_id = data.get('lab_id', '')

        # Vérifier que le patient a un suivi TB
        tb = db.execute('SELECT * FROM suivi_tb WHERE patient_id = ?', (patient_id,)).fetchone()
        if not tb:
            return jsonify({'success': False, 'error': 'Pas de suivi TB pour ce patient'}), 400

        old_lab_id = tb['lab_id'] or ''

        db.execute('UPDATE suivi_tb SET lab_id = ? WHERE patient_id = ?', (lab_id, patient_id))

        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?, ?)
        """, ('suivi_tb', patient_id, json.dumps({'lab_id': old_lab_id}, ensure_ascii=False),
               json.dumps({'lab_id': lab_id}, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/vih/code', methods=['POST'])
@role_required('admin', 'user')
def update_vih_code(patient_id):
    """Mettre à jour le code VIH d'un patient."""
    db = get_db()
    try:
        data = request.json
        code = data.get('code', '')

        # Vérifier que le patient a un suivi VIH
        vih = db.execute('SELECT * FROM suivi_vih WHERE patient_id = ?', (patient_id,)).fetchone()
        if not vih:
            return jsonify({'success': False, 'error': 'Pas de suivi VIH pour ce patient'}), 400

        old_code = vih['code'] or ''

        db.execute('UPDATE suivi_vih SET code = ? WHERE patient_id = ?', (code, patient_id))

        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?, ?)
        """, ('suivi_vih', patient_id, json.dumps({'code': old_code}, ensure_ascii=False),
               json.dumps({'code': code}, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/add-tb', methods=['POST'])
@role_required('admin', 'user')
def add_tb_to_patient(patient_id):
    """Ajouter un volet TB à un patient existant."""
    db = get_db()
    try:
        data = request.json

        # Vérifier que le patient existe
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'error': 'Patient non trouvé'}), 404

        # Vérifier qu'il n'a pas déjà un suivi TB actif
        existing = db.execute(
            'SELECT id FROM suivi_tb WHERE patient_id = ? AND (decision = "" OR decision IS NULL)',
            (patient_id,)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'error': 'Ce patient a déjà un suivi TB actif'}), 400

        # Générer le numéro de registre
        numero_tb = next_registre(db, 'TB')

        # Dates prévues des contrôles calculées depuis la date de début de traitement
        ctrl_dates = tb_control_dates(data.get('date_debut_traitement'))

        db.execute("""
            INSERT INTO suivi_tb (patient_id, numero_registre, lab_id, date_debut_traitement, forme_clinique, type_cas,
                                  ctrl_m2_date, ctrl_m5_date, ctrl_m6_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            numero_tb,
            data.get('lab_id', ''),
            data.get('date_debut_traitement'),
            data.get('forme_clinique', ''),
            data.get('type_cas', ''),
            ctrl_dates['ctrl_m2_date'],
            ctrl_dates['ctrl_m5_date'],
            ctrl_dates['ctrl_m6_date']
        ))

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'create', ?, ?)
        """, ('suivi_tb', patient_id, json.dumps({
            'numero_registre': numero_tb,
            'lab_id': data.get('lab_id', ''),
            'date_debut_traitement': data.get('date_debut_traitement'),
            'forme_clinique': data.get('forme_clinique', ''),
            'type_cas': data.get('type_cas', ''),
            'ctrl_m2_date': ctrl_dates['ctrl_m2_date'],
            'ctrl_m5_date': ctrl_dates['ctrl_m5_date'],
            'ctrl_m6_date': ctrl_dates['ctrl_m6_date']
        }, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True, 'numero_registre': numero_tb})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/add-vih', methods=['POST'])
@role_required('admin', 'user')
def add_vih_to_patient(patient_id):
    """Ajouter un volet VIH à un patient existant."""
    db = get_db()
    try:
        data = request.json

        # Vérifier que le patient existe
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'error': 'Patient non trouvé'}), 404

        # Vérifier qu'il n'a pas déjà un suivi VIH actif
        existing = db.execute(
            "SELECT id FROM suivi_vih WHERE patient_id = ? AND (observation != 'Décédé' OR observation = '')",
            (patient_id,)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'error': 'Ce patient a déjà un suivi VIH actif'}), 400

        # Générer le numéro de registre
        numero_vih = next_registre(db, 'VIH')

        # Générer le code VIH si non fourni
        vih_code = data.get('code', '').strip()
        if not vih_code:
            vih_code = generate_vih_code(
                patient['nom'], patient['prenoms'],
                patient['date_naissance'], patient['age']
            )

        db.execute("""
            INSERT INTO suivi_vih (patient_id, numero_registre, code, date_debut_suivi, observation)
            VALUES (?, ?, ?, ?, ?)
        """, (
            patient_id,
            numero_vih,
            vih_code,
            data.get('date_debut_suivi'),
            data.get('observation', 'Nouveau')
        ))

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'create', ?, ?)
        """, ('suivi_vih', patient_id, json.dumps({
            'numero_registre': numero_vih,
            'code': vih_code,
            'date_debut_suivi': data.get('date_debut_suivi'),
            'observation': data.get('observation', 'Nouveau')
        }, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True, 'numero_registre': numero_vih})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/statut', methods=['POST'])
@role_required('admin', 'user')
def change_statut(patient_id):
    """Changer le statut d'un patient."""
    db = get_db()
    try:
        data = request.json
        nouveau_statut = data.get('nouveau_statut')
        motif = data.get('motif', '')

        if nouveau_statut not in ('incarcere', 'libere', 'transfere', 'decede'):
            return jsonify({'success': False, 'error': 'Statut invalide'}), 400

        # Récupérer l'ancien statut
        patient = db.execute('SELECT statut FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'error': 'Patient non trouvé'}), 404

        ancien_statut = patient['statut']

        # Mettre à jour le statut
        db.execute('UPDATE patients SET statut = ?, updated_at = ? WHERE id = ?',
                   (nouveau_statut, now_str(), patient_id))

        # Enregistrer dans l'historique
        db.execute("""
            INSERT INTO historique_statut (patient_id, ancien_statut, nouveau_statut, motif)
            VALUES (?, ?, ?, ?)
        """, (patient_id, ancien_statut, nouveau_statut, motif))

        # Si libération, mettre à jour les infos de contact
        if nouveau_statut == 'libere':
            db.execute("""
                UPDATE patients SET telephone = ?, adresse = ?, contact_nom = ?, contact_tel = ?
                WHERE id = ?
            """, (
                data.get('telephone', ''),
                data.get('adresse', ''),
                data.get('contact_nom', ''),
                data.get('contact_tel', ''),
                patient_id
            ))

        # Si transfert, enregistrer le motif
        if nouveau_statut == 'transfere' and motif:
            pass  # Le motif est déjà enregistré dans historique_statut

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?, ?)
        """, (
            'patients', patient_id,
            json.dumps({'statut': ancien_statut}, ensure_ascii=False),
            json.dumps({'statut': nouveau_statut, 'motif': motif}, ensure_ascii=False),
            current_user()
        ))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/edit', methods=['POST'])
@role_required('admin', 'user')
def edit_patient(patient_id):
    """Modifier les informations d'un patient."""
    db = get_db()
    try:
        data = request.json

        # Vérifier que le patient existe
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'error': 'Patient non trouvé'}), 404

        # Validation: champs obligatoires
        if not data.get('nom', '').strip():
            return jsonify({'success': False, 'error': 'Le nom du patient est obligatoire.'}), 400
        if data.get('situation_penale', patient['situation_penale']) not in ('Condamné', 'Prévenu'):
            return jsonify({'success': False, 'error': 'La situation pénale (Condamné ou Prévenu) est obligatoire.'}), 400

        # Calculer l'âge si date de naissance fournie
        age = data.get('age')
        date_naissance = data.get('date_naissance')
        if date_naissance and not age:
            try:
                dob = datetime.strptime(date_naissance, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except ValueError:
                pass

        # Mettre à jour les champs modifiables
        db.execute("""
            UPDATE patients SET
                nom = ?, prenoms = ?, date_naissance = ?, age = ?, sexe = ?,
                quartier = ?, situation_penale = ?,
                telephone = ?, adresse = ?, contact_nom = ?, contact_tel = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            data.get('nom', patient['nom']).strip(),
            data.get('prenoms', patient['prenoms']).strip(),
            date_naissance or patient['date_naissance'],
            age or patient['age'],
            data.get('sexe', patient['sexe']),
            data.get('quartier', patient['quartier']),
            data.get('situation_penale', patient['situation_penale']),
            data.get('telephone', patient['telephone']),
            data.get('adresse', patient['adresse']),
            data.get('contact_nom', patient['contact_nom']),
            data.get('contact_tel', patient['contact_tel']),
            now_str(),
            patient_id
        ))

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, nouveau_contenu, auteur)
            VALUES (?, ?, 'update', ?, ?, ?)
        """, (
            'patients', patient_id,
            json.dumps({
                'nom': patient['nom'], 'prenoms': patient['prenoms'],
                'date_naissance': patient['date_naissance'],
                'quartier': patient['quartier'],
                'telephone': patient['telephone'],
                'adresse': patient['adresse'],
            }, ensure_ascii=False),
            json.dumps({
                'nom': data.get('nom', patient['nom']),
                'prenoms': data.get('prenoms', patient['prenoms']),
                'date_naissance': date_naissance or patient['date_naissance'],
                'quartier': data.get('quartier', patient['quartier']),
                'telephone': data.get('telephone', patient['telephone']),
                'adresse': data.get('adresse', patient['adresse']),
            }, ensure_ascii=False),
            current_user()
        ))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/<patient_id>/delete', methods=['POST'])
@role_required('admin')
def delete_patient(patient_id):
    """Supprimer un patient et toutes ses données associées."""
    db = get_db()
    try:
        # Vérifier que le patient existe
        patient = db.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({'success': False, 'error': 'Patient non trouvé'}), 404

        # Audit avant suppression
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, auteur)
            VALUES (?, ?, 'delete', ?, ?)
        """, (
            'patients', patient_id,
            json.dumps({
                'id': patient['id'],
                'nom': patient['nom'],
                'prenoms': patient['prenoms'],
                'date_naissance': patient['date_naissance'],
                'sexe': patient['sexe'],
                'statut': patient['statut'],
            }, ensure_ascii=False),
            current_user()
        ))

        # Supprimer les données associées (dans l'ordre pour respecter les FK)
        db.execute('DELETE FROM journal_audit WHERE id_cible = ?', (patient_id,))
        db.execute('DELETE FROM historique_statut WHERE patient_id = ?', (patient_id,))
        db.execute('DELETE FROM suivi_vih WHERE patient_id = ?', (patient_id,))
        db.execute('DELETE FROM suivi_tb WHERE patient_id = ?', (patient_id,))
        db.execute('DELETE FROM patients WHERE id = ?', (patient_id,))

        db.commit()
        return jsonify({'success': True, 'message': f'Patient {patient_id} supprimé.'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@app.route('/patient/create', methods=['POST'])
@role_required('admin', 'user')
def create_patient():
    """Créer un nouveau patient."""
    db = get_db()
    try:
        data = request.json

        # Validation: programme obligatoire
        programme = data.get('programme', '').strip()
        if not programme or programme not in ('TB', 'VIH'):
            return jsonify({'success': False, 'error': 'Le programme médical (TB ou VIH) est obligatoire.'}), 400

        # Validation: champs obligatoires
        nom = data.get('nom', '').strip()
        sexe = data.get('sexe', '')
        date_naissance = data.get('date_naissance')
        age = data.get('age')
        statut = data.get('statut', 'incarcere')
        situation_penale = data.get('situation_penale', '').strip()

        if not nom:
            return jsonify({'success': False, 'error': 'Le nom du patient est obligatoire.'}), 400
        if sexe not in ('M', 'F'):
            return jsonify({'success': False, 'error': 'Le sexe est obligatoire.'}), 400
        if not date_naissance and not age:
            return jsonify({'success': False, 'error': 'La date de naissance ou l\'âge est obligatoire.'}), 400
        if situation_penale not in ('Condamné', 'Prévenu'):
            return jsonify({'success': False, 'error': 'La situation pénale (Condamné ou Prévenu) est obligatoire.'}), 400
        if statut in ('libere', 'transfere') and (not data.get('telephone') or not data.get('adresse')):
            return jsonify({'success': False, 'error': 'Le téléphone et l\'adresse sont obligatoires pour une libération ou un transfert.'}), 400
        if programme == 'TB':
            if not data.get('date_debut_traitement'):
                return jsonify({'success': False, 'error': 'La date de début de traitement est obligatoire pour le TB.'}), 400
            if data.get('forme_clinique') not in ('TPB+', 'TPB-', 'TEP'):
                return jsonify({'success': False, 'error': 'La forme clinique est obligatoire pour le TB.'}), 400
            if data.get('type_cas') not in ('Nouveau', 'Echec', 'Rechute', 'Reprise', 'Transfert entrant'):
                return jsonify({'success': False, 'error': 'Le type de cas est obligatoire pour le TB.'}), 400
        if programme == 'VIH' and not data.get('date_debut_suivi'):
            return jsonify({'success': False, 'error': 'La date de début de suivi est obligatoire pour le VIH.'}), 400

        patient_id = next_patient_id(db)

        # Calculer l'âge si date de naissance fournie
        age = data.get('age')
        date_naissance = data.get('date_naissance')
        if date_naissance and not age:
            try:
                dob = datetime.strptime(date_naissance, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except ValueError:
                pass

        # Insérer le patient
        db.execute("""
            INSERT INTO patients (id, nom, prenoms, date_naissance, age, sexe,
                                  statut, quartier, situation_penale,
                                  telephone, adresse, contact_nom, contact_tel, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            data.get('nom', '').strip(),
            data.get('prenoms', '').strip(),
            date_naissance or None,
            age,
            data.get('sexe', 'M'),
            data.get('statut', 'incarcere'),
            data.get('quartier', ''),
            data.get('situation_penale', ''),
            data.get('telephone', ''),
            data.get('adresse', ''),
            data.get('contact_nom', ''),
            data.get('contact_tel', ''),
            current_user()
        ))

        # Si programme TB sélectionné
        if data.get('programme') == 'TB':
            numero_tb = next_registre(db, 'TB')
            # Dates prévues des contrôles calculées depuis la date de début de traitement
            ctrl_dates = tb_control_dates(data.get('date_debut_traitement'))
            db.execute("""
                INSERT INTO suivi_tb (patient_id, numero_registre, lab_id, date_debut_traitement, forme_clinique, type_cas,
                                      ctrl_m2_date, ctrl_m5_date, ctrl_m6_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                numero_tb,
                data.get('lab_id', ''),
                data.get('date_debut_traitement'),
                data.get('forme_clinique', ''),
                data.get('type_cas', ''),
                ctrl_dates['ctrl_m2_date'],
                ctrl_dates['ctrl_m5_date'],
                ctrl_dates['ctrl_m6_date']
            ))

        # Si programme VIH sélectionné
        if data.get('programme') == 'VIH':
            numero_vih = next_registre(db, 'VIH')
            # Générer le code VIH si non fourni
            vih_code = data.get('code', '').strip()
            if not vih_code:
                vih_code = generate_vih_code(
                    data.get('nom', ''), data.get('prenoms', ''),
                    data.get('date_naissance'), data.get('age')
                )
            db.execute("""
                INSERT INTO suivi_vih (patient_id, numero_registre, code, date_debut_suivi, observation)
                VALUES (?, ?, ?, ?, ?)
            """, (
                patient_id,
                numero_vih,
                vih_code,
                data.get('date_debut_suivi'),
                data.get('observation', 'Nouveau')
            ))

        # Audit
        db.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur)
            VALUES (?, ?, 'create', ?, ?)
        """, ('patients', patient_id, json.dumps(data, ensure_ascii=False), current_user()))

        db.commit()
        return jsonify({'success': True, 'id': patient_id})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ── Rapports ─────────────────────────────────────────────────────

@app.route('/rapports')
@login_required
def rapports():
    """Page des rapports mensuels."""
    db = get_db()
    try:
        # Paramètres mois/année
        mois = request.args.get('mois', '')
        annee = request.args.get('annee', '')

        now = datetime.now()
        if not mois:
            mois = str(now.month)
        if not annee:
            annee = str(now.year)

        mois = int(mois)
        annee = int(annee)

        # Dernier jour du mois choisi
        if mois == 12:
            fin_mois = f'{annee}-12-31'
            debut_mois = f'{annee}-12-01'
        else:
            fin_mois_dt = datetime(annee, mois + 1, 1) - timedelta(days=1)
            fin_mois = fin_mois_dt.strftime('%Y-%m-%d')
            debut_mois = f'{annee}-{mois:02d}-01'

        # Premier jour du mois suivant (pour bornes)
        if mois == 12:
            debut_mois_suivant = f'{annee + 1}-01-01'
        else:
            debut_mois_suivant = f'{annee}-{mois + 1:02d}-01'

        stats = {}

        # ── TB ────────────────────────────────────────────────────
        # Patients actifs TB au dernier jour du mois
        # (patient dans suivi_tb ET statut patients = incarcere à cette date)
        stats['tb_actifs'] = db.execute("""
            SELECT COUNT(DISTINCT t.patient_id)
            FROM suivi_tb t
            JOIN patients p ON p.id = t.patient_id
            WHERE (t.decision = '' OR t.decision IS NULL)
            AND p.statut = 'incarcere'
        """).fetchone()[0]

        # Nouveaux cas TB du mois
        stats['tb_nouveaux'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_debut_traitement >= ? AND date_debut_traitement <= ?
        """, (debut_mois, fin_mois)).fetchone()[0]

        # Sorties TB du mois (guéri, traitement terminé, perdu de vue)
        stats['tb_sorties'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_decision >= ? AND date_decision <= ?
            AND decision IN ('Guéri', 'Traitement terminé', 'Perdu de vue')
        """, (debut_mois, fin_mois)).fetchone()[0]

        # Décès TB du mois
        stats['tb_deces'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_decision >= ? AND date_decision <= ?
            AND decision = 'Décédé'
        """, (debut_mois, fin_mois)).fetchone()[0]

        # Transferts TB du mois
        stats['tb_transferts'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_decision >= ? AND date_decision <= ?
            AND decision = 'Transféré'
        """, (debut_mois, fin_mois)).fetchone()[0]

        # Rétention TB 6 mois
        stats['tb_total_6m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_debut_traitement <= date(?, '-6 months')
        """, (fin_mois,)).fetchone()[0]
        stats['tb_retenus_6m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_debut_traitement <= date(?, '-6 months')
            AND (decision = '' OR decision IS NULL)
        """, (fin_mois,)).fetchone()[0]

        # Rétention TB 12 mois
        stats['tb_total_12m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_debut_traitement <= date(?, '-12 months')
        """, (fin_mois,)).fetchone()[0]
        stats['tb_retenus_12m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_tb
            WHERE date_debut_traitement <= date(?, '-12 months')
            AND (decision = '' OR decision IS NULL)
        """, (fin_mois,)).fetchone()[0]

        # ── VIH ────────────────────────────────────────────────────
        # Patients actifs VIH
        stats['vih_actifs'] = db.execute("""
            SELECT COUNT(DISTINCT v.patient_id)
            FROM suivi_vih v
            JOIN patients p ON p.id = v.patient_id
            WHERE (v.observation IS NULL OR v.observation = '' OR v.observation NOT IN ('Décédé', 'Libéré'))
            AND p.statut = 'incarcere'
        """).fetchone()[0]

        # Nouveaux VIH du mois
        stats['vih_nouveaux'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE date_debut_suivi >= ? AND date_debut_suivi <= ?
        """, (debut_mois, fin_mois)).fetchone()[0]

        # Sorties VIH du mois
        stats['vih_sorties'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE observation IN ('Libéré', 'Transfert')
            AND id IN (
                SELECT id FROM suivi_vih WHERE date_debut_suivi <= ?
            )
        """, (fin_mois,)).fetchone()[0]

        # Décès VIH du mois
        stats['vih_deces'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE observation = 'Décédé'
        """).fetchone()[0]

        # Rétention VIH 6 mois
        stats['vih_total_6m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE date_debut_suivi <= date(?, '-6 months')
        """, (fin_mois,)).fetchone()[0]
        stats['vih_retenus_6m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE date_debut_suivi <= date(?, '-6 months')
            AND (observation IS NULL OR observation = '' OR observation NOT IN ('Décédé', 'Libéré'))
        """, (fin_mois,)).fetchone()[0]

        # Rétention VIH 12 mois
        stats['vih_total_12m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE date_debut_suivi <= date(?, '-12 months')
        """, (fin_mois,)).fetchone()[0]
        stats['vih_retenus_12m'] = db.execute("""
            SELECT COUNT(*) FROM suivi_vih
            WHERE date_debut_suivi <= date(?, '-12 months')
            AND (observation IS NULL OR observation = '' OR observation NOT IN ('Décédé', 'Libéré'))
        """, (fin_mois,)).fetchone()[0]

        # Taux de rétention
        stats['tb_retention_6m'] = round((stats['tb_retenus_6m'] / stats['tb_total_6m'] * 100) if stats['tb_total_6m'] > 0 else 0)
        stats['tb_retention_12m'] = round((stats['tb_retenus_12m'] / stats['tb_total_12m'] * 100) if stats['tb_total_12m'] > 0 else 0)
        stats['vih_retention_6m'] = round((stats['vih_retenus_6m'] / stats['vih_total_6m'] * 100) if stats['vih_total_6m'] > 0 else 0)
        stats['vih_retention_12m'] = round((stats['vih_retenus_12m'] / stats['vih_total_12m'] * 100) if stats['vih_total_12m'] > 0 else 0)

        # ── TB: répartition des issues du mois ─────────────────────
        stats['tb_issues'] = []
        issue_rows = db.execute("""
            SELECT decision, COUNT(*) as cnt FROM suivi_tb
            WHERE date_decision >= ? AND date_decision <= ?
            AND decision != '' AND decision IS NOT NULL
            GROUP BY decision
        """, (debut_mois, fin_mois)).fetchall()
        for row in issue_rows:
            stats['tb_issues'].append({'decision': row['decision'], 'count': row['cnt']})

        # ── TB: taux de réalisation des contrôles bactériologiques ──
        ctrl_prevus = 0
        ctrl_faits = 0
        ctrl_data = db.execute("""
            SELECT ctrl_m2_date, ctrl_m2_fait, ctrl_m5_date, ctrl_m5_fait,
                   ctrl_m6_date, ctrl_m6_fait
            FROM suivi_tb WHERE (decision = '' OR decision IS NULL)
        """).fetchall()
        for c in ctrl_data:
            for date_key, fait_key in [('ctrl_m2_date', 'ctrl_m2_fait'),
                                       ('ctrl_m5_date', 'ctrl_m5_fait'),
                                       ('ctrl_m6_date', 'ctrl_m6_fait')]:
                if c[date_key] and debut_mois <= c[date_key] <= fin_mois:
                    ctrl_prevus += 1
                    if c[fait_key]:
                        ctrl_faits += 1
        stats['tb_ctrl_prevus'] = ctrl_prevus
        stats['tb_ctrl_faits'] = ctrl_faits
        stats['tb_ctrl_taux'] = round((ctrl_faits / ctrl_prevus * 100) if ctrl_prevus > 0 else 0)

        # ── TB: répartition par forme clinique et type de cas ──────
        stats['tb_formes'] = db.execute("""
            SELECT forme_clinique, COUNT(*) as cnt FROM suivi_tb
            WHERE (decision = '' OR decision IS NULL) AND forme_clinique != ''
            GROUP BY forme_clinique
        """).fetchall()
        stats['tb_types_cas'] = db.execute("""
            SELECT type_cas, COUNT(*) as cnt FROM suivi_tb
            WHERE (decision = '' OR decision IS NULL) AND type_cas != ''
            GROUP BY type_cas
        """).fetchall()

        # ── Démographie: répartition des actifs (TB + VIH) ─────────
        # Par tranche d'âge
        stats['demo_age'] = []
        age_groups = [('<18', 0, 17), ('18-35', 18, 35), ('36-60', 36, 60), ('60+', 61, 999)]
        for label, lo, hi in age_groups:
            cnt = db.execute("""
                SELECT COUNT(DISTINCT p.id) FROM patients p
                LEFT JOIN suivi_tb t ON t.patient_id = p.id
                LEFT JOIN suivi_vih v ON v.patient_id = p.id
                WHERE p.statut = 'incarcere'
                AND (t.patient_id IS NOT NULL OR v.patient_id IS NOT NULL)
                AND (
                    (p.age IS NOT NULL AND p.age BETWEEN ? AND ?)
                    OR (p.date_naissance IS NOT NULL
                        AND CAST((julianday('now') - julianday(p.date_naissance)) / 365.25 AS INTEGER) BETWEEN ? AND ?)
                )
            """, (lo, hi, lo, hi)).fetchone()[0]
            stats['demo_age'].append({'label': label, 'count': cnt})

        # Par sexe
        stats['demo_sexe'] = db.execute("""
            SELECT p.sexe, COUNT(DISTINCT p.id) as cnt FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            WHERE p.statut = 'incarcere'
            AND (t.patient_id IS NOT NULL OR v.patient_id IS NOT NULL)
            GROUP BY p.sexe
        """).fetchall()

        # Par quartier
        stats['demo_quartier'] = db.execute("""
            SELECT p.quartier, COUNT(DISTINCT p.id) as cnt FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            WHERE p.statut = 'incarcere'
            AND (t.patient_id IS NOT NULL OR v.patient_id IS NOT NULL)
            AND p.quartier != ''
            GROUP BY p.quartier
            ORDER BY cnt DESC
        """).fetchall()

        # ── Contrôles en retard (pour résumé exécutif) ──────────────
        stats['overdue_count'] = len(compute_overdue_controls(db))

        # Noms des mois
        mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                     'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

        return render_template('rapports.html',
                               stats=stats,
                               mois=mois,
                               annee=annee,
                               mois_nom=mois_noms[mois],
                               fin_mois=fin_mois,
                               utilisateur=session.get('nom_complet', 'Utilisateur'))
    finally:
        db.close()


# ── Sauvegarde ───────────────────────────────────────────────────

@app.route('/sauvegarde')
@login_required
def sauvegarde():
    """Page de sauvegarde — export et import."""
    db = get_db()
    try:
        # Compter les enregistrements
        stats = {
            'patients': db.execute('SELECT COUNT(*) FROM patients').fetchone()[0],
            'suivi_tb': db.execute('SELECT COUNT(*) FROM suivi_tb').fetchone()[0],
            'suivi_vih': db.execute('SELECT COUNT(*) FROM suivi_vih').fetchone()[0],
            'historique': db.execute('SELECT COUNT(*) FROM historique_statut').fetchone()[0],
            'audit': db.execute('SELECT COUNT(*) FROM journal_audit').fetchone()[0],
            'users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        }
        return render_template('sauvegarde.html', stats=stats)
    finally:
        db.close()


@app.route('/sauvegarde/export-csv')
@role_required('admin', 'user')
def export_csv():
    """Export CSV de la liste des patients (compatible avec les anciens fichiers)."""
    db = get_db()
    try:
        patients = db.execute("""
            SELECT p.*, t.lab_id, t.numero_registre AS tb_registre,
                t.date_debut_traitement, t.forme_clinique, t.type_cas,
                t.decision, t.date_decision,
                v.code AS vih_code, v.numero_registre AS vih_registre,
                v.date_debut_suivi, v.observation
            FROM patients p
            LEFT JOIN suivi_tb t ON t.patient_id = p.id
            LEFT JOIN suivi_vih v ON v.patient_id = p.id
            ORDER BY p.nom, p.prenoms
        """).fetchall()

        output = io.StringIO()
        output.write('\ufeff')  # BOM UTF-8 pour Excel
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)

        # En-tête
        writer.writerow([
            'N° Registre TB', 'N° Registre VIH', 'Nom et prénoms', 'Code VIH', 'Date de naissance',
            'Année de naissance', 'Age', 'Genre', 'Quartier',
            'Situation pénale', 'Statut', 'Téléphone', 'Adresse',
            'Contact (nom)', 'Contact (tel)',
            'N° laboratoire', 'Programme TB', 'Forme clinique', 'Type de cas',
            'Date début traitement', 'Décision TB',
            'Programme VIH', 'Date début suivi VIH', 'Observation VIH',
            'Créé le', 'Modifié le', 'Auteur'
        ])

        for p in patients:
            # Déterminer le programme
            programmes = []
            if p['date_debut_traitement']:
                programmes.append('TB')
            if p['date_debut_suivi']:
                programmes.append('VIH')
            programme_str = ' + '.join(programmes) if programmes else 'Aucun'

            writer.writerow([
                p['tb_registre'] or '',
                p['vih_registre'] or '',
                f"{p['nom']} {p['prenoms']}",
                p['vih_code'] or '',
                p['date_naissance'] or '',
                p['date_naissance'].split('-')[0] if p['date_naissance'] else '',
                f"~{p['age']}" if p['age'] else '',
                'F' if p['sexe'] == 'F' else 'M',
                p['quartier'] or '',
                p['situation_penale'] or '',
                p['statut'] or '',
                p['telephone'] or '',
                p['adresse'] or '',
                p['contact_nom'] or '',
                p['contact_tel'] or '',
                p['lab_id'] or '',
                programme_str,
                p['forme_clinique'] or '',
                p['type_cas'] or '',
                p['date_debut_traitement'] or '',
                p['decision'] or '',
                'VIH' if p['date_debut_suivi'] else '',
                p['date_debut_suivi'] or '',
                p['observation'] or '',
                p['created_at'] or '',
                p['updated_at'] or '',
                p['created_by'] or '',
            ])

        # Retourner le fichier
        output.seek(0)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name=f'suivi_patients_{timestamp}.csv'
        )
    finally:
        db.close()


@app.route('/sauvegarde/export-json')
@role_required('admin', 'user')
def export_json():
    """Export JSON complet (toutes les tables)."""
    db = get_db()
    try:
        data = {
            'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'application': 'Suivi Patient TB & VIH — Mahajanga',
            'tables': {
                'patients': [dict(r) for r in db.execute('SELECT * FROM patients ORDER BY id').fetchall()],
                'suivi_tb': [dict(r) for r in db.execute('SELECT * FROM suivi_tb ORDER BY patient_id').fetchall()],
                'suivi_vih': [dict(r) for r in db.execute('SELECT * FROM suivi_vih ORDER BY patient_id').fetchall()],
                'historique_statut': [dict(r) for r in db.execute('SELECT * FROM historique_statut ORDER BY patient_id, date DESC').fetchall()],
                'journal_audit': [dict(r) for r in db.execute('SELECT * FROM journal_audit ORDER BY date DESC').fetchall()],
            }
        }

        output = json.dumps(data, ensure_ascii=False, indent=2)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        return send_file(
            io.BytesIO(output.encode('utf-8')),
            mimetype='application/json; charset=utf-8',
            as_attachment=True,
            download_name=f'suivi_patients_{timestamp}.json'
        )
    finally:
        db.close()


@app.route('/sauvegarde/import-json', methods=['POST'])
@role_required('admin', 'user')
def import_json():
    """Import JSON — restaure les données."""
    if 'fichier' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    fichier = request.files['fichier']
    if not fichier.filename.endswith('.json'):
        return jsonify({'success': False, 'error': 'Le fichier doit être un .json'}), 400

    try:
        contenu = fichier.read().decode('utf-8')
        data = json.loads(contenu)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return jsonify({'success': False, 'error': f'Fichier JSON invalide : {e}'}), 400

    if 'tables' not in data:
        return jsonify({'success': False, 'error': 'Structure invalide : clé "tables" manquante'}), 400

    db = get_db()
    try:
        tables = data['tables']
        counts = {}

        # Vider les tables dans l'ordre (respecter les FK)
        db.execute('DELETE FROM journal_audit')
        db.execute('DELETE FROM historique_statut')
        db.execute('DELETE FROM suivi_vih')
        db.execute('DELETE FROM suivi_tb')
        db.execute('DELETE FROM patients')

        # Réinsérer les patients
        for p in tables.get('patients', []):
            db.execute("""
                INSERT INTO patients (id, nom, prenoms, date_naissance, age, sexe,
                    statut, quartier, situation_penale, telephone, adresse,
                    contact_nom, contact_tel, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['id'], p['nom'], p.get('prenoms', ''),
                p.get('date_naissance'), p.get('age'),
                p.get('sexe', 'M'), p.get('statut', 'incarcere'),
                p.get('quartier', ''), p.get('situation_penale', ''),
                p.get('telephone', ''), p.get('adresse', ''),
                p.get('contact_nom', ''), p.get('contact_tel', ''),
                p.get('created_at', ''), p.get('updated_at', ''),
                p.get('created_by', 'import')
            ))
        counts['patients'] = len(tables.get('patients', []))

        # Réinsérer suivi_tb
        for t in tables.get('suivi_tb', []):
            db.execute("""
                INSERT INTO suivi_tb (patient_id, numero_registre, lab_id, date_debut_traitement, forme_clinique,
                    type_cas, poids_m0, poids_m2, poids_m5, poids_m6,
                    ctrl_m2_date, ctrl_m2_fait, ctrl_m2_resultat,
                    ctrl_m5_date, ctrl_m5_fait, ctrl_m5_resultat,
                    ctrl_m6_date, ctrl_m6_fait, ctrl_m6_resultat,
                    decision, date_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t['patient_id'], t.get('numero_registre', ''), t.get('lab_id', ''), t.get('date_debut_traitement'), t.get('forme_clinique', ''),
                t.get('type_cas', ''), t.get('poids_m0'), t.get('poids_m2'),
                t.get('poids_m5'), t.get('poids_m6'),
                t.get('ctrl_m2_date'), t.get('ctrl_m2_fait', 0), t.get('ctrl_m2_resultat', ''),
                t.get('ctrl_m5_date'), t.get('ctrl_m5_fait', 0), t.get('ctrl_m5_resultat', ''),
                t.get('ctrl_m6_date'), t.get('ctrl_m6_fait', 0), t.get('ctrl_m6_resultat', ''),
                t.get('decision', ''), t.get('date_decision')
            ))
        counts['suivi_tb'] = len(tables.get('suivi_tb', []))

        # Réinsérer suivi_vih
        for v in tables.get('suivi_vih', []):
            db.execute("""
                INSERT INTO suivi_vih (patient_id, numero_registre, code, date_debut_suivi, observation)
                VALUES (?, ?, ?, ?, ?)
            """, (v['patient_id'], v.get('numero_registre', ''), v.get('code', ''), v.get('date_debut_suivi'), v.get('observation', '')))
        counts['suivi_vih'] = len(tables.get('suivi_vih', []))

        # Réinsérer historique_statut
        for h in tables.get('historique_statut', []):
            db.execute("""
                INSERT INTO historique_statut (patient_id, ancien_statut, nouveau_statut, date, motif)
                VALUES (?, ?, ?, ?, ?)
            """, (h['patient_id'], h['ancien_statut'], h['nouveau_statut'], h.get('date', ''), h.get('motif', '')))
        counts['historique'] = len(tables.get('historique_statut', []))

        # Réinsérer journal_audit
        for a in tables.get('journal_audit', []):
            db.execute("""
                INSERT INTO journal_audit (table_ciblee, id_cible, action, ancien_contenu, nouveau_contenu, auteur, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                a['table_ciblee'], a['id_cible'], a['action'],
                a.get('ancien_contenu'), a.get('nouveau_contenu'),
                a.get('auteur', 'import'), a.get('date', '')
            ))
        counts['audit'] = len(tables.get('journal_audit', []))

        db.commit()
        return jsonify({
            'success': True,
            'message': 'Import terminé avec succès',
            'counts': counts
        })
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ── Journal d'audit ─────────────────────────────────────────────

@app.route('/audit')
@login_required
def audit_log():
    """Page du journal d'audit avec filtres et pagination."""
    db = get_db()
    try:
        # Filtres
        q = request.args.get('q', '').strip()
        table_filter = request.args.get('table_ciblee', '').strip()
        action_filter = request.args.get('action', '').strip()
        auteur_filter = request.args.get('auteur', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        per_page = 20

        # Liste des auteurs distincts
        auteurs = [r[0] for r in db.execute(
            'SELECT DISTINCT auteur FROM journal_audit ORDER BY auteur'
        ).fetchall()]

        # Construction de la requête
        query = 'SELECT * FROM journal_audit WHERE 1=1'
        count_query = 'SELECT COUNT(*) FROM journal_audit WHERE 1=1'
        params = []

        if q:
            query += ' AND (ancien_contenu LIKE ? OR nouveau_contenu LIKE ? OR id_cible LIKE ?)'
            count_query += ' AND (ancien_contenu LIKE ? OR nouveau_contenu LIKE ? OR id_cible LIKE ?)'
            params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
        if table_filter:
            query += ' AND table_ciblee = ?'
            count_query += ' AND table_ciblee = ?'
            params.append(table_filter)
        if action_filter:
            query += ' AND action = ?'
            count_query += ' AND action = ?'
            params.append(action_filter)
        if auteur_filter:
            query += ' AND auteur = ?'
            count_query += ' AND auteur = ?'
            params.append(auteur_filter)

        # Compteur total
        total = db.execute(count_query, params).fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)

        # Page hors bornes → dernière page
        if page > total_pages:
            page = total_pages

        # Offset
        offset = (page - 1) * per_page
        query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
        entries = db.execute(query, params + [per_page, offset]).fetchall()

        return render_template('audit.html',
                               entries=entries,
                               total=total,
                               page=page,
                               total_pages=total_pages,
                               q=q,
                               table_filter=table_filter,
                               action_filter=action_filter,
                               auteur_filter=auteur_filter,
                               auteurs=auteurs)
    finally:
        db.close()


@app.route('/aide')
@login_required
def aide():
    """Page d'aide / guide d'utilisation."""
    return render_template('aide.html')


# ── Main ─────────────────────────────────────────────────────────

# ── Paramètres ────────────────────────────────────────────────

@app.route('/parametres', methods=['GET', 'POST'])
@login_required
def parametres():
    """Page de paramétrage de l'application."""
    db = get_db()
    try:
        settings = get_all_settings()
        message = None
        error = None

        if request.method == 'POST':
            section = request.form.get('section', '')

            if section == 'organization':
                set_setting('org_name', request.form.get('org_name', '').strip())
                set_setting('org_drapp', request.form.get('org_drapp', '').strip())
                set_setting('org_destinator', request.form.get('org_destinator', '').strip())
                set_setting('org_service', request.form.get('org_service', '').strip())
                settings = get_all_settings()
                message = 'Identité de l\'organisation mise à jour.'

            elif section == 'clinical':
                set_setting('vih_interval_days', request.form.get('vih_interval_days', '28').strip())
                set_setting('tb_control_months', request.form.get('tb_control_months', 'M2,M5,M6').strip())
                set_setting('overdue_days', request.form.get('overdue_days', '7').strip())
                settings = get_all_settings()
                message = 'Paramètres cliniques mis à jour.'

            elif section == 'reports':
                set_setting('report_signature', 'true' if request.form.get('report_signature') else 'false')
                set_setting('report_header_note', request.form.get('report_header_note', '').strip())
                settings = get_all_settings()
                message = 'Paramètres de rapport mis à jour.'

            elif section == 'data':
                set_setting('audit_retention_months', request.form.get('audit_retention_months', '24').strip())
                set_setting('archive_inactive_months', request.form.get('archive_inactive_months', '0').strip())
                settings = get_all_settings()
                message = 'Paramètres de données mis à jour.'

            elif section == 'password':
                current_pass = request.form.get('current_password', '')
                new_pass = request.form.get('new_password', '')
                confirm_pass = request.form.get('confirm_password', '')

                user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
                if not user or not check_password_hash(user['password_hash'], current_pass):
                    error = 'Mot de passe actuel incorrect.'
                elif len(new_pass) < 6:
                    error = 'Le nouveau mot de passe doit faire au moins 6 caractères.'
                elif new_pass != confirm_pass:
                    error = 'Les mots de passe ne correspondent pas.'
                else:
                    db.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                               (generate_password_hash(new_pass), session['user_id']))
                    db.commit()
                    message = 'Mot de passe modifié avec succès.'

            elif section == 'create_user' and session.get('role') == 'admin':
                username = request.form.get('new_username', '').strip()
                nom_complet = request.form.get('new_nom_complet', '').strip()
                role = request.form.get('new_role', 'user')
                password = request.form.get('new_password_user', '')

                if not username or not nom_complet or not password:
                    error = 'Tous les champs sont obligatoires.'
                elif len(password) < 6:
                    error = 'Le mot de passe doit faire au moins 6 caractères.'
                elif db.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
                    error = f'L\'utilisateur "{username}" existe déjà.'
                else:
                    db.execute('INSERT INTO users (username, password_hash, nom_complet, role, created_at) VALUES (?, ?, ?, ?, datetime("now","localtime"))',
                               (username, generate_password_hash(password), nom_complet, role))
                    db.commit()
                    message = f'Utilisateur "{username}" créé avec succès.'

            elif section == 'edit_user' and session.get('role') == 'admin':
                user_id = request.form.get('edit_user_id', '')
                username = request.form.get('edit_username', '').strip()
                nom_complet = request.form.get('edit_nom_complet', '').strip()
                role = request.form.get('edit_role', 'user')
                actif = 1 if request.form.get('edit_actif') else 0

                if user_id and nom_complet and username:
                    # Check username uniqueness if changed
                    existing = db.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id)).fetchone()
                    if existing:
                        error = f'Le nom d\'utilisateur "{username}" est déjà pris.'
                    else:
                        db.execute('UPDATE users SET username = ?, nom_complet = ?, role = ?, actif = ? WHERE id = ?',
                                   (username, nom_complet, role, actif, user_id))
                        db.commit()
                        message = 'Utilisateur mis à jour.'

            elif section == 'delete_user' and session.get('role') == 'admin':
                user_id = request.form.get('delete_user_id', '')
                if user_id and str(user_id) != str(session.get('user_id', '')):
                    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
                    db.commit()
                    message = 'Utilisateur supprimé.'
                elif str(user_id) == str(session.get('user_id', '')):
                    error = 'Vous ne pouvez pas supprimer votre propre compte.'

            elif section == 'reset_password' and session.get('role') == 'admin':
                user_id = request.form.get('reset_user_id', '')
                new_pass = request.form.get('reset_password', '')
                if user_id and new_pass and len(new_pass) >= 6:
                    db.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                               (generate_password_hash(new_pass), user_id))
                    db.commit()
                    message = 'Mot de passe réinitialisé.'
                else:
                    error = 'Mot de passe trop court ou utilisateur invalide.'

        # Get users list for admin section
        users = []
        if session.get('role') == 'admin':
            users = db.execute('SELECT id, username, nom_complet, role, actif, created_at FROM users ORDER BY username').fetchall()

        return render_template('parametres.html',
                               settings=settings,
                               users=users,
                               message=message,
                               error=error)
    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
