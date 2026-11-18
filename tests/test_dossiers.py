import json

from donnees.dossiers import chemin, creer, lister, libelle_dossier, migrer_ancien_dossier


def ecrire(fichier, data):
    fichier.write_text(json.dumps(data), encoding="utf-8")


def test_creer_puis_lister_par_date(tmp_path):
    creer({"noms": "Tom", "date": "2027-03-01"}, tmp_path)
    creer({"noms": "Léa et Liam", "date": "2026-12-20"}, tmp_path)

    assert [dossier["noms"] for dossier in lister(tmp_path)] == ["Léa et Liam", "Tom"]


def test_migration_des_anciens_fichiers(tmp_path):
    ecrire(tmp_path / "event_data.json", {"noms": "Léa et Liam"})
    ecrire(tmp_path / "budget_data.json", [])
    ecrire(tmp_path / "agenda_data.json", [{"titre": "Essayage", "date_heure": "2026-12-01T10:00:00", "duree_minutes": 60}])

    dossier_id = migrer_ancien_dossier(tmp_path)

    assert not (tmp_path / "event_data.json").exists()
    assert (tmp_path / "dossiers" / dossier_id / "budget_data.json").exists()
    assert json.loads((tmp_path / "agenda_data.json").read_text(encoding="utf-8"))[0]["dossier_id"] == dossier_id
    assert chemin(dossier_id, "event_data.json", tmp_path).endswith("event_data.json")


def test_pas_de_migration_sans_ancien_dossier(tmp_path):
    assert migrer_ancien_dossier(tmp_path) is None


def test_libelle_dossier():
    assert libelle_dossier({"noms": "Tom", "type_evenement": "Anniversaire", "date": "2027-03-01"}) == "Tom · Anniversaire · 01/03/2027"
    assert libelle_dossier({}) == "Sans nom · Autre"
