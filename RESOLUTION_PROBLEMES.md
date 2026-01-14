# Resolution des problemes - Skinport Trading Bot

## Probleme principal: RATE LIMIT API

### Statut actuel
- **Vous etes rate limite pour 56 minutes (3372 secondes)**
- L'API Skinport vous bloque jusqu'a environ 15h40
- Cause: Trop de requetes API en peu de temps

### Solution immediate
**ATTENDRE 1 HEURE avant de retester l'API**

### Verification du rate limit
```bash
python check_rate_limit.py
```

## Probleme secondaire: Encodage Unicode (Windows)

### Symptome
Les emojis dans le code Python causent des erreurs:
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

### Solution rapide
Utiliser PowerShell avec UTF-8:
```powershell
$OutputEncoding = [console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding
python main.py
```

### Solution permanente
Ajouter au debut de chaque script Python:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

## Ce qui fonctionne MAINTENANT

### 1. Brotli est installe
```bash
pip list | findstr brotli
# Output: brotli 1.2.0
```

### 2. L'API fonctionne (quand pas rate limite)
Le test `test_api_quick.py` a reussi:
- 23,422 items recuperes
- Decompression Brotli OK
- Authentification OK

### 3. Les composants fonctionnent
- Configuration: OK
- Base de donnees: OK
- Signal Engine: OK
- Alertes Discord: OK

## Prochaines etapes

### Dans 1 heure (apres le rate limit)
1. Verifier que le rate limit est leve:
   ```bash
   python check_rate_limit.py
   ```

2. Si OK, lancer le bot:
   ```bash
   python main.py
   ```

### Configuration du rate limiting dans le code

Le bot a ete configure pour:
- **Attendre 37.5 secondes entre chaque requete** (8 req / 5min max)
- **Retry automatique** si rate limit detecte
- **60 secondes d'attente** avant retry

### Fichiers modifies

1. `requirements.txt` - Ajoute brotli
2. `skinport_collector.py` - Ameliore gestion rate limit + retry
3. `main.py` - N'echoue plus si API indisponible au demarrage
4. `test_components.py` - Pause entre tests + gestion liste vide

## Recommendations

### Pour eviter le rate limit
1. **NE PAS** lancer les tests complets plusieurs fois rapidement
2. **UTILISER** test_no_api.py pour tester sans API
3. **CONFIGURER** SCAN_INTERVAL dans .env (defaut: 60 min)
4. **LIMITER** MAX_ITEMS dans .env (defaut: 200 items)

### Configuration .env optimale
```env
# Rate limiting
SCAN_INTERVAL=60          # Scan complet toutes les heures
MAX_ITEMS=200             # Maximum 200 items suivis

# Seuils de trading
Z_SCORE_THRESHOLD=-2.2
MIN_VOLUME_24H=5
MIN_EDGE_NET=3.0
MAX_ITEM_PRICE=100.0
```

## Logs et debugging

### Fichiers de log
- `skinport_bot.log` - Log principal du bot
- Console - Output temps reel

### Commandes utiles
```bash
# Verifier le rate limit
python check_rate_limit.py

# Tester sans API
python test_no_api.py

# Lancer le bot
python main.py

# Voir les logs en direct (PowerShell)
Get-Content skinport_bot.log -Wait -Tail 20
```

## Problemes connus et solutions

### 1. Rate limit atteint
**Solution**: Attendre le temps indique dans Retry-After

### 2. Emojis ne s'affichent pas
**Solution**: Utiliser PowerShell avec UTF-8 ou ignorer (le bot fonctionne quand meme)

### 3. Base de donnees corrompue
**Solution**: Supprimer `skinport_trading.db` et relancer

### 4. Pas d'alertes Discord
**Solution**: Verifier DISCORD_WEBHOOK_URL dans .env

## Support

### Verifier la configuration
```bash
python -c "from config import Config; c=Config(); c.print_summary(); c.validate()"
```

### Verifier Brotli
```bash
python -c "import brotli; print('Brotli OK')"
```

### Verifier la DB
```bash
python -c "from database import DatabaseManager; db=DatabaseManager(); db.create_tables(); print('DB OK')"
```

## Resume

**TOUT FONCTIONNE** sauf que vous devez attendre 1 heure avant de pouvoir utiliser l'API.

Le bot est pret pour le deployment apres le rate limit.
