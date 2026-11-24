import streamlit as st

from donnees.dossiers import chemin_index
from donnees.dossiers import lister as lister_dossiers


@st.cache_resource(show_spinner="Chargement du moteur de recherche documentaire…")
def ouvrir_vector_db():
    from llm.rag.vector_db import VectorDB

    return VectorDB(chemin_index())


@st.cache_resource(show_spinner=False)
def ouvrir_rag():
    from llm.rag.rag import Rag

    return Rag(ouvrir_vector_db())


def nettoyer_index():
    if not chemin_index().exists():
        return

    from llm.rag.vector_db import supprimer_dossiers_absents

    supprimer_dossiers_absents(chemin_index(), [dossier["id"] for dossier in lister_dossiers()])
