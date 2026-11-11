import streamlit as st
from llm_agent import ConversationAgent
from event_state import EventSheet
from budget import Budget
from agenda import Agenda
from prestataires import Carnet, CATEGORIES, STATUTS, lien_whatsapp, lien_email
from messages import (
	Messagerie, TYPES_MESSAGE, detecter_messages,
	destinataire_maries, destinataire_prestataire, suggestion
)
from devis import CarnetDevis, STATUTS_DEVIS, totaux, euros, date_validite, generer_pdf
from invites import (
	ListeInvites, GROUPES, STATUTS_INVITE, REGIMES,
	nettoyer, lire_contacts, message_personnel, generer_faire_part_pdf
)
from datetime import date, datetime, timedelta
import pandas as pd
import uuid


LABELS_FICHE = {
	"noms": "Couple / client(s)",
	"telephone": "Téléphone",
	"email": "Email",
	"type_evenement": "Événement",
	"date": "Date",
	"lieu": "Lieu",
	"budget": "Budget (€)",
	"nombre_invites": "Invités",
	"theme": "Thème",
	"allergies_interdits": "Allergies / interdits",
	"preferences": "Préférences",
	"preferences_musicales": "Musique",
	"prestataires": "Prestataires"
}

CHAMPS_LISTES = {
	"allergies_interdits": "Allergies / interdits (alimentaires, religieux, à éviter absolument…)",
	"preferences": "Préférences (style, couleurs, fleurs, ambiance…)",
	"preferences_musicales": "Préférences musicales (styles, chansons, ouverture de bal…)",
	"prestataires": "Prestataires déjà choisis"
}

SOURCES_ECHANGE = ["Rendez-vous", "Appel", "Message", "Email", "Autre"]

ICONES_STATUT = {
	"À contacter": "⚪",
	"Devis demandé": "🟡",
	"Devis reçu": "🟠",
	"Réservé": "🟢",
	"Refusé": "🔴"
}

AUCUN = "—"

PLANNER = "AURORE - Wedding planner"

COLONNES_DEVIS = ["designation", "quantite", "prix_unitaire"]

CONFIG_COLONNES_DEVIS = {
	"designation": st.column_config.TextColumn("Désignation", width="large"),
	"quantite": st.column_config.NumberColumn("Qté", min_value=0),
	"prix_unitaire": st.column_config.NumberColumn("Prix unit. HT (€)", min_value=0)
}

ICONES_INVITE = {
	"À inviter": "⚪",
	"Invité": "📨",
	"Confirmé": "✅",
	"Décliné": "❌"
}

COLONNES_INVITES = ["id", "nom", "groupe", "telephone", "email", "accompagnants", "regime", "allergies", "statut"]

CONFIG_COLONNES_INVITES = {
	"id": None,
	"nom": st.column_config.TextColumn("Nom", required=True),
	"groupe": st.column_config.SelectboxColumn("Groupe", options=GROUPES, default="Autre"),
	"telephone": st.column_config.TextColumn("Téléphone"),
	"email": st.column_config.TextColumn("Email"),
	"accompagnants": st.column_config.NumberColumn("+ Accomp.", min_value=0, step=1, default=0),
	"regime": st.column_config.SelectboxColumn("Régime", options=REGIMES, default="Aucun"),
	"allergies": st.column_config.TextColumn("Allergies"),
	"statut": st.column_config.SelectboxColumn("Statut", options=STATUTS_INVITE, default="À inviter")
}

NOTES_DEVIS ="Acompte à régler à la signature, solde au plus tard le jour de l'événement."


def lire_date(texte):
	try:
		return date.fromisoformat(texte)
	except (TypeError, ValueError):
		return None


def texte_vers_liste(texte):
	return [element.strip() for element in texte.split(",") if element.strip()]


def nombre(valeur):
	try:
		valeur = float(valeur)
	except (TypeError, ValueError):
		return 0.0

	return valeur if valeur == valeur else 0.0


def lignes_valides(lignes):
	return [
		{
			"designation": str(ligne.get("designation") or "").strip(),
			"quantite": nombre(ligne.get("quantite")),
			"prix_unitaire": nombre(ligne.get("prix_unitaire"))
		}
		for ligne in lignes
		if isinstance(ligne.get("designation"), str) and ligne["designation"].strip()
	]


def resume_contexte(contexte):
	return contexte.get("titre") or contexte.get("libelle") or contexte.get("nom") or ""


class UserInterface:
	def __init__(self):
		st.set_page_config(page_title="AURORE")
		st.title("AURORE 🎉")
		self.conversation_agent_object = self.get_persistant("conversation_agent_object", ConversationAgent)
		self.event_sheet = self.get_persistant("event_sheet", EventSheet)
		self.budget = self.get_persistant("budget", Budget)
		self.agenda = self.get_persistant("agenda", Agenda)
		self.carnet = self.get_persistant("carnet", Carnet)
		self.messagerie = self.get_persistant("messagerie", Messagerie)
		self.carnet_devis = self.get_persistant("carnet_devis", CarnetDevis)
		self.liste_invites = self.get_persistant("liste_invites", ListeInvites)
		st.session_state.setdefault("version_invites", 0)
		st.session_state.setdefault("briefings", {})
		st.session_state.setdefault("lignes_devis", [])
		st.session_state.setdefault("version_lignes", 0)


	@staticmethod
	def get_persistant(cle, classe):

		if cle not in st.session_state:
			st.session_state[cle] = classe()

		return st.session_state[cle]


	def show_event_sheet(self):
		with st.sidebar:
			st.header("📋 Fiche événement")

			for key, label in LABELS_FICHE.items():
				value = self.event_sheet.data[key]

				if value:
					if isinstance(value, list):
						value = ", ".join(value)
					st.markdown(f"**{label}** : {value}")

			nombre_echanges = len(self.event_sheet.data["historique"])

			if nombre_echanges:
				st.caption(f"🗂️ {nombre_echanges} échange(s) dans l'historique")


	def show_fiche_form(self):
		data = self.event_sheet.data

		with st.form("form_fiche"):
			gauche, droite = st.columns(2)
			noms = gauche.text_input("Couple / client(s)", value=data["noms"] or "")
			type_evenement = droite.text_input("Type d'événement", value=data["type_evenement"] or "")
			telephone = gauche.text_input("Téléphone des mariés", value=data["telephone"] or "")
			email = droite.text_input("Email des mariés", value=data["email"] or "")
			date_evenement = gauche.date_input("Date de l'événement", value=lire_date(data["date"]))
			lieu = droite.text_input("Lieu", value=data["lieu"] or "")
			budget = gauche.number_input("Budget (€)", min_value=0, step=500, value=int(data["budget"]) if data["budget"] else None)
			invites = droite.number_input("Nombre d'invités", min_value=0, step=5, value=int(data["nombre_invites"]) if data["nombre_invites"] else None)
			theme = st.text_input("Thème", value=data["theme"] or "")

			st.caption("Pour les listes, sépare les éléments par des virgules.")
			listes = {
				key: st.text_area(label, value=", ".join(data[key]), height=68)
				for key, label in CHAMPS_LISTES.items()
			}

			if st.form_submit_button("💾 Enregistrer la fiche"):
				nouvelle_fiche = {
					"noms": noms or None,
					"type_evenement": type_evenement or None,
					"telephone": telephone or None,
					"email": email or None,
					"date": str(date_evenement) if date_evenement else None,
					"lieu": lieu or None,
					"budget": budget,
					"nombre_invites": invites,
					"theme": theme or None
				}

				for key, texte in listes.items():
					nouvelle_fiche[key] = texte_vers_liste(texte)

				self.event_sheet.remplacer(nouvelle_fiche)
				st.rerun()


	def show_historique(self):
		st.subheader("🗂️ Historique des échanges")

		if self.conversation_agent_object.get_conversation_history():
			if st.button("📝 Ajouter un résumé de la discussion avec AURORE"):
				with st.spinner("AURORE résume la discussion…"):
					resume = self.conversation_agent_object.summarize_conversation()

				self.event_sheet.add_echange("Discussion avec AURORE", resume)
				st.rerun()

		with st.expander("➕ Noter un échange (rendez-vous, appel, message…)"):
			with st.form("form_echange", clear_on_submit=True):
				source = st.selectbox("Type d'échange", SOURCES_ECHANGE)
				resume = st.text_area("Ce qui a été dit ou décidé")

				if st.form_submit_button("Ajouter à l'historique") and resume:
					self.event_sheet.add_echange(source, resume)
					st.rerun()

		historique = self.event_sheet.data["historique"]

		if not historique:
			st.caption("Aucun échange enregistré pour l'instant.")

		for echange in reversed(historique):
			with st.container(border=True):
				date_lisible = date.fromisoformat(echange["date"]).strftime("%d/%m/%Y")
				st.markdown(f"**{echange['source']}** · {date_lisible}")
				st.markdown(echange["resume"])


	def show_fiche_couple(self):
		self.show_fiche_form()
		self.show_historique()


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


	def generer_briefing(self, rdv):
		postes_budget = [
			{
				"nom": poste["nom"],
				"montant_prevu": poste["montant_prevu"],
				"engage": self.budget.engage_du_poste(poste)
			}
			for poste in self.budget.postes
		]

		event_data = self.event_sheet.infos_sans_historique()

		if self.liste_invites.invites:
			event_data["invites"] = self.liste_invites.recap_traiteur()

		return self.conversation_agent_object.prepare_briefing(
			rdv,
			event_data,
			self.event_sheet.data["historique"],
			postes_budget,
			self.carnet.trouver_par_nom(rdv["avec"])
		)


	def show_rdvs(self):
		rdvs = self.agenda.rdvs_a_venir()

		if not rdvs:
			st.info("Aucun rendez-vous à venir.")

		for rdv in rdvs:
			date_lisible = datetime.fromisoformat(rdv["date_heure"]).strftime("%A %d/%m/%Y à %H:%M")
			cle = f"{rdv['titre']}_{rdv['date_heure']}"

			with st.container(border=True):
				st.markdown(f"**{rdv['titre']}** — {date_lisible} ({rdv['duree_minutes']} min)")
				st.markdown(f"📍 {rdv['lieu']} · 👤 {rdv['avec']}")

				bouton_briefing, bouton_supprimer = st.columns([3, 1])

				if bouton_briefing.button("📋 Préparer le briefing", key=f"brief_{cle}"):
					with st.spinner("AURORE rassemble tout ce qu'il faut savoir…"):
						st.session_state.briefings[cle] = self.generer_briefing(rdv)

				if bouton_supprimer.button("Supprimer", key=f"del_{cle}"):
					self.agenda.supprimer_rdv(rdv["titre"], rdv["date_heure"])
					st.session_state.briefings.pop(cle, None)
					st.rerun()

				if cle in st.session_state.briefings:
					with st.expander("📋 Briefing avant le rendez-vous", expanded=True):
						st.markdown(st.session_state.briefings[cle])

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
				noms_prestataires = [AUCUN] + [prestataire["nom"] for prestataire in self.carnet.prestataires]
				prestataire_choisi = st.selectbox("Avec quel prestataire", noms_prestataires)
				autre = st.text_input("Ou avec quelqu'un d'autre (ex : les mariés, la témoin)")
				avec = autre or ("" if prestataire_choisi == AUCUN else prestataire_choisi)

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


	@staticmethod
	def show_compteurs(compteurs):
		for colonne, (label, valeur) in zip(st.columns(len(compteurs)), compteurs.items()):
			colonne.metric(label, valeur)


	def show_resume_carnet(self):
		compteurs = self.carnet.compter_par_statut()
		self.show_compteurs({f"{ICONES_STATUT[statut]} {statut}": compteurs[statut] for statut in STATUTS})


	@staticmethod
	def show_boutons_contact(telephone, email, lien="", message="", sujet=""):
		liens = []

		if telephone:
			liens.append(("💬 WhatsApp", lien_whatsapp(telephone, message)))

			if not message:
				liens.append(("📞 Appeler", f"tel:{telephone}"))

		if email:
			liens.append(("✉️ Email", lien_email(email, sujet, message)))

		if lien:
			liens.append(("🔗 Site / Instagram", lien))

		if liens:
			for colonne, (texte, url) in zip(st.columns(len(liens)), liens):
				colonne.link_button(texte, url, width="stretch")


	def show_ajout_facture_prestataire(self, prestataire):
		with st.expander("🧾 Ajouter son devis / acompte au budget"):
			if not self.budget.postes:
				st.caption("Crée d'abord tes postes dans l'onglet 💰 Budget.")
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
					st.success("Ajouté au budget ✅")


	def changer_statut_prestataire(self, prestataire, statut):
		self.carnet.changer_statut(prestataire["id"], statut)

		if statut == "Réservé":
			self.event_sheet.ajouter_prestataire(f"{prestataire['nom']} ({prestataire['categorie']})")


	def show_prestataire(self, prestataire):
		with st.container(border=True):
			infos, statut = st.columns([3, 2])
			infos.markdown(f"**{prestataire['nom']}** {ICONES_STATUT[prestataire['statut']]}")

			details = [
				texte for texte in [
					f"👤 {prestataire['contact']}" if prestataire["contact"] else "",
					f"💶 ~{prestataire['tarif_indicatif']} €" if prestataire["tarif_indicatif"] else "",
					f"📂 {prestataire['poste_budget']}" if prestataire["poste_budget"] else ""
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
				st.markdown(f"📝 {prestataire['notes']}")

			self.show_boutons_contact(prestataire["telephone"], prestataire["email"], prestataire["lien"])

			if prestataire["statut"] == "Réservé":
				self.show_ajout_facture_prestataire(prestataire)

			if st.button("Supprimer", key=f"suppr_presta_{prestataire['id']}"):
				self.carnet.supprimer(prestataire["id"])
				st.rerun()


	def show_prestataire_form(self):
		with st.expander("➕ Ajouter un prestataire"):
			with st.form("form_prestataire", clear_on_submit=True):
				gauche, droite = st.columns(2)
				nom = gauche.text_input("Nom (ex : Traiteur Saveurs d'Orient)")
				categorie = droite.selectbox("Catégorie", CATEGORIES)
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
			st.info("Ton carnet est vide. Ajoute ton premier prestataire ci-dessous 👇")
		else:
			self.show_resume_carnet()

		for categorie, membres in self.carnet.par_categorie().items():
			st.subheader(categorie)

			for prestataire in membres:
				self.show_prestataire(prestataire)

		self.show_prestataire_form()


	def rediger(self, suggestion_message, consigne=""):
		with st.spinner("AURORE rédige le message…"):
			contenu = self.conversation_agent_object.write_message(
				TYPES_MESSAGE[suggestion_message["type"]],
				suggestion_message["destinataire"],
				suggestion_message["contexte"],
				self.event_sheet.infos_sans_historique(),
				consigne
			)

		self.messagerie.ajouter(suggestion_message, contenu)
		st.rerun()


	def marquer_envoye(self, message):
		self.messagerie.modifier(message["id"], statut="envoyé", date=date.today().isoformat())
		self.event_sheet.add_echange(
			"Message",
			f"**{TYPES_MESSAGE[message['type']]}** envoyé à {message['destinataire']} :\n\n{message['contenu']}"
		)

		prestataire = self.carnet.trouver(message["prestataire_id"])

		if message["type"] == "demande_devis" and prestataire:
			self.changer_statut_prestataire(prestataire, "Devis demandé")

		st.rerun()


	def show_suggestions(self, suggestions):
		st.subheader("🔔 À préparer")

		if not suggestions:
			st.caption("Rien à préparer pour l'instant 👌")

		for suggestion_message in suggestions:
			with st.container(border=True):
				st.markdown(f"**{TYPES_MESSAGE[suggestion_message['type']]}** → {suggestion_message['destinataire']}")
				st.caption(resume_contexte(suggestion_message["contexte"]))
				bouton_rediger, bouton_ignorer = st.columns([3, 1])

				if bouton_rediger.button("✍️ Rédiger avec AURORE", key=f"rediger_{suggestion_message['cle']}"):
					self.rediger(suggestion_message)

				if bouton_ignorer.button("Ignorer", key=f"ignorer_{suggestion_message['cle']}"):
					self.messagerie.ajouter(suggestion_message, "", "ignoré")
					st.rerun()


	def show_a_envoyer(self):
		st.subheader("📤 À envoyer")
		messages = self.messagerie.par_statut("à envoyer")

		if not messages:
			st.caption("Aucun message en attente.")

		for message in messages:
			type_message = TYPES_MESSAGE[message["type"]]

			with st.container(border=True):
				st.markdown(f"**{type_message}** → {message['destinataire']}")
				contenu = st.text_area("Message", value=message["contenu"], key=f"contenu_{message['id']}", height=180, label_visibility="collapsed")

				if contenu != message["contenu"]:
					self.messagerie.modifier(message["id"], contenu=contenu)

				if not (message["telephone"] or message["email"]):
					st.caption("Pas de téléphone ni d'email pour ce destinataire : copie le message ou complète sa fiche.")

				self.show_boutons_contact(message["telephone"], message["email"], message=contenu, sujet=type_message)
				bouton_envoye, bouton_supprimer = st.columns([3, 1])

				if bouton_envoye.button("✅ Marquer comme envoyé", key=f"envoye_{message['id']}"):
					self.marquer_envoye(message)

				if bouton_supprimer.button("Supprimer", key=f"suppr_msg_{message['id']}"):
					self.messagerie.modifier(message["id"], statut="ignoré")
					st.rerun()


	def show_message_libre(self):
		destinataires = [destinataire_maries(self.event_sheet.data)] + [
			destinataire_prestataire(prestataire) for prestataire in self.carnet.prestataires
		]
		par_nom = {destinataire["destinataire"]: destinataire for destinataire in destinataires}

		with st.expander("✍️ Écrire un message libre"):
			with st.form("form_message_libre", clear_on_submit=True):
				choix = st.selectbox("Destinataire", list(par_nom))
				consigne = st.text_area("Que veux-tu lui dire ? (AURORE s'occupe de la formulation)")

				if st.form_submit_button("Rédiger") and consigne:
					nouveau = suggestion(f"libre_{uuid.uuid4().hex[:8]}", "libre", par_nom[choix], {})
					self.rediger(nouveau, f"Ce que le message doit dire : {consigne}")


	def show_envoyes(self):
		envoyes = self.messagerie.par_statut("envoyé")

		if envoyes:
			with st.expander(f"📨 Messages envoyés ({len(envoyes)})"):
				for message in reversed(envoyes):
					st.markdown(f"**{TYPES_MESSAGE[message['type']]}** → {message['destinataire']} · {message['date']}")
					st.caption(message["contenu"])


	def show_messages(self, suggestions):
		self.show_suggestions(suggestions)
		self.show_a_envoyer()
		self.show_message_libre()
		self.show_envoyes()


	def nouvelles_lignes_devis(self, lignes):
		st.session_state.lignes_devis = lignes
		st.session_state.version_lignes += 1


	def accepter_devis(self, devis, montants):
		prestataire = self.carnet.trouver(devis["prestataire_id"])
		poste = (prestataire["poste_budget"] or prestataire["categorie"]) if prestataire else "Wedding planner"

		if poste not in [poste_existant["nom"] for poste_existant in self.budget.postes]:
			self.budget.add_poste(poste, montants["ttc"])

		echeance_solde = lire_date(self.event_sheet.data["date"]) or date.today() + timedelta(days=30)
		factures = [
			(f"Acompte {devis['numero']}", montants["acompte"], date.today() + timedelta(days=7)),
			(f"Solde {devis['numero']}", round(montants["ttc"] - montants["acompte"], 2), echeance_solde)
		]

		for libelle, montant, echeance in factures:
			if montant and not self.budget.facture_existe(libelle):
				self.budget.add_facture(poste, libelle, montant, str(echeance), False)

		if prestataire:
			self.changer_statut_prestataire(prestataire, "Réservé")


	def show_devis_form(self):
		emetteurs = {PLANNER: None} | {prestataire["nom"]: prestataire for prestataire in self.carnet.prestataires}

		with st.expander("➕ Nouveau devis", expanded=not self.carnet_devis.devis):
			emetteur = st.selectbox("Émis par", list(emetteurs))
			prestataire = emetteurs[emetteur]

			if st.button("✨ Proposer les lignes avec AURORE"):
				categorie = prestataire["categorie"] if prestataire else "Wedding planner"

				with st.spinner("AURORE prépare les lignes du devis…"):
					suggestions = self.conversation_agent_object.suggest_devis_lignes(
						emetteur, categorie, self.event_sheet.infos_sans_historique()
					)

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

			if st.button("📄 Créer le devis"):
				lignes = lignes_valides(tableau.to_dict("records"))

				if not lignes:
					st.warning("Ajoute au moins une ligne avec une désignation.")
				else:
					self.carnet_devis.add_devis(
						emetteur,
						prestataire["id"] if prestataire else None,
						self.event_sheet.data["noms"] or "Les mariés",
						lignes, tva, acompte, validite, notes
					)
					self.nouvelles_lignes_devis([])
					st.rerun()


	def show_devis_carte(self, devis):
		montants = totaux(devis)
		numero = devis["numero"]

		with st.container(border=True):
			infos, statut = st.columns([3, 2])
			infos.markdown(f"**{numero}** · {devis['emetteur']} → {devis['destinataire']}")
			infos.caption(
				f"{euros(montants['ttc'])} TTC · acompte {euros(montants['acompte'])} · "
				f"valable jusqu'au {date_validite(devis):%d/%m/%Y}"
			)

			nouveau_statut = statut.selectbox(
				"Statut",
				STATUTS_DEVIS,
				index=STATUTS_DEVIS.index(devis["statut"]),
				key=f"statut_devis_{numero}_{devis['statut']}",
				label_visibility="collapsed"
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
				"📥 Télécharger le PDF",
				data=generer_pdf(devis, self.event_sheet.data),
				file_name=f"{numero}.pdf",
				mime="application/pdf",
				key=f"pdf_{numero}",
				width="stretch"
			)

			if bouton_envoi.button("✉️ Préparer le message d'envoi", key=f"envoi_{numero}", width="stretch"):
				contexte = {**devis, "totaux": montants}
				self.rediger(suggestion(f"envoi_devis_{numero}", "envoi_devis", destinataire_maries(self.event_sheet.data), contexte))

			if bouton_supprimer.button("Supprimer", key=f"suppr_devis_{numero}"):
				self.carnet_devis.supprimer(numero)
				st.rerun()


	def show_devis(self):
		if not self.carnet_devis.devis:
			st.info("Aucun devis pour l'instant.")

		for devis in reversed(self.carnet_devis.devis):
			self.show_devis_carte(devis)

		self.show_devis_form()


	def apres_modif_invites(self):
		st.session_state.version_invites += 1
		st.rerun()


	def show_compteurs_invites(self):
		compteurs = self.liste_invites.compter_par_statut()
		self.show_compteurs(
			{f"{ICONES_INVITE[statut]} {statut}": compteurs[statut] for statut in STATUTS_INVITE}
			| {"👥 Personnes attendues": self.liste_invites.personnes(["Invité", "Confirmé"])}
		)


	def show_import_contacts(self):
		with st.expander("📇 Importer des contacts (.vcf ou .csv)"):
			st.caption("Depuis ton téléphone ou Google Contacts : Exporter → fichier .vcf ou .csv.")
			fichier = st.file_uploader("Fichier de contacts", type=["vcf", "csv"])
			groupe = st.selectbox("Groupe à attribuer", GROUPES)

			if fichier and st.button("Importer"):
				self.liste_invites.importer(lire_contacts(fichier.name, fichier.getvalue()), groupe)
				self.apres_modif_invites()


	def show_table_invites(self):
		st.caption("Modifie directement le tableau. Ajoute une ligne tout en bas, supprime en cochant à gauche.")
		tableau = st.data_editor(
			pd.DataFrame(self.liste_invites.invites, columns=COLONNES_INVITES),
			column_config=CONFIG_COLONNES_INVITES,
			num_rows="dynamic",
			hide_index=True,
			width="stretch",
			key=f"invites_{st.session_state.version_invites}"
		)
		invites = nettoyer(tableau.to_dict("records"))

		if invites != self.liste_invites.invites:
			self.liste_invites.remplacer(invites)
			self.apres_modif_invites()


	def show_redaction_faire_part(self):
		if st.button("✨ Rédiger le faire-part avec AURORE"):
			with st.spinner("AURORE écrit votre faire-part…"):
				self.liste_invites.set_faire_part(
					self.conversation_agent_object.write_faire_part(self.event_sheet.infos_sans_historique())
				)

		faire_part = st.text_area("Texte du faire-part", value=self.liste_invites.faire_part, height=200)

		if faire_part != self.liste_invites.faire_part:
			self.liste_invites.set_faire_part(faire_part)

		if faire_part:
			st.download_button(
				"📥 Télécharger le faire-part (PDF)",
				data=generer_faire_part_pdf(faire_part, self.event_sheet.data),
				file_name="faire-part.pdf",
				mime="application/pdf"
			)


	def show_envoi_faire_parts(self):
		st.subheader("📨 Envoyer les faire-parts")

		if not self.liste_invites.faire_part:
			st.info("Rédige d'abord le texte du faire-part ci-dessus.")
			return

		groupes = st.multiselect("Envoyer à", GROUPES, default=GROUPES)
		selection = [
			invite for invite in self.liste_invites.invites
			if invite["statut"] == "À inviter" and invite["groupe"] in groupes
		]
		st.caption(f"{len(selection)} invité(s) n'ont pas encore reçu leur faire-part.")

		for invite in selection:
			with st.container(border=True):
				st.markdown(f"**{invite['nom']}** · {invite['groupe']}")

				if invite["telephone"] or invite["email"]:
					self.show_boutons_contact(
						invite["telephone"], invite["email"],
						message=message_personnel(invite, self.liste_invites.faire_part), sujet="Faire-part"
					)
				else:
					st.caption("Pas de téléphone ni d'email : ajoute-les dans la liste.")

				if st.button("✅ Marquer comme invité", key=f"invite_{invite['id']}"):
					self.liste_invites.changer_statut(invite["id"], "Invité")
					self.apres_modif_invites()


	def show_recap_traiteur(self):
		recap = self.liste_invites.recap_traiteur()
		self.show_compteurs({
			"🍽️ Couverts confirmés": recap["couverts_confirmes"],
			"⏳ Couverts attendus": recap["couverts_attendus"]
		})

		if recap["regimes"]:
			st.markdown("**Régimes particuliers (invités confirmés)**")

			for regime, nombre_invites in recap["regimes"].items():
				st.markdown(f"- {regime} : {nombre_invites}")

		if recap["allergies"]:
			st.markdown("**Allergies**")

			for nom, allergies in recap["allergies"].items():
				st.markdown(f"- ⚠️ {nom} : {allergies}")

		traiteurs = {prestataire["nom"]: prestataire for prestataire in self.carnet.prestataires if prestataire["categorie"] == "Traiteur"}

		if not traiteurs:
			st.caption("Ajoute ton traiteur dans 🤝 Prestataires pour lui envoyer ce récapitulatif.")
			return

		traiteur = traiteurs[st.selectbox("Traiteur", list(traiteurs))]

		if st.button("✉️ Préparer le message pour le traiteur"):
			cle = f"recap_traiteur_{uuid.uuid4().hex[:8]}"
			self.rediger(suggestion(cle, "recap_traiteur", destinataire_prestataire(traiteur), recap))


	def show_invites(self):
		liste_tab, faire_part_tab, traiteur_tab = st.tabs(["📋 Liste", "💌 Faire-parts", "🍽️ Pour le traiteur"])

		with liste_tab:
			if self.liste_invites.invites:
				self.show_compteurs_invites()

			self.show_import_contacts()
			self.show_table_invites()

		with faire_part_tab:
			self.show_redaction_faire_part()
			self.show_envoi_faire_parts()

		with traiteur_tab:
			self.show_recap_traiteur()


	def show_notification(self, suggestions):
		total = len(suggestions) + len(self.messagerie.par_statut("à envoyer"))

		if total:
			st.info(f"🔔 {total} message(s) à préparer ou à envoyer — voir l'onglet ✉️ Messages")


	def run(self):
		suggestions = self.messagerie.a_preparer(
			detecter_messages(self.event_sheet.data, self.carnet, self.agenda, self.budget)
		)
		self.show_notification(suggestions)

		chat_tab, fiche_tab, invites_tab, prestataires_tab, budget_tab, devis_tab, agenda_tab, messages_tab = st.tabs(
			["💬 Discussion", "💑 Fiche couple", "👥 Invités", "🤝 Prestataires", "💰 Budget", "📄 Devis", "📅 Rendez-vous", "✉️ Messages"]
		)

		text_interaction = st.chat_input(
			"Parle-moi de ton événement !",
			accept_file=False,
			accept_audio=False
			)

		if text_interaction :
			self.conversation_agent_object.ask_llm(text_interaction)
			new_info = self.conversation_agent_object.extract_event_info(self.event_sheet.infos_sans_historique())
			self.event_sheet.update(new_info)

		with chat_tab:
			self.show_discussion_history()

		with fiche_tab:
			self.show_fiche_couple()

		with invites_tab:
			self.show_invites()

		with prestataires_tab:
			self.show_prestataires()

		with budget_tab:
			self.show_budget()

		with agenda_tab:
			self.show_agenda()

		with devis_tab:
			self.show_devis()

		with messages_tab:
			self.show_messages(suggestions)

		self.show_event_sheet()



if __name__ == "__main__":
	user_interface_object = UserInterface()
	user_interface_object.run()








































	# response = ask_llm(user_input)
	# with st.chat_message("user"):
	# 	st.markdown(user_input)

	# with st.chat_message("system"):
	# 	st.markdown(response)


