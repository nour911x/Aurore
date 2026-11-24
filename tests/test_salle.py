import pytest

from donnees.stockage import Emplacement
from metier.invites import nouvel_invite
from metier.jour_j import ELEMENTS_SALLE, FORMES_TABLE, TABLE_HONNEUR, JourJ, creer_tables
from metier.salle import (
    COULEURS_PAR_DEFAUT,
    EMPLACEMENTS,
    LARGEUR_SALLE,
    MARGE,
    chevauchements,
    couleurs_salle,
    disposer,
    emplacement,
    tables_necessaires,
)


@pytest.fixture
def jour_j(tmp_path):
    jour_j = JourJ(Emplacement(tmp_path, "test", "jour_j"))
    jour_j.amenager(creer_tables(6, 8, "Ronde", 10), ELEMENTS_SALLE)

    return jour_j


def trouver(disposition, nom):
    return next(objet for objet in disposition["objets"] if objet["nom"] == nom)


def dans_la_salle(objet, disposition):
    return (
        objet["x"] - objet["largeur"] / 2 >= MARGE and objet["x"] + objet["largeur"] / 2 <= LARGEUR_SALLE - MARGE
        and objet["y"] - objet["profondeur"] / 2 >= MARGE and objet["y"] + objet["profondeur"] / 2 <= disposition["profondeur"] - MARGE
    )


@pytest.mark.parametrize("forme", FORMES_TABLE)
@pytest.mark.parametrize("places", [2, 8, 20])
@pytest.mark.parametrize("nombre", [1, 7, 60])
def test_disposition_automatique_sans_chevauchement(forme, places, nombre):
    disposition = disposer({"tables": creer_tables(nombre, places, forme, 30), "elements": ELEMENTS_SALLE, "placement": {}}, {})

    assert chevauchements(disposition) == []
    assert all(dans_la_salle(objet, disposition) for objet in disposition["objets"])
    assert len(disposition["objets"]) == nombre + 1 + len(ELEMENTS_SALLE)


def test_les_invites_remplissent_leur_table():
    paul = nouvel_invite("Paul", accompagnants=2)
    disposition = disposer({"tables": creer_tables(1, 8, "Ronde", 0), "elements": [], "placement": {}}, {"Table 1": [paul]})

    assert trouver(disposition, "Table 1")["occupees"] == 3
    assert trouver(disposition, "Table 1")["invites"] == ["Paul"]


def test_un_element_deplace_garde_sa_place(jour_j):
    jour_j.placer_element("DJ", 200, 300)
    disposition = disposer(JourJ(jour_j.emplacement).salle, {})

    assert (trouver(disposition, "DJ")["x"], trouver(disposition, "DJ")["y"]) == (200, 300)


def test_impossible_de_sortir_de_la_salle(jour_j):
    jour_j.placer_element(TABLE_HONNEUR, -5000, 99999)
    disposition = disposer(jour_j.salle, {})

    assert dans_la_salle(trouver(disposition, TABLE_HONNEUR), disposition)


@pytest.mark.parametrize(("nom", "x", "y"), [("Inconnu", 1, 1), ("DJ", "x", 1), ("DJ", float("nan"), 1), ("DJ", None, 1), ("DJ", True, 1)])
def test_deplacement_invalide_refuse(jour_j, nom, x, y):
    with pytest.raises(ValueError):
        jour_j.placer_element(nom, x, y)

    assert jour_j.salle["positions"] == {}


def test_chevauchement_signale(jour_j):
    position = trouver(disposer(jour_j.salle, {}), "Table 1")
    jour_j.placer_element("DJ", position["x"], position["y"])

    assert {"DJ", "Table 1"} in [set(paire) for paire in chevauchements(disposer(jour_j.salle, {}))]


@pytest.mark.parametrize("choix", list(EMPLACEMENTS))
def test_emplacements_proposes_dans_la_salle(jour_j, choix):
    disposition = disposer(jour_j.salle, {})
    jour_j.placer_element("DJ", *emplacement(disposition, "DJ", choix))
    disposition = disposer(jour_j.salle, {})

    assert dans_la_salle(trouver(disposition, "DJ"), disposition)


def test_reamenager_garde_les_positions_des_elements_restants(jour_j):
    jour_j.placer_element("DJ", 200, 300)
    jour_j.placer_element("Table 6", 300, 300)
    jour_j.definir_couleurs({"nappe": "#000000"})
    jour_j.amenager(creer_tables(2, 8, "Ronde", 10), ["DJ"])

    assert jour_j.salle["positions"] == {"DJ": [200, 300]}
    assert jour_j.salle["couleurs"] == {"nappe": "#000000"}

    jour_j.reinitialiser_positions()
    assert jour_j.salle["positions"] == {}


def test_ancienne_salle_sans_positions_toujours_lisible():
    assert disposer({"tables": creer_tables(1, 8, "Ronde", 0), "elements": ["DJ", "Élément supprimé"], "placement": {}}, {})["objets"]


@pytest.mark.parametrize(("invites", "attendu"), [(0, 1), (10, 1), (11, 1), (18, 1), (19, 2), (100, 12)])
def test_nombre_de_tables_calcule(invites, attendu):
    assert tables_necessaires(invites, 8, 10) == attendu


def test_couleurs_choisies_avant_celles_du_moodboard():
    moodboard = {"couleurs": [{"nom": "Terracotta", "hex": "#CC6644"}]}

    assert couleurs_salle({}, {}) == COULEURS_PAR_DEFAUT
    assert couleurs_salle({}, moodboard)["accent"] == "#CC6644"
    assert couleurs_salle({"couleurs": {"accent": "#111111"}}, moodboard)["accent"] == "#111111"
