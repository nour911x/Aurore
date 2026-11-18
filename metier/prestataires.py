import re
import uuid
from datetime import date
from urllib.parse import quote

from donnees.storage import load_json, save_json


CATEGORIES = [
    "Traiteur",
    "DJ / Musiciens",
    "Domaine / Salle",
    "Photographe",
    "Fleuriste",
    "Tenues",
    "Maquillage / Coiffure",
    "Autre"
]

STATUTS = ["À contacter", "Devis demandé", "Devis reçu", "Réservé", "Refusé"]


def numero_international(telephone):
    chiffres = re.sub(r"\D", "", telephone)

    if chiffres.startswith("00"):
        return chiffres[2:]

    if chiffres.startswith("0") and len(chiffres) == 10:
        return "33" + chiffres[1:]

    return chiffres


def lien_whatsapp(telephone, message=""):
    lien = f"https://wa.me/{numero_international(telephone)}"

    if message:
        lien += f"?text={quote(message)}"

    return lien


def lien_email(email, sujet="", message=""):
    return f"mailto:{email}?subject={quote(sujet)}&body={quote(message)}"


def normaliser_nom(nom):
    return nom.replace("’", "'").strip().lower()


def meme_nom(premier, second):
    return normaliser_nom(premier) == normaliser_nom(second)


def appliquer_statut(carnet, event_sheet, prestataire, statut):
    carnet.changer_statut(prestataire["id"], statut)

    if statut == "Réservé":
        event_sheet.ajouter_prestataire(f"{prestataire['nom']} ({prestataire['categorie']})")


CHAMPS_FICHE = ["nom", "categorie", "contact", "telephone", "email", "lien", "tarif_indicatif", "notes"]

CHAMPS_DU_DOSSIER = ["statut", "statut_depuis", "tarif_indicatif", "poste_budget"]


def normaliser_contact(valeur, cle):
    valeur = valeur or ""
    return re.sub(r"\D", "", valeur) if cle == "telephone" else valeur.strip().lower()


def contact_identique(premier, second, cle):
    a, b = normaliser_contact(premier.get(cle), cle), normaliser_contact(second.get(cle), cle)
    return not a or not b or a == b


def meme_fiche(premier, second):
    return meme_nom(premier["nom"], second["nom"]) and all(
        contact_identique(premier, second, cle) for cle in ("telephone", "email")
    )


def reservations_en_double(reservations):
    par_jour = {}

    for reservation in reservations:
        if reservation["date"]:
            par_jour.setdefault((reservation["prestataire_id"], reservation["date"]), []).append(reservation)

    return [
        {"prestataire": groupe[0]["nom"], "date": date_evenement, "dossiers": [element["dossier"] for element in groupe]}
        for (_, date_evenement), groupe in sorted(par_jour.items(), key=lambda element: element[0][1])
        if len({element["dossier_id"] for element in groupe}) > 1
    ]


class Annuaire:
    def __init__(self, file_path):
        self.file_path = file_path
        self.prestataires = []
        self.load()

    def load(self):
        self.prestataires = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.prestataires)

    def trouver(self, prestataire_id):
        for prestataire in self.prestataires:
            if prestataire["id"] == prestataire_id:
                return prestataire

        return None

    def ajouter(self, fiche, prestataire_id=None):
        for existant in self.prestataires:
            if meme_fiche(existant, fiche):
                for cle in CHAMPS_FICHE:
                    if not existant.get(cle) and fiche.get(cle):
                        existant[cle] = fiche[cle]

                self.save()
                return existant["id"]

        nouveau = {cle: fiche.get(cle) or ("" if cle != "tarif_indicatif" else 0) for cle in CHAMPS_FICHE}
        nouveau["id"] = prestataire_id or uuid.uuid4().hex[:8]
        self.prestataires.append(nouveau)
        self.save()

        return nouveau["id"]


class Carnet:
    def __init__(self, annuaire, file_path):
        self.annuaire = annuaire
        self.file_path = file_path
        self.selection = []
        self.load()

    def load(self):
        self.selection = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.selection)

    @property
    def prestataires(self):
        fusion = []

        for choix in self.selection:
            fiche = self.annuaire.trouver(choix["prestataire_id"])

            if fiche:
                fusion.append({**fiche, **{cle: choix.get(cle) for cle in CHAMPS_DU_DOSSIER}, "id": fiche["id"]})

        return fusion

    def choix(self, prestataire_id):
        for element in self.selection:
            if element["prestataire_id"] == prestataire_id:
                return element

        return None

    def selectionner(self, prestataire_id, tarif_indicatif=None, poste_budget=None):
        if self.choix(prestataire_id):
            return

        fiche = self.annuaire.trouver(prestataire_id)
        self.selection.append({
            "prestataire_id": prestataire_id,
            "statut": STATUTS[0],
            "statut_depuis": date.today().isoformat(),
            "tarif_indicatif": tarif_indicatif or fiche.get("tarif_indicatif") or 0,
            "poste_budget": poste_budget
        })
        self.save()

    def add_prestataire(self, nom, categorie, contact, telephone, email, lien, tarif_indicatif, poste_budget, notes):
        fiche = {
            "nom": nom, "categorie": categorie, "contact": contact, "telephone": telephone, "email": email,
            "lien": lien, "tarif_indicatif": tarif_indicatif, "notes": notes
        }
        prestataire_id = self.annuaire.ajouter(fiche)
        self.selectionner(prestataire_id, tarif_indicatif, poste_budget)

        return prestataire_id

    def disponibles(self):
        choisis = {element["prestataire_id"] for element in self.selection}
        return [fiche for fiche in self.annuaire.prestataires if fiche["id"] not in choisis]

    def trouver(self, prestataire_id):
        for prestataire in self.prestataires:
            if prestataire["id"] == prestataire_id:
                return prestataire

        return None

    def trouver_par_nom(self, nom):
        for prestataire in self.prestataires:
            if meme_nom(prestataire["nom"], nom):
                return prestataire

        return None

    def changer_statut(self, prestataire_id, statut, depuis=None):
        element = self.choix(prestataire_id)

        if element:
            element["statut"] = statut
            element["statut_depuis"] = depuis or date.today().isoformat()
            self.save()

    def modifier_conditions(self, prestataire_id, tarif_indicatif, poste_budget):
        element = self.choix(prestataire_id)

        if element:
            element["tarif_indicatif"] = tarif_indicatif
            element["poste_budget"] = poste_budget
            self.save()

    def supprimer(self, prestataire_id):
        self.selection = [element for element in self.selection if element["prestataire_id"] != prestataire_id]
        self.save()

    def par_categorie(self):
        groupes = {}

        for categorie in CATEGORIES:
            membres = [prestataire for prestataire in self.prestataires if prestataire["categorie"] == categorie]

            if membres:
                groupes[categorie] = membres

        return groupes

    def compter_par_statut(self):
        prestataires = self.prestataires
        return {
            statut: sum(1 for prestataire in prestataires if prestataire["statut"] == statut)
            for statut in STATUTS
        }
