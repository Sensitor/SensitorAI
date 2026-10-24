# Installation sur MetaTrader 5

## 1. Copier les fichiers

Dans MT5 : *Fichier → Ouvrir le dossier des données*. Copier depuis le dépôt :

| Dépôt | Dossier de données MT5 |
|---|---|
| `MQL5/Experts/SensitorAI/` | `MQL5/Experts/SensitorAI/` |
| `MQL5/Include/SensitorAI/` (y compris `Tests/`) | `MQL5/Include/SensitorAI/` |
| `MQL5/Scripts/SensitorAI/` | `MQL5/Scripts/SensitorAI/` |
| `MQL5/Presets/*.set` | `MQL5/Presets/` (et `MQL5/Profiles/Tester/` pour le testeur) |

## 2. Compiler

MetaEditor → ouvrir `Experts/SensitorAI/SensitorAI.mq5` → *Compiler* (F7). Résultat attendu :
`0 errors` (un avertissement sur le format de version, sans effet). Faire de même pour
`Scripts/SensitorAI/SensitorTests.mq5`.

En ligne de commande (Windows) :

```bat
"C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"MQL5\Experts\SensitorAI\SensitorAI.mq5" /log:"compile.log"
```

Sous Linux : `Tools/compile_mql5.sh` (Wine 10+ de WineHQ requis ; Wine 9 de la distribution déclenche la
protection anti-débogueur de MT5).

## 3. Exécuter les tests MQL5

Glisser le script `SensitorTests` sur n'importe quel graphique. Onglet *Experts* attendu :
`SensitorTests 0.1.0: 90 passed, 0 failed`. Le résultat est aussi écrit dans
`<Common>\Files\SensitorAI\tests_result.txt`. **Ne pas utiliser l'EA si un test échoue.**

## 4. Vérifier les spécifications du symbole

Ouvrir *Spécifications* du symbole or du broker (nom exact : `XAUUSD`, `GOLD`, `XAUUSD.m`, …). L'EA lit
tout dynamiquement et journalise au démarrage une ligne `INIT` contenant : digits, point, tick, valeur
du tick, taille de contrat, volumes min/pas/max, stops level, freeze level, modes de remplissage,
d'expiration, hedging/netting, devises. **Vérifier cette ligne** (onglet *Experts* et
`<Common>\Files\SensitorAI\<symbole>_<magic>_events.csv`).

Points à confirmer avec le broker :
- fuseau horaire du serveur (forme des bougies H4 et coupure journalière) ;
- commission par lot (renseigner `InpCommissionPerLot` pour qu'elle soit incluse dans le risque) ;
- swaps et jour du triple swap ;
- type de compte (hedging recommandé ; en netting l'EA limite à une position à la fois).

## 5. Lancer l'EA

1. Ouvrir un graphique du symbole (n'importe quelle UT ; l'EA lit ses propres UT).
2. Glisser `SensitorAI` ; onglet *Commun* : autoriser le trading algorithmique.
3. Charger un preset (`MQL5/Presets/SensitorAI_demo.set`) ou régler les inputs (voir
   `Docs/SPECIFICATION.md` et `Docs/ASSUMPTIONS.md`).
4. Pour une première observation sans ordre : `InpDryRun=true`.
5. Vérifier le panneau en haut à gauche : état `RUNNING`, biais H4/H1, setups, positions.

## 6. Journaux

`<Common>\Files\SensitorAI\` (*Fichier → Ouvrir le dossier des données* → remonter à `Common\Files`) :
`decisions.csv`, `setups.csv`, `orders.csv`, `events.csv`, `trades.csv`, `errors.csv`, `state.csv`,
`heartbeat.txt` (préfixés par `<symbole>_<magic>`). Analyse :

```bash
python3 Research/scripts/analyze_mt5_logs.py --dir "<chemin>/Common/Files/SensitorAI" --tag XAUUSD_20250101
```

## 7. Backtest de l'EA dans le Strategy Tester

1. *Sur les données du broker* (recommandé pour la validation finale) : Testeur → Expert `SensitorAI`,
   symbole or du broker, période M15, modèle **« Chaque tick basé sur les ticks réels »**, dépôt et
   devise du compte, paramètres du preset. Les fichiers CSV sont écrits dans `Common\Files\SensitorAI`.
2. *Sur les données de recherche Dukascopy* (pour comparer avec la recherche Python) :
   `python3 Research/scripts/export_mt5_custom.py --start 2018-01-01 --end 2019-01-01`, copier le CSV dans
   `Common\Files\SensitorAI\`, exécuter le script `ImportCustomSymbol` (crée `XAUUSD_DK`), puis tester
   l'EA sur `XAUUSD_DK` en « 1 minute OHLC ». Un compte (démo) doit être connecté pour que le testeur
   démarre. Comparer ensuite `setups.csv` avec la sortie Python (`analyze_mt5_logs.py --python-setups`).
