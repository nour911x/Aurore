import json
from types import SimpleNamespace

import httpx
import pytest
from groq import APIConnectionError, APITimeoutError, InternalServerError

from llm.agent import AgentConversation
from llm.base import DELAI_REPONSE, NOMBRE_ESSAIS, Agent, CleGroqManquante
from llm.outils import Outils
from textes import ERREUR_IA_PAR_DEFAUT, ERREURS_IA, message_erreur


REQUETE = httpx.Request("POST", "https://api.groq.com")

COUPURE = APIConnectionError(request=REQUETE)


def reponse(texte):
    return SimpleNamespace(content=texte, tool_calls=None)


def appel_outil(nom, **arguments):
    fonction = SimpleNamespace(name=nom, arguments=json.dumps(arguments))
    return SimpleNamespace(content="", tool_calls=[SimpleNamespace(id="1", function=fonction, model_dump=dict)])


class FauxAgenda:
    def __init__(self, conflit=None):
        self.rdvs = []
        self.conflit = conflit

    def ajouter_rdv(self, titre, *details):
        if not self.conflit:
            self.rdvs.append(titre)

        return self.conflit


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("GROQ_KEY", "cle-de-test")
    return AgentConversation()


def jouer(agent, *etapes):
    restantes = list(etapes)

    def appel(messages, **options):
        etape = restantes.pop(0)

        if isinstance(etape, Exception):
            raise etape

        return etape

    agent.appel = appel


def outils_avec(agenda):
    fiche = SimpleNamespace(infos_sans_historique=lambda: {})
    return Outils(fiche, agenda, None, None, None, None, None, None, None)


def test_client_groq_a_un_delai_et_reessaie(agent):
    assert agent.client_groq.timeout == DELAI_REPONSE
    assert agent.client_groq.max_retries == NOMBRE_ESSAIS


def test_cle_absente_signalee(monkeypatch):
    monkeypatch.setenv("GROQ_KEY", "")

    with pytest.raises(CleGroqManquante):
        Agent()


def test_coupure_sans_action_ne_garde_pas_le_message_dans_l_historique(agent):
    jouer(agent, COUPURE)

    with pytest.raises(APIConnectionError):
        agent.demander("Bonjour")

    assert agent.lire_historique() == []


def test_coupure_apres_une_action_dit_ce_qui_est_fait(agent):
    agenda = FauxAgenda()
    jouer(agent, appel_outil("creer_rdv", titre="Essayage", date_heure="2026-12-01 10:00"), COUPURE)

    texte = agent.demander("oui", outils=outils_avec(agenda))

    assert agenda.rdvs == ["Essayage"]
    assert "creer rdv" in texte
    assert [message["role"] for message in agent.lire_historique()] == ["user", "assistant"]


def test_action_refusee_n_est_pas_annoncee_comme_faite(agent):
    outils = outils_avec(FauxAgenda(conflit={"titre": "Visite"}))
    jouer(agent, appel_outil("creer_rdv", titre="Essayage", date_heure="2026-12-01 10:00"), COUPURE)

    with pytest.raises(APIConnectionError):
        agent.demander("oui", outils=outils)

    assert outils.actions == []


def test_reponse_vide_acceptee(agent):
    jouer(agent, reponse(None))

    assert agent.suggerer_budget_postes({}) == []


def test_messages_d_erreur():
    saturation = InternalServerError("503", response=httpx.Response(503, request=REQUETE), body=None)

    assert message_erreur(APITimeoutError(request=REQUETE)) == ERREURS_IA["APIConnectionError"]
    assert message_erreur(saturation) == ERREURS_IA["InternalServerError"]
    assert message_erreur(ValueError()) == ERREUR_IA_PAR_DEFAUT
