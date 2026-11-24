import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple


FICHIER_BASE = "aurore.db"

COMMUN = ""

DELAI_VERROU = 10

CREER_TABLE = """
CREATE TABLE IF NOT EXISTS contenus (
    dossier_id TEXT NOT NULL,
    nom TEXT NOT NULL,
    contenu TEXT NOT NULL,
    modifie_le TEXT NOT NULL,
    PRIMARY KEY (dossier_id, nom)
)
"""


class Emplacement(NamedTuple):
    racine: Path
    dossier_id: str
    nom: str


@contextmanager
def transaction(racine: Path) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(Path(racine) / FICHIER_BASE, timeout=DELAI_VERROU)) as connexion, connexion:
        connexion.execute(CREER_TABLE)
        yield connexion


def lire(connexion: sqlite3.Connection, dossier_id: str, nom: str, defaut: Any) -> Any:
    ligne = connexion.execute("SELECT contenu FROM contenus WHERE dossier_id = ? AND nom = ?", (dossier_id, nom)).fetchone()
    return json.loads(ligne[0]) if ligne else defaut


def ecrire(connexion: sqlite3.Connection, dossier_id: str, nom: str, donnees: Any) -> None:
    connexion.execute(
        "INSERT OR REPLACE INTO contenus VALUES (?, ?, ?, ?)",
        (dossier_id, nom, json.dumps(donnees, ensure_ascii=False), datetime.now().isoformat(timespec="seconds"))
    )


def charger_donnees(emplacement: Emplacement, defaut: Any) -> Any:
    with transaction(emplacement.racine) as connexion:
        return lire(connexion, emplacement.dossier_id, emplacement.nom, defaut)


def sauvegarder_donnees(emplacement: Emplacement, donnees: Any) -> None:
    with transaction(emplacement.racine) as connexion:
        ecrire(connexion, emplacement.dossier_id, emplacement.nom, donnees)


def charger_par_nom(racine: Path, nom: str) -> dict[str, Any]:
    with transaction(racine) as connexion:
        lignes = connexion.execute("SELECT dossier_id, contenu FROM contenus WHERE nom = ?", (nom,)).fetchall()

    return {dossier_id: json.loads(contenu) for dossier_id, contenu in lignes}


def charger_dossier(racine: Path, dossier_id: str) -> dict[str, Any]:
    with transaction(racine) as connexion:
        lignes = connexion.execute("SELECT nom, contenu FROM contenus WHERE dossier_id = ? ORDER BY nom", (dossier_id,)).fetchall()

    return {nom: json.loads(contenu) for nom, contenu in lignes}


def est_vide(racine: Path) -> bool:
    with transaction(racine) as connexion:
        return connexion.execute("SELECT 1 FROM contenus LIMIT 1").fetchone() is None


def premier(elements: list[dict], **criteres: Any) -> dict | None:
    return next(
        (element for element in elements if all(element.get(cle) == valeur for cle, valeur in criteres.items())),
        None
    )
