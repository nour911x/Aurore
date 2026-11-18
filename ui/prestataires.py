import streamlit as st

from donnees.dossiers import libelle_dossier
from metier.accueil import doubles_reservations
from metier.prestataires import CATEGORIES, STATUTS, appliquer_statut, meme_nom
from metier.devis import date_lisible
from textes import montant
from ui.commun import AUCUN, FORMAT_DATE, ICONES_STATUT


class VuePrestataires:
	def show_resume_carnet(self):
		compteurs = self.carnet.compter_par_statut()
		self.show_compteurs({f"{ICONES_STATUT[statut]} {statut}": compteurs[statut] for statut in STATUTS})


	def show_ajout_facture_prestataire(self, prestataire):
		with st.expander("Ajouter son devis / acompte au budget", icon=":material/receipt_long:"):
			if not self.budget.postes:
				st.caption("Créez d'abord les postes dans l'onglet Budget & devis.")
				return

			with st.form(f"facture_{prestataire['id']}", clear_on_submit=True):
				noms_postes = [poste["nom"] for poste in self.budget.postes]
				index_poste = noms_postes.index(prestataire["poste_budget"]) if prestataire["poste_budget"] in noms_postes else 0
				poste_choisi = st.selectbox("Poste", noms_postes, index=index_poste)
				libelle = st.text_input("Libellé", value=f"Acompte {prestataire['nom']}")
				montant = st.number_input("Montant (€)", min_value=0, step=50, value=prestataire["tarif_indicatif"] or 0)
				echeance = st.date_input("Date d'échéance", format=FORMAT_DATE)
				payee = st.checkbox("Déjà payée")

				if st.form_submit_button("Ajouter au budget") and libelle:
					self.budget.add_facture(poste_choisi, libelle, montant, str(echeance), payee)
					st.success("Ajouté au budget", icon=":material/check_circle:")


	def changer_statut_prestataire(self, prestataire, statut):
		appliquer_statut(self.carnet, self.event_sheet, prestataire, statut)


	def show_conditions(self, prestataire):
		with st.expander("Conditions pour ce dossier", icon=":material/tune:"):
			with st.form(f"conditions_{prestataire['id']}"):
				postes = [AUCUN] + [poste["nom"] for poste in self.budget.postes]
				actuel = prestataire["poste_budget"] if prestataire["poste_budget"] in postes else AUCUN
				gauche, droite = st.columns(2)
				tarif = gauche.number_input("Tarif pour ce dossier (€)", min_value=0, step=100, value=int(prestataire["tarif_indicatif"] or 0))
				poste_budget = droite.selectbox("Poste de budget", postes, index=postes.index(actuel))

				if st.form_submit_button("Enregistrer"):
					self.carnet.modifier_conditions(prestataire["id"], tarif, None if poste_budget == AUCUN else poste_budget)
					st.rerun()


	def show_prestataire(self, prestataire, doubles):
		with st.container(border=True):
			infos, statut = st.columns([3, 2])
			infos.markdown(f"**{prestataire['nom']}** {ICONES_STATUT[prestataire['statut']]}")

			details = [
				texte for texte in [
					f":material/person: {prestataire['contact']}" if prestataire["contact"] else "",
					f":material/euro: ~{montant(prestataire['tarif_indicatif'])} pour ce dossier" if prestataire["tarif_indicatif"] else "",
					f":material/folder: {prestataire['poste_budget']}" if prestataire["poste_budget"] else ""
				] if texte
			]

			if details:
				infos.caption(" · ".join(details))

			nouveau_statut = statut.selectbox(
				"Statut",
				STATUTS,
				index=STATUTS.index(prestataire["statut"]),
				key=f"statut_{prestataire['id']}_{prestataire['statut']}",
				label_visibility="collapsed"
			)

			if nouveau_statut != prestataire["statut"]:
				self.changer_statut_prestataire(prestataire, nouveau_statut)
				st.rerun()

			for double in doubles:
				autres = [dossier for dossier in double["dossiers"] if dossier != libelle_dossier(self.event_sheet.data)]

				if meme_nom(double["prestataire"], prestataire["nom"]) and autres:
					st.warning(
						f"Aussi réservé le {date_lisible(double['date'])} pour : {', '.join(autres)}.",
						icon=":material/event_busy:"
					)

			if prestataire["notes"]:
				st.markdown(f":material/notes: {prestataire['notes']}")

			self.show_boutons_contact(prestataire["telephone"], prestataire["email"], prestataire["lien"])

			self.show_conditions(prestataire)

			if prestataire["statut"] == "Réservé":
				self.show_ajout_facture_prestataire(prestataire)

			if st.button("Retirer de ce dossier", key=f"suppr_presta_{prestataire['id']}", help="Le prestataire reste dans le carnet commun."):
				self.carnet.supprimer(prestataire["id"])
				st.rerun()


	def show_prestataire_form(self, titre="Ajouter un prestataire", cle="form_prestataire", categorie_defaut=CATEGORIES[0]):
		with st.expander(titre, icon=":material/add:"):
			with st.form(cle, clear_on_submit=True):
				gauche, droite = st.columns(2)
				nom = gauche.text_input("Nom (ex : Traiteur Saveurs d'Orient)")
				categorie = droite.selectbox("Catégorie", CATEGORIES, index=CATEGORIES.index(categorie_defaut))
				contact = gauche.text_input("Personne à contacter")
				telephone = droite.text_input("Téléphone (ex : 06 12 34 56 78)")
				email = gauche.text_input("Email")
				lien = droite.text_input("Site ou Instagram (lien complet)")
				tarif = gauche.number_input("Tarif indicatif (€)", min_value=0, step=100)
				postes = [AUCUN] + [poste["nom"] for poste in self.budget.postes]
				poste_budget = droite.selectbox("Poste de budget", postes)
				notes = st.text_area("Notes (spécialités, disponibilités, impressions…)", height=68)

				if st.form_submit_button("Ajouter au carnet et à ce dossier") and nom:
					self.carnet.add_prestataire(
						nom, categorie, contact, telephone, email, lien,
						tarif, None if poste_budget == AUCUN else poste_budget, notes
					)
					st.rerun()


	def show_choix_dans_carnet(self):
		disponibles = {f"{fiche['nom']} · {fiche['categorie']}": fiche for fiche in self.carnet.disponibles()}

		if not disponibles:
			return

		with st.expander("Choisir dans le carnet commun", icon=":material/menu_book:"):
			choix = st.selectbox("Prestataire", list(disponibles))

			if st.button("Ajouter à ce dossier", icon=":material/add:"):
				self.carnet.selectionner(disponibles[choix]["id"])
				st.rerun()


	def show_prestataires(self):
		st.caption("Le carnet est commun à tous vos dossiers ; le statut, le tarif et le poste de budget sont propres à ce dossier.")

		if not self.carnet.prestataires:
			st.info("Aucun prestataire dans ce dossier. Choisissez-en dans le carnet commun ou ajoutez-en un nouveau.")
		else:
			self.show_resume_carnet()

		doubles = [double for double in doubles_reservations() if double["date"] == self.event_sheet.data["date"]]

		for categorie, membres in self.carnet.par_categorie().items():
			st.subheader(categorie)

			for prestataire in membres:
				self.show_prestataire(prestataire, doubles)

		self.show_choix_dans_carnet()
		self.show_prestataire_form()
