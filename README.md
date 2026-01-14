# 🎮 Skinport CS2 Trading Bot

Bot de trading automatisé pour skins Counter-Strike 2 sur Skinport.

## 📋 Description

Ce bot surveille en continu les prix des skins CS2 sur Skinport et détecte automatiquement :
- **📉 Prix sous-évalués** : Items 15%+ sous leur médiane 7 jours
- **📈 Momentum haussier** : Items avec une tendance de prix à la hausse

Il vous envoie des alertes Discord/Telegram lorsqu'une opportunité de trading est détectée.

## 🏗️ Architecture

```
skinport-trader/
├── src/                    # Code source principal
│   ├── main.py            # Point d'entrée du bot
│   ├── config.py          # Configuration (variables d'environnement)
│   ├── database.py        # Gestion base de données SQLite
│   ├── skinport_collector.py  # Collecteur API Skinport + analyse
│   └── alerts.py          # Système d'alertes Discord/Telegram
├── tests/                 # Tests
│   └── test_api.py       # Test de l'API Skinport
├── data/                  # Données générées (gitignored)
│   ├── skinport_trading.db
│   └── skinport_bot.log
├── .env                   # Variables d'environnement (à créer)
├── requirements.txt       # Dépendances Python
└── run.py                # Script de lancement
```

## 🚀 Installation

### 1. Prérequis
- Python 3.8+
- Compte Skinport avec API credentials

### 2. Installation
```bash
# Clone le repo
git clone https://github.com/ton-username/skinport-trader.git
cd skinport-trader

# Crée un environnement virtuel
python -m venv venv

# Active l'environnement virtuel
# Sur Windows:
venv\Scripts\activate
# Sur Linux/Mac:
source venv/bin/activate

# Installe les dépendances
pip install -r requirements.txt
```

### 3. Configuration

Copie `.env.example` en `.env` et remplis tes credentials :

```bash
cp .env.example .env
```

Édite `.env` avec tes propres valeurs :
```env
# API Skinport (REQUIS)
# Obtenir sur: https://skinport.com/settings
SKINPORT_CLIENT_ID=ton_client_id
SKINPORT_CLIENT_SECRET=ton_client_secret

# Alertes Discord (RECOMMANDÉ)
# Créer un webhook: Paramètres serveur > Intégrations > Webhooks
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Alertes Telegram (OPTIONNEL)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# Paramètres de trading (optionnel, valeurs par défaut OK)
MAX_ITEM_PRICE=100.0
MIN_VOLUME_24H=5
MIN_EDGE_NET=3.0
```

## ▶️ Utilisation

### Lancer le bot en mode 24/7
```bash
python run.py
```

### Tester l'API avant de lancer
```bash
python tests/test_api.py
```

Le bot va :
1. Se connecter à l'API Skinport
2. Scanner les items disponibles (par défaut : 10 items/scan)
3. Analyser les statistiques de prix (24h, 7j, 30j)
4. Détecter les signaux de trading
5. Envoyer des alertes Discord/Telegram
6. Répéter toutes les heures

## 📊 Signaux détectés

### UNDERPRICED (Sous-évalué)
- Prix actuel **< 15% sous la médiane 7 jours**
- Edge net **> 3%** après frais Skinport (12%)
- Volume **> 5 ventes/24h**
- **Action** : Acheter maintenant, revendre à prix normal

### MOMENTUM (Tendance haussière)
- Prix moyen 24h **> Prix moyen 7j**
- Momentum **> 8%**
- Volume élevé (> 7-8 ventes/24h)
- **Action** : Acheter avant la hausse, revendre au pic

## ⚙️ Configuration avancée

Modifie les variables d'environnement dans `.env` :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `MAX_ITEMS_PER_SCAN` | Nombre d'items analysés par scan | 10 |
| `SCAN_INTERVAL` | Intervalle entre scans (minutes) | 60 |
| `RATE_LIMIT_DELAY` | Délai entre requêtes API (secondes) | 45 |
| `MAX_ITEM_PRICE` | Prix max d'un item (€) | 100 |
| `MIN_VOLUME_24H` | Volume minimum requis | 5 |
| `MIN_EDGE_NET` | Edge minimum après frais (%) | 3.0 |

## 🛑 Arrêter le bot

```bash
# Appuie sur Ctrl+C
```

## 📝 Logs

Les logs sont sauvegardés dans `data/skinport_bot.log`

```bash
# Voir les logs en temps réel
tail -f data/skinport_bot.log
```

## 🔧 Développement

### Structure du code

- **`config.py`** : Charge les variables d'environnement et valide la config
- **`database.py`** : ORM SQLAlchemy pour stocker items/prix/signaux
- **`skinport_collector.py`** :
  - `SkinportCollector` : Appels API Skinport avec rate limiting
  - `SignalEngine` : Détection des signaux de trading
- **`alerts.py`** : Envoi d'alertes Discord/Telegram avec anti-spam
- **`main.py`** : Boucle principale du bot 24/7

### Ajouter un nouveau signal

Édite `src/skinport_collector.py` > `SignalEngine.detect_signals()` :

```python
# Signal personnalisé
if ma_condition:
    return TradingSignal(
        timestamp=now,
        item_name=item_data["market_hash_name"],
        signal_type=SignalType.MON_SIGNAL,
        ...
    )
```

## 📚 API Skinport

Documentation officielle : https://docs.skinport.com

Endpoints utilisés :
- `/v1/items` : Liste des items disponibles
- `/v1/sales/history` : Statistiques de prix agrégées

Rate limits : **8 requêtes / 5 minutes** (respectés automatiquement)

## ⚠️ Avertissements

- **Trading à risque** : Ce bot ne garantit pas de profit
- **Frais Skinport** : 12% de frais sur les ventes
- **Rate limits** : Respecte les limites API ou risque de ban
- **Capital requis** : Minimum 50-100€ recommandé
- **Pas de conseil financier** : À utiliser à tes risques et périls

## 📄 Licence

MIT License - Utilise à tes risques

## 🤝 Contribution

Les pull requests sont bienvenues ! Pour des changements majeurs, ouvre d'abord une issue.

## 📧 Support

En cas de problème :
1. Vérifie les logs dans `data/skinport_bot.log`
2. Teste l'API avec `python tests/test_api.py`
3. Ouvre une issue sur GitHub
