import uuid

import pandas as pd
import streamlit as st

from metier.invites import GROUPES, STATUTS_INVITE, generer_faire_part_pdf, lire_contacts, message_personnel, nettoyer
from metier.messages import destinataire_prestataire, suggestion
from metier.rgpd import CATEGORIE_DONNEES_SANTE, recap_sans_sante, sante_partageable
from textes import pluriel
from ui import composants, design
from ui.commun import COLONNES_INVITES, CONFIG_COLONNES_INVITES, ICONES_INVITE
from ui.contexte import Vue
from ui.messages import VueMessages


class VueInvites(Vue):
    def apres_modif_invites(self):
        st.session_state.version_invites += 1
        st.rerun()


    def afficher_compteurs_invites(self):
        compteurs = self.ctx.liste_invites.compter_par_statut()
        design.indicateurs(
            {f"{ICONES_INVITE[statut]} {statut}": compteurs[statut] for statut in STATUTS_INVITE}
            | {":material/groups: Personnes attendues": self.ctx.liste_invites.personnes(["Invité", "Confirmé"])}
        )


    def afficher_import_contacts(self):
        with st.expander("Importer des contacts (.vcf ou .csv)", icon=":material/contacts:"):
            st.caption(
                "Depuis votre téléphone ou Google Contacts : Exporter → fichier .vcf ou .csv. "
                "Rien n'est importé sans votre confirmation : seuls le nom, le téléphone et l'email sont repris."
            )
            fichier = st.file_uploader("Fichier de contacts", type=["vcf", "csv"])

            if not fichier:
                return

            contacts = lire_contacts(fichier.name, fichier.getvalue())
            nouveaux = self.ctx.liste_invites.a_importer(contacts)
            st.markdown(
                f"**{pluriel(len(nouveaux), 'contact à importer', 'contacts à importer')}**"
                + (f" · {pluriel(len(contacts) - len(nouveaux), 'doublon ignoré', 'doublons ignorés')}" if len(contacts) > len(nouveaux) else "")
            )
            st.dataframe(
                pd.DataFrame(nouveaux, columns=["nom", "telephone", "email"]),
                column_config={"nom": "Nom", "telephone": "Téléphone", "email": "Email"},
                hide_index=True, width="stretch"
            )
            groupe = st.selectbox("Groupe à attribuer", GROUPES)

            if nouveaux and st.button(f"Importer {pluriel(len(nouveaux), 'contact')}", icon=":material/person_add:", type="primary"):
                importes = self.ctx.liste_invites.importer(contacts, groupe)
                st.session_state.message_import = f"{pluriel(importes, 'contact importé', 'contacts importés')} dans le groupe {groupe}."
                self.apres_modif_invites()

        if "message_import" in st.session_state:
            st.success(st.session_state.pop("message_import"), icon=":material/check_circle:")


    def afficher_table_invites(self):
        st.caption("Modifie directement le tableau. Ajoute une ligne tout en bas, supprime en cochant à gauche.")
        composants.editer_tableau(
            "invites", self.ctx.liste_invites.invites, COLONNES_INVITES, CONFIG_COLONNES_INVITES,
            nettoyer, self.ctx.liste_invites.remplacer
        )


    def afficher_redaction_faire_part(self):
        if st.button("Rédiger le faire-part avec AURORE", icon=":material/auto_awesome:"):
            with st.spinner("AURORE écrit votre faire-part…"):
                self.ctx.liste_invites.definir_faire_part(
                    self.ctx.agent.rediger_faire_part(self.ctx.fiche_evenement.infos_sans_historique())
                )

        valide = self.ctx.liste_invites.faire_part_valide
        faire_part = st.text_area("Texte du faire-part", value=self.ctx.liste_invites.faire_part, height=200, disabled=valide)

        if faire_part != self.ctx.liste_invites.faire_part:
            self.ctx.liste_invites.definir_faire_part(faire_part)

        if faire_part and valide:
            st.markdown(":green[:material/task_alt: Texte validé, prêt à être envoyé]")
            st.button("Modifier le texte", icon=":material/edit:", on_click=self.ctx.liste_invites.valider_faire_part, args=(False,))
        elif faire_part:
            st.button("Valider le texte", icon=":material/task_alt:", type="primary", on_click=self.ctx.liste_invites.valider_faire_part)

        if faire_part:
            st.download_button(
                "Télécharger le faire-part (PDF)", icon=":material/download:",
                data=generer_faire_part_pdf(faire_part, self.ctx.fiche_evenement.donnees),
                file_name="faire-part.pdf",
                mime="application/pdf"
            )


    def afficher_envoi_faire_parts(self):
        design.titre_section(":material/send: Envoyer les faire-parts")

        if not self.ctx.liste_invites.faire_part_valide:
            st.info("Rédigez puis validez le texte du faire-part ci-dessus avant de l'envoyer.")
            return

        groupes = st.multiselect("Envoyer à", GROUPES, default=GROUPES)
        selection = [
            invite for invite in self.ctx.liste_invites.invites
            if invite["statut"] == "À inviter" and invite["groupe"] in groupes
        ]
        st.caption(f"{pluriel(len(selection), "invité n'a", "invités n'ont")} pas encore reçu le faire-part.")

        for invite in selection:
            with st.container(border=True):
                st.markdown(f"**{invite['nom']}** · {invite['groupe']}")

                if invite["telephone"] or invite["email"]:
                    composants.afficher_boutons_contact(
                        invite["telephone"], invite["email"],
                        message=message_personnel(invite, self.ctx.liste_invites.faire_part), sujet="Faire-part"
                    )
                else:
                    st.caption("Pas de téléphone ni d'email : ajoute-les dans la liste.")

                if st.button("Marquer comme invité", icon=":material/check_circle:", key=f"invite_{invite['id']}"):
                    self.ctx.liste_invites.changer_statut(invite["id"], "Invité")
                    self.apres_modif_invites()


    def afficher_recap_traiteur(self):
        recap = self.afficher_recap_invites()
        traiteurs = {prestataire["nom"]: prestataire for prestataire in self.ctx.carnet.prestataires if prestataire["categorie"] == CATEGORIE_DONNEES_SANTE}

        if not sante_partageable(self.ctx.fiche_evenement.donnees):
            st.warning(
                "Le client n'a pas donné son accord pour partager les allergies et les régimes : "
                "le message au traiteur ne contiendra que le nombre de couverts. Recueillez son accord dans la fiche client.",
                icon=":material/lock:"
            )
            recap = recap_sans_sante(recap)

        if not traiteurs:
            st.caption("Ajoutez le traiteur dans l'onglet Prestataires pour lui envoyer ce récapitulatif.")
            return

        traiteur = traiteurs[st.selectbox("Traiteur", list(traiteurs))]

        if st.button("Préparer le message pour le traiteur", icon=":material/mail:"):
            cle = f"recap_traiteur_{uuid.uuid4().hex[:8]}"
            VueMessages(self.ctx).rediger(suggestion(cle, "recap_traiteur", destinataire_prestataire(traiteur), recap))


    def afficher_recap_invites(self):
        recap = self.ctx.liste_invites.recap_traiteur()
        design.indicateurs({
            ":material/restaurant: Couverts confirmés": recap["couverts_confirmes"],
            "⏳ Couverts attendus": recap["couverts_attendus"]
        })

        if recap["regimes"]:
            st.markdown("**Régimes particuliers (invités confirmés)**")

            for regime, nombre_invites in recap["regimes"].items():
                st.markdown(f"- {regime} : {nombre_invites}")

        if recap["allergies"]:
            st.markdown("**Allergies**")

            for nom, allergies in recap["allergies"].items():
                st.markdown(f"- :orange[:material/warning:] {nom} : {allergies}")

        return recap


    def afficher_invites(self):
        panneau_liste, panneau_faire_part, panneau_traiteur = st.tabs(
            ["Liste", "Faire-parts", "Pour le traiteur"]
        )

        with panneau_liste:
            if self.ctx.liste_invites.invites:
                self.afficher_compteurs_invites()

            self.afficher_import_contacts()
            self.afficher_table_invites()

        with panneau_faire_part:
            self.afficher_redaction_faire_part()
            self.afficher_envoi_faire_parts()

        with panneau_traiteur:
            self.afficher_recap_traiteur()
