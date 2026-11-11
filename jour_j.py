import re

from fpdf import FPDF

from devis import texte_pdf, date_lisible
from storage import load_json, save_json


COLONNES_DEROULE = ["heure", "moment", "lieu", "intervenants", "details"]

DEBUT_DE_JOURNEE = "06:00"


def heure_valide(texte):
    correspondance = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})?", str(texte or ""))

    if not correspondance:
        return ""

    heures, minutes = int(correspondance.group(1)), int(correspondance.group(2) or 0)

    return f"{heures:02d}:{minutes:02d}" if heures < 24 and minutes < 60 else ""


def texte(valeur):
    return valeur.strip() if isinstance(valeur, str) else ""


def nettoyer_deroule(lignes):
    deroule = [
        {
            "heure": heure_valide(ligne.get("heure")),
            "moment": texte(ligne.get("moment")),
            "lieu": texte(ligne.get("lieu")),
            "intervenants": texte(ligne.get("intervenants")),
            "details": texte(ligne.get("details"))
        }
        for ligne in lignes
        if texte(ligne.get("moment"))
    ]

    return sorted(deroule, key=ordre_dans_la_journee)


def ordre_dans_la_journee(ligne):
    if not ligne["heure"]:
        return (2, "")

    return (int(ligne["heure"] < DEBUT_DE_JOURNEE), ligne["heure"])


class JourJ:
    def __init__(self, file_path="./jour_j_data.json"):
        self.file_path = file_path
        self.deroule = []
        self.load()

    def load(self):
        data = load_json(self.file_path, {"deroule": []})
        self.deroule = data["deroule"]

    def save(self):
        save_json(self.file_path, {"deroule": self.deroule})

    def set_deroule(self, deroule):
        self.deroule = nettoyer_deroule(deroule)
        self.save()

    def creneaux_de(self, nom):
        return [ligne for ligne in self.deroule if nom.lower() in ligne["intervenants"].lower()]


def generer_deroule_pdf(deroule, event_data):
    pdf = FPDF(orientation="landscape")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    titre = " - ".join(filter(None, ["Déroulé du jour J", event_data["noms"], date_lisible(event_data["date"])]))
    pdf.cell(0, 10, texte_pdf(titre), new_x="LMARGIN", new_y="NEXT")

    if event_data["lieu"]:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, texte_pdf(event_data["lieu"]), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)

    with pdf.table(col_widths=(18, 55, 45, 60, 99), line_height=6) as tableau:
        tableau.row([texte_pdf(entete) for entete in ["Heure", "Moment", "Lieu", "Qui", "Détails"]])

        for ligne in deroule:
            tableau.row([texte_pdf(ligne[colonne]) for colonne in COLONNES_DEROULE])

    return bytes(pdf.output())
