from config.evenements import CHAMPS_SPECIFIQUES, TYPES_EVENEMENT, champs_du_type, champs_masques, cle_type, libelle_evenement
from donnees.dossiers import FICHIER_FICHE, chemin, creer
from donnees.fiche_evenement import FicheEvenement


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


def test_changer_de_type_masque_les_champs_sans_les_supprimer(tmp_path):
    dossier_id = creer({"type_evenement": "Mariage", "ceremonie": "Laïque à 15h", "preferences_musicales": ["soul"]}, tmp_path)
    fiche = FicheEvenement(chemin(dossier_id, FICHIER_FICHE, tmp_path))

    assert champs_masques(fiche.donnees, "anniversaire") == ["Cérémonie", "Musique"]

    fiche.changer_type("anniversaire")
    relue = FicheEvenement(fiche.chemin_fichier).donnees

    assert "ceremonie" not in champs_du_type(relue)
    assert relue["ceremonie"] == "Laïque à 15h"

    fiche.changer_type("mariage")

    assert champs_du_type(fiche.donnees)["ceremonie"] == "Cérémonie"
    assert fiche.donnees["ceremonie"] == "Laïque à 15h"
