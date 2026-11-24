import json
import shutil
import uuid
from datetime import date
from pathlib import Path

from config.evenements import libelle_evenement
from donnees.stockage import COMMUN, Emplacement, charger_donnees, charger_par_nom, ecrire, lire, sauvegarder_donnees, transaction
from metier.devis import date_lisible
from textes import noms_courts


RACINE = Path(__file__).parent.parent

NOM_FICHE = "event_data"

NOM_AGENDA = "agenda_data"

NOM_ANNUAIRE = "annuaire_prestataires"

NOM_SELECTION = "selection_prestataires"

NOM_ETAT = "aurore_etat"

NOM_ACCES = "liens_acces"

DOSSIER_INDEX = "index_documents"



def dossier_racine(racine: Path = RACINE) -> Path:
    return Path(racine) / "dossiers"


def chemin(dossier_id: str, fichier: str, racine: Path = RACINE) -> str:
    return str(dossier_racine(racine) / dossier_id / fichier)


def emplacement(dossier_id: str, nom: str, racine: Path = RACINE) -> Emplacement:
    return Emplacement(Path(racine), dossier_id, nom)


def emplacement_agenda(racine: Path = RACINE) -> Emplacement:
    return emplacement(COMMUN, NOM_AGENDA, racine)


def emplacement_annuaire(racine: Path = RACINE) -> Emplacement:
    return emplacement(COMMUN, NOM_ANNUAIRE, racine)


def emplacement_acces(racine: Path = RACINE) -> Emplacement:
    return emplacement(COMMUN, NOM_ACCES, racine)


def chemin_index(racine: Path = RACINE) -> Path:
    return Path(racine) / DOSSIER_INDEX


def lire_etat(racine: Path = RACINE) -> dict:
    return charger_donnees(emplacement(COMMUN, NOM_ETAT, racine), {})


def ecrire_etat(cle: str, valeur: bool, racine: Path = RACINE) -> None:
    sauvegarder_donnees(emplacement(COMMUN, NOM_ETAT, racine), {**lire_etat(racine), cle: valeur})


def lister(racine: Path = RACINE) -> list[dict]:
    dossiers = [{"id": dossier_id, **fiche} for dossier_id, fiche in charger_par_nom(racine, NOM_FICHE).items()]
    return sorted(dossiers, key=lambda dossier: dossier.get("date") or "9999")


def creer(fiche: dict, racine: Path = RACINE) -> str:
    dossier_id = uuid.uuid4().hex[:8]
    sauvegarder_donnees(emplacement(dossier_id, NOM_FICHE, racine), fiche)

    return dossier_id


def libelle_dossier(dossier: dict) -> str:
    morceaux = [dossier.get("noms") or "Sans nom", libelle_evenement(dossier), date_lisible(dossier.get("date"))]
    return " · ".join(filter(None, morceaux))


def libelle_court(dossier: dict) -> str:
    jour = date.fromisoformat(dossier["date"]).strftime("%d/%m") if dossier.get("date") else ""
    return " · ".join(filter(None, [noms_courts(dossier.get("noms")) or "Sans nom", jour]))


def sans_dossier(elements: list[dict], dossier_id: str) -> list[dict]:
    return [element for element in elements if element.get("dossier_id") != dossier_id]


def effacer_ancien_agenda(dossier_id: str, racine: Path) -> None:
    fichier = Path(racine) / f"{NOM_AGENDA}.json"

    if fichier.exists():
        rdvs = json.loads(fichier.read_text(encoding="utf-8"))
        fichier.write_text(json.dumps(sans_dossier(rdvs, dossier_id), ensure_ascii=False, indent=4), encoding="utf-8")


def supprimer(dossier_id: str, racine: Path = RACINE) -> None:
    with transaction(racine) as connexion:
        connexion.execute("DELETE FROM contenus WHERE dossier_id = ?", (dossier_id,))

        for nom in (NOM_AGENDA, NOM_ACCES):
            ecrire(connexion, COMMUN, nom, sans_dossier(lire(connexion, COMMUN, nom, []), dossier_id))

    shutil.rmtree(dossier_racine(racine) / dossier_id, ignore_errors=True)
    effacer_ancien_agenda(dossier_id, racine)
