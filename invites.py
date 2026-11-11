import csv
import io
import uuid
from collections import Counter

from fpdf import FPDF

from devis import texte_pdf, date_lisible
from storage import load_json, save_json


GROUPES = ["Famille", "Amis", "Collègues", "Autre"]

STATUTS_INVITE = ["À inviter", "Invité", "Confirmé", "Décliné"]

REGIMES = ["Aucun", "Végétarien", "Végan", "Sans gluten", "Sans lactose", "Halal", "Casher", "Sans porc", "Autre"]


def texte(valeur):
    return valeur.strip() if isinstance(valeur, str) else ""


def entier(valeur):
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return 0

    return int(valeur) if valeur == valeur else 0


def choix(valeur, options):
    return valeur if valeur in options else options[0]


def nouvel_invite(nom, groupe="Autre", telephone="", email="", accompagnants=0, regime="Aucun", allergies="", statut="À inviter", invite_id=None):
    return {
        "id": invite_id or uuid.uuid4().hex[:8],
        "nom": nom,
        "groupe": choix(groupe, GROUPES),
        "telephone": telephone,
        "email": email,
        "accompagnants": accompagnants,
        "regime": choix(regime, REGIMES),
        "allergies": allergies,
        "statut": choix(statut, STATUTS_INVITE)
    }


def nettoyer(lignes):
    return [
        nouvel_invite(
            texte(ligne.get("nom")),
            ligne.get("groupe"),
            texte(ligne.get("telephone")),
            texte(ligne.get("email")),
            entier(ligne.get("accompagnants")),
            ligne.get("regime"),
            texte(ligne.get("allergies")),
            ligne.get("statut"),
            texte(ligne.get("id"))
        )
        for ligne in lignes
        if texte(ligne.get("nom"))
    ]


def lire_vcf(contenu):
    contacts = []

    for carte in contenu.split("BEGIN:VCARD")[1:]:
        contact = {"nom": "", "telephone": "", "email": ""}

        for ligne in carte.splitlines():
            cle, _, valeur = ligne.partition(":")
            cle = cle.split(";")[0].upper()

            if cle == "FN":
                contact["nom"] = valeur.strip()
            elif cle == "TEL" and not contact["telephone"]:
                contact["telephone"] = valeur.strip()
            elif cle == "EMAIL" and not contact["email"]:
                contact["email"] = valeur.strip()

        contacts.append(contact)

    return contacts


def colonne(ligne, *mots):
    for nom_colonne, valeur in ligne.items():
        if nom_colonne and texte(valeur) and any(mot in nom_colonne.lower() for mot in mots):
            return texte(valeur)

    return ""


def lire_csv(contenu):
    separateur = ";" if contenu.count(";") > contenu.count(",") else ","
    contacts = []

    for ligne in csv.DictReader(io.StringIO(contenu), delimiter=separateur):
        colonnes_exactes = {nom_colonne.strip().lower(): valeur for nom_colonne, valeur in ligne.items() if nom_colonne}
        nom_famille = colonne(ligne, "last", "nom de famille") or texte(colonnes_exactes.get("nom"))
        prenom_nom = " ".join(filter(None, [colonne(ligne, "first", "prénom", "prenom"), nom_famille]))
        contacts.append({
            "nom": colonne(ligne, "full name", "nom complet") or prenom_nom or colonne(ligne, "name", "nom"),
            "telephone": colonne(ligne, "phone", "mobile", "tél", "tel"),
            "email": colonne(ligne, "mail")
        })

    return contacts


def lire_contacts(nom_fichier, contenu_brut):
    try:
        contenu = contenu_brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        contenu = contenu_brut.decode("latin-1")

    lecteur = lire_vcf if nom_fichier.lower().endswith(".vcf") else lire_csv

    return [contact for contact in lecteur(contenu) if contact["nom"]]


class ListeInvites:
    def __init__(self, file_path="./invites_data.json"):
        self.file_path = file_path
        self.invites = []
        self.faire_part = ""
        self.load()

    def load(self):
        data = load_json(self.file_path, {"invites": [], "faire_part": ""})
        self.invites = data["invites"]
        self.faire_part = data["faire_part"]

    def save(self):
        save_json(self.file_path, {"invites": self.invites, "faire_part": self.faire_part})

    def remplacer(self, invites):
        self.invites = invites
        self.save()

    def importer(self, contacts, groupe):
        deja_la = {(invite["nom"].lower(), invite["telephone"]) for invite in self.invites}
        nouveaux = [
            nouvel_invite(contact["nom"], groupe, contact["telephone"], contact["email"])
            for contact in contacts
            if (contact["nom"].lower(), contact["telephone"]) not in deja_la
        ]
        self.remplacer(self.invites + nouveaux)

        return len(nouveaux)

    def changer_statut(self, invite_id, statut):
        for invite in self.invites:
            if invite["id"] == invite_id:
                invite["statut"] = statut
        self.save()

    def set_faire_part(self, contenu):
        self.faire_part = contenu
        self.save()

    def personnes(self, statuts):
        return sum(1 + invite["accompagnants"] for invite in self.invites if invite["statut"] in statuts)

    def compter_par_statut(self):
        return Counter(invite["statut"] for invite in self.invites)

    def recap_traiteur(self):
        confirmes = [invite for invite in self.invites if invite["statut"] == "Confirmé"]

        return {
            "couverts_confirmes": self.personnes(["Confirmé"]),
            "couverts_attendus": self.personnes(["Invité", "Confirmé"]),
            "regimes": dict(Counter(invite["regime"] for invite in confirmes if invite["regime"] != "Aucun")),
            "allergies": {invite["nom"]: invite["allergies"] for invite in confirmes if invite["allergies"]}
        }


def message_personnel(invite, faire_part):
    prenom = invite["nom"].split()[0]
    return f"Bonjour {prenom},\n\n{faire_part}"


def generer_faire_part_pdf(faire_part, event_data):
    pdf = FPDF(format=(148, 210))
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    pdf.set_draw_color(190, 150, 170)
    pdf.rect(8, 8, 132, 194)
    pdf.rect(10, 10, 128, 190)

    pdf.set_y(50)
    pdf.set_text_color(150, 100, 125)
    pdf.set_font("Times", "BI", 26)
    noms = (event_data["noms"] or "").replace(" et ", " & ")
    pdf.multi_cell(0, 12, texte_pdf(noms), align="C")

    pdf.line(54, pdf.get_y() + 4, 94, pdf.get_y() + 4)
    pdf.ln(14)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Times", "", 12)
    pdf.set_x(20)
    pdf.multi_cell(108, 6.5, texte_pdf(faire_part), align="C")

    details = " - ".join(filter(None, [date_lisible(event_data["date"]), event_data["lieu"]]))

    if details:
        pdf.set_y(178)
        pdf.set_text_color(150, 100, 125)
        pdf.set_font("Times", "I", 12)
        pdf.cell(0, 8, texte_pdf(details), align="C")

    return bytes(pdf.output())
