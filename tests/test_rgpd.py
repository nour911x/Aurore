import json

from donnees.dossiers import FICHIER_FICHE, chemin, creer, lister, supprimer
from donnees.fiche_evenement import FicheEvenement
from metier.galerie import publiable
from metier.invites import ListeInvites
from metier.rgpd import consentement, exporter, peut_recevoir_sante, recap_anonyme, recap_sans_sante


TRAITEUR = {"nom": "Saveurs d'Orient", "categorie": "Traiteur"}

DJ = {"nom": "DJ Max", "categorie": "DJ / Musiciens"}


def fiche(tmp_path, accorde=None):
    dossier_id = creer({"noms": "Léa et Liam", "allergies_interdits": ["arachides"]}, tmp_path)
    fiche_test = FicheEvenement(chemin(dossier_id, FICHIER_FICHE, tmp_path))

    if accorde is not None:
        fiche_test.definir_consentement("consentement_sante", consentement(accorde))

    return dossier_id, fiche_test


def test_allergies_jamais_envoyees_par_defaut(tmp_path):
    _, fiche_test = fiche(tmp_path, accorde=True)

    assert "allergies_interdits" not in fiche_test.infos_sans_historique()
    assert "allergies_interdits" not in fiche_test.infos_pour_prestataire()
    assert "consentement_sante" not in fiche_test.infos_sans_historique(avec_sante=True)


def test_seul_le_traiteur_recoit_les_allergies_avec_accord(tmp_path):
    _, sans_accord = fiche(tmp_path)
    _, avec_accord = fiche(tmp_path, accorde=True)

    assert not peut_recevoir_sante(sans_accord.donnees, TRAITEUR)
    assert peut_recevoir_sante(avec_accord.donnees, TRAITEUR)
    assert not peut_recevoir_sante(avec_accord.donnees, DJ)


def test_l_ia_ne_peut_pas_modifier_les_consentements_ni_effacer_une_allergie(tmp_path):
    _, fiche_test = fiche(tmp_path)

    fiche_test.mettre_a_jour({"consentement_sante": consentement(True), "droit_image": [{"personne": "X"}], "allergies_interdits": ["gluten"]})

    assert fiche_test.donnees["consentement_sante"] is None
    assert fiche_test.donnees["droit_image"] == []
    assert fiche_test.donnees["allergies_interdits"] == ["arachides", "gluten"]


def test_recap_invites_minimise():
    recap = {"couverts_confirmes": 2, "regimes": {"Végan": 1}, "allergies": {"Paul": "gluten", "Zoé": "gluten"}}

    assert recap_sans_sante(recap) == {"couverts_confirmes": 2}
    assert recap_anonyme(recap)["allergies"] == ["gluten"]


def test_photo_publiable_selon_le_tag_et_le_consentement():
    decor = {"personnes": False, "categorie": "Salle & déco"}
    clients = {"personnes": True, "categorie": "Clients"}
    invites = {"personnes": True, "categorie": "Invités"}
    droit_image = [
        {"personne": "Léa", "perimetre": "Réseaux sociaux et portfolio", "date": "2026-11-01"},
        {"personne": "Liam", "perimetre": "Portfolio", "date": "2026-11-01"}
    ]

    assert publiable(decor, [])[0]
    assert not publiable(clients, [])[0]
    assert publiable(clients, droit_image, "Portfolio")[0]
    assert not publiable(clients, droit_image, "Réseaux sociaux")[0]
    assert not publiable(invites, droit_image, "Portfolio")[0]


def test_export_puis_suppression(tmp_path):
    dossier_id, fiche_test = fiche(tmp_path)
    (tmp_path / "agenda_data.json").write_text(json.dumps([
        {"titre": "Essayage", "date_heure": "2026-12-01T10:00:00", "duree_minutes": 60, "dossier_id": dossier_id},
        {"titre": "Autre client", "date_heure": "2026-12-01T12:00:00", "duree_minutes": 60, "dossier_id": "autre"}
    ]), encoding="utf-8")

    export = json.loads(exporter(dossier_id, tmp_path))
    assert export["event_data"]["noms"] == "Léa et Liam"
    assert [rdv["titre"] for rdv in export["rendez_vous"]] == ["Essayage"]

    supprimer(dossier_id, tmp_path)

    assert lister(tmp_path) == []
    assert [rdv["titre"] for rdv in json.loads((tmp_path / "agenda_data.json").read_text(encoding="utf-8"))] == ["Autre client"]


def test_import_de_contacts_sans_doublons(tmp_path):
    invites = ListeInvites(str(tmp_path / "invites.json"))
    contacts = [
        {"nom": "Paul", "telephone": "06", "email": ""},
        {"nom": "paul", "telephone": "06", "email": ""},
        {"nom": "Zoé", "telephone": "07", "email": ""}
    ]

    assert [contact["nom"] for contact in invites.a_importer(contacts)] == ["Paul", "Zoé"]
    assert invites.importer(contacts, "Amis") == 2
    assert invites.a_importer(contacts) == []
