#!/usr/bin/env python3
"""
Script de lancement du bot Skinport Trader
"""

import sys
import os
import asyncio

# Ajoute le dossier src au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Import du module main
    from main import main as run_bot

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot arrêté par l'utilisateur")
