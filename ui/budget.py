from datetime import date, timedelta

import pandas as pd
import streamlit as st

from config.profils import ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import emplacement
from metier.budget import POSTE_ORGANISATION, Budget
from metier.devis import STATUTS_DEVIS, date_lisible, date_validite, generer_pdf, lignes_valides, totaux
from metier.messages import EMETTEUR_AURORE, destinataire_clients, suggestion
from metier.prestataires import meme_nom
from textes import NOTES_DEVIS, echeance_texte, montant, noms_clients
from ui import composants, design
from ui.commun import COLONNES_DEVIS, CONFIG_COLONNES_DEVIS, FORMAT_DATE, lire_date
from ui.contexte import Vue
from ui.messages import VueMessages


class VueBudget(Vue):
    @staticmethod
    def afficher_alertes_factures(budget):
        for facture in budget.factures_a_payer():
            if facture["jours_restants"] < 0:
                st.error(
                    f"Facture en retard : {facture['libelle']} ({montant(facture['montant'])}) — échéance dépassée le {date_lisible(facture['echeance'])}",
                    icon=":material/error:"
                )
            elif facture["jours_restants"] <= 7:
                st.warning(
                    f"À payer {echeance_texte(facture['jours_restants'])} : {facture['libelle']} ({montant(facture['montant'])}, poste {facture['poste']})",
                    icon=":material/schedule:"
                )


    @staticmethod
    def afficher_budget_postes(budget, budget_total, cle, libelle_poste="prévus", lecture_seule=False):
        total_engage = budget.total_engage()

        if budget_total:
            st.progress(min(total_engage / budget_total, 1.0))
            st.markdown(f"**{montant(total_engage)} engagés** sur un budget de **{montant(budget_total)}**")

        for poste in budget.postes:
            engage = budget.engage_du_poste(poste)
            icone = ":material/warning:" if poste["montant_prevu"] and engage > poste["montant_prevu"] else ":material/check_circle:"

            with st.expander(f"{poste['nom']} — {montant(engage)} / {montant(poste['montant_prevu'])} {libelle_poste}", icon=icone):
                for facture in poste["factures"]:
                    a_payer = f":material/hourglass_top: à payer avant le {date_lisible(facture['echeance'])}"
                    statut = ":green[:material/check_circle:] payée" if facture["payee"] else a_payer
                    st.markdown(f"- {facture['libelle']} : {montant(facture['montant'])} ({statut})")

                    if not facture["payee"] and not lecture_seule and st.button("Marquer payée", key=f"{cle}_payee_{poste['nom']}_{facture['libelle']}"):
                            budget.marquer_payee(poste["nom"], facture["libelle"])
                            st.rerun()


    @staticmethod
    def afficher_budget_forms(budget, cle, exemple_poste="traiteur", exemple_facture="acompte traiteur"):
        with st.expander("Ajouter un poste", icon=":material/add:"):
            with st.form(f"{cle}_form_poste", clear_on_submit=True):
                nom = st.text_input(f"Nom du poste (ex : {exemple_poste})")
                montant = st.number_input("Montant prévu (€)", min_value=0, step=100)

                if st.form_submit_button("Ajouter le poste") and nom:
                    budget.ajouter_poste(nom, montant)
                    st.rerun()

        with st.expander("Ajouter une facture", icon=":material/receipt_long:"):
            if budget.postes:
                with st.form(f"{cle}_form_facture", clear_on_submit=True):
                    noms_postes = [poste["nom"] for poste in budget.postes]
                    poste_choisi = st.selectbox("Poste", noms_postes)
                    libelle = st.text_input(f"Libellé (ex : {exemple_facture})")
                    montant = st.number_input("Montant (€)", min_value=0, step=50)
                    echeance = st.date_input("Date d'échéance", format=FORMAT_DATE)
                    payee = st.checkbox("Déjà payée")

                    if st.form_submit_button("Ajouter la facture") and libelle:
                        budget.ajouter_facture(poste_choisi, libelle, montant, str(echeance), payee)
                        st.rerun()
            else:
                st.caption("Ajoute d'abord un poste.")


    def afficher_achats(self):
        identifiant = self.ctx.prestataire["id"]
        achats = composants.obtenir_persistant(
            f"achats_{self.ctx.dossier_id}_{identifiant}", lambda: Budget(emplacement(self.ctx.dossier_id, f"achats_{identifiant}"))
        )
        st.caption("Vos achats pour cet événement (denrées, boissons, location…) et les factures de vos fournisseurs, avec leurs échéances.")
        self.afficher_alertes_factures(achats)
        self.afficher_budget_postes(achats, None, "achats", "budgétés")
        self.afficher_budget_forms(achats, "achats", "viandes et poissons", "facture grossiste")


    def afficher_budget(self):
        self.afficher_alertes_factures(self.ctx.budget)

        if not self.ctx.budget.postes:
            design.vide("Aucun poste de budget pour l'instant.")

            if self.ctx.fiche_evenement.donnees["budget"] and st.button("Proposer une répartition adaptée à mon événement", icon=":material/lightbulb:"):
                    postes = self.ctx.agent.suggerer_budget_postes(self.ctx.fiche_evenement.donnees)

                    for poste in postes:
                        self.ctx.budget.ajouter_poste(poste["nom"], poste["montant_prevu"])

                    st.rerun()
        else:
            self.afficher_budget_postes(self.ctx.budget, self.ctx.fiche_evenement.donnees["budget"], "budget")

        self.afficher_budget_forms(self.ctx.budget, "budget")


    def nouvelles_lignes_devis(self, lignes):
        st.session_state.lignes_devis = lignes
        st.session_state.version_lignes += 1


    def accepter_devis(self, devis, montants):
        prestataire = self.ctx.carnet.trouver(devis["prestataire_id"])
        poste = (prestataire["poste_budget"] or prestataire["categorie"]) if prestataire else POSTE_ORGANISATION
        echeance_solde = lire_date(self.ctx.fiche_evenement.donnees["date"]) or date.today() + timedelta(days=30)
        self.ctx.budget.enregistrer_devis(devis["numero"], montants, poste, echeance_solde)

        if prestataire:
            self.ctx.changer_statut_prestataire(prestataire, "Réservé")


    def afficher_devis_form(self, deja_des_devis):
        if self.ctx.prestataire:
            emetteurs = {self.ctx.prestataire["nom"]: self.ctx.prestataire}
        else:
            emetteurs = {EMETTEUR_AURORE: None} | {prestataire["nom"]: prestataire for prestataire in self.ctx.carnet.prestataires}

        with st.expander("Nouveau devis", icon=":material/add:", expanded=not deja_des_devis):
            emetteur = st.selectbox("Émis par", list(emetteurs), disabled=bool(self.ctx.prestataire))
            prestataire = emetteurs[emetteur]

            if st.button("Proposer les lignes avec AURORE", icon=":material/auto_awesome:"):
                categorie = prestataire["categorie"] if prestataire else "Organisation d'événements"
                fiche = self.ctx.fiche_evenement
                infos = self.ctx.infos_pour_destinataire(self.ctx.prestataire["id"]) if self.ctx.prestataire else fiche.infos_sans_historique()

                with st.spinner("AURORE prépare les lignes du devis…"):
                    suggestions = self.ctx.agent.suggerer_devis_lignes(emetteur, categorie, infos)

                self.nouvelles_lignes_devis(lignes_valides(suggestions))

            tableau = st.data_editor(
                pd.DataFrame(st.session_state.lignes_devis, columns=COLONNES_DEVIS),
                column_config=CONFIG_COLONNES_DEVIS,
                num_rows="dynamic",
                width="stretch",
                key=f"lignes_devis_{st.session_state.version_lignes}"
            )

            gauche, milieu, droite = st.columns(3)
            tva = gauche.number_input("TVA (%)", min_value=0.0, value=20.0, step=0.5)
            acompte = milieu.number_input("Acompte (%)", min_value=0, max_value=100, value=30, step=5)
            validite = droite.number_input("Validité (jours)", min_value=1, value=30)
            notes = st.text_area("Conditions / notes", value=NOTES_DEVIS)

            if st.button("Créer le devis", icon=":material/description:"):
                lignes = lignes_valides(tableau.to_dict("records"))

                if not lignes:
                    st.warning("Ajoute au moins une ligne avec une désignation.")
                else:
                    self.ctx.carnet_devis.ajouter_devis(
                        emetteur,
                        prestataire["id"] if prestataire else None,
                        noms_clients(self.ctx.fiche_evenement.donnees),
                        lignes, tva, acompte, validite, notes
                    )
                    self.nouvelles_lignes_devis([])
                    st.rerun()


    def afficher_devis_carte(self, devis, profil):
        montants = totaux(devis)
        numero = devis["numero"]

        with st.container(border=True):
            infos, statut = st.columns([3, 2])
            infos.markdown(f"**{numero}** · {devis['emetteur']} → {devis['destinataire']}")
            infos.caption(
                f"{montant(montants['ttc'])} TTC · acompte {montant(montants['acompte'])} · "
                f"valable jusqu'au {date_validite(devis):%d/%m/%Y}"
            )

            nouveau_statut = statut.selectbox(
                "Statut",
                STATUTS_DEVIS,
                index=STATUTS_DEVIS.index(devis["statut"]),
                key=f"statut_devis_{numero}_{devis['statut']}",
                label_visibility="collapsed",
                disabled=profil == PRESTATAIRE
            )

            if nouveau_statut != devis["statut"]:
                self.ctx.carnet_devis.changer_statut(numero, nouveau_statut)

                if nouveau_statut == "Accepté":
                    self.accepter_devis(devis, montants)

                st.rerun()

            with st.expander("Voir le détail"):
                st.dataframe(pd.DataFrame(devis["lignes"]), column_config=CONFIG_COLONNES_DEVIS, hide_index=True, width="stretch")

            bouton_pdf, bouton_envoi, bouton_supprimer = st.columns([2, 3, 1])
            bouton_pdf.download_button(
                "Télécharger le PDF", icon=":material/download:",
                data=generer_pdf(devis, self.ctx.fiche_evenement.donnees),
                file_name=f"{numero}.pdf",
                mime="application/pdf",
                key=f"pdf_{numero}",
                width="stretch"
            )

            if profil != ORGANISATEUR:
                return

            if bouton_envoi.button("Préparer le message d'envoi", icon=":material/mail:", key=f"envoi_{numero}", width="stretch"):
                contexte = {**devis, "totaux": montants}
                destinataire = destinataire_clients(self.ctx.fiche_evenement.donnees)
                VueMessages(self.ctx).rediger(suggestion(f"envoi_devis_{numero}", "envoi_devis", destinataire, contexte))

            if bouton_supprimer.button("Supprimer", key=f"suppr_devis_{numero}"):
                self.ctx.carnet_devis.supprimer(numero)
                st.rerun()


    def afficher_devis(self, profil):
        devis_visibles = [
            devis for devis in self.ctx.carnet_devis.devis
            if not self.ctx.prestataire or meme_nom(devis["emetteur"], self.ctx.prestataire["nom"])
        ]

        if not devis_visibles:
            design.vide("Aucun devis pour l'instant.")

        for devis in reversed(devis_visibles):
            self.afficher_devis_carte(devis, profil)

        if profil == ORGANISATEUR:
            self.afficher_devis_form(bool(devis_visibles))
