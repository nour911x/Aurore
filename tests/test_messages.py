import pytest

from donnees.stockage import Emplacement
from metier.messages import Messagerie, suggestion


CLIENT = {"destinataire": "Léa et Liam", "prestataire_id": None, "telephone": "0612345678", "email": None}


def messagerie_avec_un_message(tmp_path, statut="à valider"):
    messagerie = Messagerie(Emplacement(tmp_path, "test", "messages"))
    messagerie.ajouter(suggestion("cle", "libre", CLIENT, {}), "Bonjour !", statut)
    return messagerie, messagerie.messages[0]["id"]


def test_parcours_complet_jusqu_a_l_envoi(tmp_path):
    messagerie, message_id = messagerie_avec_un_message(tmp_path, "brouillon")

    for statut in ["à valider", "validé", "envoyé"]:
        messagerie.changer_statut(message_id, statut)

    message = messagerie.trouver(message_id)
    assert message["statut"] == "envoyé"
    assert [etape["statut"] for etape in message["historique"]] == ["à valider", "validé", "envoyé"]


def test_impossible_d_envoyer_sans_validation(tmp_path):
    messagerie, message_id = messagerie_avec_un_message(tmp_path)

    with pytest.raises(ValueError):
        messagerie.changer_statut(message_id, "envoyé")


def test_un_message_valide_n_est_plus_modifiable(tmp_path):
    messagerie, message_id = messagerie_avec_un_message(tmp_path)
    messagerie.changer_statut(message_id, "validé")

    with pytest.raises(ValueError):
        messagerie.modifier_contenu(message_id, "Autre texte")

    messagerie.changer_statut(message_id, "brouillon")
    messagerie.modifier_contenu(message_id, "Autre texte")
    assert messagerie.trouver(message_id)["contenu"] == "Autre texte"


def test_reecrire_repasse_a_valider(tmp_path):
    messagerie, message_id = messagerie_avec_un_message(tmp_path)
    messagerie.changer_statut(message_id, "validé")

    messagerie.reecrire(message_id, "Nouvelle version")

    assert messagerie.trouver(message_id)["statut"] == "à valider"


def test_un_message_annule_ou_envoye_est_definitif(tmp_path):
    messagerie, message_id = messagerie_avec_un_message(tmp_path)
    messagerie.changer_statut(message_id, "annulé")

    with pytest.raises(ValueError):
        messagerie.changer_statut(message_id, "à valider")
