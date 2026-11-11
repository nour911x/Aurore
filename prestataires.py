import json
import os
import re
import uuid
from urllib.parse import quote


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


class Carnet:
    def __init__(self, file_path="./prestataires_data.json"):
        self.file_path = file_path
        self.prestataires = []
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.prestataires = json.load(file)

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.prestataires, file, ensure_ascii=False, indent=4)

    def add_prestataire(self, nom, categorie, contact, telephone, email, lien, tarif_indicatif, poste_budget, notes):
        self.prestataires.append({
            "id": uuid.uuid4().hex[:8],
            "nom": nom,
            "categorie": categorie,
            "contact": contact,
            "telephone": telephone,
            "email": email,
            "lien": lien,
            "tarif_indicatif": tarif_indicatif,
            "poste_budget": poste_budget,
            "notes": notes,
            "statut": STATUTS[0]
        })
        self.save()

    def trouver(self, prestataire_id):
        for prestataire in self.prestataires:
            if prestataire["id"] == prestataire_id:
                return prestataire

        return None

    def trouver_par_nom(self, nom):
        for prestataire in self.prestataires:
            if prestataire["nom"].lower() == nom.strip().lower():
                return prestataire

        return None

    def changer_statut(self, prestataire_id, statut):
        prestataire = self.trouver(prestataire_id)

        if prestataire:
            prestataire["statut"] = statut
            self.save()

    def supprimer(self, prestataire_id):
        self.prestataires = [
            prestataire for prestataire in self.prestataires
            if prestataire["id"] != prestataire_id
        ]
        self.save()

    def par_categorie(self):
        groupes = {}

        for categorie in CATEGORIES:
            membres = [prestataire for prestataire in self.prestataires if prestataire["categorie"] == categorie]

            if membres:
                groupes[categorie] = membres

        return groupes

    def compter_par_statut(self):
        return {
            statut: sum(1 for prestataire in self.prestataires if prestataire["statut"] == statut)
            for statut in STATUTS
        }
