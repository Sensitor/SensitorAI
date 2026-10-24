# Hypothèses de développement et paramètres à confirmer

Chaque élément ci-dessous est **configurable** (input MQL5 / champ de `StrategyConfig`). Aucun n'est une
règle validée par l'utilisateur. Les éléments marqués ⚠ influencent fortement le nombre de trades ou la
nature de la stratégie et méritent une confirmation prioritaire.

## A. Paramètres explicitement définis par l'utilisateur [U] (rappel)

Marché XAU/USD ; biais H4 + H1 ; confirmation par BOS M5 ou M15 ; entrée en ordre limite dans OB ∩ OTE ;
OTE 62–79 % ; OB + FVG + OTE + BOS + biais requis ; pas d'entrée au marché de rattrapage ; pas de durée
maximale d'un ordre ; annulation sur invalidation structurelle ; RSI(14) 70/30 sur 5 bougies clôturées
comme filtre d'exclusion ; risque 1 % ; refus si le lot minimal dépasse le risque ; SL structurel ;
BE à +1R au prix réel d'entrée ; 50 % à +3R avec R initial ; quatre méthodes de runner comparées
(A structure, B liquidité, C 5R/6R, D trailing structurel) ; pas d'augmentation du risque après pertes.

## B. Hypothèses de développement [H]

| # | Hypothèse | Valeur | Impact attendu | Comment la tester |
|---|-----------|--------|----------------|-------------------|
| H1 | Swings = pivots fractals stricts à gauche / non stricts à droite | — | Définit tout le reste | Variante zigzag ATR à ajouter si désiré |
| H2 | BOS = **clôture** au-delà du dernier swing non cassé (structure interne : le swing le plus récent remplace le précédent) | buffer 0 ATR | Une mèche n'est jamais un BOS (conforme [U]) | `BosBufferATR` > 0 |
| H3 | ⚠ Biais combiné : H4 et H1 doivent être identiques | `REQUIRE_BOTH` | Beaucoup de périodes neutres ⇒ moins de trades | Variante `H4_LEADS` (E6) |
| H4 | Sweep = mèche au-delà d'un niveau de liquidité actif + clôture en deçà ; le niveau est alors retiré | — | — | Tests unitaires |
| H5 | ⚠ Classification des sweeps : sweep opposé H1/H4 récent = PRUDENCE | — | Règle proposée, non fournie par l'utilisateur | E6 `SWEEP_LOG_ONLY` |
| H6 | Origine de l'impulsion = plus bas entre le swing cassé et la barre de BOS | — | Fixe le 100 % de l'OTE | — |
| H7 | ⚠ Fin de l'impulsion = premier swing confirmé après le BOS | `SWING_CONFIRM` | Le setup n'existe qu'après le début du retracement | E6 `BOS_BAR` |
| H8 | OB = dernière bougie de couleur opposée avant le FVG du déplacement (≤ 5 barres avant, ≤ 2 barres avant l'origine) | WICK | Définit la zone d'entrée | `ObZoneMode=BODY`, tests |
| H9 | Premier couple (FVG, OB) chronologique dont l'OB recoupe l'OTE | — | — | — |
| H10 | Un FVG comblé par le retracement est normal ; seule une **clôture au-delà** de son bord distal le rend invalide | — | — | — |
| H11 | ⚠ Setup abandonné si le prix a déjà touché l'entrée avant que l'ordre puisse être placé (mesuré sur le Bid) | `true` | Écarte les « seconds contacts » | `RejectIfTouched=false` |
| H12 | Buffer SL = max(points, 0,10 × ATR) ; spread ajouté au SL des ventes | 0,10 ATR | Distance du SL | E6 `SL_BUFFER_025` |
| H13 | SL minimum = 3 × spread | 3 | Évite des stops dans le bruit du spread | — |
| H14 | ⚠ Invalidation par continuation = clôture au-delà de l'extrême de l'impulsion | `CLOSE` | Annule les ordres quand le marché repart sans retracer | E6 `INV_WICK` |
| H15 | Annulation de l'ordre si le biais H4/H1 n'est plus compatible | `true` | — | — |
| H16 | Toutes les invalidations sont évaluées à la clôture des barres (pas en intrabarre) | — | Parité EA/recherche | — |
| H17 | Un seul setup actif par direction ; un nouveau setup valide remplace l'ancien non exécuté | — | — | — |
| H18 | Méthode A : sortie à la première cassure opposée de l'UT d'entrée après la partielle | — | — | E2 |
| H19 | Méthode B : TP = premier niveau de liquidité H1 actif au-delà de +3R, figé à la confirmation ; sinon 6R | H1, 6R | — | E2 |
| H20 | Méthode D : SL derrière chaque nouveau swing confirmé de l'UT d'entrée (− 0,10 ATR), seulement s'il se resserre | 0,10 ATR | — | E2 |
| H21 | Limites de compte : 2 positions/ordres max, 2 % de risque total ouvert, perte journalière 3 % | — | Valeurs prudentes | — |
| H22 | Heure serveur UTC+2/+3 (New-York close) pour la recherche | — | Forme des barres H4, coupure journalière | Vérifier chez le broker |
| H23 | Ambiguïtés intra-minute du simulateur tranchées contre la stratégie | — | Résultats plutôt pessimistes | Comparer avec le Strategy Tester en ticks réels |
| H24 | Remplissage partiel d'un ordre limite : le reliquat est annulé | `true` | Risque effectif ≤ nominal | — |
| H25 | Compte netting : une seule position/ordre à la fois | — | Évite la fusion de positions | — |

## C. Paramètres restant à confirmer par l'utilisateur [C]

| # | Paramètre | Valeur provisoire | Question à l'utilisateur |
|---|-----------|-------------------|--------------------------|
| C1 | ⚠ UT d'entrée | M15 (M5 comparé) | Utilisez-vous M5 et M15 indifféremment, ou l'un selon un critère ? |
| C2 | ⚠ UT du RSI | UT d'entrée | Sur quelle UT lisez-vous le RSI (M5, M15, H1) ? |
| C3 | Moment du contrôle RSI | `AT_SETUP` | Refusez-vous définitivement le setup, ou attendez-vous que le RSI redevienne neutre ? |
| C4 | ⚠ Profondeur d'entrée dans OB ∩ OTE | 0,5 | Bord proximal, milieu, bord distal, ou autre (ex. 50 % de l'OB) ? |
| C5 | Fenêtres de swings | 3/3 (H1/H4), 2/2 (entrée) | Quelle « taille » de swing considérez-vous comme structurelle ? |
| C6 | Mode après CHoCH | `FLIP_ON_CHOCH` | Un CHoCH suffit-il à changer le biais, ou attendez-vous un BOS de confirmation ? |
| C7 | Action sur sweep opposé | `BLOCK` | Un sweep de la liquidité dans votre sens sur H1/H4 vous fait-il renoncer ? |
| C8 | Buffer SL | 0,10 ATR | Quelle marge mettez-vous sous/sur l'OB ? |
| C9 | Repli si 50 % impossible | `CLOSE_ALL` | Avec le lot minimal, préférez-vous tout clôturer à +3R ou tout laisser courir ? |
| C10 | Capital de référence | min(balance, equity) | Balance, equity, ou capital fixe ? |
| C11 | Spread maximal | désactivé | Quel spread maximal acceptez-vous à l'envoi de l'ordre ? |
| C12 | Fenêtre de liquidité méthode B | H1 | Quelles zones de liquidité visez-vous (H1, H4, plus hauts/bas du jour) ? |
| C13 | Filtre d'annonces | désactivé | Évitez-vous certaines annonces (NFP, CPI, FOMC) ? Combien de minutes ? |
