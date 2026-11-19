import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fpdf import FPDF

from config.evenements import libelle_evenement
from donnees.stockage import charger_json, premier, sauvegarder_json
from metier.devis import date_lisible, texte_pdf
from metier.rgpd import consentements_manquants
from textes import noms_clients


CATEGORIES_PHOTO = ["Salle & déco", "Buffet & repas", "Clients", "Invités", "Détails", "Autre"]

TAGS_PHOTO = {"decor": "Décor, sans personne", "avec_personnes": "Avec personnes"}

EXTENSIONS = {"image/png": ".png", "image/webp": ".webp"}


def tag(personnes: list[str] | None) -> str | None:
    return None if personnes is None else "avec_personnes" if personnes else "decor"


def publiable(photo: dict, droit_image: list[dict], usage: str = "Réseaux sociaux") -> tuple:
    if photo["personnes"] is None:
        return False, "à analyser avant publication"

    if not photo["personnes"]:
        return True, "décor, aucune personne reconnaissable"

    if photo["categorie"] != "Clients":
        return False, "des invités sont reconnaissables et n'ont pas donné leur accord"

    manquants = consentements_manquants(droit_image, usage)

    if manquants:
        return False, f"consentement insuffisant pour cet usage ({', '.join(manquants)})"

    return True, "consentement de droit à l'image de chaque client pour cet usage"


class Galerie:
    def __init__(self, chemin_fichier: str, dossier: Path) -> None:
        self.chemin_fichier = chemin_fichier
        self.dossier = Path(dossier)
        self.photos: list[dict] = []
        self.avis: list[dict] = []
        self.charger()

    def charger(self) -> None:
        donnees = charger_json(self.chemin_fichier, {"photos": [], "avis": []})
        self.photos = donnees["photos"]
        self.avis = donnees["avis"]

    def sauvegarder(self) -> None:
        sauvegarder_json(self.chemin_fichier, {"photos": self.photos, "avis": self.avis})

    def ajouter_photo(self, contenu: bytes, type_mime: str) -> dict:
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
        self.sauvegarder()

        return photo

    def lire(self, photo: dict) -> bytes:
        return (self.dossier / photo["fichier"]).read_bytes()

    def trouver(self, photo_id: str) -> dict | None:
        return premier(self.photos, id=photo_id)

    def modifier(self, photo_id: str, **champs: Any) -> None:
        photo = self.trouver(photo_id)

        if photo:
            photo.update(champs)
            self.sauvegarder()

    def supprimer(self, photo_id: str) -> None:
        photo = self.trouver(photo_id)

        if photo:
            (self.dossier / photo["fichier"]).unlink(missing_ok=True)
            self.photos.remove(photo)
            self.sauvegarder()

    def a_analyser(self) -> list[dict]:
        return [photo for photo in self.photos if photo["personnes"] is None]

    def publiables(self, droit_image: list[dict], usage: str = "Réseaux sociaux") -> list[dict]:
        return [photo for photo in self.photos if publiable(photo, droit_image, usage)[0]]

    def ajouter_avis(self, auteur: str, note: int, commentaire: str) -> None:
        self.avis.append({
            "id": uuid.uuid4().hex[:8],
            "date": date.today().isoformat(),
            "auteur": auteur,
            "note": note,
            "commentaire": commentaire,
            "post": ""
        })
        self.sauvegarder()

    def modifier_avis(self, avis_id: str, **champs: Any) -> None:
        avis = premier(self.avis, id=avis_id)

        if avis:
            avis.update(champs)
            self.sauvegarder()


def generer_autorisation_pdf(donnees_evenement: dict) -> bytes:
    noms = noms_clients(donnees_evenement, "les clients")
    evenement = " ".join(filter(None, [
        f"notre {libelle_evenement(donnees_evenement).lower()}",
        f"du {date_lisible(donnees_evenement['date'])}" if donnees_evenement["date"] else "",
        f"à {donnees_evenement['lieu']}" if donnees_evenement["lieu"] else ""
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
