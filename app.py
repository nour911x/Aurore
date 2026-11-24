import streamlit as st
from groq import APIError

from config.evenements import CHAMPS_ESSENTIELS, libelle_evenement
from config.profils import ORGANISATEUR, PRESTATAIRE
from donnees.demo import demo_au_premier_lancement
from donnees.dossiers import NOM_FICHE, NOM_SELECTION, chemin, emplacement, emplacement_agenda, emplacement_annuaire, libelle_court
from donnees.dossiers import lister as lister_dossiers
from donnees.fiche_evenement import FicheEvenement
from donnees.migration import migrer_json
from llm.agent import PROFILS, AgentConversation
from llm.base import CleGroqManquante
from llm.outils import Outils
from metier.agenda import Agenda
from metier.budget import Budget
from metier.devis import CarnetDevis
from metier.documents import Documents
from metier.galerie import Galerie
from metier.inspiration import Inspiration
from metier.invites import ListeInvites
from metier.jour_j import JourJ
from metier.messages import MODIFIABLES, Messagerie, detecter_messages
from metier.prestataires import Annuaire, Carnet
from metier.rgpd import peut_recevoir_sante
from textes import (
    CHAMPS_DOSSIER_PRESTATAIRE,
    ERREUR_CLE_MANQUANTE,
    ERREUR_FICHE,
    ERREUR_LIEN,
    LIBELLES_PROFIL,
    LIBELLES_SECTIONS,
    ONGLETS,
    TEXTES_INDICATIFS,
    message_erreur,
    pluriel,
)
from ui.accueil import VueAccueil
from ui.budget import VueBudget
from ui.commun import (
    ESPACES,
    INFOS_PAR_CATEGORIE,
    PROFILS_ACTIFS,
    SECTIONS,
    SECTIONS_ACTIVES,
    afficher_tuiles,
    details_dossier,
    nouveau_dossier,
    ouvrir_messages,
    ouvrir_nouveau_dossier,
)
from ui.composants import Composants
from ui.connexion import VueConnexion, identifier
from ui.documents import VueDocuments
from ui.fiche import VueFiche
from ui.habillage import accueil_html, dossier_html, marque_html, particules_html, style_html, theme_html
from ui.inspiration import VueInspiration
from ui.invites import VueInvites
from ui.messages import VueMessages
from ui.planning import VuePlanning
from ui.prestataires import VuePrestataires
from ui.vues_partagees import VuesPartagees


PREFIXES_DONNEES = (
    "fiche_evenement_", "budget_", "carnet_", "messagerie_", "liste_invites_", "inspiration_", "jour_j_", "galerie_", "achats_", "documents_"
)


class InterfaceUtilisateur(
    Composants, VueAccueil, VueFiche, VuePlanning, VueMessages, VuePrestataires, VueDocuments,
    VueConnexion, VueBudget, VueInvites, VueInspiration, VuesPartagees
):
    def __init__(self, acces):
        self.acces = acces
        self.prestataire = None
        self.profil = None
        self.dossier_id = self.choisir_dossier()
        self.agenda = self.obtenir_persistant("agenda", lambda: Agenda(emplacement_agenda()))
        self.annuaire = self.obtenir_persistant("annuaire", lambda: Annuaire(emplacement_annuaire()))
        st.session_state.setdefault("version_galerie", 0)
        st.session_state.setdefault("version_invites", 0)
        st.session_state.setdefault("briefings", {})
        st.session_state.setdefault("lignes_devis", [])
        st.session_state.setdefault("version_lignes", 0)

        if self.dossier_id:
            self.charger_dossier()


    def choisir_dossier(self):
        migrer_json()
        demo_au_premier_lancement()
        self.dossiers = {dossier["id"]: dossier for dossier in lister_dossiers()}

        if self.acces.par_lien:
            return self.acces.dossier_id if self.acces.dossier_id in self.dossiers else None

        if st.session_state.get("dossier_actif") not in self.dossiers:
            st.session_state.dossier_actif = next(iter(self.dossiers), None)

        return st.session_state.dossier_actif


    def obtenir_du_dossier(self, cle, classe, nom):
        return self.obtenir_persistant(f"{cle}_{self.dossier_id}", lambda: classe(emplacement(self.dossier_id, nom)))


    def charger_dossier(self):
        self.agenda.pour_dossier(self.dossier_id)
        self.fiche_evenement = self.obtenir_du_dossier("fiche_evenement", FicheEvenement, NOM_FICHE)
        self.budget = self.obtenir_du_dossier("budget", Budget, "budget_data")
        self.carnet = self.obtenir_persistant(
            f"carnet_{self.dossier_id}", lambda: Carnet(self.annuaire, emplacement(self.dossier_id, NOM_SELECTION))
        )
        self.messagerie = self.obtenir_du_dossier("messagerie", Messagerie, "messages_data")
        self.carnet_devis = self.obtenir_du_dossier("carnet_devis", CarnetDevis, "devis_data")
        self.liste_invites = self.obtenir_du_dossier("liste_invites", ListeInvites, "invites_data")
        self.inspiration = self.obtenir_du_dossier("inspiration", Inspiration, "inspiration_data")
        self.jour_j = self.obtenir_du_dossier("jour_j", JourJ, "jour_j_data")
        self.galerie = self.obtenir_persistant(
            f"galerie_{self.dossier_id}",
            lambda: Galerie(emplacement(self.dossier_id, "galerie_data"), chemin(self.dossier_id, "galerie"))
        )
        self.documents = self.obtenir_persistant(
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


    def details_pour_prestataire(self, donnees):
        masques = {"allergies_interdits": "allergies", "preferences_musicales": "musique"}
        return {
            cle: libelle for cle, libelle in details_dossier(donnees, prive=False).items()
            if masques.get(cle, "toujours") in self.infos_utiles() | {"toujours"}
        }


    def afficher_choix_dossier(self):
        identifiants = list(self.dossiers)
        choix = st.selectbox(
            "Dossier", identifiants, index=identifiants.index(self.dossier_id), label_visibility="collapsed",
            format_func=lambda dossier_id: libelle_court(self.dossiers[dossier_id])
        )

        if choix != self.dossier_id:
            st.session_state.dossier_actif = choix
            st.rerun()

        st.button("Nouveau dossier", icon=":material/create_new_folder:", width="stretch", on_click=ouvrir_nouveau_dossier)


    def afficher_fiche_evenement(self, profil):
        donnees = self.fiche_evenement.donnees
        affichage = {**donnees, "type_evenement": libelle_evenement(donnees)}

        with st.sidebar:
            if profil == ORGANISATEUR:
                self.afficher_choix_dossier()

            if not self.acces.par_lien:
                self.afficher_deconnexion()

            if profil == PRESTATAIRE:
                st.markdown(dossier_html(affichage, CHAMPS_DOSSIER_PRESTATAIRE, self.details_pour_prestataire(donnees)), unsafe_allow_html=True)
            else:
                st.markdown(dossier_html(affichage, CHAMPS_ESSENTIELS, details_dossier(donnees)), unsafe_allow_html=True)
                nombre_echanges = len(self.fiche_evenement.donnees["historique"])

                if nombre_echanges:
                    st.caption(f":material/history: {pluriel(nombre_echanges, 'échange')} dans l'historique")


    def recharger_donnees(self):
        for cle in [cle for cle in st.session_state if str(cle).startswith(PREFIXES_DONNEES)]:
            del st.session_state[cle]

        self.agenda.charger()
        self.annuaire.charger()


    def nouvelle_conversation(self, profil):
        st.session_state.pop(self.cle_conversation(profil), None)
        st.session_state.briefings = {}


    def afficher_notification(self, profil, suggestions):
        a_preparer = len(suggestions)
        a_valider = len(self.messagerie.par_statut(*MODIFIABLES))
        a_envoyer = len(self.messagerie.par_statut("validé"))
        morceaux = [
            pluriel(a_preparer, "message à préparer", "messages à préparer") if a_preparer else "",
            pluriel(a_valider, "message à valider", "messages à valider") if a_valider else "",
            pluriel(a_envoyer, "message validé à envoyer", "messages validés à envoyer") if a_envoyer else ""
        ]

        if not (a_preparer or a_valider or a_envoyer):
            return

        with st.container(horizontal=True, vertical_alignment="center", key="notification"):
            st.markdown(f":material/notifications: **{', '.join(filter(None, morceaux))}**")
            st.button(
                "Voir dans Messages", icon=":material/arrow_forward:", key="voir-messages",
                on_click=ouvrir_messages, args=(profil,)
            )


    def choisir_vue(self):
        with st.container(horizontal=True, key="barre-actions"):
            self.profil = st.segmented_control(
                "Je suis…", [nom for nom in PROFILS if PROFILS_ACTIFS.get(nom, True)], default=ORGANISATEUR, key="profil", format_func=LIBELLES_PROFIL.get,
                bind="query-params", required=True, label_visibility="collapsed"
            )

            if self.profil == PRESTATAIRE and self.carnet.prestataires:
                nom = st.selectbox(
                    "Prestataire", [prestataire["nom"] for prestataire in self.carnet.prestataires],
                    key="prestataire_actif", label_visibility="collapsed", width=220
                )
                self.prestataire = self.carnet.trouver_par_nom(nom)


    def appliquer_lien(self):
        self.profil = self.acces.profil

        if self.profil == PRESTATAIRE:
            self.prestataire = self.carnet.trouver(self.acces.prestataire_id)


    def lien_perime(self):
        return not self.dossier_id or (self.acces.profil == PRESTATAIRE and not self.carnet.trouver(self.acces.prestataire_id))


    def afficher_barre_haut(self):
        with st.container(horizontal=True, key="barre-haut"):
            st.markdown(marque_html(self.fiche_evenement.donnees), unsafe_allow_html=True)

            if not self.acces.par_lien:
                self.choisir_vue()

        profil = self.profil
        self.outils.pour_espace(profil, self.prestataire)
        self.agent = self.obtenir_persistant(self.cle_conversation(profil), AgentConversation)
        st.html(theme_html(profil))
        st.markdown(particules_html(self.fiche_evenement.donnees["type_evenement"]), unsafe_allow_html=True)

        return profil


    def lire_saisie(self, profil):
        saisie = st.chat_input(
            TEXTES_INDICATIFS[profil],
            accept_file=True,
            accept_audio=True,
            file_type=["jpg", "jpeg", "png", "webp"]
            )
        texte = st.session_state.pop("message_en_attente", None)

        if not saisie:
            return texte, None

        texte = saisie.text

        if saisie.audio:
            with st.spinner("AURORE écoute ton message…"):
                transcription = self.agent.transcrire(saisie.audio.getvalue())

            texte = " ".join(filter(None, [texte, transcription]))

        return texte, saisie.files[0].getvalue() if saisie.files else None


    def traiter_message(self, profil):
        demande = image = None

        try:
            demande, image = self.lire_saisie(profil)

            if demande or image:
                self.envoyer_message(profil, demande, image)
        except APIError as erreur:
            st.session_state.message_echoue = {
                "conversation": self.cle_conversation(profil), "demande": demande, "image": image, "erreur": message_erreur(erreur)
            }


    def envoyer_message(self, profil, demande, image):
        st.session_state.pop("message_echoue", None)

        with st.spinner("AURORE regarde ta photo…" if image else "AURORE réfléchit…"):
            self.agent.demander(demande, profil, self.outils, image)

        st.session_state.version_invites += 1

        if profil == ORGANISATEUR and not self.outils.documents_lus:
            self.mettre_a_jour_fiche()


    def mettre_a_jour_fiche(self):
        try:
            with st.spinner("AURORE met la fiche à jour…"):
                nouvelles_infos = self.agent.extraire_infos_evenement(self.fiche_evenement.infos_sans_historique())
        except APIError:
            st.warning(ERREUR_FICHE, icon=":material/sync_problem:")
            return

        self.fiche_evenement.mettre_a_jour(nouvelles_infos)


    def afficher_message_echoue(self, profil):
        echec = st.session_state.get("message_echoue")

        if not echec or echec["conversation"] != self.cle_conversation(profil):
            return

        st.error(echec["erreur"], icon=":material/cloud_off:")

        if not (echec["demande"] or echec["image"]):
            return

        st.markdown(f"Votre message n'a pas été perdu : *{echec['demande'] or 'photo jointe'}*")

        if st.button("Réessayer", icon=":material/refresh:", key="reessayer_message"):
            try:
                self.envoyer_message(profil, echec["demande"], echec["image"])
            except APIError as erreur:
                st.session_state.message_echoue = {**echec, "erreur": message_erreur(erreur)}

            st.rerun()


    @staticmethod
    def afficher_section(afficheur):
        try:
            afficheur()
        except APIError as erreur:
            st.error(message_erreur(erreur), icon=":material/cloud_off:")


    @staticmethod
    def sections(onglet):
        return [section for section in SECTIONS.get(onglet, [onglet]) if SECTIONS_ACTIVES.get(section, True)]


    def afficher_onglets(self, profil, afficheurs):
        onglets = ESPACES[profil]
        panneaux = st.tabs([ONGLETS[onglet] for onglet in onglets], key=f"onglets_{profil}", on_change="rerun")

        for onglet, panneau in zip(onglets, panneaux, strict=True):
            if not panneau.open:
                continue

            with panneau:
                sections = self.sections(onglet)

                if len(sections) == 1:
                    self.afficher_section(afficheurs[sections[0]])
                    continue

                sous_panneaux = st.tabs(
                    [LIBELLES_SECTIONS[section] for section in sections],
                    key=f"sections_{profil}_{onglet}", on_change="rerun"
                )

                for section, sous_panneau in zip(sections, sous_panneaux, strict=True):
                    if sous_panneau.open:
                        with sous_panneau:
                            self.afficher_section(afficheurs[section])


    @staticmethod
    def ouvrir_dialogue_si_demande():
        if st.session_state.get("ouvrir_nouveau_dossier"):
            nouveau_dossier()


    def afficher_premier_dossier(self):
        st.markdown(marque_html({}), unsafe_allow_html=True)
        st.markdown(accueil_html(ORGANISATEUR), unsafe_allow_html=True)
        afficher_tuiles("tuiles", ouvrir_nouveau_dossier)


    def lancer(self):
        if self.acces.par_lien:
            if self.lien_perime():
                st.error(ERREUR_LIEN, icon=":material/link_off:")
                return

            self.appliquer_lien()

        if not self.dossier_id:
            self.afficher_premier_dossier()
            self.ouvrir_dialogue_si_demande()
            return

        profil = self.afficher_barre_haut()

        if profil == PRESTATAIRE and not self.prestataire:
            st.info("Aucun prestataire dans le carnet : ajoutez-en depuis l'espace Organisateur (onglet Prestataires).")
            self.afficher_fiche_evenement(profil)
            return

        self.traiter_message(profil)
        self.afficher_message_echoue(profil)
        suggestions = self.messagerie.a_preparer(
            detecter_messages(self.fiche_evenement.donnees, self.carnet, self.agenda, self.budget)
        )

        if profil == ORGANISATEUR and st.session_state.get(f"onglets_{profil}", ONGLETS["accueil"]) != ONGLETS["accueil"]:
            self.afficher_notification(profil, suggestions)

        self.afficher_onglets(profil, {
            "accueil": self.afficher_tableau_de_bord,
            "recap": self.afficher_recap_client,
            "budget_client": self.afficher_budget_client,
            "invitations": self.afficher_invitations,
            "agenda_prestataire": self.afficher_agenda_prestataire,
            "devis_prestataire": lambda: self.afficher_devis_prestataire(profil),
            "discussion": lambda: self.afficher_discussion(profil),
            "a_envoyer": lambda: self.afficher_messages(suggestions),
            "fiche": self.afficher_fiche_client,
            "evenement": self.afficher_evenement,
            "invites": self.afficher_invites,
            "prestataires": self.afficher_prestataires,
            "documents": self.afficher_documents,
            "budget": self.afficher_budget,
            "devis": lambda: self.afficher_devis(profil),
            "agenda": self.afficher_agenda,
            "deroule": self.afficher_deroule,
            "plan_salle": self.afficher_plan_salle,
            "salle_3d": self.afficher_salle_3d,
            "moodboard": self.afficher_moodboard,
            "adresses": self.afficher_adresses,
            "photos": self.afficher_photos,
            "droit_image": lambda: self.afficher_droit_image(profil),
            "avis": lambda: self.afficher_avis(profil),
            "instagram": self.afficher_instagram
        })

        self.afficher_fiche_evenement(profil)
        self.ouvrir_dialogue_si_demande()


if __name__ == "__main__":
    st.set_page_config(page_title="AURORE", page_icon=":material/wb_twilight:", layout="wide")
    st.html(style_html())
    acces = identifier()

    try:
        if acces:
            InterfaceUtilisateur(acces).lancer()
    except CleGroqManquante:
        st.error(ERREUR_CLE_MANQUANTE, icon=":material/key_off:")
    except APIError as erreur:
        st.error(message_erreur(erreur), icon=":material/cloud_off:")
