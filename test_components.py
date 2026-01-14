"""
Script de test pour chaque composant du bot
Lance avec: python test_components.py
"""

import asyncio
import sys
from datetime import datetime, timedelta

def print_section(title):
    """Affiche un titre de section"""
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
            print("✅ Configuration OK")
            return True
        else:
            print("❌ Configuration invalide")
            return False
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

async def test_database():
    """Test 2: Base de données"""
    print_section("TEST 2: Base de données")
    
    try:
        from database import DatabaseManager
        from datetime import datetime
        
        # Utilise SQLite en mémoire pour test
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        print("✅ Tables créées")
        
        # Test ajout item
        session = db.get_session()
        item = db.add_item(
            session,
            market_hash_name="AK-47 | Redline (Field-Tested)",
            category="weapon",
            type="rifle"
        )
        print(f"✅ Item ajouté: {item.market_hash_name}")
        
        # Test ajout prix
        tick = db.add_price_tick(session, item.id, 30.5, volume=10)
        print(f"✅ Prix ajouté: {tick.price}€")
        
        # Test ajout signal
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
        print(f"✅ Signal ajouté: {signal.signal_type}")
        
        session.close()
        print("✅ Base de données OK")
        return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_skinport_api():
    """Test 3: API Skinport"""
    print_section("TEST 3: API Skinport")
    
    try:
        from config import Config
        from skinport_collector import SkinportCollector
        
        config = Config()
        
        if not config.skinport.client_id or not config.skinport.client_secret:
            print("❌ Client ID ou Secret manquant dans .env")
            print("   Configure SKINPORT_CLIENT_ID et SKINPORT_CLIENT_SECRET")
            return False
        
        async with SkinportCollector(
            client_id=config.skinport.client_id,
            client_secret=config.skinport.client_secret
        ) as collector:
            
            print("📡 Test récupération items...")
            items = await collector.get_items()
            
            if items:
                print(f"✅ {len(items)} items récupérés")
                print(f"   Exemple: {items[0].get('market_hash_name')}")
                
                # Test historique
                print("\n📡 Test historique ventes...")
                history = await collector.get_sales_history(
                    items[0]['market_hash_name'],
                    days=7
                )
                
                if history:
                    print(f"✅ {len(history)} ventes historiques")
                    print(f"   Prix moyen: {sum(s['price'] for s in history) / len(history):.2f}€")
                else:
                    print("⚠️  Pas d'historique disponible")
                
                print("✅ API Skinport OK")
                return True
            else:
                print("❌ Aucun item récupéré")
                return False
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_signal_engine():
    """Test 4: Moteur de signaux"""
    print_section("TEST 4: Moteur de signaux")
    
    try:
        from skinport_collector import SignalEngine
        
        engine = SignalEngine(
            z_threshold=-2.0,
            min_volume_24h=5,
            min_edge=3.0
        )
        print("✅ Signal engine initialisé")
        
        # Simule des données
        prices = [30.0, 31.0, 29.5, 30.5, 28.0, 27.5, 26.0]  # Prix en baisse
        
        z_score = engine.calculate_z_score(26.0, prices)
        print(f"✅ Z-score calculé: {z_score:.2f}")
        
        # Simule des timestamps
        now = datetime.utcnow()
        timestamps = [now - timedelta(hours=i) for i in range(len(prices))]
        
        momentum = engine.calculate_momentum(prices, timestamps)
        print(f"✅ Momentum: 1h={momentum['1h']:.1f}%, 24h={momentum['24h']:.1f}%")
        
        edge = engine.calculate_edge(26.0, 30.0)
        print(f"✅ Edge net: {edge:.1f}%")
        
        print("✅ Signal engine OK")
        return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_alerts():
    """Test 5: Système d'alertes"""
    print_section("TEST 5: Système d'alertes")
    
    try:
        from config import Config
        from alerts import AlertManager
        from dataclasses import dataclass
        from skinport_collector import SignalType
        
        config = Config()
        
        if not config.alerts.discord_webhook_url and not config.alerts.telegram_bot_token:
            print("⚠️  Aucun webhook configuré")
            print("   Configure DISCORD_WEBHOOK_URL ou TELEGRAM_BOT_TOKEN dans .env")
            return False
        
        # Crée un signal de test
        @dataclass
        class FakeItem:
            market_hash_name: str = "AK-47 | Redline (Field-Tested)"
        
        @dataclass
        class FakeSignal:
            timestamp: datetime
            item_name: str
            signal_type: SignalType
            z_score: float
            volume_24h: int
            edge_net: float
            spread: float
            reason: str
            confidence: float
            item: FakeItem
            id: int
        
        signal = FakeSignal(
            timestamp=datetime.now(),
            item_name="AK-47 | Redline (Field-Tested)",
            signal_type=SignalType.UNDERPRICED,
            z_score=-2.3,
            volume_24h=15,
            edge_net=4.5,
            spread=0.08,
            reason="Test d'alerte - ignore ce message",
            confidence=85.0,
            item=FakeItem(),
            id=1
        )
        
        async with AlertManager(
            discord_webhook=config.alerts.discord_webhook_url,
            telegram_bot_token=config.alerts.telegram_bot_token,
            telegram_chat_id=config.alerts.telegram_chat_id
        ) as alert_mgr:
            
            print("📤 Envoi message de test...")
            if alert_mgr.discord:
                await alert_mgr.discord.send_message(
                    "🧪 Test du système",
                    "Ceci est un message de test. Si tu le reçois, les alertes fonctionnent !",
                    color=0x00ff00
                )
            
            if alert_mgr.telegram:
                await alert_mgr.telegram.send_message(
                    "🧪 *Test du système*\n\nCeci est un message de test. Si tu le reçois, les alertes fonctionnent !"
                )
            
            print("✅ Check Discord/Telegram pour voir le message")
            print("✅ Système d'alertes OK")
            return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_pipeline():
    """Test 6: Pipeline complet"""
    print_section("TEST 6: Pipeline complet (simulation)")
    
    try:
        from config import Config
        from database import DatabaseManager
        from skinport_collector import SkinportCollector, SignalEngine
        
        config = Config()
        
        if not config.skinport.client_id or not config.skinport.client_secret:
            print("❌ API Skinport non configurée")
            return False
        
        # DB en mémoire pour test
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        session = db.get_session()
        
        print("🔄 Simulation pipeline complet...")
        
        async with SkinportCollector(
            client_id=config.skinport.client_id,
            client_secret=config.skinport.client_secret
        ) as collector:
            
            # 1. Récupère items
            items = await collector.get_items()
            print(f"  1. ✅ {len(items)} items récupérés")

            if not items:
                print("  ❌ Impossible de récupérer les items (rate limit?)")
                session.close()
                return False

            # 2. Prend le premier item
            test_item = items[0]
            item = db.add_item(
                session,
                market_hash_name=test_item['market_hash_name']
            )
            print(f"  2. ✅ Item en DB: {item.market_hash_name}")
            
            # 3. Récupère historique
            history = await collector.get_sales_history(test_item['market_hash_name'])
            print(f"  3. ✅ Historique: {len(history)} ventes")
            
            # 4. Analyse signal
            signal_engine = SignalEngine()
            signal = signal_engine.detect_signals(test_item, history)
            
            if signal:
                print(f"  4. ✅ Signal détecté: {signal.signal_type.value}")
                
                # 5. Sauvegarde signal
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
                print(f"  5. ✅ Signal en DB (id={db_signal.id})")
            else:
                print("  4. ℹ️  Aucun signal pour cet item (normal)")
            
            session.close()
            
            print("\n✅ Pipeline complet OK")
            return True
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Lance tous les tests"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           TESTS DES COMPOSANTS DU BOT                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Charge .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env chargé\n")
    except ImportError:
        print("⚠️  python-dotenv non installé\n")
    
    results = {}
    
    # Lance chaque test
    tests = [
        ("Configuration", test_config),
        ("Base de données", test_database),
        ("API Skinport", test_skinport_api),
        ("Signal Engine", test_signal_engine),
        ("Alertes", test_alerts),
        ("Pipeline complet", test_full_pipeline)
    ]
    
    for name, test_func in tests:
        try:
            results[name] = await test_func()
            # Pause entre les tests pour éviter le rate limiting
            if "API" in name or "Pipeline" in name:
                await asyncio.sleep(5)
        except KeyboardInterrupt:
            print("\n⏹️  Tests interrompus")
            break
        except Exception as e:
            print(f"\n❌ Erreur inattendue dans {name}: {e}")
            results[name] = False
    
    # Résumé
    print_section("RÉSUMÉ DES TESTS")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")
    
    print(f"\n{'='*60}")
    print(f"Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont OK ! Tu peux lancer le bot.")
        print("   Commande: python main.py")
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifie ta config avant de lancer le bot.")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Tests arrêtés")