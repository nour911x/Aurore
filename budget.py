import json
import os
from datetime import date


class Budget:
    def __init__(self, file_path="./budget_data.json"):
        self.file_path = file_path
        self.postes = []
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.postes = json.load(file)

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.postes, file, ensure_ascii=False, indent=4)

    def add_poste(self, nom, montant_prevu):
        self.postes.append({
            "nom": nom,
            "montant_prevu": montant_prevu,
            "factures": []
        })
        self.save()

    def add_facture(self, nom_poste, libelle, montant, echeance, payee):
        for poste in self.postes:
            if poste["nom"] == nom_poste:
                poste["factures"].append({
                    "libelle": libelle,
                    "montant": montant,
                    "echeance": echeance,
                    "payee": payee
                })
        self.save()

    def marquer_payee(self, nom_poste, libelle):
        for poste in self.postes:
            if poste["nom"] == nom_poste:
                for facture in poste["factures"]:
                    if facture["libelle"] == libelle:
                        facture["payee"] = True
        self.save()

    def engage_du_poste(self, poste):
        return sum(facture["montant"] for facture in poste["factures"])

    def depense_du_poste(self, poste):
        return sum(facture["montant"] for facture in poste["factures"] if facture["payee"])

    def total_engage(self):
        return sum(self.engage_du_poste(poste) for poste in self.postes)

    def factures_a_payer(self):
        aujourd_hui = date.today()
        a_payer = []

        for poste in self.postes:
            for facture in poste["factures"]:
                if not facture["payee"]:
                    echeance = date.fromisoformat(facture["echeance"])
                    a_payer.append({
                        "poste": poste["nom"],
                        "libelle": facture["libelle"],
                        "montant": facture["montant"],
                        "echeance": facture["echeance"],
                        "jours_restants": (echeance - aujourd_hui).days
                    })

        return sorted(a_payer, key=lambda facture: facture["jours_restants"])
