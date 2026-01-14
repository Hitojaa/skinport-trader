"""
Outil pour vérifier l'état du rate limit de l'API Skinport
"""
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

async def check_rate_limit():
    """Vérifie si l'API répond et affiche les headers de rate limit"""

    client_id = os.getenv('SKINPORT_CLIENT_ID', '')
    client_secret = os.getenv('SKINPORT_CLIENT_SECRET', '')

    if not client_id or not client_secret:
        print("ERREUR - Client ID ou Secret manquant dans .env")
        return

    import base64
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Accept-Encoding": "br"
    }

    url = "https://api.skinport.com/v1/items"
    params = {"app_id": 730, "currency": "EUR"}

    print("Verification du rate limit Skinport API...")
    print(f"Heure: {datetime.now().strftime('%H:%M:%S')}\n")

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, params=params) as response:
                print(f"Status Code: {response.status}")

                # Affiche les headers de rate limit
                print("\nHeaders de Rate Limit:")
                for header in ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset',
                              'Retry-After', 'X-Request-Id']:
                    value = response.headers.get(header)
                    if value:
                        print(f"   {header}: {value}")

                if response.status == 200:
                    data = await response.json()
                    print(f"\nOK - API OK - {len(data)} items disponibles")
                    print(f"   Premier item: {data[0].get('market_hash_name')}")

                elif response.status == 429:
                    print("\nERREUR - Rate limit atteint!")
                    retry_after = response.headers.get('Retry-After', 'inconnu')
                    print(f"   Retry-After: {retry_after} secondes")

                    text = await response.text()
                    print(f"\n   Message: {text[:200]}")

                else:
                    text = await response.text()
                    print(f"\nERREUR - Erreur {response.status}")
                    print(f"   Message: {text[:300]}")

        except Exception as e:
            print(f"\nException: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_rate_limit())
