import uuid

import pandas as pd
import streamlit as st

from metier.invites import GROUPES, STATUTS_INVITE, generer_faire_part_pdf, lire_contacts, message_personnel, nettoyer
from metier.messages import destinataire_prestataire, suggestion
from metier.rgpd import CATEGORIE_DONNEES_SANTE, recap_sans_sante, sante_partageable
from textes import pluriel
from ui.commun import COLONNES_INVITES, CONFIG_COLONNES_INVITES, ICONES_INVITE


class VueInvites:
    def apres_modif_invites(self):
        st.session_state.version_invites += 1
        st.rerun()


    def show_compteurs_invites(self):
        compteurs = self.liste_invites.compter_par_statut()
        self.show_compteurs(
            {f"{ICONES_INVITE[statut]} {statut}": compteurs[statut] for statut in STATUTS_INVITE}
            | {":material/groups: Personnes attendues": self.liste_invites.personnes(["Invité", "Confirmé"])}
        )


    def show_import_contacts(self):
        with st.expander("Importer des contacts (.vcf ou .csv)", icon=":material/contacts:"):
            st.caption(
                "Depuis votre téléphone ou Google Contacts : Exporter → fichier .vcf ou .csv. "
                "Rien n'est importé sans votre confirmation : seuls le nom, le téléphone et l'email sont repris."
            )
            fichier = st.file_uploader("Fichier de contacts", type=["vcf", "csv"])

            if not fichier:
                return

            contacts = lire_contacts(fichier.name, fichier.getvalue())
            nouveaux = self.liste_invites.a_importer(contacts)
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
                importes = self.liste_invites.importer(contacts, groupe)
                st.session_state.message_import = f"{pluriel(importes, 'contact importé', 'contacts importés')} dans le groupe {groupe}."
                self.apres_modif_invites()

        if "message_import" in st.session_state:
            st.success(st.session_state.pop("message_import"), icon=":material/check_circle:")


    def show_table_invites(self):
        st.caption("Modifie directement le tableau. Ajoute une ligne tout en bas, supprime en cochant à gauche.")
        self.editer_tableau(
            "invites", self.liste_invites.invites, COLONNES_INVITES, CONFIG_COLONNES_INVITES,
            nettoyer, self.liste_invites.remplacer
        )


    def show_redaction_faire_part(self):
        if st.button("Rédiger le faire-part avec AURORE", icon=":material/auto_awesome:"):
            with st.spinner("AURORE écrit votre faire-part…"):
                self.liste_invites.set_faire_part(
                    self.conversation_agent_object.write_faire_part(self.event_sheet.infos_sans_historique())
                )

        valide = self.liste_invites.faire_part_valide
        faire_part = st.text_area("Texte du faire-part", value=self.liste_invites.faire_part, height=200, disabled=valide)

        if faire_part != self.liste_invites.faire_part:
            self.liste_invites.set_faire_part(faire_part)

        if faire_part and valide:
            st.markdown(":green[:material/task_alt: Texte validé, prêt à être envoyé]")
            st.button("Modifier le texte", icon=":material/edit:", on_click=self.liste_invites.valider_faire_part, args=(False,))
        elif faire_part:
            st.button("Valider le texte", icon=":material/task_alt:", type="primary", on_click=self.liste_invites.valider_faire_part)

        if faire_part:
            st.download_button(
                "Télécharger le faire-part (PDF)", icon=":material/download:",
                data=generer_faire_part_pdf(faire_part, self.event_sheet.data),
                file_name="faire-part.pdf",
                mime="application/pdf"
            )


    def show_envoi_faire_parts(self):
        st.subheader(":material/send: Envoyer les faire-parts")

        if not self.liste_invites.faire_part_valide:
            st.info("Rédigez puis validez le texte du faire-part ci-dessus avant de l'envoyer.")
            return

        groupes = st.multiselect("Envoyer à", GROUPES, default=GROUPES)
        selection = [
            invite for invite in self.liste_invites.invites
            if invite["statut"] == "À inviter" and invite["groupe"] in groupes
        ]
        st.caption(f"{pluriel(len(selection), "invité n'a", "invités n'ont")} pas encore reçu le faire-part.")

        for invite in selection:
            with st.container(border=True):
                st.markdown(f"**{invite['nom']}** · {invite['groupe']}")

                if invite["telephone"] or invite["email"]:
                    self.show_boutons_contact(
                        invite["telephone"], invite["email"],
                        message=message_personnel(invite, self.liste_invites.faire_part), sujet="Faire-part"
                    )
                else:
                    st.caption("Pas de téléphone ni d'email : ajoute-les dans la liste.")

                if st.button("Marquer comme invité", icon=":material/check_circle:", key=f"invite_{invite['id']}"):
                    self.liste_invites.changer_statut(invite["id"], "Invité")
                    self.apres_modif_invites()


    def show_recap_traiteur(self):
        recap = self.show_recap_invites()
        traiteurs = {prestataire["nom"]: prestataire for prestataire in self.carnet.prestataires if prestataire["categorie"] == CATEGORIE_DONNEES_SANTE}

        if not sante_partageable(self.event_sheet.data):
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
            self.rediger(suggestion(cle, "recap_traiteur", destinataire_prestataire(traiteur), recap))


    def show_recap_invites(self):
        recap = self.liste_invites.recap_traiteur()
        self.show_compteurs({
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


    def show_invites(self):
        liste_tab, faire_part_tab, traiteur_tab = st.tabs([":material/assignment: Liste", ":material/mail: Faire-parts", ":material/restaurant: Pour le traiteur"])

        with liste_tab:
            if self.liste_invites.invites:
                self.show_compteurs_invites()

            self.show_import_contacts()
            self.show_table_invites()

        with faire_part_tab:
            self.show_redaction_faire_part()
            self.show_envoi_faire_parts()

        with traiteur_tab:
            self.show_recap_traiteur()
