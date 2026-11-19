import base64
from datetime import datetime

import streamlit as st

from config.profils import ORGANISATEUR
from donnees.demo import creer_demo, demo_active, retirer_demo
from metier.accueil import JOURS_SURVEILLANCE, synthese
from metier.devis import date_lisible
from textes import RACCOURCIS, RACCOURCIS_CLIENTS, RACCOURCIS_PRESTATAIRE, montant, pluriel
from ui.commun import echeance_lisible, heure_rdv, ouvrir_dossier
from ui.habillage import AVERTISSEMENT_HTML, accueil_html, aujourdhui_html


class VueAccueil:
    @staticmethod
    def bouton_ouvrir(cle, dossier_id, onglet, section=None, libelle="Ouvrir le dossier"):
        st.button(
            libelle, key=cle, icon=":material/open_in_new:", type="tertiary",
            on_click=ouvrir_dossier, args=(dossier_id, onglet, section)
        )


    @staticmethod
    def section_accueil(titre, icone):
        conteneur = st.container(border=True)
        conteneur.markdown(f"**:material/{icone}: {titre}**")
        return conteneur


    def afficher_rdvs_du_jour(self, rdvs):
        with self.section_accueil("Aujourd'hui", "today"):
            if not rdvs:
                st.caption("Aucun rendez-vous aujourd'hui.")

            for index, rdv in enumerate(rdvs):
                st.markdown(f"**{heure_rdv(rdv)}** · {rdv['titre']} · :gray[{rdv['type']}]")
                st.caption(f"{rdv['dossier']} · avec {rdv['avec'] or '—'} · {rdv['lieu'] or 'lieu à préciser'}")

                if rdv.get("briefing"):
                    with st.expander("Briefing", icon=":material/assignment:"):
                        st.markdown(rdv["briefing"])
                self.bouton_ouvrir(f"jour_{index}", rdv["dossier_id"], "planning", "agenda")


    def afficher_conflits(self, paires, doubles):
        with self.section_accueil("Conflits", "warning"):
            if not paires and not doubles:
                st.caption("Aucun chevauchement dans le calendrier, aucun prestataire réservé deux fois le même jour.")

            for double in doubles:
                st.markdown(
                    f":orange[:material/event_busy:] **{double['prestataire']}** est réservé deux fois le "
                    f"**{date_lisible(double['date'])}** : {', '.join(double['dossiers'])}"
                )

            for premier, second in paires:
                st.markdown(
                    f":orange[:material/warning:] **{heure_rdv(premier, True)} {premier['titre']}** ({premier['dossier']}) "
                    f"chevauche **{heure_rdv(second, True)} {second['titre']}** ({second['dossier']})"
                )


    def confirmer_rdv(self, rdv):
        self.agenda.confirmer(rdv["titre"], rdv["date_heure"], rdv["dossier_id"])


    def afficher_a_faire(self, elements):
        with self.section_accueil("À faire", "task_alt"):
            if not elements:
                st.caption("Rien en attente.")

            for element in elements:
                morceaux = [
                    pluriel(element["a_valider"], "message à valider", "messages à valider") if element["a_valider"] else "",
                    pluriel(element["a_envoyer"], "message validé à envoyer", "messages validés à envoyer") if element["a_envoyer"] else "",
                    pluriel(element["relances"], "relance") if element["relances"] else "",
                    pluriel(element["a_preparer"], "message à préparer", "messages à préparer") if element["a_preparer"] else "",
                    pluriel(len(element["confirmations"]), "confirmation attendue", "confirmations attendues") if element["confirmations"] else "",
                    f":orange[à définir : {', '.join(element['a_definir'])}]" if element["a_definir"] else ""
                ]
                st.markdown(f"**{element['dossier']}** : {', '.join(filter(None, morceaux))}")

                for rdv in element["confirmations"]:
                    texte, bouton = st.columns([4, 1], vertical_alignment="center")
                    texte.caption(f"{heure_rdv(rdv, True)} · {rdv['titre']} avec {rdv['avec']} : confirmation non reçue")
                    bouton.button(
                        "Confirmé", key=f"confirmer_{rdv['dossier_id']}_{rdv['date_heure']}_{rdv['titre']}",
                        icon=":material/check:", type="tertiary", on_click=self.confirmer_rdv, args=(rdv,)
                    )

                if element["a_definir"]:
                    self.bouton_ouvrir(f"definir_{element['dossier_id']}", element["dossier_id"], "fiche", libelle="Compléter la fiche")

                if element["a_valider"] or element["a_envoyer"] or element["relances"] or element["a_preparer"]:
                    self.bouton_ouvrir(f"faire_{element['dossier_id']}", element["dossier_id"], "messages", "a_envoyer", "Ouvrir les messages")


    def afficher_paiements(self, factures):
        with self.section_accueil("Paiements", "payments"):
            if not factures:
                st.caption("Aucune facture en retard ni à échéance dans les 7 jours.")

            for index, facture in enumerate(sorted(factures, key=lambda facture: facture["jours_restants"])):
                sens = "À encaisser auprès du client" if facture["sens"] == "client" else "À régler au prestataire"
                st.markdown(f"{echeance_lisible(facture['jours_restants'])} · **{facture['libelle']}** · {montant(facture['montant'])}")
                st.caption(f"{sens} · {facture['dossier']}")
                self.bouton_ouvrir(f"paiement_{index}", facture["dossier_id"], "budget", "budget")


    def afficher_a_surveiller(self, dossiers):
        with self.section_accueil(f"Dossiers à surveiller (J-{JOURS_SURVEILLANCE} et moins)", "visibility"):
            if not dossiers:
                st.caption(f"Aucun événement dans les {JOURS_SURVEILLANCE} prochains jours.")

            for dossier in dossiers:
                etat = f":orange[À définir : {', '.join(dossier['manquants'])}]" if dossier["manquants"] else ":green[Dossier complet]"
                st.markdown(f"**{dossier['dossier']}** · J-{dossier['jours']} · {etat}")
                self.bouton_ouvrir(f"surveiller_{dossier['dossier_id']}", dossier["dossier_id"], "fiche")


    def afficher_demo(self):
        with st.expander("Données de démonstration", icon=":material/science:"):
            if demo_active():
                st.caption(
                    "La démonstration est chargée : l'anniversaire de Tom, la baby shower d'Inès & Malik et des éléments "
                    "ajoutés au mariage de Léa & Liam. Les retirer ne touche pas à vos propres données."
                )

                if st.button("Retirer les données de démonstration", icon=":material/delete:"):
                    retirer_demo()
                    self.recharger_donnees()
                    st.rerun()
            else:
                st.caption("Ajoute un anniversaire, une baby shower et des éléments au mariage de Léa & Liam, datés à partir d'aujourd'hui.")

                if st.button("Ajouter les données de démonstration", icon=":material/add:"):
                    creer_demo()
                    self.recharger_donnees()
                    st.rerun()


    def afficher_aujourd_hui(self):
        maintenant = datetime.now()
        donnees = synthese(maintenant=maintenant)
        st.markdown(aujourdhui_html(maintenant), unsafe_allow_html=True)
        self.afficher_compteurs({
            ":material/today: Rendez-vous aujourd'hui": len(donnees["rdvs_du_jour"]),
            ":material/task_alt: Dossiers à traiter": len(donnees["a_faire"]),
            ":material/payments: Paiements à suivre": len(donnees["paiements"]),
            ":material/warning: Conflits": len(donnees["conflits"]) + len(donnees["doubles_reservations"])
        })
        gauche, droite = st.columns(2)

        with gauche:
            self.afficher_rdvs_du_jour(donnees["rdvs_du_jour"])
            self.afficher_conflits(donnees["conflits"], donnees["doubles_reservations"])

        with droite:
            self.afficher_a_faire(donnees["a_faire"])
            self.afficher_paiements(donnees["paiements"])

        self.afficher_a_surveiller(donnees["a_surveiller"])
        self.afficher_demo()


    def afficher_tableau_de_bord(self):
        historique = self.agent.lire_historique()
        self.afficher_aujourd_hui()
        st.caption("Demander à AURORE")
        self.afficher_boutons_messages("raccourcis", RACCOURCIS)

        if historique:
            st.caption("Dernier échange avec AURORE. Toute la discussion est dans l'onglet Messages.")
            self.afficher_conversation(historique[-2:])


    def afficher_accueil(self, profil):
        st.markdown(accueil_html(profil), unsafe_allow_html=True)


    @staticmethod
    def afficher_conversation(messages):
        for message in messages:
            with st.chat_message(message["role"]):
                if message.get("image"):
                    st.image(base64.b64decode(message["image"]), width=280)

                st.markdown(message["content"])

        st.markdown(AVERTISSEMENT_HTML, unsafe_allow_html=True)


    def afficher_discussion(self, profil):
        historique = self.agent.lire_historique()

        if historique:
            st.button(
                "Nouvelle conversation", icon=":material/add_comment:", key="nouvelle_conversation",
                on_click=self.nouvelle_conversation, args=(profil,)
            )

        if profil != ORGANISATEUR:
            if not historique:
                self.afficher_accueil(profil)

            self.afficher_boutons_messages("raccourcis", RACCOURCIS_PRESTATAIRE if self.prestataire else RACCOURCIS_CLIENTS)
        elif not historique:
            st.caption("Aucune discussion pour l'instant : écrivez à AURORE dans la zone de saisie en bas de page.")

        self.afficher_conversation(historique)
