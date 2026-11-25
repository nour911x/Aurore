import re
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from donnees.stockage import Emplacement, charger_donnees, premier, sauvegarder_donnees


if TYPE_CHECKING:
    from donnees.fiche_evenement import FicheEvenement


CATEGORIES = [
    "Traiteur",
    "DJ / Musiciens",
    "Domaine / Salle",
    "Photographe",
    "Fleuriste",
    "Tenues",
    "Maquillage / Coiffure",
    "Audiovisuel / Technique",
    "Autre"
]

STATUTS = ["À contacter", "Devis demandé", "Devis reçu", "Réservé", "Refusé"]


def numero_international(telephone: str) -> str:
    chiffres = re.sub(r"\D", "", telephone)

    if chiffres.startswith("00"):
        return chiffres[2:]

    if chiffres.startswith("0") and len(chiffres) == 10:
        return "33" + chiffres[1:]

    return chiffres


def lien_whatsapp(telephone: str, message: str = "") -> str:
    lien = f"https://wa.me/{numero_international(telephone)}"

    if message:
        lien += f"?text={quote(message)}"

    return lien


def lien_email(email: str, sujet: str = "", message: str = "") -> str:
    return f"mailto:{email}?subject={quote(sujet)}&body={quote(message)}"


def normaliser_nom(nom: str) -> str:
    return nom.replace("’", "'").strip().lower()


def meme_nom(premier: str, second: str) -> bool:
    return normaliser_nom(premier) == normaliser_nom(second)


def appliquer_statut(carnet: "Carnet", fiche_evenement: "FicheEvenement", prestataire: dict, statut: str) -> None:
    carnet.changer_statut(prestataire["id"], statut)

    if statut == "Réservé":
        fiche_evenement.ajouter_prestataire(f"{prestataire['nom']} ({prestataire['categorie']})")


CHAMPS_FICHE = ["nom", "categorie", "contact", "telephone", "email", "lien", "tarif_indicatif", "notes"]

CHAMPS_DU_DOSSIER = ["statut", "statut_depuis", "tarif_indicatif", "poste_budget"]


def normaliser_contact(valeur: str | None, cle: str) -> str:
    valeur = valeur or ""
    return re.sub(r"\D", "", valeur) if cle == "telephone" else valeur.strip().lower()


def contact_identique(premier: dict, second: dict, cle: str) -> bool:
    a, b = normaliser_contact(premier.get(cle), cle), normaliser_contact(second.get(cle), cle)
    return not a or not b or a == b


def meme_fiche(premier: dict, second: dict) -> bool:
    return meme_nom(premier["nom"], second["nom"]) and all(
        contact_identique(premier, second, cle) for cle in ("telephone", "email")
    )


def reservations_en_double(reservations: list[dict]) -> list[dict]:
    par_jour: dict[tuple, list[dict]] = {}

    for reservation in reservations:
        if reservation["date"]:
            par_jour.setdefault((reservation["prestataire_id"], reservation["date"]), []).append(reservation)

    return [
        {"prestataire": groupe[0]["nom"], "date": date_evenement, "dossiers": [element["dossier"] for element in groupe]}
        for (_, date_evenement), groupe in sorted(par_jour.items(), key=lambda element: element[0][1])
        if len({element["dossier_id"] for element in groupe}) > 1
    ]


class Annuaire:
    def __init__(self, emplacement: Emplacement) -> None:
        self.emplacement = emplacement
        self.prestataires: list[dict] = []
        self.charger()

    def charger(self) -> None:
        self.prestataires = charger_donnees(self.emplacement, [])

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.prestataires)

    def trouver(self, prestataire_id: str) -> dict | None:
        return premier(self.prestataires, id=prestataire_id)

    def ajouter(self, fiche: dict, prestataire_id: str | None = None) -> str:
        for existant in self.prestataires:
            if meme_fiche(existant, fiche):
                for cle in CHAMPS_FICHE:
                    if not existant.get(cle) and fiche.get(cle):
                        existant[cle] = fiche[cle]

                self.sauvegarder()
                return existant["id"]

        nouveau: dict[str, Any] = {cle: fiche.get(cle) or ("" if cle != "tarif_indicatif" else 0) for cle in CHAMPS_FICHE}
        nouveau["id"] = prestataire_id or uuid.uuid4().hex[:8]
        self.prestataires.append(nouveau)
        self.sauvegarder()

        return nouveau["id"]


class Carnet:
    def __init__(self, annuaire: "Annuaire", emplacement: Emplacement) -> None:
        self.annuaire = annuaire
        self.emplacement = emplacement
        self.selection: list[dict] = []
        self.charger()

    def charger(self) -> None:
        self.selection = charger_donnees(self.emplacement, [])

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.selection)

    @property
    def prestataires(self) -> list[dict]:
        fusion = []

        for choix in self.selection:
            fiche = self.annuaire.trouver(choix["prestataire_id"])

            if fiche:
                fusion.append({**fiche, **{cle: choix.get(cle) for cle in CHAMPS_DU_DOSSIER}, "id": fiche["id"]})

        return fusion

    def choix(self, prestataire_id: str) -> dict | None:
        return premier(self.selection, prestataire_id=prestataire_id)

    def selectionner(self, prestataire_id: str, tarif_indicatif: float | None = None, poste_budget: str | None = None) -> None:
        if self.choix(prestataire_id):
            return

        fiche = self.annuaire.trouver(prestataire_id)
        self.selection.append({
            "prestataire_id": prestataire_id,
            "statut": STATUTS[0],
            "statut_depuis": date.today().isoformat(),
            "tarif_indicatif": tarif_indicatif or (fiche or {}).get("tarif_indicatif") or 0,
            "poste_budget": poste_budget
        })
        self.sauvegarder()

    def ajouter_prestataire(
        self, nom: str, categorie: str, contact: str, telephone: str, email: str, lien: str,
        tarif_indicatif: float, poste_budget: str | None, notes: str
    ) -> str:
        fiche = {
            "nom": nom, "categorie": categorie, "contact": contact, "telephone": telephone, "email": email,
            "lien": lien, "tarif_indicatif": tarif_indicatif, "notes": notes
        }
        prestataire_id = self.annuaire.ajouter(fiche)
        self.selectionner(prestataire_id, tarif_indicatif, poste_budget)

        return prestataire_id

    def disponibles(self) -> list[dict]:
        choisis = {element["prestataire_id"] for element in self.selection}
        return [fiche for fiche in self.annuaire.prestataires if fiche["id"] not in choisis]

    def trouver(self, prestataire_id: str) -> dict | None:
        return premier(self.prestataires, id=prestataire_id)

    def trouver_par_nom(self, nom: str) -> dict | None:
        for prestataire in self.prestataires:
            if meme_nom(prestataire["nom"], nom):
                return prestataire

        return None

    def changer_statut(self, prestataire_id: str, statut: str, depuis: str | None = None) -> None:
        element = self.choix(prestataire_id)

        if element:
            element["statut"] = statut
            element["statut_depuis"] = depuis or date.today().isoformat()
            self.sauvegarder()

    def modifier_conditions(self, prestataire_id: str, tarif_indicatif: float, poste_budget: str | None) -> None:
        element = self.choix(prestataire_id)

        if element:
            element["tarif_indicatif"] = tarif_indicatif
            element["poste_budget"] = poste_budget
            self.sauvegarder()

    def supprimer(self, prestataire_id: str) -> None:
        self.selection = [element for element in self.selection if element["prestataire_id"] != prestataire_id]
        self.sauvegarder()

    def par_categorie(self) -> dict[str, list[dict]]:
        groupes = {}

        for categorie in CATEGORIES:
            membres = [prestataire for prestataire in self.prestataires if prestataire["categorie"] == categorie]

            if membres:
                groupes[categorie] = membres

        return groupes

    def compter_par_statut(self) -> dict[str, int]:
        prestataires = self.prestataires
        return {
            statut: sum(1 for prestataire in prestataires if prestataire["statut"] == statut)
            for statut in STATUTS
        }
