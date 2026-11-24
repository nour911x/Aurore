import re
from html import escape
from pathlib import Path

import streamlit as st

from textes import BASELINE


FICHIER_THEME = Path(__file__).with_name("theme.css")

ICONE = re.compile(r":\w+\[:material/\w+:\]\s*|:material/\w+:\s*")

SYMBOLE = re.compile(r":material/(\w+):")


def icone(texte):
    return re.search(r":material/\w+:", texte).group()


def sans_icone(texte):
    return ICONE.sub("", texte)


def charger_theme():
    st.html(f"<style>{FICHIER_THEME.read_text(encoding='utf-8')}</style>")


def afficher_html(contenu):
    st.markdown(contenu, unsafe_allow_html=True)


def logo_html(avec_baseline=True):
    baseline = f'<div class="baseline">{BASELINE}</div>' if avec_baseline else ""
    return f'<div class="logo"><span class="monogramme">A</span><div class="nom">AURORE</div>{baseline}</div>'


def grand_titre(titre, sur_titre="", intro=""):
    sur_titre_html = f'<div class="sur-titre">{escape(sur_titre)}</div>' if sur_titre else ""
    intro_html = f'<p class="intro">{escape(intro)}</p>' if intro else ""
    afficher_html(f'<div class="grand-titre">{sur_titre_html}<h1>{escape(titre)}</h1>{intro_html}</div>')


def symbole_html(nom):
    return f'<span class="symbole" aria-hidden="true">{nom}</span>'


def titre_section(titre):
    trouve = SYMBOLE.search(titre)
    symbole = symbole_html(trouve.group(1)) if trouve else ""
    afficher_html(f'<div class="titre-section" role="heading" aria-level="2">{symbole}{escape(sans_icone(titre))}</div>')


def badge_html(texte, classe=""):
    return f'<span class="badge {classe}">{escape(texte)}</span>'


def banniere(titre, sur_titre, intro):
    afficher_html(
        f'<div class="banniere"><div><div class="sur-titre">{escape(sur_titre)}</div><h1>{escape(titre)}</h1><p>{escape(intro)}</p></div>'
        '<div class="photo" role="img" aria-label="Table de réception fleurie"></div></div>'
    )


def carte(cle, symbole, teinte, libelle, valeur, alerte=False, au_clic=None, arguments=()):
    with st.container(key=f"carte-{cle}"):
        afficher_html(
            f'<div class="carte{" alerte" if alerte else ""}"><span class="pastille {teinte}">{symbole_html(symbole)}</span>'
            f'<div><div class="valeur">{valeur}</div><div class="libelle">{escape(libelle)}</div></div></div>'
        )

        if au_clic:
            st.button(f"Ouvrir : {libelle}", icon=":material/chevron_right:", key=f"ouvrir_{cle}", type="tertiary", on_click=au_clic, args=arguments)


def bloc(cle):
    return st.container(key=f"bloc-{cle}")


def evenement(titre, detail, symbole="", vignette="", heure="", teinte="", badge="", classe_badge=""):
    heure_html = f'<span class="heure">{escape(heure)}</span><span class="point" style="--teinte:{teinte}"></span>' if heure else ""
    contenu = symbole_html(symbole) if symbole else ""
    afficher_html(
        f'<div class="evenement">{heure_html}<span class="vignette {vignette}">{contenu}</span>'
        f'<div class="ligne"><div class="titre"><b>{escape(titre)}</b></div><div class="detail">{escape(detail)}</div></div>'
        f'{badge_html(badge, classe_badge) if badge else ""}</div>'
    )


def profil(nom, role):
    afficher_html(f'<div class="profil"><span class="initiale">{escape(nom[:1].upper())}</span><div>{escape(nom)}<small>{escape(role)}</small></div></div>')


def vide(texte):
    afficher_html(f'<p class="vide">{escape(texte)}</p>')


def entete_dossier(titre, details, fort=None):
    elements = [f"<span>{escape(str(detail))}</span>" for detail in details if detail]

    if fort:
        elements.append(f'<span class="fort">{escape(fort)}</span>')

    afficher_html(f'<header class="entete-dossier"><h1>{escape(titre)}</h1><div class="details">{"".join(elements)}</div></header>')


def indicateur_html(libelle, valeur, alerte=False, en_texte=False):
    etat = " nul" if valeur == 0 else " alerte" if alerte else ""
    taille = " texte" if en_texte else ""

    return f'<div class="indicateur{etat}{taille}"><dt>{escape(sans_icone(libelle))}</dt><dd>{escape(str(valeur))}</dd></div>'


def indicateurs(valeurs, alertes=()):
    en_texte = any(isinstance(valeur, str) for valeur in valeurs.values())
    contenu = "".join(indicateur_html(libelle, valeur, libelle in alertes, en_texte) for libelle, valeur in valeurs.items())
    afficher_html(f'<dl class="indicateurs">{contenu}</dl>')


def ligne(cle):
    return st.container(key=f"ligne-{cle}", horizontal=True, horizontal_alignment="distribute", vertical_alignment="center")


def texte_ligne(titre, detail="", heure="", etat="", classe_etat="attention"):
    heure_html = f'<span class="heure">{escape(heure)}</span>' if heure else ""
    etat_html = f' <span class="etat-{classe_etat}">{escape(etat)}</span>' if etat else ""
    detail_html = f'<div class="detail">{escape(detail)}</div>' if detail else ""
    afficher_html(f'<div class="ligne"><div class="titre">{heure_html}<b>{escape(titre)}</b>{etat_html}</div>{detail_html}</div>')


def lien_action(libelle, cle, au_clic, arguments=()):
    st.button(libelle, key=cle, type="tertiary", on_click=au_clic, args=arguments)
