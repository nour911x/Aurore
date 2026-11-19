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
    "sous_type": ("Type précis", "texte", "EVJF, fiançailles, crémaillère, gala…")
}

MOTS_CLES = {
    "mariage": ["mariage", "noces"],
    "baby_shower": ["baby", "naissance", "gender"],
    "anniversaire": ["anniv"]
}

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
