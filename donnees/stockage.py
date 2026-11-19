import json
import os
from pathlib import Path
from typing import Any


def charger_json(chemin_fichier: str | Path, defaut: Any) -> Any:
    if not os.path.exists(chemin_fichier):
        return defaut

    with open(chemin_fichier, encoding="utf-8") as fichier:
        return json.load(fichier)


def sauvegarder_json(chemin_fichier: str | Path, donnees: Any) -> None:
    with open(chemin_fichier, "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=4)


def premier(elements: list[dict], **criteres: Any) -> dict | None:
    return next(
        (element for element in elements if all(element.get(cle) == valeur for cle, valeur in criteres.items())),
        None
    )
