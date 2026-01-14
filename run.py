#!/usr/bin/env python3
"""
Script de lancement du bot Skinport Trader
"""

import sys
import os

# Ajoute le dossier src au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import et lance le bot
from main import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot arrêté par l'utilisateur")
