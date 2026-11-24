import streamlit as st
from groq import APIError

from config.evenements import CHAMPS_ESSENTIELS, libelle_evenement
from config.profils import ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import libelle_court
from llm.agent import PROFILS
from metier.devis import date_lisible
from metier.messages import MODIFIABLES, detecter_messages
from textes import (
    ACCUEILS,
    CHAMPS_DOSSIER_PRESTATAIRE,
    ERREUR_LIEN,
    LIBELLES_PROFIL,
    LIBELLES_SECTIONS,
    ONGLETS,
    PAGES_SANS_DOSSIER,
    message_erreur,
    noms_courts,
    pluriel,
)
from ui import design
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
    ouvrir_onglet,
)
from ui.connexion import VueConnexion
from ui.contexte import Vue
from ui.design import icone, sans_icone
from ui.discussion import VueDiscussion
from ui.documents import VueDocuments
from ui.fiche import VueFiche
from ui.habillage import compte_a_rebours, details_dossier_html, jours_restants, nom_organisateur, salutation
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

        with st.container(key="menu-dossier"):
            choix = st.selectbox(
                "Dossier", identifiants, index=identifiants.index(self.ctx.dossier_id), label_visibility="collapsed",
                format_func=lambda dossier_id: libelle_court(self.ctx.dossiers[dossier_id])
            )

        if choix != self.ctx.dossier_id:
            st.session_state.dossier_actif = choix
            st.rerun()


    def choisir_vue(self):
        self.ctx.profil = st.segmented_control(
            "Vue", [nom for nom in PROFILS if PROFILS_ACTIFS.get(nom, True)], default=ORGANISATEUR, key="profil", format_func=LIBELLES_PROFIL.get,
            bind="query-params", required=True, label_visibility="collapsed"
        )

        if self.ctx.profil == PRESTATAIRE and self.ctx.carnet.prestataires:
            nom = st.selectbox(
                "Prestataire", [prestataire["nom"] for prestataire in self.ctx.carnet.prestataires],
                key="prestataire_actif", label_visibility="collapsed"
            )
            self.ctx.prestataire = self.ctx.carnet.trouver_par_nom(nom)


    def page_ouverte(self):
        libelles = {ONGLETS[onglet]: onglet for onglet in ESPACES[self.ctx.profil]}
        return libelles.get(st.session_state.get(f"onglets_{self.ctx.profil}"), ESPACES[self.ctx.profil][0])


    def compteur_menu(self, onglet):
        if onglet != "messages":
            return ""

        a_valider = len(self.ctx.messagerie.par_statut(*MODIFIABLES))
        return f" `{a_valider}`" if a_valider else ""


    def afficher_navigation(self):
        ouverte = self.page_ouverte()

        for onglet in ESPACES[self.ctx.profil]:
            st.button(
                sans_icone(ONGLETS[onglet]) + self.compteur_menu(onglet), icon=icone(ONGLETS[onglet]), key=f"menu_{onglet}", width="stretch",
                type="primary" if onglet == ouverte else "secondary",
                on_click=ouvrir_onglet, args=(self.ctx.profil, onglet)
            )


    def afficher_menu(self):
        with st.sidebar:
            design.afficher_html(design.logo_html())
            dossier = st.container()
            navigation = st.container(key="menu-navigation")

            nouveau = st.container(key="menu-nouveau")

            if not self.ctx.acces.par_lien:
                with st.container(key="menu-bas"):
                    if nom_organisateur():
                        design.profil(nom_organisateur(), LIBELLES_PROFIL[ORGANISATEUR])

                    self.choisir_vue()
                    VueConnexion(self.ctx).afficher_deconnexion()

            if self.ctx.profil == ORGANISATEUR:
                with dossier:
                    self.afficher_choix_dossier()

                nouveau.button("Nouveau dossier", icon=":material/add:", width="stretch", on_click=ouvrir_nouveau_dossier)

            with navigation:
                self.afficher_navigation()


    def afficher_entete_dossier(self):
        donnees = self.ctx.fiche_evenement.donnees
        profil = self.ctx.profil
        invites = donnees["nombre_invites"]
        design.entete_dossier(
            noms_courts(donnees["noms"]) or "Dossier sans nom",
            [date_lisible(donnees["date"]), libelle_evenement(donnees), donnees["lieu"], pluriel(invites, "invité") if invites else ""],
            compte_a_rebours(jours_restants(donnees["date"]))
        )
        affichage = {**donnees, "type_evenement": libelle_evenement(donnees)}

        with st.expander("Récapitulatif du dossier"):
            if profil == PRESTATAIRE:
                design.afficher_html(details_dossier_html(affichage, CHAMPS_DOSSIER_PRESTATAIRE, self.details_pour_prestataire(donnees)))
            else:
                design.afficher_html(details_dossier_html(affichage, CHAMPS_ESSENTIELS, details_dossier(donnees)))
                nombre_echanges = len(donnees["historique"])

                if nombre_echanges:
                    st.caption(f"{pluriel(nombre_echanges, 'échange')} dans l'historique")


    def afficher_notification(self, suggestions):
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
            st.markdown(", ".join(filter(None, morceaux)))
            design.lien_action("Voir dans Messages", "voir-messages", ouvrir_messages, (self.ctx.profil,))


    @staticmethod
    def afficher_section(afficheur):
        try:
            afficheur()
        except APIError as erreur:
            st.error(message_erreur(erreur), icon=":material/cloud_off:")


    @staticmethod
    def sections(onglet):
        return [section for section in SECTIONS.get(onglet, [onglet]) if SECTIONS_ACTIVES.get(section, True)]


    def afficher_page(self, afficheurs):
        profil, onglet = self.ctx.profil, self.page_ouverte()
        sections = self.sections(onglet)

        if len(sections) == 1:
            self.afficher_section(afficheurs[sections[0]])
            return

        panneaux = st.tabs(
            [sans_icone(LIBELLES_SECTIONS[section]) for section in sections],
            key=f"sections_{profil}_{onglet}", on_change="rerun"
        )

        for section, panneau in zip(sections, panneaux, strict=True):
            if panneau.open:
                with panneau:
                    self.afficher_section(afficheurs[section])


    @staticmethod
    def ouvrir_dialogue_si_demande():
        if st.session_state.get("ouvrir_nouveau_dossier"):
            nouveau_dossier()


    def afficher_premier_dossier(self):
        titre, intro = ACCUEILS[ORGANISATEUR]
        design.afficher_html(design.logo_html())
        design.grand_titre(titre, salutation(), intro)
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

        self.afficher_menu()
        profil = self.ctx.profil

        if profil == PRESTATAIRE and not self.ctx.prestataire:
            design.vide("Aucun prestataire dans le carnet : ajoutez-en depuis l'espace Organisateur (onglet Prestataires).")
            return

        self.ctx.preparer_conversation()

        page = st.container(key="page")

        with st.container(key="saisie"):
            VueDiscussion(self.ctx).traiter_message(profil)

        with page:
            VueDiscussion(self.ctx).afficher_message_echoue(profil)
            suggestions = self.ctx.messagerie.a_preparer(
                detecter_messages(self.ctx.fiche_evenement.donnees, self.ctx.carnet, self.ctx.agenda, self.ctx.budget)
            )

            if self.page_ouverte() not in PAGES_SANS_DOSSIER:
                self.afficher_entete_dossier()

                if profil == ORGANISATEUR and self.page_ouverte() != "messages":
                    self.afficher_notification(suggestions)

            self.afficher_page({
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

        self.ouvrir_dialogue_si_demande()
