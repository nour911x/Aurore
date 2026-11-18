from donnees.dossiers import creer, libelle_dossier, lister


def test_creer_puis_lister_par_date(tmp_path):
    creer({"noms": "Tom", "date": "2027-03-01"}, tmp_path)
    creer({"noms": "Léa et Liam", "date": "2026-12-20"}, tmp_path)

    assert [dossier["noms"] for dossier in lister(tmp_path)] == ["Léa et Liam", "Tom"]


def test_libelle_dossier():
    assert libelle_dossier({"noms": "Tom", "type_evenement": "Anniversaire", "date": "2027-03-01"}) == "Tom · Anniversaire · 01/03/2027"
    assert libelle_dossier({}) == "Sans nom · Autre"
