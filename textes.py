import re

from config.profils import CLIENTS, ORGANISATEUR, PRESTATAIRE


PARTICULES = {"de", "du", "des", "d", "la", "le", "van", "von", "der", "den", "di", "da", "del", "dos"}

LIAISONS = {"et", "and", "&"}

PREFIXES_APOSTROPHE = {"d", "l"}

BASELINE = "Vos événements, organisés de bout en bout."

AVERTISSEMENT = "AURORE peut se tromper : vérifiez les montants et les dates importantes."

ACCUEILS = {
    ORGANISATEUR: (
        "Quel événement préparez-vous pour vos clients ?",
        "Rendez-vous, prestataires, devis et invités : tout le suivi de vos clients au même endroit."
    ),
    CLIENTS: (
        "Bienvenue dans votre espace.",
        "Rendez-vous, budget et invitations : suivez la préparation de votre événement."
    ),
    PRESTATAIRE: (
        "Sur quel événement travaillez-vous ?",
        "Rendez-vous, devis et informations utiles à votre prestation."
    )
}

ERREURS_IA = {
    "RateLimitError": "AURORE a reçu trop de demandes d'un coup. Réessayez dans une minute.",
    "AuthenticationError": "La clé GROQ_KEY du fichier .env est refusée par Groq. Vérifiez-la.",
    "APIConnectionError": "AURORE n'arrive pas à joindre son serveur. Vérifiez votre connexion internet."
}

ERREUR_IA_PAR_DEFAUT = "AURORE n'a pas pu répondre. Réessayez dans un instant."

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def majuscule(mot):
    if any(lettre.isupper() for lettre in mot[1:]) and not mot.isupper():
        return mot

    return mot[:1].upper() + mot[1:].lower()


def format_mot(mot, en_tete):
    if mot.lower() in LIAISONS and not en_tete:
        return mot.lower()

    if mot.lower() in PARTICULES and not en_tete:
        return mot.lower()

    if "'" in mot or "’" in mot:
        apostrophe = "'" if "'" in mot else "’"
        prefixe, reste = mot.split(apostrophe, 1)
        prefixe = prefixe.lower() if prefixe.lower() in PREFIXES_APOSTROPHE and not en_tete else majuscule(prefixe)
        return f"{prefixe}{apostrophe}{format_mot(reste, True)}"

    return "-".join(majuscule(partie) for partie in mot.split("-"))


def format_person_name(nom):
    if not nom:
        return nom

    morceaux = re.split(r"(\s+)", nom.strip())
    resultat = []
    en_tete = True

    for morceau in morceaux:
        if not morceau or morceau.isspace():
            resultat.append(morceau)
            continue

        resultat.append(format_mot(morceau, en_tete))
        en_tete = morceau.lower() in LIAISONS

    return "".join(resultat)


def noms_courts(noms):
    return (noms or "").replace(" et ", " & ")


def noms_clients(data, defaut="Les clients"):
    return data.get("noms") or defaut


def date_longue(jour):
    return f"{JOURS[jour.weekday()]} {jour.day} {MOIS[jour.month - 1]}"


def montant(valeur):
    if valeur is None:
        return ""

    texte = f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte.removesuffix(',00')} €"


def echeance_texte(jours):
    if jours == 0:
        return "aujourd'hui"

    if jours == 1:
        return "demain"

    return f"dans {pluriel(jours, 'jour')}"


def pluriel(nombre, singulier, forme_plurielle=None):
    return f"{nombre} {singulier if nombre <= 1 else forme_plurielle or singulier + 's'}"


LIBELLES_PROFIL = {ORGANISATEUR: "Organisateur", CLIENTS: "Clients", PRESTATAIRE: "Prestataire"}

ONGLETS = {
    "accueil": ":material/home: Accueil",
    "messages": ":material/mail: Messages",
    "fiche": ":material/folder_shared: Fiche client",
    "planning": ":material/event: Planning",
    "prestataires": ":material/handshake: Prestataires",
    "budget": ":material/payments: Budget & devis",
    "invites": ":material/groups: Invités",
    "inspiration": ":material/palette: Inspiration & galerie",
    "discussion": ":material/chat: Discussion",
    "evenement": ":material/celebration: L'événement",
    "recap": ":material/folder_shared: Notre événement",
    "budget_client": ":material/payments: Budget",
    "invitations": ":material/mail: Invitations",
    "agenda_prestataire": ":material/event: Mes rendez-vous",
    "devis_prestataire": ":material/request_quote: Devis & factures"
}

LIBELLES_SECTIONS = {
    "discussion": ":material/chat: Discussion avec AURORE",
    "a_envoyer": ":material/outbox: À préparer et à envoyer",
    "agenda": ":material/event: Rendez-vous",
    "deroule": ":material/schedule: Déroulé du jour J",
    "plan_salle": ":material/table_restaurant: Plan de salle",
    "salle_3d": ":material/view_in_ar: Salle en 3D",
    "budget": ":material/payments: Budget",
    "devis": ":material/request_quote: Devis",
    "achats": ":material/receipt_long: Achats & factures",
    "moodboard": ":material/palette: Moodboard",
    "adresses": ":material/storefront: Boutiques & beauté",
    "photos": ":material/photo_library: Photos",
    "droit_image": ":material/verified_user: Droit à l'image",
    "avis": ":material/star: Avis",
    "instagram": ":material/share: Instagram"
}

RACCOURCIS = [
    ("agenda", ":material/calendar_month:", "Mon agenda de la semaine", "Quels sont mes rendez-vous des 7 prochains jours ?"),
    ("budget", ":material/payments:", "Point budget", "Fais-moi le point sur le budget et les factures à payer."),
    ("invites", ":material/groups:", "Réponses des invités", "Où en sont les réponses des invités et les régimes alimentaires ?"),
    ("message", ":material/mail:", "Préparer un message", "Aide-moi à préparer un message pour un prestataire.")
]

RACCOURCIS_CLIENTS = [
    ("agenda", ":material/calendar_month:", "Nos prochains rendez-vous", "Quels sont nos prochains rendez-vous ?"),
    ("budget", ":material/payments:", "Où en est le budget ?", "Où en est notre budget et que reste-t-il à payer ?"),
    ("invites", ":material/groups:", "Réponses des invités", "Combien d'invités ont répondu ?")
]

RACCOURCIS_PRESTATAIRE = [
    ("agenda", ":material/calendar_month:", "Mes rendez-vous", "Quels sont mes prochains rendez-vous pour cet événement ?"),
    ("couverts", ":material/restaurant:", "Couverts et allergies", "Combien de couverts, quels régimes et quelles allergies ?"),
    ("devis", ":material/request_quote:", "Préparer un devis", "Aide-moi à préparer mon devis pour cet événement.")
]

PLACEHOLDERS = {
    ORGANISATEUR: "Que puis-je faire pour vous ? (ex : ajoute une dégustation jeudi à 14h)",
    CLIENTS: "Parle-moi de ton événement ! (ex : où en est notre budget ?)",
    PRESTATAIRE: "Que puis-je faire pour vous ? (ex : combien de couverts végétariens ?)"
}

NOTES_DEVIS ="Acompte à régler à la signature, solde au plus tard le jour de l'événement."

CHOIX_TYPE_RDV = "Selon le titre"

CHAMPS_LISTES = {
    "allergies_interdits": "Allergies / interdits (alimentaires, religieux, à éviter absolument…)",
    "preferences": "Préférences (style, couleurs, fleurs, ambiance…)",
    "prestataires": "Prestataires déjà choisis"
}

SOURCES_ECHANGE = ["Rendez-vous", "Appel", "Message", "Email", "Autre"]

CHAMPS_DOSSIER_PRESTATAIRE = {"date": "Date", "lieu": "Lieu", "nombre_invites": "Invités"}
