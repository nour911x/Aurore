import pytest

from donnees.dossiers import NOM_FICHE, creer, emplacement
from donnees.fiche_evenement import FicheEvenement
from metier.invites import nouvel_invite
from textes import formater_nom, noms_clients, noms_courts, pluriel


@pytest.mark.parametrize("saisi, attendu", [
    ("Léa et liam", "Léa et Liam"),
    ("LÉA & LIAM", "Léa & Liam"),
    ("jean-pierre", "Jean-Pierre"),
    ("Jean-pierre dupont", "Jean-Pierre Dupont"),
    ("marie de la tour", "Marie de la Tour"),
    ("de gaulle", "De Gaulle"),
    ("jeanne d'arc", "Jeanne d'Arc"),
    ("o'neil", "O'Neil"),
    ("ruud van nistelrooy", "Ruud van Nistelrooy"),
    ("Paul McDonald", "Paul McDonald"),
    ("  inès   et malik ", "Inès   et Malik"),
])
def test_format_person_name(saisi, attendu):
    assert formater_nom(saisi) == attendu


def test_nom_absent_et_forme_courte():
    assert formater_nom(None) is None
    assert noms_clients({"noms": None}) == "Les clients"
    assert noms_courts("Léa et Liam") == "Léa & Liam"


def test_pluriel():
    assert pluriel(0, "message") == "0 message"
    assert pluriel(1, "message") == "1 message"
    assert pluriel(3, "message") == "3 messages"
    assert pluriel(2, "rendez-vous", "rendez-vous") == "2 rendez-vous"


def test_noms_normalises_a_l_enregistrement(tmp_path):
    fiche = FicheEvenement(emplacement(creer({}, tmp_path), NOM_FICHE, tmp_path))
    fiche.remplacer({"noms": "léa et liam"})
    fiche.mettre_a_jour({"noms": "JEAN-PIERRE et marie de la tour"})

    assert FicheEvenement(fiche.emplacement).donnees["noms"] == "Jean-Pierre et Marie de la Tour"
    assert nouvel_invite("paul o'neil")["nom"] == "Paul O'Neil"
