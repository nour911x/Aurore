from datetime import date, datetime
from html import escape
from pathlib import Path

from devis import date_lisible, euros


FICHIER_STYLE = Path(__file__).with_name("assets") / "style.css"

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
