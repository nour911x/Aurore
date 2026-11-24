from datetime import date

from config.evenements import CHAMPS_SPECIFIQUES, TYPES_EVENEMENT, champs_par_defaut
from donnees.stockage import Emplacement, charger_donnees, sauvegarder_donnees
from metier.rgpd import CHAMPS_CONSENTEMENT, CHAMPS_SANTE, sans_sante
from textes import formater_nom


CHAMPS_POUR_PRESTATAIRE = [
    "type_evenement", "noms", "date", "lieu", "nombre_invites", "theme",
    "allergies_interdits", "preferences", *CHAMPS_SPECIFIQUES
]


CHAMPS_PROTEGES = {"historique", "demo", *CHAMPS_CONSENTEMENT}


def renseigne(valeur: int | list[str] | str | None) -> bool:
    return valeur is False or bool(valeur)


class FicheEvenement:
    def __init__(self, emplacement: Emplacement) -> None:
        self.emplacement = emplacement
        self.donnees = {
            "type_evenement": None,
            "noms": None,
            "telephone": None,
            "email": None,
            "date": None,
            "lieu": None,
            "budget": None,
            "nombre_invites": None,
            "theme": None,
            "allergies_interdits": [],
            "preferences": [],
            "prestataires": [],
            "historique": [],
            "consentement_sante": None,
            "droit_image": [],
            **champs_par_defaut()
        }
        self.charger()

    def charger(self) -> None:
        self.donnees.update(charger_donnees(self.emplacement, {}))
        self.normaliser_noms()

    def normaliser_noms(self) -> None:
        if isinstance(self.donnees["noms"], list):
            self.donnees["noms"] = " et ".join(self.donnees["noms"]) or None

        self.donnees["noms"] = formater_nom(self.donnees["noms"]) or None

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.donnees)

    def infos_pour_prestataire(self, avec_sante: bool = False) -> dict:
        infos = {cle: self.donnees[cle] for cle in CHAMPS_POUR_PRESTATAIRE}
        return infos if avec_sante else sans_sante(infos)

    def infos_sans_historique(self, avec_sante: bool = False) -> dict:
        infos = {cle: valeur for cle, valeur in self.donnees.items() if cle not in CHAMPS_PROTEGES}
        return infos if avec_sante else sans_sante(infos)

    def mettre_a_jour(self, nouvelles_infos: dict) -> None:
        for cle, valeur in nouvelles_infos.items():
            if cle in CHAMPS_SANTE and isinstance(valeur, list):
                valeur = self.donnees[cle] + [element for element in valeur if element not in self.donnees[cle]]

            if cle in self.donnees and cle not in CHAMPS_PROTEGES and renseigne(valeur):
                self.donnees[cle] = valeur
        self.normaliser_noms()
        self.sauvegarder()

    def remplacer(self, nouvelles_infos: dict) -> None:
        for cle, valeur in nouvelles_infos.items():
            if cle in self.donnees and cle not in CHAMPS_PROTEGES:
                self.donnees[cle] = valeur
        self.normaliser_noms()
        self.sauvegarder()

    def changer_type(self, cle_type: str) -> None:
        self.remplacer({"type_evenement": TYPES_EVENEMENT[cle_type]["libelle"]})

    def definir_consentement(self, cle: str, valeur: dict) -> None:
        self.donnees[cle] = valeur
        self.sauvegarder()

    def ajouter_prestataire(self, description: str) -> None:
        if description not in self.donnees["prestataires"]:
            self.donnees["prestataires"].append(description)
            self.sauvegarder()

    def ajouter_echange(self, source: str, resume: str) -> None:
        self.donnees["historique"].append({
            "date": date.today().isoformat(),
            "source": source,
            "resume": resume
        })
        self.sauvegarder()
