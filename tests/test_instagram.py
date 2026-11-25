import io
import json
from email.message import Message
from urllib.error import HTTPError

import pytest
from PIL import Image

from metier.instagram import (
    CarteTemoignage,
    ErreurInstagram,
    PublicationInstagram,
)


JETON = "jeton-secret"
URL_PUBLIQUE = "https://aurore.exemple.org/"


class FauxInstagram(PublicationInstagram):
    """Répond comme l'API Instagram, sans réseau."""

    def __init__(self, dossier, statuts=("IN_PROGRESS", "FINISHED")):
        self.pauses = []
        super().__init__(
            JETON, "17841400000", URL_PUBLIQUE, dossier, self.pauses.append
        )
        self.statuts = list(statuts)
        self.requetes = []

    def lire_url(self, requete):
        corps = requete.data.decode() if requete.data else ""
        self.requetes.append({
            "methode": requete.get_method(), "url": requete.full_url,
            "corps": corps, "autorisation": requete.get_header("Authorization")
        })

        if requete.full_url.endswith("/media"):
            self.image_publique = sorted(self.dossier_public.iterdir())
            reponse = {"id": "conteneur1"}
        elif "conteneur1?fields=status_code" in requete.full_url:
            reponse = {"status_code": self.statuts.pop(0)}
        elif requete.full_url.endswith("/media_publish"):
            reponse = {"id": "post1"}
        else:
            reponse = {"permalink": "https://www.instagram.com/p/abc/"}

        return json.dumps(reponse).encode()


def test_publication_complete(tmp_path):
    instagram = FauxInstagram(tmp_path / "publications")

    resultat = instagram.publier(b"image", "Une belle table 🌿")

    assert resultat == {
        "id": "post1", "lien": "https://www.instagram.com/p/abc/"
    }
    assert [requete["methode"] for requete in instagram.requetes] == [
        "POST", "GET", "GET", "POST", "GET"
    ]
    creation = instagram.requetes[0]
    assert "image_url=https%3A%2F%2Faurore.exemple.org%2Fapp%2Fstatic" in (
        creation["corps"]
    )
    assert "caption=Une+belle+table" in creation["corps"]
    assert instagram.pauses == [2]


def test_le_jeton_ne_passe_jamais_dans_l_adresse(tmp_path):
    instagram = FauxInstagram(tmp_path / "publications")
    instagram.publier(b"image", "Légende")

    for requete in instagram.requetes:
        assert JETON not in requete["url"] and JETON not in requete["corps"]
        assert requete["autorisation"] == f"Bearer {JETON}"


def test_l_image_n_est_publique_que_pendant_la_publication(tmp_path):
    instagram = FauxInstagram(tmp_path / "publications")
    instagram.publier(b"image", "Légende")

    assert len(instagram.image_publique) == 1
    assert list(instagram.dossier_public.iterdir()) == []


def test_image_illisible_par_instagram(tmp_path):
    instagram = FauxInstagram(tmp_path / "publications", statuts=["ERROR"])

    with pytest.raises(ErreurInstagram, match="AURORE_URL_PUBLIQUE"):
        instagram.publier(b"image", "Légende")

    assert list(instagram.dossier_public.iterdir()) == []


def test_conteneur_trop_long_a_preparer(tmp_path):
    instagram = FauxInstagram(
        tmp_path / "publications", statuts=["IN_PROGRESS"] * 10
    )

    with pytest.raises(ErreurInstagram, match="trop de temps"):
        instagram.publier(b"image", "Légende")


def test_refus_de_meta_explique(tmp_path):
    class InstagramRefuse(FauxInstagram):
        def lire_url(self, requete):
            corps = io.BytesIO(json.dumps(
                {"error": {"message": "Invalid OAuth access token"}}
            ).encode())
            raise HTTPError(requete.full_url, 400, "Bad", Message(), corps)

    with pytest.raises(ErreurInstagram, match="Invalid OAuth access token"):
        InstagramRefuse(tmp_path).publier(b"image", "Légende")


def test_sans_configuration_rien_n_est_envoye(tmp_path, monkeypatch):
    for variable in ("INSTAGRAM_TOKEN", "INSTAGRAM_USER_ID",
                     "AURORE_URL_PUBLIQUE"):
        monkeypatch.delenv(variable, raising=False)

    monkeypatch.setattr("metier.instagram.load_dotenv", lambda: None)
    instagram = PublicationInstagram(dossier_public=tmp_path)

    assert not instagram.est_configuree()

    with pytest.raises(ErreurInstagram, match="pas configurée"):
        instagram.publier(b"image", "Légende")

    assert list(tmp_path.iterdir()) == []


def test_carte_temoignage_carree_avec_accents():
    carte = CarteTemoignage(
        "Une journée magique, tout était parfait à l'arrivée !" * 3, 9, "Léa"
    )

    with Image.open(io.BytesIO(carte.generer())) as image:
        assert image.format == "JPEG"
        assert image.size == (1080, 1080)

    assert carte.note == 5
    assert CarteTemoignage.fichier_police() is not None
    assert CarteTemoignage("Top", -1, "").note == 0
