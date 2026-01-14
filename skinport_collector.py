"""
Skinport CS2 Skin Trading System
Architecture modulaire pour analyse et alertes de trading
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import base64

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    UNDERPRICED = "UNDERPRICED"
    MOMENTUM = "MOMENTUM"
    REVERSAL = "REVERSAL"
    TRAP = "TRAP"

@dataclass
class TradingSignal:
    timestamp: datetime
    item_name: str
    signal_type: SignalType
    z_score: float
    volume_24h: int
    edge_net: float
    spread: float
    reason: str
    confidence: float
    item: Optional[object] = None  # Référence à l'objet Item de la DB
    id: Optional[int] = None  # ID du signal en DB

class SkinportCollector:
    """Collecteur de données Skinport avec respect des rate limits"""

    BASE_URL = "https://api.skinport.com/v1"
    RATE_LIMIT_DELAY = 45.0  # 8 req / 5min = 37.5s, on prend 45s pour sécurité
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = None
        self.last_request_time = {}
    
    def _get_auth_header(self) -> Dict:
        """Génère le header d'authentification"""
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
    
    async def _rate_limit_wait(self, endpoint: str):
        """Respect des rate limits"""
        now = datetime.now()
        if endpoint in self.last_request_time:
            elapsed = (now - self.last_request_time[endpoint]).total_seconds()
            if elapsed < self.RATE_LIMIT_DELAY:
                wait_time = self.RATE_LIMIT_DELAY - elapsed
                logger.info(f"Rate limit: attente {wait_time:.1f}s pour {endpoint}")
                await asyncio.sleep(wait_time)
        
        self.last_request_time[endpoint] = now
    
    async def get_items(self, app_id: int = 730) -> List[Dict]:
        """Récupère la liste des items disponibles"""
        endpoint = "/items"
        await self._rate_limit_wait(endpoint)

        url = f"{self.BASE_URL}{endpoint}"
        params = {"app_id": app_id, "currency": "EUR"}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ {len(data)} items récupérés")
                    return data
                elif response.status == 429:
                    logger.warning("⚠️  Rate limit atteint - Attente de 60s avant retry")
                    await asyncio.sleep(60)
                    # Retry une fois après le rate limit
                    async with self.session.get(url, params=params) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            logger.info(f"✅ {len(data)} items récupérés (après retry)")
                            return data
                        else:
                            logger.error(f"❌ Échec après retry: {retry_response.status}")
                            return []
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Erreur {response.status}: {error_text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"❌ Exception lors de la requête: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    async def get_sales_history(self, market_hash_name: str, days: int = 7) -> List[Dict]:
        """Récupère l'historique des ventes (rate limit: 8 req / 5min)"""
        endpoint = "/sales/history"
        await self._rate_limit_wait(endpoint)

        url = f"{self.BASE_URL}{endpoint}"
        params = {
            "market_hash_name": market_hash_name,
            "currency": "EUR"
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 429:
                    # Rate limit - attendre plus longtemps
                    retry_after = int(response.headers.get('Retry-After', 120))
                    logger.warning(f"⚠️  Rate limit 429 pour {market_hash_name} - Attente {retry_after}s")
                    await asyncio.sleep(retry_after)
                    # Ne pas retry ici, on retourne vide et on passera au prochain scan
                    return []
                else:
                    logger.warning(f"Erreur {response.status} pour {market_hash_name}")
                    return []
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return []


class SignalEngine:
    """Moteur de calcul des signaux de trading"""
    
    def __init__(self, 
                 z_threshold: float = -2.0,
                 min_volume_24h: int = 5,
                 min_edge: float = 3.0,
                 max_spread: float = 0.15):
        self.z_threshold = z_threshold
        self.min_volume_24h = min_volume_24h
        self.min_edge = min_edge
        self.max_spread = max_spread
    
    def calculate_z_score(self, current_price: float, prices: List[float]) -> float:
        """Calcule le z-score (écart par rapport à la moyenne)"""
        if len(prices) < 2:
            return 0.0
        
        mean = np.mean(prices)
        std = np.std(prices)
        
        if std == 0:
            return 0.0
        
        return (current_price - mean) / std
    
    def calculate_momentum(self, prices: List[float], timestamps: List[datetime]) -> Dict:
        """Calcule le momentum sur différentes périodes"""
        if len(prices) < 2:
            return {"1h": 0, "6h": 0, "24h": 0}
        
        df = pd.DataFrame({"price": prices, "time": timestamps})
        df = df.sort_values("time")
        
        now = timestamps[-1]
        price_now = prices[-1]
        
        momentum = {}
        for hours, label in [(1, "1h"), (6, "6h"), (24, "24h")]:
            cutoff = now - timedelta(hours=hours)
            old_prices = df[df["time"] <= cutoff]["price"]
            
            if len(old_prices) > 0:
                old_price = old_prices.iloc[-1]
                momentum[label] = ((price_now - old_price) / old_price) * 100
            else:
                momentum[label] = 0
        
        return momentum
    
    def calculate_edge(self, buy_price: float, sell_price: float, 
                      skinport_fee: float = 0.12, slippage: float = 0.01) -> float:
        """Calcule l'edge net après frais"""
        gross_profit = sell_price - buy_price
        fees = sell_price * skinport_fee
        slippage_cost = sell_price * slippage
        
        net_profit = gross_profit - fees - slippage_cost
        return (net_profit / buy_price) * 100
    
    def detect_signals(self, item_data: Dict, history: List[Dict]) -> Optional[TradingSignal]:
        """Détecte les signaux de trading"""
        
        if len(history) < 10:
            return None
        
        # Prépare les données
        prices = [sale["price"] for sale in history]
        timestamps = [datetime.fromtimestamp(sale["sold_at"]) for sale in history]
        current_price = item_data.get("min_price", prices[-1])
        
        # Volume 24h
        now = datetime.now()
        volume_24h = len([s for s in history if datetime.fromtimestamp(s["sold_at"]) > now - timedelta(hours=24)])
        
        if volume_24h < self.min_volume_24h:
            return TradingSignal(
                timestamp=now,
                item_name=item_data["market_hash_name"],
                signal_type=SignalType.TRAP,
                z_score=0,
                volume_24h=volume_24h,
                edge_net=0,
                spread=0,
                reason=f"Volume insuffisant ({volume_24h} ventes/24h)",
                confidence=0.0
            )
        
        # Calculs
        z_score = self.calculate_z_score(current_price, prices)
        momentum = self.calculate_momentum(prices, timestamps)
        
        # Estimation spread (simplifié)
        spread = 0.05  # À affiner avec bid/ask réels si disponibles
        
        # Edge potentiel (prix cible = moyenne mobile)
        target_price = np.mean(prices)
        edge = self.calculate_edge(current_price, target_price)
        
        # Détection signaux
        
        # Signal UNDERPRICED
        if (z_score < self.z_threshold and 
            volume_24h >= self.min_volume_24h and 
            edge > self.min_edge and 
            spread < self.max_spread):
            
            return TradingSignal(
                timestamp=now,
                item_name=item_data["market_hash_name"],
                signal_type=SignalType.UNDERPRICED,
                z_score=z_score,
                volume_24h=volume_24h,
                edge_net=edge,
                spread=spread,
                reason=f"Prix {abs(z_score):.1f} écarts-types sous moyenne, edge net {edge:.1f}%",
                confidence=min(abs(z_score) / 3 * 100, 95)
            )
        
        # Signal MOMENTUM
        if (momentum["24h"] > 10 and 
            momentum["6h"] > momentum["24h"] * 0.5 and
            volume_24h >= self.min_volume_24h * 1.5):
            
            return TradingSignal(
                timestamp=now,
                item_name=item_data["market_hash_name"],
                signal_type=SignalType.MOMENTUM,
                z_score=z_score,
                volume_24h=volume_24h,
                edge_net=edge,
                spread=spread,
                reason=f"Momentum +{momentum['24h']:.1f}% sur 24h, volume élevé",
                confidence=75
            )
        
        return None


class AlertManager:
    """Gestionnaire d'alertes (à connecter à Discord/Telegram)"""
    
    def __init__(self):
        self.sent_alerts = set()  # Anti-spam
    
    def should_send(self, signal: TradingSignal) -> bool:
        """Vérifie si l'alerte doit être envoyée (anti-spam)"""
        key = f"{signal.item_name}_{signal.signal_type.value}_{signal.timestamp.date()}"
        
        if key in self.sent_alerts:
            return False
        
        self.sent_alerts.add(key)
        return True
    
    def format_alert(self, signal: TradingSignal) -> str:
        """Formate une alerte pour affichage"""
        return f"""
{signal.signal_type.value}
━━━━━━━━━━━━━━━━━━
📦 Item: {signal.item_name}
📊 Z-score: {signal.z_score:.2f}
📈 Volume 24h: {signal.volume_24h}
💰 Edge net: {signal.edge_net:+.1f}%
📏 Spread: {signal.spread:.1%}
🎯 Confiance: {signal.confidence:.0f}%

💡 {signal.reason}
⏰ {signal.timestamp.strftime('%H:%M:%S')}
"""
    
    async def send_alert(self, signal: TradingSignal):
        """Envoie une alerte (à implémenter avec Discord/Telegram webhook)"""
        if not self.should_send(signal):
            return
        
        alert_text = self.format_alert(signal)
        logger.info(f"\n{'='*50}\nNOUVELLE ALERTE:\n{alert_text}\n{'='*50}")
        
        # TODO: Implémenter webhook Discord/Telegram
        # await self.send_discord(alert_text)
        # await self.send_telegram(alert_text)


async def main():
    """Fonction principale - exemple d'utilisation"""
    
    # Initialisation
    collector = SkinportCollector(
        client_id="17503a57a1c746ba9f18e2e857f22de7",  # Remplace par ton vrai client_id
        client_secret="86b2jFBmbYuvSA5fguOMYzOwdhkWRowfaX0vYamZ9CeoVWf0x6afCfjXACD0aFKtn8IAMipfcats9wwIEBX1KA=="  # Remplace par ton vrai client_secret
    )
    signal_engine = SignalEngine(
        z_threshold=-2.2,
        min_volume_24h=5,
        min_edge=3.0,
        max_spread=0.15
    )
    alert_manager = AlertManager()
    
    async with collector:
        # 1. Récupère liste items
        items = await collector.get_items()
        
        if not items:
            logger.error("Aucun item récupéré")
            return
        
        # 2. Filtre les items populaires (commence petit)
        popular_items = [
            item for item in items 
            if item.get("quantity", 0) > 10  # Items avec stock > 10
        ][:50]  # Limite à 50 items pour test
        
        logger.info(f"🎯 Analyse de {len(popular_items)} items populaires")
        
        # 3. Analyse chaque item
        for idx, item in enumerate(popular_items, 1):
            logger.info(f"[{idx}/{len(popular_items)}] Analyse: {item['market_hash_name']}")
            
            # Récupère historique
            history = await collector.get_sales_history(item["market_hash_name"])
            
            if not history:
                continue
            
            # Détecte signaux
            signal = signal_engine.detect_signals(item, history)
            
            if signal and signal.signal_type != SignalType.TRAP:
                await alert_manager.send_alert(signal)
            
            # Pause pour respecter rate limits
            await asyncio.sleep(2)
        
        logger.info("✅ Analyse terminée")


if __name__ == "__main__":
    asyncio.run(main())