from datetime import date, datetime, timedelta

import streamlit as st

from config import features
from config.evenements import TYPES_EVENEMENT, champs_du_type, type_du_dossier
from config.profils import CLIENTS, ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import creer as creer_dossier
from metier.invites import GROUPES, REGIMES, STATUTS_INVITE
from textes import LIBELLES_SECTIONS, ONGLETS, pluriel


ICONES_STATUT = {
    "À contacter": ":gray[:material/radio_button_unchecked:]",
    "Devis demandé": ":orange[:material/hourglass_top:]",
    "Devis reçu": ":blue[:material/description:]",
    "Réservé": ":green[:material/check_circle:]",
    "Refusé": ":red[:material/cancel:]"
}


AUCUN = "—"

FORMAT_DATE = "DD/MM/YYYY"


OUI_NON = {AUCUN: None, "Oui": True, "Non": False}


SECTIONS = {
    "messages": ["discussion", "a_envoyer"],
    "planning": ["agenda", "deroule", "plan_salle", "salle_3d"],
    "prestataires": ["prestataires", "documents"],
    "budget": ["budget", "devis"],
    "inspiration": ["moodboard", "adresses", "photos", "droit_image", "avis", "instagram"]
}


SECTIONS_ACTIVES = {
    "instagram": features.INSTAGRAM_FEEDBACK,
    "salle_3d": features.DIGITAL_EVENT_REPRESENTATION,
    "adresses": features.VENDOR_RECOMMENDATIONS
}


PROFILS_ACTIFS = {CLIENTS: features.CLIENT_PORTAL, PRESTATAIRE: features.VENDOR_PORTAL}


INFOS_PAR_CATEGORIE = {
    "Traiteur": {"allergies", "invites", "tables"},
    "DJ / Musiciens": {"musique"},
    "Domaine / Salle": {"couverts"}
}


CONFIG_COLONNES_DEROULE = {
    "heure": st.column_config.TextColumn("Heure", help="Format 14:30", width="small"),
    "moment": st.column_config.TextColumn("Moment", required=True),
    "lieu": st.column_config.TextColumn("Lieu"),
    "intervenants": st.column_config.TextColumn("Qui"),
    "details": st.column_config.TextColumn("Détails", width="large")
}


ESPACES = {
    ORGANISATEUR: ["accueil", "messages", "fiche", "planning", "prestataires", "budget", "invites", "inspiration"],
    CLIENTS: ["recap", "budget_client", "invitations", "discussion"],
    PRESTATAIRE: ["discussion", "evenement", "agenda_prestataire", "devis_prestataire"]
}


COLONNES_DEVIS = ["designation", "quantite", "prix_unitaire"]


CONFIG_COLONNES_DEVIS = {
    "designation": st.column_config.TextColumn("Désignation", width="large"),
    "quantite": st.column_config.NumberColumn("Qté", min_value=0),
    "prix_unitaire": st.column_config.NumberColumn("Prix unit. HT (€)", min_value=0)
}


ICONES_INVITE = {
    "À inviter": ":gray[:material/radio_button_unchecked:]",
    "Invité": ":blue[:material/send:]",
    "Confirmé": ":green[:material/check_circle:]",
    "Décliné": ":red[:material/cancel:]"
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


def lire_date(texte):
    try:
        return date.fromisoformat(texte)
    except (TypeError, ValueError):
        return None


def texte_vers_liste(texte):
    return [element.strip() for element in texte.split(",") if element.strip()]


def resume_contexte(contexte):
    return contexte.get("titre") or contexte.get("libelle") or contexte.get("nom") or ""


def details_dossier(donnees, prive=True):
    details = {"noms": type_du_dossier(donnees)["personnes"], "type_evenement": "Événement", "theme": "Thème"}
    details |= champs_du_type(donnees)
    details["allergies_interdits"] = "Allergies"

    if prive:
        details["prestataires"] = "Prestataires"

    return details


DELAI_BRIEFING_AUTOMATIQUE = timedelta(hours=24)


def ouvrir_onglet(profil, onglet, section=None):
    st.session_state[f"onglets_{profil}"] = ONGLETS[onglet]

    if section:
        st.session_state[f"sections_{profil}_{onglet}"] = LIBELLES_SECTIONS[section]


def ouvrir_messages(profil):
    ouvrir_onglet(profil, "messages", "a_envoyer")


def ouvrir_dossier(dossier_id, onglet="fiche", section=None):
    st.session_state.dossier_actif = dossier_id
    ouvrir_onglet(ORGANISATEUR, onglet, section)


def heure_rdv(rdv, avec_jour=False):
    debut = datetime.fromisoformat(rdv["date_heure"])
    return f"{debut:%d/%m %H:%M}" if avec_jour else f"{debut:%H:%M}"


def echeance_lisible(jours):
    if jours < 0:
        return f":red[En retard de {pluriel(-jours, 'jour')}]"

    if jours == 0:
        return ":orange[Aujourd'hui]"

    return f":orange[Dans {pluriel(jours, 'jour')}]"


def personnes_du_dossier(donnees):
    noms = donnees["noms"] or ""
    return [nom.strip() for nom in noms.replace(" & ", ",").replace(" et ", ",").split(",") if nom.strip()]


def ouvrir_nouveau_dossier(cle_type=None):
    st.session_state.type_nouveau_dossier = cle_type
    st.session_state.ouvrir_nouveau_dossier = True


def choisir_type(cle_type=None):
    st.session_state.type_nouveau_dossier = cle_type


def fermer_nouveau_dossier():
    st.session_state.type_nouveau_dossier = None
    st.session_state.ouvrir_nouveau_dossier = False


def afficher_tuiles(cle, au_clic):
    with st.container(horizontal=True, key=cle):
        for cle_type, type_evenement in TYPES_EVENEMENT.items():
            st.button(
                f"**{type_evenement['libelle']}**  \n{type_evenement['exemples']}",
                key=f"{cle}-{cle_type}", icon=type_evenement["icone"], width="stretch",
                on_click=au_clic, args=(cle_type,)
            )


@st.dialog("Nouveau dossier", width="large", on_dismiss=fermer_nouveau_dossier)
def nouveau_dossier():
    cle_type = st.session_state.get("type_nouveau_dossier")

    if not cle_type:
        st.markdown("Quel type d'événement organisez-vous ?")
        afficher_tuiles("tuiles-dialogue", choisir_type)
        return

    type_evenement = TYPES_EVENEMENT[cle_type]

    with st.form("form_nouveau_dossier"):
        st.markdown(f"**{type_evenement['libelle']}**")
        noms = st.text_input(type_evenement["personnes"])
        jour = st.date_input("Date de l'événement", value=None, format=FORMAT_DATE)
        sous_type = st.text_input("Type précis (EVJF, fiançailles, crémaillère…)") if cle_type == "autre" else ""

        if st.form_submit_button("Créer le dossier", type="primary"):
            st.session_state.dossier_actif = creer_dossier({
                "type_evenement": type_evenement["libelle"],
                "noms": noms or None,
                "date": str(jour) if jour else None,
                "sous_type": sous_type or None
            })
            fermer_nouveau_dossier()
            st.rerun()

    st.button("Changer de type", on_click=choisir_type)
