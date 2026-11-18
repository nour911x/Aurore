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

## Feature flags

Dans `config/features.py`. Un module désactivé n'apparaît pas dans l'interface, mais son code reste en place.

| Flag | Défaut | Rôle |
|---|---|---|
| `INSTAGRAM_FEEDBACK` | `False` | Publication Instagram et avis transformés en posts |
| `PINTEREST_MOODBOARD_AUTO` | `False` | Liens Pinterest générés pour le moodboard |
| `DIGITAL_EVENT_REPRESENTATION` | `False` | Salle en 3D |
| `WHATSAPP_AUTO_SEND` | `False` | Réservé : aucun envoi automatique n'existe et ce flag doit rester à `False` |
| `VENDOR_RECOMMENDATIONS` | `False` | Recommandations de boutiques et de maquilleurs |
| `CLIENT_PORTAL` | `True` | Vue Clients (lecture seule) |
| `VENDOR_PORTAL` | `True` | Vue Prestataire (lecture seule) |

## Lancer le projet

Prérequis : Python 3.12 ou plus récent.

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur http://localhost:8501. Au tout premier lancement, des données de démonstration sont créées (un mariage, un anniversaire, une baby shower, datés à partir d'aujourd'hui) pour que l'accueil soit rempli. Elles se retirent et se remettent depuis **Accueil › Données de démonstration**, sans toucher à vos propres données.

## Variables d'environnement

À mettre dans un fichier `.env` à la racine. Il est ignoré par git.

| Variable | Obligatoire | Rôle |
|---|---|---|
| `GROQ_KEY` | oui | Clé de l'API Groq (chat, vision, transcription audio) |
| `OUTLOOK_ACCOUNT` | non | Compte Outlook à utiliser pour synchroniser l'agenda (Windows, Outlook installé) |

Aucune clé n'est écrite dans le code.

## Tests

```powershell
pytest
```

Les tests couvrent la logique métier : conflits de calendrier, budget et devis, normalisation des noms, statuts des messages, règles RGPD, accueil sur les données de démonstration. Ils n'écrivent que dans des dossiers temporaires.

## Structure

```
app.py                point d'entrée Streamlit
textes.py             libellés de l'interface, noms propres, pluriels
config/               evenements.py (types et champs par type), features.py (flags)
ui/                   un module par onglet, composants partagés, habillage HTML/CSS
metier/               agenda, budget, devis, messages, invités, galerie, jour J, accueil, RGPD
donnees/              stockage JSON, dossiers clients, fiche, données de démonstration
llm/                  agent Groq, outils de l'agent, Outlook, prompt système
assets/               feuille de style, salle 3D
tests/                tests unitaires (pytest)
dossiers/             données des clients, un sous-dossier par client (créé au lancement, ignoré par git)
```

À la racine, `agenda_data.json` (agenda commun), `annuaire_prestataires.json` (carnet commun) et `aurore_etat.json` (migrations déjà faites, démo) sont créés au lancement et ignorés par git. Les migrations des anciennes données (dossier unique, carnets par dossier, noms) se font automatiquement.
