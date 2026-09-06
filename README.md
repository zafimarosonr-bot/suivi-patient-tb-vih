# 🏥 Suivi Patient TB & VIH

Application web de suivi patient pour l'**infirmerie de la Maison Centrale de Mahajanga** (DRAP BOENY, Madagascar).

> Remplace deux fichiers HTML autonomes par une application unifiée Flask + SQLite, 100% locale.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/Licence-MIT-green)

---

## 📋 Fonctionnalités

### Gestion des patients
- **Dashboard** avec cartes cliquables et alertes contrôles TB en retard
- **Liste patients** avec recherche, filtres combinables (statut, programme, âge, sexe, quartier, décision TB) et pagination
- **Fiche patient détaillée** avec timeline TB (M0/M2/M5/M6), badges colorés, historique des statuts
- **Création multi-étapes** (wizard 5 étapes) avec validation

### Suivi médical
- **Tuberculose** : poids, contrôles bactériologiques (M2/M5/M5/M6), dates auto-calculées, décision finale
- **VIH** : code auto-généré (DDMMYY + initiales), date début de suivi
- **Changement de statut** : libération, transfert, décès avec formulaires contextuels

### Rapports & Export
- **Rapport mensuel dynamique** avec statistiques TB/VIH, répartition démographique
- **Export PDF** avec en-tête officiel (Maison Centrale, DRAP BOENY, DHDPRS/SSPD)
- **Export CSV** (compatible Excel) et **JSON** complet
- **Import JSON** pour restauration de données

### Sécurité & Confidentialité
- **Authentification** avec 3 rôles : admin, user, lecture seule
- **Noms VIH masqués** par défaut (flou), révélation par mot de passe
- **Journal d'audit** traçant toutes les modifications
- **Mode sombre** avec toggle instantané

### Déploiement
- **100% local** — aucune dépendance internet requise
- **Launcher Linux** — double-clic pour démarrer
- **Interface Apple-style** — design épuré, responsive

---

## 🚀 Démarrage rapide

### Prérequis
- Python 3.8+
- Aucune dépendance système supplémentaire

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/zafimarosonr-bot/suivi-patient-tb-vih.git
cd suivi-patient-tb-vih

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base de données
python3 init_db.py

# Lancer l'application
python3 app.py
```

Ouvrir **http://localhost:5000** dans le navigateur.

### Connexion par défaut

| Utilisateur | Mot de passe | Rôle |
|------------|-------------|------|
| `admin` | `admin123` | Administrateur (accès complet) |
| `visiteur` | `visiteur123` | Lecture seule |

---

## 🖥️ Utilisation sur Linux (double-clic)

Pour les utilisateurs non techniques (infirmiers) :

1. Copier les raccourcis `.desktop` sur le Bureau
2. **Double-cliquez** sur « Suivi Patient » pour démarrer
3. Le navigateur s'ouvre automatiquement
4. Pour arrêter : double-cliquez sur « Arrêter Suivi Patient »

---

## 📁 Structure du projet

```
├── app.py                    # Application Flask (routes)
├── schema.sql                # Schéma SQLite (7 tables)
├── seed_data.sql             # Données de démonstration
├── init_db.py                # Initialisation de la base
├── requirements.txt          # Dépendances Python
├── launcher.py               # Lanceur Linux (double-clic)
├── stop_server.py            # Arrêt du serveur
├── Suivi Patient.desktop     # Raccourci Bureau (lancement)
├── Arrêter Suivi Patient.desktop  # Raccourci Bureau (arrêt)
├── LISEZ-MOI.txt             # Instructions simples
├── suivi_patient.png         # Icône de l'application
│
├── templates/
│   ├── base.html             # Layout + CSS complet + dark mode
│   ├── login.html            # Page de connexion
│   ├── dashboard.html        # Tableau de bord
│   ├── patients.html         # Liste patients + wizard création
│   ├── patient_detail.html   # Fiche patient détaillée
│   ├── rapports.html         # Rapports mensuels
│   ├── sauvegarde.html       # Export/Import
│   ├── audit.html            # Journal d'audit
│   ├── aide.html             # Guide d'utilisation (11 sections)
│   ├── patient_print.html    # Fiche patient imprimable
│   └── patients_print.html   # Liste patients imprimable
│
├── migrate_*.py              # Scripts de migration
└── NOTE_DE_SESSION.md        # Documentation interne
```

---

## 🗄️ Base de données

| Table | Description |
|-------|-------------|
| `patients` | Dossier unique (identité, statut, contact) |
| `historique_statut` | Journal des changements de statut |
| `suivi_tb` | Volet tuberculose (poids, contrôles, décision) |
| `suivi_vih` | Volet VIH (code, date début, observation) |
| `journal_audit` | Piste d'audit complète |
| `users` | Utilisateurs (authentification) |
| `settings` | Paramètres de l'application |

---

## 🎨 Design

- **Style** : Apple-inspired (frosted glass, bordures subtiles, coins arrondis)
- **Palette** : Bleu primary (#007AFF), Violet VIH (#AF52DE), Teal (#30B0C7)
- **Mode sombre** : toggle dans le menu profil
- **Responsive** : adapté desktop et tablette
- **Font** : Inter (OFL, embeddée en base64)
- **Icônes** : SVG inline (style outline, 100% offline)

---

## 🔧 Technologies

| Composant | Technologie |
|-----------|-------------|
| Backend | Flask 3.0+ (Python) |
| Base de données | SQLite 3 |
| Frontend | Jinja2 + vanilla JS |
| Authentification | Sessions Flask + werkzeug.security |
| Design | CSS custom (variables) + SVG inline |
| Déploiement | 100% local, aucune dépendance CDN |

---

## 📄 Licence

MIT — Utilisation libre pour l'infirmerie de la Maison Centrale de Mahajanga.

---

## 👥 Contributeurs

- **Infirmerie** — Maison Centrale de Mahajanga
- **DRAP BOENY** — Direction Régionale de l'Administration Pénitentiaire
- **DHDPRS/SSPD** — Destinataire des rapports

---

<p align="center">
  <i>Application développée pour améliorer le suivi des patients TB et VIH en milieu carcéral à Madagascar.</i>
</p>
