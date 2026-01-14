"""
SKINPORT TRADING BOT - Main
Système de trading automatisé pour skins CS2

Lance avec: python main.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
import sys
import os

# Fix encodage Windows pour emojis et caractères spéciaux
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.system('chcp 65001 >nul 2>&1')

# Imports des modules du projet
# (assure-toi d'avoir tous les fichiers dans le même dossier)
from config import Config
from database import DatabaseManager, Item, PriceTick, Signal
from skinport_collector import SkinportCollector, SignalEngine
from alerts import AlertManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skinport_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Bot principal de trading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config.database.connection_string)
        self.running = False
        
        # Statistiques
        self.stats = {
            'signals_detected': 0,
            'alerts_sent': 0,
            'trades_executed': 0,
            'profit_net': 0.0,
            'last_reset': datetime.now()
        }
    
    async def initialize(self):
        """Initialise le bot"""
        logger.info("="*60)
        logger.info("INITIALISATION DU BOT")
        logger.info("="*60)
        
        # Crée les tables si nécessaire
        self.db.create_tables()
        logger.info("✅ Base de données initialisée")
        
        # Test connexion Skinport
        async with SkinportCollector(
            client_id=self.config.skinport.client_id,
            client_secret=self.config.skinport.client_secret
        ) as collector:
            items = await collector.get_items()
            if items:
                logger.info(f"✅ API Skinport OK ({len(items)} items disponibles)")
            else:
                logger.warning("⚠️  Impossible de récupérer les items au démarrage (rate limit?)")
                logger.info("Le bot va continuer et réessayer lors du premier scan...")
                # Ne pas échouer l'initialisation, juste un warning
        
        # Test alertes
        async with AlertManager(
            discord_webhook=self.config.alerts.discord_webhook_url,
            telegram_bot_token=self.config.alerts.telegram_bot_token,
            telegram_chat_id=self.config.alerts.telegram_chat_id
        ) as alert_mgr:
            await alert_mgr.send_startup_message()
            logger.info("✅ Système d'alertes initialisé")
        
        return True
    
    async def collect_and_analyze(self):
        """Collecte les données et analyse les signaux"""
        session = self.db.get_session()
        
        try:
            # Init collecteur et analyseur
            async with SkinportCollector(
                client_id=self.config.skinport.client_id,
                client_secret=self.config.skinport.client_secret
            ) as collector:
                
                signal_engine = SignalEngine(
                    z_threshold=self.config.trading.z_score_threshold,
                    min_volume_24h=self.config.trading.min_volume_24h,
                    min_edge=self.config.trading.min_edge_net,
                    max_spread=self.config.trading.max_spread
                )
                
                # 1. Récupère les items disponibles
                logger.info("🔍 Récupération des items...")
                all_items = await collector.get_items()
                
                if not all_items:
                    logger.error("Aucun item récupéré")
                    return
                
                # 2. Filtre selon config
                filtered_items = []
                for item in all_items:
                    # Prix max
                    if item.get('min_price', 999) > self.config.trading.max_item_price:
                        continue
                    
                    # Quantité min
                    if item.get('quantity', 0) < self.config.collector.min_item_quantity:
                        continue
                    
                    # Catégories
                    if self.config.collector.target_categories:
                        # TODO: filtrer par catégorie si API le permet
                        pass
                    
                    filtered_items.append(item)

                    if len(filtered_items) >= self.config.collector.max_items_per_scan:
                        break

                logger.info(f"📊 {len(filtered_items)} items sélectionnés pour analyse")

                if len(filtered_items) > 0:
                    estimated_time = len(filtered_items) * self.config.collector.rate_limit_delay / 60
                    logger.info(f"⏱️  Temps estimé: {estimated_time:.1f} minutes (rate limit: {self.config.collector.rate_limit_delay}s/item)")
                
                # 3. Analyse chaque item
                signals_detected = []
                
                for idx, item_data in enumerate(filtered_items, 1):
                    try:
                        item_name = item_data.get('market_hash_name')
                        if not item_name:
                            logger.warning(f"[{idx}/{len(filtered_items)}] Item sans nom - ignoré")
                            continue

                        logger.info(f"[{idx}/{len(filtered_items)}] Analyse: {item_name}")
                        
                        # Ajoute/màj l'item en DB
                        item = self.db.add_item(
                            session,
                            market_hash_name=item_name,
                            category=item_data.get('category'),
                            type=item_data.get('type'),
                            rarity=item_data.get('rarity')
                        )
                        
                        # Ajoute tick de prix actuel
                        current_price = item_data.get('min_price')
                        if current_price:
                            self.db.add_price_tick(
                                session,
                                item_id=item.id,
                                price=current_price,
                                quantity=item_data.get('quantity'),
                                timestamp=datetime.utcnow()
                            )
                        
                        # Récupère historique (statistiques agrégées)
                        history = await collector.get_sales_history(item_name, days=7)

                        if not history:
                            logger.debug(f"  ⚠️  Pas d'historique disponible pour {item_name}")
                            continue

                        # Log des stats disponibles
                        stats_24h = history.get("last_24_hours", {})
                        logger.debug(f"  📊 Stats 24h: vol={stats_24h.get('volume', 0)}, "
                                   f"avg={stats_24h.get('avg', 0):.2f}€, "
                                   f"median={stats_24h.get('median', 0):.2f}€")

                        # Sauvegarde les stats agrégées en DB (optionnel)
                        # On sauvegarde juste le prix actuel et les stats principales
                        if stats_24h:
                            self.db.add_price_tick(
                                session,
                                item_id=item.id,
                                price=stats_24h.get('median', current_price),
                                volume=stats_24h.get('volume', 0),
                                timestamp=datetime.utcnow()
                            )
                            logger.debug(f"  💾 Stats sauvegardées en DB")

                        # Détecte signaux
                        signal = signal_engine.detect_signals(item_data, history)
                        
                        if signal and signal.signal_type != 'TRAP':
                            # Sauvegarde en DB
                            signal_data = {
                                'item_id': item.id,
                                'signal_type': signal.signal_type.value,
                                'z_score': signal.z_score,
                                'volume_24h': signal.volume_24h,
                                'edge_net': signal.edge_net,
                                'spread': signal.spread,
                                'confidence': signal.confidence,
                                'reason': signal.reason,
                                'timestamp': signal.timestamp
                            }
                            db_signal = self.db.add_signal(session, signal_data)
                            
                            # Ajoute l'item au signal pour l'alerte
                            signal.item = item
                            signal.id = db_signal.id
                            
                            signals_detected.append(signal)
                            self.stats['signals_detected'] += 1
                            
                            logger.info(f"  ✅ Signal {signal.signal_type.value}: "
                                      f"z={signal.z_score:.2f}, "
                                      f"edge={signal.edge_net:.1f}%")
                        
                        # Pause pour rate limit
                        await asyncio.sleep(2)
                    
                    except Exception as e:
                        logger.error(f"Erreur analyse {item_data.get('market_hash_name', 'unknown')}: {e}")
                        logger.debug(f"Détails de l'erreur:", exc_info=True)
                        # Continue avec l'item suivant
                        continue
                
                # 4. Envoie les alertes
                if signals_detected:
                    logger.info(f"\n🔔 {len(signals_detected)} signaux à alerter")
                    
                    async with AlertManager(
                        discord_webhook=self.config.alerts.discord_webhook_url,
                        telegram_bot_token=self.config.alerts.telegram_bot_token,
                        telegram_chat_id=self.config.alerts.telegram_chat_id,
                        min_alert_interval_minutes=self.config.alerts.min_alert_interval_minutes
                    ) as alert_mgr:
                        
                        for signal in signals_detected:
                            try:
                                success = await alert_mgr.send_signal(signal)
                                if success:
                                    self.stats['alerts_sent'] += 1
                                    self.db.mark_signal_alerted(session, signal.id)
                                
                                await asyncio.sleep(1)
                            except Exception as e:
                                logger.error(f"Erreur envoi alerte: {e}")
                
                else:
                    logger.info("Aucun signal détecté")
        
        except Exception as e:
            logger.error(f"❌ Erreur dans collect_and_analyze: {e}", exc_info=True)
        
        finally:
            session.close()
    
    async def send_daily_summary(self):
        """Envoie le résumé quotidien"""
        async with AlertManager(
            discord_webhook=self.config.alerts.discord_webhook_url,
            telegram_bot_token=self.config.alerts.telegram_bot_token,
            telegram_chat_id=self.config.alerts.telegram_chat_id
        ) as alert_mgr:
            await alert_mgr.send_daily_summary(self.stats)
        
        # Reset stats
        self.stats = {
            'signals_detected': 0,
            'alerts_sent': 0,
            'trades_executed': 0,
            'profit_net': 0.0,
            'last_reset': datetime.now()
        }
    
    async def run_loop(self):
        """Boucle principale"""
        self.running = True
        last_scan = datetime.now() - timedelta(hours=1)
        last_daily_summary = datetime.now()
        
        logger.info("\n" + "="*60)
        logger.info("🚀 BOT DÉMARRÉ - MODE 24/7")
        logger.info("="*60 + "\n")
        
        while self.running:
            try:
                now = datetime.now()
                
                # Scan complet toutes les X minutes
                time_since_scan = (now - last_scan).total_seconds() / 60
                scan_interval = self.config.collector.full_scan_interval_minutes
                
                if time_since_scan >= scan_interval:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"NOUVEAU SCAN - {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"{'='*60}\n")
                    
                    await self.collect_and_analyze()
                    last_scan = now
                    
                    logger.info(f"\n📊 Stats session:")
                    logger.info(f"   Signaux détectés: {self.stats['signals_detected']}")
                    logger.info(f"   Alertes envoyées: {self.stats['alerts_sent']}")
                
                # Résumé quotidien (à minuit)
                if now.date() > last_daily_summary.date():
                    await self.send_daily_summary()
                    last_daily_summary = now
                
                # Attente avant prochain cycle
                await asyncio.sleep(60)  # Vérifie toutes les minutes

            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {e}", exc_info=True)
                logger.info("⏭️  Le bot va continuer malgré l'erreur...")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Arrête le bot proprement"""
        logger.info("Arrêt du bot...")
        self.running = False


async def main():
    """Point d'entrée principal"""
    
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          SKINPORT CS2 TRADING BOT v1.0                   ║
║                                                          ║
║  Bot de trading automatisé pour skins Counter-Strike 2  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Charge la configuration
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Variables d'environnement chargées depuis .env")
    except ImportError:
        logger.warning("⚠️  python-dotenv non installé, utilise les variables d'environnement système")
    
    config = Config()
    config.print_summary()
    
    # Valide la config
    if not config.validate():
        logger.error("\n❌ Configuration invalide - Arrêt du bot")
        return
    
    # Crée et lance le bot
    bot = TradingBot(config)
    
    if not await bot.initialize():
        logger.error("❌ Échec de l'initialisation")
        return
    
    # Lance la boucle principale
    try:
        await bot.run_loop()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Interruption par l'utilisateur")
    finally:
        await bot.stop()
        logger.info("✅ Bot arrêté proprement\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")