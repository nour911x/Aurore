import base64

import streamlit as st
from groq import APIError

from config.profils import ORGANISATEUR
from textes import (
    ERREUR_FICHE,
    RACCOURCIS_CLIENTS,
    RACCOURCIS_PRESTATAIRE,
    TEXTES_INDICATIFS,
    message_erreur,
)
from ui import composants
from ui.contexte import Vue
from ui.habillage import AVERTISSEMENT_HTML, accueil_html


class VueDiscussion(Vue):
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
                transcription = self.ctx.agent.transcrire(saisie.audio.getvalue())

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
                "conversation": self.ctx.cle_conversation(profil), "demande": demande, "image": image, "erreur": message_erreur(erreur)
            }


    def envoyer_message(self, profil, demande, image):
        st.session_state.pop("message_echoue", None)

        with st.spinner("AURORE regarde ta photo…" if image else "AURORE réfléchit…"):
            self.ctx.agent.demander(demande, profil, self.ctx.outils, image)

        st.session_state.version_invites += 1

        if profil == ORGANISATEUR and not self.ctx.outils.documents_lus:
            self.mettre_a_jour_fiche()


    def mettre_a_jour_fiche(self):
        try:
            with st.spinner("AURORE met la fiche à jour…"):
                nouvelles_infos = self.ctx.agent.extraire_infos_evenement(self.ctx.fiche_evenement.infos_sans_historique())
        except APIError:
            st.warning(ERREUR_FICHE, icon=":material/sync_problem:")
            return

        self.ctx.fiche_evenement.mettre_a_jour(nouvelles_infos)


    def afficher_message_echoue(self, profil):
        echec = st.session_state.get("message_echoue")

        if not echec or echec["conversation"] != self.ctx.cle_conversation(profil):
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


    def afficher_accueil(self, profil):
        st.markdown(accueil_html(profil), unsafe_allow_html=True)


    def afficher_conversation(self, messages):
        for message in messages:
            with st.chat_message(message["role"]):
                if message.get("image"):
                    st.image(base64.b64decode(message["image"]), width=280)

                st.markdown(message["content"])
                composants.afficher_sources(message.get("sources"))

        st.markdown(AVERTISSEMENT_HTML, unsafe_allow_html=True)


    def afficher_discussion(self, profil):
        historique = self.ctx.agent.lire_historique()

        if historique:
            st.button(
                "Nouvelle conversation", icon=":material/add_comment:", key="nouvelle_conversation",
                on_click=self.ctx.nouvelle_conversation, args=(profil,)
            )

        if profil != ORGANISATEUR:
            if not historique:
                self.afficher_accueil(profil)

            composants.afficher_boutons_messages("raccourcis", RACCOURCIS_PRESTATAIRE if self.ctx.prestataire else RACCOURCIS_CLIENTS)
        elif not historique:
            st.caption("Aucune discussion pour l'instant : écrivez à AURORE dans la zone de saisie en bas de page.")

        self.afficher_conversation(historique)
