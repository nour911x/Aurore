import json
from datetime import datetime, timedelta

import pytest

from config.profils import PRESTATAIRE
from donnees.fiche_evenement import FicheEvenement
from donnees.stockage import Emplacement
from llm.outils import Outils
from metier.agenda import Agenda
from metier.budget import Budget
from metier.devis import CarnetDevis
from metier.invites import ListeInvites
from metier.jour_j import JourJ
from metier.messages import Messagerie
from metier.prestataires import Annuaire, Carnet


DEMAIN = f"{datetime.now() + timedelta(days=1):%Y-%m-%d} 10:00"


@pytest.fixture
def outils(tmp_path):
    def ou(nom):
        return Emplacement(tmp_path, "lea", nom)

    outils = Outils(
        FicheEvenement(ou("fiche")), Agenda(ou("agenda"), "lea"), Budget(ou("budget")), Carnet(Annuaire(ou("annuaire")), ou("selection")),
        ListeInvites(ou("invites")), Messagerie(ou("messages")), CarnetDevis(ou("devis")), JourJ(ou("jour_j")), None
    )
    outils.avec_outlook = False

    return outils


def executer(outils, outil, /, **arguments):
    return json.loads(outils.executer(outil, arguments))


def test_agenda(outils):
    executer(outils, "creer_rdv", titre="Essayage", date_heure=DEMAIN, avec=None)

    assert executer(outils, "creer_rdv", titre="Visite", date_heure=DEMAIN)["erreur"] == "conflit d'horaire"
    assert [rdv["titre"] for rdv in executer(outils, "consulter_agenda")] == ["Essayage"]

    executer(outils, "supprimer_rdv", titre="essayage", date_heure=DEMAIN)
    assert executer(outils, "consulter_agenda") == []
    assert "erreur" in executer(outils, "supprimer_rdv", titre="essayage", date_heure=DEMAIN)


def test_budget(outils):
    outils.budget.ajouter_poste("Traiteur", 5000)
    executer(outils, "ajouter_facture", poste="traiteur", libelle="Acompte", montant=1500, echeance="2026-12-01")

    assert executer(outils, "consulter_budget")["postes"] == [{"nom": "Traiteur", "prevu": 5000, "engage": 1500}]
    assert "introuvable" in executer(outils, "ajouter_facture", poste="Fleurs", libelle="x", montant=1, echeance="2026-12-01")["erreur"]


def test_prestataires_et_devis(outils):
    executer(outils, "ajouter_prestataire", nom="DJ Groove", categorie="DJ / Musiciens")
    executer(outils, "changer_statut_prestataire", nom="dj groove", statut="Réservé")
    lignes = [{"designation": "Soirée", "quantite": 1, "prix_unitaire": 1000}]

    assert executer(outils, "consulter_prestataires")[0]["statut"] == "Réservé"
    assert executer(outils, "creer_devis", emetteur="DJ Groove", lignes=lignes)["ttc"] == 1200
    assert "erreur" in executer(outils, "creer_devis", emetteur="AURORE", lignes=[])


def test_invites(outils):
    executer(outils, "ajouter_invite", nom="paul martin")
    executer(outils, "noter_reponse_invite", nom="Paul Martin", statut="Confirmé", regime="Végan", allergies="noix")
    recap = executer(outils, "consulter_invites")

    assert recap["couverts_confirmes"] == 1
    assert "Paul" not in json.dumps(recap["allergies"])
    assert "info" in executer(outils, "consulter_deroule")


def test_un_message_de_l_ia_reste_a_valider(outils):
    executer(outils, "preparer_message", destinataire="clients", contenu="Bonjour")

    assert [message["statut"] for message in outils.messagerie.messages] == ["à valider"]


def test_le_prestataire_ne_peut_rien_ecrire_ni_voir_les_autres(outils):
    executer(outils, "ajouter_prestataire", nom="DJ Groove", categorie="DJ / Musiciens")
    executer(outils, "creer_rdv", titre="Dégustation", date_heure=DEMAIN, avec="Traiteur")
    outils.pour_espace(PRESTATAIRE, outils.carnet.prestataires[0])

    assert executer(outils, "consulter_agenda") == []

    for nom in ("creer_rdv", "consulter_budget", "consulter_prestataires", "preparer_message"):
        assert "non disponible" in executer(outils, nom)["erreur"]

    assert "regimes" not in executer(outils, "consulter_invites")
