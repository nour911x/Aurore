import io
import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, UnidentifiedImageError


URL_OPENVERSE = "https://api.openverse.org/v1/images/"
AGENT_HTTP = "AURORE/1.0 (projet etudiant)"
DELAI_HTTP = 10
TAILLE_MAX_TELECHARGEMENT = 8 * 1024 * 1024
COTE_IMAGE = 500
IMAGES_PAR_ELEMENT = 3
CANDIDATES_PAR_RECHERCHE = 20
PAGES_MINIMUM = 2
TELECHARGEMENTS_SIMULTANES = 6

RECHERCHES_PAR_DEFAUT = {
    "Décoration": "event decoration",
    "Fleurs": "flower bouquet",
    "Tenues": "elegant outfit",
    "Gâteau": "celebration cake",
    "Table": "table setting",
    "Papeterie": "invitation card"
}

NOMS_LICENCES = {"cc0": "CC0", "pdm": "Domaine public"}


class BanqueImages:
    """Recherche d'images libres de droits sur Openverse, sans clé."""

    def __init__(self, delai: int = DELAI_HTTP) -> None:
        self.delai = delai

    def lire_url(self, url: str) -> bytes:
        requete = Request(url, headers={"User-Agent": AGENT_HTTP})

        with urlopen(requete, timeout=self.delai) as reponse:
            return reponse.read(TAILLE_MAX_TELECHARGEMENT + 1)

    def interroger(self, recherche: str) -> list:
        parametres = urlencode({
            "q": recherche,
            "page_size": CANDIDATES_PAR_RECHERCHE,
            "mature": "false"
        })

        try:
            url = f"{URL_OPENVERSE}?{parametres}"
            reponse = json.loads(self.lire_url(url))
        except (URLError, TimeoutError, ValueError):
            return []

        return reponse.get("results") or []

    def rechercher(self, recherche: str, nombre: int, page: int = 1) -> list:
        """Les candidates, auteurs variés en tête.

        Tant qu'il y a trop peu de choix, retire le premier mot : en
        anglais le mot principal est à la fin (boho wedding arch).
        Garde la recherche qui a donné le plus d'images. Chaque page
        décale la sélection de `nombre` images, en boucle.
        """
        mots = recherche.split()
        meilleurs: list = []

        while mots:
            resultats = self.interroger(" ".join(mots))

            if len(resultats) > len(meilleurs):
                meilleurs = resultats

            if len(meilleurs) >= nombre * PAGES_MINIMUM:
                break

            mots.pop(0)

        images = self.varier([self.decrire(image) for image in meilleurs])

        return self.tourner(images, (page - 1) * nombre)

    @staticmethod
    def tourner(images: list[dict], decalage: int) -> list[dict]:
        if not images:
            return images

        decalage %= len(images)

        return images[decalage:] + images[:decalage]

    @staticmethod
    def varier(images: list[dict]) -> list[dict]:
        """Préfère des auteurs différents pour ne pas montrer un seul album."""
        auteurs: set[str] = set()
        choisies: list[dict] = []

        for image in images:
            if image["auteur"] not in auteurs:
                auteurs.add(image["auteur"])
                choisies.append(image)

        restantes = [image for image in images if image not in choisies]

        return choisies + restantes

    @staticmethod
    def decrire(resultat: dict) -> dict:
        return {
            "url": resultat.get("url") or "",
            "vignette": resultat.get("thumbnail") or "",
            "titre": resultat.get("title") or "Sans titre",
            "auteur": resultat.get("creator") or "Auteur inconnu",
            "licence": BanqueImages.nom_licence(
                resultat.get("license") or "",
                resultat.get("license_version") or ""
            ),
            "source": resultat.get("foreign_landing_url") or ""
        }

    @staticmethod
    def nom_licence(licence: str, version: str) -> str:
        if licence in NOMS_LICENCES:
            return NOMS_LICENCES[licence]

        return f"CC {licence.upper()} {version}".strip()

    def telecharger(self, image: dict) -> bytes | None:
        """Renvoie l'image en JPEG carré, ou None si elle est illisible."""
        for url in (image["url"], image["vignette"]):
            if not url:
                continue

            try:
                contenu = self.lire_url(url)
            except (URLError, TimeoutError, ValueError):
                continue

            if len(contenu) <= TAILLE_MAX_TELECHARGEMENT:
                reduite = self.reduire(contenu)

                if reduite:
                    return reduite

        return None

    @staticmethod
    def reduire(contenu: bytes) -> bytes | None:
        try:
            with Image.open(io.BytesIO(contenu)) as originale:
                image = ImageOps.fit(
                    originale.convert("RGB"), (COTE_IMAGE, COTE_IMAGE)
                )
                sortie = io.BytesIO()
                image.save(sortie, format="JPEG", quality=85)
        except (UnidentifiedImageError, OSError, ValueError):
            return None

        return sortie.getvalue()


class ImagesMoodboard:
    """Les images du moodboard, rangées dans le dossier du client."""

    def __init__(
        self, dossier: Path, banque: BanqueImages | None = None
    ) -> None:
        self.dossier = Path(dossier)
        self.banque = banque or BanqueImages()

    @staticmethod
    def recherches(moodboard: dict) -> dict[str, str]:
        proposees = moodboard.get("recherches_images") or {}

        return {
            element: proposees.get(element) or recherche
            for element, recherche in RECHERCHES_PAR_DEFAUT.items()
        }

    def vider(self) -> None:
        shutil.rmtree(self.dossier, ignore_errors=True)

    def enregistrer(self, image: dict) -> dict | None:
        contenu = self.banque.telecharger(image)

        if contenu is None:
            return None

        fichier = f"{uuid.uuid4().hex[:8]}.jpg"
        (self.dossier / fichier).write_bytes(contenu)

        return {**image, "fichier": fichier}

    def chercher(self, recherche: str, nombre: int, page: int) -> list:
        return self.banque.rechercher(recherche, nombre, page)

    @staticmethod
    def sans_doublons(
        trouvees: dict[str, list[dict]], nombre: int
    ) -> dict[str, list[dict]]:
        """Une même photo n'apparaît que dans un seul élément."""
        vues: set[str] = set()
        uniques = {}

        for element, liste in trouvees.items():
            nouvelles = [image for image in liste if image["url"] not in vues]
            uniques[element] = nouvelles[:nombre]
            vues.update(image["url"] for image in uniques[element])

        return uniques

    def composer(
        self, moodboard: dict, page: int = 1,
        nombre: int = IMAGES_PAR_ELEMENT
    ) -> dict[str, list[dict]]:
        """Cherche et télécharge les images de chaque élément du moodboard."""
        self.vider()
        self.dossier.mkdir(parents=True, exist_ok=True)
        recherches = self.recherches(moodboard)

        with ThreadPoolExecutor(TELECHARGEMENTS_SIMULTANES) as executeur:
            resultats = executeur.map(
                self.chercher, recherches.values(),
                [nombre] * len(recherches), [page] * len(recherches)
            )
            trouvees = self.sans_doublons(
                dict(zip(recherches, resultats, strict=True)), nombre
            )
            images = {
                element: [
                    image
                    for image in executeur.map(self.enregistrer, liste)
                    if image
                ]
                for element, liste in trouvees.items()
            }

        return {element: liste for element, liste in images.items() if liste}

    def lire(self, image: dict) -> bytes | None:
        chemin = self.dossier / image["fichier"]

        return chemin.read_bytes() if chemin.is_file() else None

    @staticmethod
    def credit(image: dict) -> str:
        return (
            f"« {image['titre']} » par {image['auteur']}, {image['licence']}"
        )
