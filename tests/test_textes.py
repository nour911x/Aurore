import pytest

from textes import format_person_name, noms_clients, pluriel


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
    assert format_person_name(saisi) == attendu


def test_nom_absent():
    assert format_person_name(None) is None
    assert noms_clients({"noms": None}) == "Les clients"
    assert noms_clients({"noms": "tom"}) == "Tom"


def test_pluriel():
    assert pluriel(0, "message") == "0 message"
    assert pluriel(1, "message") == "1 message"
    assert pluriel(3, "message") == "3 messages"
    assert pluriel(2, "rendez-vous", "rendez-vous") == "2 rendez-vous"
