# Déploiement sur VPS

## 1. Pourquoi un VPS

Le SL (et le TP des méthodes B/C) est enregistré **chez le serveur** du broker : il protège la position
même si le terminal est arrêté. En revanche **le passage au break-even, la prise partielle à +3R, la
sortie A (structure) et le stop suiveur D sont exécutés par l'EA** : ils n'ont lieu que si le terminal
tourne et est connecté. Un VPS proche du serveur du broker réduit aussi la latence.

## 2. Choix

- Windows Server 2019/2022 (ou le VPS intégré MetaQuotes : *Outils → Hébergement virtuel*, qui migre
  l'EA et ses paramètres ; vérifier dans ce cas l'accès aux fichiers `Common\Files`, non garanti).
- Localisation proche du serveur de trading (ping < 10–20 ms).
- 2 vCPU, 4 Go RAM suffisent pour un terminal.

## 3. Installation

1. Installer MT5 du broker, se connecter au compte (démo d'abord).
2. Copier et compiler les fichiers (`Docs/INSTALL_MT5.md`), exécuter `SensitorTests` (90/90 requis).
3. *Outils → Options → Expert Advisors* : autoriser le trading algorithmique ; désactiver « Désactiver le
   trading algorithmique lors du changement de compte/profil » selon vos préférences.
4. Attacher l'EA sur un seul graphique du symbole, avec un **magic number unique** par instance.
5. Désactiver la mise en veille et les redémarrages automatiques Windows Update aux heures de marché ;
   placer MT5 en démarrage automatique (raccourci dans `shell:startup`) avec le profil sauvegardé, de
   sorte que l'EA soit rechargé après un redémarrage.

## 4. Reprise après incident (comportement de l'EA)

- Au redémarrage, l'EA rejoue les dernières barres clôturées (résultat déterministe), rattache les ordres
  existants aux setups actifs, **annule les ordres orphelins**, reconstruit chaque position (volume
  initial, SL initial, BE, partielle) depuis l'historique MT5 et le fichier d'état, puis reprend la
  gestion. Un setup déjà envoyé n'est jamais renvoyé.
- Pendant une déconnexion : les SL/TP serveur restent actifs ; si +1R ou +3R est franchi pendant la
  coupure, l'EA applique BE puis partielle au premier tick après reconnexion (si le prix est encore
  au-delà du niveau ; sinon l'opportunité est perdue — limite documentée).
- `ERROR_SAFE` persiste après redémarrage tant qu'un humain ne l'a pas levé (`InpClearErrorSafe=true`).

## 5. Surveillance

- `Common\Files\SensitorAI\<symbole>_<magic>_heartbeat.txt` est réécrit chaque minute
  (heure locale, heure serveur, état, connexion, nombre de positions).
- `Tools/watchdog.ps1` (PowerShell, tâche planifiée toutes les 5 min) alerte si le battement de cœur a
  plus de 5 minutes ou si l'état est `ERROR_SAFE`, et peut relancer le terminal.
- Consulter quotidiennement `errors.csv` et `events.csv`. Activer les notifications push MT5 si souhaité.

## 6. Sécurité

- Mot de passe *investisseur* pour toute surveillance à distance ; ne jamais partager le mot de passe
  maître.
- Sauvegarder `Common\Files\SensitorAI\` (journaux, état) hors du VPS.
- Ne pas exécuter plusieurs instances avec le même magic number sur le même compte.
