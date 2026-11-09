import streamlit as st
from llm_agent import ConversationAgent
from event_state import EventSheet


class UserInterface:
	def __init__(self):
		st.set_page_config(page_title="AURORE")
		st.title("AURORE 🎉")
		self.conversation_agent_object = self.get_persistant_conversation_agent()
		self.event_sheet = self.get_persistant_event_sheet()


	def get_persistant_conversation_agent(self):

		if "conversation_agent_object" not in st.session_state:
			st.session_state.conversation_agent_object = ConversationAgent()

		return st.session_state.conversation_agent_object


	def get_persistant_event_sheet(self):

		if "event_sheet" not in st.session_state:
			st.session_state.event_sheet = EventSheet()

		return st.session_state.event_sheet


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


	def run(self):
		text_interaction = st.chat_input(
			"Parle-moi de ton événement !",
			accept_file=False,
			accept_audio=False
			)

		if text_interaction :
			self.conversation_agent_object.ask_llm(text_interaction)
			new_info = self.conversation_agent_object.extract_event_info(self.event_sheet.data)
			self.event_sheet.update(new_info)
			self.show_discussion_history()

		self.show_event_sheet()



if __name__ == "__main__":
	user_interface_object = UserInterface()
	user_interface_object.run()








































	# response = ask_llm(user_input)
	# with st.chat_message("user"):
	# 	st.markdown(user_input)

	# with st.chat_message("system"):
	# 	st.markdown(response)


