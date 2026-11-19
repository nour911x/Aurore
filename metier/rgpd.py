import json
from datetime import date
from pathlib import Path

from donnees.dossiers import RACINE, chemin_agenda, dossier_racine
from donnees.stockage import charger_json


CHAMPS_SANTE = ["allergies_interdits"]

CHAMPS_CONSENTEMENT = ["consentement_sante", "droit_image"]

CATEGORIE_DONNEES_SANTE = "Traiteur"

PERIMETRES_IMAGE = ["Aucun", "Portfolio", "Réseaux sociaux et portfolio"]

USAGES_PHOTO = {"Portfolio": "Portfolio", "Réseaux sociaux": "Réseaux sociaux et portfolio"}

TEXTE_CONSENTEMENT_SANTE = (
    "Le client accepte que ces informations (allergies, régimes, interdits alimentaires) soient conservées "
    "et partagées avec les prestataires concernés, c'est-à-dire le traiteur uniquement."
)


def consentement(accorde: bool) -> dict:
    return {"accorde": accorde, "date": date.today().isoformat()}


def sante_partageable(donnees: dict) -> bool:
    return bool((donnees.get("consentement_sante") or {}).get("accorde"))


def peut_recevoir_sante(donnees: dict, prestataire: dict) -> bool:
    return bool(prestataire) and prestataire["categorie"] == CATEGORIE_DONNEES_SANTE and sante_partageable(donnees)


def sans_sante(donnees: dict) -> dict:
    return {cle: valeur for cle, valeur in donnees.items() if cle not in CHAMPS_SANTE}


def recap_sans_sante(recap: dict) -> dict:
    return {cle: valeur for cle, valeur in recap.items() if cle not in ("regimes", "allergies")}


def recap_anonyme(recap: dict) -> dict:
    return {**recap, "allergies": sorted(set(recap.get("allergies", {}).values()))}


def couvre(perimetre: str, usage: str) -> bool:
    return PERIMETRES_IMAGE.index(perimetre) >= PERIMETRES_IMAGE.index(USAGES_PHOTO[usage])


def consentements_manquants(droit_image: list[dict], usage: str) -> list[str]:
    if not droit_image:
        return ["aucun consentement enregistré"]

    return [element["personne"] for element in droit_image if not couvre(element["perimetre"], usage)]


def exporter(dossier_id: str, racine: Path = RACINE) -> str:
    dossier = dossier_racine(racine) / dossier_id
    contenu = {fichier.stem: charger_json(fichier, None) for fichier in sorted(dossier.glob("*.json"))}
    contenu["rendez_vous"] = [rdv for rdv in charger_json(chemin_agenda(racine), []) if rdv.get("dossier_id") == dossier_id]
    contenu["photos"] = sorted(photo.name for photo in (dossier / "galerie").glob("*")) if (dossier / "galerie").exists() else []

    return json.dumps({"dossier": dossier_id, "export": date.today().isoformat(), **contenu}, ensure_ascii=False, indent=2)
