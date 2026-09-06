#!/usr/bin/env python3
"""Arrête le serveur Suivi Patient."""

import os
import sys
import subprocess
import socket
import time

PORT = 5000


def server_responding(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def find_pid_on_port(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def main():
    if not server_responding(PORT):
        print("ℹ️  Le serveur ne semble pas être en cours d'exécution.")
        input("   Appuyez sur Entrée pour quitter...")
        return

    pid = find_pid_on_port(PORT)
    if pid:
        print(f"🛑 Arrêt du serveur (PID {pid})...")
        try:
            os.kill(pid, 15)  # SIGTERM
            time.sleep(2)
            try:
                os.kill(pid, 0)
                os.kill(pid, 9)  # SIGKILL si persiste
                print("   (arrêt forcé)")
            except OSError:
                pass
        except OSError:
            print("   Le processus s'est déjà arrêté.")

    if not server_responding(PORT):
        print("✅ Serveur arrêté avec succès.")
    else:
        print("⚠️  Le serveur semble toujours en cours.")
        print("   Essayez de fermer la fenêtre du terminal manuellement.")

    time.sleep(2)


if __name__ == "__main__":
    main()
