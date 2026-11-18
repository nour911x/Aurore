import json
from datetime import date

from donnees.dossiers import RACINE, chemin_agenda, dossier_racine
from donnees.storage import load_json


CHAMPS_SANTE = ["allergies_interdits"]

CHAMPS_CONSENTEMENT = ["consentement_sante", "droit_image"]

CATEGORIE_DONNEES_SANTE = "Traiteur"

PERIMETRES_IMAGE = ["Aucun", "Portfolio", "Réseaux sociaux et portfolio"]

USAGES_PHOTO = {"Portfolio": "Portfolio", "Réseaux sociaux": "Réseaux sociaux et portfolio"}

TEXTE_CONSENTEMENT_SANTE = (
    "Le client accepte que ces informations (allergies, régimes, interdits alimentaires) soient conservées "
    "et partagées avec les prestataires concernés, c'est-à-dire le traiteur uniquement."
)


def consentement(accorde):
    return {"accorde": accorde, "date": date.today().isoformat()}


def sante_partageable(data):
    return bool((data.get("consentement_sante") or {}).get("accorde"))


def peut_recevoir_sante(data, prestataire):
    return bool(prestataire) and prestataire["categorie"] == CATEGORIE_DONNEES_SANTE and sante_partageable(data)


def sans_sante(data):
    return {cle: valeur for cle, valeur in data.items() if cle not in CHAMPS_SANTE}


def recap_sans_sante(recap):
    return {cle: valeur for cle, valeur in recap.items() if cle not in ("regimes", "allergies")}


def recap_anonyme(recap):
    return {**recap, "allergies": sorted(set(recap.get("allergies", {}).values()))}


def couvre(perimetre, usage):
    return PERIMETRES_IMAGE.index(perimetre) >= PERIMETRES_IMAGE.index(USAGES_PHOTO[usage])


def consentements_manquants(droit_image, usage):
    if not droit_image:
        return ["aucun consentement enregistré"]

    return [element["personne"] for element in droit_image if not couvre(element["perimetre"], usage)]


def exporter(dossier_id, racine=RACINE):
    dossier = dossier_racine(racine) / dossier_id
    contenu = {fichier.stem: load_json(fichier, None) for fichier in sorted(dossier.glob("*.json"))}
    contenu["rendez_vous"] = [rdv for rdv in load_json(chemin_agenda(racine), []) if rdv.get("dossier_id") == dossier_id]
    contenu["photos"] = sorted(photo.name for photo in (dossier / "galerie").glob("*")) if (dossier / "galerie").exists() else []

    return json.dumps({"dossier": dossier_id, "export": date.today().isoformat(), **contenu}, ensure_ascii=False, indent=2)
