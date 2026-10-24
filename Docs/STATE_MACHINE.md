# Machine à états — Sensitor AI

Implémentation : `MQL5/Experts/SensitorAI/SensitorAI.mq5` (suivi des setups `STrack`) et
`MQL5/Include/SensitorAI/PositionManager.mqh` (suivi des positions `SPosState`).
Chaque transition est journalisée dans `<symbole>_<magic>_events.csv` (heure, setup, position, état
de départ, état d'arrivée, prix, détail).

## 1. États

| État | Signification |
|------|---------------|
| `NO_SETUP` | Aucun setup actif dans cette direction. |
| `SETUP_VALID` | Setup confirmé et figé par le moteur, ordre pas encore envoyé (attente du filtre RSI en mode `GATE`, du spread, d'une annonce, ou nouvelle tentative après erreur transitoire). |
| `PENDING_ORDER` | Ordre limite accepté **et relu** côté serveur (`OrderSelect`/`HistoryOrderSelect`). |
| `POSITION_OPEN` | Exécution confirmée par une transaction `DEAL_ADD` (entrée) ou par l'historique. |
| `BREAK_EVEN_SET` | SL déplacé au prix réel d'entrée, modification relue chez le serveur. |
| `PARTIAL_CLOSED` | 50 % du volume initial clôturés (baisse de volume constatée). État transitoire. |
| `RUNNER_ACTIVE` | Solde géré par la méthode de runner A/B/C/D. |
| `CLOSED` | Position entièrement clôturée (journal `trades.csv` écrit depuis l'historique des deals). |
| `INVALIDATED` | Setup/ordre abandonné (raison codée). |
| `ERROR_SAFE` | État global : plus aucune nouvelle entrée ; la protection des positions continue. |

## 2. Transitions

| # | De | Vers | Condition (déterministe) | Action |
|---|----|------|--------------------------|--------|
| T1 | `NO_SETUP` | `SETUP_VALID` | Le moteur confirme un setup (§4–8 de la spécification) | Figer les niveaux, journaliser `setups.csv` |
| T2 | `SETUP_VALID` | `PENDING_ORDER` | Prêt à placer **et** limites de risque OK **et** volume > 0 **et** `OrderCheck` OK **et** retcode `DONE/PLACED` **et** ordre relu | `OrderSend` (limite, SL, TP éventuel), commentaire `SAI <id>` |
| T3 | `SETUP_VALID` | `SETUP_VALID` | Spread trop large, annonce, erreur transitoire (< 5 essais) | Nouvelle tentative (barre suivante / tick suivant) |
| T4 | `SETUP_VALID` | `INVALIDATED` | Règle d'invalidation (§9.2), prix déjà au-delà de l'entrée, limite de risque, volume min > risque, échec définitif, `ERROR_SAFE`, limite journalière | Raison codée |
| T5 | `PENDING_ORDER` | `INVALIDATED` | `INV_CONTINUATION`, `INV_DEEP_FAILURE`, `INV_BIAS_CHANGED`, `INV_SUPERSEDED`, `INV_RSI`, `INV_SAFETY_*`, ordre supprimé hors EA | `TRADE_ACTION_REMOVE` puis relecture |
| T6 | `PENDING_ORDER` | `POSITION_OPEN` | `DEAL_ADD` avec `DEAL_ENTRY_IN` pour l'ordre, ou historique `ORDER_STATE_FILLED/PARTIAL` | Enregistrer 1R = |prix réel − SL initial|, volume initial ; annuler le reliquat d'un remplissage partiel |
| T7 | `PENDING_ORDER` | `SETUP_VALID` | Ordre expiré par le broker (mode `DAY` uniquement) alors que le setup reste valide | Ré-envoi (jamais si un deal d'entrée existe) |
| T8 | `POSITION_OPEN` | `BREAK_EVEN_SET` | Prix ≥ entrée + 1R (achat ; Ask ≤ entrée − 1R en vente) et modification confirmée, ou SL déjà au-delà de l'entrée | `TRADE_ACTION_SLTP`, relecture |
| T9 | `BREAK_EVEN_SET` | `PARTIAL_CLOSED` | Prix ≥ entrée + 3R (R initial) et clôture partielle confirmée par la baisse de volume | Volume = floor(50 % × volume initial / pas) ; repli `CLOSE_ALL`/`KEEP_ALL` si indivisible |
| T9' | `POSITION_OPEN` | `BREAK_EVEN_SET` → `PARTIAL_CLOSED` | +1R et +3R franchis entre deux ticks (gap) | BE d'abord, puis partielle (règle PM-7) |
| T10 | `PARTIAL_CLOSED` | `RUNNER_ACTIVE` | Immédiat | Méthode A/B/C/D |
| T11 | `POSITION_OPEN`/`BREAK_EVEN_SET`/`RUNNER_ACTIVE` | `CLOSED` | SL/TP serveur, sortie runner A (cassure de structure), stop suiveur D, intervention externe | Journal `trades.csv` |
| T12 | tout état | `ERROR_SAFE` | ≥ `InpMaxConsecErrors` erreurs de trading consécutives ; position sans SL non restaurable ; SL initial inconnu ; données indisponibles > 600 ticks ; garde anti-lookahead | Annulation des ordres en attente ; persistance dans le fichier d'état |
| T13 | `ERROR_SAFE` | (normal) | **Uniquement** redémarrage de l'EA avec `InpClearErrorSafe=true` après analyse humaine | — |

Suspension journalière (`SUSPENDED`) : quand perte réalisée + latente du jour ≥ `InpDailyLossLimitPct`
de la balance de début de journée serveur, les ordres en attente sont annulés et aucun nouvel ordre
n'est envoyé jusqu'au jour serveur suivant. Ce n'est pas `ERROR_SAFE` (levée automatique).

## 3. Règles de robustesse

1. **Jamais d'exécution supposée** : `OrderSend()==true` ne suffit pas ; seuls le retcode, la relecture
   et les transactions font foi (`ExecutionManager.mqh`).
2. **Idempotence** : un setup a un identifiant déterministe (`B`/`S` + heure d'ouverture de la barre de
   cassure). Avant tout envoi, l'EA vérifie les ordres ouverts, l'historique (commentaire `SAI <id>`)
   et le fichier d'état (`sent_<id>`). Un setup n'est jamais envoyé deux fois.
3. **Retcodes incertains** (`TIMEOUT`, `CONNECTION`) : recherche de l'ordre par commentaire avant toute
   nouvelle tentative.
4. **Redémarrage** : le moteur rejoue les `InpWarmupEntryBars` dernières barres clôturées (résultat
   déterministe), puis `Reconcile()` rattache les ordres existants aux setups actifs, annule les ordres
   orphelins et reconstruit chaque position depuis MT5 : volume initial = somme des deals d'entrée, SL
   initial = SL de l'ordre d'ouverture dans l'historique (ou fichier d'état), BE fait = SL au-delà de
   l'entrée, partielle faite = volume courant < volume initial.
5. **Protections serveur vs locales** : SL et TP (méthodes B et C) sont chez le serveur et protègent la
   position même terminal coupé. Le passage au BE, la partielle, la sortie A et le stop suiveur D
   **nécessitent que l'EA tourne** (VPS).
