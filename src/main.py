"""
SKINPORT TRACKER - Surveillance d'UN skin
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.system('chcp 65001 >nul 2>&1')

from config import Config
from skinport_tracker import SkinportTracker
from alerts import DiscordAlert

# Configuration du logging
os.makedirs('data', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/skinport_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TrackerBot:
    """Bot de surveillance d'un skin"""

    def __init__(self, config: Config):
        self.config = config
        self.running = False

    async def run(self):
        """Boucle principale"""
        self.running = True

        print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          SKINPORT TRACKER - UN SEUL SKIN                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """)

        self.config.print_summary()

        # Validation
        if not self.config.validate():
            logger.error("❌ Configuration invalide")
            return

        skin_name = self.config.tracker.skin_name
        check_interval = self.config.tracker.check_interval

        logger.info(f"🚀 Démarrage du tracker pour: {skin_name}")
        logger.info(f"⏱️  Check toutes les {check_interval} minutes\n")

        # Initialisation
        async with SkinportTracker(
            client_id=self.config.skinport.client_id,
            client_secret=self.config.skinport.client_secret
        ) as tracker:

            async with DiscordAlert(
                webhook_url=self.config.alerts.discord_webhook_url,
                min_interval_minutes=self.config.alerts.min_alert_interval
            ) as discord:

                # Message de démarrage
                await discord.send_startup_message(skin_name)

                # Boucle principale
                while self.running:
                    try:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"🔄 CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"{'='*60}")

                        # Vérification du skin
                        alert = await tracker.check_skin(
                            skin_name=skin_name,
                            drop_threshold=self.config.tracker.price_drop_threshold,
                            min_edge=self.config.tracker.min_edge_percent,
                            skinport_fee=self.config.tracker.skinport_fee
                        )

                        # Envoi d'alerte si opportunité détectée
                        if alert:
                            logger.info(f"\n🔔 OPPORTUNITÉ DÉTECTÉE !")
                            await discord.send_price_alert(alert)

                        # Attente avant prochain check
                        logger.info(f"\n⏸️  Pause de {check_interval} minutes...")
                        await asyncio.sleep(check_interval * 60)

                    except Exception as e:
                        logger.error(f"❌ Erreur: {e}", exc_info=True)
                        logger.info("⏭️  Le bot continue malgré l'erreur...")
                        await asyncio.sleep(60)

    def stop(self):
        """Arrête le bot"""
        logger.info("\n⏹️  Arrêt du bot...")
        self.running = False


async def main():
    """Point d'entrée"""

    # Chargement config
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Variables d'environnement chargées")
    except ImportError:
        logger.warning("⚠️  python-dotenv non installé")

    config = Config()

    # Lancement du bot
    bot = TrackerBot(config)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Interruption par l'utilisateur")
    finally:
        bot.stop()
        logger.info("✅ Bot arrêté proprement\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
