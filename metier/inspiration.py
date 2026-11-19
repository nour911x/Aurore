import re
from typing import Any
from urllib.parse import quote

from fpdf import FPDF

from donnees.stockage import charger_json, sauvegarder_json
from metier.devis import texte_pdf


ELEMENTS_MOODBOARD = ["Décoration", "Fleurs", "Tenues", "Gâteau", "Table", "Papeterie"]

CATEGORIES_BEAUTE = {
    "Robe de mariée": "Tenues",
    "Costume": "Tenues",
    "Chaussures & accessoires": "Tenues",
    "Bijoux & alliances": "Autre",
    "Maquillage": "Maquillage / Coiffure",
    "Coiffure": "Maquillage / Coiffure"
}

COULEUR_PAR_DEFAUT = "#CCCCCC"


def lien_pinterest(recherche: str) -> str:
    return f"https://www.pinterest.fr/search/pins/?q={quote(recherche)}"


def lien_maps(recherche: str, lieu: str | None) -> str:
    return f"https://www.google.com/maps/search/{quote(' '.join(filter(None, [recherche, lieu])))}"


def couleur_valide(code: Any) -> str:
    return code if isinstance(code, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", code) else COULEUR_PAR_DEFAUT


def nettoyer_moodboard(moodboard: dict) -> dict:
    recherches = moodboard.get("recherches") or {}

    return {
        "titre": moodboard.get("titre") or "Moodboard",
        "ambiance": moodboard.get("ambiance") or "",
        "couleurs": [
            {"nom": couleur.get("nom") or "", "hex": couleur_valide(couleur.get("hex"))}
            for couleur in moodboard.get("couleurs") or []
            if isinstance(couleur, dict)
        ],
        "mots_cles": [mot for mot in moodboard.get("mots_cles") or [] if isinstance(mot, str)],
        "liens": {
            element: lien_pinterest(recherches[element])
            for element in ELEMENTS_MOODBOARD
            if isinstance(recherches.get(element), str)
        }
    }


class Inspiration:
    def __init__(self, chemin_fichier: str) -> None:
        self.chemin_fichier = chemin_fichier
        self.moodboard: dict = {}
        self.recommandations: dict = {}
        self.charger()

    def charger(self) -> None:
        donnees = charger_json(self.chemin_fichier, {"moodboard": {}, "recommandations": {}})
        self.moodboard = donnees["moodboard"]
        self.recommandations = donnees["recommandations"]

    def sauvegarder(self) -> None:
        sauvegarder_json(self.chemin_fichier, {"moodboard": self.moodboard, "recommandations": self.recommandations})

    def definir_moodboard(self, moodboard: dict) -> None:
        self.moodboard = nettoyer_moodboard(moodboard)
        self.sauvegarder()

    def definir_recommandation(self, categorie: str, recommandation: Any) -> None:
        self.recommandations[categorie] = recommandation
        self.sauvegarder()


def hex_vers_rgb(code: str) -> tuple[int, ...]:
    return tuple(int(code[index:index + 2], 16) for index in (1, 3, 5))


def generer_moodboard_pdf(moodboard: dict, noms: str, avec_liens: bool = True) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(150, 100, 125)
    pdf.cell(0, 6, texte_pdf(f"Moodboard - {noms}" if noms else "Moodboard"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "BI", 28)
    pdf.cell(0, 14, texte_pdf(moodboard["titre"]), new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(0, 6, texte_pdf(moodboard["ambiance"]))
    pdf.ln(8)

    taille = 30
    y = pdf.get_y()

    for index, couleur in enumerate(moodboard["couleurs"][:6]):
        x = pdf.l_margin + index * (taille + 2)
        pdf.set_fill_color(*hex_vers_rgb(couleur["hex"]))
        pdf.rect(x, y, taille, taille, style="F")
        pdf.set_xy(x, y + taille + 1)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(taille, 4, texte_pdf(f"{couleur['nom']}\n{couleur['hex']}"), align="C")

    pdf.set_y(y + taille + 14)

    if moodboard["mots_cles"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Mots-clés", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, texte_pdf(" · ".join(moodboard["mots_cles"]).replace("·", "-")))
        pdf.ln(4)

    if not avec_liens:
        return bytes(pdf.output())

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, texte_pdf("Inspirations Pinterest (cliquer pour ouvrir)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "U", 11)
    pdf.set_text_color(150, 100, 125)

    for element, lien in moodboard["liens"].items():
        pdf.cell(0, 7, texte_pdf(f"> {element}"), link=lien, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
