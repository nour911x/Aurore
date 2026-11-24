import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ui.connexion as connexion
from config.profils import CLIENTS, ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import creer, emplacement_acces, supprimer
from metier.acces import DUREE_BLOCAGE, DUREE_LIEN, ECHECS_AUTORISES, Acces, LiensAcces, Tentatives, hacher, verifier


MOT_DE_PASSE = "mot-de-passe-de-test"

JOUR = date(2026, 12, 1)


@pytest.fixture
def liens(tmp_path):
    return LiensAcces(emplacement_acces(tmp_path))


def test_mot_de_passe_hache_avec_un_sel():
    hache = hacher(MOT_DE_PASSE)

    assert MOT_DE_PASSE not in hache
    assert hache != hacher(MOT_DE_PASSE)
    assert verifier(MOT_DE_PASSE, hache)
    assert not verifier("autre", hache)


@pytest.mark.parametrize("hache", ["", ":", "pas-de-l-hexa", "ab:"])
def test_hache_mal_forme_refuse(hache):
    assert not verifier("", hache)
    assert not verifier(MOT_DE_PASSE, hache)


def test_blocage_apres_trop_d_echecs():
    maintenant = [0.0]
    tentatives = Tentatives(lambda: maintenant[0])

    for _ in range(ECHECS_AUTORISES):
        assert tentatives.secondes_restantes() == 0
        tentatives.echec()

    assert tentatives.secondes_restantes() == DUREE_BLOCAGE
    maintenant[0] = DUREE_BLOCAGE
    assert tentatives.secondes_restantes() == 0


def test_lien_donne_acces_a_un_seul_espace(liens):
    jeton = liens.creer(PRESTATAIRE, "lea", "dj")

    assert liens.acces(jeton) == Acces(PRESTATAIRE, "lea", "dj")
    assert liens.acces(jeton + "x") is None
    assert liens.acces("") is None
    assert liens.du_dossier("tom") == []


def test_jeton_jamais_enregistre_en_clair(liens):
    jeton = liens.creer(CLIENTS, "lea")

    assert jeton not in json.dumps(LiensAcces(liens.emplacement).liens)
    assert LiensAcces(liens.emplacement).acces(jeton)


def test_lien_expire_et_revoque(liens):
    jeton = liens.creer(CLIENTS, "lea", aujourd_hui=JOUR)

    assert liens.acces(jeton, JOUR + DUREE_LIEN)
    assert liens.acces(jeton, JOUR + DUREE_LIEN + timedelta(days=1)) is None

    liens.revoquer(liens.liens[0]["id"])
    assert liens.acces(jeton, JOUR) is None


def test_supprimer_un_dossier_supprime_ses_liens(liens, tmp_path):
    dossier_id = creer({"noms": "Léa"}, tmp_path)
    jeton, autre = liens.creer(CLIENTS, dossier_id), liens.creer(CLIENTS, "tom")

    supprimer(dossier_id, tmp_path)
    liens.charger()

    assert liens.acces(jeton) is None
    assert liens.acces(autre)


def page_identification():
    import streamlit as st

    from ui.connexion import identifier

    acces = identifier()

    if acces:
        st.session_state.resultat = tuple(acces)


@pytest.fixture
def page(monkeypatch, tmp_path):
    connexion.tentatives.clear()
    monkeypatch.setenv("MOT_DE_PASSE_HACHE", hacher(MOT_DE_PASSE))
    monkeypatch.setattr(connexion, "emplacement_acces", lambda: emplacement_acces(tmp_path))

    return AppTest.from_function(page_identification)


def se_connecter(page, mot_de_passe):
    page.text_input[0].set_value(mot_de_passe)
    page.button[0].click().run()


def test_page_bloquee_sans_mot_de_passe_configure(page, monkeypatch):
    monkeypatch.setenv("MOT_DE_PASSE_HACHE", "")
    page.run()

    assert "resultat" not in page.session_state
    assert not page.text_input


def test_connexion_avec_le_bon_mot_de_passe_seulement(page):
    page.run()
    se_connecter(page, "faux")
    assert "resultat" not in page.session_state

    se_connecter(page, MOT_DE_PASSE)
    assert page.session_state.resultat == (ORGANISATEUR, None, None)


def test_le_bon_mot_de_passe_est_refuse_pendant_le_blocage(page):
    page.run()

    for _ in range(ECHECS_AUTORISES):
        se_connecter(page, "faux")

    se_connecter(page, MOT_DE_PASSE)

    assert "resultat" not in page.session_state
    assert "Trop d'essais" in page.error[0].value


def test_lien_valide_puis_vue_desactivee(page, tmp_path, monkeypatch):
    jeton = LiensAcces(emplacement_acces(tmp_path)).creer(CLIENTS, "lea")
    page.query_params["acces"] = jeton
    page.run()
    assert page.session_state.resultat == (CLIENTS, "lea", None)

    monkeypatch.setitem(connexion.PROFILS_ACTIFS, CLIENTS, False)
    del page.session_state["resultat"]
    page.run()
    assert "resultat" not in page.session_state


def test_un_faux_lien_ne_donne_rien_meme_avec_profil_dans_l_adresse(page):
    page.query_params["acces"] = "faux"
    page.query_params["profil"] = "Organisateur"
    page.run()

    assert "resultat" not in page.session_state
    assert page.error


def test_application_fermee_sans_connexion(monkeypatch):
    monkeypatch.setenv("MOT_DE_PASSE_HACHE", hacher(MOT_DE_PASSE))
    page = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"), default_timeout=30).run()

    assert [champ.label for champ in page.text_input] == ["Mot de passe organisateur"]
    assert not page.tabs
