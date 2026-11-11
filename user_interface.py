import streamlit as st
from llm_agent import ConversationAgent
from event_state import EventSheet
from budget import Budget
from agenda import Agenda
from datetime import datetime


class UserInterface:
	def __init__(self):
		st.set_page_config(page_title="AURORE")
		st.title("AURORE 🎉")
		self.conversation_agent_object = self.get_persistant_conversation_agent()
		self.event_sheet = self.get_persistant_event_sheet()
		self.budget = self.get_persistant_budget()
		self.agenda = self.get_persistant_agenda()


	def get_persistant_conversation_agent(self):

		if "conversation_agent_object" not in st.session_state:
			st.session_state.conversation_agent_object = ConversationAgent()

		return st.session_state.conversation_agent_object


	def get_persistant_event_sheet(self):

		if "event_sheet" not in st.session_state:
			st.session_state.event_sheet = EventSheet()

		return st.session_state.event_sheet


	def get_persistant_budget(self):

		if "budget" not in st.session_state:
			st.session_state.budget = Budget()

		return st.session_state.budget


	def get_persistant_agenda(self):

		if "agenda" not in st.session_state:
			st.session_state.agenda = Agenda()

		return st.session_state.agenda


	def show_event_sheet(self):
		labels = {
			"type_evenement": "Événement",
			"date": "Date",
			"lieu": "Lieu",
			"budget": "Budget (€)",
			"nombre_invites": "Invités",
			"theme": "Thème",
			"allergies_interdits": "Allergies / interdits",
			"prestataires": "Prestataires"
		}

		with st.sidebar:
			st.header("📋 Fiche événement")

			for key, label in labels.items():
				value = self.event_sheet.data[key]

				if value:
					if isinstance(value, list):
						value = ", ".join(value)
					st.markdown(f"**{label}** : {value}")


	def show_discussion_history(self):
		for message in self.conversation_agent_object.get_conversation_history():
			with st.chat_message(message["role"]):
				st.markdown(message["content"])


	def show_alertes_factures(self):
		for facture in self.budget.factures_a_payer():
			if facture["jours_restants"] < 0:
				st.error(f"🚨 Facture en retard : {facture['libelle']} ({facture['montant']} €) — échéance dépassée ({facture['echeance']})")
			elif facture["jours_restants"] <= 7:
				st.warning(f"📬 À payer dans {facture['jours_restants']} jours : {facture['libelle']} ({facture['montant']} €, poste {facture['poste']})")


	def show_budget_postes(self):
		budget_total = self.event_sheet.data["budget"]
		total_engage = self.budget.total_engage()

		if budget_total:
			st.progress(min(total_engage / budget_total, 1.0))
			st.markdown(f"**{total_engage} € engagés** sur un budget de **{budget_total} €**")

		for poste in self.budget.postes:
			engage = self.budget.engage_du_poste(poste)
			icone = "🔴" if engage > poste["montant_prevu"] else "🟢"

			with st.expander(f"{icone} {poste['nom']} — {engage} € / {poste['montant_prevu']} € prévus"):
				for facture in poste["factures"]:
					statut = "✅ payée" if facture["payee"] else f"⏳ à payer avant le {facture['echeance']}"
					st.markdown(f"- {facture['libelle']} : {facture['montant']} € ({statut})")

					if not facture["payee"]:
						if st.button("Marquer payée", key=f"payee_{poste['nom']}_{facture['libelle']}"):
							self.budget.marquer_payee(poste["nom"], facture["libelle"])
							st.rerun()


	def show_budget_forms(self):
		with st.expander("➕ Ajouter un poste"):
			with st.form("form_poste", clear_on_submit=True):
				nom = st.text_input("Nom du poste (ex : traiteur)")
				montant = st.number_input("Montant prévu (€)", min_value=0, step=100)

				if st.form_submit_button("Ajouter le poste") and nom:
					self.budget.add_poste(nom, montant)
					st.rerun()

		with st.expander("🧾 Ajouter une facture / un devis"):
			if self.budget.postes:
				with st.form("form_facture", clear_on_submit=True):
					noms_postes = [poste["nom"] for poste in self.budget.postes]
					poste_choisi = st.selectbox("Poste", noms_postes)
					libelle = st.text_input("Libellé (ex : acompte traiteur)")
					montant = st.number_input("Montant (€)", min_value=0, step=50)
					echeance = st.date_input("Date d'échéance")
					payee = st.checkbox("Déjà payée")

					if st.form_submit_button("Ajouter la facture") and libelle:
						self.budget.add_facture(poste_choisi, libelle, montant, str(echeance), payee)
						st.rerun()
			else:
				st.caption("Ajoute d'abord un poste de budget.")


	def show_budget(self):
		self.show_alertes_factures()

		if not self.budget.postes:
			st.info("Aucun poste de budget pour l'instant.")

			if self.event_sheet.data["budget"]:
				if st.button("💡 Proposer une répartition adaptée à mon événement"):
					postes = self.conversation_agent_object.suggest_budget_postes(self.event_sheet.data)

					for poste in postes:
						self.budget.add_poste(poste["nom"], poste["montant_prevu"])

					st.rerun()
		else:
			self.show_budget_postes()

		self.show_budget_forms()


	def show_rappels_rdv(self):
		for rdv in self.agenda.rdvs_proches():
			date_lisible = datetime.fromisoformat(rdv["date_heure"]).strftime("%d/%m à %H:%M")
			st.info(f"📅 Bientôt : {rdv['titre']} le {date_lisible} avec {rdv['avec']}")


	def show_rdvs(self):
		rdvs = self.agenda.rdvs_a_venir()

		if not rdvs:
			st.info("Aucun rendez-vous à venir.")

		for rdv in rdvs:
			date_lisible = datetime.fromisoformat(rdv["date_heure"]).strftime("%A %d/%m/%Y à %H:%M")

			with st.container(border=True):
				st.markdown(f"**{rdv['titre']}** — {date_lisible} ({rdv['duree_minutes']} min)")
				st.markdown(f"📍 {rdv['lieu']} · 👤 {rdv['avec']}")

				if st.button("Supprimer", key=f"del_{rdv['titre']}_{rdv['date_heure']}"):
					self.agenda.supprimer_rdv(rdv["titre"], rdv["date_heure"])
					st.rerun()

		if self.agenda.rdvs:
			st.download_button(
				"📥 Exporter vers mon calendrier (.ics)",
				data=self.agenda.export_ics(),
				file_name="aurore_rendez_vous.ics",
				mime="text/calendar"
			)


	def show_rdv_form(self):
		with st.expander("➕ Ajouter un rendez-vous"):
			with st.form("form_rdv", clear_on_submit=True):
				titre = st.text_input("Titre (ex : essayage robe, visite de salle, dégustation)")
				jour = st.date_input("Date")
				heure = st.time_input("Heure")
				duree = st.number_input("Durée (minutes)", min_value=15, step=15, value=60)
				lieu = st.text_input("Lieu")
				avec = st.text_input("Avec qui (ex : traiteur, DJ, propriétaire de la salle)")

				if st.form_submit_button("Ajouter le rendez-vous") and titre:
					date_heure = datetime.combine(jour, heure).isoformat()
					conflit = self.agenda.add_rdv(titre, date_heure, duree, lieu, avec)

					if conflit:
						st.error(f"⚠️ Conflit avec « {conflit['titre']} » déjà prévu à ce moment-là. Choisis un autre créneau.")
					else:
						st.rerun()


	def show_agenda(self):
		self.show_rappels_rdv()
		self.show_rdvs()
		self.show_rdv_form()


	def run(self):
		chat_tab, budget_tab, agenda_tab = st.tabs(["💬 Discussion", "💰 Budget", "📅 Rendez-vous"])

		text_interaction = st.chat_input(
			"Parle-moi de ton événement !",
			accept_file=False,
			accept_audio=False
			)

		if text_interaction :
			self.conversation_agent_object.ask_llm(text_interaction)
			new_info = self.conversation_agent_object.extract_event_info(self.event_sheet.data)
			self.event_sheet.update(new_info)

		with chat_tab:
			self.show_discussion_history()

		with budget_tab:
			self.show_budget()

		with agenda_tab:
			self.show_agenda()

		self.show_event_sheet()



if __name__ == "__main__":
	user_interface_object = UserInterface()
	user_interface_object.run()








































	# response = ask_llm(user_input)
	# with st.chat_message("user"):
	# 	st.markdown(user_input)

	# with st.chat_message("system"):
	# 	st.markdown(response)


