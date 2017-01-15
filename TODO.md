# TODO

Liste des changements à faire, par ordre de priorité.

## Urgent

- [X] Chaque équipe doit pouvoir choisir son pays, et le drapeau doit être affiché dans le classement
- [X] Implémenter notre système de points (point fixe + (+3/+2/+1) pour les breakthrough)
- [ ] Le format de flag doit être THCon{[a-zA-Z0-9\_]+}. Accepter le flag même si l'utilisateur ne donne que ce qu'il y a dans les accolades.
- [ ] Ajouter un système d'announcement, qui permettra aussi de communiquer les indices

## Tests

- [ ] Tester la plateforme sur plusieurs navigateurs:
  - [ ] Sur Chrome et Firefox, l'interface devra être conforme aux attentes de design
  - [ ] Sur les autres navigateurs, seul le côté fonctionnel sera nécessaire

## Optionnel

- [ ] Ajouter un champ de soumission des flags global (non spécifique à un challenge)
- [ ] Le classement doit pouvoir être masqué ou figé par les organisateurs
- [ ] On doit pouvoir ajouter une mention « down » à un challenge. Facultatif, puisqu'il suffirait de renommer le challenge avec un tag [DOWN] et/ou de modifier la description.
- [ ] Les joueurs doivent pouvoir donner une note (de 0 à 5 étoiles) à un challenge qu'ils auront résolus. La note est non visible des autre participants
- [ ] Stocker les flags sous forme de hash (ex: PBKDF2)
- [ ] La page de classement devra être dynamique et se mettre à jour sans action de l'utilisateur.
