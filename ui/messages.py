import streamlit as st
import uuid

from metier.devis import date_lisible
from metier.messages import MODIFIABLES, TYPES_MESSAGE, destinataire_maries, destinataire_prestataire, suggestion
from metier.rgpd import peut_recevoir_sante
from ui.commun import nom_affiche, resume_contexte


class VueMessages:
	def infos_pour_destinataire(self, prestataire_id):
		prestataire = self.carnet.trouver(prestataire_id)

		if not prestataire:
			return self.event_sheet.infos_sans_historique()

		infos_prestataire = self.event_sheet.infos_pour_prestataire(
			avec_sante=peut_recevoir_sante(self.event_sheet.data, prestataire)
		)

		if st.session_state.get("donner_enveloppe"):
			infos_prestataire["budget_prestation"] = self.budget.prevu_pour(prestataire)

		return infos_prestataire


	def ecrire(self, message, consigne=""):
		with st.spinner("AURORE rédige le message…"):
			return self.conversation_agent_object.write_message(
				TYPES_MESSAGE[message["type"]],
				message["destinataire"],
				message.get("contexte") or {},
				self.infos_pour_destinataire(message["prestataire_id"]),
				consigne
			)


	def rediger(self, suggestion_message, consigne=""):
		self.messagerie.ajouter(suggestion_message, self.ecrire(suggestion_message, consigne))
		st.rerun()


	def reecrire(self, message):
		self.messagerie.reecrire(message["id"], self.ecrire(message))
		st.rerun()


	def changer_statut_message(self, message, statut):
		self.messagerie.changer_statut(message["id"], statut)
		st.rerun()


	def marquer_envoye(self, message):
		self.messagerie.changer_statut(message["id"], "envoyé")
		self.event_sheet.add_echange(
			"Message",
			f"**{TYPES_MESSAGE[message['type']]}** envoyé à {nom_affiche(message)} :\n\n{message['contenu']}"
		)

		prestataire = self.carnet.trouver(message["prestataire_id"])

		if message["type"] == "demande_devis" and prestataire:
			self.changer_statut_prestataire(prestataire, "Devis demandé")

		st.rerun()


	def show_suggestions(self, suggestions):
		st.subheader(":material/notifications: À préparer")

		if not suggestions:
			st.caption("Rien à préparer pour l'instant.")

		for suggestion_message in suggestions:
			with st.container(border=True):
				st.markdown(f"**{TYPES_MESSAGE[suggestion_message['type']]}** → {nom_affiche(suggestion_message)}")
				st.caption(resume_contexte(suggestion_message["contexte"]))
				bouton_rediger, bouton_ignorer = st.columns([3, 1])

				if bouton_rediger.button("Rédiger avec AURORE", icon=":material/edit:", key=f"rediger_{suggestion_message['cle']}"):
					self.rediger(suggestion_message)

				if bouton_ignorer.button("Ignorer", key=f"ignorer_{suggestion_message['cle']}"):
					self.messagerie.ajouter(suggestion_message, "", "annulé")
					st.rerun()


	def show_a_valider(self):
		st.subheader(":material/rate_review: À relire et valider")
		st.caption("Rien ne part sans votre validation : relisez, corrigez si besoin, puis validez.")
		messages = self.messagerie.par_statut(*MODIFIABLES)

		if not messages:
			st.caption("Aucun message à relire.")

		for message in messages:
			with st.container(border=True):
				badge = ":gray[brouillon]" if message["statut"] == "brouillon" else ":orange[à valider]"
				st.markdown(f"**{TYPES_MESSAGE[message['type']]}** → {nom_affiche(message)} · {badge}")
				contenu = st.text_area(
					"Message", value=message["contenu"], height=180, label_visibility="collapsed",
					key=f"contenu_{message['id']}_{hash(message['contenu'])}"
				)

				if contenu != message["contenu"]:
					self.messagerie.modifier_contenu(message["id"], contenu)

				principal, reecrire, annuler = st.columns([2, 2, 1])

				if message["statut"] == "brouillon":
					if principal.button("Prêt à relire", icon=":material/rate_review:", key=f"relire_{message['id']}"):
						self.changer_statut_message(message, "à valider")
				elif principal.button("Valider", icon=":material/task_alt:", type="primary", key=f"valider_{message['id']}"):
					self.changer_statut_message(message, "validé")

				if reecrire.button("Réécrire avec AURORE", icon=":material/refresh:", key=f"reecrire_{message['id']}"):
					self.reecrire(message)

				if annuler.button("Annuler", key=f"annuler_{message['id']}"):
					self.changer_statut_message(message, "annulé")


	def show_valides(self):
		st.subheader(":material/outbox: Validés, à envoyer")
		messages = self.messagerie.par_statut("validé")

		if not messages:
			st.caption("Aucun message validé en attente d'envoi.")

		for message in messages:
			type_message = TYPES_MESSAGE[message["type"]]

			with st.container(border=True):
				st.markdown(f"**{type_message}** → {nom_affiche(message)} · :green[validé]")
				st.markdown(message["contenu"])

				if not (message["telephone"] or message["email"]):
					st.caption("Pas de téléphone ni d'email pour ce destinataire : copiez le message ou complétez sa fiche.")

				self.show_boutons_contact(message["telephone"], message["email"], message=message["contenu"], sujet=type_message)
				st.caption("Ces boutons ouvrent WhatsApp ou votre messagerie avec le texte prêt : c'est vous qui envoyez.")
				envoye, modifier, annuler = st.columns([2, 2, 1])

				if envoye.button("Marquer comme envoyé", icon=":material/check_circle:", key=f"envoye_{message['id']}"):
					self.marquer_envoye(message)

				if modifier.button("Modifier", icon=":material/edit:", key=f"modifier_{message['id']}"):
					self.changer_statut_message(message, "brouillon")

				if annuler.button("Annuler", key=f"annuler_{message['id']}"):
					self.changer_statut_message(message, "annulé")


	def show_message_libre(self):
		destinataires = [destinataire_maries(self.event_sheet.data)] + [
			destinataire_prestataire(prestataire) for prestataire in self.carnet.prestataires
		]
		par_nom = {destinataire["destinataire"]: destinataire for destinataire in destinataires}

		with st.expander("Écrire un message libre", icon=":material/edit:"):
			with st.form("form_message_libre", clear_on_submit=True):
				choix = st.selectbox("Destinataire", list(par_nom))
				consigne = st.text_area("Que voulez-vous lui dire ?")
				avec_aurore, moi_meme = st.columns(2)
				rediger = avec_aurore.form_submit_button("Rédiger avec AURORE", icon=":material/auto_awesome:")
				ecrire = moi_meme.form_submit_button("Garder mon texte en brouillon", icon=":material/edit_note:")

				if consigne and (rediger or ecrire):
					nouveau = suggestion(f"libre_{uuid.uuid4().hex[:8]}", "libre", par_nom[choix], {})

					if rediger:
						self.rediger(nouveau, f"Ce que le message doit dire : {consigne}")

					self.messagerie.ajouter(nouveau, consigne, "brouillon")
					st.rerun()


	def show_historique_messages(self):
		for statut, titre, icone in [("envoyé", "Envoyés", "send"), ("annulé", "Annulés", "cancel")]:
			messages = [message for message in self.messagerie.par_statut(statut) if message["contenu"]]

			if messages:
				with st.expander(f"{titre} ({len(messages)})", icon=f":material/{icone}:"):
					for message in reversed(messages):
						st.markdown(f"**{TYPES_MESSAGE[message['type']]}** → {nom_affiche(message)} · {date_lisible(message['date'])}")
						st.caption(message["contenu"])


	def show_messages(self, suggestions):
		st.toggle(
			"Indiquer aux prestataires l'enveloppe prévue pour leur poste",
			key="donner_enveloppe",
			help="Désactivé : aucun montant n'est donné, le prestataire propose son prix."
		)
		self.show_suggestions(suggestions)
		self.show_a_valider()
		self.show_valides()
		self.show_message_libre()
		self.show_historique_messages()
