import pytest

from donnees.stockage import Emplacement
from metier.galerie import Galerie, publiable


@pytest.fixture
def galerie(tmp_path):
    return Galerie(Emplacement(tmp_path, "test", "galerie"), tmp_path / "dossiers" / "test" / "galerie")


def test_ajouter_lire_et_supprimer_une_photo(galerie):
    photo = galerie.ajouter_photo(b"image", "image/png")

    assert photo["fichier"].endswith(".png")
    assert galerie.lire(photo) == b"image"
    assert Galerie(galerie.emplacement, galerie.dossier).photos == [photo]

    galerie.supprimer(photo["id"])
    assert galerie.photos == []
    assert list(galerie.dossier.iterdir()) == []


def test_photo_non_analysee_jamais_publiable(galerie):
    photo = galerie.ajouter_photo(b"image", "image/jpeg")

    assert galerie.a_analyser() == [photo]
    assert not publiable(photo, [])[0]

    galerie.modifier(photo["id"], personnes=False)
    assert galerie.a_analyser() == []
    assert galerie.publiables([]) == [photo]


def test_identifiants_inconnus_ignores(galerie):
    galerie.modifier("inconnu", legende="x")
    galerie.supprimer("inconnu")
    galerie.modifier_avis("inconnu", post="x")

    assert galerie.photos == galerie.avis == []


def test_avis(galerie):
    galerie.ajouter_avis("Léa", 5, "Parfait")
    galerie.modifier_avis(galerie.avis[0]["id"], post="Merci !")

    assert Galerie(galerie.emplacement, galerie.dossier).avis[0]["post"] == "Merci !"
