import re


PARTICULES = {"de", "du", "des", "d", "la", "le", "van", "von", "der", "den", "di", "da", "del", "dos"}

LIAISONS = {"et", "and", "&"}

PREFIXES_APOSTROPHE = {"d", "l"}


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


def noms_clients(data, defaut="Les clients"):
    return format_person_name(data.get("noms")) or defaut


def pluriel(nombre, singulier, forme_plurielle=None):
    return f"{nombre} {singulier if nombre <= 1 else forme_plurielle or singulier + 's'}"
