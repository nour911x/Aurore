from datetime import datetime

import streamlit as st

from donnees.demo import creer_demo, demo_active, retirer_demo
from metier.accueil import JOURS_SURVEILLANCE, synthese
from metier.devis import date_lisible
from textes import RACCOURCIS, date_longue, montant, pluriel
from ui import composants, design
from ui.commun import echeance_lisible, heure_rdv, ouvrir_dossier, sans_couleur
from ui.contexte import Vue
from ui.discussion import VueDiscussion
from ui.habillage import salutation
from ui.index_documents import nettoyer_index


class VueAccueil(Vue):
    @staticmethod
    def lien_ouvrir(cle, dossier_id, onglet, section=None, libelle="Ouvrir"):
        design.lien_action(libelle, cle, ouvrir_dossier, (dossier_id, onglet, section))


    def afficher_rdvs_du_jour(self, rdvs):
        design.titre_section("Aujourd'hui")

        if not rdvs:
            design.vide("Aucun rendez-vous aujourd'hui.")

        for index, rdv in enumerate(rdvs):
            with design.ligne(f"rdv-{index}"):
                design.texte_ligne(
                    rdv["titre"], f"{rdv['dossier']} · avec {rdv['avec'] or '—'} · {rdv['lieu'] or 'lieu à préciser'}", heure_rdv(rdv)
                )
                self.lien_ouvrir(f"jour_{index}", rdv["dossier_id"], "planning", "agenda")

            if rdv.get("briefing"):
                with st.expander("Briefing"):
                    st.markdown(rdv["briefing"])


    def afficher_conflits(self, paires, doubles):
        design.titre_section("Conflits")

        if not paires and not doubles:
            design.vide("Aucun conflit.")

        for index, double in enumerate(doubles):
            with design.ligne(f"double-{index}"):
                design.texte_ligne(
                    double["prestataire"], ", ".join(double["dossiers"]), etat=f"réservé deux fois le {date_lisible(double['date'])}", classe_etat="alerte"
                )

        for index, (premier, second) in enumerate(paires):
            with design.ligne(f"conflit-{index}"):
                design.texte_ligne(
                    f"{premier['titre']} et {second['titre']}",
                    f"{heure_rdv(premier, True)} {premier['dossier']} / {heure_rdv(second, True)} {second['dossier']}",
                    etat="se chevauchent", classe_etat="alerte"
                )


    def confirmer_rdv(self, rdv):
        self.ctx.agenda.confirmer(rdv["titre"], rdv["date_heure"], rdv["dossier_id"])


    def afficher_confirmation(self, rdv):
        cle = f"{rdv['dossier_id']}_{rdv['date_heure']}_{rdv['titre']}"

        with design.ligne(f"confirmation-{cle}"):
            design.texte_ligne(rdv["titre"], f"{heure_rdv(rdv, True)} avec {rdv['avec']}", etat="confirmation non reçue")
            design.lien_action("Marquer confirmé", f"confirmer_{cle}", self.confirmer_rdv, (rdv,))


    def afficher_a_faire(self, elements):
        design.titre_section("À faire")

        if not elements:
            design.vide("Rien en attente.")

        for element in elements:
            messages = [
                pluriel(element["a_valider"], "message à valider", "messages à valider") if element["a_valider"] else "",
                pluriel(element["a_envoyer"], "message validé à envoyer", "messages validés à envoyer") if element["a_envoyer"] else "",
                pluriel(element["relances"], "relance") if element["relances"] else "",
                pluriel(element["a_preparer"], "message à préparer", "messages à préparer") if element["a_preparer"] else ""
            ]

            if any(messages):
                with design.ligne(f"faire-{element['dossier_id']}"):
                    design.texte_ligne(element["dossier"], ", ".join(filter(None, messages)))
                    self.lien_ouvrir(f"faire_{element['dossier_id']}", element["dossier_id"], "messages", "a_envoyer", "Ouvrir les messages")

            if element["a_definir"]:
                with design.ligne(f"definir-{element['dossier_id']}"):
                    design.texte_ligne(element["dossier"], f"À définir : {', '.join(element['a_definir'])}")
                    self.lien_ouvrir(f"definir_{element['dossier_id']}", element["dossier_id"], "fiche", libelle="Compléter la fiche")

            for rdv in element["confirmations"]:
                self.afficher_confirmation(rdv)


    def afficher_paiements(self, factures):
        design.titre_section("Paiements")

        if not factures:
            design.vide("Aucun paiement à suivre.")

        for index, facture in enumerate(sorted(factures, key=lambda facture: facture["jours_restants"])):
            sens = "À encaisser auprès du client" if facture["sens"] == "client" else "À régler au prestataire"
            retard = facture["jours_restants"] < 0

            with design.ligne(f"paiement-{index}"):
                design.texte_ligne(
                    f"{facture['libelle']} · {montant(facture['montant'])}", f"{sens} · {facture['dossier']}",
                    etat=sans_couleur(echeance_lisible(facture["jours_restants"])).lower(), classe_etat="alerte" if retard else "attention"
                )
                self.lien_ouvrir(f"paiement_{index}", facture["dossier_id"], "budget", "budget")


    def afficher_a_surveiller(self, dossiers):
        design.titre_section(f"Dossiers à surveiller (J-{JOURS_SURVEILLANCE} et moins)")

        if not dossiers:
            design.vide(f"Aucun événement dans les {JOURS_SURVEILLANCE} prochains jours.")

        for dossier in dossiers:
            etat = f"à définir : {', '.join(dossier['manquants'])}" if dossier["manquants"] else "dossier complet"

            with design.ligne(f"surveiller-{dossier['dossier_id']}"):
                design.texte_ligne(
                    dossier["dossier"], heure=f"J-{dossier['jours']}", etat=etat, classe_etat="attention" if dossier["manquants"] else "ok"
                )
                self.lien_ouvrir(f"surveiller_{dossier['dossier_id']}", dossier["dossier_id"], "fiche")


    def afficher_demo(self):
        with st.expander("Données de démonstration", icon=":material/science:"):
            if demo_active():
                st.caption(
                    "La démonstration est chargée : l'anniversaire de Tom, la baby shower d'Inès & Malik et des éléments "
                    "ajoutés au mariage de Léa & Liam. Les retirer ne touche pas à vos propres données."
                )

                if st.button("Retirer les données de démonstration", icon=":material/delete:"):
                    retirer_demo()
                    nettoyer_index()
                    self.ctx.recharger_donnees()
                    st.rerun()
            else:
                st.caption("Ajoute un anniversaire, une baby shower et des éléments au mariage de Léa & Liam, datés à partir d'aujourd'hui.")

                if st.button("Ajouter les données de démonstration", icon=":material/add:"):
                    creer_demo()
                    self.ctx.recharger_donnees()
                    st.rerun()


    def afficher_aujourd_hui(self):
        maintenant = datetime.now()
        donnees = synthese(maintenant=maintenant)
        retards = any(facture["jours_restants"] < 0 for facture in donnees["paiements"])
        design.grand_titre(f"{salutation()}.", date_longue(maintenant))
        design.indicateurs(
            {
                "Rendez-vous aujourd'hui": len(donnees["rdvs_du_jour"]),
                "Dossiers à traiter": len(donnees["a_faire"]),
                "Paiements à suivre": len(donnees["paiements"]),
                "Conflits": len(donnees["conflits"]) + len(donnees["doubles_reservations"])
            },
            alertes={"Conflits"} | ({"Paiements à suivre"} if retards else set())
        )
        self.afficher_rdvs_du_jour(donnees["rdvs_du_jour"])
        self.afficher_a_faire(donnees["a_faire"])
        self.afficher_conflits(donnees["conflits"], donnees["doubles_reservations"])
        self.afficher_paiements(donnees["paiements"])
        self.afficher_a_surveiller(donnees["a_surveiller"])


    def afficher_tableau_de_bord(self):
        historique = self.ctx.agent.lire_historique()
        self.afficher_aujourd_hui()
        design.titre_section("Demander à AURORE")
        composants.afficher_boutons_messages("raccourcis", RACCOURCIS)

        if historique:
            st.caption("Dernier échange avec AURORE. Toute la discussion est dans Messages.")
            VueDiscussion(self.ctx).afficher_conversation(historique[-2:])

        self.afficher_demo()
