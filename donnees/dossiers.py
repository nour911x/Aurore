import shutil
import uuid
from datetime import date
from pathlib import Path

from config.evenements import libelle_evenement
from donnees.stockage import charger_json, sauvegarder_json
from metier.devis import date_lisible
from textes import noms_courts


RACINE = Path(__file__).parent.parent

FICHIER_FICHE = "event_data.json"

FICHIER_AGENDA = "agenda_data.json"

FICHIER_ANNUAIRE = "annuaire_prestataires.json"

FICHIER_SELECTION = "selection_prestataires.json"

FICHIER_ETAT = "aurore_etat.json"



def dossier_racine(racine: Path = RACINE) -> Path:
    return Path(racine) / "dossiers"


def chemin(dossier_id: str, fichier: str, racine: Path = RACINE) -> str:
    return str(dossier_racine(racine) / dossier_id / fichier)


def chemin_agenda(racine: Path = RACINE) -> str:
    return str(Path(racine) / FICHIER_AGENDA)


def lire_etat(racine: Path = RACINE) -> dict:
    return charger_json(Path(racine) / FICHIER_ETAT, {})


def ecrire_etat(cle: str, valeur: bool, racine: Path = RACINE) -> None:
    sauvegarder_json(Path(racine) / FICHIER_ETAT, {**lire_etat(racine), cle: valeur})


def chemin_annuaire(racine: Path = RACINE) -> str:
    return str(Path(racine) / FICHIER_ANNUAIRE)


def lister(racine: Path = RACINE) -> list[dict]:
    if not dossier_racine(racine).exists():
        return []

    dossiers = [
        {"id": dossier.name, **charger_json(dossier / FICHIER_FICHE, {})}
        for dossier in dossier_racine(racine).iterdir()
        if (dossier / FICHIER_FICHE).exists()
    ]

    return sorted(dossiers, key=lambda dossier: dossier.get("date") or "9999")


def creer(fiche: dict, racine: Path = RACINE) -> str:
    dossier_id = uuid.uuid4().hex[:8]
    dossier = dossier_racine(racine) / dossier_id
    dossier.mkdir(parents=True)
    sauvegarder_json(dossier / FICHIER_FICHE, fiche)

    return dossier_id


def libelle_dossier(dossier: dict) -> str:
    morceaux = [dossier.get("noms") or "Sans nom", libelle_evenement(dossier), date_lisible(dossier.get("date"))]
    return " · ".join(filter(None, morceaux))


def libelle_court(dossier: dict) -> str:
    jour = date.fromisoformat(dossier["date"]).strftime("%d/%m") if dossier.get("date") else ""
    return " · ".join(filter(None, [noms_courts(dossier.get("noms")) or "Sans nom", jour]))


def supprimer(dossier_id: str, racine: Path = RACINE) -> None:
    shutil.rmtree(dossier_racine(racine) / dossier_id, ignore_errors=True)
    rdvs = charger_json(chemin_agenda(racine), [])
    sauvegarder_json(chemin_agenda(racine), [rdv for rdv in rdvs if rdv.get("dossier_id") != dossier_id])
