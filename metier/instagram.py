import functools
import importlib.util
import io
import json
import math
import os
import textwrap
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


URL_API = "https://graph.instagram.com/v21.0"
DELAI_HTTP = 20
ESSAIS_STATUT = 10
PAUSE_STATUT = 2
DOSSIER_PUBLIC = Path(__file__).parent.parent / "static" / "publications"
CHEMIN_PUBLIC = "app/static/publications"

COTE_CARTE = 1080
MARGE_CARTE = 110
FOND_CARTE = "#2B0E20"
OR_CARTE = "#C79A5B"
TEXTE_CARTE = "#F8F1EE"
GRIS_CARTE = "#C9B8BF"
MOTIF_POLICE = "SourceSerifVariable-Roman*.woff2"


class ErreurInstagram(RuntimeError):
    """Instagram a refusé la publication ; le message vient de Meta."""


class CarteTemoignage:
    """Une image carrée qui met en scène l'avis d'un client."""

    def __init__(self, commentaire: str, note: int, auteur: str) -> None:
        self.commentaire = commentaire.strip()
        self.note = max(0, min(5, int(note)))
        self.auteur = auteur.strip()

    @staticmethod
    @functools.cache
    def fichier_police() -> Path | None:
        """La police Source Serif livrée avec Streamlit (licence OFL).

        La police par défaut de Pillow n'a ni « é » ni « à ». On cherche
        le fichier sans importer Streamlit : metier/ n'en dépend pas.
        """
        module = importlib.util.find_spec("streamlit")

        if module is None or module.origin is None:
            return None

        medias = Path(module.origin).parent / "static" / "static" / "media"

        return next(iter(sorted(medias.glob(MOTIF_POLICE))), None)

    @staticmethod
    def police(taille: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        fichier = CarteTemoignage.fichier_police()

        if fichier is not None:
            try:
                return ImageFont.truetype(str(fichier), taille)
            except OSError:
                pass

        return ImageFont.load_default(size=taille)

    @staticmethod
    def etoile(centre: tuple[float, float], rayon: float) -> list:
        """Les dix sommets d'une étoile à cinq branches."""
        x, y = centre
        sommets = []

        for index in range(10):
            angle = math.pi / 2 + index * math.pi / 5
            longueur = rayon if index % 2 == 0 else rayon * 0.45
            sommets.append((
                x + longueur * math.cos(angle),
                y - longueur * math.sin(angle)
            ))

        return sommets

    def lignes(self, dessin: ImageDraw.ImageDraw, taille: int) -> list[str]:
        """Coupe la citation pour qu'elle tienne dans la largeur utile."""
        largeur = COTE_CARTE - 2 * MARGE_CARTE
        police = self.police(taille)
        caracteres = 60

        while caracteres > 10:
            lignes = textwrap.wrap(f"« {self.commentaire} »", caracteres)

            if all(
                dessin.textlength(ligne, font=police) <= largeur
                for ligne in lignes
            ):
                return lignes

            caracteres -= 2

        return textwrap.wrap(f"« {self.commentaire} »", caracteres)

    def generer(self) -> bytes:
        image = Image.new("RGB", (COTE_CARTE, COTE_CARTE), FOND_CARTE)
        dessin = ImageDraw.Draw(image)
        taille = 54 if len(self.commentaire) < 160 else 42
        lignes = self.lignes(dessin, taille)[:12]
        hauteur_ligne = int(taille * 1.35)
        hauteur_texte = len(lignes) * hauteur_ligne
        y = (COTE_CARTE - hauteur_texte) // 2

        for index in range(self.note):
            x = COTE_CARTE / 2 + (index - (self.note - 1) / 2) * 70
            dessin.polygon(self.etoile((x, y - 110), 26), fill=OR_CARTE)

        for ligne in lignes:
            dessin.text(
                (COTE_CARTE / 2, y), ligne, font=self.police(taille),
                fill=TEXTE_CARTE, anchor="ma"
            )
            y += hauteur_ligne

        if self.auteur:
            dessin.text(
                (COTE_CARTE / 2, y + 50), f"— {self.auteur}",
                font=self.police(40), fill=OR_CARTE, anchor="ma"
            )

        dessin.text(
            (COTE_CARTE / 2, COTE_CARTE - 90), "AURORE",
            font=self.police(34), fill=GRIS_CARTE, anchor="ma"
        )
        sortie = io.BytesIO()
        image.save(sortie, format="JPEG", quality=92)

        return sortie.getvalue()


class PublicationInstagram:
    """Publication d'une photo sur un compte Instagram professionnel.

    Instagram télécharge lui-même l'image : elle doit être accessible à
    une adresse publique. AURORE la dépose dans static/publications le
    temps de la publication, puis la supprime.
    """

    def __init__(
        self, jeton: str | None = None, compte: str | None = None,
        url_publique: str | None = None, dossier_public: Path = DOSSIER_PUBLIC,
        attendre: Callable[[float], None] = time.sleep
    ) -> None:
        load_dotenv()
        self.jeton = jeton or os.environ.get("INSTAGRAM_TOKEN") or ""
        self.compte = compte or os.environ.get("INSTAGRAM_USER_ID") or ""
        self.url_publique = (
            url_publique or os.environ.get("AURORE_URL_PUBLIQUE") or ""
        ).rstrip("/")
        self.dossier_public = Path(dossier_public)
        self.attendre = attendre

    def est_configuree(self) -> bool:
        return bool(self.jeton and self.compte and self.url_publique)

    def lire_url(self, requete: Request) -> bytes:
        with urlopen(requete, timeout=DELAI_HTTP) as reponse:
            return reponse.read()

    def appeler(
        self, chemin: str, parametres: dict, envoyer: bool = False
    ) -> dict:
        """Le jeton passe dans l'en-tête, jamais dans l'adresse."""
        donnees = urlencode(parametres)
        url = f"{URL_API}/{chemin}"

        if not envoyer and donnees:
            url = f"{url}?{donnees}"

        requete = Request(
            url, data=donnees.encode() if envoyer else None,
            headers={"Authorization": f"Bearer {self.jeton}"},
            method="POST" if envoyer else "GET"
        )

        try:
            return json.loads(self.lire_url(requete))
        except HTTPError as erreur:
            raise ErreurInstagram(self.message_erreur(erreur)) from erreur
        except (URLError, TimeoutError) as erreur:
            raise ErreurInstagram(
                "Instagram ne répond pas : vérifiez la connexion internet."
            ) from erreur

    @staticmethod
    def message_erreur(erreur: HTTPError) -> str:
        try:
            detail = json.loads(erreur.read())["error"]["message"]
        except (ValueError, KeyError, TypeError):
            detail = erreur.reason

        return f"Instagram a refusé la publication : {detail}"

    def rendre_public(self, contenu: bytes) -> tuple[Path, str]:
        self.dossier_public.mkdir(parents=True, exist_ok=True)
        fichier = self.dossier_public / f"{uuid.uuid4().hex}.jpg"
        fichier.write_bytes(contenu)

        return fichier, f"{self.url_publique}/{CHEMIN_PUBLIC}/{fichier.name}"

    def attendre_conteneur(self, conteneur: str) -> None:
        """Instagram prépare l'image avant qu'on puisse la publier."""
        for _ in range(ESSAIS_STATUT):
            statut = self.appeler(conteneur, {"fields": "status_code"})

            if statut.get("status_code") == "FINISHED":
                return

            if statut.get("status_code") == "ERROR":
                raise ErreurInstagram(
                    "Instagram n'a pas pu lire l'image : vérifiez que "
                    "AURORE_URL_PUBLIQUE est bien l'adresse en ligne de "
                    "l'application."
                )

            self.attendre(PAUSE_STATUT)

        raise ErreurInstagram("Instagram met trop de temps : réessayez.")

    def publier(self, contenu: bytes, legende: str) -> dict:
        """Publie l'image et renvoie l'identifiant et le lien du post."""
        if not self.est_configuree():
            raise ErreurInstagram(
                "La publication Instagram n'est pas configurée."
            )

        fichier, url_image = self.rendre_public(contenu)

        try:
            conteneur = self.appeler(
                f"{self.compte}/media",
                {"image_url": url_image, "caption": legende}, envoyer=True
            )["id"]
            self.attendre_conteneur(conteneur)
            post = self.appeler(
                f"{self.compte}/media_publish", {"creation_id": conteneur},
                envoyer=True
            )["id"]
            lien = self.appeler(post, {"fields": "permalink"}).get(
                "permalink", ""
            )
        finally:
            fichier.unlink(missing_ok=True)

        return {"id": post, "lien": lien}
