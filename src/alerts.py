"""
Système d'alertes pour Discord et Telegram
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Envoie des alertes sur Discord via webhook"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _build_embed(self, signal) -> Dict:
        """Construit un embed Discord riche"""
        
        # Couleur selon le type de signal
        colors = {
            'UNDERPRICED': 0x00ff00,  # Vert
            'MOMENTUM': 0xff9900,      # Orange
            'REVERSAL': 0x00ffff,      # Cyan
            'TRAP': 0xff0000           # Rouge
        }
        color = colors.get(signal.signal_type, 0x808080)
        
        # Emojis
        emoji_map = {
            'UNDERPRICED': '🔻',
            'MOMENTUM': '📈',
            'REVERSAL': '🔁',
            'TRAP': '⚠️'
        }
        emoji = emoji_map.get(signal.signal_type, '📊')
        
        # Constructioon de l'embed
        embed = {
            "title": f"{emoji} {signal.signal_type}",
            "description": f"**{signal.item_name}**",
            "color": color,
            "fields": [
                {
                    "name": "📊 Z-Score",
                    "value": f"`{signal.z_score:.2f}`",
                    "inline": True
                },
                {
                    "name": "📦 Volume 24h",
                    "value": f"`{signal.volume_24h}`",
                    "inline": True
                },
                {
                    "name": "💰 Edge Net",
                    "value": f"`{signal.edge_net:+.1f}%`",
                    "inline": True
                },
                {
                    "name": "📏 Spread",
                    "value": f"`{signal.spread:.1%}`",
                    "inline": True
                },
                {
                    "name": "🎯 Confiance",
                    "value": f"`{signal.confidence:.0f}%`",
                    "inline": True
                },
                {
                    "name": "⏰ Timestamp",
                    "value": f"`{signal.timestamp.strftime('%H:%M:%S')}`",
                    "inline": True
                }
            ],
            "footer": {
                "text": signal.reason
            },
            "timestamp": signal.timestamp.isoformat()
        }
        
        return embed
    
    async def send_signal(self, signal) -> bool:
        """Envoie un signal sur Discord"""
        try:
            embed = self._build_embed(signal)
            
            payload = {
                "username": "Skinport Trader Bot",
                "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
                "embeds": [embed]
            }
            
            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Alerte Discord envoyée: {signal.signal_type}")
                    return True
                else:
                    logger.error(f"❌ Erreur Discord: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ Exception Discord: {e}")
            return False
    
    async def send_message(self, title: str, message: str, color: int = 0x3498db):
        """Envoie un message simple"""
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "username": "Skinport Trader Bot",
                "embeds": [embed]
            }
            
            async with self.session.post(self.webhook_url, json=payload) as response:
                return response.status == 204
        
        except Exception as e:
            logger.error(f"❌ Exception Discord: {e}")
            return False


class TelegramNotifier:
    """Envoie des alertes sur Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _format_signal_message(self, signal) -> str:
        """Formate le message pour Telegram (Markdown)"""
        
        emoji_map = {
            'UNDERPRICED': '🔻',
            'MOMENTUM': '📈',
            'REVERSAL': '🔁',
            'TRAP': '⚠️'
        }
        emoji = emoji_map.get(signal.signal_type, '📊')
        
        message = f"""
{emoji} *{signal.signal_type}*
━━━━━━━━━━━━━━━━━━

📦 *Item:* `{signal.item_name}`

📊 *Z-score:* `{signal.z_score:.2f}`
📈 *Volume 24h:* `{signal.volume_24h}`
💰 *Edge net:* `{signal.edge_net:+.1f}%`
📏 *Spread:* `{signal.spread:.1%}`
🎯 *Confiance:* `{signal.confidence:.0f}%`

💡 _{signal.reason}_

⏰ {signal.timestamp.strftime('%H:%M:%S')}
"""
        return message.strip()
    
    async def send_signal(self, signal) -> bool:
        """Envoie un signal sur Telegram"""
        try:
            message = self._format_signal_message(signal)
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"✅ Alerte Telegram envoyée: {signal.signal_type}")
                    return True
                else:
                    data = await response.json()
                    logger.error(f"❌ Erreur Telegram: {data}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ Exception Telegram: {e}")
            return False
    
    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Envoie un message simple"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            async with self.session.post(url, json=payload) as response:
                return response.status == 200
        
        except Exception as e:
            logger.error(f"❌ Exception Telegram: {e}")
            return False


class AlertManager:
    """Gestionnaire d'alertes unifié avec anti-spam"""
    
    def __init__(self, discord_webhook: Optional[str] = None,
                 telegram_bot_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None,
                 min_alert_interval_minutes: int = 30):
        
        self.discord = None
        self.telegram = None
        self.min_alert_interval = timedelta(minutes=min_alert_interval_minutes)
        
        # Anti-spam: stocke les dernières alertes par item
        self.last_alerts: Dict[str, datetime] = {}
        
        # Initialise les notifiers si configurés
        if discord_webhook:
            self.discord = DiscordNotifier(discord_webhook)
        
        if telegram_bot_token and telegram_chat_id:
            self.telegram = TelegramNotifier(telegram_bot_token, telegram_chat_id)
    
    async def __aenter__(self):
        if self.discord:
            await self.discord.__aenter__()
        if self.telegram:
            await self.telegram.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        if self.discord:
            await self.discord.__aexit__(*args)
        if self.telegram:
            await self.telegram.__aexit__(*args)
    
    def should_send_alert(self, signal) -> bool:
        """Vérifie si l'alerte doit être envoyée (anti-spam)"""
        key = f"{signal.item_name}_{signal.signal_type}"
        now = datetime.utcnow()
        
        if key in self.last_alerts:
            elapsed = now - self.last_alerts[key]
            if elapsed < self.min_alert_interval:
                logger.info(f"⏸️  Anti-spam: alerte ignorée pour {signal.item_name} "
                          f"(dernière: {elapsed.seconds//60}min)")
                return False
        
        self.last_alerts[key] = now
        return True
    
    async def send_signal(self, signal) -> bool:
        """Envoie un signal sur tous les canaux configurés"""
        
        # Ignore les TRAPs
        if signal.signal_type == 'TRAP':
            logger.debug(f"Trap signal ignoré: {signal.item_name}")
            return False
        
        # Anti-spam
        if not self.should_send_alert(signal):
            return False
        
        success = False
        
        # Envoi Discord
        if self.discord:
            try:
                result = await self.discord.send_signal(signal)
                success = success or result
            except Exception as e:
                logger.error(f"Erreur Discord: {e}")
        
        # Envoi Telegram
        if self.telegram:
            try:
                result = await self.telegram.send_signal(signal)
                success = success or result
            except Exception as e:
                logger.error(f"Erreur Telegram: {e}")
        
        return success
    
    async def send_startup_message(self):
        """Envoie un message au démarrage du bot"""
        message = f"""
🤖 *Skinport Trader Bot*

✅ Bot démarré avec succès
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Le bot surveille maintenant le marché et vous alertera des opportunités de trading.
"""
        
        if self.discord:
            await self.discord.send_message("🚀 Bot démarré", message, color=0x00ff00)
        
        if self.telegram:
            await self.telegram.send_message(message)
    
    async def send_error_alert(self, error_message: str):
        """Envoie une alerte d'erreur"""
        message = f"""
🚨 *ERREUR SYSTÈME*

{error_message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        
        if self.discord:
            await self.discord.send_message("❌ Erreur", message, color=0xff0000)
        
        if self.telegram:
            await self.telegram.send_message(message)
    
    async def send_daily_summary(self, stats: Dict):
        """Envoie un résumé quotidien"""
        message = f"""
📊 *Résumé quotidien*

🔍 Signaux détectés: {stats.get('signals_detected', 0)}
✅ Alertes envoyées: {stats.get('alerts_sent', 0)}
💰 Trades exécutés: {stats.get('trades_executed', 0)}
📈 Profit net: {stats.get('profit_net', 0):.2f}€

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        
        if self.discord:
            await self.discord.send_message("📊 Résumé", message, color=0x3498db)
        
        if self.telegram:
            await self.telegram.send_message(message)


# ================== TEST UNITAIRE ==================

async def test_alerts():
    """Test des alertes"""
    from dataclasses import dataclass
    from datetime import datetime
    
    # Simule un signal
    @dataclass
    class FakeSignal:
        timestamp: datetime
        item_name: str
        signal_type: str
        z_score: float
        volume_24h: int
        edge_net: float
        spread: float
        reason: str
        confidence: float
    
    signal = FakeSignal(
        timestamp=datetime.now(),
        item_name="AK-47 | Redline (Field-Tested)",
        signal_type="UNDERPRICED",
        z_score=-2.3,
        volume_24h=15,
        edge_net=4.5,
        spread=0.08,
        reason="Prix 2.3 écarts-types sous moyenne, volume OK",
        confidence=85.0
    )
    
    # Configure avec tes webhooks
    discord_url = "TON_WEBHOOK_DISCORD_ICI"
    telegram_token = "TON_TOKEN_TELEGRAM_ICI"
    telegram_chat = "TON_CHAT_ID_ICI"
    
    async with AlertManager(
        discord_webhook=discord_url if discord_url != "TON_WEBHOOK_DISCORD_ICI" else None,
        telegram_bot_token=telegram_token if telegram_token != "TON_TOKEN_TELEGRAM_ICI" else None,
        telegram_chat_id=telegram_chat if telegram_chat != "TON_CHAT_ID_ICI" else None
    ) as alert_manager:
        
        print("\n🧪 Test d'envoi d'alerte...")
        
        if alert_manager.discord or alert_manager.telegram:
            await alert_manager.send_startup_message()
            await asyncio.sleep(2)
            
            success = await alert_manager.send_signal(signal)
            print(f"{'✅' if success else '❌'} Alerte envoyée: {success}")
        else:
            print("⚠️  Aucun webhook configuré - Configure tes webhooks pour tester")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_alerts())