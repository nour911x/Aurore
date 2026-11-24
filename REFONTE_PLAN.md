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

## Arbitrages rendus (18/11/2026)
- **Vrai multi-dossiers.** Un dossier par client dans `dossiers/<id>/` (fiche, budget, devis, invités, messages, galerie, jour J, inspiration, carnet de prestataires). Un sélecteur « Dossier » et un bouton « Nouveau dossier » dans la barre latérale. **L'agenda est commun** à l'organisateur : chaque rendez-vous porte un `dossier_id`, ce qui permet de détecter les conflits entre clients. Le carnet de prestataires a d'abord été rangé par dossier (phase 1), puis rendu commun à tous les dossiers dans les finitions (voir la dernière section). Les données de la racine sont migrées automatiquement dans un premier dossier au lancement. Ce socle est construit au début de la phase 1, car le flux « Nouveau dossier » en dépend.
- **Base git** : la PR de `feature/jour-j` est fusionnée dans `main` d'abord, les branches `feature/refonte-*` partent de `main`.
- **Phase 7** : réorganisation complète en dossiers `config/`, `ui/`, `metier/`, `donnees/`, `llm/`.

---

## Fichiers concernés par phase

Cette liste date d'avant la phase 7 et cite donc les fichiers à leur ancien emplacement. Correspondance avec la structure actuelle :

| Avant | Aujourd'hui |
|---|---|
| `user_interface.py` | `app.py` et un module par onglet dans `ui/` (`ui/commun.py` pour les constantes et fonctions partagées) |
| `habillage.py` | `ui/habillage.py` |
| `storage.py`, `dossiers.py`, `event_state.py`, `demo.py` | `donnees/` |
| `agenda.py`, `budget.py`, `devis.py`, `messages.py`, `invites.py`, `galerie.py`, `jour_j.py`, `accueil.py`, `rgpd.py`, `prestataires.py`, `inspiration.py` | `metier/` |
| `llm_agent.py`, `outils.py`, `outlook.py`, `context.txt` | `llm/` |

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
- `outils.py` : `preparer_message` enregistre le message « à valider », il n'envoie jamais rien

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
- **Carnet de prestataires par dossier** (et non commun comme prévu au départ) : le statut d'un prestataire (« Devis demandé », « Réservé »…) dépend de l'événement. Seul l'agenda est commun à tous les dossiers. *Décision revue dans les finitions : carnet commun, et statut, tarif et poste propres à chaque dossier.*
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

### Phase 3
- **L'accueil regroupe tous les dossiers** (`accueil.synthese`) : un organisateur voit sa journée entière, pas seulement le dossier ouvert. Chaque ligne a un bouton « Ouvrir le dossier » qui sélectionne le dossier et ouvre le bon onglet.
- **Fenêtre de surveillance à J-45** (constante `JOURS_SURVEILLANCE` dans `metier/accueil.py`) et non J-30 : l'exemple du brief (« lieu non défini à J-32 = alerte ») sortait de la fenêtre à 30 jours.
- **Paiements** : une facture du poste « Organisation » est « à encaisser auprès du client », toutes les autres sont « à régler au prestataire ». Sont affichées les factures en retard et celles dont l'échéance tombe dans les 7 jours.
- **À faire** : pour chaque dossier, les messages prêts à valider, les relances, les messages à préparer et les confirmations de rendez-vous attendues (rendez-vous avec un interlocuteur, dans les 7 jours, non confirmés). Le bouton « Confirmé » valide un rendez-vous sans quitter l'accueil.
- **Rendez-vous** : nouveaux champs `type` (Essayage, Visite, Dégustation, Réunion, Appel, Autre ; deviné depuis le titre si rien n'est choisi) et `confirme`. Les anciens rendez-vous fonctionnent sans migration.
- **Conflits** : l'ajout reste refusé en cas de chevauchement, mais l'accueil détecte aussi ceux qui existent déjà dans le fichier (anciennes données, imports).
- **Données de démonstration à la demande** (`donnees/demo.py`) : trois dossiers fictifs marqués `"demo": true`, datés à partir du jour courant. Ils s'ajoutent et se retirent depuis l'accueil, et ne sont jamais créés automatiquement, pour ne pas mélanger des données fictives à tes vrais dossiers.
- **Vue Clients** : l'accueil garde la salutation et les raccourcis. La vue partagée en lecture seule arrive en phase 4.
- **Chat** : la zone de saisie reste en bas de page, et les raccourcis sont sous l'accueil. Le dernier échange s'affiche sous l'accueil, la discussion complète est dans Messages.

### Phase 4
- **Flags dans `config/features.py`.** Chaque section liée à un flag est retirée des onglets (`SECTIONS_ACTIVES` dans `ui/commun.py`), mais son code reste en place : repasser le flag à `True` suffit à la réafficher.
  - `INSTAGRAM_FEEDBACK` : sous-onglet Instagram et bouton « Transformer en post témoignage ». La saisie des avis reste, et elle se fait maintenant côté organisateur (« Enregistrer un avis reçu »).
  - `PINTEREST_MOODBOARD_AUTO` : liens Pinterest du moodboard, dans l'écran, le PDF et le message d'envoi.
  - `DIGITAL_EVENT_REPRESENTATION` : sous-onglet « Salle en 3D ». Le plan de salle reste.
  - `VENDOR_RECOMMENDATIONS` : sous-onglet « Boutiques & beauté ».
  - `WHATSAPP_AUTO_SEND` : aucun code d'envoi automatique n'existe. Les boutons WhatsApp ouvrent un lien que l'organisateur clique lui-même. Un test vérifie que le flag reste à `False`.
  - `CLIENT_PORTAL` / `VENDOR_PORTAL` : affichent ou masquent les vues Clients et Prestataire dans le sélecteur.
- **Vue Clients, en lecture seule** : Notre événement (récap et prochains rendez-vous), Budget (postes et factures, sans bouton « Marquer payée »), Invitations (compteurs, liste sans coordonnées, texte du faire-part), Discussion. Aucun formulaire. Le chat n'utilise que des outils `consulter_*`, et il ne remplit plus la fiche (l'extraction automatique est réservée à l'organisateur). Le droit à l'image n'est plus accordé par un bouton côté client : il sera saisi par l'organisateur sur le dossier (phase 6).
- **Vue Prestataire, en lecture seule** : Discussion, L'événement, Mes rendez-vous (sans formulaire ni suppression), Devis & factures (ses devis et les factures du budget liées à sa prestation). Ce qu'il voit dépend de son métier (`INFOS_PAR_CATEGORIE`) : allergies, invités et tables pour le traiteur, musique pour le DJ, couverts pour la salle. Le même filtre s'applique au dossier dans la barre latérale. L'onglet « Achats & factures » du prestataire est retiré de la vue, mais le code reste.
- **Briefing automatique (brique 1)** : pour l'organisateur, chaque rendez-vous dans les 24 h reçoit un briefing généré à l'ouverture du Planning. Il est enregistré avec le rendez-vous et affiché aussi sur l'accueil. La version prestataire est générée à la demande, avec ses données filtrées, et n'est jamais enregistrée, pour qu'elle ne remplace pas celle de l'organisateur (qui contient le budget).
- **Démo enrichie** : une fleuriste au statut « Devis reçu » avec un devis envoyé, pour tester la brique 4 (devis accepté → acompte et solde au budget → prestataire réservé → paiement sur l'accueil). Vérifié de bout en bout.

### Phase 5
- **Signification des statuts**, définis dans `metier/messages.py` avec leurs transitions :
  - `brouillon` : texte écrit ou remis en chantier par l'organisateur, librement modifiable ;
  - `à valider` : texte prêt à relire ; c'est là qu'arrive tout ce qu'AURORE rédige (suggestion, message libre, chat) ;
  - `validé` : approuvé, le texte est verrouillé et les boutons WhatsApp / email apparaissent ;
  - `envoyé` : l'organisateur a cliqué « Marquer comme envoyé » après avoir envoyé le message lui-même ;
  - `annulé` : abandonné.
  - `envoyé` et `annulé` sont définitifs. On ne peut pas passer à `envoyé` sans être passé par `validé`, et un message validé doit repasser en brouillon pour être modifié. Ces règles sont dans `Messagerie`, pas seulement dans l'interface, et sont couvertes par les tests.
- **Aucun envoi automatique** : les boutons d'envoi ouvrent WhatsApp ou la messagerie avec le texte prérempli, et n'apparaissent que sur un message validé. L'outil `preparer_message` de l'IA enregistre toujours « à valider », et sa description dit explicitement à l'IA qu'il n'envoie rien.
- **Message libre** : deux choix, « Rédiger avec AURORE » (→ à valider) ou « Garder mon texte en brouillon » (→ brouillon).
- **Historique** : chaque message garde la liste de ses changements de statut avec leur date. Les envois sont aussi ajoutés à l'historique du dossier, que lit le briefing. Les messages envoyés et annulés restent consultables dans Messages.
- **Migration** : les anciens `à envoyer` deviennent `à valider`, les anciens `ignoré` deviennent `annulé`.
- **Faire-parts** : même principe. Le texte doit être validé avant que les liens d'envoi par invité apparaissent, et le modifier annule la validation.
- **Notifications conservées** : la bannière et l'accueil distinguent « à préparer », « à valider » et « validés à envoyer ».

### Phase 6
- **Données de santé** (`metier/rgpd.py`) : le champ `allergies_interdits` de la fiche, et les régimes et allergies des invités. Les régimes halal et casher révèlent une conviction religieuse, une autre catégorie particulière du RGPD : ils suivent donc la même règle.
  - **Consentement explicite** sur le dossier (Fiche client › Consentements), avec sa date. Seul l'organisateur peut le modifier, jamais l'IA : `consentement_sante` et `droit_image` sont des champs protégés dans `EventSheet.update`.
  - **Partage limité** : seul un prestataire de catégorie « Traiteur » reçoit ces données, et seulement avec le consentement. C'est vrai dans sa vue, dans la barre latérale, dans les messages qu'on lui écrit, dans son chat et dans le récapitulatif invités. Sans accord, le traiteur ne voit que le nombre de couverts, et on lui explique pourquoi.
  - **IA** : par défaut, la fiche envoyée au LLM ne contient plus les allergies (`infos_sans_historique` / `infos_pour_prestataire`, paramètre `avec_sante=False`). Exceptions : le briefing d'une dégustation ou d'un rendez-vous avec le traiteur, avec consentement. Les allergies des invités partent sans les noms (`recap_anonyme`). Le plan de table n'envoie plus les régimes, inutiles pour placer les invités.
  - **Extraction depuis le chat** : les allergies déjà connues ne sont plus envoyées au LLM. Celles qu'il trouve dans la conversation s'*ajoutent* à la liste, il ne peut plus en effacer.
  - **Journaux** : le seul `print` du projet (le bloc `__main__` de `llm/llm_agent.py`, qui affichait les réponses de l'IA en console) est supprimé. Il n'y a aucun autre log.
- **Droit à l'image** : un consentement par personne (nom, périmètre « Aucun / Portfolio / Réseaux sociaux et portfolio », date), stocké dans la fiche et géré dans Fiche client et dans Inspiration & galerie › Droit à l'image. Chaque photo a un tag `decor` / `avec_personnes`, qui découle du champ `personnes` déjà renseigné par l'analyse IA.
  - Une photo de décor est toujours publiable.
  - Une photo avec les clients est publiable seulement si **chaque** client a consenti à cet usage (portfolio ou réseaux sociaux).
  - Une photo avec des invités reconnaissables n'est jamais publiable.
  - L'ancien statut global de la galerie (« Accordé », « Refusé »…) n'est plus utilisé et n'a pas été converti : aucun dossier existant n'avait de photos.
- **Import de contacts** : aperçu obligatoire (nombre de contacts, doublons ignorés, tableau nom / téléphone / email), puis bouton explicite « Importer N contacts ». Seuls ces trois champs sont repris.
- **Export / suppression** (Fiche client › Données personnelles) : export JSON de tous les fichiers du dossier, de ses rendez-vous et de la liste de ses photos (les images elles-mêmes ne sont pas dans le JSON). La suppression est définitive : dossier, photos et rendez-vous. Elle demande de cocher une case de confirmation qui reprend le nom du dossier.
- **Clés API** : aucune clé dans le code, les prompts ou la documentation. `GROQ_KEY` est lue depuis l'environnement (`.env`, ignoré par git) et `OUTLOOK_ACCOUNT` est optionnelle. `GEMINI_KEY` est présente dans `.env` mais n'est utilisée nulle part : à retirer si elle ne sert plus.

### Phase 7
- **Arborescence** : `app.py` (point d'entrée), `config/`, `ui/`, `metier/`, `donnees/`, `llm/`, `textes.py`, `tests/`. La commande de lancement devient `streamlit run app.py`.
- **Découpage de l'interface** : chaque onglet est une classe « vue » dans `ui/`, et `UserInterface` (dans `app.py`) en hérite. Les corps des méthodes n'ont pas changé, ce qui limite le risque de régression. Les imports de chaque module ont été recalculés automatiquement à partir des noms réellement utilisés, puis vérifiés : aucun import inutile.
- **Logique métier sortie de l'interface** : résumé du budget, enveloppe d'un poste, factures d'un prestataire et enregistrement d'un devis accepté sont maintenant des méthodes de `Budget` (`metier/budget.py`), testées.
- **Chemins** : les classes n'ont plus de chemin de fichier par défaut (`"./budget_data.json"`…), qui risquait de recréer des fichiers à la racine. `context.txt` est dans `llm/` et se lit par un chemin absolu.
- **Textes** : les libellés structurants sont dans `textes.py` : onglets, sections, vues, raccourcis, titres d'accueil, baseline, avertissement, messages d'erreur de l'IA, libellés de champs. Les libellés ponctuels (boutons, aides) restent dans les modules `ui/`. Pour une version anglaise, il restera à les y déplacer un par un.
- **Avertissement conservé** : « AURORE peut se tromper : vérifiez les montants et les dates importantes. »
- **README** réécrit : produit, vues, flags, lancement, variables d'environnement, tests, structure.

---

## Finitions (branche `feature/refonte-finitions`)

### Prestataires : retour sur la décision de la phase 1
- **Carnet commun à tous les dossiers** (`annuaire_prestataires.json` à la racine, classe `Annuaire` dans `metier/prestataires.py`) : la fiche d'un prestataire (nom, catégorie, contact, téléphone, email, site, notes) n'existe qu'une fois.
- **Sélection par dossier** (`dossiers/<id>/selection_prestataires.json`, classe `Carnet`) : chaque dossier choisit ses prestataires et garde ses propres statut, date de statut, tarif et poste de budget. `Carnet` renvoie des fiches fusionnées avec les mêmes clés qu'avant : le reste du code (messages, devis, agent, vues partagées) n'a pas changé.
- **Retirer un prestataire d'un dossier** ne le supprime pas du carnet commun. On peut ensuite le rechoisir depuis « Choisir dans le carnet commun ».
- **Double réservation** : un prestataire « Réservé » sur deux dossiers dont l'événement tombe le même jour apparaît dans Accueil › Conflits, et en alerte sur sa carte dans les autres dossiers concernés.
- **Migration** (`migrer_carnets`, au lancement) : chaque ancien `prestataires_data.json` est versé dans l'annuaire puis supprimé. Deux fiches sont fusionnées si elles ont le même nom (casse et apostrophes ignorées) et aucun téléphone ni email contradictoire ; les champs vides sont complétés par l'autre fiche. Les identifiants fusionnés sont mis à jour dans les messages et les devis du dossier. Le statut et le tarif de chaque dossier sont conservés.
- **Une seule instance de l'annuaire par session**, comme pour l'agenda, pour que deux dossiers ne s'écrasent pas.

### Autres décisions
- **Démo** (`donnees/demo.py`) : le mariage est le dossier existant « Léa et Liam », complété ; l'anniversaire de Tom et la baby shower d'Inès & Malik sont créés. Tout ce que la démo ajoute à Léa & Liam (rendez-vous, facture, prestataires choisis, devis, message, postes) est marqué `"demo": true`, ce qui permet de le retirer sans toucher au reste. Le dossier lui-même n'est supprimé que s'il a été créé par la démo. Contenu :
  - un rendez-vous aujourd'hui ;
  - une facture en retard ;
  - un conflit entre deux dossiers (essayage de Léa à 15 h, visite de salle d'Inès à 15 h 30) ;
  - un DJ réservé le même jour pour le mariage et pour l'anniversaire ;
  - un lieu manquant pour Léa & Liam, à J-32.
- **Démo créée une seule fois**, au tout premier lancement (`aurore_etat.json`, clé `demo_initialisee`). Si on la retire, elle ne revient pas toute seule ; le bouton « Ajouter les données de démonstration » la remet.
- **« À définir » dans À faire** : un dossier dont l'événement est à J-45 ou moins et dont un champ essentiel est vide (date, lieu, invités, budget) apparaît dans « À faire », avec un bouton « Compléter la fiche ».
- **Changement de type** : un sélecteur demande confirmation et liste les champs qui seront masqués. Ces valeurs restent dans la fiche et réapparaissent si l'on revient au type d'origine (`EventSheet.changer_type`, `champs_masques`).
- **Noms normalisés à l'enregistrement** (`format_person_name`) : fiche, invités, consentements de droit à l'image. Migration unique des dossiers existants (`migrer_noms`, clé `noms_normalises`) : fiche, consentements, invités, avis, messages et devis adressés aux clients. Les noms de prestataires ne sont pas modifiés.
- **Sélecteur de dossier** : libellé court « Léa & Liam · 20/12 », sans titre au-dessus (le bloc « Dossier » juste en dessous suffit).
- **Dates** : tous les champs de saisie sont au format JJ/MM/AAAA (`FORMAT_DATE` dans `ui/commun.py`), ainsi que les dates affichées.
- **Montants** : `textes.montant` affiche le séparateur de milliers (« 15 000 € », « 471,60 € »). Le champ Budget de la fiche avance par pas de 500 €. Les champs de saisie Streamlit ne savent pas afficher de séparateur de milliers.
- **Accueil** : la bannière de notification n'apparaît plus sur l'accueil, puisque « À faire » en reprend le contenu. Elle reste sur les autres onglets.
- **Nouvelle conversation** : le bouton est passé de la barre latérale à la discussion (Messages › Discussion, ou Discussion dans les vues partagées). Il n'apparaît que s'il y a une conversation.
- **Pétales** : passés sous le contenu (`z-index: -1` dans la zone principale) avec une opacité réduite de moitié environ. Ils ne recouvrent plus le texte.

---

## Simplifications avant la code review

- **Indentation** : tout le projet est en espaces (PEP 8). Les 13 fichiers qui venaient de l'ancien `user_interface.py` étaient en tabulations. La conversion a été vérifiée fichier par fichier : l'arbre syntaxique est identique avant et après.
- **Imports** : rangés partout avec isort, en trois groupes (bibliothèque standard, bibliothèques externes, modules du projet), chacun trié. pyflakes ne signale plus aucun import inutile ni aucun nom non défini. Seule exception : `win32com` dans `llm/outlook.py`, importé exprès pour détecter si Outlook est installé.
- **Clés des vues** : les chaînes `"Wedding planner"`, `"Mariés"` et `"Prestataire"`, héritées de la version mariage, sont remplacées par les constantes `ORGANISATEUR`, `CLIENTS` et `PRESTATAIRE` (`config/profils.py`). Les libellés affichés et l'adresse (`?profil=Organisateur`) ne changent pas.
- **Migrations supprimées** : elles convertissaient le dossier unique, les carnets par dossier, les noms et les anciens statuts de messages. Toutes les données existantes étaient déjà converties (vérifié avant la suppression). Leurs tests sont retirés aussi.
- **Code de compatibilité de la galerie supprimé** : l'ancien statut global de droit à l'image et la conversion de la catégorie « Couple ». Le tag d'une photo n'est plus recopié dans la photo : c'est une simple fonction de `personnes` (`metier.galerie.tag`).
- **Noms normalisés à un seul endroit** : à l'enregistrement (fiche, invités, consentements). La normalisation qui était répétée à chaque affichage (barre latérale, messages, PDF, devis, avis) est retirée.
- **Vocabulaire** : `destinataire_maries` devient `destinataire_clients`.
- **Conservé volontairement** : `show_achats` (écran « Achats & factures » du prestataire, retiré de sa vue en phase 4) et `Budget.depense_du_poste`, qui ne sont plus appelés par l'interface, parce que le brief demande de ne supprimer aucune fonctionnalité sans accord. Les classes `Vue…` de `ui/` restent des classes de méthodes assemblées par héritage dans `UserInterface` : les transformer en vrais objets serait un chantier trop risqué juste avant la review.

---

## Qualité du code (`feature/qualite`)

Les sections précédentes gardent les noms de l'époque. Ce tableau donne leur équivalent actuel.

- **Tout le code est en français.** Seuls restent en anglais les noms imposés par les bibliothèques (`set_font`, `add_page`, `key=`, `data=`…), les feature flags nommés dans le brief et le fichier `event_data.json`, gardé pour ne pas déplacer les données existantes. Le renommage a été fait sur les noms de code uniquement, jamais dans les chaînes, pour ne toucher à aucune clé JSON.

  | Avant | Après |
  |---|---|
  | `donnees/storage.py`, `load_json`, `save_json` | `donnees/stockage.py`, `charger_json`, `sauvegarder_json` |
  | `donnees/event_state.py`, `EventSheet`, `event_sheet`, `.data`, `.update()` | `donnees/fiche_evenement.py`, `FicheEvenement`, `fiche_evenement`, `.donnees`, `.mettre_a_jour()` |
  | `llm/llm_agent.py`, `ConversationAgent`, `conversation_agent_object` | `llm/agent.py`, `AgentConversation`, `agent` |
  | `UserInterface`, `run()` | `InterfaceUtilisateur`, `lancer()` |
  | `load()`, `save()` dans toutes les classes | `charger()`, `sauvegarder()` |
  | `show_…`, `add_…`, `set_…`, `get_…` | `afficher_…`, `ajouter_…`, `definir_…`, `obtenir_…` |
  | `ask_llm`, `suggest_…`, `write_…`, `extract_event_info` | `demander`, `suggerer_…`, `rediger_…`, `extraire_infos_evenement` |
  | `format_person_name`, `event_data`, `file_path` | `formater_nom`, `donnees_evenement`, `chemin_fichier` |

- **Duplication supprimée** : les sept méthodes `trouver()` / `choix()` qui parcouraient une liste à la main utilisent maintenant `premier(elements, **criteres)` (`donnees/stockage.py`), par exemple `premier(self.photos, id=photo_id)`.
- **Recherche introuvable** : `Messagerie.trouver` lève une `ValueError` au lieu de renvoyer `None` puis de planter plus loin. Même règle dans la démo pour un prestataire introuvable.
- **Type hints** sur `config/`, `donnees/`, `metier/` et `textes.py`, vérifiés par mypy en mode strict sur les signatures (`disallow_untyped_defs`). Les types ont été relevés en exécutant les tests et les 23 onglets de l'app, puis complétés à la main. mypy a révélé des cas où une recherche pouvait renvoyer `None` sans vérification : ils sont tous traités.
- **Linter** : ruff (`pyproject.toml`) avec les règles pycodestyle, pyflakes, isort, bugbear, pyupgrade et simplify, et des lignes de 160 caractères maximum. Les `zip()` déclarent `strict=`, les `if` imbriqués inutiles sont fusionnés. Outlook est détecté avec `importlib.util.find_spec` au lieu d'un import inutilisé. `SIM117` (fusionner les `with`) est désactivée, parce que les blocs Streamlit imbriqués sont plus lisibles tels quels.
- **Dépendances figées** : `requirements.txt` donne les versions exactes de l'app ; `requirements-dev.txt` celles des outils (pytest, pytest-cov, ruff, mypy).
- **Intégration continue** : `.github/workflows/qualite.yml` lance ruff, mypy et pytest avec la couverture à chaque push et à chaque pull request.
- **Configuration centralisée** : `pytest.ini` est remplacé par `pyproject.toml`, qui regroupe pytest, ruff, mypy et coverage.
- **Tests** : 69 (5 nouveaux pour `donnees/stockage.py`). Couverture de 70 % sur la logique métier. Les modules à moins de 50 % (devis, galerie, inspiration, invités, jour J) sont surtout des générateurs de PDF ; ils seront traités dans `feature/finalisation`.
- **Conservé volontairement** : `afficher_achats` et `Budget.depense_du_poste` (voir la section précédente).

---

## Recherche dans les documents (`feature/rag`)

- **Pipeline du cours** (md5-my-first-rag) repris dans `llm/rag/` : `AtomicQuestionAgent` découpe la demande, `VectorDB` (ChromaDB, `distiluse-base-multilingual-cased-v2`) cherche les 20 extraits les plus proches, `RerankingAgent` garde les extraits utiles, `Rag` répond avec ses sources.
- **Différences avec le cours**, volontaires :
  - les documents sont importés dans l'app (PDF, TXT, MD) et découpés en extraits de 800 caractères au plus, au lieu d'un CSV déjà découpé ;
  - chaque extrait porte un `dossier_id` et la recherche filtre dessus : un dossier ne voit jamais les documents d'un autre ;
  - le reclassement renvoie les numéros des extraits au lieu de les recopier : moins de jetons, et un extrait ne peut pas être altéré ;
  - les extraits sont dans le message utilisateur, entre balises échappées, et non dans le prompt système ;
  - sans extrait utile, la réponse est fixe et le modèle n'est pas appelé.
- **Injection de prompt** : les textes des documents sont déclarés comme données dans les prompts, et leurs chevrons sont échappés. Surtout, après `chercher_documents`, `Outils` n'autorise plus que la lecture jusqu'au message suivant, et la fiche n'est pas mise à jour depuis cette réponse. Cette règle est dans le code, elle ne dépend pas du modèle.
- **Limite connue** : la réponse reste dans l'historique de la conversation. Au message suivant, les outils d'écriture et la mise à jour de la fiche sont de nouveau actifs, avec la seule consigne de demander confirmation. Les messages restent validés à la main.
- **Accès** : organisateur uniquement. Les vues Clients et Prestataire n'ont ni l'onglet ni l'outil.
- **RGPD** : les extraits utiles à une question sont envoyés à Groq ; l'embedding est calculé en local. Supprimer un dossier (ou la démo) efface aussi ses vecteurs (`nettoyer_index`).
- **Factorisation** : `llm/base.py` (`Agent`) regroupe le client Groq et les appels, partagés par `AgentConversation` et les agents du RAG.
- **Tests** : 84 (15 nouveaux), avec un faux modèle d'embedding et sans appel à Groq.

---

## Robustesse (`feature/robustesse`)

- **SQLite au lieu des fichiers JSON** : une base `aurore.db`, une table `contenus` (dossier, rubrique, contenu, date de modification), clé primaire (dossier, rubrique). Chaque écriture est une transaction : elle réussit entièrement ou pas du tout. `Emplacement` (racine, dossier, rubrique) remplace les chemins de fichiers dans les classes métier.
- **Choix assumé** : le contenu d'une rubrique reste du JSON dans une colonne. Les classes métier lisent et écrivent toujours une rubrique entière, et aucune recherche SQL dans le détail n'est nécessaire. Un schéma complet (une table par objet) apporterait des clés étrangères et des requêtes, au prix d'une réécriture de toutes les classes.
- **Requêtes paramétrées** : les valeurs sont passées avec `?`, jamais collées dans le SQL.
- **Suppression d'un dossier** : les rubriques et les rendez-vous partent dans la même transaction, puis les photos, les documents et les anciens JSON.
- **Reprise des JSON** (`donnees/migration.py`) : une seule fois, si la base est vide. Tous les fichiers sont lus avant la première écriture ; un fichier illisible arrête la reprise avec son nom, sans rien enregistrer. Les JSON sont conservés.
- **Groq** : délai de 30 s par essai, 3 nouvelles tentatives (client Groq). Une erreur n'arrête plus toute la page : elle s'affiche dans la section concernée.
- **Message conservé** : si l'envoi échoue, le texte et la photo sont gardés avec un bouton « Réessayer ». Un enregistrement vocal dont la transcription échoue est à refaire.
- **Pas d'action en double** : si la connexion tombe après une action (rendez-vous créé…), AURORE liste ce qui est déjà fait au lieu de proposer de tout relancer.
- **Clé absente** : message clair au lieu d'une erreur Python.
- **Limite connue** : deux fenêtres ouvertes sur le même dossier gardent chacune leur copie en mémoire ; la dernière sauvegarde l'emporte.
- **Tests** : 99 (15 nouveaux : stockage, reprise, pannes Groq).

---

## Sécurité (`feature/securite`)

- **Avant** : le choix « Organisateur / Clients / Prestataire » n'était qu'un sélecteur d'affichage. N'importe qui pouvait tout voir.
- **Mot de passe organisateur** : haché avec scrypt et un sel aléatoire, dans `.env` (`MOT_DE_PASSE_HACHE`). 12 caractères minimum. Comparaison à temps constant. 5 échecs bloquent la connexion 60 secondes. Sans mot de passe défini, l'application est fermée.
- **Liens privés** (`metier/acces.py`) : jeton aléatoire de 256 bits. Seule son empreinte SHA-256 est enregistrée, donc une copie de la base ne permet pas de reconstituer les liens. SHA-256 suffit ici, contrairement au mot de passe, parce qu'un jeton aléatoire ne peut pas être deviné.
- **Le lien décide** : la vue, le dossier et le prestataire viennent du lien enregistré, jamais de l'adresse ni de la session. Il est revérifié à chaque action. Il est refusé s'il est expiré, révoqué, si le dossier est supprimé, si le prestataire est retiré ou si la vue est désactivée (feature flags).
- **Aperçu** : l'organisateur connecté garde le sélecteur pour voir ce que voient ses clients et prestataires.
- **Erreurs** : `.streamlit/config.toml` cache les détails techniques au visiteur (ils restent dans le terminal) et limite les fichiers à 20 Mo.
- **Limites connues** : pas de durée de session, mais recharger la page (F5) déconnecte l'organisateur ; un lien partagé donne accès à qui le possède ; le blocage est commun à tous, donc quelqu'un peut retarder la connexion de l'organisateur ; les conversations des visiteurs consomment le quota Groq ; la base n'est pas chiffrée sur le disque.
- **Tests** : 115 (16 nouveaux).
