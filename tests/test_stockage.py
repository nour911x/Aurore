import sqlite3

import pytest

from donnees.stockage import COMMUN, Emplacement, charger_donnees, charger_dossier, ecrire, est_vide, premier, sauvegarder_donnees, transaction


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


def test_charger_renvoie_le_defaut_si_rien_n_est_enregistre(tmp_path):
    assert charger_donnees(Emplacement(tmp_path, COMMUN, "absent"), []) == []
    assert est_vide(tmp_path)


def test_sauvegarder_remplace_et_garde_les_accents(tmp_path):
    fiche = Emplacement(tmp_path, "lea", "event_data")
    sauvegarder_donnees(fiche, {"noms": "Brouillon"})
    sauvegarder_donnees(fiche, {"noms": "Léa et Liam"})

    assert charger_donnees(fiche, {}) == {"noms": "Léa et Liam"}
    assert charger_dossier(tmp_path, "lea") == {"event_data": {"noms": "Léa et Liam"}}
    assert charger_dossier(tmp_path, "tom") == {}


def test_transaction_annulee_en_cas_d_erreur(tmp_path):
    fiche = Emplacement(tmp_path, "lea", "event_data")
    sauvegarder_donnees(fiche, {"noms": "Léa"})

    with pytest.raises(RuntimeError), transaction(tmp_path) as connexion:
        ecrire(connexion, "lea", "event_data", {"noms": "Effacée"})
        raise RuntimeError

    assert charger_donnees(fiche, {}) == {"noms": "Léa"}


def test_donnees_impossibles_a_enregistrer_ne_detruisent_rien(tmp_path):
    fiche = Emplacement(tmp_path, "lea", "event_data")
    sauvegarder_donnees(fiche, {"noms": "Léa"})

    with pytest.raises(TypeError):
        sauvegarder_donnees(fiche, {"noms": object()})

    assert charger_donnees(fiche, {}) == {"noms": "Léa"}


def test_un_texte_sql_reste_du_texte(tmp_path):
    piege = Emplacement(tmp_path, "lea'; DROP TABLE contenus; --", "event_data")
    sauvegarder_donnees(piege, "x")

    assert charger_donnees(piege, None) == "x"


def test_la_connexion_est_fermee(tmp_path):
    with transaction(tmp_path) as connexion:
        pass

    with pytest.raises(sqlite3.ProgrammingError):
        connexion.execute("SELECT 1")
