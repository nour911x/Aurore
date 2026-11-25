from datetime import datetime

import streamlit as st

from config.evenements import cle_type, libelle_evenement
from donnees.demo import creer_demo, demo_active, retirer_demo
from donnees.dossiers import libelle_dossier
from metier.accueil import JOURS_SURVEILLANCE, synthese
from metier.agenda import bornes
from metier.devis import date_lisible
from textes import RACCOURCIS, date_longue, montant, noms_courts, pluriel
from ui import composants, design
from ui.commun import echeance_lisible, heure_rdv, ouvrir_dossier, ouvrir_nouveau_dossier, sans_couleur
from ui.contexte import Vue
from ui.discussion import VueDiscussion
from ui.habillage import nom_organisateur, salutation
from ui.index_documents import nettoyer_index


SYMBOLES_RDV = {"Essayage": "checkroom", "Visite": "apartment", "Dégustation": "restaurant", "Réunion": "groups", "Appel": "call"}

TEINTES_RDV = ["#C79A5B", "#8B2340", "#6F8F6A"]


class VueAccueil(Vue):
    @staticmethod
    def lien_ouvrir(cle, dossier_id, onglet, section=None, libelle="Ouvrir"):
        design.lien_action(libelle, cle, ouvrir_dossier, (dossier_id, onglet, section))


    @staticmethod
    def etat_rdv(rdv, maintenant):
        debut, fin = bornes(rdv)

        if fin <= maintenant:
            return "Passé", "neutre"

        return ("En cours", "ok") if debut <= maintenant else ("À venir", "")


    def afficher_rdvs_du_jour(self, rdvs, maintenant):
        design.titre_section(":material/today: Aujourd'hui")

        if not rdvs:
            design.vide("Aucun rendez-vous aujourd'hui.")

        for index, rdv in enumerate(rdvs):
            badge, classe = self.etat_rdv(rdv, maintenant)

            with design.ligne(f"rdv-{index}"):
                design.evenement(
                    rdv["titre"], f"{rdv['dossier']} · avec {rdv['avec'] or '—'} · {rdv['lieu'] or 'lieu à préciser'}",
                    SYMBOLES_RDV.get(rdv["type"], "event"), heure=heure_rdv(rdv), teinte=TEINTES_RDV[index % len(TEINTES_RDV)],
                    badge=badge, classe_badge=classe
                )
                self.lien_ouvrir(f"jour_{index}", rdv["dossier_id"], "planning", "agenda")

            if rdv.get("briefing"):
                with st.expander("Briefing"):
                    st.markdown(rdv["briefing"])


    def afficher_conflits(self, paires, doubles):
        design.titre_section(":material/warning: Conflits")

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
        design.titre_section(":material/task_alt: À faire")

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
        design.titre_section(":material/payments: Paiements")

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
        design.titre_section(":material/auto_awesome: Prochains événements")

        if not dossiers:
            design.vide(f"Aucun événement dans les {JOURS_SURVEILLANCE} prochains jours.")

        for dossier in dossiers:
            fiche = self.ctx.dossiers.get(dossier["dossier_id"], {})
            manquants = f" · à définir : {', '.join(dossier['manquants'])}" if dossier["manquants"] else " · dossier complet"
            vignette = "mariage" if cle_type(fiche.get("type_evenement")) == "mariage" else "fete"

            with design.ligne(f"surveiller-{dossier['dossier_id']}"):
                design.evenement(
                    f"{noms_courts(fiche.get('noms')) or 'Sans nom'} · {libelle_evenement(fiche)}",
                    f"{date_lisible(fiche.get('date'))}{manquants}", vignette=vignette,
                    badge=f"J-{dossier['jours']}", classe_badge="" if dossier["manquants"] else "ok"
                )
                self.lien_ouvrir(f"surveiller_{dossier['dossier_id']}", dossier["dossier_id"], "fiche")


    @staticmethod
    def ouvrir_recherche():
        dossier_id = st.session_state.recherche

        if dossier_id:
            ouvrir_dossier(dossier_id)

        st.session_state.recherche = None


    def afficher_barre_recherche(self, a_faire):
        recherche, cloche = st.columns([6, 1], vertical_alignment="center")

        with recherche.container(key="recherche-globale"):
            st.selectbox(
                "Rechercher", list(self.ctx.dossiers), index=None, key="recherche", placeholder="Rechercher un événement, un client…",
                format_func=lambda dossier_id: libelle_dossier(self.ctx.dossiers[dossier_id]),
                label_visibility="collapsed", on_change=self.ouvrir_recherche
            )

        with cloche.popover(str(len(a_faire)) if a_faire else "", icon=":material/notifications:", help="Dossiers à traiter", width="stretch"):
            if not a_faire:
                design.vide("Rien en attente.")

            for element in a_faire:
                st.button(
                    element["dossier"], key=f"cloche_{element['dossier_id']}", type="tertiary",
                    on_click=ouvrir_dossier, args=(element["dossier_id"], "fiche" if element["a_definir"] else "messages")
                )


    @staticmethod
    def destination(elements, onglet, section=None):
        return {"au_clic": ouvrir_dossier, "arguments": (elements[0]["dossier_id"], onglet, section)} if elements else {}


    def afficher_cartes(self, donnees):
        conflits = [premier for premier, _ in donnees["conflits"]]
        nombre_conflits = len(conflits) + len(donnees["doubles_reservations"])
        retards = any(facture["jours_restants"] < 0 for facture in donnees["paiements"])
        a_traiter = donnees["a_faire"]
        cartes = [
            ("rdv", "calendar_today", "", "Rendez-vous aujourd'hui", len(donnees["rdvs_du_jour"]), False,
             self.destination(donnees["rdvs_du_jour"], "planning", "agenda")),
            ("dossiers", "folder", "", "Dossiers à traiter", len(a_traiter), False, self.destination(a_traiter, "messages", "a_envoyer")),
            ("paiements", "euro", "rose", "Paiements à suivre", len(donnees["paiements"]), retards, self.destination(donnees["paiements"], "budget", "budget")),
            ("conflits", "warning" if nombre_conflits else "check", "rose" if nombre_conflits else "menthe", "Conflits", nombre_conflits,
             bool(nombre_conflits), self.destination(conflits, "planning", "agenda"))
        ]

        for colonne, (cle, symbole, teinte, libelle, valeur, alerte, destination) in zip(st.columns(4), cartes, strict=True):
            with colonne:
                design.carte(cle, symbole, teinte, libelle, valeur, alerte, **destination)


    def afficher_demo(self):
        with st.expander("Données de démonstration", icon=":material/science:"):
            if demo_active():
                st.caption(
                    "La démonstration est chargée : l'anniversaire de Tom, "
                    "la baby shower d'Inès & Malik, le séminaire de "
                    "Nova Tech et des éléments "
                    "ajoutés au mariage de Léa & Liam. Les retirer ne touche pas à vos propres données."
                )

                if st.button("Retirer les données de démonstration", icon=":material/delete:"):
                    retirer_demo()
                    nettoyer_index()
                    self.ctx.recharger_donnees()
                    st.rerun()
            else:
                st.caption(
                    "Ajoute un anniversaire, une baby shower, un séminaire "
                    "d'entreprise et des éléments au mariage de Léa & "
                    "Liam, datés à partir d'aujourd'hui."
                )

                if st.button("Ajouter les données de démonstration", icon=":material/add:"):
                    creer_demo()
                    self.ctx.recharger_donnees()
                    st.rerun()


    def afficher_aujourd_hui(self):
        maintenant = datetime.now()
        donnees = synthese(maintenant=maintenant)
        nom = nom_organisateur()
        self.afficher_barre_recherche(donnees["a_faire"])
        design.banniere(
            f"{salutation()}, {nom.split()[0]} !" if nom else f"{salutation()} !",
            f"{date_longue(maintenant)} {maintenant.year}", "Créons des moments inoubliables."
        )
        self.afficher_cartes(donnees)
        gauche, droite = st.columns([2, 1])

        with gauche:
            with design.bloc("jour"):
                self.afficher_rdvs_du_jour(donnees["rdvs_du_jour"], maintenant)

            with design.bloc("faire"):
                self.afficher_a_faire(donnees["a_faire"])

        with droite:
            st.button("Nouveau dossier", icon=":material/add:", key="nouveau_dossier_accueil", type="primary", width="stretch", on_click=ouvrir_nouveau_dossier)

            with design.bloc("evenements"):
                self.afficher_a_surveiller(donnees["a_surveiller"])

            with design.bloc("conflits"):
                self.afficher_conflits(donnees["conflits"], donnees["doubles_reservations"])

            with design.bloc("paiements"):
                self.afficher_paiements(donnees["paiements"])


    def afficher_tableau_de_bord(self):
        historique = self.ctx.agent.lire_historique()
        self.afficher_aujourd_hui()
        design.titre_section("Demander à AURORE")
        composants.afficher_boutons_messages("raccourcis", RACCOURCIS)

        if historique:
            st.caption("Dernier échange avec AURORE. Toute la discussion est dans Messages.")
            VueDiscussion(self.ctx).afficher_conversation(historique[-2:])

        self.afficher_demo()
