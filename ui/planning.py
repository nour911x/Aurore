from datetime import datetime

import streamlit as st
from groq import APIError

from config.profils import ORGANISATEUR
from donnees.dossiers import libelle_dossier
from donnees.stockage import premier
from metier.agenda import AUTRE_TYPE, TYPES_RDV, bornes, type_rdv
from metier.jour_j import (
    AUCUNE_TABLE,
    COLONNES_DEROULE,
    ELEMENTS_SALLE,
    FORMES_TABLE,
    TABLE_HONNEUR,
    creer_tables,
    generer_deroule_pdf,
    generer_plan_table_pdf,
    invites_a_placer,
    nettoyer_deroule,
    personnes,
)
from metier.messages import fiche_publique
from metier.rgpd import CATEGORIE_DONNEES_SANTE, recap_anonyme, recap_sans_sante, sante_partageable
from metier.salle import EMPLACEMENTS, MARGE, chevauchements, couleurs_salle, disposer, tables_necessaires
from metier.salle import emplacement as emplacement_dans_la_salle
from textes import CHOIX_TYPE_RDV, date_longue, pluriel
from ui import composants, design
from ui.commun import AUCUN, CONFIG_COLONNES_DEROULE, DELAI_BRIEFING_AUTOMATIQUE, FORMAT_DATE
from ui.contexte import Vue
from ui.habillage import frise_html, plan_salle_html
from ui.salle_3d import salle_3d


class VuePlanning(Vue):
    def afficher_rappels_rdv(self):
        for rdv in self.ctx.rdvs_visibles(self.ctx.agenda.rdvs_proches()):
            date_lisible = datetime.fromisoformat(rdv["date_heure"]).strftime("%d/%m à %H:%M")
            st.info(f"Bientôt : {rdv['titre']} le {date_lisible} avec {rdv['avec']}", icon=":material/event:")


    def generer_briefing(self, rdv):
        if self.ctx.prestataire:
            donnees_evenement = self.ctx.infos_pour_destinataire(self.ctx.prestataire["id"])
            historique, budget, fiche = [], [], fiche_publique(self.ctx.prestataire)
        else:
            fiche = self.ctx.carnet.trouver_par_nom(rdv["avec"])
            besoin_sante = type_rdv(rdv) == "Dégustation" or bool(fiche and fiche["categorie"] == CATEGORIE_DONNEES_SANTE)
            avec_sante = besoin_sante and sante_partageable(self.ctx.fiche_evenement.donnees)
            donnees_evenement = self.ctx.fiche_evenement.infos_sans_historique(avec_sante=avec_sante)
            historique, budget = self.ctx.fiche_evenement.donnees["historique"], self.ctx.budget.resume()

        if self.ctx.liste_invites.invites:
            recap = self.ctx.liste_invites.recap_traiteur()
            avec_sante = "allergies_interdits" in donnees_evenement
            donnees_evenement["invites"] = recap_anonyme(recap) if avec_sante else recap_sans_sante(recap)

        return self.ctx.agent.preparer_briefing(rdv, donnees_evenement, historique, budget, fiche)


    def briefing(self, rdv):
        if self.ctx.prestataire:
            return st.session_state.briefings.get(f"{rdv['titre']}_{rdv['date_heure']}")

        return rdv.get("briefing")


    def preparer_briefing(self, rdv):
        with st.spinner(f"AURORE prépare le briefing de « {rdv['titre']} »…"):
            texte = self.generer_briefing(rdv)

        if self.ctx.prestataire:
            st.session_state.briefings[f"{rdv['titre']}_{rdv['date_heure']}"] = texte
            return

        rdv["briefing"] = texte
        self.ctx.agenda.sauvegarder()


    def briefing_automatique(self, rdv):
        if self.ctx.prestataire or rdv.get("briefing") or bornes(rdv)[0] - datetime.now() > DELAI_BRIEFING_AUTOMATIQUE:
            return

        try:
            self.preparer_briefing(rdv)
        except APIError:
            st.caption("Le briefing automatique n'a pas pu être préparé. Réessayez avec le bouton ci-dessous.")


    def afficher_rdvs(self, lecture_seule=False):
        rdvs = self.ctx.rdvs_visibles(self.ctx.agenda.rdvs_a_venir())

        if not rdvs:
            design.vide("Aucun rendez-vous à venir.")

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
                        on_click=self.ctx.agenda.confirmer, args=(rdv["titre"], rdv["date_heure"], self.ctx.dossier_id)
                    )

                self.briefing_automatique(rdv)
                libelle = "Mettre à jour le briefing" if self.briefing(rdv) else "Préparer le briefing"

                if bouton_briefing.button(libelle, icon=":material/assignment:", key=f"brief_{cle}"):
                    self.preparer_briefing(rdv)

                if not lecture_seule and bouton_supprimer.button("Supprimer", key=f"del_{cle}"):
                    self.ctx.agenda.supprimer_rdv(rdv["titre"], rdv["date_heure"])
                    st.session_state.briefings.pop(cle, None)
                    st.rerun()

                if self.briefing(rdv):
                    with st.expander("Briefing avant le rendez-vous", icon=":material/assignment:", expanded=True):
                        st.markdown(self.briefing(rdv))

        if rdvs:
            st.download_button(
                "Exporter vers mon calendrier (.ics)", icon=":material/download:",
                data=self.ctx.agenda.exporter_ics(rdvs),
                file_name="aurore_rendez_vous.ics",
                mime="text/calendar"
            )

        if self.ctx.outils.avec_outlook and not self.ctx.prestataire and st.button("Envoyer mes rendez-vous vers Outlook", icon=":material/outbox:"):
            with st.spinner("Synchronisation avec Outlook…"):
                nombre_envoyes = self.ctx.outils.synchroniser_outlook()

            st.success(f"{pluriel(nombre_envoyes, 'rendez-vous ajouté', 'rendez-vous ajoutés')} à Outlook.")


    def afficher_rdv_form(self):
        with st.expander("Ajouter un rendez-vous", icon=":material/add:"):
            with st.form("form_rdv", clear_on_submit=True):
                titre = st.text_input("Titre (ex : essayage robe, visite de salle, dégustation)")
                type_choisi = st.selectbox("Type de rendez-vous", [CHOIX_TYPE_RDV, *TYPES_RDV, AUTRE_TYPE])
                jour = st.date_input("Date", format=FORMAT_DATE)
                heure = st.time_input("Heure")
                duree = st.number_input("Durée (minutes)", min_value=15, step=15, value=60)
                lieu = st.text_input("Lieu")

                if self.ctx.prestataire:
                    avec = self.ctx.prestataire["nom"]
                else:
                    noms_prestataires = [AUCUN] + [prestataire["nom"] for prestataire in self.ctx.carnet.prestataires]
                    prestataire_choisi = st.selectbox("Avec quel prestataire", noms_prestataires)
                    autre = st.text_input("Ou avec quelqu'un d'autre (ex : les clients, la témoin)")
                    avec = autre or ("" if prestataire_choisi == AUCUN else prestataire_choisi)

                if st.form_submit_button("Ajouter le rendez-vous") and titre:
                    date_heure = datetime.combine(jour, heure).isoformat()
                    conflit = self.ctx.agenda.ajouter_rdv(titre, date_heure, duree, lieu, avec, None if type_choisi == CHOIX_TYPE_RDV else type_choisi)

                    if conflit and self.ctx.profil != ORGANISATEUR:
                        st.error("Ce créneau est déjà pris dans l'agenda de l'organisateur. Choisissez un autre horaire.", icon=":material/warning:")
                    elif conflit:
                        st.error(
                            f"Conflit avec « {conflit['titre']} »{self.precision_dossier(conflit)} déjà prévu à ce moment-là. Choisissez un autre créneau.",
                            icon=":material/warning:"
                        )
                    else:
                        st.rerun()


    def precision_dossier(self, rdv):
        dossier = self.ctx.dossiers.get(rdv.get("dossier_id"))

        if not dossier or dossier["id"] == self.ctx.dossier_id:
            return ""

        return f" (dossier {libelle_dossier(dossier)})"


    def afficher_agenda(self):
        self.afficher_rappels_rdv()
        self.afficher_rdvs()
        self.afficher_rdv_form()


    def generer_deroule(self):
        reserves = [
            {"nom": prestataire["nom"], "categorie": prestataire["categorie"]}
            for prestataire in self.ctx.carnet.prestataires if prestataire["statut"] == "Réservé"
        ]
        date_evenement = self.ctx.fiche_evenement.donnees["date"] or ""
        rdvs_jour_j = [rdv for rdv in self.ctx.agenda.rdvs if date_evenement and rdv["date_heure"].startswith(date_evenement)]

        with st.spinner("AURORE construit le déroulé de la journée…"):
            deroule = self.ctx.agent.suggerer_deroule(self.ctx.fiche_evenement.infos_pour_prestataire(), reserves, rdvs_jour_j)

        self.ctx.jour_j.definir_deroule(deroule)
        st.session_state["version_deroule"] = st.session_state.get("version_deroule", 0) + 1
        st.rerun()


    def afficher_deroule(self):
        libelle = "Régénérer le déroulé avec AURORE" if self.ctx.jour_j.deroule else "Construire le déroulé avec AURORE"

        if st.button(libelle, icon=":material/auto_awesome:"):
            self.generer_deroule()

        if not self.ctx.jour_j.deroule:
            st.info("AURORE peut proposer le programme heure par heure à partir de la fiche et des prestataires réservés.")

        st.markdown(frise_html(self.ctx.jour_j.deroule), unsafe_allow_html=True)

        with st.expander("Modifier le déroulé", icon=":material/edit:"):
            composants.editer_tableau(
                "deroule", self.ctx.jour_j.deroule, COLONNES_DEROULE, CONFIG_COLONNES_DEROULE,
                nettoyer_deroule, self.ctx.jour_j.definir_deroule
            )

        if self.ctx.jour_j.deroule:
            st.download_button(
                "Télécharger le déroulé (PDF) pour les prestataires", icon=":material/download:",
                data=generer_deroule_pdf(self.ctx.jour_j.deroule, self.ctx.fiche_evenement.donnees),
                file_name="deroule-jour-j.pdf",
                mime="application/pdf"
            )


    def invites_prevus(self, total_personnes):
        return max(total_personnes, int(self.ctx.fiche_evenement.donnees["nombre_invites"] or 0))


    def afficher_amenagement(self, total_personnes):
        salle = self.ctx.jour_j.salle

        with st.expander("Aménager la salle", icon=":material/construction:", expanded=not salle["tables"]):
            with st.form("form_salle"):
                honneur = premier(salle["tables"], nom=TABLE_HONNEUR)
                ordinaires = [table for table in salle["tables"] if table["nom"] != TABLE_HONNEUR]
                modele = ordinaires[0] if ordinaires else {"forme": FORMES_TABLE[0], "places": 8}
                gauche, droite = st.columns(2)
                invites = gauche.number_input("Nombre d'invités", min_value=0, max_value=1000, value=self.invites_prevus(total_personnes))
                nombre = droite.number_input(
                    "Nombre de tables", min_value=0, max_value=60, value=len(ordinaires), help="0 : calculé d'après le nombre d'invités."
                )
                gauche, droite = st.columns(2)
                forme = gauche.selectbox("Forme des tables", FORMES_TABLE, index=FORMES_TABLE.index(modele["forme"]))
                places = droite.number_input("Places par table", min_value=2, max_value=20, value=modele["places"])
                gauche, droite = st.columns(2)
                places_honneur = gauche.number_input(
                    "Places à la table d'honneur", min_value=0, max_value=30,
                    value=honneur["places"] if honneur else 0 if salle["tables"] else 10, help="0 : pas de table d'honneur."
                )
                elements = droite.multiselect("Dans la salle", ELEMENTS_SALLE, default=salle["elements"] or ELEMENTS_SALLE[:3])

                if st.form_submit_button("Créer le plan de la salle", type="primary"):
                    nombre = nombre or min(60, tables_necessaires(invites, places, places_honneur))
                    self.ctx.jour_j.amenager(creer_tables(nombre, places, forme, places_honneur), elements)
                    st.session_state["version_placement"] = st.session_state.get("version_placement", 0) + 1
                    st.rerun()


    def proposer_placement(self, a_placer):
        invites = [
            {"id": invite["id"], "nom": invite["nom"], "groupe": invite["groupe"], "personnes": personnes(invite)}
            for invite in a_placer
        ]
        tables = [{"nom": table["nom"], "places": table["places"]} for table in self.ctx.jour_j.salle["tables"]]

        with st.spinner("AURORE réfléchit au plan de table…"):
            souhaits = self.ctx.agent.suggerer_placement(invites, tables, self.ctx.fiche_evenement.infos_pour_prestataire())

        if not self.ctx.jour_j.placer(souhaits, self.ctx.liste_invites.invites):
            st.warning("AURORE n'a pas réussi à proposer un placement cette fois-ci. Réessaie, ou place les invités à la main ci-dessous.")
            return

        st.session_state["version_placement"] = st.session_state.get("version_placement", 0) + 1
        st.rerun()


    def lignes_placement(self, a_placer):
        return [
            {
                "id": invite["id"], "nom": invite["nom"], "groupe": invite["groupe"], "personnes": personnes(invite),
                "table": self.ctx.jour_j.salle["placement"].get(invite["id"], AUCUNE_TABLE)
            }
            for invite in a_placer
        ]


    def afficher_placement(self, a_placer):
        noms_tables = [AUCUNE_TABLE] + [table["nom"] for table in self.ctx.jour_j.salle["tables"]]
        config = {
            "id": None,
            "nom": st.column_config.TextColumn("Invité", disabled=True),
            "groupe": st.column_config.TextColumn("Groupe", disabled=True),
            "personnes": st.column_config.NumberColumn("Personnes", disabled=True),
            "table": st.column_config.SelectboxColumn("Table", options=noms_tables, required=True)
        }

        with st.expander("Modifier le placement", icon=":material/edit:"):
            composants.editer_tableau(
                "placement", self.lignes_placement(a_placer), ["id", "nom", "groupe", "personnes", "table"], config,
                lambda lignes: [{**ligne, "table": ligne["table"] or AUCUNE_TABLE} for ligne in lignes],
                lambda lignes: self.ctx.jour_j.placer({ligne["id"]: ligne["table"] for ligne in lignes}, self.ctx.liste_invites.invites),
                num_rows="fixed"
            )


    def afficher_tables(self, repartition):
        colonnes = st.columns(3)

        for index, (table, invites) in enumerate(repartition.items()):
            places = next(ligne["places"] for ligne in self.ctx.jour_j.salle["tables"] if ligne["nom"] == table)
            regimes = [invite["regime"] for invite in invites if invite["regime"] != "Aucun"]

            with colonnes[index % 3].container(border=True):
                st.markdown(f"**{table}** · {sum(personnes(invite) for invite in invites)}/{places}")
                st.caption(", ".join(invite["nom"] for invite in invites) or "Personne pour l'instant")

                if regimes:
                    st.caption(":material/restaurant: " + ", ".join(sorted(set(regimes))))


    def afficher_plan_salle(self):
        a_placer = invites_a_placer(self.ctx.liste_invites.invites)
        total = sum(personnes(invite) for invite in a_placer)
        self.afficher_amenagement(total)

        if not self.ctx.jour_j.salle["tables"]:
            st.info("Commence par aménager la salle : nombre de tables, forme, table d'honneur.")
            return

        repartition = self.ctx.jour_j.par_table(self.ctx.liste_invites.invites)
        non_places = self.ctx.jour_j.non_places(self.ctx.liste_invites.invites)
        design.indicateurs({
            ":material/table_restaurant: Tables": len(self.ctx.jour_j.salle["tables"]),
            ":material/chair: Places": sum(table["places"] for table in self.ctx.jour_j.salle["tables"]),
            ":material/groups: Personnes": total,
            "Non placés": len(non_places)
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
            self.afficher_placement(a_placer)
            self.afficher_tables(repartition)
            st.download_button(
                "Télécharger le plan de table (PDF)", icon=":material/download:",
                data=generer_plan_table_pdf(repartition, self.ctx.fiche_evenement.donnees),
                file_name="plan-de-table.pdf",
                mime="application/pdf"
            )


    def disposition_salle(self, repartition):
        return disposer(self.ctx.jour_j.salle, repartition)


    def deplacer_element(self):
        deplacement = st.session_state["salle_3d"].deplacement

        try:
            self.ctx.jour_j.placer_element(deplacement["nom"], deplacement["x"], deplacement["y"])
        except (KeyError, TypeError, ValueError):
            st.session_state.deplacement_refuse = True


    def afficher_emplacements(self, disposition):
        with st.expander("Placer un élément sans la souris", icon=":material/place:"):
            with st.form("form_emplacement"):
                gauche, droite = st.columns(2)
                nom = gauche.selectbox("Élément", [objet["nom"] for objet in disposition["objets"]])
                choix = droite.selectbox("Emplacement", list(EMPLACEMENTS))

                if st.form_submit_button("Placer"):
                    self.ctx.jour_j.placer_element(nom, *emplacement_dans_la_salle(disposition, nom, choix))
                    st.rerun()


    def afficher_couleurs_salle(self, couleurs):
        with st.expander("Couleurs de la décoration", icon=":material/palette:"):
            with st.form("form_couleurs_salle"):
                gauche, droite = st.columns(2)
                nappe = gauche.color_picker("Nappes", couleurs["nappe"])
                accent = droite.color_picker("Fleurs et détails", couleurs["accent"])

                if st.form_submit_button("Appliquer"):
                    self.ctx.jour_j.definir_couleurs({"nappe": nappe, "accent": accent})
                    st.rerun()


    def afficher_controle_salle(self, disposition):
        salle = self.ctx.jour_j.salle
        places = sum(table["places"] for table in salle["tables"])
        a_placer = invites_a_placer(self.ctx.liste_invites.invites)
        attendus = self.invites_prevus(sum(personnes(invite) for invite in a_placer))
        design.indicateurs({"Tables": len(salle["tables"]), "Places": places, "Invités prévus": attendus}, {"Places"} if places < attendus else ())

        if places < attendus:
            st.warning(f"Il manque {pluriel(attendus - places, 'place')} pour asseoir tout le monde.", icon=":material/chair:")

        conflits = [f"{premier_nom} et {second_nom}" for premier_nom, second_nom in chevauchements(disposition)]

        if conflits:
            st.warning(f"Ces éléments se chevauchent : {', '.join(conflits)}.", icon=":material/warning:")

        if st.session_state.pop("deplacement_refuse", False):
            st.error("Ce déplacement n'a pas pu être enregistré.", icon=":material/error:")


    def afficher_salle_3d(self):
        jour_j = self.ctx.jour_j
        self.afficher_amenagement(sum(personnes(invite) for invite in invites_a_placer(self.ctx.liste_invites.invites)))

        if not jour_j.salle["tables"]:
            design.vide("Aménagez la salle pour la voir en 3D.")
            return

        disposition = self.disposition_salle(jour_j.par_table(self.ctx.liste_invites.invites))
        couleurs = couleurs_salle(jour_j.salle, self.ctx.inspiration.moodboard)
        self.afficher_controle_salle(disposition)
        salle_3d(
            key="salle_3d", data={**disposition, "couleurs": couleurs, "marge": MARGE},
            on_deplacement_change=self.deplacer_element
        )
        st.caption("Chaise dorée : place occupée d'après le plan de table. Les positions sont aussi celles du Plan de salle.")
        self.afficher_couleurs_salle(couleurs)
        self.afficher_emplacements(disposition)

        if jour_j.salle["positions"] and st.button("Revenir à la disposition automatique", icon=":material/restart_alt:"):
            jour_j.reinitialiser_positions()
            st.rerun()
