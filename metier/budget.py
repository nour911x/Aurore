from datetime import date, timedelta

from donnees.storage import load_json, save_json
from metier.prestataires import meme_nom, normaliser_nom


POSTE_ORGANISATION = "Organisation"

DELAI_ACOMPTE = 7


class Budget:
    def __init__(self, file_path):
        self.file_path = file_path
        self.postes = []
        self.load()

    def load(self):
        self.postes = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.postes)

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

    def facture_existe(self, libelle):
        return any(facture["libelle"] == libelle for poste in self.postes for facture in poste["factures"])

    def engage_du_poste(self, poste):
        return sum(facture["montant"] for facture in poste["factures"])

    def depense_du_poste(self, poste):
        return sum(facture["montant"] for facture in poste["factures"] if facture["payee"])

    def total_engage(self):
        return sum(self.engage_du_poste(poste) for poste in self.postes)

    def resume(self):
        return [
            {"nom": poste["nom"], "montant_prevu": poste["montant_prevu"], "engage": self.engage_du_poste(poste)}
            for poste in self.postes
        ]

    def prevu_pour(self, prestataire):
        for nom_poste in filter(None, [prestataire["poste_budget"], prestataire["categorie"]]):
            for poste in self.postes:
                if meme_nom(poste["nom"], nom_poste):
                    return poste["montant_prevu"]

        return None

    def factures_de(self, prestataire):
        nom = normaliser_nom(prestataire["nom"])
        postes = {prestataire["poste_budget"], prestataire["categorie"]}

        return [
            {**facture, "poste": poste["nom"]}
            for poste in self.postes
            for facture in poste["factures"]
            if poste["nom"] in postes or nom in normaliser_nom(facture["libelle"])
        ]

    def enregistrer_devis(self, numero, montants, poste, echeance_solde):
        if poste not in [poste_existant["nom"] for poste_existant in self.postes]:
            self.add_poste(poste, montants["ttc"])

        factures = [
            (f"Acompte {numero}", montants["acompte"], date.today() + timedelta(days=DELAI_ACOMPTE)),
            (f"Solde {numero}", round(montants["ttc"] - montants["acompte"], 2), echeance_solde)
        ]

        for libelle, montant, echeance in factures:
            if montant and not self.facture_existe(libelle):
                self.add_facture(poste, libelle, montant, str(echeance), False)

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
