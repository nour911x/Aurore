import streamlit as st
from llm_agent import ConversationAgent
from event_state import EventSheet
from budget import Budget


class UserInterface:
	def __init__(self):
		st.set_page_config(page_title="AURORE")
		st.title("AURORE 🎉")
		self.conversation_agent_object = self.get_persistant_conversation_agent()
		self.event_sheet = self.get_persistant_event_sheet()
		self.budget = self.get_persistant_budget()


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


	def run(self):
		chat_tab, budget_tab = st.tabs(["💬 Discussion", "💰 Budget"])

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

		self.show_event_sheet()



if __name__ == "__main__":
	user_interface_object = UserInterface()
	user_interface_object.run()








































	# response = ask_llm(user_input)
	# with st.chat_message("user"):
	# 	st.markdown(user_input)

	# with st.chat_message("system"):
	# 	st.markdown(response)


