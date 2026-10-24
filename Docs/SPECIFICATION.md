# Sensitor AI — Spécification formelle (v0.1)

> Document de référence. Toute implémentation (Python de référence `Research/sensitor/`,
> Expert Advisor MQL5 `MQL5/`) doit s'y conformer. Toute modification de la stratégie doit
> passer par ce document et être consignée dans `Docs/CHANGELOG.md`.

Légende des origines de règle :

| Tag | Signification |
|-----|---------------|
| **[U]** | Règle **explicitement définie par l'utilisateur** dans le cahier des charges. |
| **[H]** | **Hypothèse de développement** proposée par l'équipe de développement, configurable, non validée par l'utilisateur. |
| **[C]** | **Paramètre restant à confirmer** par l'utilisateur ; une valeur provisoire est utilisée. |

Une hypothèse [H] ou [C] n'est jamais une règle validée. La section 12 récapitule la liste.

---

## 0. Conventions générales

| ID | Convention | Origine |
|----|-----------|---------|
| CV-1 | Les barres sont indexées chronologiquement `0 … n-1` (0 = la plus ancienne). L'EA MQL5 utilise `ArraySetAsSeries(false)` pour respecter la même convention. | [H] |
| CV-2 | Une barre `i` d'unité de temps `tf` ouvre à `t_i` et **clôture à `t_i + tf`**. Ses OHLC ne sont utilisables qu'à partir de `t_i + tf` (instant de décision). Aucune décision n'utilise une barre en cours de formation. | [U] (pas de données futures) |
| CV-3 | Toute la structure (swings, BOS, OB, FVG, OTE, RSI, ATR) est calculée sur les prix **Bid** (prix affichés par MT5). Les exécutions tiennent compte du Bid/Ask : un buy limit est exécuté quand l'**Ask** atteint le prix ; un SL de vente est déclenché par l'**Ask**. | [H] |
| CV-4 | Multi-timeframe : à l'instant de décision `T` (clôture d'une barre de l'UT d'entrée), seules les barres H1/H4 dont la clôture est `≤ T` sont utilisées. | [U] |
| CV-5 | Les prix sont normalisés au `SYMBOL_TRADE_TICK_SIZE` du broker. Aucun « pip » codé en dur : toutes les distances sont exprimées en prix, en multiples d'ATR ou en points broker (`SYMBOL_POINT`). | [U] |
| CV-6 | Heures : l'EA travaille en heure serveur broker. La recherche Python travaille en UTC et reconstruit les barres H4 selon un décalage serveur configurable (défaut UTC+2 / UTC+3 en heure d'été US — convention « New-York close » la plus répandue). Les barres H4 dépendent du fuseau du broker : c'est une source d'écart documentée. | [H] |
| CV-7 | ATR = moyenne **simple** du True Range sur 14 barres (identique à `iATR` MT5). RSI = algorithme exact de `RSI.mq5` MT5 (lissage de Wilder initialisé par moyenne simple). Les deux sont recalculés en interne (MQL5 et Python) pour garantir la parité. | [H] |

---

## 1. Swings (pivots)

**Définition SW-1 — Fractal L/R** [H] (variante unique implémentée en v0.1)

Une barre `i` est un **swing high** si :
- `H[i] > H[j]` pour tout `j ∈ [i-L, i-1]` (strict à gauche),
- `H[i] ≥ H[j]` pour tout `j ∈ [i+1, i+R]` (non strict à droite).

Symétriquement, swing low : `L[i] < L[j]` à gauche, `L[i] ≤ L[j]` à droite.
En cas d'égalité, c'est donc **le premier** des sommets égaux qui est le pivot.

- **Confirmation** : le swing `i` n'existe qu'à la clôture de la barre `i+R`
  (`confirm_index = i+R`). C'est le mécanisme anti-lookahead principal.
- Paramètres : `SwingLeft/SwingRight` pour les UT de biais (défaut provisoire 3/3) [C]
  et pour l'UT d'entrée (défaut provisoire 2/2) [C].

Variantes documentées non implémentées (pour éviter de mélanger les définitions) :
zigzag ATR, swings « forts » (swing ayant provoqué un BOS). Elles pourront être ajoutées comme
valeurs supplémentaires de l'énumération `SwingMethod`.

## 2. Structure, BOS, CHoCH et biais par UT

Un **tracker de structure** indépendant est tenu pour chaque UT (H4, H1, UT d'entrée).
Il traite les barres clôturées une par une, dans l'ordre suivant, à la clôture de la barre `k` :

1. **Liquidité / sweeps** (section 3) — sur la base des niveaux actifs avant la barre `k`.
2. **Cassures** — sur la base de la référence courante :
   - `ref_high` = dernier swing high confirmé **non encore cassé** (il est remplacé par tout
     nouveau swing high confirmé, même plus bas : structure « interne »).
   - **Cassure haussière** si `C[k] > ref_high + buffer` où `buffer = BosBufferATR × ATR(k)`
     (défaut `0` ⇒ simple clôture au-delà). [H]
   - **Une mèche au-delà du niveau sans clôture n'est jamais une cassure** (c'est un sweep). [U]
   - Après cassure, `ref_high` est consommé (aucune autre cassure de ce niveau).
   - Symétrique pour `ref_low`. Si les deux cassures se produisent sur la même barre
     (cas dégénéré), la haussière est traitée d'abord, puis la baissière (ordre déterministe).
3. **Confirmation des nouveaux swings** dont `confirm_index = k` (ils deviennent les nouvelles
   références). L'ordre « cassure puis confirmation » est sans ambiguïté car la barre de
   confirmation d'un swing high ne peut pas clôturer au-dessus de ce swing.

**Qualification de la cassure** [H] :
- `BOS` si la cassure est dans le sens de la tendance courante de l'UT (ou tendance neutre) ;
- `CHoCH` (change of character) si elle est contraire à la tendance courante.

**Tendance par UT** — paramètre `BiasFlipMode` [H] :
- `FLIP_ON_CHOCH` (défaut provisoire [C]) : la tendance prend la direction de la dernière
  cassure confirmée (BOS ou CHoCH).
- `NEUTRAL_ON_CHOCH` : un CHoCH met la tendance à NEUTRE ; elle ne redevient directionnelle
  qu'au BOS suivant dans la nouvelle direction.

Au démarrage (pas encore de cassure observée) la tendance est NEUTRE.

### 2.1 Biais combiné H4/H1 — paramètre `BiasMode`

| H4 | H1 | `REQUIRE_BOTH` (défaut) | `H4_LEADS` |
|----|----|----|----|
| HAUSSE | HAUSSE | HAUSSE | HAUSSE |
| BAISSE | BAISSE | BAISSE | BAISSE |
| HAUSSE | BAISSE | **NEUTRE** | NEUTRE |
| HAUSSE | NEUTRE | NEUTRE | HAUSSE |
| NEUTRE | x | NEUTRE | NEUTRE |

- Contradiction H4/H1 ⇒ **aucune nouvelle entrée** [U] (comportement conservateur demandé).
- `REQUIRE_BOTH` est le défaut [H] ; `H4_LEADS` est une variante testable [H].

## 3. Liquidité et sweeps

Pour chaque UT, une liste de **niveaux de liquidité actifs** est tenue :
chaque swing high (resp. low) confirmé entre dans la liste (au plus `LiquidityMaxLevels`, défaut 30,
les plus anciens sortent en premier) [H].

À la clôture de la barre `k`, pour chaque niveau haut actif `P` :
- si `C[k] > P + buffer` ⇒ niveau **cassé** (retiré, ce n'est pas un sweep) ;
- sinon si `H[k] > P` ⇒ **sweep de liquidité acheteuse (BSL)** : mèche au-delà et clôture en
  deçà. Un événement `SWEEP_HIGH` est émis, le niveau est retiré (liquidité prise).

Symétrique pour les niveaux bas (`SWEEP_LOW`, liquidité vendeuse SSL).

**Classification d'un sweep vis-à-vis d'un setup** [H] (règles proposées, à valider) :

| Sweep | Setup ACHAT | Setup VENTE |
|-------|-------------|-------------|
| `SWEEP_LOW` sur UT d'entrée, H1 ou H4, avant le BOS d'entrée, dans la fenêtre `SweepLookbackBars` | **COMPATIBLE** (confluence : prise de liquidité vendeuse puis cassure haussière) | — |
| `SWEEP_HIGH` sur H1 ou H4, dans les `SweepLookbackBars` (UT concernée) précédant la création du setup | **PRUDENCE** | — |
| `SWEEP_HIGH` sur UT d'entrée, avant le BOS d'entrée | — | **COMPATIBLE** |
| `SWEEP_LOW` sur H1 ou H4 dans la fenêtre | — | **PRUDENCE** |

- Paramètre `CautionSweepAction` : `LOG_ONLY` | `BLOCK` (défaut provisoire `BLOCK` [C]).
- Paramètre `RequireCompatibleSweep` : `false` par défaut [C] — si `true`, un sweep COMPATIBLE est
  exigé pour valider le setup.
- **Invalidation par sweep** : un sweep n'invalide pas en lui-même un ordre en attente ; seules les
  règles d'invalidation de la section 9 annulent les ordres. Un sweep du point d'origine de
  l'impulsion avec clôture au-delà est une cassure, traitée par la section 9. [H]

## 4. BOS d'entrée et impulsion de référence (UT d'entrée)

- UT d'entrée : `EntryTF` ∈ {M5, M15} [U] ; défaut provisoire **M15** [C]. M5 est comparé en recherche.
- Un setup ACHAT naît d'une **cassure haussière** (BOS ou CHoCH) sur l'UT d'entrée survenant
  alors que le biais combiné (section 2.1) est HAUSSIER à l'instant de clôture de la barre de cassure [U].
- Enregistrement : swing cassé (index, prix, heure), barre de cassure, heure de confirmation [U].

**Origine de l'impulsion** (achat) : `o = argmin L[j]` pour `j ∈ [i_sh, k]` (dernier index en cas
d'égalité), où `i_sh` est l'index du swing high cassé et `k` la barre de cassure. `Lo = L[o]`. [H]

**Fin de l'impulsion** — paramètre `ImpulseAnchor` [H] :
- `SWING_CONFIRM` (défaut provisoire [C]) : on attend le **premier swing high confirmé** dont le pivot
  `p > o` après la cassure. `Hi = max H[j], j ∈ [o, p]`. Le setup est **confirmé à la clôture de
  la barre `p + R`**. Tant qu'il n'est pas confirmé, le candidat est abandonné si une cassure
  baissière survient sur l'UT d'entrée ou si le biais n'est plus haussier.
- `BOS_BAR` : `Hi = max H[j], j ∈ [o, k]`, setup confirmé à la clôture de `k`.

**Figeage** : `Lo`, `Hi`, OTE, OB, FVG, entrée et SL sont **figés à la confirmation du setup** et
ne sont plus jamais recalculés [U].

Filtre de taille optionnel `MinImpulseATR` (défaut 0 = désactivé) [H].

La vente est strictement symétrique (cassure baissière, origine = plus haut, fin = premier swing
low confirmé).

## 5. OTE (Optimal Trade Entry)

- Zone : retracement de **62 % à 79 %** de l'impulsion de référence [U].
- **Convention** [H, documentée] : le retracement `r` est mesuré **depuis l'extrémité de
  l'impulsion vers son origine** : 0 % = extrémité atteinte (`Hi` pour un achat), 100 % = origine
  (`Lo` pour un achat).
  - Achat : `niveau(r) = Hi − r × (Hi − Lo)` ⇒ `OTE = [Hi − 0,79·R ; Hi − 0,62·R]`, `R = Hi − Lo`.
  - Vente : `niveau(r) = Lo + r × (Hi − Lo)` ⇒ `OTE = [Lo + 0,62·R ; Lo + 0,79·R]`.
- Exemple numérique de référence (achat) : `Lo = 2000`, `Hi = 2010` ⇒ OTE = `[2002,10 ; 2003,80]`.
- Exemple (vente) : `Hi = 2010`, `Lo = 2000` ⇒ OTE = `[2006,20 ; 2007,90]`.
- Paramètres `OteMin = 0.62`, `OteMax = 0.79` [U].

## 6. Fair Value Gap et Order Block

### 6.1 FVG (achat ; vente symétrique)
Motif de 3 bougies `(m−1, m, m+1)` : **FVG haussier** si `L[m+1] > H[m−1]` (strict).
Zone : `[H[m−1] ; L[m+1]]`. Taille minimale `FvgMinATR × ATR` (défaut 0) et au moins 1 tick [H].
Recherche : uniquement dans l'impulsion de référence, `o ≤ m−1` et `m+1 ≤ e` où `e` est l'index de
fin d'impulsion (`argmax` de `Hi`). Les FVG sont examinés **chronologiquement**. [H]

### 6.2 Order Block (achat ; vente symétrique)
Pour un FVG candidat d'index `m`, l'**OB est la dernière bougie baissière** (`C < O`) d'index
`j ∈ [max(o − ObPreOriginBars, m − 1 − ObMaxDistBars) ; m − 1]`, recherchée en remontant depuis `m−1` [H].
- `ObMaxDistBars` défaut 5, `ObPreOriginBars` défaut 2 [C].
- Zone de l'OB — paramètre `ObZoneMode` [H] : `WICK` (défaut, `[L ; H]` de la bougie) | `BODY`
  (`[min(O,C) ; max(O,C)]`).
- Le **couple (OB, FVG)** retenu est le premier (dans l'ordre chronologique des FVG) pour lequel un
  OB existe **et** dont l'intersection OB ∩ OTE est non vide. Le FVG est ainsi « laissé par le
  mouvement associé à la création de l'OB » [U] : c'est le déplacement qui suit immédiatement l'OB.

### 6.3 États des zones (OB et FVG)

Suivi à partir de la barre qui suit la création de la zone (`m+2` pour le FVG, `m+2` pour l'OB —
le déplacement qui crée la zone n'est pas une mitigation) :

| État | OB haussier `[a ; b]` | FVG haussier `[a ; b]` |
|------|------------------------|-------------------------|
| `NEW` | barre de création | barre de création |
| `VALID` | aucun prix `≤ b` depuis | aucun prix `≤ b` depuis |
| `PARTIALLY_MITIGATED` | `min L ≤ b` et `> a` | `min L ≤ b` et `> a` |
| `FULLY_MITIGATED` | `min L ≤ a` | `min L ≤ a` (gap comblé) |
| `INVALIDATED` | une clôture `< a` | une clôture `< a` |

Condition de setup [H] : à la confirmation, l'OB n'est ni `FULLY_MITIGATED` ni `INVALIDATED` et le
FVG n'est pas `INVALIDATED` (un FVG `FULLY_MITIGATED` est accepté : le retracement vers l'OB, situé
au-delà du FVG, le comble normalement — décision consignée dans `Docs/CHANGELOG.md`). Une zone n'est jamais considérée valide indéfiniment :
le setup est abandonné dès qu'une règle de la section 9 s'applique.
Note : pour un achat l'OB est sous le FVG ; le prix doit donc traverser le FVG pour atteindre
l'ordre. Le comblement du FVG **après** la confirmation est attendu et n'invalide pas le setup.

## 7. Prix d'entrée

- Zone autorisée `Z = OB ∩ OTE = [max(OB.a, OTE.a) ; min(OB.b, OTE.b)]` [U].
  - **Cas A** : OB entièrement inclus dans l'OTE ⇒ `Z = OB`.
  - **Cas B** : chevauchement partiel ⇒ `Z` = intersection exacte.
  - Intersection vide ⇒ pas de setup (`REJECT_NO_OB_OTE_OVERLAP`).
- Paramètre `EntryDepth ∈ [0 ; 1]` [U : configurable, C : valeur] :
  - Achat : `E = Z.b − EntryDepth × (Z.b − Z.a)` (0 = bord proximal haut, 1 = bord distal bas).
  - Vente : `E = Z.a + EntryDepth × (Z.b − Z.a)`.
  - Défaut provisoire **0.5** ; les valeurs 0, 0.5 et 1 sont comparées en recherche. Le milieu
    n'est pas présumé optimal [U].
- Arrondi : `E` est arrondi au tick le plus proche (arrondi « demi vers le haut », identique à
  `MathRound` MQL5) puis **borné** dans
  `[ceil_tick(Z.a) ; floor_tick(Z.b)]`. Si cet intervalle est vide ⇒ `REJECT_ZONE_TOO_NARROW`.
  **L'entrée n'est jamais hors de Z** [U].
- Ordre **limite uniquement** ; aucune entrée au marché de rattrapage [U]. Si, au moment de placer
  l'ordre, le prix a déjà franchi `E` (achat : `Ask ≤ E`), le setup est marqué
  `MISSED_AT_PLACEMENT` et **n'est pas exécuté** [H].
- Si le prix (Bid) a déjà touché `E` entre la fin de l'impulsion et le moment où l'ordre peut être placé
  (attente de la confirmation du swing ou du filtre RSI), le setup est marqué
  `MISSED_TOUCHED_BEFORE_PLACEMENT` (paramètre `RejectIfTouched`, défaut `true`) [H] : le premier
  retour dans la zone a été manqué et un « second contact » n'est pas pris par défaut.

## 8. Stop Loss

- Paramètre `SlAnchor` [H] :
  - `STRUCTURAL` (défaut) : achat `SL = min(OB.a, Lo) − buffer` ; vente `SL = max(OB.b, Hi) + buffer`.
  - `OB_DISTAL` : achat `SL = OB.a − buffer`.
  - `IMPULSE_ORIGIN` : achat `SL = Lo − buffer`.
- `buffer = max(SlBufferPoints × point, SlBufferATR × ATR_entrée)` ; défauts `SlBufferPoints = 0`,
  `SlBufferATR = 0.10` [C].
- Vente : le spread courant est ajouté au SL (`SlAddSpreadForSells = true`) car le SL d'une vente est
  déclenché par l'Ask alors que la structure est mesurée sur le Bid [H].
- Arrondi du SL **vers l'extérieur** (achat : vers le bas ; vente : vers le haut).
- Distance de risque `D = |E − SL|`. Contrôles [H] :
  `D > 0`, `D ≥ MinSlSpreadMult × spread` (défaut 3), `D ≥ SYMBOL_TRADE_STOPS_LEVEL × point`,
  `D ≤ MaxSlATR × ATR` si `MaxSlATR > 0` (défaut 0 = désactivé).
- Le SL **n'est pas une distance fixe** [U]. Les distances manuelles de l'utilisateur (« 50 à 80 pips »)
  servent uniquement de contrôle de cohérence dans les rapports.
- `D` (ou plus exactement l'écart réel `|prix d'exécution − SL initial|`) est enregistré comme **1R** [U].

## 9. Cycle de vie du setup et invalidation

### 9.1 Filtre RSI (exclusion uniquement) [U]
- RSI(14), seuils 70/30, fenêtre des **5 dernières bougies clôturées** [U].
- Achat refusé si `max(RSI[k−4..k]) ≥ 70` ; vente refusée si `min(RSI[k−4..k]) ≤ 30` [U].
- UT du RSI : **paramètre** `RsiTF` ; valeur de référence provisoire = UT d'entrée [C].
- Moment de vérification — paramètre `RsiMode` [U : comparer ; H : modes] :
  - `OFF` : référence sans filtre (obligatoire en recherche) ;
  - `AT_SETUP` (défaut provisoire [C]) : vérifié une fois à la confirmation du setup ; échec ⇒ rejet définitif ;
  - `GATE_PLACEMENT` : le setup reste vivant ; l'ordre n'est placé qu'à la première clôture où la fenêtre
    RSI est conforme (et le setup toujours valide) ;
  - `CONTINUOUS` : comme `GATE_PLACEMENT`, puis réévalué à chaque clôture tant que l'ordre est en attente ;
    une violation annule l'ordre et invalide le setup.

### 9.2 Règles d'invalidation (ordre en attente ou setup non encore placé)
Évaluées à **chaque clôture de barre** de l'UT d'entrée (et à chaque mise à jour H1/H4 pour le biais),
jamais par simple écoulement du temps [U]. Il n'y a **aucune durée maximale** [U].

| Code | Condition (achat ; vente symétrique) | Paramètre |
|------|------|------|
| `INV_CONTINUATION` | Le prix prolonge l'impulsion au-delà de `Hi` sans retracer : `CLOSE` ⇒ `C > Hi + buffer` (défaut [H]) ; `WICK` ⇒ `H > Hi`. | `ContinuationInvalidation` |
| `INV_DEEP_FAILURE` | Clôture sous le SL ou sous l'origine `Lo` sans exécution (gap / spread). | — |
| `INV_BIAS_CHANGED` | Le biais combiné n'est plus haussier. | `CancelOnBiasChange` (défaut true [H]) |
| `INV_SUPERSEDED` | Un nouveau setup confirmé dans la même direction remplace l'ancien (un seul setup actif par direction). | — |
| `INV_RSI` | Mode `CONTINUOUS` uniquement. | `RsiMode` |
| `INV_SAFETY` | Limite journalière atteinte, mode ERROR_SAFE, filtre news (si `NewsCancelPending`). | section 11 |

Exemple utilisateur [U] : vente en attente, le prix poursuit sa baisse sous `Lo` (nouveau plus bas
confirmé par clôture) ⇒ `INV_CONTINUATION` ⇒ annulation, pas de vente en retard ; attente d'un
nouveau setup (qui naîtra de la cassure correspondante).

Une mèche isolée (`WICK`), une clôture (`CLOSE`) et un BOS confirmé ne sont pas équivalents [U] :
avec `ImpulseAnchor = SWING_CONFIRM`, `Hi` est un swing confirmé, donc `CLOSE` au-delà de `Hi`
**est** un BOS confirmé de l'UT d'entrée ; `WICK` est la variante plus stricte.

## 10. Gestion de position

| ID | Règle | Origine |
|----|-------|---------|
| PM-1 | `1R = |prix d'exécution réel − SL initial|`, figé à l'exécution, persisté. | [U] |
| PM-2 | **Break-even** quand le prix atteint `+1R` (achat : `Bid ≥ entrée + 1R`) : SL ← prix réel d'entrée (+ `BeOffsetPoints`, défaut 0). | [U] |
| PM-3 | Le SL n'est **jamais** éloigné (achat : le nouveau SL doit être `>` à l'ancien). | [U] |
| PM-4 | Modification confirmée par relecture de la position chez le serveur ; heure et prix journalisés. | [U] |
| PM-5 | **Prise partielle** à `+3R` (calculé avec le R initial) : clôture de `50 %` du **volume initial**, une seule fois. | [U] |
| PM-6 | Volume partiel = `floor(volume_initial × 0,5 / step) × step`. Si `< volume_min` : `PartialFallback` = `CLOSE_ALL` (défaut [C]) ou `KEEP_ALL`. Jamais de volume invalide. | [U] + [H] |
| PM-7 | Si un même tick dépasse `+1R` et `+3R`, l'ordre est : BE puis partielle. | [H] |
| PM-8 | Après la partielle, le runner est géré par la méthode `RunnerMethod`. | [U] |

### 10.1 Méthodes de runner [U : les quatre méthodes ; H : définitions précises]

| Méthode | Définition algorithmique |
|---------|--------------------------|
| **A — `STRUCTURE`** | Clôture du runner à la première **cassure baissière** (clôture sous le dernier swing low confirmé non cassé) de l'UT d'entrée survenant après l'exécution. Sortie au marché à l'ouverture suivante. |
| **B — `LIQUIDITY`** | TP serveur au premier niveau de liquidité actif de `LiquidityTF` (défaut H1 [C]) **strictement au-dessus** de `entrée + 3R`, figé à la confirmation du setup. À défaut : `LiquidityFallbackR` (défaut 6R [C]). |
| **C — `FIXED_R`** | TP serveur à `RunnerTargetR` (5R ou 6R comparés) placé dès l'envoi de l'ordre. |
| **D — `TRAILING`** | SL déplacé derrière chaque nouveau swing low confirmé de l'UT d'entrée (`swing − buffer`), uniquement si cela **rapproche** le SL. |

Toutes les méthodes conservent le SL au break-even comme protection serveur. Comparaison sur les
**mêmes signaux** (même moteur de setups, mêmes coûts, mêmes périodes) [U].

## 11. Risque, sizing et sécurité

| ID | Règle | Défaut | Origine |
|----|-------|--------|---------|
| RK-1 | Risque nominal par trade | 1 % | [U] |
| RK-2 | Capital de référence `RiskBase` : `BALANCE`, `EQUITY`, `MIN_BALANCE_EQUITY`, `FIXED` | `MIN_BALANCE_EQUITY` | [C] |
| RK-3 | Perte au SL pour 1 lot calculée par `OrderCalcProfit` (devise du compte, spécifications du symbole) ; jamais de valeur du pip supposée. Commission estimée (`CommissionPerLot`) incluse dans le risque. | — | [U] |
| RK-4 | `volume = floor(risque_monétaire / perte_par_lot / step) × step` ⇒ le risque n'est jamais dépassé par l'arrondi. | — | [U] |
| RK-5 | Si `volume < volume_min` ⇒ **trade refusé** (`REJECT_MIN_LOT_EXCEEDS_RISK`). Plafond `volume_max` et `SYMBOL_VOLUME_LIMIT`. | — | [U] |
| RK-6 | Vérification de la marge (`OrderCalcMargin`) et `OrderCheck` avant tout envoi. | — | [U] |
| RK-7 | Perte journalière max (réalisée + latente, référence = balance de début de journée serveur) ⇒ suspension des entrées et annulation des ordres en attente jusqu'au jour suivant. | 3 % | [H] |
| RK-8 | Positions simultanées max | 2 | [H] |
| RK-9 | Ordres en attente max | 1 par direction | [H] |
| RK-10 | Risque total ouvert max (somme des pertes au SL des positions + ordres en attente) | 2 % | [H] |
| RK-11 | Spread max au placement (`MaxSpreadPoints`) | 0 = auto : 3 × spread médian observé | [C] |
| RK-12 | Aucun mécanisme d'augmentation du risque après pertes (pas de martingale, pas de grille) | — | [U] |
| RK-13 | Le risque de 1 % est **nominal** : gap, slippage, exécution dégradée peuvent le dépasser. | — | [U] |
| RK-14 | Filtre d'annonces économiques (`NewsFilter`, API Calendar MT5, événements USD de haute importance, fenêtre `NewsMinutesBefore/After`) — **désactivé par défaut** car non testable dans le Strategy Tester. | off | [U]+[H] |
| RK-15 | Sessions : aucune restriction par défaut ; classification UTC Asie 00–07, Londres 07–12, chevauchement 12–16, New York 16–21, fin 21–24 pour l'analyse. | — | [U]+[H] |

## 12. Machine à états

États par setup : `NO_SETUP → SETUP_VALID → PENDING_ORDER → POSITION_OPEN → BREAK_EVEN_SET →
PARTIAL_CLOSED → RUNNER_ACTIVE → CLOSED`, plus `INVALIDATED` et l'état global `ERROR_SAFE`.
Voir `Docs/STATE_MACHINE.md` pour la table de transitions complète. Principes :

- Un ordre n'est **jamais** considéré exécuté parce que `OrderSend` a été appelé : seuls le retcode,
  les transactions (`OnTradeTransaction`) et la relecture des ordres/positions font foi [U].
- L'état est **reconstructible depuis MT5** au redémarrage (magic + commentaire `SAI <dir> <id>`,
  historique des ordres et deals) ; un fichier d'état local n'est qu'une seconde ligne de défense [U].
- `ERROR_SAFE` : suspension des nouvelles entrées, la gestion des positions existantes (protection)
  continue. Sortie manuelle uniquement (réinitialisation de l'EA) [H].

## 13. Cas de tests attendus

Voir `Tests/README.md` : chaque concept (swings, BOS, sweeps, OB, FVG, OTE, intersection, RSI,
volume, R, invalidation, BE, partielle, runners) possède des cas synthétiques achat/vente,
ambigus, invalides et incomplets dont le résultat attendu est écrit **avant** l'exécution.

## 14. Récapitulatif des hypothèses [H] et paramètres à confirmer [C]

Voir `Docs/ASSUMPTIONS.md` (liste numérotée, avec impact attendu et plan de test de chacune).
