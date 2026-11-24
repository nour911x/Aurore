import uuid

import streamlit as st

from metier.devis import date_lisible
from metier.messages import MODIFIABLES, TYPES_MESSAGE, destinataire_clients, destinataire_prestataire, suggestion
from ui import composants, design
from ui.commun import resume_contexte
from ui.contexte import Vue


class VueMessages(Vue):
    def ecrire(self, message, consigne=""):
        with st.spinner("AURORE rédige le message…"):
            return self.ctx.agent.rediger_message(
                TYPES_MESSAGE[message["type"]],
                message["destinataire"],
                message.get("contexte") or {},
                self.ctx.infos_pour_destinataire(message["prestataire_id"]),
                consigne
            )


    def rediger(self, suggestion_message, consigne=""):
        self.ctx.messagerie.ajouter(suggestion_message, self.ecrire(suggestion_message, consigne))
        st.rerun()


    def reecrire(self, message):
        self.ctx.messagerie.reecrire(message["id"], self.ecrire(message))
        st.rerun()


    def changer_statut_message(self, message, statut):
        self.ctx.messagerie.changer_statut(message["id"], statut)
        st.rerun()


    def marquer_envoye(self, message):
        self.ctx.messagerie.changer_statut(message["id"], "envoyé")
        self.ctx.fiche_evenement.ajouter_echange(
            "Message",
            f"**{TYPES_MESSAGE[message['type']]}** envoyé à {message['destinataire']} :\n\n{message['contenu']}"
        )

        prestataire = self.ctx.carnet.trouver(message["prestataire_id"])

        if message["type"] == "demande_devis" and prestataire:
            self.ctx.changer_statut_prestataire(prestataire, "Devis demandé")

        st.rerun()


    def afficher_suggestions(self, suggestions):
        design.titre_section(":material/notifications: À préparer")

        if not suggestions:
            design.vide("Rien à préparer pour l'instant.")

        for suggestion_message in suggestions:
            with st.container(border=True):
                st.markdown(f"**{TYPES_MESSAGE[suggestion_message['type']]}** → {suggestion_message['destinataire']}")
                st.caption(resume_contexte(suggestion_message["contexte"]))
                bouton_rediger, bouton_ignorer = st.columns([3, 1])

                if bouton_rediger.button("Rédiger avec AURORE", icon=":material/edit:", key=f"rediger_{suggestion_message['cle']}"):
                    self.rediger(suggestion_message)

                if bouton_ignorer.button("Ignorer", key=f"ignorer_{suggestion_message['cle']}"):
                    self.ctx.messagerie.ajouter(suggestion_message, "", "annulé")
                    st.rerun()


    def afficher_a_valider(self):
        design.titre_section(":material/rate_review: À relire et valider")
        st.caption("Rien ne part sans votre validation : relisez, corrigez si besoin, puis validez.")
        messages = self.ctx.messagerie.par_statut(*MODIFIABLES)

        if not messages:
            design.vide("Aucun message à relire.")

        for message in messages:
            with st.container(border=True):
                badge = ":gray[brouillon]" if message["statut"] == "brouillon" else ":orange[à valider]"
                st.markdown(f"**{TYPES_MESSAGE[message['type']]}** → {message['destinataire']} · {badge}")
                contenu = st.text_area(
                    "Message", value=message["contenu"], height=180, label_visibility="collapsed",
                    key=f"contenu_{message['id']}_{hash(message['contenu'])}"
                )

                if contenu != message["contenu"]:
                    self.ctx.messagerie.modifier_contenu(message["id"], contenu)

                principal, reecrire, annuler = st.columns([2, 2, 1])

                if message["statut"] == "brouillon":
                    if principal.button("Prêt à relire", icon=":material/rate_review:", key=f"relire_{message['id']}"):
                        self.changer_statut_message(message, "à valider")
                elif principal.button("Valider", icon=":material/task_alt:", type="primary", key=f"valider_{message['id']}"):
                    self.changer_statut_message(message, "validé")

                if reecrire.button("Réécrire avec AURORE", icon=":material/refresh:", key=f"reecrire_{message['id']}"):
                    self.reecrire(message)

                if annuler.button("Annuler", key=f"annuler_{message['id']}"):
                    self.changer_statut_message(message, "annulé")


    def afficher_valides(self):
        design.titre_section(":material/outbox: Validés, à envoyer")
        messages = self.ctx.messagerie.par_statut("validé")

        if not messages:
            design.vide("Aucun message validé en attente d'envoi.")

        for message in messages:
            type_message = TYPES_MESSAGE[message["type"]]

            with st.container(border=True):
                st.markdown(f"**{type_message}** → {message['destinataire']} · :green[validé]")
                st.markdown(message["contenu"])

                if not (message["telephone"] or message["email"]):
                    st.caption("Pas de téléphone ni d'email pour ce destinataire : copiez le message ou complétez sa fiche.")

                composants.afficher_boutons_contact(message["telephone"], message["email"], message=message["contenu"], sujet=type_message)
                st.caption("Ces boutons ouvrent WhatsApp ou votre messagerie avec le texte prêt : c'est vous qui envoyez.")
                envoye, modifier, annuler = st.columns([2, 2, 1])

                if envoye.button("Marquer comme envoyé", icon=":material/check_circle:", key=f"envoye_{message['id']}"):
                    self.marquer_envoye(message)

                if modifier.button("Modifier", icon=":material/edit:", key=f"modifier_{message['id']}"):
                    self.changer_statut_message(message, "brouillon")

                if annuler.button("Annuler", key=f"annuler_{message['id']}"):
                    self.changer_statut_message(message, "annulé")


    def afficher_message_libre(self):
        destinataires = [destinataire_clients(self.ctx.fiche_evenement.donnees)] + [
            destinataire_prestataire(prestataire) for prestataire in self.ctx.carnet.prestataires
        ]
        par_nom = {destinataire["destinataire"]: destinataire for destinataire in destinataires}

        with st.expander("Écrire un message libre", icon=":material/edit:"):
            with st.form("form_message_libre", clear_on_submit=True):
                choix = st.selectbox("Destinataire", list(par_nom))
                consigne = st.text_area("Que voulez-vous lui dire ?")
                avec_aurore, moi_meme = st.columns(2)
                rediger = avec_aurore.form_submit_button("Rédiger avec AURORE", icon=":material/auto_awesome:")
                ecrire = moi_meme.form_submit_button("Garder mon texte en brouillon", icon=":material/edit_note:")

                if consigne and (rediger or ecrire):
                    nouveau = suggestion(f"libre_{uuid.uuid4().hex[:8]}", "libre", par_nom[choix], {})

                    if rediger:
                        self.rediger(nouveau, f"Ce que le message doit dire : {consigne}")

                    self.ctx.messagerie.ajouter(nouveau, consigne, "brouillon")
                    st.rerun()


    def afficher_historique_messages(self):
        for statut, titre, icone in [("envoyé", "Envoyés", "send"), ("annulé", "Annulés", "cancel")]:
            messages = [message for message in self.ctx.messagerie.par_statut(statut) if message["contenu"]]

            if messages:
                with st.expander(f"{titre} ({len(messages)})", icon=f":material/{icone}:"):
                    for message in reversed(messages):
                        st.markdown(f"**{TYPES_MESSAGE[message['type']]}** → {message['destinataire']} · {date_lisible(message['date'])}")
                        st.caption(message["contenu"])


    def afficher_messages(self, suggestions):
        st.toggle(
            "Indiquer aux prestataires l'enveloppe prévue pour leur poste",
            key="donner_enveloppe",
            help="Désactivé : aucun montant n'est donné, le prestataire propose son prix."
        )
        self.afficher_suggestions(suggestions)
        self.afficher_a_valider()
        self.afficher_valides()
        self.afficher_message_libre()
        self.afficher_historique_messages()
