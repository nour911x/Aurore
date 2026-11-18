import streamlit as st

from metier.prestataires import CATEGORIES, STATUTS, appliquer_statut
from ui.commun import AUCUN, ICONES_STATUT


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
				echeance = st.date_input("Date d'échéance")
				payee = st.checkbox("Déjà payée")

				if st.form_submit_button("Ajouter au budget") and libelle:
					self.budget.add_facture(poste_choisi, libelle, montant, str(echeance), payee)
					st.success("Ajouté au budget", icon=":material/check_circle:")


	def changer_statut_prestataire(self, prestataire, statut):
		appliquer_statut(self.carnet, self.event_sheet, prestataire, statut)


	def show_prestataire(self, prestataire):
		with st.container(border=True):
			infos, statut = st.columns([3, 2])
			infos.markdown(f"**{prestataire['nom']}** {ICONES_STATUT[prestataire['statut']]}")

			details = [
				texte for texte in [
					f":material/person: {prestataire['contact']}" if prestataire["contact"] else "",
					f":material/euro: ~{prestataire['tarif_indicatif']} €" if prestataire["tarif_indicatif"] else "",
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

			if prestataire["notes"]:
				st.markdown(f":material/notes: {prestataire['notes']}")

			self.show_boutons_contact(prestataire["telephone"], prestataire["email"], prestataire["lien"])

			if prestataire["statut"] == "Réservé":
				self.show_ajout_facture_prestataire(prestataire)

			if st.button("Supprimer", key=f"suppr_presta_{prestataire['id']}"):
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

				if st.form_submit_button("Ajouter au carnet") and nom:
					self.carnet.add_prestataire(
						nom, categorie, contact, telephone, email, lien,
						tarif, None if poste_budget == AUCUN else poste_budget, notes
					)
					st.rerun()


	def show_prestataires(self):
		if not self.carnet.prestataires:
			st.info("Le carnet est vide. Ajoutez un premier prestataire ci-dessous.")
		else:
			self.show_resume_carnet()

		for categorie, membres in self.carnet.par_categorie().items():
			st.subheader(categorie)

			for prestataire in membres:
				self.show_prestataire(prestataire)

		self.show_prestataire_form()
