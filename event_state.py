import json
import os


class EventSheet:
    def __init__(self, file_path="./event_data.json"):
        self.file_path = file_path
        self.data = {
            "type_evenement": None,
            "date": None,
            "lieu": None,
            "budget": None,
            "nombre_invites": None,
            "theme": None,
            "allergies_interdits": [],
            "prestataires": []
        }
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.data = json.load(file)

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def update(self, new_info):
        for key, value in new_info.items():
            if key in self.data and value:
                self.data[key] = value
        self.save()
