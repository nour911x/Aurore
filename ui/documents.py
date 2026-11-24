import streamlit as st

from donnees.dossiers import chemin_index
from donnees.dossiers import lister as lister_dossiers
from metier.devis import date_lisible
from textes import pluriel


TYPES_DOCUMENT = ["pdf", "txt", "md"]


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


class VueDocuments:
    def interroger_documents(self, question):
        if not self.documents.documents:
            raise ValueError("Aucun document dans ce dossier. Ajoutez-en dans Prestataires › Documents.")

        return ouvrir_rag().interroger(question, self.dossier_id)


    def importer_document(self, nom, contenu):
        from llm.rag.extraits import extraire

        self.documents.verifier_nom(nom)
        extraits = extraire(nom, contenu)
        document_id = self.documents.nouvel_id()
        ouvrir_vector_db().ajouter_document(self.dossier_id, document_id, extraits)
        self.documents.ajouter(document_id, nom, contenu, len(extraits))


    def supprimer_document(self, document):
        ouvrir_vector_db().supprimer_document(document["id"])
        self.documents.supprimer(document["id"])


    def afficher_import_document(self):
        with st.form("form_document", clear_on_submit=True):
            fichier = st.file_uploader("Ajouter un contrat, un devis ou des conditions", type=TYPES_DOCUMENT)

            if not st.form_submit_button("Ajouter au dossier", icon=":material/upload_file:") or not fichier:
                return

            try:
                with st.spinner("Lecture et indexation du document…"):
                    self.importer_document(fichier.name, fichier.getvalue())
            except ValueError as erreur:
                st.error(str(erreur), icon=":material/error:")
            else:
                st.success(f"« {fichier.name} » est prêt à être interrogé.", icon=":material/check_circle:")


    def afficher_liste_documents(self):
        if not self.documents.documents:
            st.caption("Aucun document pour l'instant.")

        for document in self.documents.documents:
            infos, bouton = st.columns([5, 1], vertical_alignment="center")
            infos.markdown(
                f":material/description: **{document['nom']}** · "
                f":gray[ajouté le {date_lisible(document['date'])}, {pluriel(document['extraits'], 'extrait')}]"
            )

            if bouton.button("Supprimer", icon=":material/delete:", key=f"suppr_document_{document['id']}"):
                self.supprimer_document(document)
                st.rerun()


    def afficher_question_documents(self):
        with st.form("form_question_documents"):
            question = st.text_input("Votre question", placeholder="Jusqu'à quand peut-on annuler le traiteur sans frais ?")

            if not st.form_submit_button("Chercher dans les documents", icon=":material/search:") or not question:
                return

        with st.spinner("AURORE lit les documents…"):
            resultats = self.interroger_documents(question)

        for resultat in resultats:
            st.markdown(f"**{resultat['question']}**")
            st.markdown(resultat["reponse"])
            self.afficher_sources(resultat["sources"])


    def afficher_documents(self):
        st.caption("AURORE répond uniquement à partir des documents de ce dossier, en citant ses sources.")
        self.afficher_import_document()
        self.afficher_liste_documents()

        if self.documents.documents:
            st.subheader(":material/search: Interroger les documents")
            self.afficher_question_documents()
