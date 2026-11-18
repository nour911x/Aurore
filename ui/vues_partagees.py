import pandas as pd
import streamlit as st
from datetime import datetime

from config.evenements import champs_du_type
from metier.devis import date_lisible
from metier.jour_j import personnes
from metier.rgpd import CATEGORIE_DONNEES_SANTE, sante_partageable
from textes import date_longue, montant
from ui.habillage import accueil_html, frise_html


class VuesPartagees:
	def show_evenement(self):
		infos = self.infos_pour_destinataire(self.prestataire["id"])
		utiles = self.infos_utiles()
		self.show_compteurs({
			":material/event: Date": date_lisible(infos["date"]) or "À définir",
			":material/location_on: Lieu": infos["lieu"] or "À définir",
			":material/groups: Invités prévus": infos["nombre_invites"] or "À définir"
		})

		if self.prestataire["categorie"] == CATEGORIE_DONNEES_SANTE and not sante_partageable(self.event_sheet.data):
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
			self.show_recap_invites()
		elif "couverts" in utiles:
			recap = self.liste_invites.recap_traiteur()
			self.show_compteurs({
				":material/restaurant: Couverts confirmés": recap["couverts_confirmes"],
				":material/hourglass_top: Couverts attendus": recap["couverts_attendus"]
			})

		if self.jour_j.salle["tables"] and "tables" in utiles:
			st.subheader(":material/chair: Couverts par table")
			repartition = self.jour_j.par_table(self.liste_invites.invites)
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

		if self.jour_j.deroule:
			st.subheader(":material/schedule: Déroulé du jour J")
			st.caption("Vos créneaux sont mis en avant.")
			st.markdown(frise_html(self.jour_j.deroule, self.prestataire["nom"]), unsafe_allow_html=True)


	def show_prochains_rdvs(self):
		rdvs = self.agenda.rdvs_a_venir()

		if not rdvs:
			st.caption("Aucun rendez-vous prévu pour l'instant.")

		for rdv in rdvs:
			debut = datetime.fromisoformat(rdv["date_heure"])
			st.markdown(f"**{date_longue(debut)} à {debut:%H:%M}** · {rdv['titre']} · :gray[{rdv['lieu'] or 'lieu à préciser'}]")


	def show_recap_client(self):
		data = self.event_sheet.data
		st.markdown(accueil_html("Mariés"), unsafe_allow_html=True)
		self.show_compteurs({
			":material/event: Date": date_lisible(data["date"]) or "À définir",
			":material/location_on: Lieu": data["lieu"] or "À définir",
			":material/groups: Invités": data["nombre_invites"] or "À définir"
		})

		for cle, libelle in champs_du_type(data).items():
			valeur = data[cle]

			if isinstance(valeur, list):
				valeur = ", ".join(valeur)

			if isinstance(valeur, bool):
				valeur = "Oui" if valeur else "Non"

			if valeur:
				st.markdown(f"**{libelle}** : {date_lisible(valeur) if cle.startswith('date') else valeur}")

		st.subheader(":material/event: Prochains rendez-vous")
		self.show_prochains_rdvs()


	def show_budget_client(self):
		st.caption("Suivi en lecture seule. Pour toute modification, écrivez à votre organisateur.")
		self.show_alertes_factures(self.budget)

		if not self.budget.postes:
			st.info("Le budget n'a pas encore été détaillé.")

		self.show_budget_postes(self.budget, self.event_sheet.data["budget"], "budget_client", lecture_seule=True)


	def show_invitations(self):
		if not self.liste_invites.invites:
			st.info("La liste d'invités n'a pas encore été créée.")
			return

		self.show_compteurs_invites()
		st.dataframe(
			pd.DataFrame(self.liste_invites.invites, columns=["nom", "groupe", "accompagnants", "statut"]),
			column_config={
				"nom": "Nom", "groupe": "Groupe", "accompagnants": "+ Accomp.", "statut": "Statut"
			},
			hide_index=True,
			width="stretch"
		)

		if self.liste_invites.faire_part:
			with st.expander("Texte du faire-part", icon=":material/mail:"):
				st.markdown(self.liste_invites.faire_part)


	def show_agenda_prestataire(self):
		self.show_rappels_rdv()
		self.show_rdvs(lecture_seule=True)


	def show_devis_prestataire(self, profil):
		self.show_devis(profil)
		st.subheader(":material/receipt_long: Factures")
		factures = self.budget.factures_de(self.prestataire)

		if not factures:
			st.caption("Aucune facture enregistrée pour votre prestation.")

		for facture in factures:
			statut = ":green[payée]" if facture["payee"] else f":orange[à régler avant le {date_lisible(facture['echeance'])}]"
			st.markdown(f"- {facture['libelle']} : {montant(facture['montant'])} · {statut}")
