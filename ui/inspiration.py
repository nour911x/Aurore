import uuid
from html import escape

import streamlit as st
from groq import RateLimitError

from config import features
from config.profils import ORGANISATEUR
from metier.devis import date_lisible
from metier.galerie import CATEGORIES_PHOTO, TAGS_PHOTO, generer_autorisation_pdf, publiable, tag
from metier.inspiration import CATEGORIES_BEAUTE, ELEMENTS_MOODBOARD, generer_moodboard_pdf, lien_maps
from metier.instagram import (
    CarteTemoignage,
    ErreurInstagram,
    PublicationInstagram,
)
from metier.messages import destinataire_clients, suggestion
from metier.rgpd import USAGES_PHOTO, consentements_manquants
from textes import noms_clients, pluriel
from ui import composants, design
from ui.contexte import Vue
from ui.fiche import VueFiche
from ui.messages import VueMessages
from ui.prestataires import VuePrestataires


class VueInspiration(Vue):
    @staticmethod
    def afficher_palette(couleurs):
        pastilles = "".join(
            f'<div><span style="--teinte:{escape(couleur["hex"])}"></span>{escape(couleur["nom"])}<br>{escape(couleur["hex"])}</div>'
            for couleur in couleurs
        )
        design.afficher_html(f'<div class="palette">{pastilles}</div>')


    def afficher_moodboard(self):
        if st.button("Créer le moodboard à partir de la discussion", icon=":material/auto_awesome:"):
            with st.spinner("AURORE compose votre moodboard…"):
                self.ctx.inspiration.definir_moodboard(
                    self.ctx.agent.suggerer_moodboard(self.ctx.fiche_evenement.infos_sans_historique(), ELEMENTS_MOODBOARD)
                )

        moodboard = self.ctx.inspiration.moodboard

        if not moodboard:
            st.info("Discute d'abord avec AURORE de vos goûts (style, couleurs, saison…), puis crée le moodboard.")
            return

        design.grand_titre(moodboard["titre"], "Moodboard")
        st.markdown(moodboard["ambiance"])
        self.afficher_palette(moodboard["couleurs"])
        st.markdown(" ".join(f"`{mot}`" for mot in moodboard["mots_cles"]))

        if features.PINTEREST_MOODBOARD_AUTO:
            st.markdown("**:material/push_pin: Inspirations Pinterest**")
            composants.afficher_liens({f":material/push_pin: {element}": lien for element, lien in moodboard["liens"].items()})

        bouton_pdf, bouton_envoi = st.columns(2)
        bouton_pdf.download_button(
            "Télécharger le moodboard (PDF)", icon=":material/download:",
            data=generer_moodboard_pdf(moodboard, self.ctx.fiche_evenement.donnees["noms"], features.PINTEREST_MOODBOARD_AUTO),
            file_name="moodboard.pdf",
            mime="application/pdf",
            width="stretch"
        )

        if bouton_envoi.button("Préparer l'envoi aux clients", icon=":material/mail:", width="stretch"):
            cle = f"moodboard_{uuid.uuid4().hex[:8]}"
            avec_liens = features.PINTEREST_MOODBOARD_AUTO
            contexte = moodboard if avec_liens else {cle_moodboard: valeur for cle_moodboard, valeur in moodboard.items() if cle_moodboard != "liens"}
            VueMessages(self.ctx).rediger(
                suggestion(cle, "envoi_moodboard", destinataire_clients(self.ctx.fiche_evenement.donnees), contexte),
                "Présente le style en une phrase" + (" et inclus les liens Pinterest du contexte, un par ligne." if avec_liens else ".")
            )


    def afficher_recommandation(self, categorie, recommandation, lieu):
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


    def afficher_adresses(self):
        categorie = st.selectbox("Que cherchez-vous ?", list(CATEGORIES_BEAUTE))
        lieu = st.text_input("Ville ou secteur de recherche", value=self.ctx.fiche_evenement.donnees["lieu"] or "")

        if st.button("Demander conseil à AURORE", icon=":material/auto_awesome:"):
            with st.spinner("AURORE réfléchit à ce qui vous correspond…"):
                self.ctx.inspiration.definir_recommandation(
                    categorie,
                    self.ctx.agent.recommander_adresses(
                        categorie, self.ctx.fiche_evenement.infos_sans_historique(), self.ctx.budget.resume()
                    )
                )

        recommandation = self.ctx.inspiration.recommandations.get(categorie)

        if recommandation:
            self.afficher_recommandation(categorie, recommandation, lieu)
            VuePrestataires(self.ctx).afficher_prestataire_form(
                "Vous avez trouvé une adresse ? Ajoutez-la au carnet",
                f"form_adresse_{categorie}",
                CATEGORIES_BEAUTE[categorie]
            )


    def analyser_photos(self, photos):
        for photo in photos:
            try:
                analyse = self.ctx.agent.analyser_photo(self.ctx.galerie.lire(photo), CATEGORIES_PHOTO)
            except RateLimitError:
                st.warning("Limite de Groq atteinte : relance l'analyse des photos restantes dans une minute.")
                return

            categorie = analyse.get("categorie")
            self.ctx.galerie.modifier(
                photo["id"],
                categorie=categorie if categorie in CATEGORIES_PHOTO else "Autre",
                personnes=bool(analyse["personnes"]) if "personnes" in analyse else None,
                description=analyse.get("description", "")
            )


    def afficher_import_photos(self):
        fichiers = st.file_uploader(
            "Ajouter des photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
            key=f"photos_{st.session_state.version_galerie}"
        )

        if fichiers and st.button("Ajouter à la galerie et trier avec AURORE", icon=":material/download:", type="primary"):
            nouvelles = [self.ctx.galerie.ajouter_photo(fichier.getvalue(), fichier.type) for fichier in fichiers]

            with st.spinner(f"AURORE trie {pluriel(len(nouvelles), 'photo')}…"):
                self.analyser_photos(nouvelles)

            st.session_state.version_galerie += 1
            st.rerun()

        restantes = self.ctx.galerie.a_analyser()

        if restantes and st.button(f"Analyser {pluriel(len(restantes), 'photo restante', 'photos restantes')}", icon=":material/search:"):
            with st.spinner("AURORE analyse les photos…"):
                self.analyser_photos(restantes)

            st.rerun()


    def afficher_photo(self, photo):
        with st.container(border=True):
            st.image(self.ctx.galerie.lire(photo), width="stretch")

            for usage in USAGES_PHOTO:
                ok, raison = publiable(photo, self.ctx.fiche_evenement.donnees["droit_image"], usage)
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
                self.ctx.galerie.modifier(photo["id"], **changements)
                st.rerun()

            if st.button("Supprimer", key=f"suppr_photo_{photo['id']}"):
                self.ctx.galerie.supprimer(photo["id"])
                st.rerun()


    def afficher_photos(self):
        self.afficher_import_photos()

        if not self.ctx.galerie.photos:
            design.vide("Aucune photo pour l'instant. Ajoute les photos du jour J ci-dessus.")
            return

        filtre = st.pills("Afficher", ["Toutes"] + CATEGORIES_PHOTO, default="Toutes")
        photos = [photo for photo in reversed(self.ctx.galerie.photos) if filtre in ("Toutes", None, photo["categorie"])]

        for index, colonne in enumerate(st.columns(3)):
            with colonne:
                for photo in photos[index::3]:
                    self.afficher_photo(photo)


    def afficher_droit_image(self, profil):
        st.caption(
            "Sans consentement, seules les photos sans personne reconnaissable (salle, déco, buffet, détails) sont publiables. "
            "Les photos où des invités sont reconnaissables ne sont jamais publiées."
        )
        VueFiche(self.ctx).afficher_consentements_image()

        if profil == ORGANISATEUR and st.button("Préparer la demande d'autorisation aux clients", icon=":material/mail:"):
            cle = f"droit_image_{uuid.uuid4().hex[:8]}"
            destinataire = destinataire_clients(self.ctx.fiche_evenement.donnees)
            VueMessages(self.ctx).rediger(suggestion(cle, "demande_droit_image", destinataire, {"usage": "Instagram et site d'AURORE"}))

        st.download_button(
            "Télécharger l'autorisation à signer (PDF)", icon=":material/download:",
            data=generer_autorisation_pdf(self.ctx.fiche_evenement.donnees),
            file_name="autorisation-droit-image.pdf",
            mime="application/pdf"
        )


    @staticmethod
    def instagram():
        return PublicationInstagram()

    def publier_par_api(self, instagram, cle, contenu, legende, au_publier):
        """Toujours après une confirmation : un post est public."""
        with st.popover(
            "Publier", icon=":material/send:", type="primary", width="stretch"
        ):
            st.markdown(
                "L'image et la légende seront publiées sur le compte "
                "Instagram d'AURORE, visibles par tout le monde."
            )

            if not st.button(
                "Confirmer la publication", key=f"confirmer_{cle}",
                type="primary", disabled=not legende.strip()
            ):
                return

            with st.spinner("Publication sur Instagram…"):
                try:
                    resultat = instagram.publier(contenu, legende)
                except ErreurInstagram as erreur:
                    st.error(str(erreur), icon=":material/error:")
                    return

            au_publier(resultat["lien"])
            st.rerun()

    def afficher_actions_publication(
        self, cle, contenu, nom_fichier, legende, au_publier
    ):
        """Télécharger, puis publier par l'API si elle est configurée,
        sinon ouvrir Instagram et marquer le post comme publié."""
        instagram = self.instagram()
        telecharger, publier, marquer = st.columns(3)
        telecharger.download_button(
            "Image", icon=":material/download:", data=contenu,
            file_name=nom_fichier, key=f"dl_{cle}", width="stretch"
        )

        if instagram.est_configuree():
            with publier:
                self.publier_par_api(
                    instagram, cle, contenu, legende, au_publier
                )
            return

        publier.link_button(
            "Instagram", "https://www.instagram.com/",
            icon=":material/share:", width="stretch"
        )

        if marquer.button(
            "Publiée", icon=":material/check_circle:",
            key=f"publiee_{cle}", width="stretch"
        ):
            au_publier("")
            st.rerun()

    @staticmethod
    def lien_post(element):
        lien = element.get("lien_instagram")

        return f" · [voir le post]({lien})" if lien else ""

    def afficher_publication(self, photo):
        with st.container(border=True):
            image, texte = st.columns([1, 2])
            contenu = self.ctx.galerie.lire(photo)
            image.image(contenu, width="stretch")

            with texte:
                if st.button("Rédiger la légende avec AURORE", icon=":material/auto_awesome:", key=f"legende_{photo['id']}"):
                    with st.spinner("AURORE écrit la légende…"):
                        legende = self.ctx.agent.rediger_legende(
                            f"photo « {photo['categorie']} » : {photo['description']}", self.ctx.fiche_evenement.infos_pour_prestataire()
                        )

                    self.ctx.galerie.modifier(photo["id"], legende=legende)
                    st.rerun()

                legende = st.text_area(
                    "Légende", value=photo["legende"], height=150,
                    key=f"texte_legende_{photo['id']}_{hash(photo['legende'])}"
                )

                if legende != photo["legende"]:
                    self.ctx.galerie.modifier(photo["id"], legende=legende)

                self.afficher_actions_publication(
                    f"photo_{photo['id']}", contenu, photo["fichier"], legende,
                    lambda lien: self.ctx.galerie.modifier(
                        photo["id"], publiee=True, lien_instagram=lien
                    )
                )


    def afficher_instagram(self):
        a_publier = [photo for photo in self.ctx.galerie.publiables(self.ctx.fiche_evenement.donnees["droit_image"]) if not photo["publiee"]]
        deja_publiees = [photo for photo in self.ctx.galerie.photos if photo["publiee"]]
        if self.instagram().est_configuree():
            st.caption(
                "Seules les photos autorisées apparaissent ici. Relis la "
                "légende, puis publie : AURORE demande toujours confirmation."
            )
        else:
            st.caption(
                "Seules les photos autorisées apparaissent ici. Copie la "
                "légende, télécharge la photo et publie-la depuis "
                "Instagram. Pour publier directement depuis AURORE, "
                "configure l'API Instagram (voir le README)."
            )

        if not a_publier:
            design.vide("Aucune photo publiable en attente.")

        for photo in a_publier:
            self.afficher_publication(photo)

        if deja_publiees:
            nombre = pluriel(
                len(deja_publiees), "photo déjà publiée",
                "photos déjà publiées"
            )
            liens = "".join(self.lien_post(photo) for photo in deja_publiees)
            st.caption(f":material/push_pin: {nombre}{liens}.")


    def afficher_avis(self, profil):
        with st.expander("Enregistrer un avis reçu", icon=":material/add:"):
            with st.form("form_avis", clear_on_submit=True):
                note = st.slider("Note", 1, 5, 5)
                commentaire = st.text_area("Avis des clients sur l'organisation de leur événement")

                if st.form_submit_button("Enregistrer l'avis") and commentaire:
                    self.ctx.galerie.ajouter_avis(noms_clients(self.ctx.fiche_evenement.donnees), note, commentaire)
                    st.rerun()

        if st.button("Demander un avis aux clients", icon=":material/mail:"):
            cle = f"avis_manuel_{uuid.uuid4().hex[:8]}"
            destinataire = destinataire_clients(self.ctx.fiche_evenement.donnees)
            VueMessages(self.ctx).rediger(suggestion(cle, "demande_avis", destinataire, {"date_evenement": self.ctx.fiche_evenement.donnees["date"]}))

        if not self.ctx.galerie.avis:
            design.vide("Aucun avis pour l'instant.")

        for avis in reversed(self.ctx.galerie.avis):
            with st.container(border=True):
                st.markdown(f":orange[{':material/star:' * avis['note']}] · **{avis['auteur']}** · {date_lisible(avis['date'])}")
                st.markdown(f"« {avis['commentaire']} »")

                if not features.INSTAGRAM_FEEDBACK:
                    continue

                if consentements_manquants(self.ctx.fiche_evenement.donnees["droit_image"], "Réseaux sociaux"):
                    st.caption(":material/lock: Pour en faire un post, il faut le consentement de droit à l'image de chaque client pour les réseaux sociaux.")
                    continue

                if st.button("Transformer en post témoignage", icon=":material/auto_awesome:", key=f"post_avis_{avis['id']}"):
                    with st.spinner("AURORE prépare le post…"):
                        publication = self.ctx.agent.rediger_legende(
                            f"témoignage des clients, note {avis['note']}/5 : « {avis['commentaire']} »",
                            self.ctx.fiche_evenement.infos_pour_prestataire(),
                            "Cite un court extrait de leur avis entre guillemets."
                        )

                    self.ctx.galerie.modifier_avis(avis["id"], post=publication)
                    st.rerun()

                if avis["post"]:
                    self.afficher_post_temoignage(avis)

    def afficher_post_temoignage(self, avis):
        """La carte témoignage et sa légende, prêtes à publier."""
        if avis.get("publie"):
            st.caption(
                ":material/check_circle: Témoignage publié sur Instagram"
                f"{self.lien_post(avis)}."
            )
            return

        carte = CarteTemoignage(
            avis["commentaire"], avis["note"], avis["auteur"]
        ).generer()
        image, texte = st.columns([1, 2])
        image.image(carte, width="stretch")

        with texte:
            legende = st.text_area(
                "Post Instagram", value=avis["post"], height=150,
                key=f"texte_post_{avis['id']}_{hash(avis['post'])}"
            )

            if legende != avis["post"]:
                self.ctx.galerie.modifier_avis(avis["id"], post=legende)

            self.afficher_actions_publication(
                f"avis_{avis['id']}", carte, f"temoignage_{avis['id']}.jpg",
                legende,
                lambda lien: self.ctx.galerie.modifier_avis(
                    avis["id"], publie=True, lien_instagram=lien
                )
            )
