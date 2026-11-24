import re
import tomllib
from pathlib import Path

import pytest

from ui.design import FICHIER_THEME, indicateur_html, logo_html, sans_icone


RACINE = Path(__file__).parent.parent

COULEURS = dict(re.findall(r"--([\w-]+): (#[0-9A-F]{6});", FICHIER_THEME.read_text(encoding="utf-8")))


def luminance(couleur):
    canaux = [int(couleur[position:position + 2], 16) / 255 for position in (1, 3, 5)]
    rouge, vert, bleu = [canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4 for canal in canaux]

    return 0.2126 * rouge + 0.7152 * vert + 0.0722 * bleu


def contraste(couleur, fond):
    clair, fonce = sorted((luminance(couleur), luminance(fond)), reverse=True)
    return (clair + 0.05) / (fonce + 0.05)


@pytest.mark.parametrize("fond", ["ivoire", "blanc"])
@pytest.mark.parametrize("texte", ["noir", "gris", "dore-texte", "bordeaux", "sauge-texte"])
def test_contraste_aa_sur_fond_clair(texte, fond):
    assert contraste(COULEURS[texte], COULEURS[fond]) >= 4.5


@pytest.mark.parametrize("texte", ["ivoire", "gris-menu", "dore"])
def test_contraste_aa_dans_le_menu(texte):
    assert contraste(COULEURS[texte], COULEURS["noir"]) >= 4.5


def test_dore_clair_et_sauge_jamais_utilises_pour_du_texte_sur_fond_clair():
    css = FICHIER_THEME.read_text(encoding="utf-8")
    interdits = re.findall(r"([^{}]+)\{[^{}]*(?<![\w-])color: var\(--(?:dore|sauge)\)", css)

    assert all("Sidebar" in selecteur or "menu-" in selecteur or "Avatar" in selecteur for selecteur in interdits)


def test_config_streamlit_utilise_la_palette():
    theme = tomllib.loads((RACINE / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    valeurs = [*theme.values(), *theme["sidebar"].values()]
    couleurs = {valeur for valeur in valeurs if isinstance(valeur, str) and valeur.startswith("#")}

    assert couleurs - set(COULEURS.values()) == {"#3A172B"}


def test_tout_le_style_est_dans_le_theme():
    for fichier in (RACINE / "ui").glob("*.py"):
        contenu = fichier.read_text(encoding="utf-8")
        assert not re.search(r'style="(?!--teinte)', contenu), fichier.name
        assert contenu.count("<style>") == (1 if fichier.name == "design.py" else 0), fichier.name


def test_indicateurs():
    assert "nul" in indicateur_html("Conflits", 0, alerte=True)
    assert "alerte" in indicateur_html("Conflits", 2, alerte=True)
    assert "&lt;b&gt;" in indicateur_html("Lieu", "<b>")


def test_icones_retirees_des_titres():
    assert sans_icone(":gray[:material/send:] À inviter") == "À inviter"
    assert sans_icone(":material/chair: Couverts") == "Couverts"
    assert "AURORE" in logo_html()
