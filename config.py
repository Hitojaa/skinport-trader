# config.py
"""
Configuration centralisée pour le système de trading Skinport
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
    
    def get_auth_header(self) -> str:
        """Génère le header d'authentification Base64"""
        import base64
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

@dataclass
class DatabaseConfig:
    """Configuration base de données"""
    # Pour dev local : SQLite
    connection_string: str = "sqlite:///skinport_trading.db"
    
    # Pour prod : PostgreSQL
    # connection_string: str = "postgresql://user:password@localhost:5432/skinport_trading"
    
    echo_sql: bool = False  # Affiche les requêtes SQL (debug)

@dataclass
class TradingConfig:
    """Paramètres de trading"""
    # Seuils pour signaux
    z_score_threshold: float = -2.2
    min_volume_24h: int = 5
    min_edge_net: float = 3.0  # % minimum de profit net
    max_spread: float = 0.15  # 15% max
    
    # Frais Skinport
    skinport_fee: float = 0.12  # 12% de frais
    slippage: float = 0.01  # 1% de slippage estimé
    
    # Limites de sécurité
    max_item_price: float = 100.0  # Prix max d'un item (€)
    max_daily_trades: int = 10
    max_position_size: float = 200.0  # Montant max investi total (€)

@dataclass
class AlertConfig:
    """Configuration des alertes"""
    # Discord
    discord_webhook_url: Optional[str] = None
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Email (optionnel)
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    email_password: Optional[str] = None
    
    # Anti-spam
    min_alert_interval_minutes: int = 30  # Max 1 alerte/30min par item

@dataclass
class CollectorConfig:
    """Configuration du collecteur de données"""
    # Rate limits - TRÈS IMPORTANT pour éviter ban API
    rate_limit_delay: float = 45.0  # secondes entre requêtes (8 req / 5min = 37.5s, on prend 45s pour marge)

    # Items à suivre par scan
    target_categories: list = None  # ['weapon', 'sticker'] ou None pour tous
    max_items_per_scan: int = 10  # RÉDUIT: seulement 10 items par scan pour respecter rate limit
    min_item_quantity: int = 5  # Stock minimum pour suivre un item

    # Intervalles de collecte
    full_scan_interval_minutes: int = 60  # Scan complet toutes les heures
    price_update_interval_minutes: int = 10  # Màj prix tous les 10min
    
    def __post_init__(self):
        if self.target_categories is None:
            self.target_categories = ['weapon']  # Par défaut: armes uniquement


class Config:
    """Configuration globale - charge depuis variables d'environnement"""
    
    def __init__(self):
        # Skinport API
        self.skinport = SkinportConfig(
            client_id=os.getenv('SKINPORT_CLIENT_ID', ''),
            client_secret=os.getenv('SKINPORT_CLIENT_SECRET', '')
        )
        
        # Database
        self.database = DatabaseConfig(
            connection_string=os.getenv('DATABASE_URL', 'sqlite:///skinport_trading.db'),
            echo_sql=os.getenv('DB_ECHO', 'false').lower() == 'true'
        )
        
        # Trading
        self.trading = TradingConfig(
            z_score_threshold=float(os.getenv('Z_SCORE_THRESHOLD', '-2.2')),
            min_volume_24h=int(os.getenv('MIN_VOLUME_24H', '5')),
            min_edge_net=float(os.getenv('MIN_EDGE_NET', '3.0')),
            max_item_price=float(os.getenv('MAX_ITEM_PRICE', '100.0'))
        )
        
        # Alerts
        self.alerts = AlertConfig(
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID')
        )
        
        # Collector
        self.collector = CollectorConfig(
            max_items_per_scan=int(os.getenv('MAX_ITEMS_PER_SCAN', '10')),
            rate_limit_delay=float(os.getenv('RATE_LIMIT_DELAY', '45.0')),
            full_scan_interval_minutes=int(os.getenv('SCAN_INTERVAL', '60'))
        )
    
    def validate(self) -> bool:
        """Vérifie que la config est valide"""
        errors = []
        
        if not self.skinport.client_id or not self.skinport.client_secret:
            errors.append("❌ SKINPORT_CLIENT_ID et SKINPORT_CLIENT_SECRET requis")
        
        if not self.alerts.discord_webhook_url and not self.alerts.telegram_bot_token:
            errors.append("⚠️  Aucun système d'alerte configuré (Discord ou Telegram)")
        
        if self.trading.max_item_price < 10:
            errors.append("⚠️  MAX_ITEM_PRICE très bas, risque de manquer des opportunités")
        
        if errors:
            print("\n🚨 ERREURS DE CONFIGURATION:")
            for error in errors:
                print(f"   {error}")
            return False
        
        print("✅ Configuration valide")
        return True
    
    def print_summary(self):
        """Affiche un résumé de la configuration"""
        print("\n" + "="*60)
        print("CONFIGURATION DU SYSTÈME")
        print("="*60)
        
        print(f"\n📡 SKINPORT API:")
        print(f"   Client ID: {'✅ Configuré' if self.skinport.client_id else '❌ Manquant'}")
        print(f"   Client Secret: {'✅ Configuré' if self.skinport.client_secret else '❌ Manquant'}")
        
        print(f"\n💾 BASE DE DONNÉES:")
        print(f"   Connection: {self.database.connection_string}")
        
        print(f"\n📊 PARAMÈTRES DE TRADING:")
        print(f"   Z-score seuil: {self.trading.z_score_threshold}")
        print(f"   Volume min 24h: {self.trading.min_volume_24h}")
        print(f"   Edge net min: {self.trading.min_edge_net}%")
        print(f"   Prix max item: {self.trading.max_item_price}€")
        print(f"   Position max: {self.trading.max_position_size}€")
        
        print(f"\n🔔 ALERTES:")
        print(f"   Discord: {'✅ Configuré' if self.alerts.discord_webhook_url else '❌ Non configuré'}")
        print(f"   Telegram: {'✅ Configuré' if self.alerts.telegram_bot_token else '❌ Non configuré'}")
        
        print(f"\n🔄 COLLECTEUR:")
        print(f"   Items/scan: {self.collector.max_items_per_scan}")
        print(f"   Délai rate limit: {self.collector.rate_limit_delay}s")
        print(f"   Scan complet: {self.collector.full_scan_interval_minutes} min")
        print(f"   Màj prix: {self.collector.price_update_interval_minutes} min")
        
        print("\n" + "="*60 + "\n")


# Exemple de fichier .env à créer
ENV_TEMPLATE = """
# ============================================
# CONFIGURATION SKINPORT TRADER
# Copie ce fichier en .env et remplis tes valeurs
# ============================================

# === SKINPORT API (REQUIS) ===
# Obtenir sur: https://skinport.com/settings
SKINPORT_CLIENT_ID=ton_client_id_ici
SKINPORT_CLIENT_SECRET=ton_client_secret_ici

# === BASE DE DONNÉES ===
# SQLite (par défaut, pour dev local)
DATABASE_URL=sqlite:///skinport_trading.db

# PostgreSQL (pour prod)
# DATABASE_URL=postgresql://user:password@localhost:5432/skinport_trading

# === PARAMÈTRES DE TRADING ===
Z_SCORE_THRESHOLD=-2.2
MIN_VOLUME_24H=5
MIN_EDGE_NET=3.0
MAX_ITEM_PRICE=100.0
MAX_POSITION_SIZE=200.0

# === ALERTES DISCORD ===
# Créer un webhook: Paramètres serveur > Intégrations > Webhooks
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# === ALERTES TELEGRAM (optionnel) ===
# Créer un bot: @BotFather sur Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# === COLLECTEUR ===
MAX_ITEMS=200
SCAN_INTERVAL=60
"""

if __name__ == "__main__":
    # Crée un fichier .env.example
    with open('.env.example', 'w') as f:
        f.write(ENV_TEMPLATE.strip())
    print("✅ Fichier .env.example créé")
    print("📝 Copie-le en .env et remplis tes valeurs\n")
    
    # Test de la config
    config = Config()
    config.print_summary()
    config.validate()