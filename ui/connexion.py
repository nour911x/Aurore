
import os

import streamlit as st
from dotenv import load_dotenv

from config.profils import CLIENTS, ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import emplacement_acces
from metier.acces import Acces, LiensAcces, Tentatives, verifier
from metier.devis import date_lisible
from textes import ERREUR_LIEN, ERREUR_MOT_DE_PASSE_ABSENT
from ui.commun import PROFILS_ACTIFS
from ui.contexte import Vue
from ui.habillage import marque_html


PARAMETRE_LIEN = "acces"


@st.cache_resource
def tentatives():
    return Tentatives()


def afficher_connexion():
    load_dotenv()
    hache = os.environ.get("MOT_DE_PASSE_HACHE")
    st.markdown(marque_html({}), unsafe_allow_html=True)

    if not hache:
        st.error(ERREUR_MOT_DE_PASSE_ABSENT, icon=":material/lock:")
        return

    with st.form("connexion", width=420):
        mot_de_passe = st.text_input("Mot de passe organisateur", type="password")

        if not st.form_submit_button("Se connecter", icon=":material/login:", type="primary"):
            return

    attente = tentatives().secondes_restantes()

    if attente:
        st.error(f"Trop d'essais. Réessayez dans {attente} secondes.", icon=":material/timer:")
    elif verifier(mot_de_passe, hache):
        tentatives().reussite()
        st.session_state.organisateur = True
        st.rerun()
    else:
        tentatives().echec()
        st.error("Mot de passe incorrect.", icon=":material/lock:")


def identifier():
    if PARAMETRE_LIEN in st.query_params:
        acces = LiensAcces(emplacement_acces()).acces(st.query_params[PARAMETRE_LIEN])

        if acces and PROFILS_ACTIFS.get(acces.profil, False):
            return acces

        st.error(ERREUR_LIEN, icon=":material/link_off:")
        return None

    if st.session_state.get("organisateur"):
        return Acces(ORGANISATEUR)

    afficher_connexion()
    return None


def adresse_du_lien(jeton):
    adresse = (st.context.url or "").split("?")[0]
    return f"{adresse}?{PARAMETRE_LIEN}={jeton}"


class VueConnexion(Vue):
    def afficher_deconnexion(self):
        if st.button("Se déconnecter", icon=":material/logout:", width="stretch"):
            st.session_state.clear()
            st.rerun()


    def nom_du_lien(self, lien):
        if lien["profil"] == CLIENTS:
            return "Clients"

        prestataire = self.ctx.carnet.trouver(lien["prestataire_id"])
        return prestataire["nom"] if prestataire else "Prestataire retiré du dossier"


    def afficher_nouveau_lien(self, liens):
        destinataires = {"Clients": None} if PROFILS_ACTIFS[CLIENTS] else {}

        if PROFILS_ACTIFS[PRESTATAIRE]:
            destinataires |= {f"{prestataire['nom']} (prestataire)": prestataire["id"] for prestataire in self.ctx.carnet.prestataires}

        if not destinataires:
            return

        with st.form("form_lien"):
            choix = st.selectbox("Pour", list(destinataires))

            if not st.form_submit_button("Créer un lien privé", icon=":material/add_link:"):
                return

        prestataire_id = destinataires[choix]
        jeton = liens.creer(PRESTATAIRE if prestataire_id else CLIENTS, self.ctx.dossier_id, prestataire_id)
        st.warning("Copiez ce lien maintenant : il ne sera plus affiché. Toute personne qui l'a peut voir cet espace.", icon=":material/key:")
        st.code(adresse_du_lien(jeton), language=None)


    def afficher_acces_prives(self):
        liens = LiensAcces(emplacement_acces())

        with st.expander("Liens privés (clients et prestataires)", icon=":material/link:"):
            self.afficher_nouveau_lien(liens)

            for lien in liens.du_dossier(self.ctx.dossier_id):
                infos, bouton = st.columns([4, 1], vertical_alignment="center")
                infos.markdown(f"**{self.nom_du_lien(lien)}** · :gray[valable jusqu'au {date_lisible(lien['expire_le'])}]")

                if bouton.button("Révoquer", icon=":material/link_off:", key=f"revoquer_{lien['id']}"):
                    liens.revoquer(lien["id"])
                    st.rerun()
