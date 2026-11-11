from datetime import date

from storage import load_json, save_json


CHAMPS_POUR_PRESTATAIRE = [
    "type_evenement", "noms", "date", "lieu", "nombre_invites", "theme",
    "allergies_interdits", "preferences", "preferences_musicales"
]


class EventSheet:
    def __init__(self, file_path="./event_data.json"):
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
            "preferences_musicales": [],
            "prestataires": [],
            "historique": []
        }
        self.load()

    def load(self):
        self.data.update(load_json(self.file_path, {}))
        self.normaliser_noms()

    def normaliser_noms(self):
        if isinstance(self.data["noms"], list):
            self.data["noms"] = " et ".join(self.data["noms"]) or None

    def save(self):
        save_json(self.file_path, self.data)

    def infos_pour_prestataire(self):
        return {key: self.data[key] for key in CHAMPS_POUR_PRESTATAIRE}

    def infos_sans_historique(self):
        return {key: value for key, value in self.data.items() if key != "historique"}

    def update(self, new_info):
        for key, value in new_info.items():
            if key in self.data and key != "historique" and value:
                self.data[key] = value
        self.normaliser_noms()
        self.save()

    def remplacer(self, new_info):
        for key, value in new_info.items():
            if key in self.data and key != "historique":
                self.data[key] = value
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
