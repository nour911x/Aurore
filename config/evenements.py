TYPES_EVENEMENT = {
    "mariage": {
        "libelle": "Mariage",
        "icone": ":material/favorite:",
        "exemples": "Cérémonie, vin d'honneur, réception",
        "personnes": "Client(s)",
        "champs": ["ceremonie", "reception", "preferences_musicales"],
        "deroule": (
            "Pour un mariage en France, repères habituels : préparatifs le matin, cérémonie vers 15h-16h, "
            "vin d'honneur ensuite pendant 2h environ, entrée des mariés et dîner vers 19h30-20h30, "
            "discours entre les plats, dessert et pièce montée vers 23h, ouverture du bal après le dessert, "
            "fin de soirée vers 3h-4h."
        )
    },
    "baby_shower": {
        "libelle": "Baby shower",
        "icone": ":material/child_care:",
        "exemples": "Gender reveal, naissance",
        "personnes": "Parent(s)",
        "champs": ["date_naissance", "gender_reveal"],
        "deroule": (
            "Une baby shower dure en général 3 à 4 heures l'après-midi : accueil et boissons, jeux, "
            "ouverture des cadeaux, goûter et gâteau, gender reveal éventuel en fin de fête."
        )
    },
    "anniversaire": {
        "libelle": "Anniversaire",
        "icone": ":material/cake:",
        "exemples": "Surprise, 30 ans, enfant",
        "personnes": "Client(s)",
        "champs": ["personne_fetee", "age", "surprise"],
        "deroule": (
            "Pour un anniversaire : arrivée des invités, apéritif, repas ou buffet, discours, gâteau et bougies, "
            "puis soirée dansante. Pour une surprise, les invités arrivent avant la personne fêtée."
        )
    },
    "entreprise": {
        "libelle": "Entreprise",
        "icone": ":material/business_center:",
        "exemples": "Séminaire, conférence, gala",
        "personnes": "Contact(s)",
        "champs": [
            "entreprise", "format_entreprise", "materiel_technique",
            "facturation"
        ],
        "deroule": (
            "Pour un séminaire d'entreprise : accueil café et badges vers "
            "8h30, plénière d'ouverture vers 9h, ateliers en sous-groupes, "
            "pause en milieu de matinée, déjeuner vers 12h30, sessions de "
            "l'après-midi avec une pause vers 16h, conclusion vers 17h30. "
            "Une soirée de gala commence vers 19h30 par un cocktail, puis "
            "dîner, discours de la direction entre les plats et animation."
        )
    },
    "autre": {
        "libelle": "Autre",
        "icone": ":material/celebration:",
        "exemples": "EVJF, fiançailles, crémaillère",
        "personnes": "Client(s)",
        "champs": ["sous_type"],
        "deroule": ""
    }
}

CHAMPS_ESSENTIELS = {"date": "Date", "lieu": "Lieu", "nombre_invites": "Invités", "budget": "Budget"}

CHAMPS_SPECIFIQUES = {
    "ceremonie": ("Cérémonie", "texte", "Lieu, heure, laïque ou religieuse…"),
    "reception": ("Réception", "texte", "Lieu et format : dîner assis, cocktail…"),
    "preferences_musicales": ("Musique", "liste", "Styles, chansons, ouverture de bal…"),
    "date_naissance": ("Naissance prévue", "date", None),
    "gender_reveal": ("Gender reveal", "oui_non", None),
    "personne_fetee": ("Personne fêtée", "texte", None),
    "age": ("Âge", "nombre", None),
    "surprise": ("Surprise", "oui_non", "La personne fêtée ne doit pas être au courant"),
    "entreprise": (
        "Entreprise", "texte", "Raison sociale de l'entreprise cliente"
    ),
    "format_entreprise": (
        "Format", "texte",
        "Séminaire, conférence, team building, soirée de gala…"
    ),
    "materiel_technique": (
        "Matériel technique", "liste",
        "Vidéoprojecteur, micros, sono, wifi…"
    ),
    "facturation": (
        "Facturation", "texte",
        "SIRET, adresse de facturation, bon de commande…"
    ),
    "sous_type": ("Type précis", "texte", "EVJF, fiançailles, crémaillère…")
}

MOTS_CLES = {
    "mariage": ["mariage", "noces"],
    "baby_shower": ["baby", "naissance", "gender"],
    "anniversaire": ["anniv"],
    "entreprise": [
        "entreprise", "seminaire", "séminaire", "conference", "conférence",
        "corporate", "team building", "gala", "salon professionnel"
    ]
}

CHAMPS_INTERNES = {"facturation"}

GENRES_LLM = {"texte": "texte", "liste": "liste de textes courts", "date": "date AAAA-MM-JJ", "oui_non": "true ou false", "nombre": "nombre"}


def cle_type(type_evenement: str | None) -> str:
    texte = (type_evenement or "").lower()

    for cle, mots in MOTS_CLES.items():
        if any(mot in texte for mot in mots):
            return cle

    return "autre"


def type_du_dossier(donnees: dict) -> dict:
    return TYPES_EVENEMENT[cle_type(donnees.get("type_evenement"))]


def champs_du_type(donnees: dict) -> dict[str, str]:
    return {cle: CHAMPS_SPECIFIQUES[cle][0] for cle in type_du_dossier(donnees)["champs"]}


def champs_masques(donnees: dict, nouvelle_cle: str) -> list[str]:
    gardes = set(TYPES_EVENEMENT[nouvelle_cle]["champs"])
    return [
        CHAMPS_SPECIFIQUES[cle][0] for cle in type_du_dossier(donnees)["champs"]
        if cle not in gardes and donnees.get(cle) not in (None, "", [])
    ]


def libelle_evenement(donnees: dict) -> str:
    type_evenement = type_du_dossier(donnees)

    if type_evenement["libelle"] != "Autre":
        return type_evenement["libelle"]

    return donnees.get("sous_type") or donnees.get("type_evenement") or "Autre"


def valeur_par_defaut(genre: str) -> list | None:
    return [] if genre == "liste" else None


def champs_par_defaut() -> dict:
    return {cle: valeur_par_defaut(genre) for cle, (_, genre, _) in CHAMPS_SPECIFIQUES.items()}


def description_champs_llm() -> str:
    lignes = []

    for type_evenement in TYPES_EVENEMENT.values():
        champs = ", ".join(
            f"{cle} ({CHAMPS_SPECIFIQUES[cle][0].lower()}, {GENRES_LLM[CHAMPS_SPECIFIQUES[cle][1]]})"
            for cle in type_evenement["champs"]
        )
        lignes.append(f"{type_evenement['libelle']} : {champs}")

    return " ; ".join(lignes)
