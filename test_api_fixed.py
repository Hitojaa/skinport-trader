"""
Test rapide de l'API Skinport avec la vraie structure des données
"""

import asyncio
import os
from dotenv import load_dotenv
from skinport_collector import SkinportCollector, SignalEngine

load_dotenv()

async def test_api():
    """Test de l'API avec un seul item"""

    client_id = os.getenv('SKINPORT_CLIENT_ID')
    client_secret = os.getenv('SKINPORT_CLIENT_SECRET')

    async with SkinportCollector(client_id, client_secret) as collector:
        # 1. Récupère quelques items
        print("\n🔍 Récupération des items...")
        items = await collector.get_items()

        if not items:
            print("❌ Aucun item récupéré")
            return

        print(f"✅ {len(items)} items disponibles")

        # 2. Prend le premier item avec du stock
        test_item = None
        for item in items:
            if item.get('quantity', 0) > 5:
                test_item = item
                break

        if not test_item:
            print("❌ Aucun item avec stock suffisant")
            return

        item_name = test_item['market_hash_name']
        print(f"\n📦 Test avec: {item_name}")
        print(f"   Prix actuel: {test_item.get('min_price', 'N/A')}€")
        print(f"   Stock: {test_item.get('quantity', 0)}")

        # 3. Récupère l'historique
        print(f"\n📊 Récupération de l'historique...")
        history = await collector.get_sales_history(item_name)

        if not history:
            print("❌ Pas d'historique disponible")
            return

        print(f"✅ Historique récupéré !")
        print(f"\nStructure des données:")
        print(f"  Clés disponibles: {list(history.keys())}")

        # Affiche les stats
        for period in ['last_24_hours', 'last_7_days', 'last_30_days']:
            if period in history:
                stats = history[period]
                print(f"\n  {period}:")
                print(f"    Volume: {stats.get('volume', 0)} ventes")
                print(f"    Prix moyen: {stats.get('avg', 0):.2f}€")
                print(f"    Prix médian: {stats.get('median', 0):.2f}€")
                print(f"    Min: {stats.get('min', 0):.2f}€ | Max: {stats.get('max', 0):.2f}€")

        # 4. Test de détection de signal
        print(f"\n🎯 Détection de signal...")
        signal_engine = SignalEngine(
            z_threshold=-2.0,
            min_volume_24h=5,
            min_edge=3.0,
            max_spread=0.15
        )

        signal = signal_engine.detect_signals(test_item, history)

        if signal:
            print(f"\n🔔 SIGNAL DÉTECTÉ!")
            print(f"  Type: {signal.signal_type.value}")
            print(f"  Volume 24h: {signal.volume_24h}")
            print(f"  Edge: {signal.edge_net:.1f}%")
            print(f"  Confiance: {signal.confidence:.0f}%")
            print(f"  Raison: {signal.reason}")
        else:
            print(f"\n✅ Pas de signal (c'est normal, la plupart des items n'ont pas de signal)")

        print("\n✅ Test terminé avec succès!")

if __name__ == "__main__":
    asyncio.run(test_api())
