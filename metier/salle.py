from typing import Any

from metier.jour_j import TABLE_HONNEUR, personnes


UNITES_PAR_METRE = 40

LARGEUR_SALLE = 1000

PROFONDEUR_MINIMALE = 640

MARGE = 30

ALLEE = 70

LARGEUR_PAR_PLACE = 24

COTE_TABLE = 48

DIAMETRE_MINIMAL = 60

TAILLES_ELEMENTS = {
    "Piste de danse": (240, 120),
    "DJ": (90, 50),
    "Buffet": (50, 240),
    "Bar": (50, 180),
    "Photobooth": (130, 50),
    "Arche": (120, 30),
    "Gâteau": (50, 50)
}

EMPLACEMENTS = {
    f"{profondeur}, {cote}": (x, y)
    for profondeur, y in {"Au fond": 0.0, "Au milieu": 0.5, "Devant": 1.0}.items()
    for cote, x in {"à gauche": 0.0, "au centre": 0.5, "à droite": 1.0}.items()
}

COULEURS_PAR_DEFAUT = {"nappe": "#FFFFFF", "accent": "#B8975A"}


def objet(nom: str, genre: str, largeur: float, profondeur: float, **details: Any) -> dict:
    return {"nom": nom, "genre": genre, "x": 0.0, "y": 0.0, "largeur": largeur, "profondeur": profondeur, **details}


def taille_table(table: dict) -> tuple[float, float]:
    places = table["places"]

    if table["forme"] == "Ronde":
        diametre = max(DIAMETRE_MINIMAL, round(places * LARGEUR_PAR_PLACE / 3.14) + 10)
        return diametre, diametre

    par_cote = places if table["nom"] == TABLE_HONNEUR else -(-places // 2)
    return max(72, par_cote * LARGEUR_PAR_PLACE), COTE_TABLE


def objet_table(table: dict, invites: list[dict]) -> dict:
    largeur, profondeur = taille_table(table)

    return objet(
        table["nom"], "table", largeur, profondeur, forme=table["forme"], places=table["places"], honneur=table["nom"] == TABLE_HONNEUR,
        occupees=sum(personnes(invite) for invite in invites), invites=[invite["nom"] for invite in invites]
    )


def poser(element: dict, x: float, y: float) -> dict:
    return {**element, "x": x, "y": y}


def poser_tables(tables: list[dict], debut: float) -> tuple[list[dict], float]:
    if not tables:
        return [], debut

    pas_x = max(table["largeur"] for table in tables) + ALLEE
    pas_y = max(table["profondeur"] for table in tables) + ALLEE
    colonnes = max(1, int((LARGEUR_SALLE - 4 * MARGE - 2 * ALLEE) // pas_x))
    posees = []

    for index, table in enumerate(tables):
        rang, colonne = divmod(index, colonnes)
        dans_le_rang = min(colonnes, len(tables) - rang * colonnes)
        x = LARGEUR_SALLE / 2 + (colonne - (dans_le_rang - 1) / 2) * pas_x
        posees.append(poser(table, x, debut + pas_y * (rang + 0.5)))

    return posees, debut + pas_y * -(-len(tables) // colonnes)


def disposition_automatique(tables: list[dict], elements: list[dict]) -> tuple[list[dict], float]:
    par_nom = {element["nom"]: element for element in elements}
    posees = []
    y: float = MARGE + 45

    for table in [table for table in tables if table["honneur"]]:
        posees.append(poser(table, LARGEUR_SALLE / 2, y))
        y += 75

    if "Piste de danse" in par_nom:
        posees.append(poser(par_nom["Piste de danse"], LARGEUR_SALLE / 2, y + 60))

    if "DJ" in par_nom:
        posees.append(poser(par_nom["DJ"], LARGEUR_SALLE / 2 + (180 if "Piste de danse" in par_nom else 0), y + 60))

    if "Gâteau" in par_nom:
        posees.append(poser(par_nom["Gâteau"], LARGEUR_SALLE / 2 - 180, y + 60))

    if {"Piste de danse", "DJ", "Gâteau"} & par_nom.keys():
        y += 140

    rangees, y = poser_tables([table for table in tables if not table["honneur"]], y)
    devant = 80 if {"Arche", "Photobooth"} & par_nom.keys() else 0
    profondeur = max(PROFONDEUR_MINIMALE, y + 2 * MARGE + devant)

    for nom, x in [("Buffet", MARGE + 25), ("Bar", LARGEUR_SALLE - MARGE - 25)]:
        if nom in par_nom:
            posees.append(poser(par_nom[nom], x, profondeur / 2))

    for nom, x in [("Arche", 120), ("Photobooth", LARGEUR_SALLE - 120)]:
        if nom in par_nom:
            posees.append(poser(par_nom[nom], x, profondeur - MARGE - 25))

    return posees + rangees, profondeur


def borner(element: dict, x: float, y: float, profondeur: float) -> tuple[float, float]:
    demi_largeur, demi_profondeur = element["largeur"] / 2, element["profondeur"] / 2

    return (
        min(max(x, demi_largeur + MARGE), LARGEUR_SALLE - demi_largeur - MARGE),
        min(max(y, demi_profondeur + MARGE), profondeur - demi_profondeur - MARGE)
    )


def disposer(salle: dict, repartition: dict[str, list[dict]]) -> dict:
    tables = [objet_table(table, repartition.get(table["nom"], [])) for table in salle["tables"]]
    elements = [objet(nom, "element", *TAILLES_ELEMENTS[nom]) for nom in salle["elements"] if nom in TAILLES_ELEMENTS]
    objets, profondeur = disposition_automatique(tables, elements)
    positions = salle.get("positions", {})
    places = []

    for element in objets:
        x, y = positions.get(element["nom"], (element["x"], element["y"]))
        places.append(poser(element, *borner(element, x, y, profondeur)))

    return {"largeur": LARGEUR_SALLE, "profondeur": profondeur, "objets": places}


def emplacement(disposition: dict, nom: str, choix: str) -> tuple[float, float]:
    part_x, part_y = EMPLACEMENTS[choix]
    element = next(element for element in disposition["objets"] if element["nom"] == nom)

    return borner(element, part_x * disposition["largeur"], part_y * disposition["profondeur"], disposition["profondeur"])


def se_touchent(premier: dict, second: dict) -> bool:
    return (
        abs(premier["x"] - second["x"]) < (premier["largeur"] + second["largeur"]) / 2
        and abs(premier["y"] - second["y"]) < (premier["profondeur"] + second["profondeur"]) / 2
    )


def chevauchements(disposition: dict) -> list[tuple[str, str]]:
    objets = disposition["objets"]

    return [
        (premier["nom"], second["nom"])
        for index, premier in enumerate(objets)
        for second in objets[index + 1:]
        if se_touchent(premier, second)
    ]


def tables_necessaires(nombre_invites: int, places: int, places_honneur: int) -> int:
    return max(1, -(-max(nombre_invites - places_honneur, 0) // places))


def couleurs_salle(salle: dict, moodboard: dict) -> dict[str, str]:
    teintes = [couleur["hex"] for couleur in moodboard.get("couleurs", [])]
    proposees = {**COULEURS_PAR_DEFAUT, **({"accent": teintes[0]} if teintes else {})}

    return {**proposees, **salle.get("couleurs", {})}
