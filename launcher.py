#!/usr/bin/env python3
"""Lanceur Suivi Patient — double-clic pour démarrer l'application.

- Vérifie si le serveur tourne déjà sur le port 5000
- Si oui : ouvre simplement le navigateur
- Si non : démarre app.py en arrière-plan, attend qu'il soit prêt, ouvre le navigateur
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

PORT = 5000
URL = f"http://localhost:{PORT}"
PROJECT_DIR = Path(__file__).resolve().parent
APP_PY = PROJECT_DIR / "app.py"
PID_FILE = PROJECT_DIR / ".server.pid"


def server_responding(port: int) -> bool:
    """Vérifie si le port est ouvert et répond."""
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def find_pid_on_port(port: int) -> int | None:
    """Trouve le PID du processus qui écoute sur le port donné (Linux)."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            # Prendre le premier PID trouvé
            return int(result.stdout.strip().split("\n")[0])
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def start_server() -> int:
    """Démarre app.py en arrière-plan, retourne le PID."""
    proc = subprocess.Popen(
        [sys.executable, str(APP_PY)],
        cwd=str(PROJECT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Détache du processus parent
    )
    # Sauvegarder le PID
    PID_FILE.write_text(str(proc.pid))
    return proc.pid


def wait_for_server(port: int, timeout: int = 15) -> bool:
    """Attend que le serveur réponde, avec essais répétés."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server_responding(port):
            return True
        time.sleep(0.5)
    return False


def open_browser():
    """Ouvre le navigateur par défaut."""
    webbrowser.open(URL)


def stop_server():
    """Arrête le serveur proprement."""
    pid = find_pid_on_port(PORT)
    if pid:
        try:
            os.kill(pid, 15)  # SIGTERM
            time.sleep(1)
            # Vérifier s'il tourne encore
            try:
                os.kill(pid, 0)
                os.kill(pid, 9)  # SIGKILL si persiste
            except OSError:
                pass
        except OSError:
            pass
    # Nettoyer le fichier PID
    if PID_FILE.exists():
        PID_FILE.unlink()


def main():
    if server_responding(PORT):
        # Le serveur tourne déjà → ouvrir le navigateur
        open_browser()
        return

    # Le serveur ne tourne pas → le démarrer
    pid = start_server()
    print(f"⏳ Démarrage du serveur (PID {pid})...")

    if wait_for_server(PORT):
        print(f"✅ Serveur prêt sur {URL}")
        open_browser()
    else:
        print("❌ Le serveur n'a pas démarré à temps.")
        print("   Vérifiez qu'aucune autre application n'utilise le port 5000.")
        input("   Appuyez sur Entrée pour quitter...")

    # Garder la fenêtre ouverte quelques secondes
    time.sleep(1)


if __name__ == "__main__":
    main()
