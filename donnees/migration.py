import json
from pathlib import Path
from typing import Any

from donnees.dossiers import NOM_AGENDA, NOM_ANNUAIRE, NOM_ETAT, RACINE, dossier_racine
from donnees.stockage import COMMUN, ecrire, est_vide, transaction


def lire_json(fichier: Path) -> Any:
    try:
        return json.loads(fichier.read_text(encoding="utf-8"))
    except ValueError as erreur:
        raise ValueError(f"Le fichier {fichier} est illisible : corrigez-le ou retirez-le, puis relancez AURORE.") from erreur


def anciens_fichiers(racine: Path) -> list[tuple[str, Path]]:
    communs = [(COMMUN, Path(racine) / f"{nom}.json") for nom in (NOM_AGENDA, NOM_ANNUAIRE, NOM_ETAT)]
    par_dossier = [(fichier.parent.name, fichier) for fichier in sorted(dossier_racine(racine).glob("*/*.json"))]

    return [(dossier_id, fichier) for dossier_id, fichier in communs + par_dossier if fichier.exists()]


def migrer_json(racine: Path = RACINE) -> int:
    if not est_vide(racine):
        return 0

    contenus = [(dossier_id, fichier.stem, lire_json(fichier)) for dossier_id, fichier in anciens_fichiers(racine)]

    with transaction(racine) as connexion:
        for dossier_id, nom, donnees in contenus:
            ecrire(connexion, dossier_id, nom, donnees)

    return len(contenus)
