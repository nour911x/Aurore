import streamlit as st
from groq import APIError

from config.evenements import CHAMPS_ESSENTIELS, libelle_evenement
from config.profils import ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import libelle_court
from llm.agent import PROFILS
from metier.messages import MODIFIABLES, detecter_messages
from textes import (
    CHAMPS_DOSSIER_PRESTATAIRE,
    ERREUR_LIEN,
    LIBELLES_PROFIL,
    LIBELLES_SECTIONS,
    ONGLETS,
    message_erreur,
    pluriel,
)
from ui.accueil import VueAccueil
from ui.budget import VueBudget
from ui.commun import (
    ESPACES,
    PROFILS_ACTIFS,
    SECTIONS,
    SECTIONS_ACTIVES,
    afficher_tuiles,
    details_dossier,
    nouveau_dossier,
    ouvrir_messages,
    ouvrir_nouveau_dossier,
)
from ui.connexion import VueConnexion
from ui.contexte import Vue
from ui.discussion import VueDiscussion
from ui.documents import VueDocuments
from ui.fiche import VueFiche
from ui.habillage import accueil_html, dossier_html, marque_html, particules_html, theme_html
from ui.inspiration import VueInspiration
from ui.invites import VueInvites
from ui.messages import VueMessages
from ui.planning import VuePlanning
from ui.prestataires import VuePrestataires
from ui.vues_partagees import VuesPartagees


class InterfaceUtilisateur(Vue):
    def details_pour_prestataire(self, donnees):
        masques = {"allergies_interdits": "allergies", "preferences_musicales": "musique"}
        return {
            cle: libelle for cle, libelle in details_dossier(donnees, prive=False).items()
            if masques.get(cle, "toujours") in self.ctx.infos_utiles() | {"toujours"}
        }


    def afficher_choix_dossier(self):
        identifiants = list(self.ctx.dossiers)
        choix = st.selectbox(
            "Dossier", identifiants, index=identifiants.index(self.ctx.dossier_id), label_visibility="collapsed",
            format_func=lambda dossier_id: libelle_court(self.ctx.dossiers[dossier_id])
        )

        if choix != self.ctx.dossier_id:
            st.session_state.dossier_actif = choix
            st.rerun()

        st.button("Nouveau dossier", icon=":material/create_new_folder:", width="stretch", on_click=ouvrir_nouveau_dossier)


    def afficher_fiche_evenement(self, profil):
        donnees = self.ctx.fiche_evenement.donnees
        affichage = {**donnees, "type_evenement": libelle_evenement(donnees)}

        with st.sidebar:
            if profil == ORGANISATEUR:
                self.afficher_choix_dossier()

            if not self.ctx.acces.par_lien:
                VueConnexion(self.ctx).afficher_deconnexion()

            if profil == PRESTATAIRE:
                st.markdown(dossier_html(affichage, CHAMPS_DOSSIER_PRESTATAIRE, self.details_pour_prestataire(donnees)), unsafe_allow_html=True)
            else:
                st.markdown(dossier_html(affichage, CHAMPS_ESSENTIELS, details_dossier(donnees)), unsafe_allow_html=True)
                nombre_echanges = len(self.ctx.fiche_evenement.donnees["historique"])

                if nombre_echanges:
                    st.caption(f":material/history: {pluriel(nombre_echanges, 'échange')} dans l'historique")


    def afficher_notification(self, profil, suggestions):
        a_preparer = len(suggestions)
        a_valider = len(self.ctx.messagerie.par_statut(*MODIFIABLES))
        a_envoyer = len(self.ctx.messagerie.par_statut("validé"))
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
            self.ctx.profil = st.segmented_control(
                "Je suis…", [nom for nom in PROFILS if PROFILS_ACTIFS.get(nom, True)], default=ORGANISATEUR, key="profil", format_func=LIBELLES_PROFIL.get,
                bind="query-params", required=True, label_visibility="collapsed"
            )

            if self.ctx.profil == PRESTATAIRE and self.ctx.carnet.prestataires:
                nom = st.selectbox(
                    "Prestataire", [prestataire["nom"] for prestataire in self.ctx.carnet.prestataires],
                    key="prestataire_actif", label_visibility="collapsed", width=220
                )
                self.ctx.prestataire = self.ctx.carnet.trouver_par_nom(nom)


    def afficher_barre_haut(self):
        with st.container(horizontal=True, key="barre-haut"):
            st.markdown(marque_html(self.ctx.fiche_evenement.donnees), unsafe_allow_html=True)

            if not self.ctx.acces.par_lien:
                self.choisir_vue()

        profil = self.ctx.profil
        self.ctx.preparer_conversation()
        st.html(theme_html(profil))
        st.markdown(particules_html(self.ctx.fiche_evenement.donnees["type_evenement"]), unsafe_allow_html=True)

        return profil


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
        if self.ctx.acces.par_lien:
            if self.ctx.lien_perime():
                st.error(ERREUR_LIEN, icon=":material/link_off:")
                return

            self.ctx.appliquer_lien()

        if not self.ctx.dossier_id:
            self.afficher_premier_dossier()
            self.ouvrir_dialogue_si_demande()
            return

        profil = self.afficher_barre_haut()

        if profil == PRESTATAIRE and not self.ctx.prestataire:
            st.info("Aucun prestataire dans le carnet : ajoutez-en depuis l'espace Organisateur (onglet Prestataires).")
            self.afficher_fiche_evenement(profil)
            return

        VueDiscussion(self.ctx).traiter_message(profil)
        VueDiscussion(self.ctx).afficher_message_echoue(profil)
        suggestions = self.ctx.messagerie.a_preparer(
            detecter_messages(self.ctx.fiche_evenement.donnees, self.ctx.carnet, self.ctx.agenda, self.ctx.budget)
        )

        if profil == ORGANISATEUR and st.session_state.get(f"onglets_{profil}", ONGLETS["accueil"]) != ONGLETS["accueil"]:
            self.afficher_notification(profil, suggestions)

        self.afficher_onglets(profil, {
            "accueil": VueAccueil(self.ctx).afficher_tableau_de_bord,
            "recap": VuesPartagees(self.ctx).afficher_recap_client,
            "budget_client": VuesPartagees(self.ctx).afficher_budget_client,
            "invitations": VuesPartagees(self.ctx).afficher_invitations,
            "agenda_prestataire": VuesPartagees(self.ctx).afficher_agenda_prestataire,
            "devis_prestataire": lambda: VuesPartagees(self.ctx).afficher_devis_prestataire(profil),
            "discussion": lambda: VueDiscussion(self.ctx).afficher_discussion(profil),
            "a_envoyer": lambda: VueMessages(self.ctx).afficher_messages(suggestions),
            "fiche": VueFiche(self.ctx).afficher_fiche_client,
            "evenement": VuesPartagees(self.ctx).afficher_evenement,
            "invites": VueInvites(self.ctx).afficher_invites,
            "prestataires": VuePrestataires(self.ctx).afficher_prestataires,
            "documents": VueDocuments(self.ctx).afficher_documents,
            "budget": VueBudget(self.ctx).afficher_budget,
            "devis": lambda: VueBudget(self.ctx).afficher_devis(profil),
            "agenda": VuePlanning(self.ctx).afficher_agenda,
            "deroule": VuePlanning(self.ctx).afficher_deroule,
            "plan_salle": VuePlanning(self.ctx).afficher_plan_salle,
            "salle_3d": VuePlanning(self.ctx).afficher_salle_3d,
            "moodboard": VueInspiration(self.ctx).afficher_moodboard,
            "adresses": VueInspiration(self.ctx).afficher_adresses,
            "photos": VueInspiration(self.ctx).afficher_photos,
            "droit_image": lambda: VueInspiration(self.ctx).afficher_droit_image(profil),
            "avis": lambda: VueInspiration(self.ctx).afficher_avis(profil),
            "instagram": VueInspiration(self.ctx).afficher_instagram
        })

        self.afficher_fiche_evenement(profil)
        self.ouvrir_dialogue_si_demande()
