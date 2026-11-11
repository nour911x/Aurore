import uuid
from datetime import date
from pathlib import Path

from fpdf import FPDF

from devis import texte_pdf, date_lisible
from storage import load_json, save_json


CATEGORIES_PHOTO = ["Salle & déco", "Buffet & repas", "Couple", "Invités", "Détails", "Autre"]

STATUTS_DROIT = ["Non demandé", "Demandé", "Accordé", "Refusé"]

EXTENSIONS = {"image/png": ".png", "image/webp": ".webp"}


def publiable(photo, droit_image):
    if photo["personnes"] is None:
        return False, "à analyser avant publication"

    if not photo["personnes"]:
        return True, "aucune personne reconnaissable"

    if photo["categorie"] == "Couple" and droit_image == "Accordé":
        return True, "droit à l'image accordé par les mariés"

    if photo["categorie"] == "Couple":
        return False, "les mariés n'ont pas accordé leur droit à l'image"

    return False, "des invités sont reconnaissables et n'ont pas donné leur accord"


class Galerie:
    def __init__(self, file_path="./galerie_data.json", dossier="./galerie"):
        self.file_path = file_path
        self.dossier = Path(dossier)
        self.photos = []
        self.avis = []
        self.droit_image = STATUTS_DROIT[0]
        self.load()

    def load(self):
        data = load_json(self.file_path, {"photos": [], "avis": [], "droit_image": STATUTS_DROIT[0]})
        self.photos = data["photos"]
        self.avis = data["avis"]
        self.droit_image = data["droit_image"]

    def save(self):
        save_json(self.file_path, {"photos": self.photos, "avis": self.avis, "droit_image": self.droit_image})

    def ajouter_photo(self, contenu, type_mime):
        self.dossier.mkdir(exist_ok=True)
        photo_id = uuid.uuid4().hex[:8]
        fichier = f"{photo_id}{EXTENSIONS.get(type_mime, '.jpg')}"
        (self.dossier / fichier).write_bytes(contenu)
        photo = {
            "id": photo_id,
            "fichier": fichier,
            "date": date.today().isoformat(),
            "categorie": "Autre",
            "personnes": None,
            "description": "",
            "legende": "",
            "publiee": False
        }
        self.photos.append(photo)
        self.save()

        return photo

    def lire(self, photo):
        return (self.dossier / photo["fichier"]).read_bytes()

    def trouver(self, photo_id):
        for photo in self.photos:
            if photo["id"] == photo_id:
                return photo

        return None

    def modifier(self, photo_id, **champs):
        photo = self.trouver(photo_id)

        if photo:
            photo.update(champs)
            self.save()

    def supprimer(self, photo_id):
        photo = self.trouver(photo_id)

        if photo:
            (self.dossier / photo["fichier"]).unlink(missing_ok=True)
            self.photos.remove(photo)
            self.save()

    def a_analyser(self):
        return [photo for photo in self.photos if photo["personnes"] is None]

    def publiables(self):
        return [photo for photo in self.photos if publiable(photo, self.droit_image)[0]]

    def set_droit_image(self, statut):
        self.droit_image = statut
        self.save()

    def ajouter_avis(self, auteur, note, commentaire):
        self.avis.append({
            "id": uuid.uuid4().hex[:8],
            "date": date.today().isoformat(),
            "auteur": auteur,
            "note": note,
            "commentaire": commentaire,
            "post": ""
        })
        self.save()

    def modifier_avis(self, avis_id, **champs):
        for avis in self.avis:
            if avis["id"] == avis_id:
                avis.update(champs)
        self.save()


def generer_autorisation_pdf(event_data):
    noms = event_data["noms"] or "les mariés"
    evenement = " ".join(filter(None, [
        f"notre {event_data['type_evenement'] or 'mariage'}",
        f"du {date_lisible(event_data['date'])}" if event_data["date"] else "",
        f"à {event_data['lieu']}" if event_data["lieu"] else ""
    ]))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, texte_pdf("Autorisation de droit à l'image"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 11)

    paragraphes = [
        f"Nous soussignés, {noms}, autorisons AURORE - Organisation d'événements à utiliser les photographies "
        f"sur lesquelles nous apparaissons, prises lors de {evenement}.",
        "Ces photographies pourront être publiées sur le compte Instagram et le site internet d'AURORE, "
        "uniquement pour présenter son activité. Elles ne seront ni vendues ni cédées à des tiers.",
        "Cette autorisation est donnée gratuitement, pour une durée de cinq ans. Nous pouvons la retirer "
        "à tout moment par simple message : les photos concernées seront alors retirées.",
        "Les photographies sur lesquelles des invités sont reconnaissables ne seront pas publiées sans leur propre accord."
    ]

    for paragraphe in paragraphes:
        pdf.multi_cell(0, 6, texte_pdf(paragraphe))
        pdf.ln(4)

    pdf.ln(8)
    pdf.cell(95, 6, texte_pdf("Fait à ......................., le ..../..../........"))
    pdf.ln(16)

    for colonne in range(2):
        pdf.set_x(pdf.l_margin + colonne * 95)
        pdf.cell(85, 6, texte_pdf("Signature précédée de « Lu et approuvé »"))

    y = pdf.get_y() + 8
    pdf.rect(pdf.l_margin, y, 80, 30)
    pdf.rect(pdf.l_margin + 95, y, 80, 30)

    return bytes(pdf.output())
