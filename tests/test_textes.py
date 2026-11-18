import json

import pytest

from donnees.dossiers import FICHIER_FICHE, chemin, creer, lire_etat, migrer_noms
from donnees.event_state import EventSheet
from metier.invites import nouvel_invite
from textes import format_person_name, noms_clients, pluriel


@pytest.mark.parametrize("saisi, attendu", [
    ("Léa et liam", "Léa et Liam"),
    ("LÉA & LIAM", "Léa & Liam"),
    ("jean-pierre", "Jean-Pierre"),
    ("Jean-pierre dupont", "Jean-Pierre Dupont"),
    ("marie de la tour", "Marie de la Tour"),
    ("de gaulle", "De Gaulle"),
    ("jeanne d'arc", "Jeanne d'Arc"),
    ("o'neil", "O'Neil"),
    ("ruud van nistelrooy", "Ruud van Nistelrooy"),
    ("Paul McDonald", "Paul McDonald"),
    ("  inès   et malik ", "Inès   et Malik"),
])
def test_format_person_name(saisi, attendu):
    assert format_person_name(saisi) == attendu


def test_nom_absent():
    assert format_person_name(None) is None
    assert noms_clients({"noms": None}) == "Les clients"
    assert noms_clients({"noms": "tom"}) == "Tom"


def test_pluriel():
    assert pluriel(0, "message") == "0 message"
    assert pluriel(1, "message") == "1 message"
    assert pluriel(3, "message") == "3 messages"
    assert pluriel(2, "rendez-vous", "rendez-vous") == "2 rendez-vous"


def test_noms_normalises_a_l_enregistrement(tmp_path):
    fiche = EventSheet(chemin(creer({}, tmp_path), FICHIER_FICHE, tmp_path))
    fiche.remplacer({"noms": "léa et liam"})
    fiche.update({"noms": "JEAN-PIERRE et marie de la tour"})

    assert EventSheet(fiche.file_path).data["noms"] == "Jean-Pierre et Marie de la Tour"
    assert nouvel_invite("paul o'neil")["nom"] == "Paul O'Neil"


def test_migration_des_noms_des_dossiers_existants(tmp_path):
    dossier_id = creer({"noms": "léa et liam", "droit_image": [{"personne": "léa"}]}, tmp_path)
    dossier = tmp_path / "dossiers" / dossier_id
    (dossier / "invites_data.json").write_text(json.dumps({"invites": [{"nom": "paul dupont"}], "faire_part": ""}), encoding="utf-8")
    (dossier / "messages_data.json").write_text(json.dumps([
        {"destinataire": "léa et liam", "prestataire_id": None},
        {"destinataire": "DJ SoundBox", "prestataire_id": "dj"}
    ]), encoding="utf-8")

    migrer_noms(tmp_path)

    fiche = json.loads((dossier / "event_data.json").read_text(encoding="utf-8"))
    messages = json.loads((dossier / "messages_data.json").read_text(encoding="utf-8"))
    assert fiche["noms"] == "Léa et Liam"
    assert fiche["droit_image"][0]["personne"] == "Léa"
    assert json.loads((dossier / "invites_data.json").read_text(encoding="utf-8"))["invites"][0]["nom"] == "Paul Dupont"
    assert [message["destinataire"] for message in messages] == ["Léa et Liam", "DJ SoundBox"]
    assert lire_etat(tmp_path)["noms_normalises"]
