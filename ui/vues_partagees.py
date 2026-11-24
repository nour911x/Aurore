from datetime import datetime

import pandas as pd
import streamlit as st

from config.evenements import champs_du_type
from config.profils import CLIENTS
from metier.devis import date_lisible
from metier.jour_j import personnes
from metier.rgpd import CATEGORIE_DONNEES_SANTE, sante_partageable
from textes import date_longue, montant
from ui import composants
from ui.budget import VueBudget
from ui.contexte import Vue
from ui.habillage import accueil_html, frise_html
from ui.invites import VueInvites
from ui.planning import VuePlanning


class VuesPartagees(Vue):
    def afficher_evenement(self):
        infos = self.ctx.infos_pour_destinataire(self.ctx.prestataire["id"])
        utiles = self.ctx.infos_utiles()
        composants.afficher_compteurs({
            ":material/event: Date": date_lisible(infos["date"]) or "À définir",
            ":material/location_on: Lieu": infos["lieu"] or "À définir",
            ":material/groups: Invités prévus": infos["nombre_invites"] or "À définir"
        })

        if self.ctx.prestataire["categorie"] == CATEGORIE_DONNEES_SANTE and not sante_partageable(self.ctx.fiche_evenement.donnees):
            st.info("Les allergies et régimes ne vous sont pas transmis : le client n'a pas encore donné son accord.", icon=":material/lock:")

        for cle, titre, besoin in [
            ("allergies_interdits", ":material/warning: Allergies et interdits", "allergies"),
            ("preferences", ":material/palette: Préférences des clients", None),
            ("preferences_musicales", ":material/music_note: Goûts musicaux", "musique")
        ]:
            if infos.get(cle) and (besoin is None or besoin in utiles):
                st.markdown(f"**{titre}** : {', '.join(infos[cle])}")

        if "invites" in utiles:
            st.subheader(":material/restaurant: Les invités")
            VueInvites(self.ctx).afficher_recap_invites()
        elif "couverts" in utiles:
            recap = self.ctx.liste_invites.recap_traiteur()
            composants.afficher_compteurs({
                ":material/restaurant: Couverts confirmés": recap["couverts_confirmes"],
                ":material/hourglass_top: Couverts attendus": recap["couverts_attendus"]
            })

        if self.ctx.jour_j.salle["tables"] and "tables" in utiles:
            st.subheader(":material/chair: Couverts par table")
            repartition = self.ctx.jour_j.par_table(self.ctx.liste_invites.invites)
            st.dataframe(
                pd.DataFrame([
                    {
                        "Table": table,
                        "Couverts": sum(personnes(invite) for invite in invites),
                        "Régimes": ", ".join(invite["regime"] for invite in invites if invite["regime"] != "Aucun")
                    }
                    for table, invites in repartition.items()
                ]),
                hide_index=True,
                width="stretch"
            )

        if self.ctx.jour_j.deroule:
            st.subheader(":material/schedule: Déroulé du jour J")
            st.caption("Vos créneaux sont mis en avant.")
            st.markdown(frise_html(self.ctx.jour_j.deroule, self.ctx.prestataire["nom"]), unsafe_allow_html=True)


    def afficher_prochains_rdvs(self):
        rdvs = self.ctx.agenda.rdvs_a_venir()

        if not rdvs:
            st.caption("Aucun rendez-vous prévu pour l'instant.")

        for rdv in rdvs:
            debut = datetime.fromisoformat(rdv["date_heure"])
            st.markdown(f"**{date_longue(debut)} à {debut:%H:%M}** · {rdv['titre']} · :gray[{rdv['lieu'] or 'lieu à préciser'}]")


    def afficher_recap_client(self):
        donnees = self.ctx.fiche_evenement.donnees
        st.markdown(accueil_html(CLIENTS), unsafe_allow_html=True)
        composants.afficher_compteurs({
            ":material/event: Date": date_lisible(donnees["date"]) or "À définir",
            ":material/location_on: Lieu": donnees["lieu"] or "À définir",
            ":material/groups: Invités": donnees["nombre_invites"] or "À définir"
        })

        for cle, libelle in champs_du_type(donnees).items():
            valeur = donnees[cle]

            if isinstance(valeur, list):
                valeur = ", ".join(valeur)

            if isinstance(valeur, bool):
                valeur = "Oui" if valeur else "Non"

            if valeur:
                st.markdown(f"**{libelle}** : {date_lisible(valeur) if cle.startswith('date') else valeur}")

        st.subheader(":material/event: Prochains rendez-vous")
        self.afficher_prochains_rdvs()


    def afficher_budget_client(self):
        st.caption("Suivi en lecture seule. Pour toute modification, écrivez à votre organisateur.")
        VueBudget.afficher_alertes_factures(self.ctx.budget)

        if not self.ctx.budget.postes:
            st.info("Le budget n'a pas encore été détaillé.")

        VueBudget.afficher_budget_postes(self.ctx.budget, self.ctx.fiche_evenement.donnees["budget"], "budget_client", lecture_seule=True)


    def afficher_invitations(self):
        if not self.ctx.liste_invites.invites:
            st.info("La liste d'invités n'a pas encore été créée.")
            return

        VueInvites(self.ctx).afficher_compteurs_invites()
        st.dataframe(
            pd.DataFrame(self.ctx.liste_invites.invites, columns=["nom", "groupe", "accompagnants", "statut"]),
            column_config={
                "nom": "Nom", "groupe": "Groupe", "accompagnants": "+ Accomp.", "statut": "Statut"
            },
            hide_index=True,
            width="stretch"
        )

        if self.ctx.liste_invites.faire_part:
            with st.expander("Texte du faire-part", icon=":material/mail:"):
                st.markdown(self.ctx.liste_invites.faire_part)


    def afficher_agenda_prestataire(self):
        VuePlanning(self.ctx).afficher_rappels_rdv()
        VuePlanning(self.ctx).afficher_rdvs(lecture_seule=True)


    def afficher_devis_prestataire(self, profil):
        VueBudget(self.ctx).afficher_devis(profil)
        st.subheader(":material/receipt_long: Factures")
        factures = self.ctx.budget.factures_de(self.ctx.prestataire)

        if not factures:
            st.caption("Aucune facture enregistrée pour votre prestation.")

        for facture in factures:
            statut = ":green[payée]" if facture["payee"] else f":orange[à régler avant le {date_lisible(facture['echeance'])}]"
            st.markdown(f"- {facture['libelle']} : {montant(facture['montant'])} · {statut}")
