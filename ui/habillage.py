import json
from datetime import date, datetime
from html import escape
from pathlib import Path

from donnees.fiche_evenement import renseigne
from metier.devis import date_lisible
from metier.jour_j import TABLE_HONNEUR
from textes import montant


DOSSIER_ASSETS = Path(__file__).parent.parent / "assets"

FICHIER_SALLE_3D = DOSSIER_ASSETS / "salle_3d.html"

PALETTE_PAR_DEFAUT = ["#B8975A", "#141210", "#E6DFD4", "#8C6D3A", "#FFFFFF"]

def salutation():
    heure = datetime.now().hour
    return "Bonsoir" if heure < 5 or heure >= 18 else "Bonjour"


def jours_restants(texte_date):
    try:
        return (date.fromisoformat(texte_date) - date.today()).days
    except (TypeError, ValueError):
        return None


def compte_a_rebours(jours):
    if jours is None or jours < 0:
        return None

    if jours == 0:
        return "C'est aujourd'hui"

    if jours == 1:
        return "C'est demain"

    return f"J-{jours}"


def frise_html(deroule, mis_en_avant=None):
    etapes = []

    for ligne in deroule:
        concerne = mis_en_avant and mis_en_avant.lower() in ligne["intervenants"].lower()
        classe = "concerne" if concerne else ""
        infos = " · ".join(escape(valeur) for valeur in [ligne["lieu"], ligne["intervenants"]] if valeur)
        infos_html = f"<small>{infos}</small>" if infos else ""
        details_html = f"<p>{escape(ligne['details'])}</p>" if ligne["details"] else ""
        etapes.append(
            f'<li class="{classe}"><span class="heure">{escape(ligne["heure"] or "—")}</span>'
            f'<div><strong>{escape(ligne["moment"])}</strong>{infos_html}{details_html}</div></li>'
        )

    return f'<ol class="frise">{"".join(etapes)}</ol>'


LARGEUR_PLAN = 880
COLONNES_PLAN = 5
ECART_X = 160
ECART_Y = 130


def zone(libelle, x, y, largeur, hauteur):
    return {"libelle": libelle, "x": x, "y": y, "largeur": largeur, "hauteur": hauteur}


def table_placee(table, invites, x, y):
    if table["forme"] == "Ronde":
        largeur, profondeur = 84, 84
    else:
        largeur, profondeur = (240 if table["nom"] == TABLE_HONNEUR else 110), 48

    return {
        "nom": table["nom"],
        "forme": table["forme"],
        "places": table["places"],
        "x": x,
        "y": y,
        "largeur": largeur,
        "profondeur": profondeur,
        "occupees": sum(1 + invite["accompagnants"] for invite in invites),
        "invites": [invite["nom"] for invite in invites]
    }


def disposition_salle(tables, repartition, elements):
    honneur = [table for table in tables if table["nom"] == TABLE_HONNEUR]
    autres = [table for table in tables if table["nom"] != TABLE_HONNEUR]
    placees, zones = [], []
    y = 50

    for table in honneur:
        placees.append(table_placee(table, repartition.get(table["nom"], []), LARGEUR_PLAN / 2, y))
        y += 60

    if "Piste de danse" in elements:
        zones.append(zone("Piste de danse", LARGEUR_PLAN / 2 - 120, y, 240, 100))

        if "DJ" in elements:
            zones.append(zone("DJ", LARGEUR_PLAN / 2 + 135, y + 25, 70, 50))

        y += 120
    elif "DJ" in elements:
        zones.append(zone("DJ", LARGEUR_PLAN / 2 - 35, y, 70, 50))
        y += 70

    debut_tables = y + 50
    marge = (LARGEUR_PLAN - (COLONNES_PLAN - 1) * ECART_X) / 2

    for index, table in enumerate(autres):
        x = marge + (index % COLONNES_PLAN) * ECART_X
        placees.append(table_placee(table, repartition.get(table["nom"], []), x, debut_tables + (index // COLONNES_PLAN) * ECART_Y))

    hauteur = debut_tables + max(1, -(-len(autres) // COLONNES_PLAN)) * ECART_Y

    for position, element in [(16, "Buffet"), (LARGEUR_PLAN - 66, "Bar")]:
        if element in elements:
            zones.append(zone(element, position, 120, 50, hauteur - 200))

    if "Photobooth" in elements:
        zones.append(zone("Photobooth", LARGEUR_PLAN - 150, hauteur - 50, 130, 40))

    return {"largeur": LARGEUR_PLAN, "hauteur": hauteur, "tables": placees, "zones": zones}


def zone_svg(element):
    x, y, largeur, hauteur = element["x"], element["y"], element["largeur"], element["hauteur"]

    return (
        f'<rect class="plan-zone" x="{x}" y="{y}" width="{largeur}" height="{hauteur}" rx="3"/>'
        f'<text class="plan-texte" x="{x + largeur / 2}" y="{y + hauteur / 2 + 5}">{escape(element["libelle"])}</text>'
    )


def table_svg(table):
    x, y = table["x"], table["y"]
    classe = "plan-table pleine" if table["occupees"] >= table["places"] else "plan-table"
    noms = escape(", ".join(table["invites"]) or "Personne pour l'instant")

    if table["forme"] == "Ronde":
        forme = f'<circle class="{classe}" cx="{x}" cy="{y}" r="{table["largeur"] / 2}"/>'
    else:
        largeur, profondeur = table["largeur"], table["profondeur"]
        forme = f'<rect class="{classe}" x="{x - largeur / 2}" y="{y - profondeur / 2}" width="{largeur}" height="{profondeur}" rx="3"/>'

    return (
        f"<g><title>{noms}</title>{forme}"
        f'<text class="plan-texte" x="{x}" y="{y - 2}">{escape(table["nom"])}</text>'
        f'<text class="plan-compte" x="{x}" y="{y + 15}">{table["occupees"]}/{table["places"]}</text></g>'
    )


def plan_salle_html(disposition):
    largeur, hauteur = disposition["largeur"], disposition["hauteur"]
    morceaux = [zone_svg(element) for element in disposition["zones"]] + [table_svg(table) for table in disposition["tables"]]

    return (
        f'<svg class="plan" viewBox="0 0 {largeur} {hauteur}" role="img" aria-label="Plan de salle">'
        f'<rect class="plan-fond" x="2" y="2" width="{largeur - 4}" height="{hauteur - 4}" rx="3"/>'
        f'{"".join(morceaux)}</svg>'
    )


def salle_3d_html(disposition, palette):
    donnees = json.dumps({**disposition, "palette": palette or PALETTE_PAR_DEFAUT}, ensure_ascii=False)

    return FICHIER_SALLE_3D.read_text(encoding="utf-8").replace("__DONNEES__", donnees.replace("</", "<\\/"))


def valeur_lisible(cle, contenu):
    if isinstance(contenu, bool):
        return "Oui" if contenu else "Non"

    if isinstance(contenu, list):
        return ", ".join(contenu)

    if cle.startswith("date"):
        return date_lisible(contenu)

    if cle == "budget" and contenu:
        return montant(contenu)

    return contenu


def details_dossier_html(donnees_evenement, champs_essentiels, champs_details):
    connus = [
        (libelle, valeur_lisible(cle, donnees_evenement[cle]))
        for cle, libelle in {**champs_essentiels, **champs_details}.items() if renseigne(donnees_evenement[cle])
    ]
    manquants = [libelle.lower() for cle, libelle in champs_essentiels.items() if not renseigne(donnees_evenement[cle])]
    lignes = "".join(f"<div><dt>{escape(libelle)}</dt><dd>{escape(str(contenu))}</dd></div>" for libelle, contenu in connus)
    corps = f'<dl class="details-dossier">{lignes}</dl>' if connus else '<p class="a-definir">AURORE remplit ce dossier au fil de la discussion.</p>'
    a_definir = f'<p class="a-definir">À définir : {", ".join(manquants)}</p>' if manquants else ""

    return corps + a_definir
