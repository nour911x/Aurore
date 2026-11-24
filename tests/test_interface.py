import io
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from groq import APIConnectionError
from PIL import Image
from streamlit.testing.v1 import AppTest

from config.profils import CLIENTS, ORGANISATEUR, PRESTATAIRE
from donnees.dossiers import NOM_SELECTION, chemin, emplacement, emplacement_acces, emplacement_annuaire, lister
from donnees.stockage import charger_donnees
from llm.agent import AgentConversation
from metier.acces import LiensAcces
from metier.documents import Documents
from metier.galerie import Galerie
from metier.inspiration import Inspiration
from metier.invites import ListeInvites, nouvel_invite
from metier.jour_j import JourJ, creer_tables
from metier.prestataires import Annuaire, Carnet
from textes import LIBELLES_PROFIL, LIBELLES_SECTIONS, ONGLETS
from ui.commun import ESPACES
from ui.design import sans_icone
from ui.interface import InterfaceUtilisateur


APP = str(Path(__file__).parent.parent / "app.py")

ECRANS = [
    (profil, onglet, section)
    for profil, onglets in ESPACES.items()
    for onglet in onglets
    for section in InterfaceUtilisateur.sections(onglet)
]

PANNE = APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))


def nouvelle_page(profil=ORGANISATEUR, onglet=None, section=None):
    page = AppTest.from_file(APP, default_timeout=60)
    page.session_state["organisateur"] = True
    page.query_params["profil"] = LIBELLES_PROFIL[profil]

    if onglet:
        page.session_state[f"onglets_{profil}"] = ONGLETS[onglet]

    if section and section != onglet:
        page.session_state[f"sections_{profil}_{onglet}"] = sans_icone(LIBELLES_SECTIONS[section])

    return page


def bouton(page, libelle):
    return next(bouton for bouton in page.button if bouton.label == libelle)


def pages_du_menu(page):
    return [bouton.key.removeprefix("menu_") for bouton in page.sidebar.button if (bouton.key or "").startswith("menu_")]


def champ(page, libelle):
    return next(champ for champ in page.text_input if champ.label == libelle)


def dossier_avec_prestataires():
    nouvelle_page().run()
    dossier = next(dossier for dossier in lister() if dossier["noms"] == "Léa et Liam")

    return dossier["id"], Carnet(Annuaire(emplacement_annuaire()), emplacement(dossier["id"], NOM_SELECTION))


def ecran_du_mariage(profil=ORGANISATEUR, onglet=None, section=None):
    dossier_id, _ = dossier_avec_prestataires()
    page = nouvelle_page(profil, onglet, section)
    page.session_state["dossier_actif"] = dossier_id

    return page, dossier_id


@pytest.mark.parametrize(("profil", "onglet", "section"), ECRANS)
def test_chaque_ecran_s_affiche(profil, onglet, section):
    page, _ = ecran_du_mariage(profil, onglet, section)
    page.run()

    assert not page.exception
    assert pages_du_menu(page) == ESPACES[profil]
    assert page.button(key=f"menu_{onglet}").proto.type == "primary"


def remplir(dossier_id):
    def ou(nom):
        return emplacement(dossier_id, nom)

    liste = ListeInvites(ou("invites_data"))
    liste.remplacer([
        nouvel_invite("Paul Martin", "Amis", "06", "paul@exemple.fr", 1, "Végan", "noix", "Confirmé", "a"),
        nouvel_invite("Zoé", invite_id="b")
    ])
    liste.definir_faire_part("Nous nous marions !")
    liste.valider_faire_part()

    jour_j = JourJ(ou("jour_j_data"))
    jour_j.amenager(creer_tables(1, 4, "Ronde", 2), ["Buffet"])
    jour_j.placer({"a": "Table 1"}, liste.invites)
    jour_j.definir_deroule([{"heure": "15h", "moment": "Cérémonie", "intervenants": "DJ Groove"}])

    Inspiration(ou("inspiration_data")).definir_moodboard({
        "titre": "Bohème", "couleurs": [{"nom": "Terracotta", "hex": "#CC6644"}], "recherches": {"Fleurs": "bouquet"}
    })

    image = io.BytesIO()
    Image.new("RGB", (8, 8)).save(image, format="PNG")
    galerie = Galerie(ou("galerie_data"), chemin(dossier_id, "galerie"))
    galerie.modifier(galerie.ajouter_photo(image.getvalue(), "image/png")["id"], personnes=False)
    galerie.ajouter_avis("Léa", 5, "Parfait")


@pytest.mark.parametrize(("profil", "onglet", "section"), ECRANS)
def test_chaque_ecran_s_affiche_avec_des_donnees(profil, onglet, section):
    page, dossier_id = ecran_du_mariage(profil, onglet, section)
    remplir(dossier_id)
    page.run()

    assert not page.exception


@pytest.mark.parametrize("profil", [CLIENTS, PRESTATAIRE])
def test_un_lien_impose_sa_vue_et_son_dossier(profil):
    dossier_id, carnet = dossier_avec_prestataires()
    prestataire = carnet.prestataires[0]["id"] if profil == PRESTATAIRE else None
    jeton = LiensAcces(emplacement_acces()).creer(profil, dossier_id, prestataire)
    page = AppTest.from_file(APP, default_timeout=60)
    page.query_params["acces"] = jeton
    page.query_params["profil"] = "Organisateur"
    page.session_state["dossier_actif"] = next(dossier["id"] for dossier in lister() if dossier["id"] != dossier_id)
    page.run()

    assert not page.exception
    assert pages_du_menu(page) == ESPACES[profil]
    assert "Nouveau dossier" not in [bouton.label for bouton in page.button]
    assert "Tom" not in " ".join(texte.value for texte in page.markdown)


def test_modifier_la_fiche_est_enregistre():
    page, dossier_id = ecran_du_mariage(onglet="fiche")
    page.run()
    champ(page, "Lieu").set_value("Domaine des Lys")
    bouton(page, next(bouton.label for bouton in page.button if bouton.label.startswith("Enregistrer") and "consentement" not in bouton.label)).click().run()

    assert not page.exception
    assert charger_donnees(emplacement(dossier_id, "event_data"), {})["lieu"] == "Domaine des Lys"


def test_un_message_passe_par_toutes_les_validations():
    page, dossier_id = ecran_du_mariage(onglet="messages", section="a_envoyer")
    page.run()
    next(bouton for bouton in page.button if bouton.label == "Valider").click().run()
    assert "Marquer comme envoyé" in [bouton.label for bouton in page.button]

    bouton(page, "Marquer comme envoyé").click().run()
    statuts = {message["cle"]: message["statut"] for message in charger_donnees(emplacement(dossier_id, "messages_data"), [])}

    assert not page.exception
    assert statuts["demo_menu"] == "envoyé"


def test_message_conserve_pendant_une_panne_puis_renvoye(monkeypatch):
    page, _ = ecran_du_mariage(onglet="messages", section="discussion")
    page.run()

    def panne(*arguments, **options):
        raise PANNE

    monkeypatch.setattr(AgentConversation, "appel", panne)
    page.chat_input[0].set_value("Bonjour AURORE").run()

    assert not page.exception
    assert any("Bonjour AURORE" in texte.value for texte in page.markdown)
    assert pages_du_menu(page)

    monkeypatch.setattr(AgentConversation, "appel", lambda *arguments, **options: SimpleNamespace(content="Me revoilà", tool_calls=None))
    bouton(page, "Réessayer").click().run()

    assert not page.error
    assert "Me revoilà" in [texte.value for texte in page.markdown]


def test_cle_groq_absente(monkeypatch):
    monkeypatch.setenv("GROQ_KEY", "")
    page = nouvelle_page().run()

    assert not page.exception
    assert "GROQ_KEY" in page.error[0].value


def test_creer_puis_revoquer_un_lien_prive():
    page, dossier_id = ecran_du_mariage(onglet="fiche")
    page.run()
    avant = {lien["id"] for lien in LiensAcces(emplacement_acces()).du_dossier(dossier_id)}
    bouton(page, "Créer un lien privé").click().run()
    nouveau = next(lien["id"] for lien in LiensAcces(emplacement_acces()).du_dossier(dossier_id) if lien["id"] not in avant)

    assert "acces=" in page.code[0].value

    page.button(key=f"revoquer_{nouveau}").click().run()
    assert nouveau not in [lien["id"] for lien in LiensAcces(emplacement_acces()).liens]


def test_interroger_un_document_affiche_ses_sources(monkeypatch):
    page, dossier_id = ecran_du_mariage(onglet="prestataires", section="documents")
    documents = Documents(emplacement(dossier_id, "documents_data"), chemin(dossier_id, "documents"))
    documents.ajouter("abc", "contrat.txt", b"Acompte 30 %", 1)
    reponses = [{"question": "Acompte ?", "reponse": "30 %", "sources": [{"document": "contrat.txt", "page": 1, "texte": "Acompte 30 %"}]}]
    monkeypatch.setattr("ui.contexte.ouvrir_rag", lambda: SimpleNamespace(interroger=lambda *arguments: reponses))
    page.run()
    champ(page, "Votre question").set_value("Acompte ?")
    bouton(page, "Chercher dans les documents").click().run()

    assert not page.exception
    assert "30 %" in [texte.value for texte in page.markdown]
    assert "contrat.txt, page 1" in [texte.value for texte in page.caption]


def test_se_deconnecter():
    page = nouvelle_page().run()
    bouton(page, "Se déconnecter").click().run()

    assert not pages_du_menu(page)
