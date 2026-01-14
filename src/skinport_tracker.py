"""
Tracker Skinport simplifié - Surveille UN SEUL skin
"""

import aiohttp
import asyncio
import base64
import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceAlert:
    """Alerte de prix"""
    skin_name: str
    current_price: float
    median_7d: float
    drop_percent: float
    edge_percent: float
    volume_24h: int
    reason: str
    timestamp: datetime


class SkinportTracker:
    """Tracker simple pour un seul skin"""

    BASE_URL = "https://api.skinport.com/v1"
    RATE_LIMIT_DELAY = 45.0  # Secondes entre requêtes

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = None
        self.last_request_time = None

    def _get_auth_header(self) -> Dict:
        """Génère le header d'auth"""
        headers = {"Accept-Encoding": "br"}

        if self.client_id and self.client_secret:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    async def __aenter__(self):
        headers = self._get_auth_header()
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _rate_limit_wait(self):
        """Respect du rate limit"""
        now = datetime.now()
        if self.last_request_time:
            elapsed = (now - self.last_request_time).total_seconds()
            if elapsed < self.RATE_LIMIT_DELAY:
                wait_time = self.RATE_LIMIT_DELAY - elapsed
                logger.debug(f"⏳ Rate limit: attente {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self.last_request_time = now

    async def get_item_price(self, skin_name: str) -> Optional[float]:
        """Récupère le prix actuel d'un skin"""
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/items"
        params = {"app_id": 730, "currency": "EUR"}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    items = await response.json()

                    # Cherche le skin
                    for item in items:
                        if item.get('market_hash_name') == skin_name:
                            return item.get('min_price')

                    logger.warning(f"❌ Skin '{skin_name}' non trouvé")
                    return None

                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 300))
                    logger.warning(f"⚠️  Rate limit 429 - Tu as dépassé le quota API!")
                    logger.warning(f"⏳ Attente de {retry_after}s avant de réessayer...")
                    logger.info(f"💡 Astuce: Attends 5 minutes entre chaque test pour éviter le rate limit")
                    await asyncio.sleep(retry_after)
                    return None

                else:
                    logger.error(f"❌ Erreur API {response.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return None

    async def get_sales_history(self, skin_name: str) -> Optional[Dict]:
        """Récupère l'historique des ventes (stats agrégées)"""
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/sales/history"
        params = {"market_hash_name": skin_name, "currency": "EUR"}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # L'API retourne une liste avec un élément
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                    elif isinstance(data, dict):
                        return data

                    return None

                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"⚠️  Rate limit 429 - Attente {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return None

                else:
                    logger.warning(f"⚠️  Erreur {response.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return None

    def analyze_price(
        self,
        skin_name: str,
        current_price: float,
        history: Dict,
        drop_threshold: float = 15.0,
        min_edge: float = 5.0,
        skinport_fee: float = 0.12
    ) -> Optional[PriceAlert]:
        """Analyse le prix et détecte une opportunité"""

        if not history:
            return None

        # Stats 7 jours
        stats_7d = history.get("last_7_days", {})
        stats_24h = history.get("last_24_hours", {})

        median_7d = stats_7d.get("median")
        volume_24h = stats_24h.get("volume", 0)

        if not median_7d or median_7d == 0:
            logger.debug("Pas de médiane 7j disponible")
            return None

        # Calcul de la baisse en %
        drop_percent = ((median_7d - current_price) / median_7d) * 100

        # Si le prix est au-dessus de la médiane, pas d'alerte
        if drop_percent < 0:
            logger.debug(f"Prix au-dessus de la médiane ({drop_percent:.1f}%)")
            return None

        # Calcul de l'edge net (profit après frais)
        # On achète à current_price, on revend à median_7d
        gross_profit = median_7d - current_price
        fees = median_7d * skinport_fee
        net_profit = gross_profit - fees
        edge_percent = (net_profit / current_price) * 100

        # Vérification des seuils
        if drop_percent >= drop_threshold and edge_percent >= min_edge:
            return PriceAlert(
                skin_name=skin_name,
                current_price=current_price,
                median_7d=median_7d,
                drop_percent=drop_percent,
                edge_percent=edge_percent,
                volume_24h=volume_24h,
                reason=f"Prix {drop_percent:.1f}% sous médiane 7j, edge net {edge_percent:.1f}%",
                timestamp=datetime.now()
            )

        logger.debug(f"Pas d'opportunité: drop={drop_percent:.1f}%, edge={edge_percent:.1f}%")
        return None

    async def check_skin(
        self,
        skin_name: str,
        drop_threshold: float = 15.0,
        min_edge: float = 5.0,
        skinport_fee: float = 0.12
    ) -> Optional[PriceAlert]:
        """Check complet d'un skin"""

        logger.info(f"🔍 Vérification: {skin_name}")

        # 1. Prix actuel
        current_price = await self.get_item_price(skin_name)
        if not current_price:
            logger.error(f"❌ Impossible de récupérer le prix")
            return None

        logger.info(f"   💰 Prix actuel: {current_price:.2f}€")

        # 2. Historique
        history = await self.get_sales_history(skin_name)
        if not history:
            logger.error(f"❌ Impossible de récupérer l'historique")
            return None

        stats_7d = history.get("last_7_days", {})
        stats_24h = history.get("last_24_hours", {})

        logger.info(f"   📊 Médiane 7j: {stats_7d.get('median', 0):.2f}€")
        logger.info(f"   📈 Volume 24h: {stats_24h.get('volume', 0)} ventes")

        # 3. Analyse
        alert = self.analyze_price(
            skin_name, current_price, history,
            drop_threshold, min_edge, skinport_fee
        )

        if alert:
            logger.info(f"   🔔 ALERTE: {alert.reason}")
        else:
            logger.info(f"   ✅ Pas d'opportunité pour le moment")

        return alert
