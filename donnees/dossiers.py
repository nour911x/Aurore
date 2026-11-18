import shutil
import uuid
from datetime import date
from pathlib import Path

from config.evenements import libelle_evenement
from metier.devis import date_lisible
from donnees.storage import load_json, save_json
from metier.prestataires import STATUTS, Annuaire
from textes import format_person_name, noms_courts


RACINE = Path(__file__).parent.parent

FICHIER_FICHE = "event_data.json"

FICHIER_AGENDA = "agenda_data.json"

FICHIER_ANNUAIRE = "annuaire_prestataires.json"

FICHIER_SELECTION = "selection_prestataires.json"

ANCIEN_CARNET = "prestataires_data.json"

FICHIERS_AVEC_PRESTATAIRE = ["messages_data.json", "devis_data.json"]

FICHIER_ETAT = "aurore_etat.json"

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


def lire_etat(racine=RACINE):
    return load_json(Path(racine) / FICHIER_ETAT, {})


def ecrire_etat(cle, valeur, racine=RACINE):
    save_json(Path(racine) / FICHIER_ETAT, {**lire_etat(racine), cle: valeur})


def chemin_annuaire(racine=RACINE):
    return str(Path(racine) / FICHIER_ANNUAIRE)


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


def libelle_court(dossier):
    jour = date.fromisoformat(dossier["date"]).strftime("%d/%m") if dossier.get("date") else ""
    return " · ".join(filter(None, [noms_courts(dossier.get("noms")) or "Sans nom", jour]))


def normaliser_noms_fichier(fichier, chemins):
    data = load_json(fichier, None)

    if data is None:
        return

    avant = repr(data)

    for chemin_liste, cle in chemins:
        elements = data.get(chemin_liste, []) if chemin_liste else (data if isinstance(data, list) else [data])

        for element in elements:
            if isinstance(element, dict) and element.get(cle) and (cle != "destinataire" or not element.get("prestataire_id")):
                element[cle] = format_person_name(element[cle])

    if repr(data) != avant:
        save_json(fichier, data)


def migrer_noms(racine=RACINE):
    if lire_etat(racine).get("noms_normalises"):
        return

    for dossier in dossier_racine(racine).glob("*") if dossier_racine(racine).exists() else []:
        normaliser_noms_fichier(dossier / FICHIER_FICHE, [(None, "noms"), ("droit_image", "personne")])
        normaliser_noms_fichier(dossier / "invites_data.json", [("invites", "nom")])
        normaliser_noms_fichier(dossier / "galerie_data.json", [("avis", "auteur")])
        normaliser_noms_fichier(dossier / "messages_data.json", [(None, "destinataire")])
        normaliser_noms_fichier(dossier / "devis_data.json", [(None, "destinataire")])

    ecrire_etat("noms_normalises", True, racine)


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


def renommer_prestataires(dossier, correspondances):
    for fichier in FICHIERS_AVEC_PRESTATAIRE:
        elements = load_json(dossier / fichier, None)

        if not elements:
            continue

        for element in elements:
            element["prestataire_id"] = correspondances.get(element.get("prestataire_id"), element.get("prestataire_id"))

        save_json(dossier / fichier, elements)


def migrer_carnets(racine=RACINE):
    anciens = sorted(dossier_racine(racine).glob(f"*/{ANCIEN_CARNET}")) if dossier_racine(racine).exists() else []

    if not anciens:
        return 0

    annuaire = Annuaire(chemin_annuaire(racine))

    for ancien in anciens:
        dossier = ancien.parent
        selection = load_json(dossier / FICHIER_SELECTION, [])
        deja_choisis = {element["prestataire_id"] for element in selection}
        correspondances = {}

        for entree in load_json(ancien, []):
            prestataire_id = annuaire.ajouter(entree, entree["id"])
            correspondances[entree["id"]] = prestataire_id

            if prestataire_id in deja_choisis:
                continue

            deja_choisis.add(prestataire_id)
            selection.append({
                "prestataire_id": prestataire_id,
                "statut": entree.get("statut") or STATUTS[0],
                "statut_depuis": entree.get("statut_depuis") or date.today().isoformat(),
                "tarif_indicatif": entree.get("tarif_indicatif") or 0,
                "poste_budget": entree.get("poste_budget")
            })

        save_json(dossier / FICHIER_SELECTION, selection)
        renommer_prestataires(dossier, correspondances)
        ancien.unlink()

    return len(anciens)


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
