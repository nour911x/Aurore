import uuid

import streamlit as st
from groq import RateLimitError

from config import features
from config.profils import ORGANISATEUR
from metier.devis import date_lisible
from metier.galerie import CATEGORIES_PHOTO, TAGS_PHOTO, generer_autorisation_pdf, publiable, tag
from metier.inspiration import CATEGORIES_BEAUTE, ELEMENTS_MOODBOARD, generer_moodboard_pdf, lien_maps
from metier.messages import destinataire_clients, suggestion
from metier.rgpd import USAGES_PHOTO, consentements_manquants
from textes import noms_clients, pluriel


class VueInspiration:
    @staticmethod
    def show_palette(couleurs):
        pastilles = "".join(
            f'<div style="text-align:center;font-size:0.8em">'
            f'<div style="width:72px;height:72px;border-radius:14px;background:{couleur["hex"]};'
            f'border:1px solid rgba(128,128,128,0.3)"></div>{couleur["nom"]}<br>{couleur["hex"]}</div>'
            for couleur in couleurs
        )
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:12px">{pastilles}</div>', unsafe_allow_html=True)


    def show_moodboard(self):
        if st.button("Créer le moodboard à partir de la discussion", icon=":material/auto_awesome:"):
            with st.spinner("AURORE compose votre moodboard…"):
                self.inspiration.set_moodboard(
                    self.conversation_agent_object.suggest_moodboard(self.event_sheet.infos_sans_historique(), ELEMENTS_MOODBOARD)
                )

        moodboard = self.inspiration.moodboard

        if not moodboard:
            st.info("Discute d'abord avec AURORE de vos goûts (style, couleurs, saison…), puis crée le moodboard.")
            return

        st.subheader(moodboard["titre"])
        st.markdown(moodboard["ambiance"])
        self.show_palette(moodboard["couleurs"])
        st.markdown(" ".join(f"`{mot}`" for mot in moodboard["mots_cles"]))

        if features.PINTEREST_MOODBOARD_AUTO:
            st.markdown("**:material/push_pin: Inspirations Pinterest**")
            self.show_liens({f":material/push_pin: {element}": lien for element, lien in moodboard["liens"].items()})

        bouton_pdf, bouton_envoi = st.columns(2)
        bouton_pdf.download_button(
            "Télécharger le moodboard (PDF)", icon=":material/download:",
            data=generer_moodboard_pdf(moodboard, self.event_sheet.data["noms"], features.PINTEREST_MOODBOARD_AUTO),
            file_name="moodboard.pdf",
            mime="application/pdf",
            width="stretch"
        )

        if bouton_envoi.button("Préparer l'envoi aux clients", icon=":material/mail:", width="stretch"):
            cle = f"moodboard_{uuid.uuid4().hex[:8]}"
            avec_liens = features.PINTEREST_MOODBOARD_AUTO
            contexte = moodboard if avec_liens else {cle_moodboard: valeur for cle_moodboard, valeur in moodboard.items() if cle_moodboard != "liens"}
            self.rediger(
                suggestion(cle, "envoi_moodboard", destinataire_clients(self.event_sheet.data), contexte),
                "Présente le style en une phrase" + (" et inclus les liens Pinterest du contexte, un par ligne." if avec_liens else ".")
            )


    def show_recommandation(self, categorie, recommandation, lieu):
        st.markdown(f"**:material/euro: Budget à prévoir :** {recommandation.get('fourchette', '')}")
        st.markdown(recommandation.get("conseil", ""))

        for type_adresse in recommandation.get("types", []):
            with st.container(border=True):
                st.markdown(f"**{type_adresse.get('type', '')}**")
                st.caption(type_adresse.get("pourquoi", ""))
                st.link_button("Trouver près de chez vous", lien_maps(type_adresse.get("recherche", categorie), lieu), icon=":material/location_on:")

        if recommandation.get("questions"):
            st.markdown("**:material/help: Questions à poser**")

            for question in recommandation["questions"]:
                st.markdown(f"- {question}")


    def show_adresses(self):
        categorie = st.selectbox("Que cherchez-vous ?", list(CATEGORIES_BEAUTE))
        lieu = st.text_input("Ville ou secteur de recherche", value=self.event_sheet.data["lieu"] or "")

        if st.button("Demander conseil à AURORE", icon=":material/auto_awesome:"):
            with st.spinner("AURORE réfléchit à ce qui vous correspond…"):
                self.inspiration.set_recommandation(
                    categorie,
                    self.conversation_agent_object.recommend_adresses(
                        categorie, self.event_sheet.infos_sans_historique(), self.budget.resume()
                    )
                )

        recommandation = self.inspiration.recommandations.get(categorie)

        if recommandation:
            self.show_recommandation(categorie, recommandation, lieu)
            self.show_prestataire_form(
                "Vous avez trouvé une adresse ? Ajoutez-la au carnet",
                f"form_adresse_{categorie}",
                CATEGORIES_BEAUTE[categorie]
            )


    def analyser_photos(self, photos):
        for photo in photos:
            try:
                analyse = self.conversation_agent_object.analyser_photo(self.galerie.lire(photo), CATEGORIES_PHOTO)
            except RateLimitError:
                st.warning("Limite de Groq atteinte : relance l'analyse des photos restantes dans une minute.")
                return

            categorie = analyse.get("categorie")
            self.galerie.modifier(
                photo["id"],
                categorie=categorie if categorie in CATEGORIES_PHOTO else "Autre",
                personnes=bool(analyse["personnes"]) if "personnes" in analyse else None,
                description=analyse.get("description", "")
            )


    def show_import_photos(self):
        fichiers = st.file_uploader(
            "Ajouter des photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
            key=f"photos_{st.session_state.version_galerie}"
        )

        if fichiers and st.button("Ajouter à la galerie et trier avec AURORE", icon=":material/download:", type="primary"):
            nouvelles = [self.galerie.ajouter_photo(fichier.getvalue(), fichier.type) for fichier in fichiers]

            with st.spinner(f"AURORE trie {pluriel(len(nouvelles), 'photo')}…"):
                self.analyser_photos(nouvelles)

            st.session_state.version_galerie += 1
            st.rerun()

        restantes = self.galerie.a_analyser()

        if restantes and st.button(f"Analyser {pluriel(len(restantes), 'photo restante', 'photos restantes')}", icon=":material/search:"):
            with st.spinner("AURORE analyse les photos…"):
                self.analyser_photos(restantes)

            st.rerun()


    def show_photo(self, photo):
        with st.container(border=True):
            st.image(self.galerie.lire(photo), width="stretch")

            for usage in USAGES_PHOTO:
                ok, raison = publiable(photo, self.event_sheet.data["droit_image"], usage)
                etat = ":green[:material/check_circle: publiable]" if ok else ":material/lock: non publiable"
                st.caption(f"**{usage}** : {etat} · {raison}")

            categorie = st.selectbox(
                "Catégorie", CATEGORIES_PHOTO, index=CATEGORIES_PHOTO.index(photo["categorie"]),
                key=f"categorie_{photo['id']}_{photo['categorie']}", label_visibility="collapsed"
            )
            tag_choisi = st.segmented_control(
                "Tag", list(TAGS_PHOTO), default=tag(photo["personnes"]), format_func=TAGS_PHOTO.get,
                key=f"tag_{photo['id']}_{photo['personnes']}", label_visibility="collapsed"
            )

            changements = {}

            if categorie != photo["categorie"]:
                changements["categorie"] = categorie

            if tag_choisi and tag_choisi != tag(photo["personnes"]):
                changements["personnes"] = tag_choisi == "avec_personnes"

            if changements:
                self.galerie.modifier(photo["id"], **changements)
                st.rerun()

            if st.button("Supprimer", key=f"suppr_photo_{photo['id']}"):
                self.galerie.supprimer(photo["id"])
                st.rerun()


    def show_photos(self):
        self.show_import_photos()

        if not self.galerie.photos:
            st.info("Aucune photo pour l'instant. Ajoute les photos du jour J ci-dessus.")
            return

        filtre = st.pills("Afficher", ["Toutes"] + CATEGORIES_PHOTO, default="Toutes")
        photos = [photo for photo in reversed(self.galerie.photos) if filtre in ("Toutes", None, photo["categorie"])]

        for index, colonne in enumerate(st.columns(3)):
            with colonne:
                for photo in photos[index::3]:
                    self.show_photo(photo)


    def show_droit_image(self, profil):
        st.caption(
            "Sans consentement, seules les photos sans personne reconnaissable (salle, déco, buffet, détails) sont publiables. "
            "Les photos où des invités sont reconnaissables ne sont jamais publiées."
        )
        self.show_consentements_image()

        if profil == ORGANISATEUR:
            if st.button("Préparer la demande d'autorisation aux clients", icon=":material/mail:"):
                cle = f"droit_image_{uuid.uuid4().hex[:8]}"
                self.rediger(suggestion(cle, "demande_droit_image", destinataire_clients(self.event_sheet.data), {"usage": "Instagram et site d'AURORE"}))

        st.download_button(
            "Télécharger l'autorisation à signer (PDF)", icon=":material/download:",
            data=generer_autorisation_pdf(self.event_sheet.data),
            file_name="autorisation-droit-image.pdf",
            mime="application/pdf"
        )


    def show_publication(self, photo):
        with st.container(border=True):
            image, texte = st.columns([1, 2])
            contenu = self.galerie.lire(photo)
            image.image(contenu, width="stretch")

            with texte:
                if st.button("Rédiger la légende avec AURORE", icon=":material/auto_awesome:", key=f"legende_{photo['id']}"):
                    with st.spinner("AURORE écrit la légende…"):
                        legende = self.conversation_agent_object.write_legende(
                            f"photo « {photo['categorie']} » : {photo['description']}", self.event_sheet.infos_pour_prestataire()
                        )

                    self.galerie.modifier(photo["id"], legende=legende)
                    st.rerun()

                legende = st.text_area(
                    "Légende", value=photo["legende"], height=150,
                    key=f"texte_legende_{photo['id']}_{hash(photo['legende'])}"
                )

                if legende != photo["legende"]:
                    self.galerie.modifier(photo["id"], legende=legende)

                telecharger, ouvrir, publiee = st.columns(3)
                telecharger.download_button(
                    "Photo", icon=":material/download:", data=contenu, file_name=photo["fichier"], key=f"dl_photo_{photo['id']}", width="stretch"
                )
                ouvrir.link_button("Instagram", "https://www.instagram.com/", icon=":material/share:", width="stretch")

                if publiee.button("Publiée", icon=":material/check_circle:", key=f"publiee_{photo['id']}", width="stretch"):
                    self.galerie.modifier(photo["id"], publiee=True)
                    st.rerun()


    def show_instagram(self):
        a_publier = [photo for photo in self.galerie.publiables(self.event_sheet.data["droit_image"]) if not photo["publiee"]]
        deja_publiees = [photo for photo in self.galerie.photos if photo["publiee"]]
        st.caption("Seules les photos autorisées apparaissent ici. Copie la légende, télécharge la photo et publie-la depuis Instagram.")

        if not a_publier:
            st.info("Aucune photo publiable en attente.")

        for photo in a_publier:
            self.show_publication(photo)

        if deja_publiees:
            st.caption(f":material/push_pin: {pluriel(len(deja_publiees), 'photo déjà publiée', 'photos déjà publiées')}.")


    def show_avis(self, profil):
        with st.expander("Enregistrer un avis reçu", icon=":material/add:"):
            with st.form("form_avis", clear_on_submit=True):
                note = st.slider("Note", 1, 5, 5)
                commentaire = st.text_area("Avis des clients sur l'organisation de leur événement")

                if st.form_submit_button("Enregistrer l'avis") and commentaire:
                    self.galerie.ajouter_avis(noms_clients(self.event_sheet.data), note, commentaire)
                    st.rerun()

        if st.button("Demander un avis aux clients", icon=":material/mail:"):
            cle = f"avis_manuel_{uuid.uuid4().hex[:8]}"
            self.rediger(suggestion(cle, "demande_avis", destinataire_clients(self.event_sheet.data), {"date_evenement": self.event_sheet.data["date"]}))

        if not self.galerie.avis:
            st.caption("Aucun avis pour l'instant.")

        for avis in reversed(self.galerie.avis):
            with st.container(border=True):
                st.markdown(f":orange[{':material/star:' * avis['note']}] · **{avis['auteur']}** · {date_lisible(avis['date'])}")
                st.markdown(f"« {avis['commentaire']} »")

                if not features.INSTAGRAM_FEEDBACK:
                    continue

                if consentements_manquants(self.event_sheet.data["droit_image"], "Réseaux sociaux"):
                    st.caption(":material/lock: Pour en faire un post, il faut le consentement de droit à l'image de chaque client pour les réseaux sociaux.")
                    continue

                if st.button("Transformer en post témoignage", icon=":material/auto_awesome:", key=f"post_avis_{avis['id']}"):
                    with st.spinner("AURORE prépare le post…"):
                        post = self.conversation_agent_object.write_legende(
                            f"témoignage des clients, note {avis['note']}/5 : « {avis['commentaire']} »",
                            self.event_sheet.infos_pour_prestataire(),
                            "Cite un court extrait de leur avis entre guillemets."
                        )

                    self.galerie.modifier_avis(avis["id"], post=post)
                    st.rerun()

                if avis["post"]:
                    st.text_area("Post Instagram", value=avis["post"], height=150, key=f"texte_post_{avis['id']}_{hash(avis['post'])}")
