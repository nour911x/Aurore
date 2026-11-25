import io
import json
from urllib.error import URLError

from PIL import Image
from pypdf import PdfReader

from metier.images import (
    RECHERCHES_PAR_DEFAUT,
    TAILLE_MAX_TELECHARGEMENT,
    BanqueImages,
    ImagesMoodboard,
)
from metier.inspiration import (
    ELEMENTS_MOODBOARD,
    generer_moodboard_pdf,
    nettoyer_moodboard,
)


def image_png(cote=900, teinte=(204, 102, 68)):
    sortie = io.BytesIO()
    Image.new("RGB", (cote, cote // 2), teinte).save(sortie, format="PNG")

    return sortie.getvalue()


def resultat(numero, auteur="Ana"):
    return {
        "url": f"https://exemple.org/{numero}.png",
        "thumbnail": f"https://exemple.org/{numero}/thumb",
        "title": f"Photo {numero}",
        "creator": auteur,
        "license": "by",
        "license_version": "2.0",
        "foreign_landing_url": f"https://exemple.org/{numero}"
    }


class FausseBanque(BanqueImages):
    """Répond comme Openverse, sans réseau."""

    def __init__(self, resultats_par_recherche=None, contenu=None):
        super().__init__()
        self.resultats_par_recherche = resultats_par_recherche or {}
        self.contenu = image_png() if contenu is None else contenu
        self.recherches = []

    def lire_url(self, url):
        if "api.openverse.org" not in url:
            if self.contenu == b"panne":
                raise URLError("hors ligne")
            return self.contenu

        recherche = url.split("q=")[1].split("&")[0].replace("+", " ")
        self.recherches.append(recherche)
        resultats = self.resultats_par_recherche.get(recherche, [])

        return json.dumps({"results": resultats}).encode()


def test_les_recherches_par_defaut_couvrent_chaque_element():
    assert list(RECHERCHES_PAR_DEFAUT) == ELEMENTS_MOODBOARD


def test_recherche_raccourcie_si_trop_peu_de_resultats():
    banque = FausseBanque({
        "boho table centerpiece": [resultat(9)],
        "centerpiece": [resultat(1), resultat(2, "Ben"), resultat(3, "Cy")]
    })

    images = banque.rechercher("boho table centerpiece", 3)

    assert banque.recherches == [
        "boho table centerpiece", "table centerpiece", "centerpiece"
    ]
    assert [image["titre"] for image in images] == [
        "Photo 1", "Photo 2", "Photo 3"
    ]
    assert images[0]["licence"] == "CC BY 2.0"


def test_auteurs_varies_en_priorite():
    banque = FausseBanque({"gateau": [
        resultat(1, "Ana"), resultat(2, "Ana"), resultat(3, "Ben"),
        resultat(4, "Cy")
    ]})

    images = banque.rechercher("gateau", 3)[:3]
    auteurs = [image["auteur"] for image in images]

    assert auteurs == ["Ana", "Ben", "Cy"]


def test_panne_reseau_sans_erreur():
    class BanqueHorsLigne(BanqueImages):
        def lire_url(self, url):
            raise URLError("hors ligne")

    assert BanqueHorsLigne().rechercher("wedding cake", 3) == []


def test_licences_lisibles():
    assert BanqueImages.nom_licence("cc0", "1.0") == "CC0"
    assert BanqueImages.nom_licence("pdm", "") == "Domaine public"
    assert BanqueImages.nom_licence("by-sa", "4.0") == "CC BY-SA 4.0"


def test_image_recadree_en_carre_jpeg():
    contenu = BanqueImages.reduire(image_png(1200))

    with Image.open(io.BytesIO(contenu)) as image:
        assert image.format == "JPEG"
        assert image.size == (500, 500)

    assert BanqueImages.reduire(b"pas une image") is None


def test_image_trop_lourde_ou_illisible_ignoree():
    image = BanqueImages.decrire(resultat(1))

    trop_lourde = FausseBanque(contenu=b"x" * (TAILLE_MAX_TELECHARGEMENT + 1))
    assert trop_lourde.telecharger(image) is None
    assert FausseBanque(contenu=b"panne").telecharger(image) is None


def test_composer_range_les_images_dans_le_dossier(tmp_path):
    banque = FausseBanque({
        "rustic cake": [resultat(1), resultat(2, "Ben")]
    })
    stock = ImagesMoodboard(tmp_path / "moodboard", banque)

    images = stock.composer(
        {"recherches_images": {"Gâteau": "rustic cake"}}, nombre=2
    )

    assert list(images) == ["Gâteau"]
    assert len(images["Gâteau"]) == 2
    assert stock.lire(images["Gâteau"][0]).startswith(b"\xff\xd8")
    assert "par Ana, CC BY 2.0" in ImagesMoodboard.credit(images["Gâteau"][0])
    assert "elegant outfit" in banque.recherches

    stock.composer({}, nombre=2)
    assert stock.lire(images["Gâteau"][0]) is None


def test_recherches_images_nettoyees():
    moodboard = nettoyer_moodboard({"recherches_images": {
        "Fleurs": "peony bouquet", "Table": 3, "Inconnu": "x"
    }})

    assert moodboard["recherches_images"] == {"Fleurs": "peony bouquet"}
    assert nettoyer_moodboard({"recherches_images": "x"})[
        "recherches_images"
    ] == {}


def test_pdf_avec_images_et_credits():
    moodboard = nettoyer_moodboard({"titre": "Bohème"})
    images = {
        element: [
            (
                BanqueImages.reduire(
                    image_png(teinte=(rang * 40, numero * 80, 90))
                ),
                f"« Photo » par Ana, CC BY 2.0 ({element})"
            )
            for numero in range(3)
        ]
        for rang, element in enumerate(ELEMENTS_MOODBOARD)
    }

    pdf = PdfReader(io.BytesIO(generer_moodboard_pdf(
        moodboard, "Léa et Liam", avec_liens=False, images=images
    )))
    texte = " ".join(page.extract_text() for page in pdf.pages)

    assert "Crédits des photos" in texte
    assert "par Ana, CC BY 2.0" in texte
    assert sum(len(page.images) for page in pdf.pages) == 18


def test_chaque_page_decale_la_selection_en_boucle():
    banque = FausseBanque({"boho arch": [
        resultat(numero, f"Auteur {numero}") for numero in range(1, 6)
    ]})

    def titres(page):
        images = banque.rechercher("boho arch", 3, page)[:3]
        return [image["titre"] for image in images]

    assert titres(1) == ["Photo 1", "Photo 2", "Photo 3"]
    assert titres(2) == ["Photo 4", "Photo 5", "Photo 1"]
    assert BanqueImages.tourner([], 3) == []


def test_une_photo_n_apparait_que_dans_un_element():
    trouvees = {
        "Décoration": [resultat(1), resultat(2)],
        "Tenues": [resultat(1), resultat(3), resultat(4)]
    }
    trouvees = {
        element: [BanqueImages.decrire(image) for image in liste]
        for element, liste in trouvees.items()
    }

    uniques = ImagesMoodboard.sans_doublons(trouvees, 2)

    assert [image["titre"] for image in uniques["Tenues"]] == [
        "Photo 3", "Photo 4"
    ]
