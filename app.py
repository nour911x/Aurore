import streamlit as st
from groq import APIError

from llm.base import CleGroqManquante
from textes import (
    ERREUR_CLE_MANQUANTE,
    message_erreur,
)
from ui.connexion import identifier
from ui.contexte import Contexte
from ui.habillage import style_html
from ui.interface import InterfaceUtilisateur


if __name__ == "__main__":
    st.set_page_config(page_title="AURORE", page_icon=":material/wb_twilight:", layout="wide")
    st.html(style_html())
    acces = identifier()

    try:
        if acces:
            InterfaceUtilisateur(Contexte(acces)).lancer()
    except CleGroqManquante:
        st.error(ERREUR_CLE_MANQUANTE, icon=":material/key_off:")
    except APIError as erreur:
        st.error(message_erreur(erreur), icon=":material/cloud_off:")
