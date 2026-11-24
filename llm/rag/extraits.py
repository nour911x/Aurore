import io
import re
import textwrap
from html import escape
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


TAILLE_EXTRAIT = 800

SEPARATEUR_PHRASES = re.compile(r"(?<=[.!?;])\s+|\n+")


def lire_pages(nom, contenu):
    if Path(nom).suffix.lower() == ".pdf":
        try:
            return [page.extract_text() for page in PdfReader(io.BytesIO(contenu)).pages]
        except PyPdfError as erreur:
            raise ValueError("Ce PDF est illisible : il est abîmé ou protégé par un mot de passe.") from erreur

    try:
        return [contenu.decode("utf-8-sig")]
    except UnicodeDecodeError:
        return [contenu.decode("cp1252", errors="replace")]


def phrases(texte):
    for phrase in SEPARATEUR_PHRASES.split(texte):
        yield from textwrap.wrap(phrase, TAILLE_EXTRAIT)


def decouper(texte):
    extraits = []
    courant = []

    for phrase in phrases(texte):
        if courant and len(" ".join([*courant, phrase])) > TAILLE_EXTRAIT:
            extraits.append(" ".join(courant))
            derniere = courant[-1]
            courant = [derniere] if len(derniere) + len(phrase) < TAILLE_EXTRAIT else []

        courant.append(phrase)

    if courant:
        extraits.append(" ".join(courant))

    return extraits


def extraire(nom, contenu):
    extraits = [
        {"texte": texte, "document": nom, "page": numero}
        for numero, page in enumerate(lire_pages(nom, contenu), start=1)
        for texte in decouper(page)
    ]

    if not extraits:
        raise ValueError("Aucun texte trouvé dans ce document (PDF scanné ou fichier vide ?).")

    return extraits


def baliser(extraits):
    return "\n".join(
        f'<extrait numero="{numero}" document="{escape(extrait["document"])}" page="{extrait["page"]}">\n'
        f"{escape(extrait['texte'], quote=False)}\n</extrait>"
        for numero, extrait in enumerate(extraits, start=1)
    )
