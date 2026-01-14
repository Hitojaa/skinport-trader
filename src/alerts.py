"""
Alertes Discord simplifiées
"""

import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class DiscordAlert:
    """Gestion des alertes Discord"""

    def __init__(self, webhook_url: str, min_interval_minutes: int = 30):
        self.webhook_url = webhook_url
        self.min_interval = min_interval_minutes
        self.last_alert_time = None
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def should_send_alert(self) -> bool:
        """Vérifie si on peut envoyer une alerte (anti-spam)"""
        if not self.last_alert_time:
            return True

        elapsed = datetime.now() - self.last_alert_time
        return elapsed >= timedelta(minutes=self.min_interval)

    async def send_price_alert(self, alert) -> bool:
        """Envoie une alerte de prix sur Discord"""

        if not self.should_send_alert():
            minutes_left = self.min_interval - (datetime.now() - self.last_alert_time).total_seconds() / 60
            logger.info(f"⏸️  Anti-spam: prochaine alerte dans {minutes_left:.0f} min")
            return False

        try:
            # Construction de l'embed Discord
            embed = {
                "title": "🔔 OPPORTUNITÉ DÉTECTÉE !",
                "description": f"**{alert.skin_name}**",
                "color": 0x00ff00,  # Vert
                "fields": [
                    {
                        "name": "💰 Prix actuel",
                        "value": f"`{alert.current_price:.2f}€`",
                        "inline": True
                    },
                    {
                        "name": "📊 Médiane 7j",
                        "value": f"`{alert.median_7d:.2f}€`",
                        "inline": True
                    },
                    {
                        "name": "📉 Baisse",
                        "value": f"`-{alert.drop_percent:.1f}%`",
                        "inline": True
                    },
                    {
                        "name": "💵 Profit net estimé",
                        "value": f"`+{alert.edge_percent:.1f}%`",
                        "inline": True
                    },
                    {
                        "name": "📈 Volume 24h",
                        "value": f"`{alert.volume_24h} ventes`",
                        "inline": True
                    },
                    {
                        "name": "⏰ Heure",
                        "value": f"`{alert.timestamp.strftime('%H:%M:%S')}`",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": alert.reason
                },
                "timestamp": alert.timestamp.isoformat()
            }

            payload = {
                "embeds": [embed],
                "username": "Skinport Tracker"
            }

            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info("[OK] Alerte Discord envoyée !")
                    self.last_alert_time = datetime.now()
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Erreur Discord {response.status}: {error_text[:200]}")
                    return False

        except Exception as e:
            logger.error(f"❌ Exception envoi Discord: {e}")
            return False

    async def send_startup_message(self, skin_name: str) -> bool:
        """Envoie un message de démarrage"""
        try:
            payload = {
                "content": f"✅ **Tracker démarré** - Surveillance de: `{skin_name}`",
                "username": "Skinport Tracker"
            }

            async with self.session.post(self.webhook_url, json=payload) as response:
                return response.status == 204

        except Exception as e:
            logger.error(f"❌ Erreur message démarrage: {e}")
            return False
