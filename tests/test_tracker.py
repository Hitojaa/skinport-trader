"""
Test rapide du tracker Skinport
"""

import asyncio
import os
import sys

# Ajoute src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
from config import Config
from skinport_tracker import SkinportTracker

load_dotenv()


async def test_tracker():
    """Test du tracker avec le skin configuré"""

    print("\n🧪 TEST DU TRACKER SKINPORT\n")

    # Charge la config
    config = Config()
    config.print_summary()

    if not config.validate():
        print("❌ Configuration invalide")
        return

    skin_name = config.tracker.skin_name
    print(f"📦 Test avec: {skin_name}\n")

    # Test du tracker
    async with SkinportTracker(
        client_id=config.skinport.client_id,
        client_secret=config.skinport.client_secret
    ) as tracker:

        # Check du skin
        alert = await tracker.check_skin(
            skin_name=skin_name,
            drop_threshold=config.tracker.price_drop_threshold,
            min_edge=config.tracker.min_edge_percent,
            skinport_fee=config.tracker.skinport_fee
        )

        if alert:
            print(f"\n🔔 OPPORTUNITÉ DÉTECTÉE !")
            print(f"   Prix: {alert.current_price:.2f}€")
            print(f"   Médiane 7j: {alert.median_7d:.2f}€")
            print(f"   Baisse: -{alert.drop_percent:.1f}%")
            print(f"   Profit: +{alert.edge_percent:.1f}%")
            print(f"   Volume 24h: {alert.volume_24h}")
        else:
            print(f"\n✅ Pas d'opportunité pour le moment")
            print(f"   C'est normal, réessaye plus tard ou change de skin")

        print(f"\n✅ Test terminé avec succès!")


if __name__ == "__main__":
    asyncio.run(test_tracker())
