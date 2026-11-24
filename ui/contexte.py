
import streamlit as st

from config.profils import PRESTATAIRE
from donnees.demo import actualiser_rdvs, demo_au_premier_lancement
from donnees.dossiers import NOM_FICHE, NOM_SELECTION, chemin, emplacement, emplacement_agenda, emplacement_annuaire
from donnees.dossiers import lister as lister_dossiers
from donnees.fiche_evenement import FicheEvenement
from donnees.migration import migrer_json
from llm.agent import AgentConversation
from llm.outils import Outils
from metier.agenda import Agenda
from metier.budget import Budget
from metier.devis import CarnetDevis
from metier.documents import Documents
from metier.galerie import Galerie
from metier.inspiration import Inspiration
from metier.invites import ListeInvites
from metier.jour_j import (
    JourJ,
)
from metier.messages import Messagerie
from metier.prestataires import Annuaire, Carnet, appliquer_statut
from metier.rgpd import peut_recevoir_sante
from ui import composants
from ui.commun import (
    INFOS_PAR_CATEGORIE,
)
from ui.index_documents import ouvrir_rag


PREFIXES_DONNEES = (
    "fiche_evenement_", "budget_", "carnet_", "messagerie_", "liste_invites_", "inspiration_", "jour_j_", "galerie_", "achats_", "documents_"
)


class Contexte:
    def __init__(self, acces):
        self.acces = acces
        self.prestataire = None
        self.profil = None
        self.agent = None
        self.dossier_id = self.choisir_dossier()
        self.agenda = composants.obtenir_persistant("agenda", lambda: Agenda(emplacement_agenda()))
        self.annuaire = composants.obtenir_persistant("annuaire", lambda: Annuaire(emplacement_annuaire()))
        st.session_state.setdefault("version_galerie", 0)
        st.session_state.setdefault("version_invites", 0)
        st.session_state.setdefault("briefings", {})
        st.session_state.setdefault("lignes_devis", [])
        st.session_state.setdefault("version_lignes", 0)

        if self.dossier_id:
            self.charger_dossier()


    def preparer_conversation(self):
        self.outils.pour_espace(self.profil, self.prestataire)
        self.agent = composants.obtenir_persistant(self.cle_conversation(self.profil), AgentConversation)


    def choisir_dossier(self):
        migrer_json()
        demo_au_premier_lancement()

        if actualiser_rdvs():
            st.session_state.pop("agenda", None)

        self.dossiers = {dossier["id"]: dossier for dossier in lister_dossiers()}

        if self.acces.par_lien:
            return self.acces.dossier_id if self.acces.dossier_id in self.dossiers else None

        if st.session_state.get("dossier_actif") not in self.dossiers:
            st.session_state.dossier_actif = next(iter(self.dossiers), None)

        return st.session_state.dossier_actif


    def obtenir_du_dossier(self, cle, classe, nom):
        return composants.obtenir_persistant(f"{cle}_{self.dossier_id}", lambda: classe(emplacement(self.dossier_id, nom)))


    def charger_dossier(self):
        self.agenda.pour_dossier(self.dossier_id)
        self.fiche_evenement = self.obtenir_du_dossier("fiche_evenement", FicheEvenement, NOM_FICHE)
        self.budget = self.obtenir_du_dossier("budget", Budget, "budget_data")
        self.carnet = composants.obtenir_persistant(
            f"carnet_{self.dossier_id}", lambda: Carnet(self.annuaire, emplacement(self.dossier_id, NOM_SELECTION))
        )
        self.messagerie = self.obtenir_du_dossier("messagerie", Messagerie, "messages_data")
        self.carnet_devis = self.obtenir_du_dossier("carnet_devis", CarnetDevis, "devis_data")
        self.liste_invites = self.obtenir_du_dossier("liste_invites", ListeInvites, "invites_data")
        self.inspiration = self.obtenir_du_dossier("inspiration", Inspiration, "inspiration_data")
        self.jour_j = self.obtenir_du_dossier("jour_j", JourJ, "jour_j_data")
        self.galerie = composants.obtenir_persistant(
            f"galerie_{self.dossier_id}",
            lambda: Galerie(emplacement(self.dossier_id, "galerie_data"), chemin(self.dossier_id, "galerie"))
        )
        self.documents = composants.obtenir_persistant(
            f"documents_{self.dossier_id}",
            lambda: Documents(emplacement(self.dossier_id, "documents_data"), chemin(self.dossier_id, "documents"))
        )
        self.outils = Outils(
            self.fiche_evenement, self.agenda, self.budget, self.carnet,
            self.liste_invites, self.messagerie, self.carnet_devis, self.jour_j, self.interroger_documents
        )


    def cle_conversation(self, profil):
        identifiant = self.prestataire["id"] if self.prestataire else ""
        return f"conversation_{self.dossier_id}_{profil}_{identifiant}"


    def infos_utiles(self):
        if not self.prestataire:
            return set()

        utiles = set(INFOS_PAR_CATEGORIE.get(self.prestataire["categorie"], set()))

        if not peut_recevoir_sante(self.fiche_evenement.donnees, self.prestataire) and utiles & {"allergies", "invites", "tables"}:
            utiles = (utiles - {"allergies", "invites", "tables"}) | {"couverts"}

        return utiles


    def recharger_donnees(self):
        for cle in [cle for cle in st.session_state if str(cle).startswith(PREFIXES_DONNEES)]:
            del st.session_state[cle]

        self.agenda.charger()
        self.annuaire.charger()


    def nouvelle_conversation(self, profil):
        st.session_state.pop(self.cle_conversation(profil), None)
        st.session_state.briefings = {}


    def appliquer_lien(self):
        self.profil = self.acces.profil

        if self.profil == PRESTATAIRE:
            self.prestataire = self.carnet.trouver(self.acces.prestataire_id)


    def lien_perime(self):
        return not self.dossier_id or (self.acces.profil == PRESTATAIRE and not self.carnet.trouver(self.acces.prestataire_id))


    def interroger_documents(self, question):
        if not self.documents.documents:
            raise ValueError("Aucun document dans ce dossier. Ajoutez-en dans Prestataires › Documents.")

        return ouvrir_rag().interroger(question, self.dossier_id)


    def infos_pour_destinataire(self, prestataire_id):
        prestataire = self.carnet.trouver(prestataire_id)

        if not prestataire:
            return self.fiche_evenement.infos_sans_historique()

        infos_prestataire = self.fiche_evenement.infos_pour_prestataire(
            avec_sante=peut_recevoir_sante(self.fiche_evenement.donnees, prestataire)
        )

        if st.session_state.get("donner_enveloppe"):
            infos_prestataire["budget_prestation"] = self.budget.prevu_pour(prestataire)

        return infos_prestataire


    def rdvs_visibles(self, rdvs):
        visibles = self.outils.rdvs_visibles()
        return [rdv for rdv in rdvs if rdv in visibles]


    def changer_statut_prestataire(self, prestataire, statut):
        appliquer_statut(self.carnet, self.fiche_evenement, prestataire, statut)


class Vue:
    def __init__(self, ctx):
        self.ctx = ctx
