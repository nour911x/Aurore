from datetime import date, timedelta
from typing import Any

from fpdf import FPDF

from donnees.stockage import Emplacement, charger_donnees, premier, sauvegarder_donnees


STATUTS_DEVIS = ["Brouillon", "Envoyé", "Accepté", "Refusé"]

REMPLACEMENTS_PDF = {
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "OE", "€": "EUR",
    "\u202f": " ", "\u2009": " ", "\u2011": "-", "\u2010": "-"
}


def nombre(valeur: Any) -> float:
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return 0.0

    return valeur if valeur == valeur else 0.0


def lignes_valides(lignes: list[dict]) -> list[dict]:
    return [
        {
            "designation": ligne["designation"].strip(),
            "quantite": nombre(ligne.get("quantite")),
            "prix_unitaire": nombre(ligne.get("prix_unitaire"))
        }
        for ligne in lignes
        if isinstance(ligne.get("designation"), str) and ligne["designation"].strip()
    ]


def totaux(devis: dict) -> dict:
    total_ht = sum(ligne["quantite"] * ligne["prix_unitaire"] for ligne in devis["lignes"])
    tva = total_ht * devis["tva"] / 100
    total_ttc = total_ht + tva

    return {
        "ht": round(total_ht, 2),
        "tva": round(tva, 2),
        "ttc": round(total_ttc, 2),
        "acompte": round(total_ttc * devis["acompte_pourcent"] / 100, 2)
    }


def euros(montant: float) -> str:
    return f"{montant:,.2f} EUR".replace(",", " ").replace(".", ",")


def texte_pdf(texte: str) -> str:
    for ancien, nouveau in REMPLACEMENTS_PDF.items():
        texte = str(texte).replace(ancien, nouveau)

    return texte.encode("latin-1", "replace").decode("latin-1")


def date_lisible(texte: Any) -> Any:
    try:
        return date.fromisoformat(texte).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return texte


def date_validite(devis: dict) -> date:
    return date.fromisoformat(devis["date"]) + timedelta(days=devis["validite_jours"])


class CarnetDevis:
    def __init__(self, emplacement: Emplacement) -> None:
        self.emplacement = emplacement
        self.devis: list[dict] = []
        self.charger()

    def charger(self) -> None:
        self.devis = charger_donnees(self.emplacement, [])

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.devis)

    def prochain_numero(self) -> str:
        prefixe = f"DEV-{date.today().year}-"
        numeros = [int(devis["numero"].removeprefix(prefixe)) for devis in self.devis if devis["numero"].startswith(prefixe)]

        return f"{prefixe}{max(numeros, default=0) + 1:03d}"

    def ajouter_devis(
        self, emetteur: str, prestataire_id: str | None, destinataire: str, lignes: list[dict],
        tva: float, acompte_pourcent: float, validite_jours: int, notes: str
    ) -> None:
        self.devis.append({
            "numero": self.prochain_numero(),
            "date": date.today().isoformat(),
            "emetteur": emetteur,
            "prestataire_id": prestataire_id,
            "destinataire": destinataire,
            "lignes": lignes,
            "tva": tva,
            "acompte_pourcent": acompte_pourcent,
            "validite_jours": validite_jours,
            "notes": notes,
            "statut": STATUTS_DEVIS[0]
        })
        self.sauvegarder()

    def trouver(self, numero: str) -> dict | None:
        return premier(self.devis, numero=numero)

    def changer_statut(self, numero: str, statut: str) -> None:
        devis = self.trouver(numero)

        if devis:
            devis["statut"] = statut
            self.sauvegarder()

    def supprimer(self, numero: str) -> None:
        self.devis = [devis for devis in self.devis if devis["numero"] != numero]
        self.sauvegarder()


class DevisPDF(FPDF):
    def ligne_tableau(self, valeurs: list[str], largeurs: list[int], gras: bool = False, fond: bool = False) -> None:
        self.set_font("Helvetica", "B" if gras else "", 10)

        if fond:
            self.set_fill_color(245, 235, 240)

        for index, (valeur, largeur) in enumerate(zip(valeurs, largeurs, strict=True)):
            alignement = "L" if index == 0 else "R"
            self.cell(largeur, 8, texte_pdf(valeur), border="B", align=alignement, fill=fond)

        self.ln()


def generer_pdf(devis: dict, donnees_evenement: dict) -> bytes:
    montants = totaux(devis)
    pdf = DevisPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, texte_pdf(devis["emetteur"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, texte_pdf(f"Devis n° {devis['numero']}"), new_x="LMARGIN", new_y="NEXT")
    emission = date.fromisoformat(devis["date"]).strftime("%d/%m/%Y")
    pdf.cell(0, 6, texte_pdf(f"Émis le {emission} - valable jusqu'au {date_validite(devis).strftime('%d/%m/%Y')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    evenement = " - ".join(
        str(valeur) for valeur in [donnees_evenement["type_evenement"], date_lisible(donnees_evenement["date"]), donnees_evenement["lieu"]] if valeur
    )
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, texte_pdf(f"Client : {devis['destinataire']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    if evenement:
        pdf.cell(0, 6, texte_pdf(f"Événement : {evenement}"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    largeurs = [95, 20, 35, 40]
    pdf.ligne_tableau(["Désignation", "Qté", "Prix unit. HT", "Total HT"], largeurs, gras=True, fond=True)

    for ligne in devis["lignes"]:
        pdf.ligne_tableau(
            [ligne["designation"], f"{ligne['quantite']:g}", euros(ligne["prix_unitaire"]), euros(ligne["quantite"] * ligne["prix_unitaire"])],
            largeurs
        )

    pdf.ln(4)

    for libelle, montant, gras in [
        ("Total HT", montants["ht"], False),
        (f"TVA {devis['tva']:g} %", montants["tva"], False),
        ("Total TTC", montants["ttc"], True),
        (f"Acompte à la signature ({devis['acompte_pourcent']:g} %)", montants["acompte"], False)
    ]:
        pdf.set_font("Helvetica", "B" if gras else "", 11)
        pdf.cell(150, 7, texte_pdf(libelle), align="R")
        pdf.cell(40, 7, texte_pdf(euros(montant)), align="R", new_x="LMARGIN", new_y="NEXT")

    if devis["notes"]:
        pdf.ln(6)
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 5, texte_pdf(devis["notes"]))

    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, texte_pdf("Date et signature précédées de « Bon pour accord »"))
    pdf.rect(pdf.l_margin, pdf.get_y() + 8, 90, 25)

    return bytes(pdf.output())
