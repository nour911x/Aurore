import streamlit as st
from datetime import datetime
from groq import APIError

from donnees.dossiers import libelle_dossier
from metier.agenda import AUTRE_TYPE, TYPES_RDV, bornes, type_rdv
from metier.devis import date_lisible
from metier.jour_j import AUCUNE_TABLE, COLONNES_DEROULE, ELEMENTS_SALLE, FORMES_TABLE, creer_tables, generer_deroule_pdf, generer_plan_table_pdf, invites_a_placer, nettoyer_deroule, personnes
from metier.messages import fiche_publique
from metier.rgpd import CATEGORIE_DONNEES_SANTE, recap_anonyme, recap_sans_sante, sante_partageable
from textes import CHOIX_TYPE_RDV, date_longue, pluriel
from ui.commun import AUCUN, CONFIG_COLONNES_DEROULE, DELAI_BRIEFING_AUTOMATIQUE
from ui.habillage import disposition_salle, frise_html, plan_salle_html, salle_3d_html


class VuePlanning:
	def rdvs_visibles(self, rdvs):
		visibles = self.outils.rdvs_visibles()
		return [rdv for rdv in rdvs if rdv in visibles]


	def show_rappels_rdv(self):
		for rdv in self.rdvs_visibles(self.agenda.rdvs_proches()):
			date_lisible = datetime.fromisoformat(rdv["date_heure"]).strftime("%d/%m à %H:%M")
			st.info(f"Bientôt : {rdv['titre']} le {date_lisible} avec {rdv['avec']}", icon=":material/event:")


	def generer_briefing(self, rdv):
		if self.prestataire:
			event_data = self.infos_pour_destinataire(self.prestataire["id"])
			historique, budget, fiche = [], [], fiche_publique(self.prestataire)
		else:
			fiche = self.carnet.trouver_par_nom(rdv["avec"])
			besoin_sante = type_rdv(rdv) == "Dégustation" or bool(fiche and fiche["categorie"] == CATEGORIE_DONNEES_SANTE)
			avec_sante = besoin_sante and sante_partageable(self.event_sheet.data)
			event_data = self.event_sheet.infos_sans_historique(avec_sante=avec_sante)
			historique, budget = self.event_sheet.data["historique"], self.budget.resume()

		if self.liste_invites.invites:
			recap = self.liste_invites.recap_traiteur()
			avec_sante = "allergies_interdits" in event_data
			event_data["invites"] = recap_anonyme(recap) if avec_sante else recap_sans_sante(recap)

		return self.conversation_agent_object.prepare_briefing(rdv, event_data, historique, budget, fiche)


	def briefing(self, rdv):
		if self.prestataire:
			return st.session_state.briefings.get(f"{rdv['titre']}_{rdv['date_heure']}")

		return rdv.get("briefing")


	def preparer_briefing(self, rdv):
		with st.spinner(f"AURORE prépare le briefing de « {rdv['titre']} »…"):
			texte = self.generer_briefing(rdv)

		if self.prestataire:
			st.session_state.briefings[f"{rdv['titre']}_{rdv['date_heure']}"] = texte
			return

		rdv["briefing"] = texte
		self.agenda.save()


	def briefing_automatique(self, rdv):
		if self.prestataire or rdv.get("briefing") or bornes(rdv)[0] - datetime.now() > DELAI_BRIEFING_AUTOMATIQUE:
			return

		try:
			self.preparer_briefing(rdv)
		except APIError:
			st.caption("Le briefing automatique n'a pas pu être préparé. Réessayez avec le bouton ci-dessous.")


	def show_rdvs(self, lecture_seule=False):
		rdvs = self.rdvs_visibles(self.agenda.rdvs_a_venir())

		if not rdvs:
			st.info("Aucun rendez-vous à venir.")

		for rdv in rdvs:
			debut = datetime.fromisoformat(rdv["date_heure"])
			cle = f"{rdv['titre']}_{rdv['date_heure']}"
			confirmation = ":green[:material/check_circle: confirmé]" if rdv.get("confirme") else ":orange[:material/hourglass_top: à confirmer]"

			with st.container(border=True):
				st.markdown(
					f"**{rdv['titre']}** · :gray[{type_rdv(rdv)}] — {date_longue(debut)} à {debut:%H:%M} "
					f"({rdv['duree_minutes']} min)" + (f" · {confirmation}" if rdv["avec"] else "")
				)
				st.markdown(f":material/location_on: {rdv['lieu'] or 'Lieu à préciser'} · :material/person: {rdv['avec'] or '—'}")

				bouton_briefing, bouton_confirmer, bouton_supprimer = st.columns([3, 2, 1])

				if rdv["avec"] and not rdv.get("confirme") and not lecture_seule:
					bouton_confirmer.button(
						"Marquer confirmé", key=f"confirme_{cle}", icon=":material/check:",
						on_click=self.agenda.confirmer, args=(rdv["titre"], rdv["date_heure"], self.dossier_id)
					)

				self.briefing_automatique(rdv)
				libelle = "Mettre à jour le briefing" if self.briefing(rdv) else "Préparer le briefing"

				if bouton_briefing.button(libelle, icon=":material/assignment:", key=f"brief_{cle}"):
					self.preparer_briefing(rdv)

				if not lecture_seule and bouton_supprimer.button("Supprimer", key=f"del_{cle}"):
					self.agenda.supprimer_rdv(rdv["titre"], rdv["date_heure"])
					st.session_state.briefings.pop(cle, None)
					st.rerun()

				if self.briefing(rdv):
					with st.expander("Briefing avant le rendez-vous", icon=":material/assignment:", expanded=True):
						st.markdown(self.briefing(rdv))

		if rdvs:
			st.download_button(
				"Exporter vers mon calendrier (.ics)", icon=":material/download:",
				data=self.agenda.export_ics(rdvs),
				file_name="aurore_rendez_vous.ics",
				mime="text/calendar"
			)

		if self.outils.avec_outlook and not self.prestataire and st.button("Envoyer mes rendez-vous vers Outlook", icon=":material/outbox:"):
			with st.spinner("Synchronisation avec Outlook…"):
				nombre_envoyes = self.outils.synchroniser_outlook()

			st.success(f"{pluriel(nombre_envoyes, 'rendez-vous ajouté', 'rendez-vous ajoutés')} à Outlook.")


	def show_rdv_form(self):
		with st.expander("Ajouter un rendez-vous", icon=":material/add:"):
			with st.form("form_rdv", clear_on_submit=True):
				titre = st.text_input("Titre (ex : essayage robe, visite de salle, dégustation)")
				type_choisi = st.selectbox("Type de rendez-vous", [CHOIX_TYPE_RDV, *TYPES_RDV, AUTRE_TYPE])
				jour = st.date_input("Date")
				heure = st.time_input("Heure")
				duree = st.number_input("Durée (minutes)", min_value=15, step=15, value=60)
				lieu = st.text_input("Lieu")

				if self.prestataire:
					avec = self.prestataire["nom"]
				else:
					noms_prestataires = [AUCUN] + [prestataire["nom"] for prestataire in self.carnet.prestataires]
					prestataire_choisi = st.selectbox("Avec quel prestataire", noms_prestataires)
					autre = st.text_input("Ou avec quelqu'un d'autre (ex : les clients, la témoin)")
					avec = autre or ("" if prestataire_choisi == AUCUN else prestataire_choisi)

				if st.form_submit_button("Ajouter le rendez-vous") and titre:
					date_heure = datetime.combine(jour, heure).isoformat()
					conflit = self.agenda.add_rdv(titre, date_heure, duree, lieu, avec, None if type_choisi == CHOIX_TYPE_RDV else type_choisi)

					if conflit and self.profil != "Wedding planner":
						st.error("Ce créneau est déjà pris dans l'agenda de l'organisateur. Choisissez un autre horaire.", icon=":material/warning:")
					elif conflit:
						st.error(f"Conflit avec « {conflit['titre']} »{self.precision_dossier(conflit)} déjà prévu à ce moment-là. Choisissez un autre créneau.", icon=":material/warning:")
					else:
						st.rerun()


	def precision_dossier(self, rdv):
		dossier = self.dossiers.get(rdv.get("dossier_id"))

		if not dossier or dossier["id"] == self.dossier_id:
			return ""

		return f" (dossier {libelle_dossier(dossier)})"


	def show_agenda(self):
		self.show_rappels_rdv()
		self.show_rdvs()
		self.show_rdv_form()


	def generer_deroule(self):
		reserves = [
			{"nom": prestataire["nom"], "categorie": prestataire["categorie"]}
			for prestataire in self.carnet.prestataires if prestataire["statut"] == "Réservé"
		]
		date_evenement = self.event_sheet.data["date"] or ""
		rdvs_jour_j = [rdv for rdv in self.agenda.rdvs if date_evenement and rdv["date_heure"].startswith(date_evenement)]

		with st.spinner("AURORE construit le déroulé de la journée…"):
			deroule = self.conversation_agent_object.suggest_deroule(self.event_sheet.infos_pour_prestataire(), reserves, rdvs_jour_j)

		self.jour_j.set_deroule(deroule)
		st.session_state["version_deroule"] = st.session_state.get("version_deroule", 0) + 1
		st.rerun()


	def show_deroule(self):
		libelle = "Régénérer le déroulé avec AURORE" if self.jour_j.deroule else "Construire le déroulé avec AURORE"

		if st.button(libelle, icon=":material/auto_awesome:"):
			self.generer_deroule()

		if not self.jour_j.deroule:
			st.info("AURORE peut proposer le programme heure par heure à partir de la fiche et des prestataires réservés.")

		st.markdown(frise_html(self.jour_j.deroule), unsafe_allow_html=True)

		with st.expander("Modifier le déroulé", icon=":material/edit:"):
			self.editer_tableau(
				"deroule", self.jour_j.deroule, COLONNES_DEROULE, CONFIG_COLONNES_DEROULE,
				nettoyer_deroule, self.jour_j.set_deroule
			)

		if self.jour_j.deroule:
			st.download_button(
				"Télécharger le déroulé (PDF) pour les prestataires", icon=":material/download:",
				data=generer_deroule_pdf(self.jour_j.deroule, self.event_sheet.data),
				file_name="deroule-jour-j.pdf",
				mime="application/pdf"
			)


	def show_amenagement(self, total_personnes):
		with st.expander("Aménager la salle", icon=":material/construction:", expanded=not self.jour_j.salle["tables"]):
			with st.form("form_salle"):
				gauche, milieu, droite = st.columns(3)
				forme = gauche.selectbox("Forme des tables", FORMES_TABLE)
				places = milieu.number_input("Places par table", min_value=2, max_value=20, value=8)
				places_honneur = droite.number_input("Table d'honneur (places, 0 = aucune)", min_value=0, max_value=30, value=10)
				suggestion_tables = max(1, -(-max(total_personnes - places_honneur, 0) // places))
				nombre = st.number_input("Nombre de tables", min_value=1, max_value=60, value=suggestion_tables)
				elements = st.multiselect("Dans la salle", ELEMENTS_SALLE, default=self.jour_j.salle["elements"] or ELEMENTS_SALLE[:3])

				if st.form_submit_button("Créer le plan de la salle"):
					self.jour_j.amenager(creer_tables(nombre, places, forme, places_honneur), elements)
					st.session_state["version_placement"] = st.session_state.get("version_placement", 0) + 1
					st.rerun()


	def proposer_placement(self, a_placer):
		invites = [
			{"id": invite["id"], "nom": invite["nom"], "groupe": invite["groupe"], "personnes": personnes(invite)}
			for invite in a_placer
		]
		tables = [{"nom": table["nom"], "places": table["places"]} for table in self.jour_j.salle["tables"]]

		with st.spinner("AURORE réfléchit au plan de table…"):
			souhaits = self.conversation_agent_object.suggest_placement(invites, tables, self.event_sheet.infos_pour_prestataire())

		if not self.jour_j.placer(souhaits, self.liste_invites.invites):
			st.warning("AURORE n'a pas réussi à proposer un placement cette fois-ci. Réessaie, ou place les invités à la main ci-dessous.")
			return

		st.session_state["version_placement"] = st.session_state.get("version_placement", 0) + 1
		st.rerun()


	def lignes_placement(self, a_placer):
		return [
			{
				"id": invite["id"], "nom": invite["nom"], "groupe": invite["groupe"], "personnes": personnes(invite),
				"table": self.jour_j.salle["placement"].get(invite["id"], AUCUNE_TABLE)
			}
			for invite in a_placer
		]


	def show_placement(self, a_placer):
		noms_tables = [AUCUNE_TABLE] + [table["nom"] for table in self.jour_j.salle["tables"]]
		config = {
			"id": None,
			"nom": st.column_config.TextColumn("Invité", disabled=True),
			"groupe": st.column_config.TextColumn("Groupe", disabled=True),
			"personnes": st.column_config.NumberColumn("Personnes", disabled=True),
			"table": st.column_config.SelectboxColumn("Table", options=noms_tables, required=True)
		}

		with st.expander("Modifier le placement", icon=":material/edit:"):
			self.editer_tableau(
				"placement", self.lignes_placement(a_placer), ["id", "nom", "groupe", "personnes", "table"], config,
				lambda lignes: [{**ligne, "table": ligne["table"] or AUCUNE_TABLE} for ligne in lignes],
				lambda lignes: self.jour_j.placer({ligne["id"]: ligne["table"] for ligne in lignes}, self.liste_invites.invites),
				num_rows="fixed"
			)


	def show_tables(self, repartition):
		colonnes = st.columns(3)

		for index, (table, invites) in enumerate(repartition.items()):
			places = next(ligne["places"] for ligne in self.jour_j.salle["tables"] if ligne["nom"] == table)
			regimes = [invite["regime"] for invite in invites if invite["regime"] != "Aucun"]

			with colonnes[index % 3].container(border=True):
				st.markdown(f"**{table}** · {sum(personnes(invite) for invite in invites)}/{places}")
				st.caption(", ".join(invite["nom"] for invite in invites) or "Personne pour l'instant")

				if regimes:
					st.caption(":material/restaurant: " + ", ".join(sorted(set(regimes))))


	def show_plan_salle(self):
		a_placer = invites_a_placer(self.liste_invites.invites)
		total = sum(personnes(invite) for invite in a_placer)
		self.show_amenagement(total)

		if not self.jour_j.salle["tables"]:
			st.info("Commence par aménager la salle : nombre de tables, forme, table d'honneur.")
			return

		repartition = self.jour_j.par_table(self.liste_invites.invites)
		non_places = self.jour_j.non_places(self.liste_invites.invites)
		self.show_compteurs({
			":material/table_restaurant: Tables": len(self.jour_j.salle["tables"]),
			":material/chair: Places": sum(table["places"] for table in self.jour_j.salle["tables"]),
			":material/groups: Personnes": total,
			"⏳ Non placés": len(non_places)
		})

		if not a_placer:
			st.caption("Ajoutez des invités dans l'onglet Invités pour faire le plan de table.")
		elif st.button("Proposer le plan de table avec AURORE", icon=":material/auto_awesome:"):
			self.proposer_placement(a_placer)

		if non_places and len(non_places) < len(a_placer):
			st.warning("Pas encore placés : " + ", ".join(invite["nom"] for invite in non_places))

		st.markdown(plan_salle_html(self.disposition_salle(repartition)), unsafe_allow_html=True)
		st.caption("Survole une table pour voir qui y est assis.")

		if a_placer:
			self.show_placement(a_placer)
			self.show_tables(repartition)
			st.download_button(
				"Télécharger le plan de table (PDF)", icon=":material/download:",
				data=generer_plan_table_pdf(repartition, self.event_sheet.data),
				file_name="plan-de-table.pdf",
				mime="application/pdf"
			)


	def disposition_salle(self, repartition):
		return disposition_salle(self.jour_j.salle["tables"], repartition, self.jour_j.salle["elements"])


	def show_salle_3d(self):
		if not self.jour_j.salle["tables"]:
			st.info("Aménagez d'abord la salle dans Plan de salle : la 3D est construite à partir du plan.")
			return

		palette = [couleur["hex"] for couleur in self.inspiration.moodboard.get("couleurs", [])]
		st.caption(
			"La salle est construite à partir de ton plan de salle, aux couleurs du moodboard."
			if palette else "Créez le moodboard dans Inspiration & galerie pour habiller la salle à vos couleurs."
		)
		disposition = self.disposition_salle(self.jour_j.par_table(self.liste_invites.invites))
		st.iframe(salle_3d_html(disposition, palette), height=620)
