import json

from donnees.dossiers import ANCIEN_CARNET, FICHIER_SELECTION, chemin, chemin_annuaire, creer, migrer_carnets
from metier.prestataires import Annuaire, Carnet, meme_fiche, reservations_en_double


def ecrire(fichier, data):
    fichier.write_text(json.dumps(data), encoding="utf-8")


def lire(fichier):
    return json.loads(fichier.read_text(encoding="utf-8"))


def ancien(prestataire_id, nom, telephone="", email="", statut="À contacter", tarif=0):
    return {
        "id": prestataire_id, "nom": nom, "categorie": "Traiteur", "contact": "", "telephone": telephone, "email": email,
        "lien": "", "tarif_indicatif": tarif, "poste_budget": "Traiteur", "notes": "", "statut": statut
    }


def test_un_prestataire_commun_garde_statut_et_tarif_propres_a_chaque_dossier(tmp_path):
    annuaire = Annuaire(str(tmp_path / "annuaire.json"))
    mariage = Carnet(annuaire, str(tmp_path / "mariage.json"))
    anniversaire = Carnet(annuaire, str(tmp_path / "anniversaire.json"))

    traiteur = mariage.add_prestataire("Saveurs d'Orient", "Traiteur", "", "0612345678", "", "", 9500, "Traiteur", "")
    anniversaire.selectionner(traiteur, 2000)
    mariage.changer_statut(traiteur, "Réservé")

    assert len(annuaire.prestataires) == 1
    assert mariage.trouver(traiteur)["statut"] == "Réservé"
    assert anniversaire.trouver(traiteur)["statut"] == "À contacter"
    assert anniversaire.trouver(traiteur)["tarif_indicatif"] == 2000
    assert anniversaire.disponibles() == []


def test_retirer_d_un_dossier_garde_le_prestataire_dans_le_carnet(tmp_path):
    annuaire = Annuaire(str(tmp_path / "annuaire.json"))
    carnet = Carnet(annuaire, str(tmp_path / "dossier.json"))
    prestataire_id = carnet.add_prestataire("DJ Max", "DJ / Musiciens", "", "", "", "", 0, None, "")

    carnet.supprimer(prestataire_id)

    assert carnet.prestataires == []
    assert [fiche["nom"] for fiche in carnet.disponibles()] == ["DJ Max"]


def test_doublons_reconnus_par_nom_et_contacts():
    assert meme_fiche({"nom": "Saveurs d’Orient", "telephone": "06 12 34 56 78"}, {"nom": "saveurs d'orient", "telephone": "0612345678"})
    assert meme_fiche({"nom": "DJ Max", "email": "max@dj.fr"}, {"nom": "DJ Max", "telephone": "0600000000"})
    assert not meme_fiche({"nom": "DJ Max", "telephone": "0611111111"}, {"nom": "DJ Max", "telephone": "0622222222"})
    assert not meme_fiche({"nom": "DJ Max"}, {"nom": "DJ Maxime"})


def test_migration_des_carnets_par_dossier_avec_fusion_des_doublons(tmp_path):
    premier = creer({"noms": "Léa et Liam"}, tmp_path)
    second = creer({"noms": "Tom"}, tmp_path)
    dossier_premier = tmp_path / "dossiers" / premier
    dossier_second = tmp_path / "dossiers" / second
    ecrire(dossier_premier / ANCIEN_CARNET, [ancien("a1", "saveurs d'orient", "0766691616", statut="Réservé", tarif=9500)])
    ecrire(dossier_second / ANCIEN_CARNET, [
        ancien("b1", "Saveurs d'Orient", "07 66 69 16 16", "contact@saveurs.fr"),
        ancien("b2", "Saveurs d'Orient", "0600000000")
    ])
    ecrire(dossier_second / "messages_data.json", [{"id": "m", "prestataire_id": "b1", "statut": "à valider"}])

    assert migrer_carnets(tmp_path) == 2

    annuaire = lire(tmp_path / "annuaire_prestataires.json")
    fusionne = next(fiche for fiche in annuaire if fiche["telephone"].replace(" ", "") == "0766691616")
    assert len(annuaire) == 2
    assert fusionne["id"] in ("a1", "b1")
    assert fusionne["email"] == "contact@saveurs.fr"
    assert lire(dossier_second / "messages_data.json")[0]["prestataire_id"] == fusionne["id"]
    assert not (dossier_premier / ANCIEN_CARNET).exists()

    carnet = Carnet(Annuaire(chemin_annuaire(tmp_path)), chemin(premier, FICHIER_SELECTION, tmp_path))
    assert carnet.trouver(fusionne["id"])["statut"] == "Réservé"
    assert carnet.trouver(fusionne["id"])["tarif_indicatif"] == 9500
    assert migrer_carnets(tmp_path) == 0


def test_reservations_en_double_le_meme_jour():
    reservations = [
        {"prestataire_id": "dj", "nom": "DJ Groove", "date": "2026-12-20", "dossier_id": "a", "dossier": "Léa & Liam"},
        {"prestataire_id": "dj", "nom": "DJ Groove", "date": "2026-12-20", "dossier_id": "b", "dossier": "Tom"},
        {"prestataire_id": "dj", "nom": "DJ Groove", "date": "2026-12-27", "dossier_id": "c", "dossier": "Zoé"},
        {"prestataire_id": "traiteur", "nom": "Saveurs", "date": "2026-12-20", "dossier_id": "a", "dossier": "Léa & Liam"}
    ]

    assert reservations_en_double(reservations) == [
        {"prestataire": "DJ Groove", "date": "2026-12-20", "dossiers": ["Léa & Liam", "Tom"]}
    ]
