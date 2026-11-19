import pandas as pd
import streamlit as st

from metier.prestataires import lien_email, lien_whatsapp


class Composants:
    @staticmethod
    def obtenir_persistant(cle, classe):

        if cle not in st.session_state:
            st.session_state[cle] = classe()

        return st.session_state[cle]


    @staticmethod
    def afficher_compteurs(compteurs):
        for colonne, (label, valeur) in zip(st.columns(len(compteurs)), compteurs.items(), strict=True):
            colonne.metric(label, valeur)


    @staticmethod
    def afficher_boutons_contact(telephone, email, lien="", message="", sujet=""):
        liens = []

        if telephone:
            liens.append((":material/chat: WhatsApp", lien_whatsapp(telephone, message)))

            if not message:
                liens.append((":material/call: Appeler", f"tel:{telephone}"))

        if email:
            liens.append((":material/mail: Email", lien_email(email, sujet, message)))

        if lien:
            liens.append((":material/link: Site / Instagram", lien))

        if liens:
            for colonne, (texte, url) in zip(st.columns(len(liens)), liens, strict=True):
                colonne.link_button(texte, url, width="stretch")


    @staticmethod
    def editer_tableau(cle, lignes, colonnes, config, nettoyer_lignes, enregistrer, num_rows="dynamic"):
        version = st.session_state.setdefault(f"version_{cle}", 0)
        tableau = st.data_editor(
            pd.DataFrame(lignes, columns=colonnes),
            column_config=config,
            num_rows=num_rows,
            hide_index=True,
            width="stretch",
            key=f"{cle}_{version}"
        )
        nouvelles = nettoyer_lignes(tableau.to_dict("records"))

        if nouvelles != lignes:
            enregistrer(nouvelles)
            st.session_state[f"version_{cle}"] += 1
            st.rerun()


    def afficher_boutons_messages(self, cle, elements, **options):
        with st.container(horizontal=True, key=cle):
            for identifiant, icone, libelle, message in elements:
                st.button(
                    libelle, key=f"{cle}-{identifiant}", icon=icone,
                    on_click=self.mettre_en_attente, args=(message,), **options
                )


    @staticmethod
    def mettre_en_attente(texte):
        st.session_state.message_en_attente = texte


    @staticmethod
    def afficher_liens(liens, par_ligne=3):
        elements = list(liens.items())

        for debut in range(0, len(elements), par_ligne):
            for colonne, (texte, url) in zip(st.columns(par_ligne), elements[debut:debut + par_ligne], strict=False):
                colonne.link_button(texte, url, width="stretch")
