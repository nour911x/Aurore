from datetime import date, timedelta

from fpdf import FPDF

from storage import load_json, save_json


STATUTS_DEVIS = ["Brouillon", "Envoyé", "Accepté", "Refusé"]

REMPLACEMENTS_PDF = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "OE", "€": "EUR"}


def nombre(valeur):
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return 0.0

    return valeur if valeur == valeur else 0.0


def lignes_valides(lignes):
    return [
        {
            "designation": ligne["designation"].strip(),
            "quantite": nombre(ligne.get("quantite")),
            "prix_unitaire": nombre(ligne.get("prix_unitaire"))
        }
        for ligne in lignes
        if isinstance(ligne.get("designation"), str) and ligne["designation"].strip()
    ]


def totaux(devis):
    total_ht = sum(ligne["quantite"] * ligne["prix_unitaire"] for ligne in devis["lignes"])
    tva = total_ht * devis["tva"] / 100
    total_ttc = total_ht + tva

    return {
        "ht": round(total_ht, 2),
        "tva": round(tva, 2),
        "ttc": round(total_ttc, 2),
        "acompte": round(total_ttc * devis["acompte_pourcent"] / 100, 2)
    }


def euros(montant):
    return f"{montant:,.2f} EUR".replace(",", " ").replace(".", ",")


def texte_pdf(texte):
    for ancien, nouveau in REMPLACEMENTS_PDF.items():
        texte = str(texte).replace(ancien, nouveau)

    return texte.encode("latin-1", "replace").decode("latin-1")


def date_lisible(texte):
    try:
        return date.fromisoformat(texte).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return texte


def date_validite(devis):
    return date.fromisoformat(devis["date"]) + timedelta(days=devis["validite_jours"])


class CarnetDevis:
    def __init__(self, file_path="./devis_data.json"):
        self.file_path = file_path
        self.devis = []
        self.load()

    def load(self):
        self.devis = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.devis)

    def prochain_numero(self):
        annee = date.today().year
        nombre = sum(1 for devis in self.devis if devis["numero"].startswith(f"DEV-{annee}-"))

        return f"DEV-{annee}-{nombre + 1:03d}"

    def add_devis(self, emetteur, prestataire_id, destinataire, lignes, tva, acompte_pourcent, validite_jours, notes):
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
        self.save()

    def trouver(self, numero):
        for devis in self.devis:
            if devis["numero"] == numero:
                return devis

        return None

    def changer_statut(self, numero, statut):
        devis = self.trouver(numero)

        if devis:
            devis["statut"] = statut
            self.save()

    def supprimer(self, numero):
        self.devis = [devis for devis in self.devis if devis["numero"] != numero]
        self.save()


class DevisPDF(FPDF):
    def ligne_tableau(self, valeurs, largeurs, gras=False, fond=False):
        self.set_font("Helvetica", "B" if gras else "", 10)

        if fond:
            self.set_fill_color(245, 235, 240)

        for index, (valeur, largeur) in enumerate(zip(valeurs, largeurs)):
            alignement = "L" if index == 0 else "R"
            self.cell(largeur, 8, texte_pdf(valeur), border="B", align=alignement, fill=fond)

        self.ln()


def generer_pdf(devis, event_data):
    montants = totaux(devis)
    pdf = DevisPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, texte_pdf(devis["emetteur"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, texte_pdf(f"Devis n° {devis['numero']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, texte_pdf(f"Émis le {date.fromisoformat(devis['date']).strftime('%d/%m/%Y')} - valable jusqu'au {date_validite(devis).strftime('%d/%m/%Y')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    evenement = " - ".join(
        str(valeur) for valeur in [event_data["type_evenement"], date_lisible(event_data["date"]), event_data["lieu"]] if valeur
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
