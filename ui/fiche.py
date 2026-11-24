from datetime import date

import streamlit as st

from config.evenements import CHAMPS_SPECIFIQUES, TYPES_EVENEMENT, champs_masques, cle_type, type_du_dossier
from config.profils import ORGANISATEUR
from donnees.dossiers import libelle_dossier
from donnees.dossiers import supprimer as supprimer_dossier
from metier.devis import date_lisible
from metier.invites import entier
from metier.rgpd import PERIMETRES_IMAGE, TEXTE_CONSENTEMENT_SANTE, consentement, exporter
from textes import CHAMPS_LISTES, SOURCES_ECHANGE, formater_nom
from ui.commun import FORMAT_DATE, OUI_NON, lire_date, personnes_du_dossier, texte_vers_liste
from ui.documents import nettoyer_index


class VueFiche:
    def afficher_type_evenement(self):
        donnees = self.fiche_evenement.donnees
        actuel = cle_type(donnees["type_evenement"])
        version = st.session_state.get("version_type", 0)
        choix = st.segmented_control(
            "Type d'événement", list(TYPES_EVENEMENT), default=actuel,
            format_func=lambda cle: TYPES_EVENEMENT[cle]["libelle"], key=f"type_{self.dossier_id}_{actuel}_{version}"
        )

        if not choix or choix == actuel:
            return

        masques = champs_masques(donnees, choix)

        with st.container(border=True):
            st.warning(
                f"Passer ce dossier de « {TYPES_EVENEMENT[actuel]['libelle']} » à « {TYPES_EVENEMENT[choix]['libelle']} » ?",
                icon=":material/swap_horiz:"
            )

            if masques:
                st.caption(
                    f"Ces champs seront masqués, pas supprimés : ils réapparaîtront si vous revenez au type "
                    f"{TYPES_EVENEMENT[actuel]['libelle']}. {', '.join(masques)}."
                )

            confirmer, annuler = st.columns(2)

            if confirmer.button("Confirmer le changement", icon=":material/check:", type="primary"):
                self.fiche_evenement.changer_type(choix)
                st.rerun()

            if annuler.button("Annuler", icon=":material/close:"):
                st.session_state.version_type = version + 1
                st.rerun()


    @staticmethod
    def champ_specifique(conteneur, cle, valeur):
        libelle, genre, aide = CHAMPS_SPECIFIQUES[cle]

        if genre == "texte":
            return conteneur.text_input(libelle, value=valeur or "", help=aide) or None

        if genre == "nombre":
            return conteneur.number_input(libelle, min_value=0, step=1, value=entier(valeur) or None, help=aide)

        if genre == "date":
            jour = conteneur.date_input(libelle, value=lire_date(valeur), help=aide, format=FORMAT_DATE)
            return str(jour) if jour else None

        if genre == "oui_non":
            choix = conteneur.selectbox(libelle, list(OUI_NON), index=list(OUI_NON.values()).index(valeur if isinstance(valeur, bool) else None), help=aide)
            return OUI_NON[choix]

        return texte_vers_liste(conteneur.text_area(libelle, value=", ".join(valeur), height=68, help=aide))


    def afficher_fiche_form(self):
        donnees = self.fiche_evenement.donnees
        champs = type_du_dossier(donnees)["champs"]
        simples = [cle for cle in champs if CHAMPS_SPECIFIQUES[cle][1] != "liste"]
        listes_du_type = [cle for cle in champs if CHAMPS_SPECIFIQUES[cle][1] == "liste"]

        with st.form("form_fiche"):
            gauche, droite = st.columns(2)
            noms = gauche.text_input(type_du_dossier(donnees)["personnes"], value=donnees["noms"] or "")
            lieu = droite.text_input("Lieu", value=donnees["lieu"] or "")
            telephone = gauche.text_input("Téléphone du client", value=donnees["telephone"] or "")
            email = droite.text_input("Email du client", value=donnees["email"] or "")
            date_evenement = gauche.date_input("Date de l'événement", value=lire_date(donnees["date"]), format=FORMAT_DATE)
            theme = droite.text_input("Thème", value=donnees["theme"] or "")
            budget = gauche.number_input("Budget (€)", min_value=0, step=500, value=int(donnees["budget"]) if donnees["budget"] else None)
            invites = droite.number_input("Nombre d'invités", min_value=0, step=5, value=int(donnees["nombre_invites"]) if donnees["nombre_invites"] else None)
            colonnes = st.columns(2)
            specifiques = {
                cle: self.champ_specifique(colonnes[index % 2], cle, donnees[cle])
                for index, cle in enumerate(simples)
            }

            st.caption("Pour les listes, sépare les éléments par des virgules.")
            listes = {
                cle: st.text_area(label, value=", ".join(donnees[cle]), height=68)
                for cle, label in CHAMPS_LISTES.items()
            }
            specifiques |= {cle: self.champ_specifique(st, cle, donnees[cle]) for cle in listes_du_type}

            if st.form_submit_button("Enregistrer la fiche", icon=":material/save:"):
                nouvelle_fiche = {
                    **specifiques,
                    "noms": noms or None,
                    "telephone": telephone or None,
                    "email": email or None,
                    "date": str(date_evenement) if date_evenement else None,
                    "lieu": lieu or None,
                    "budget": budget,
                    "nombre_invites": invites,
                    "theme": theme or None
                }

                for cle, texte in listes.items():
                    nouvelle_fiche[cle] = texte_vers_liste(texte)

                self.fiche_evenement.remplacer(nouvelle_fiche)
                st.rerun()


    def afficher_historique(self):
        st.subheader(":material/history: Historique des échanges")

        if self.agent.lire_historique() and st.button("Ajouter un résumé de la discussion avec AURORE", icon=":material/summarize:"):
                with st.spinner("AURORE résume la discussion…"):
                    resume = self.agent.resumer_conversation()

                self.fiche_evenement.ajouter_echange("Discussion avec AURORE", resume)
                st.rerun()

        with st.expander("Noter un échange (rendez-vous, appel, message…)", icon=":material/add:"):
            with st.form("form_echange", clear_on_submit=True):
                source = st.selectbox("Type d'échange", SOURCES_ECHANGE)
                resume = st.text_area("Ce qui a été dit ou décidé")

                if st.form_submit_button("Ajouter à l'historique") and resume:
                    self.fiche_evenement.ajouter_echange(source, resume)
                    st.rerun()

        historique = self.fiche_evenement.donnees["historique"]

        if not historique:
            st.caption("Aucun échange enregistré pour l'instant.")

        for echange in reversed(historique):
            with st.container(border=True):
                date_lisible = date.fromisoformat(echange["date"]).strftime("%d/%m/%Y")
                st.markdown(f"**{echange['source']}** · {date_lisible}")
                st.markdown(echange["resume"])


    def afficher_consentement_sante(self):
        donnees = self.fiche_evenement.donnees
        accord = donnees["consentement_sante"] or {}
        accorde = st.toggle(TEXTE_CONSENTEMENT_SANTE, value=bool(accord.get("accorde")), key=f"sante_{self.dossier_id}_{accord.get('accorde')}")

        if accorde != bool(accord.get("accorde")):
            self.fiche_evenement.definir_consentement("consentement_sante", consentement(accorde))
            st.rerun()

        if accord:
            st.caption(f"{'Accordé' if accord['accorde'] else 'Retiré'} le {date_lisible(accord['date'])}.")

        if donnees["allergies_interdits"] and not accorde:
            st.warning(
                "Des allergies sont notées sans l'accord du client : elles restent visibles par vous seul·e, "
                "ne sont envoyées ni aux prestataires ni à l'IA.", icon=":material/lock:"
            )


    def afficher_consentements_image(self):
        consentements = self.fiche_evenement.donnees["droit_image"]

        for index, element in enumerate(consentements):
            texte, retirer = st.columns([5, 1], vertical_alignment="center")
            texte.markdown(f"**{element['personne']}** · {element['perimetre']} · :gray[recueilli le {date_lisible(element['date'])}]")

            if self.profil == ORGANISATEUR and retirer.button("Retirer", key=f"retirer_image_{index}", type="tertiary"):
                self.fiche_evenement.definir_consentement("droit_image", consentements[:index] + consentements[index + 1:])
                st.rerun()

        if not consentements:
            st.caption("Aucun consentement de droit à l'image enregistré : seules les photos de décor sont publiables.")

        if self.profil != ORGANISATEUR:
            return

        with st.form(f"form_droit_image_{self.dossier_id}", clear_on_submit=True):
            personnes = personnes_du_dossier(self.fiche_evenement.donnees)
            gauche, milieu, droite = st.columns([2, 2, 1])
            personne = gauche.selectbox("Personne", personnes + ["Autre (préciser)"]) if personnes else "Autre (préciser)"
            autre = gauche.text_input("Nom") if not personnes else ""
            perimetre = milieu.selectbox("Périmètre accepté", PERIMETRES_IMAGE, index=len(PERIMETRES_IMAGE) - 1)
            jour = droite.date_input("Date", value=date.today(), format=FORMAT_DATE)
            precision = st.text_input("Si « Autre », nom de la personne") if personnes else ""

            if st.form_submit_button("Enregistrer le consentement", icon=":material/verified_user:"):
                nom = formater_nom(autre or precision if personne == "Autre (préciser)" else personne)

                if nom:
                    autres = [element for element in consentements if element["personne"] != nom]
                    self.fiche_evenement.definir_consentement(
                        "droit_image", autres + [{"personne": nom, "perimetre": perimetre, "date": str(jour)}]
                    )
                    st.rerun()


    def retirer_dossier(self):
        supprimer_dossier(self.dossier_id)
        nettoyer_index()

        for cle in [cle for cle in st.session_state if self.dossier_id in str(cle)]:
            del st.session_state[cle]

        st.session_state.dossier_actif = None
        self.agenda.charger()


    def afficher_donnees_client(self):
        with st.expander("Données personnelles du client (RGPD)", icon=":material/shield_person:"):
            st.download_button(
                "Exporter toutes les données de ce client (JSON)", icon=":material/download:",
                data=exporter(self.dossier_id), file_name=f"aurore-dossier-{self.dossier_id}.json", mime="application/json"
            )
            st.divider()
            st.markdown("**Supprimer ce dossier**")
            st.caption(
                "Supprime définitivement la fiche, l'historique, le budget, les devis, les invités, les messages, "
                "les documents, les photos et les rendez-vous de ce client. Cette action est irréversible : exportez d'abord si besoin."
            )
            confirme = st.checkbox(f"Je confirme la suppression définitive du dossier « {libelle_dossier(self.fiche_evenement.donnees)} »")
            st.button(
                "Supprimer définitivement", icon=":material/delete_forever:", type="primary",
                disabled=not confirme, on_click=self.retirer_dossier
            )


    def afficher_fiche_client(self):
        self.afficher_type_evenement()
        self.afficher_fiche_form()

        st.subheader(":material/verified_user: Consentements")
        st.markdown("**Données de santé**")
        self.afficher_consentement_sante()
        st.markdown("**Droit à l'image**")
        self.afficher_consentements_image()

        self.afficher_historique()
        self.afficher_acces_prives()
        self.afficher_donnees_client()
