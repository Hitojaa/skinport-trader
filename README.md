# 🎯 Skinport Tracker - UN SEUL SKIN

Bot ultra-simple qui surveille **UN SEUL skin CS2** sur Skinport et t'alerte sur Discord quand le prix est intéressant.

## 💡 Concept

Au lieu de scanner des centaines de skins au hasard :
- ✅ Tu choisis **UN skin volatile** (ex: AK-47 Redline, AWP Asiimov)
- ✅ Le bot check son prix **toutes les 5 minutes**
- ✅ Il t'envoie une **alerte Discord** quand le prix est **15%+ sous la médiane 7j**
- ✅ **Économique** : minimum d'appels API

## 🚀 Installation rapide

```bash
# 1. Clone le repo
git clone https://github.com/ton-username/skinport-trader.git
cd skinport-trader

# 2. Installe les dépendances
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Édite .env avec tes credentials

# 4. Lance !
python run.py
```

## ⚙️ Configuration (.env)

```env
# API Skinport (obligatoire)
SKINPORT_CLIENT_ID=ton_client_id
SKINPORT_CLIENT_SECRET=ton_secret

# Skin à surveiller (obligatoire)
SKIN_TO_TRACK=AK-47 | Redline (Field-Tested)

# Discord webhook (obligatoire)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Paramètres (optionnel)
CHECK_INTERVAL_MINUTES=5        # Check toutes les 5 min
PRICE_DROP_THRESHOLD=15.0       # Alerte si -15% sous médiane
MIN_EDGE_PERCENT=5.0            # Profit min après frais
MIN_ALERT_INTERVAL=30           # Max 1 alerte/30min
```

## 📊 Comment ça marche ?

1. **Récupère le prix actuel** du skin
2. **Compare avec la médiane 7 jours** (prix moyen récent)
3. **Calcule le profit potentiel** après frais Skinport (12%)
4. **Alerte si opportunité** :
   - Prix ≥ 15% sous la médiane
   - Profit net ≥ 5% après frais

### Exemple concret

```
Skin: AK-47 | Redline (Field-Tested)
Prix actuel: 7.50€
Médiane 7j: 9.00€
Baisse: -16.7% ✅
Profit net: +7.2% après frais ✅

→ ALERTE DISCORD envoyée ! 🔔
```

## 🎮 Choix du skin

Choisis un skin **volatile** avec **bon volume** :

**✅ Bons choix (populaires + volatils) :**
- AK-47 | Redline (Field-Tested)
- AWP | Asiimov (Field-Tested)
- M4A4 | Desolate Space (Field-Tested)
- Glock-18 | Water Elemental (Field-Tested)

**❌ Mauvais choix :**
- Skins rares/chers (pas de volume)
- Skins stables (pas de volatilité)
- Capsules/stickers (marché différent)

💡 **Astuce** : Va sur Skinport, cherche un skin populaire, regarde son graphique de prix sur 7j. S'il bouge beaucoup = bon candidat !

## 📁 Structure

```
skinport-trader/
├── src/
│   ├── config.py           # Configuration
│   ├── skinport_tracker.py # Surveillance du skin
│   ├── alerts.py           # Alertes Discord
│   └── main.py             # Boucle principale
├── data/                    # Logs (auto-créé)
├── .env                     # Ta config (à créer)
└── run.py                   # Lance le bot
```

## 🔔 Format de l'alerte Discord

```
🔔 OPPORTUNITÉ DÉTECTÉE !
AK-47 | Redline (Field-Tested)

💰 Prix actuel: 7.50€
📊 Médiane 7j: 9.00€
📉 Baisse: -16.7%
💵 Profit net estimé: +7.2%
📈 Volume 24h: 42 ventes
⏰ Heure: 14:23:45

Prix 16.7% sous médiane 7j, edge net 7.2%
```

## 📊 Logs

Les logs sont dans `data/skinport_tracker.log` :

```bash
# Voir les logs en temps réel
tail -f data/skinport_tracker.log
```

## ⏹️ Arrêter le bot

Appuie sur `Ctrl+C`

## 🔧 API Rate Limits

Skinport autorise **8 requêtes / 5 minutes**.
Le bot respecte automatiquement ce limit (45s entre requêtes).

**Avec check toutes les 5 min** :
- 2 requêtes par check (prix + historique)
- 90 secondes d'attente minimum
- **Largement dans les limites** ✅

## ⚠️ Avertissements

- 🎲 **Trading = risque** : pas de garantie de profit
- 💰 **Frais Skinport** : 12% sur les ventes
- ⏱️ **Rate limits** : ne modifie pas l'intervalle sans raison
- 💵 **Capital requis** : minimum 50€ recommandé

## 🆘 Problèmes fréquents

### ❌ "Skin not found"
→ Vérifie l'orthographe exacte sur Skinport (copie-colle le nom)

### ❌ "API Error 401"
→ Vérifie tes credentials Skinport

### ❌ "Discord Error 404"
→ Vérifie ton webhook Discord (doit être valide)

### ❌ Pas d'alertes
→ Normal ! La plupart du temps, le prix est stable. Sois patient.

## 📈 Optimisations

### Skin trop stable ?
→ Change de skin, choisis-en un plus volatile

### Trop/pas assez d'alertes ?
→ Ajuste `PRICE_DROP_THRESHOLD` dans .env (10-20%)

### Check plus fréquent ?
→ Baisse `CHECK_INTERVAL_MINUTES` (attention aux rate limits)

## 📄 Licence

MIT - Utilise à tes risques et périls

## 🙏 Crédits

API: [Skinport](https://skinport.com) | Bot: fait maison 🚀
