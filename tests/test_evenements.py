from config.evenements import TYPES_EVENEMENT, CHAMPS_SPECIFIQUES, cle_type, champs_du_type, libelle_evenement


def test_types_reconnus_depuis_un_texte_libre():
    assert cle_type("mariage") == "mariage"
    assert cle_type("Baby shower") == "baby_shower"
    assert cle_type("Anniversaire surprise 30 ans") == "anniversaire"
    assert cle_type("EVJF") == "autre"
    assert cle_type(None) == "autre"


def test_chaque_champ_d_un_type_est_decrit():
    for type_evenement in TYPES_EVENEMENT.values():
        assert all(cle in CHAMPS_SPECIFIQUES for cle in type_evenement["champs"])


def test_champs_affiches_selon_le_type():
    assert "gender_reveal" in champs_du_type({"type_evenement": "Baby shower"})
    assert "preferences_musicales" not in champs_du_type({"type_evenement": "Anniversaire"})


def test_libelle_d_un_evenement_autre():
    assert libelle_evenement({"type_evenement": "Autre", "sous_type": "Fiançailles"}) == "Fiançailles"
    assert libelle_evenement({"type_evenement": "EVJF"}) == "EVJF"
    assert libelle_evenement({"type_evenement": "mariage"}) == "Mariage"
