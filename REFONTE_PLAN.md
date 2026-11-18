# Refonte AURORE — plan

## État des lieux (exploration)

| Élément | Constat |
|---|---|
| Point d'entrée | `user_interface.py` (1 900 lignes) : une classe `UserInterface` qui contient toute l'UI, une partie de la logique métier et les appels LLM |
| Données | un fichier JSON par module à la racine (`event_data.json`, `agenda_data.json`, `budget_data.json`, `messages_data.json`…), via `storage.py` |
| Modèle | **un seul dossier client à la fois** : `EventSheet` lit `event_data.json`, il n'existe aucune notion de « liste de dossiers » |
| Vues | `ESPACES` dans `user_interface.py` + `PROFILS` dans `llm_agent.py` + `OUTILS_PAR_ESPACE` dans `outils.py` (clés `"Wedding planner"`, `"Mariés"`, `"Prestataire"`) |
| Messages | statuts actuels : `à envoyer`, `ignoré`, `envoyé`. Aucun envoi automatique : les boutons WhatsApp / email ouvrent un lien `wa.me` / `mailto:` que l'utilisateur clique |
| Tests | aucun |
| Streamlit | 1.67.0 installé, non épinglé dans `requirements.txt` (supporte `:material/…:` dans les onglets) |
| Git | branche courante `feature/jour-j`, **4 commits pas encore dans `main`** (déroulé, plan de salle, salle 3D) |

### WENDY
Aucune occurrence de « WENDY » dans le code, les prompts (`context.txt`) ni les assets. Rien à remplacer. En revanche `context.txt` présente l'assistante comme « AURORE (A Unique Real Organisation Running your Events) » : le backronym sera retiré là aussi.

### Clés API
Aucune clé en dur. `GROQ_KEY` est lue via `os.environ` (`llm_agent.py:59`), `.env` est bien dans `.gitignore`. `GEMINI_KEY` est présente dans `.env` mais n'est utilisée nulle part. `OUTLOOK_ACCOUNT` (optionnelle) est lue dans `outlook.py`.

### Données de santé envoyées au LLM aujourd'hui
`consignes_session` (`llm_agent.py`) injecte **toute la fiche**, allergies comprises, à chaque message du chat. Idem pour `extract_event_info`, `suggest_budget_postes`, `recommend_adresses`, `write_faire_part`, `suggest_moodboard`, `write_legende`.

---

## Fichiers concernés par phase

### Phase 1 — Positionnement multi-événements
- `dossiers.py` (nouveau) : liste des dossiers, création, dossier actif, migration des JSON de la racine
- tous les modules à fichier JSON : chemin passé par le dossier actif (ils acceptent déjà `file_path`)
- `config/evenements.py` (nouveau) : types d'événements et champs par type
- `event_state.py` : champs génériques + champs spécifiques au type (`details`)
- `habillage.py` : `ACCUEILS`, `marque_html` (baseline), `dossier_html` (lit la config)
- `user_interface.py` : libellés des vues et onglets, `show_fiche_form` générée depuis la config, cartes de type déplacées dans un `st.dialog` « Nouveau dossier »
- `llm_agent.py` : `PROFILS`, prompts qui disent « mariage »
- `outils.py`, `messages.py`, `galerie.py`, `devis.py` : textes « mariés » → « client(s) »
- `context.txt` : retrait du backronym, vocabulaire multi-événements

### Phase 2 — Interface
- `textes.py` (nouveau, amorcé ici et complété en phase 7) : `format_person_name()`, `pluriel()`
- `habillage.py`, `assets/style.css` : ancres, en-tête, largeur des onglets
- `user_interface.py` : regroupement des onglets, icônes Material, bannière cliquable
- `requirements.txt` : `streamlit>=1.67`, ajout de `groq`

### Phase 3 — Accueil « Aujourd'hui »
- `accueil.py` (nouveau, logique) : rendez-vous du jour, à faire, paiements, dossiers à surveiller, conflits
- `agenda.py` : `rdvs_du_jour()`, `conflits()` (aujourd'hui le conflit n'est vérifié qu'à l'ajout), champs `type` et `confirme` sur les rendez-vous
- `demo.py` (nouveau) : jeu de données de démonstration cohérent
- `user_interface.py` : onglet Accueil, chat + raccourcis secondaires

### Phase 4 — Feature flags et vues partagées
- `config/features.py` (nouveau)
- `user_interface.py` : masquage conditionnel, vues Clients / Prestataire en lecture seule
- `outils.py` : outils de l'agent restreints en lecture seule pour ces vues

### Phase 5 — Validation humaine des messages
- `messages.py` : statuts `brouillon → à valider → validé → envoyé (+ annulé)`, migration des anciens statuts, historique par dossier
- `user_interface.py` : boutons « Valider », « Marquer comme envoyé » actif seulement après validation
- `outils.py` : `preparer_message` crée un `brouillon`, jamais plus

### Phase 6 — RGPD
- `event_state.py` : `consentement_sante`, `droit_image` (par personne : date + périmètre)
- `messages.py`, `user_interface.py` : allergies partagées seulement avec la catégorie Traiteur
- `llm_agent.py` : fiche filtrée avant envoi au LLM (allergies retirées sauf briefing traiteur / dégustation)
- `galerie.py` : tag `avec_personnes` / `decor`, règle de publication liée au consentement
- `invites.py` : récapitulatif avant import de contacts
- `rgpd.py` (nouveau) : export JSON et suppression des données d'un client

### Phase 7 — Qualité
- Arborescence cible :
  ```
  app.py                  point d'entrée (remplace user_interface.py)
  config/                 features.py, evenements.py
  ui/                     un module par onglet
  metier/                 agenda, budget, messages, devis, invites, galerie, jour_j, accueil, rgpd
  donnees/                storage, event_state, demo
  llm/                    llm_agent, outils, outlook, context.txt
  textes.py               tous les libellés de l'interface
  tests/
  ```
- `README.md` réécrit

---

## Ordre d'exécution
1. Tests de base sur le code existant (conflits, budget) **avant** de toucher quoi que ce soit, pour détecter les régressions
2. Phases 1 → 7 dans l'ordre demandé, chacune sur sa branche, vérifiée (lancement + `pytest`) avant de passer à la suivante

Branches proposées (en regroupant ce qui va ensemble) :

| Branche | Phases |
|---|---|
| `feature/refonte-positionnement` | 1 + 2 |
| `feature/refonte-accueil` | 3 |
| `feature/refonte-perimetre-messages` | 4 + 5 |
| `feature/refonte-rgpd` | 6 |
| `feature/refonte-structure` | 7 |

---

## Risques de régression

| Risque | Parade |
|---|---|
| Renommer les clés `"Wedding planner"` / `"Mariés"` casse `ESPACES`, `PROFILS`, `OUTILS_PAR_ESPACE` et le paramètre d'URL `?profil=` | garder les clés internes, ne changer que les libellés affichés |
| Champs de dossier par type : les anciens `event_data.json` n'ont pas la nouvelle structure | migration au chargement (`load`) avec valeurs par défaut |
| `extract_event_info` remplit la fiche depuis le chat : il doit connaître les nouveaux champs | prompt généré depuis `config/evenements.py` |
| Clés de widgets Streamlit (`key=`) en double après regroupement des onglets | vérifier chaque onglet à l'écran |
| Anciens messages au statut `à envoyer` / `ignoré` | migration `à envoyer → à valider`, `ignoré → annulé` |
| Déplacement des fichiers en phase 7 : imports cassés | phase isolée, en dernier, uniquement des déplacements |
| Les 4 commits de `feature/jour-j` ne sont pas dans `main` | partir de `feature/jour-j` ou la fusionner avant (voir arbitrage) |

---

## Décisions prises
- **Noms internes conservés** (`"Wedding planner"`, `"Mariés"`, `noms`, `allergies_interdits`…) : seul l'affichage change. Plus simple et réversible.
- **Noms propres normalisés à l'affichage** uniquement, la donnée stockée n'est pas modifiée.
- **`WHATSAPP_AUTO_SEND`** : aucun envoi automatique n'existe aujourd'hui. Le flag est créé à `False` pour verrouiller, et il n'existe aucun code qui l'active.
- **« Représentation numérique de l'événement »** = la « Salle en 3D » du Jour J → `DIGITAL_EVENT_REPRESENTATION`.
- **`INSTAGRAM_FEEDBACK`** couvre le sous-onglet Instagram de la galerie et la transformation d'un avis en post. Les avis eux-mêmes restent.
- **`PINTEREST_MOODBOARD_AUTO`** masque les liens Pinterest générés ; le moodboard (palette, ambiance, PDF) reste.
- **`VENDOR_RECOMMENDATIONS`** masque le sous-onglet « Boutiques & beauté ».
- **Plan de salle** : reste visible dans Planning (ce n'est pas la 3D).
- **Commits** : je ne lance pas les commandes git, je te donne les commandes à taper à la fin de chaque phase.

### Phase 1
- **Carnet de prestataires par dossier** (et non commun comme prévu au départ) : le statut d'un prestataire (« Devis demandé », « Réservé »…) dépend de l'événement. Seul l'agenda est commun à tous les dossiers.
- **Migration** : au premier lancement, les fichiers JSON de la racine sont *déplacés* dans `dossiers/<id>/`, et les rendez-vous existants sont rattachés à ce dossier. Pour revenir en arrière, il suffit de remettre ces fichiers à la racine.
- **Champs spécifiques stockés à plat** dans la fiche (`ceremonie`, `gender_reveal`, `age`…) plutôt que dans un sous-objet : `EventSheet.update` et l'extraction par l'IA fonctionnent sans changement de structure.
- **Lieu et allergies** sont communs à tous les types (présents dans les 4 listes du brief). La musique n'est affichée que pour un mariage, comme demandé.
- **Type d'événement** : le texte libre existant (« mariage », « EVJF »…) est reconnu par mots-clés. Changer de type se fait par un sélecteur au-dessus de la fiche.
- **Sélecteur de dossier** visible uniquement dans la vue Organisateur : un client ou un prestataire ne voit pas la liste des autres clients.
- **Conflits entre dossiers** : l'organisateur voit le titre et le dossier du rendez-vous en conflit. Un client ou un prestataire voit seulement « créneau déjà pris », dans l'interface comme dans le chat.
- **URL** : le paramètre devient `?profil=Organisateur` / `?profil=Clients`. Les anciens liens `?profil=Mariés` retombent sur la vue Organisateur.
- **Catégorie photo « Couple » → « Clients »**, avec conversion automatique des photos existantes.
- **Émetteur des devis d'AURORE** : « AURORE - Organisation d'événements », et poste budgétaire « Organisation » à l'acceptation (au lieu de « Wedding planner »).
- **Émojis des onglets** : seuls les libellés changent en phase 1 ; les icônes sont unifiées en phase 2.

### Phase 2
- **Noms normalisés à l'affichage seulement** (`textes.format_person_name`) : la donnée saisie n'est jamais modifiée. Les noms de prestataires ne sont pas touchés, pour ne pas transformer « DJ SoundBox » en « Dj Soundbox ».
- **Ancres des titres** masquées en CSS, à un seul endroit (`assets/style.css`), plutôt qu'avec `anchor=False` sur chaque titre.
- **Icônes** : tous les émojis de l'interface sont remplacés par des icônes Material, sur les onglets, les boutons, les sections dépliables, les alertes et les métriques. Les pastilles de statut deviennent des icônes colorées. L'enveloppe cassée a disparu. Les titres du briefing généré par l'IA n'ont plus d'émojis.
- **8 onglets** côté Organisateur et Clients : Accueil, Messages, Fiche client, Planning, Prestataires, Budget & devis, Invités, Inspiration & galerie. Les anciens sous-onglets imbriqués (Jour J, Galerie, Inspiration) sont mis à plat pour éviter trois niveaux d'onglets.
- **Vue Prestataire** : Discussion, L'événement, Rendez-vous, Devis & achats (elle sera revue en phase 4).
- **Accueil provisoire** : salutation, raccourcis et dernier échange avec AURORE. La discussion complète est dans Messages. La phase 3 ajoute le tableau de bord.
- **Onglets « paresseux »** (`on_change="rerun"` + `.open`) : seul l'onglet affiché est calculé. La bannière ouvre directement « Messages › À préparer et à envoyer ».
- **Pluriels** : plus aucun « (s) » dans l'interface, grâce à `textes.pluriel`.
- **Rendu à 1280 px (phase 2)** : les libellés d'onglets ne passent plus à la ligne (`white-space: nowrap`). Si les onglets dépassent, Streamlit les fait défiler horizontalement. La vérification visuelle reste à faire dans le navigateur, l'extension Chrome n'étant pas connectée.

## Arbitrages rendus (18/11/2026)
- **Vrai multi-dossiers.** Un dossier par client dans `dossiers/<id>/` (fiche, budget, devis, invités, messages, galerie, jour J, inspiration). Un sélecteur « Dossier » et un bouton « Nouveau dossier » dans la barre latérale. **L'agenda et le carnet de prestataires restent communs** à l'organisateur : chaque rendez-vous porte un `dossier_id`, ce qui permet de détecter les conflits entre clients. Les données actuelles à la racine sont migrées automatiquement dans un premier dossier au lancement. Ce socle est construit au début de la phase 1, car le flux « Nouveau dossier » en dépend.
- **Base git** : la PR de `feature/jour-j` est fusionnée dans `main` d'abord, les branches `feature/refonte-*` partent de `main`.
- **Phase 7** : réorganisation complète en dossiers `config/`, `ui/`, `metier/`, `donnees/`, `llm/`.

### Phase 3
- **L'accueil regroupe tous les dossiers** (`accueil.synthese`) : un organisateur voit sa journée entière, pas seulement le dossier ouvert. Chaque ligne a un bouton « Ouvrir le dossier » qui sélectionne le dossier et ouvre le bon onglet.
- **Fenêtre de surveillance à J-45** (constante `JOURS_SURVEILLANCE` dans `accueil.py`) et non J-30 : l'exemple du brief (« lieu non défini à J-32 = alerte ») sortait de la fenêtre à 30 jours.
- **Paiements** : une facture du poste « Organisation » est « à encaisser auprès du client », toutes les autres sont « à régler au prestataire ». Sont affichées les factures en retard et celles dont l'échéance tombe dans les 7 jours.
- **À faire** : pour chaque dossier, les messages prêts à valider, les relances, les messages à préparer et les confirmations de rendez-vous attendues (rendez-vous avec un interlocuteur, dans les 7 jours, non confirmés). Le bouton « Confirmé » valide un rendez-vous sans quitter l'accueil.
- **Rendez-vous** : nouveaux champs `type` (Essayage, Visite, Dégustation, Réunion, Appel, Autre ; deviné depuis le titre si rien n'est choisi) et `confirme`. Les anciens rendez-vous fonctionnent sans migration.
- **Conflits** : l'ajout reste refusé en cas de chevauchement, mais l'accueil détecte aussi ceux qui existent déjà dans le fichier (anciennes données, imports).
- **Données de démonstration à la demande** (`demo.py`) : trois dossiers fictifs marqués `"demo": true`, datés à partir du jour courant. Ils s'ajoutent et se retirent depuis l'accueil, et ne sont jamais créés automatiquement, pour ne pas mélanger des données fictives à tes vrais dossiers.
- **Vue Clients** : l'accueil garde la salutation et les raccourcis. La vue partagée en lecture seule arrive en phase 4.
- **Chat** : la zone de saisie reste en bas de page, et les raccourcis sont sous l'accueil. Le dernier échange s'affiche sous l'accueil, la discussion complète est dans Messages.
