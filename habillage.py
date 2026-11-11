from datetime import date, datetime
from html import escape
import json
from pathlib import Path

from devis import date_lisible, euros
from jour_j import TABLE_HONNEUR


FICHIER_STYLE = Path(__file__).with_name("assets") / "style.css"

FICHIER_SALLE_3D = Path(__file__).with_name("assets") / "salle_3d.html"

PALETTE_PAR_DEFAUT = ["#B9506F", "#9CAF88", "#F8EDEF", "#E9C46A", "#FFFFFF"]

FORMES = {"mariage": "petale", "baby": "feuille", "naissance": "feuille", "anniversaire": "confetti"}

TEINTES_CONFETTI = ["#F0A273", "#E9C46A", "#F4C7CF", "#B9D3E8"]

PLACEMENTS = [
    (-3, 44, 40, -6, 6, 300),
    (12, 28, 47, -24, -4, -260),
    (31, 36, 53, -37, 5, 330),
    (52, 24, 42, -14, -6, -290),
    (70, 40, 50, -31, 4, 270),
    (88, 30, 45, -9, -5, -310),
    (97, 46, 56, -45, -3, 250)
]

THEME_PRO = """<style>
:root {
    --accent: #6E52A6;
    --accent-fonce: #573F8C;
    --lueur-1: #E4D5F5;
    --lueur-2: #D8C7EF;
    --lueur-3: #F1D7E6;
}
.particule.petale { background: linear-gradient(140deg, #EFE7FB, #D3C3EF 60%, #B39CDD); }
button[role="tab"][aria-selected="true"] { background: var(--accent); }
</style>"""

ACCUEILS = {
    "Wedding planner": (
        "Quel mariage préparez-vous pour vos clients ?",
        "Rendez-vous, prestataires, devis et invités : tout le suivi de vos clients au même endroit."
    ),
    "Mariés": (
        "Qu'organise-t-on ensemble ?",
        "Budget, prestataires, invités, inspiration : je t'accompagne de la première idée au jour J."
    ),
    "Prestataire": (
        "Sur quel mariage travaillez-vous ?",
        "Couverts, allergies, rendez-vous et devis : les infos utiles pour votre prestation."
    )
}

AVERTISSEMENT_HTML = (
    '<div class="aurore-avertissement">AURORE peut se tromper : '
    "vérifiez les montants et les dates importantes.</div>"
)


def style_html():
    return f"<style>{FICHIER_STYLE.read_text(encoding='utf-8')}</style>"


def theme_html(profil):
    return THEME_PRO if profil != "Mariés" else "<style></style>"


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
        return "C'est aujourd'hui ✨"

    if jours == 1:
        return "C'est demain ✨"

    return f"J-{jours}"


def forme_particules(type_evenement):
    texte = (type_evenement or "mariage").lower()

    for mot, forme in FORMES.items():
        if mot in texte:
            return forme

    return "lueur"


def particules_html(type_evenement):
    forme = forme_particules(type_evenement)
    spans = []

    for index, (gauche, taille, duree, delai, derive, rotation) in enumerate(PLACEMENTS):
        teinte = f"--teinte:{TEINTES_CONFETTI[index % len(TEINTES_CONFETTI)]};" if forme == "confetti" else ""
        spans.append(
            f'<span class="particule {forme}" style="left:{gauche}%;--taille:{taille}px;'
            f'--duree:{duree}s;--delai:{delai}s;--derive:{derive}vw;--rotation:{rotation}deg;{teinte}"></span>'
        )

    return f'<div class="particules" aria-hidden="true">{"".join(spans)}</div>'


def marque_html(event_data):
    compte = compte_a_rebours(jours_restants(event_data["date"]))
    noms = (event_data["noms"] or "").replace(" et ", " & ")
    pastille = " · ".join(filter(None, [compte, escape(noms)]))
    pastille_html = f'<span class="aurore-compte">{pastille}</span>' if pastille else ""

    return (
        '<div class="aurore-marque"><span class="aurore-sceau">A</span>'
        '<div><div class="aurore-nom">AURORE</div>'
        '<div class="aurore-sous-titre">A Unique Real Organisation Running your Events</div></div>'
        f"{pastille_html}</div>"
    )


def accueil_html(profil):
    titre, intro = ACCUEILS[profil]

    return f'<div class="aurore-accueil"><h1>{salutation()}. {titre}</h1><p>{intro}</p></div>'


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

    return f'<ol class="aurore-frise">{"".join(etapes)}</ol>'


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
        f'<rect class="plan-zone" x="{x}" y="{y}" width="{largeur}" height="{hauteur}" rx="14"/>'
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
        forme = f'<rect class="{classe}" x="{x - largeur / 2}" y="{y - profondeur / 2}" width="{largeur}" height="{profondeur}" rx="8"/>'

    return (
        f"<g><title>{noms}</title>{forme}"
        f'<text class="plan-texte" x="{x}" y="{y - 2}">{escape(table["nom"])}</text>'
        f'<text class="plan-compte" x="{x}" y="{y + 15}">{table["occupees"]}/{table["places"]}</text></g>'
    )


def plan_salle_html(disposition):
    largeur, hauteur = disposition["largeur"], disposition["hauteur"]
    morceaux = [zone_svg(element) for element in disposition["zones"]] + [table_svg(table) for table in disposition["tables"]]

    return (
        f'<svg class="aurore-plan" viewBox="0 0 {largeur} {hauteur}" role="img" aria-label="Plan de salle">'
        f'<rect class="plan-fond" x="2" y="2" width="{largeur - 4}" height="{hauteur - 4}" rx="24"/>'
        f'{"".join(morceaux)}</svg>'
    )


def salle_3d_html(disposition, palette):
    donnees = json.dumps({**disposition, "palette": palette or PALETTE_PAR_DEFAUT}, ensure_ascii=False)

    return FICHIER_SALLE_3D.read_text(encoding="utf-8").replace("__DONNEES__", donnees.replace("</", "<\\/"))


def dossier_html(event_data, champs_essentiels, champs_details):
    compte = compte_a_rebours(jours_restants(event_data["date"]))
    badge = f'<span class="aurore-compte">{compte}</span>' if compte else ""

    def valeur(cle):
        contenu = event_data[cle]

        if isinstance(contenu, list):
            return ", ".join(contenu)

        if cle == "date":
            return date_lisible(contenu)

        if cle == "budget" and contenu:
            return euros(contenu).replace(",00 EUR", " €")

        return contenu

    connus = [(label, valeur(cle)) for cle, label in {**champs_essentiels, **champs_details}.items() if event_data[cle]]
    manquants = [label.lower() for cle, label in champs_essentiels.items() if not event_data[cle]]

    lignes = "".join(f"<div><dt>{escape(label)}</dt><dd>{escape(str(contenu))}</dd></div>" for label, contenu in connus)
    corps = f"<dl>{lignes}</dl>" if connus else '<p class="a-definir">AURORE remplit ce dossier au fil de la discussion.</p>'
    a_definir = f'<p class="a-definir">À définir : {", ".join(manquants)}</p>' if manquants else ""

    return (
        '<section class="aurore-dossier"><header>'
        f'<span class="titre-dossier">📋 Dossier</span>{badge}</header>{corps}{a_definir}</section>'
    )
