import json

import pytest

from donnees.dossiers import lire_etat, lister, supprimer
from donnees.migration import migrer_json
from donnees.stockage import Emplacement, charger_donnees, est_vide, sauvegarder_donnees


RDVS = [{"titre": "Essayage", "dossier_id": "lea"}, {"titre": "Visite", "dossier_id": "tom"}]


@pytest.fixture
def anciens_json(tmp_path):
    for fichier, contenu in {
        "agenda_data.json": RDVS,
        "aurore_etat.json": {"demo_initialisee": True},
        "dossiers/lea/event_data.json": {"noms": "Léa et Liam", "date": "2026-12-20"},
        "dossiers/lea/budget_data.json": [{"nom": "Traiteur"}],
        "dossiers/tom/event_data.json": {"noms": "Tom", "date": "2027-03-01"}
    }.items():
        chemin = tmp_path / fichier
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")

    return tmp_path


def test_migration_reprend_tout_et_garde_les_fichiers(anciens_json):
    assert migrer_json(anciens_json) == 5
    assert [dossier["noms"] for dossier in lister(anciens_json)] == ["Léa et Liam", "Tom"]
    assert charger_donnees(Emplacement(anciens_json, "lea", "budget_data"), []) == [{"nom": "Traiteur"}]
    assert charger_donnees(Emplacement(anciens_json, "", "agenda_data"), []) == RDVS
    assert lire_etat(anciens_json) == {"demo_initialisee": True}
    assert (anciens_json / "dossiers/lea/event_data.json").exists()


def test_migration_une_seule_fois(anciens_json):
    migrer_json(anciens_json)
    fiche = Emplacement(anciens_json, "lea", "event_data")
    sauvegarder_donnees(fiche, {"noms": "Léa et Karim"})

    assert migrer_json(anciens_json) == 0
    assert charger_donnees(fiche, {}) == {"noms": "Léa et Karim"}


def test_fichier_corrompu_signale_sans_migration_partielle(anciens_json):
    (anciens_json / "dossiers/tom/event_data.json").write_text('{"noms": "To', encoding="utf-8")

    with pytest.raises(ValueError, match="event_data.json"):
        migrer_json(anciens_json)

    assert est_vide(anciens_json)


def test_supprimer_efface_aussi_les_anciens_fichiers(anciens_json):
    migrer_json(anciens_json)
    supprimer("lea", anciens_json)

    assert [dossier["noms"] for dossier in lister(anciens_json)] == ["Tom"]
    assert charger_donnees(Emplacement(anciens_json, "", "agenda_data"), []) == RDVS[1:]
    assert json.loads((anciens_json / "agenda_data.json").read_text(encoding="utf-8")) == RDVS[1:]
    assert not (anciens_json / "dossiers/lea").exists()
