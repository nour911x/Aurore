# Décisions techniques

Chaque décision : le problème, le choix, ce qu'il coûte. Le détail de chaque étape est dans `REFONTE_PLAN.md`.

## 1. Streamlit pour l'interface

- **Problème** : livrer une application complète en Python, sans front séparé.
- **Choix** : Streamlit.
- **Coût** : tout le script est relancé à chaque action ; l'état vit dans `st.session_state`.

## 2. Un contexte partagé au lieu de l'héritage

- **Problème** : `InterfaceUtilisateur` héritait de 11 classes. Toutes les méthodes partageaient le même espace de noms, au risque qu'une vue en écrase une autre (c'est arrivé avec `afficher_liens` pendant `feature/securite`).
- **Choix** : `Contexte` (`ui/contexte.py`) porte l'état du dossier ouvert. Chaque vue est un objet qui le reçoit (`VueBudget(ctx)`). C'est de la composition.
- **Coût** : on écrit `self.ctx.budget` au lieu de `self.budget`.

## 3. Le code métier ne connaît pas Streamlit

- **Choix** : `metier/` et `donnees/` n'importent ni `ui/` ni Streamlit. Ils se testent sans navigateur et sont vérifiés par mypy.
- **Coût** : les données passent par des appels explicites entre couches.

## 4. SQLite, une ligne par rubrique

- **Problème** : une coupure pendant l'écriture d'un fichier JSON pouvait le corrompre.
- **Choix** : SQLite avec transactions ; le contenu d'une rubrique reste du JSON dans une colonne.
- **Alternative écartée** : une table par objet. Elle permettrait des requêtes et des clés étrangères, inutiles tant que chaque classe lit et écrit sa rubrique entière.
- **Coût** : si deux fenêtres modifient la même rubrique, la dernière sauvegarde gagne.

## 5. RAG sur les documents du dossier

- **Choix** : le pipeline du cours (questions atomiques, recherche vectorielle, reclassement, réponse avec sources), filtré par dossier.
- **Différence avec le cours** : le reclassement renvoie des numéros d'extraits au lieu de recopier les textes.
- **Coût** : PyTorch et le modèle d'embedding sont lourds ; chaque question fait au moins trois appels au LLM quand des extraits sont trouvés.

## 6. Les garde-fous sont dans le code, pas seulement dans le prompt

- **Problème** : un document peut contenir une instruction cachée (injection de prompt).
- **Choix** : après la lecture d'un document, `Outils.est_permis` n'autorise plus que la lecture jusqu'au message suivant. Les vues partagées n'ont que des outils de consultation. Aucun message n'est envoyé par l'application.
- **Coût** : il faut deux messages pour lire un contrat puis agir.

## 7. Mot de passe et liens privés

- **Choix** : scrypt et sel pour le mot de passe ; jeton aléatoire de 256 bits pour les liens, dont seule l'empreinte est stockée. La vue, le dossier et le prestataire viennent du lien enregistré, jamais de l'adresse.
- **Alternative écartée** : des comptes pour chaque client et prestataire, trop lourds pour un usage ponctuel.
- **Coût** : un lien transféré fonctionne pour qui le reçoit. Il expire et se révoque.

## 8. Données personnelles

- **Choix** : les allergies ne sont transmises qu'au traiteur, et seulement avec le consentement. L'IA ne peut ni accorder un consentement ni effacer une allergie. Export et suppression par dossier.
- **Coût** : les conversations sont traitées par Groq, un service extérieur.

## 9. Tests

- **Choix** : tests unitaires pour le métier, AppTest pour les écrans, faux modèle pour le RAG, aucun appel réel à Groq. Les tests écrivent dans un dossier temporaire (`AURORE_DONNEES`). La CI refuse une couverture sous 80 %.
- **Coût** : la qualité des réponses du LLM n'est pas testée automatiquement ; elle a été vérifiée à la main.

## 10. Feature flags

- **Choix** : les fonctions en attente (Instagram, Pinterest, recommandations) sont désactivées dans `config/features.py`, pas supprimées.
- **Coût** : ce code reste à maintenir et il est moins testé.

## 11. Un menu latéral maison plutôt que `st.navigation`

- **Problème** : la navigation native de Streamlit efface les paramètres de l'adresse en changeant de page, donc le jeton `?acces=` des liens privés.
- **Choix** : un menu de boutons dans la barre latérale ; la page ouverte est dans `st.session_state`.
- **Coût** : pas d'adresse propre à chaque page.

## 12. Un système de design

- **Choix** : couleurs, échelle typographique et styles dans `ui/theme.css` ; composants dans `ui/design.py`. Un test vérifie le contraste WCAG AA des couleurs de texte et l'absence de style ailleurs.
- **Coût** : `.streamlit/config.toml` répète les couleurs, Streamlit ne lisant pas les variables CSS (un test vérifie qu'elles concordent). Les sélecteurs CSS dépendent de la structure interne de Streamlit, d'où la version figée.

## 13. Salle en 3D interactive

- **Choix** : `metier/salle.py` calcule la disposition sans interface ; le plan 2D et la scène Three.js dessinent les mêmes objets. Un composant Streamlit v2 renvoie chaque déplacement à Python, qui le vérifie avant de l'enregistrer.
- **Alternative écartée** : une image générée par IA. Elle demanderait un autre fournisseur que Groq et ne respecterait ni le nombre de tables ni les places.
- **Coût** : Three.js (version figée) est chargé depuis jsDelivr, donc la 3D demande internet et fait confiance à ce service. Le navigateur doit accepter WebGL.

## 14. Images du moodboard avec Openverse

- **Problème** : le moodboard n'avait que du texte et des couleurs ; les services de génération d'images et l'API Pinterest sont payants ou fermés.
- **Choix** : `metier/images.py` cherche des images sous licence Creative Commons sur Openverse, sans clé. Groq écrit trois recherches en anglais par élément, de la plus précise à la plus générale, car le catalogue est surtout décrit en anglais. Un filtre sur le titre écarte les photos hors sujet. Les images sont téléchargées, recadrées et stockées dans le dossier du client.
- **Alternative écartée** : raccourcir une recherche mot par mot quand elle donne trop peu d'images. Essayé : « burgundy décor » devenait « décor », et la Bourgogne remplaçait le bordeaux.
- **Alternative écartée** : afficher les images depuis leur adresse d'origine, sans les télécharger. Le PDF aurait demandé internet, et une image retirée du site d'origine aurait disparu du moodboard.
- **Coût** : la pertinence dépend des mots-clés et des descriptions d'Openverse ; sans clé, Openverse limite le nombre de requêtes (une par élément, soit six par moodboard). Les licences NC interdisent un usage commercial : les images servent d'inspiration privée avec les clients, pas de publication.
