import pandas as pd
import streamlit as st
from datetime import date, timedelta

from donnees.dossiers import chemin
from metier.budget import Budget, POSTE_ORGANISATION
from metier.devis import STATUTS_DEVIS, date_lisible, date_validite, generer_pdf, lignes_valides, totaux
from metier.messages import EMETTEUR_AURORE, destinataire_maries, suggestion
from metier.prestataires import meme_nom
from textes import NOTES_DEVIS, echeance_texte, format_person_name, montant, noms_clients
from ui.commun import COLONNES_DEVIS, CONFIG_COLONNES_DEVIS, FORMAT_DATE, lire_date


class VueBudget:
	@staticmethod
	def show_alertes_factures(budget):
		for facture in budget.factures_a_payer():
			if facture["jours_restants"] < 0:
				st.error(f"Facture en retard : {facture['libelle']} ({montant(facture['montant'])}) — échéance dépassée le {date_lisible(facture['echeance'])}", icon=":material/error:")
			elif facture["jours_restants"] <= 7:
				st.warning(f"À payer {echeance_texte(facture['jours_restants'])} : {facture['libelle']} ({montant(facture['montant'])}, poste {facture['poste']})", icon=":material/schedule:")


	@staticmethod
	def show_budget_postes(budget, budget_total, cle, libelle_poste="prévus", lecture_seule=False):
		total_engage = budget.total_engage()

		if budget_total:
			st.progress(min(total_engage / budget_total, 1.0))
			st.markdown(f"**{montant(total_engage)} engagés** sur un budget de **{montant(budget_total)}**")

		for poste in budget.postes:
			engage = budget.engage_du_poste(poste)
			icone = ":material/warning:" if poste["montant_prevu"] and engage > poste["montant_prevu"] else ":material/check_circle:"

			with st.expander(f"{poste['nom']} — {montant(engage)} / {montant(poste['montant_prevu'])} {libelle_poste}", icon=icone):
				for facture in poste["factures"]:
					statut = ":green[:material/check_circle:] payée" if facture["payee"] else f":material/hourglass_top: à payer avant le {date_lisible(facture['echeance'])}"
					st.markdown(f"- {facture['libelle']} : {montant(facture['montant'])} ({statut})")

					if not facture["payee"] and not lecture_seule:
						if st.button("Marquer payée", key=f"{cle}_payee_{poste['nom']}_{facture['libelle']}"):
							budget.marquer_payee(poste["nom"], facture["libelle"])
							st.rerun()


	@staticmethod
	def show_budget_forms(budget, cle, exemple_poste="traiteur", exemple_facture="acompte traiteur"):
		with st.expander("Ajouter un poste", icon=":material/add:"):
			with st.form(f"{cle}_form_poste", clear_on_submit=True):
				nom = st.text_input(f"Nom du poste (ex : {exemple_poste})")
				montant = st.number_input("Montant prévu (€)", min_value=0, step=100)

				if st.form_submit_button("Ajouter le poste") and nom:
					budget.add_poste(nom, montant)
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
						budget.add_facture(poste_choisi, libelle, montant, str(echeance), payee)
						st.rerun()
			else:
				st.caption("Ajoute d'abord un poste.")


	def show_achats(self):
		identifiant = self.prestataire["id"]
		achats = self.get_persistant(
			f"achats_{self.dossier_id}_{identifiant}", lambda: Budget(chemin(self.dossier_id, f"achats_{identifiant}.json"))
		)
		st.caption("Vos achats pour cet événement (denrées, boissons, location…) et les factures de vos fournisseurs, avec leurs échéances.")
		self.show_alertes_factures(achats)
		self.show_budget_postes(achats, None, "achats", "budgétés")
		self.show_budget_forms(achats, "achats", "viandes et poissons", "facture grossiste")


	def show_budget(self):
		self.show_alertes_factures(self.budget)

		if not self.budget.postes:
			st.info("Aucun poste de budget pour l'instant.")

			if self.event_sheet.data["budget"]:
				if st.button("Proposer une répartition adaptée à mon événement", icon=":material/lightbulb:"):
					postes = self.conversation_agent_object.suggest_budget_postes(self.event_sheet.data)

					for poste in postes:
						self.budget.add_poste(poste["nom"], poste["montant_prevu"])

					st.rerun()
		else:
			self.show_budget_postes(self.budget, self.event_sheet.data["budget"], "budget")

		self.show_budget_forms(self.budget, "budget")


	def nouvelles_lignes_devis(self, lignes):
		st.session_state.lignes_devis = lignes
		st.session_state.version_lignes += 1


	def accepter_devis(self, devis, montants):
		prestataire = self.carnet.trouver(devis["prestataire_id"])
		poste = (prestataire["poste_budget"] or prestataire["categorie"]) if prestataire else POSTE_ORGANISATION
		echeance_solde = lire_date(self.event_sheet.data["date"]) or date.today() + timedelta(days=30)
		self.budget.enregistrer_devis(devis["numero"], montants, poste, echeance_solde)

		if prestataire:
			self.changer_statut_prestataire(prestataire, "Réservé")


	def show_devis_form(self, deja_des_devis):
		if self.prestataire:
			emetteurs = {self.prestataire["nom"]: self.prestataire}
		else:
			emetteurs = {EMETTEUR_AURORE: None} | {prestataire["nom"]: prestataire for prestataire in self.carnet.prestataires}

		with st.expander("Nouveau devis", icon=":material/add:", expanded=not deja_des_devis):
			emetteur = st.selectbox("Émis par", list(emetteurs), disabled=bool(self.prestataire))
			prestataire = emetteurs[emetteur]

			if st.button("Proposer les lignes avec AURORE", icon=":material/auto_awesome:"):
				categorie = prestataire["categorie"] if prestataire else "Organisation d'événements"
				infos = self.infos_pour_destinataire(self.prestataire["id"]) if self.prestataire else self.event_sheet.infos_sans_historique()

				with st.spinner("AURORE prépare les lignes du devis…"):
					suggestions = self.conversation_agent_object.suggest_devis_lignes(emetteur, categorie, infos)

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
					self.carnet_devis.add_devis(
						emetteur,
						prestataire["id"] if prestataire else None,
						noms_clients(self.event_sheet.data),
						lignes, tva, acompte, validite, notes
					)
					self.nouvelles_lignes_devis([])
					st.rerun()


	def show_devis_carte(self, devis, profil):
		montants = totaux(devis)
		numero = devis["numero"]

		with st.container(border=True):
			infos, statut = st.columns([3, 2])
			infos.markdown(f"**{numero}** · {devis['emetteur']} → {format_person_name(devis['destinataire'])}")
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
				disabled=profil == "Prestataire"
			)

			if nouveau_statut != devis["statut"]:
				self.carnet_devis.changer_statut(numero, nouveau_statut)

				if nouveau_statut == "Accepté":
					self.accepter_devis(devis, montants)

				st.rerun()

			with st.expander("Voir le détail"):
				st.dataframe(pd.DataFrame(devis["lignes"]), column_config=CONFIG_COLONNES_DEVIS, hide_index=True, width="stretch")

			bouton_pdf, bouton_envoi, bouton_supprimer = st.columns([2, 3, 1])
			bouton_pdf.download_button(
				"Télécharger le PDF", icon=":material/download:",
				data=generer_pdf(devis, self.event_sheet.data),
				file_name=f"{numero}.pdf",
				mime="application/pdf",
				key=f"pdf_{numero}",
				width="stretch"
			)

			if profil != "Wedding planner":
				return

			if bouton_envoi.button("Préparer le message d'envoi", icon=":material/mail:", key=f"envoi_{numero}", width="stretch"):
				contexte = {**devis, "totaux": montants}
				self.rediger(suggestion(f"envoi_devis_{numero}", "envoi_devis", destinataire_maries(self.event_sheet.data), contexte))

			if bouton_supprimer.button("Supprimer", key=f"suppr_devis_{numero}"):
				self.carnet_devis.supprimer(numero)
				st.rerun()


	def show_devis(self, profil):
		devis_visibles = [
			devis for devis in self.carnet_devis.devis
			if not self.prestataire or meme_nom(devis["emetteur"], self.prestataire["nom"])
		]

		if not devis_visibles:
			st.info("Aucun devis pour l'instant.")

		for devis in reversed(devis_visibles):
			self.show_devis_carte(devis, profil)

		if profil == "Wedding planner":
			self.show_devis_form(bool(devis_visibles))
