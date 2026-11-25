# AURORE

**Vos événements, organisés de bout en bout.**

AURORE est un assistant pour les organisateurs d'événements : wedding planners, mais aussi organisateurs de baby showers, d'anniversaires, d'EVJF, de fiançailles ou de crémaillères. L'application rassemble au même endroit les dossiers clients, le calendrier, les prestataires, le budget, les devis, les invités et les messages. Une IA (Groq) prépare le travail, et l'organisateur garde toujours la main.

Application Streamlit, en Python.

## Fonctionnalités

### Vue Organisateur

| Onglet | Ce qu'on y fait |
|---|---|
| **Accueil** | La journée sur tous les dossiers : rendez-vous du jour, choses à faire (messages à valider, relances, confirmations attendues, champs encore « À définir » à J-45 et moins), paiements en retard ou à 7 jours, dossiers à surveiller, conflits d'agenda et prestataires réservés deux fois le même jour. Chaque ligne ouvre le bon dossier. |
| **Messages** | La discussion avec AURORE et les messages à préparer, relire, valider puis envoyer. |
| **Fiche client** | Les champs du dossier selon le type d'événement, les consentements RGPD, l'historique des échanges, l'export et la suppression des données. |
| **Planning** | Les rendez-vous, avec type, confirmation et briefing automatique dans les 24 h ; le déroulé du jour J ; le plan de salle. |
| **Prestataires** | Un carnet commun à tous les dossiers. Chaque dossier y choisit ses prestataires, avec un statut (à contacter → réservé), un tarif et un poste de budget propres. Alerte si un prestataire est réservé sur deux événements le même jour. |
| **Budget & devis** | Les postes, les factures et leurs échéances ; des devis en PDF qui, une fois acceptés, créent l'acompte et le solde. |
| **Invités** | La liste, l'import de contacts avec aperçu, les faire-parts et le récapitulatif pour le traiteur. |
| **Inspiration & galerie** | Le moodboard, les photos taguées décor / avec personnes, le droit à l'image, les avis. |

La barre latérale permet de changer de dossier et d'en créer un nouveau (Mariage, Baby shower, Anniversaire ou Autre). Changer le type d'un dossier demande une confirmation : les champs propres à l'ancien type sont masqués, pas supprimés. La zone de saisie en bas de page comprend le langage naturel : « ajoute une dégustation jeudi 14h ».

### Vues partagées, en lecture seule

- **Clients** : le récap du dossier, les prochains rendez-vous, le suivi du budget et des factures, les invitations.
- **Prestataire** : ses rendez-vous, ses devis et factures, et seulement les informations utiles à son métier (allergies pour le traiteur, musique pour le DJ…).

Dans ces deux vues, l'IA consulte les données mais ne modifie rien.

### Messages : toujours une validation humaine

`brouillon` → `à valider` → `validé` → `envoyé` (ou `annulé`)

Tout ce qu'AURORE rédige arrive « à valider ». Les boutons WhatsApp et email n'apparaissent que sur un message validé : ils ouvrent l'application avec le texte prérempli, et c'est l'organisateur qui envoie. Chaque envoi est ajouté à l'historique du dossier.

### RGPD

- **Données de santé** (allergies, régimes, interdits) : consentement explicite sur le dossier. Elles ne sont partagées qu'avec le traiteur et n'entrent dans les prompts de l'IA que lorsque c'est nécessaire (dégustation, traiteur), sans les noms des invités.
- **Droit à l'image** : un consentement par personne, avec un périmètre (aucun, portfolio, réseaux sociaux) et une date. Sans consentement, seules les photos de décor sont publiables.
- **Import de contacts** : uniquement à l'initiative de l'utilisateur, après un aperçu.
- **Export JSON et suppression** de toutes les données d'un client.

## Publication Instagram

Dans **Inspiration & galerie › Instagram**, seules les photos publiables apparaissent : photos de décor, ou photos des clients avec leur consentement de droit à l'image pour les réseaux sociaux. AURORE rédige la légende, que l'organisateur relit et modifie. Dans **Avis**, un avis client devient un post témoignage : une carte carrée aux couleurs d'AURORE (citation, étoiles, auteur) et sa légende.

- **Sans configuration** : on télécharge l'image, on ouvre Instagram et on publie à la main, puis on marque le post comme publié.
- **Avec l'API** : le bouton **Publier** demande une confirmation, puis AURORE publie et garde le lien du post. L'IA ne publie jamais seule.

Pour activer l'API :

1. Passer le compte Instagram d'AURORE en compte professionnel (créateur ou entreprise).
2. Créer une application sur [developers.facebook.com](https://developers.facebook.com), ajouter le produit **Instagram** (API avec connexion Instagram) et l'autorisation `instagram_business_content_publish`.
3. Générer un jeton d'accès pour le compte, et relever son identifiant.
4. Mettre en ligne AURORE (par exemple sur Streamlit Community Cloud) : Instagram télécharge l'image à une adresse publique. L'image est déposée dans `static/publications/` le temps de la publication, puis supprimée.
5. Renseigner `INSTAGRAM_TOKEN`, `INSTAGRAM_USER_ID` et `AURORE_URL_PUBLIQUE` dans le `.env` (ou les secrets de l'hébergeur).

En local, sans adresse publique, la publication reste manuelle.

## Feature flags

Dans `config/features.py`. Un module désactivé n'apparaît pas dans l'interface, mais son code reste en place.

| Flag | Défaut | Rôle |
|---|---|---|
| `INSTAGRAM_FEEDBACK` | `True` | Publication Instagram des photos autorisées et des avis transformés en cartes témoignage |
| `PINTEREST_MOODBOARD_AUTO` | `False` | Liens Pinterest générés pour le moodboard |
| `DIGITAL_EVENT_REPRESENTATION` | `True` | Salle en 3D |
| `WHATSAPP_AUTO_SEND` | `False` | Réservé : aucun envoi automatique n'existe et ce flag doit rester à `False` |
| `VENDOR_RECOMMENDATIONS` | `False` | Recommandations de boutiques et de maquilleurs |
| `CLIENT_PORTAL` | `True` | Vue Clients (lecture seule) |
| `VENDOR_PORTAL` | `True` | Vue Prestataire (lecture seule) |

## Lancer le projet

Prérequis : Python 3.13 ou plus récent.

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python definir_mot_de_passe.py
streamlit run app.py
```

L'application s'ouvre sur http://localhost:8501. Au tout premier lancement, des données de démonstration sont créées (un mariage, un anniversaire, une baby shower, datés à partir d'aujourd'hui) pour que l'accueil soit rempli. Elles se retirent et se remettent depuis **Accueil › Données de démonstration**, sans toucher à vos propres données.

## Variables d'environnement

À mettre dans un fichier `.env` à la racine. Il est ignoré par git.

| Variable | Obligatoire | Rôle |
|---|---|---|
| `GROQ_KEY` | oui | Clé de l'API Groq (chat, vision, transcription audio) |
| `MOT_DE_PASSE_HACHE` | oui | Mot de passe organisateur haché, écrit par `python definir_mot_de_passe.py` |
| `NOM_ORGANISATEUR` | non | Nom affiché dans le menu et l'accueil |
| `AURORE_DONNEES` | non | Dossier où enregistrer les données (par défaut, celui du projet) |
| `OUTLOOK_ACCOUNT` | non | Compte Outlook à utiliser pour synchroniser l'agenda (Windows, Outlook installé) |
| `INSTAGRAM_TOKEN` | non | Jeton d'accès de l'API Instagram, pour publier depuis AURORE |
| `INSTAGRAM_USER_ID` | non | Identifiant du compte Instagram professionnel |
| `AURORE_URL_PUBLIQUE` | non | Adresse en ligne de l'application (ex. `https://aurore.streamlit.app`) : Instagram y télécharge l'image |

Aucune clé n'est écrite dans le code.

## Accès

- **Organisateur** : mot de passe. Sans mot de passe défini, l'application reste fermée.
- **Clients et prestataires** : lien privé créé dans **Fiche client › Liens privés**. Il ouvre une seule vue, sur un seul dossier, expire au bout de 90 jours et peut être révoqué. Il n'est affiché qu'une fois.

## Recherche dans les documents (RAG)

Dans **Prestataires › Documents**, l'organisateur ajoute des contrats ou devis (PDF, TXT, MD) et pose ses questions. La discussion avec AURORE y a aussi accès. Les réponses citent leurs sources et se limitent au dossier ouvert. Au premier usage, le modèle d'embedding (environ 500 Mo) est téléchargé.

1. La demande est découpée en questions atomiques.
2. Chaque question est vectorisée et comparée aux extraits du dossier (20 plus proches).
3. Le LLM ne garde que les extraits utiles.
4. Il répond uniquement à partir de ces extraits.

## Tests et qualité

```powershell
pip install -r requirements-dev.txt
pytest --cov       # tests et couverture
ruff check .       # style et erreurs courantes
mypy               # vérification des types
```

Les trois commandes sont lancées automatiquement par GitHub Actions à chaque push (`.github/workflows/qualite.yml`). Leur configuration est dans `pyproject.toml`.

Les tests couvrent la logique métier, les PDF, l'agent et ses outils, le RAG, la sécurité et chaque écran (AppTest). Ils n'écrivent que dans des dossiers temporaires et n'appellent jamais Groq. Une couverture sous 80 % fait échouer la CI.

## Structure

```
app.py                point d'entrée : connexion, puis interface
DECISIONS.md          choix techniques et leurs limites
textes.py             libellés de l'interface, noms propres, pluriels
config/               evenements.py (types et champs par type), features.py (flags), profils.py (les trois vues)
ui/                   contexte.py (état du dossier ouvert), interface.py (mise en page), une vue par page, design.py (composants), theme.css (couleurs, typographie), habillage.py (frise, plan)
metier/               agenda, budget, devis, messages, invités, galerie, jour J, accueil, RGPD
donnees/              base SQLite, reprise des anciens JSON, dossiers clients, fiche, démonstration
llm/                  agent Groq, outils de l'agent, Outlook, prompt système
llm/rag/              recherche dans les documents : extraits, base vectorielle, reclassement, prompts
exemples/             documents fictifs pour essayer la recherche (dont un piégé)
index_documents/      base vectorielle ChromaDB (créée au premier import, ignorée par git)
assets/               salle 3D
static/               photos de l'accueil
tests/                tests unitaires (pytest)
.github/workflows/     intégration continue (ruff, mypy, pytest)
dossiers/             photos et documents des clients, un sous-dossier par client (ignoré par git)
```

À la racine, `aurore.db` (base SQLite, ignorée par git) contient toutes les données, sauf les photos et les documents importés. Si la base est vide et que d'anciens fichiers JSON existent, leur contenu est repris au lancement ; ces fichiers sont conservés et ne servent plus ensuite.
