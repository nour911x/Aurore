import pytest

from donnees.stockage import Emplacement
from metier.invites import nouvel_invite
from metier.jour_j import TABLE_HONNEUR, JourJ, creer_tables, heure_valide, nettoyer_deroule


@pytest.fixture
def jour_j(tmp_path):
    jour_j = JourJ(Emplacement(tmp_path, "test", "jour_j"))
    jour_j.amenager(creer_tables(2, 3, "Ronde", 2), ["Buffet"])

    return jour_j


def invite(invite_id, accompagnants=0, statut="Confirmé"):
    return nouvel_invite(invite_id, accompagnants=accompagnants, statut=statut, invite_id=invite_id)


@pytest.mark.parametrize(("texte", "attendu"), [("14h30", "14:30"), ("9 h", "09:00"), ("25:00", ""), ("12:75", ""), (None, ""), ("midi", "")])
def test_heures_reconnues(texte, attendu):
    assert heure_valide(texte) == attendu


def test_deroule_trie_avec_l_apres_minuit_a_la_fin():
    lignes = [{"heure": "01h00", "moment": "Fin"}, {"moment": "Sans heure"}, {"heure": "15:00", "moment": "Cérémonie"}, {"heure": "10:00", "moment": " "}]

    assert [ligne["moment"] for ligne in nettoyer_deroule(lignes)] == ["Cérémonie", "Fin", "Sans heure"]


def test_placement_respecte_les_places_et_les_refus(jour_j):
    invites = [invite("a", 1), invite("b", 1), invite("c"), invite("d", statut="Décliné")]
    places = jour_j.placer({"a": "table 1", "b": "Table 1", "c": "TABLE 1", "d": "Table 2"}, invites)

    assert places == 2
    assert [i["id"] for i in jour_j.par_table(invites)["Table 1"]] == ["a", "c"]
    assert [i["id"] for i in jour_j.non_places(invites)] == ["b"]


def test_placement_accepte_une_reponse_imbriquee_de_l_ia(jour_j):
    assert jour_j.placer({"placement": {"a": TABLE_HONNEUR}}, [invite("a")]) == 1


def test_reamenager_oublie_les_tables_supprimees(jour_j):
    jour_j.placer({"a": "Table 2", "b": "Table 1"}, [invite("a"), invite("b")])
    jour_j.amenager(creer_tables(1, 3, "Ronde", 0), [])

    assert jour_j.salle["placement"] == {"b": "Table 1"}


def test_jour_j_conserve_apres_rechargement(jour_j):
    jour_j.definir_deroule([{"heure": "14h", "moment": "Accueil"}])

    assert JourJ(jour_j.emplacement).deroule == jour_j.deroule
    assert JourJ(jour_j.emplacement).salle == jour_j.salle
