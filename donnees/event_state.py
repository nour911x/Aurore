from datetime import date

from config.evenements import CHAMPS_SPECIFIQUES, TYPES_EVENEMENT, champs_par_defaut
from donnees.storage import load_json, save_json
from metier.rgpd import CHAMPS_CONSENTEMENT, CHAMPS_SANTE, sans_sante
from textes import format_person_name


CHAMPS_POUR_PRESTATAIRE = [
    "type_evenement", "noms", "date", "lieu", "nombre_invites", "theme",
    "allergies_interdits", "preferences", *CHAMPS_SPECIFIQUES
]


CHAMPS_PROTEGES = {"historique", "demo", *CHAMPS_CONSENTEMENT}


def renseigne(valeur):
    return valeur is False or bool(valeur)


class EventSheet:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = {
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
        self.load()

    def load(self):
        self.data.update(load_json(self.file_path, {}))
        self.normaliser_noms()

    def normaliser_noms(self):
        if isinstance(self.data["noms"], list):
            self.data["noms"] = " et ".join(self.data["noms"]) or None

        self.data["noms"] = format_person_name(self.data["noms"]) or None

    def save(self):
        save_json(self.file_path, self.data)

    def infos_pour_prestataire(self, avec_sante=False):
        infos = {key: self.data[key] for key in CHAMPS_POUR_PRESTATAIRE}
        return infos if avec_sante else sans_sante(infos)

    def infos_sans_historique(self, avec_sante=False):
        infos = {key: value for key, value in self.data.items() if key not in CHAMPS_PROTEGES}
        return infos if avec_sante else sans_sante(infos)

    def update(self, new_info):
        for key, value in new_info.items():
            if key in CHAMPS_SANTE and isinstance(value, list):
                value = self.data[key] + [element for element in value if element not in self.data[key]]

            if key in self.data and key not in CHAMPS_PROTEGES and renseigne(value):
                self.data[key] = value
        self.normaliser_noms()
        self.save()

    def remplacer(self, new_info):
        for key, value in new_info.items():
            if key in self.data and key not in CHAMPS_PROTEGES:
                self.data[key] = value
        self.normaliser_noms()
        self.save()

    def changer_type(self, cle_type):
        self.remplacer({"type_evenement": TYPES_EVENEMENT[cle_type]["libelle"]})

    def set_consentement(self, cle, valeur):
        self.data[cle] = valeur
        self.save()

    def ajouter_prestataire(self, description):
        if description not in self.data["prestataires"]:
            self.data["prestataires"].append(description)
            self.save()

    def add_echange(self, source, resume):
        self.data["historique"].append({
            "date": date.today().isoformat(),
            "source": source,
            "resume": resume
        })
        self.save()
