import json
import os
from datetime import date


class EventSheet:
    def __init__(self, file_path="./event_data.json"):
        self.file_path = file_path
        self.data = {
            "type_evenement": None,
            "noms": None,
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
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.data.update(json.load(file))

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def infos_sans_historique(self):
        return {key: value for key, value in self.data.items() if key != "historique"}

    def update(self, new_info):
        for key, value in new_info.items():
            if key in self.data and key != "historique" and value:
                self.data[key] = value
        self.save()

    def remplacer(self, new_info):
        for key, value in new_info.items():
            if key in self.data and key != "historique":
                self.data[key] = value
        self.save()

    def add_echange(self, source, resume):
        self.data["historique"].append({
            "date": date.today().isoformat(),
            "source": source,
            "resume": resume
        })
        self.save()
