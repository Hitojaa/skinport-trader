"""
Tests sans appels API - utilise des donnees mockees
Lance avec: python test_no_api.py
"""
import asyncio
import sys
from datetime import datetime, timedelta

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

async def test_config():
    """Test 1: Configuration"""
    print_section("TEST 1: Configuration")

    try:
        from config import Config
        config = Config()
        config.print_summary()

        if config.validate():
            print("OK - Configuration valide")
            return True
        else:
            print("ERREUR - Configuration invalide")
            return False
    except Exception as e:
        print(f"ERREUR: {e}")
        return False

async def test_database():
    """Test 2: Base de donnees"""
    print_section("TEST 2: Base de donnees")

    try:
        from database import DatabaseManager
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        print("OK - Tables creees")

        session = db.get_session()
        item = db.add_item(
            session,
            market_hash_name="AK-47 | Redline (Field-Tested)",
            category="weapon",
            type="rifle"
        )
        print(f"OK - Item ajoute: {item.market_hash_name}")

        tick = db.add_price_tick(session, item.id, 30.5, volume=10)
        print(f"OK - Prix ajoute: {tick.price} EUR")

        signal_data = {
            'item_id': item.id,
            'signal_type': 'UNDERPRICED',
            'z_score': -2.3,
            'volume_24h': 15,
            'edge_net': 4.5,
            'spread': 0.08,
            'confidence': 85.0,
            'reason': 'Test signal'
        }
        signal = db.add_signal(session, signal_data)
        print(f"OK - Signal ajoute: {signal.signal_type}")

        session.close()
        print("OK - Base de donnees OK")
        return True
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_signal_engine():
    """Test 3: Moteur de signaux"""
    print_section("TEST 3: Moteur de signaux")

    try:
        from skinport_collector import SignalEngine

        engine = SignalEngine(
            z_threshold=-2.0,
            min_volume_24h=5,
            min_edge=3.0
        )
        print("OK - Signal engine initialise")

        prices = [30.0, 31.0, 29.5, 30.5, 28.0, 27.5, 26.0]
        z_score = engine.calculate_z_score(26.0, prices)
        print(f"OK - Z-score calcule: {z_score:.2f}")

        now = datetime.utcnow()
        timestamps = [now - timedelta(hours=i) for i in range(len(prices))]
        momentum = engine.calculate_momentum(prices, timestamps)
        print(f"OK - Momentum: 1h={momentum['1h']:.1f}%, 24h={momentum['24h']:.1f}%")

        edge = engine.calculate_edge(26.0, 30.0)
        print(f"OK - Edge net: {edge:.1f}%")

        print("OK - Signal engine OK")
        return True
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mock_pipeline():
    """Test 4: Pipeline complet avec donnees mockees"""
    print_section("TEST 4: Pipeline complet (donnees mockees)")

    try:
        from database import DatabaseManager
        from skinport_collector import SignalEngine, SignalType
        from datetime import datetime
        import time

        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        session = db.get_session()

        # Donnees mockees d'un item
        mock_item_data = {
            'market_hash_name': 'AK-47 | Redline (Field-Tested)',
            'min_price': 26.50,
            'quantity': 50,
            'category': 'weapon',
            'type': 'rifle',
            'rarity': 'classified'
        }

        # Historique mocke (prix en baisse)
        now = datetime.now()
        mock_history = []
        for i in range(30):
            mock_history.append({
                'price': 30.0 - (i * 0.2),  # Prix qui baisse
                'sold_at': (now - timedelta(hours=i)).timestamp()
            })

        print("1. Donnees mockees preparees")

        # Ajoute l'item en DB
        item = db.add_item(
            session,
            market_hash_name=mock_item_data['market_hash_name'],
            category=mock_item_data.get('category'),
            type=mock_item_data.get('type'),
            rarity=mock_item_data.get('rarity')
        )
        print(f"2. Item en DB: {item.market_hash_name}")

        # Ajoute les prix en DB
        for sale in mock_history[-20:]:
            db.add_price_tick(
                session,
                item_id=item.id,
                price=sale['price'],
                volume=1,
                timestamp=datetime.fromtimestamp(sale['sold_at'])
            )
        print("3. Historique ajoute en DB (20 ventes)")

        # Analyse avec le signal engine
        signal_engine = SignalEngine()
        signal = signal_engine.detect_signals(mock_item_data, mock_history)

        if signal:
            print(f"4. Signal detecte: {signal.signal_type.value}")
            print(f"   Z-score: {signal.z_score:.2f}")
            print(f"   Volume 24h: {signal.volume_24h}")
            print(f"   Edge net: {signal.edge_net:.1f}%")
            print(f"   Confiance: {signal.confidence:.0f}%")

            if signal.signal_type != SignalType.TRAP:
                signal_data = {
                    'item_id': item.id,
                    'signal_type': signal.signal_type.value,
                    'z_score': signal.z_score,
                    'volume_24h': signal.volume_24h,
                    'edge_net': signal.edge_net,
                    'spread': signal.spread,
                    'confidence': signal.confidence,
                    'reason': signal.reason
                }
                db_signal = db.add_signal(session, signal_data)
                print(f"5. Signal sauvegarde en DB (id={db_signal.id})")
        else:
            print("4. Aucun signal detecte pour ces donnees")

        session.close()
        print("\nOK - Pipeline complet OK avec donnees mockees")
        return True

    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("""
==============================================================
        TESTS SANS APPELS API (DONNEES MOCKEES)
==============================================================
""")

    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("OK - .env charge\n")
    except ImportError:
        print("WARNING - python-dotenv non installe\n")

    results = {}

    tests = [
        ("Configuration", test_config),
        ("Base de donnees", test_database),
        ("Signal Engine", test_signal_engine),
        ("Pipeline complet (mock)", test_mock_pipeline)
    ]

    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except KeyboardInterrupt:
            print("\nTests interrompus")
            break
        except Exception as e:
            print(f"\nERREUR inattendue dans {name}: {e}")
            results[name] = False

    print_section("RESUME DES TESTS")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for name, result in results.items():
        status = "OK  " if result else "FAIL"
        print(f"{status}  {name}")

    print(f"\n{'='*60}")
    print(f"Resultat: {passed}/{total} tests reussis")

    if passed == total:
        print("\nTous les tests sont OK (sauf API - rate limited)")
        print("Attendre 56 minutes avant de tester l'API")
    else:
        print("\nCertains tests ont echoue")

    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTests arretes")
