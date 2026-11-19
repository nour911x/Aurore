from donnees.stockage import charger_json, premier, sauvegarder_json


ELEMENTS = [
    {"id": "a1", "nom": "Saveurs d'Orient", "dossier_id": "lea"},
    {"id": "b2", "nom": "DJ Groove", "dossier_id": "lea"},
    {"id": "c3", "nom": "DJ Groove", "dossier_id": "tom"},
]


def test_premier_trouve_par_un_critere():
    assert premier(ELEMENTS, id="b2")["nom"] == "DJ Groove"


def test_premier_combine_les_criteres():
    assert premier(ELEMENTS, nom="DJ Groove", dossier_id="tom")["id"] == "c3"


def test_premier_renvoie_none_si_absent():
    assert premier(ELEMENTS, id="zz") is None
    assert premier([], id="a1") is None


def test_charger_json_renvoie_le_defaut_si_le_fichier_manque(tmp_path):
    assert charger_json(tmp_path / "absent.json", []) == []


def test_sauvegarder_puis_charger_garde_les_accents(tmp_path):
    fichier = tmp_path / "donnees.json"
    sauvegarder_json(fichier, {"noms": "Léa et Liam"})

    assert charger_json(fichier, {}) == {"noms": "Léa et Liam"}
    assert "Léa" in fichier.read_text(encoding="utf-8")
