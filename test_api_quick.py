"""
Quick test to verify Brotli compression works with Skinport API
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from config import Config
from skinport_collector import SkinportCollector

async def test_api():
    config = Config()

    print("Testing Skinport API with Brotli compression...")
    print(f"Client ID configured: {bool(config.skinport.client_id)}")
    print(f"Client Secret configured: {bool(config.skinport.client_secret)}")

    async with SkinportCollector(
        client_id=config.skinport.client_id,
        client_secret=config.skinport.client_secret
    ) as collector:
        items = await collector.get_items()

        if items:
            print(f"\nSUCCESS! Retrieved {len(items)} items")
            print(f"Example item: {items[0].get('market_hash_name')}")
            print(f"Price: {items[0].get('min_price')} EUR")
            return True
        else:
            print("\nFAILED: No items retrieved")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_api())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
