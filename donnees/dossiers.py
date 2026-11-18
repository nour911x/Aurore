import shutil
import uuid
from pathlib import Path

from config.evenements import libelle_evenement
from metier.devis import date_lisible
from donnees.storage import load_json, save_json
from textes import format_person_name


RACINE = Path(__file__).parent.parent

FICHIER_FICHE = "event_data.json"

FICHIER_AGENDA = "agenda_data.json"

FICHIERS_DOSSIER = [
    FICHIER_FICHE, "budget_data.json", "prestataires_data.json", "messages_data.json", "devis_data.json",
    "invites_data.json", "inspiration_data.json", "galerie_data.json", "jour_j_data.json"
]


def dossier_racine(racine=RACINE):
    return Path(racine) / "dossiers"


def chemin(dossier_id, fichier, racine=RACINE):
    return str(dossier_racine(racine) / dossier_id / fichier)


def chemin_agenda(racine=RACINE):
    return str(Path(racine) / FICHIER_AGENDA)


def lister(racine=RACINE):
    if not dossier_racine(racine).exists():
        return []

    dossiers = [
        {"id": dossier.name, **load_json(dossier / FICHIER_FICHE, {})}
        for dossier in dossier_racine(racine).iterdir()
        if (dossier / FICHIER_FICHE).exists()
    ]

    return sorted(dossiers, key=lambda dossier: dossier.get("date") or "9999")


def creer(fiche, racine=RACINE):
    dossier_id = uuid.uuid4().hex[:8]
    dossier = dossier_racine(racine) / dossier_id
    dossier.mkdir(parents=True)
    save_json(dossier / FICHIER_FICHE, fiche)

    return dossier_id


def libelle_dossier(dossier):
    morceaux = [format_person_name(dossier.get("noms")) or "Sans nom", libelle_evenement(dossier), date_lisible(dossier.get("date"))]
    return " · ".join(filter(None, morceaux))


def rattacher_rdvs(dossier_id, racine=RACINE):
    rdvs = load_json(chemin_agenda(racine), [])

    for rdv in rdvs:
        rdv.setdefault("dossier_id", dossier_id)

    if rdvs:
        save_json(chemin_agenda(racine), rdvs)


def supprimer(dossier_id, racine=RACINE):
    shutil.rmtree(dossier_racine(racine) / dossier_id, ignore_errors=True)
    rdvs = load_json(chemin_agenda(racine), [])
    save_json(chemin_agenda(racine), [rdv for rdv in rdvs if rdv.get("dossier_id") != dossier_id])


def migrer_ancien_dossier(racine=RACINE):
    racine = Path(racine)

    if not (racine / FICHIER_FICHE).exists():
        return None

    dossier_id = uuid.uuid4().hex[:8]
    dossier = dossier_racine(racine) / dossier_id
    dossier.mkdir(parents=True)
    anciens = [racine / fichier for fichier in FICHIERS_DOSSIER] + list(racine.glob("achats_*.json")) + [racine / "galerie"]

    for ancien in anciens:
        if ancien.exists():
            shutil.move(ancien, dossier / ancien.name)

    rattacher_rdvs(dossier_id, racine)

    return dossier_id
