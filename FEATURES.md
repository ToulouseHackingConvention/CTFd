# Features

vim: set spell spelllang=fr:

## Spécifications pour la plateforme web
- [x] La plateforme web devra comprendre deux interfaces distinctes:
  - [x] Interface joueur
  - [x] Interface organisateur
- [ ] L'interface devra être testée sur plusieurs navigateurs
  - [ ] Sur Chrome et Firefox l'interface devra être conforme aux attentes de design
  - [ ] Sur les autres navigateurs seul le côté fonctionnel sera nécessaire
- [X] L'interface joueur devra être suffisamment modulaire pour permettre à une autre team de modifier le design.

## Interface joueur
L'interface joueur proposera les fonctionnalités suivantes :
- Si non authentifié
  - [x] Une page pour l'enregistrement d'une nouvelle équipe participante
- Si authentifié
  - [x] Une page contenant la liste des challenges
  - [ ] Une page de soumission des flags
  - [x] Une page de classement des équipes

### Enregistrement - Accès anonyme
- [x] Les utilisateurs anonymes pourront créer une team avec comme information:
  - [x] Nom de team (sanitisé)
  - [x] Mot de passe
  - [ ] Pays (avec drapeau)
- [x] L'ensemble des membres d'une équipe utilisera le même identifiant commun à toute l'équipe.

### Liste des challenges - Accès authentifié seulement
- [x] L'ensemble des challenges sera disponible aux joueurs dès le début de la partie.
- [x] Pour chaque challenge devra être visible
  - [x] Le nombre d'équipes ayant résolu le challenge
  - [x] Le détail du nombre de points que donnera la résolution (base fixe+bonus dynamique)
  - [x] Un utilisateur d'une équipe devra pouvoir identifier visuellement qu'un challenge a déjà été résolu par son équipe.
  - [ ] La mention « désactivé » le cas échéant
  - [x] Une description
- [x] Sur la page de la liste des challenges, un espace unique devra être utilisé pour communiquer les indices aux participants
- [x] 1 challenge = 1 flag, pour les challenges imbriqués, on aura plusieurs challenges et plusieurs flags
- [ ] Si possible, les joueurs devront pouvoir donner une note (de 0 à 5 étoiles) à un challenge qu'ils auront résolus. La note est non visible des autre participants

### Soumission des flags - Accès authentifié seulement
- [ ] Un champ unique de saisie sera proposé, sur une page dédiée
- [x] Le format de flag autorisé devra être THCon{[a-zA-Z0-9\_]+}
- [x] La valeur de ce champ sera strippé des espaces à gauche et à droite.
- [x] La valeur de ce champ sera lower-casé.
- [X] La taille minimale du flag devra être de 20 caractères, et la taille maximale de 512 caractères.
- [ ] Le flag sera stocké sous forme de hash (ex: PBKDF2) et la soumission sera donc hashé puis comparé avec les valeurs en base de données.
- [x] La soumission de flags devra être limité à 1 soumission par seconde par équipe.
- [x] Un grand soin devra être apporté au code implémentant la logique de vérification du flag, afin d'éviter les races conditions et la soumission multiple (des contraintes peuvent être directement intégrés dans la base de données pour garantir au maximum la cohérence des données.)
- [ ] Le scoring de la résolution d'un challenge devra suivre la logique suivante:
  - [ ] (points fixe) + (points dynamiques) (dynamique = +3,+2,+1,+0, pour les breakthrough)
  - [x] Les points scorés une fois ne bougent pas, on ne perd pas de points au cours du temps.

### Classement - Accès authentifié seulement
- [ ] Le classement devra afficher les informations suivantes, dans l'ordre décroissant du nombre de points:
  - [x] Team Name
  - [ ] Pays/Drapeau
  - [x] Score
- [ ] A noter que le classement pourra être masqué par les organisateurs.
- [ ] Si possible, la page de classement devra être dynamique et se mettre à jour sans action de l'utilisateur.
- [ ] Le classement ne permettra pas de voir le détail des challenges résolus par une équipe concurrente.

## Interface organisateur - Accès administrateur seulement
- [x] L'interface organisateur sera uniquement accessible après authentification.
- [x] Si possible, l'interface organisateur sera découplé de l'interface joueur.

L'interface organisateur devrait proposer les fonctionnalités suivantes:
- [x] Ajout/suppresion d'un flag/challenge: Permet d'ajouter/supprimer un flag d'un challenge de l'ensemble des flags valides, permet de préciser le nombre de points de base offert par le challenge + le nombre de points dynamiques et K
- [X] Monitoring des soumissions de flags: heure, IP source, nom de l'équipe d'origine (sanitisé), valeur flag (sanitisée)
  - [X] Si la valeur du flag soumise n'a pas matché avec le hash d'un flag existant, l'indiquer en clair (afin de pouvoir guider des participants s'il y a un souci avec un challenge)
  - [X] Si la valeur du flag soumise a matché avec le hash d'un flag existant, indiquer à quel challenge cela correspond.

- [ ] Ajout/suppression des indices: Permet d'ajouter/supprimer des indices, permet d'indiquer le challenge concerné
- [x] Possibilité d'ajouter/enlever des points aux équipes: avec traçabilité
- [x] Possibilité de désactiver un challenge
- [x] Possibilité de modifier la description d'un challenge
- [ ] Possibilité de masquer le scoreboard(classement) aux joueurs
- [ ] Visualisation des notes/feedback des joueurs sur les challenges
- [ ] Monitoring de l'état des challenges (dans la mesure du possible): utiliser le script de résolution/monitoring fourni par les auteurs
- [x] Gestion des teams password reset/détail des challenges résolus avec heure et points


# Hébergement et déploiement

- [ ] Afin de garantir une traçabilité, l'infrastructure devra être architecturée de manière à pouvoir identifier de quelle équipe proviennent les requêtes (ex: VLAN et sous-réseau par équipe)
- [ ] Les 2 interfaces seront proposées uniquement à travers HTTPS sur IPv4, avec un certificat valide.
