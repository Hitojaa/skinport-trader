# config.py
"""
Configuration pour le tracker Skinport - UN SEUL SKIN
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SkinportConfig:
    """Configuration API Skinport"""
    client_id: str
    client_secret: str
    base_url: str = "https://api.skinport.com/v1"

@dataclass
class TrackerConfig:
    """Configuration du tracker"""
    # Nom exact du skin à surveiller (market_hash_name)
    skin_name: str

    # Intervalle entre chaque check (minutes)
    check_interval: int = 5

    # Seuils pour déclencher une alerte
    price_drop_threshold: float = 15.0  # % sous la médiane 7j
    min_edge_percent: float = 5.0  # % de profit minimum après frais

    # Frais Skinport
    skinport_fee: float = 0.12  # 12%

@dataclass
class AlertConfig:
    """Configuration des alertes"""
    discord_webhook_url: Optional[str] = None

    # Anti-spam : intervalle minimum entre 2 alertes (minutes)
    min_alert_interval: int = 30


class Config:
    """Configuration globale"""

    def __init__(self):
        # Skinport API
        self.skinport = SkinportConfig(
            client_id=os.getenv('SKINPORT_CLIENT_ID', ''),
            client_secret=os.getenv('SKINPORT_CLIENT_SECRET', '')
        )

        # Tracker - Skin à surveiller
        self.tracker = TrackerConfig(
            skin_name=os.getenv('SKIN_TO_TRACK', 'AK-47 | Redline (Field-Tested)'),
            check_interval=int(os.getenv('CHECK_INTERVAL_MINUTES', '5')),
            price_drop_threshold=float(os.getenv('PRICE_DROP_THRESHOLD', '15.0')),
            min_edge_percent=float(os.getenv('MIN_EDGE_PERCENT', '5.0'))
        )

        # Alertes
        self.alerts = AlertConfig(
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            min_alert_interval=int(os.getenv('MIN_ALERT_INTERVAL', '30'))
        )

    def validate(self) -> bool:
        """Vérifie la config"""
        errors = []

        if not self.skinport.client_id or not self.skinport.client_secret:
            errors.append("❌ SKINPORT_CLIENT_ID et SKINPORT_CLIENT_SECRET requis")

        if not self.tracker.skin_name:
            errors.append("❌ SKIN_TO_TRACK requis (nom du skin à surveiller)")

        if not self.alerts.discord_webhook_url:
            errors.append("❌ DISCORD_WEBHOOK_URL requis")

        if errors:
            print("\n🚨 ERREURS DE CONFIGURATION:")
            for error in errors:
                print(f"   {error}")
            return False

        print("✅ Configuration valide")
        return True

    def print_summary(self):
        """Affiche un résumé"""
        print("\n" + "="*60)
        print("🎯 SKINPORT TRACKER - UN SEUL SKIN")
        print("="*60)

        print(f"\n📡 SKINPORT API:")
        print(f"   Client ID: {'✅ Configuré' if self.skinport.client_id else '❌ Manquant'}")

        print(f"\n🎮 SKIN SURVEILLÉ:")
        print(f"   Nom: {self.tracker.skin_name}")
        print(f"   Check toutes les: {self.tracker.check_interval} min")

        print(f"\n📊 SEUILS D'ALERTE:")
        print(f"   Baisse de prix: {self.tracker.price_drop_threshold}%")
        print(f"   Edge minimum: {self.tracker.min_edge_percent}%")

        print(f"\n🔔 ALERTES:")
        print(f"   Discord: {'✅ Configuré' if self.alerts.discord_webhook_url else '❌ Non configuré'}")

        print("\n" + "="*60 + "\n")
