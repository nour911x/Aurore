import os
from datetime import date, datetime
from html import escape

from donnees.fiche_evenement import renseigne
from metier.devis import date_lisible
from textes import montant


def salutation():
    heure = datetime.now().hour
    return "Bonsoir" if heure < 5 or heure >= 18 else "Bonjour"


def nom_organisateur():
    return os.environ.get("NOM_ORGANISATEUR", "").strip()


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


def element_svg(element):
    x, y, largeur, profondeur = element["x"], element["y"], element["largeur"], element["profondeur"]
    texte = f'<text class="plan-texte" x="{x}" y="{y + 5}">{escape(element["nom"])}</text>'

    if profondeur > largeur:
        texte = f'<text class="plan-texte" transform="translate({x + 5} {y}) rotate(-90)">{escape(element["nom"])}</text>'

    return f'<rect class="plan-zone" x="{x - largeur / 2}" y="{y - profondeur / 2}" width="{largeur}" height="{profondeur}" rx="3"/>{texte}'


def table_svg(table):
    x, y, largeur, profondeur = table["x"], table["y"], table["largeur"], table["profondeur"]
    classe = "plan-table pleine" if table["occupees"] >= table["places"] else "plan-table"
    noms = escape(", ".join(table["invites"]) or "Personne pour l'instant")

    if table["forme"] == "Ronde":
        forme = f'<circle class="{classe}" cx="{x}" cy="{y}" r="{largeur / 2}"/>'
    else:
        forme = f'<rect class="{classe}" x="{x - largeur / 2}" y="{y - profondeur / 2}" width="{largeur}" height="{profondeur}" rx="3"/>'

    return (
        f"<g><title>{noms}</title>{forme}"
        f'<text class="plan-texte" x="{x}" y="{y - 2}">{escape(table["nom"])}</text>'
        f'<text class="plan-compte" x="{x}" y="{y + 15}">{table["occupees"]}/{table["places"]}</text></g>'
    )


def plan_salle_html(disposition):
    largeur, profondeur = disposition["largeur"], disposition["profondeur"]
    dessins = {"table": table_svg, "element": element_svg}
    morceaux = "".join(dessins[objet["genre"]](objet) for objet in disposition["objets"])

    return (
        f'<svg class="plan" viewBox="0 0 {largeur} {profondeur}" role="img" aria-label="Plan de salle">'
        f'<rect class="plan-fond" x="2" y="2" width="{largeur - 4}" height="{profondeur - 4}" rx="3"/>{morceaux}</svg>'
    )


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
