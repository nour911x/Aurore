import re

from fpdf import FPDF

from devis import texte_pdf, date_lisible
from prestataires import normaliser_nom
from storage import load_json, save_json


COLONNES_DEROULE = ["heure", "moment", "lieu", "intervenants", "details"]

DEBUT_DE_JOURNEE = "06:00"

TABLE_HONNEUR = "Table d'honneur"

FORMES_TABLE = ["Ronde", "Rectangulaire"]

ELEMENTS_SALLE = ["Piste de danse", "Buffet", "DJ", "Bar", "Photobooth"]

AUCUNE_TABLE = "—"


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


def personnes(invite):
    return 1 + invite["accompagnants"]


def invites_a_placer(invites):
    return [invite for invite in invites if invite["statut"] != "Décliné"]


def creer_tables(nombre, places, forme, places_honneur):
    tables = [{"nom": TABLE_HONNEUR, "places": places_honneur, "forme": "Rectangulaire"}] if places_honneur else []

    return tables + [{"nom": f"Table {numero}", "places": places, "forme": forme} for numero in range(1, nombre + 1)]


class JourJ:
    def __init__(self, file_path="./jour_j_data.json"):
        self.file_path = file_path
        self.deroule = []
        self.salle = {"tables": [], "elements": [], "placement": {}}
        self.load()

    def load(self):
        data = load_json(self.file_path, {})
        self.deroule = data.get("deroule", [])
        self.salle = data.get("salle", self.salle)

    def save(self):
        save_json(self.file_path, {"deroule": self.deroule, "salle": self.salle})

    def set_deroule(self, deroule):
        self.deroule = nettoyer_deroule(deroule)
        self.save()

    def amenager(self, tables, elements):
        noms = {table["nom"] for table in tables}
        self.salle = {
            "tables": tables,
            "elements": elements,
            "placement": {invite: table for invite, table in self.salle["placement"].items() if table in noms}
        }
        self.save()

    def placer(self, souhaits, invites):
        if len(souhaits) == 1 and isinstance(next(iter(souhaits.values())), dict):
            souhaits = next(iter(souhaits.values()))

        places_libres = {table["nom"]: table["places"] for table in self.salle["tables"]}
        noms_exacts = {normaliser_nom(nom): nom for nom in places_libres}
        placement = {}

        for invite in invites_a_placer(invites):
            table = noms_exacts.get(normaliser_nom(str(souhaits.get(invite["id"], ""))))

            if table and places_libres[table] >= personnes(invite):
                placement[invite["id"]] = table
                places_libres[table] -= personnes(invite)

        self.salle["placement"] = placement
        self.save()

        return len(placement)

    def par_table(self, invites):
        repartition = {table["nom"]: [] for table in self.salle["tables"]}

        for invite in invites_a_placer(invites):
            table = self.salle["placement"].get(invite["id"])

            if table in repartition:
                repartition[table].append(invite)

        return repartition

    def non_places(self, invites):
        return [invite for invite in invites_a_placer(invites) if invite["id"] not in self.salle["placement"]]


def generer_plan_table_pdf(repartition, event_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, texte_pdf(" - ".join(filter(None, ["Plan de table", event_data["noms"]]))), new_x="LMARGIN", new_y="NEXT")

    for table, invites in repartition.items():
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, texte_pdf(f"{table} ({sum(personnes(invite) for invite in invites)} couverts)"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

        if not invites:
            continue

        with pdf.table(col_widths=(70, 30, 40, 50), line_height=6) as tableau:
            tableau.row([texte_pdf(entete) for entete in ["Invité", "Accompagnants", "Régime", "Allergies"]])

            for invite in invites:
                regime = "" if invite["regime"] == "Aucun" else invite["regime"]
                tableau.row([texte_pdf(valeur) for valeur in [invite["nom"], str(invite["accompagnants"] or ""), regime, invite["allergies"]]])

    return bytes(pdf.output())


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
