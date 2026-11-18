from datetime import date, datetime, time, timedelta

from metier.accueil import champs_a_definir, confirmations_attendues, synthese
from metier.agenda import conflits, deviner_type
import json

from donnees.demo import creer_demo, demo_active, demo_au_premier_lancement, retirer_demo
from donnees.dossiers import creer, lister


def rdv(titre, debut, duree=60, avec="", confirme=False):
    return {"titre": titre, "date_heure": debut, "duree_minutes": duree, "avec": avec, "confirme": confirme}


def test_conflits_detecte_les_chevauchements():
    rdvs = [
        rdv("Visite", "2026-12-03T15:30:00"),
        rdv("Essayage", "2026-12-03T15:00:00"),
        rdv("Appel", "2026-12-03T16:30:00", 15)
    ]

    paires = conflits(rdvs)

    assert [(premier["titre"], second["titre"]) for premier, second in paires] == [("Essayage", "Visite")]


def test_type_devine_depuis_le_titre():
    assert deviner_type("Essayage robe") == "Essayage"
    assert deviner_type("degustation menu") == "Dégustation"
    assert deviner_type("Signature contrat") == "Autre"


def test_confirmations_attendues():
    maintenant = datetime(2026, 12, 1, 9)
    rdvs = [
        rdv("Avec prestataire", "2026-12-02T10:00:00", avec="DJ"),
        rdv("Déjà confirmé", "2026-12-02T11:00:00", avec="DJ", confirme=True),
        rdv("Sans interlocuteur", "2026-12-02T12:00:00"),
        rdv("Trop loin", "2026-12-20T10:00:00", avec="DJ")
    ]

    assert [element["titre"] for element in confirmations_attendues(rdvs, maintenant)] == ["Avec prestataire"]


def test_champs_a_definir():
    assert champs_a_definir({"date": "2026-12-20", "lieu": None, "nombre_invites": 25, "budget": None}) == ["lieu", "budget"]


def demo_du_jour(tmp_path):
    aujourd_hui = date.today()
    creer_demo(tmp_path, aujourd_hui)
    return synthese(tmp_path, datetime.combine(aujourd_hui, time(8)))


def test_l_accueil_est_rempli_par_la_demo(tmp_path):
    resultat = demo_du_jour(tmp_path)

    assert {dossier["type_evenement"] for dossier in lister(tmp_path)} == {"Mariage", "Anniversaire", "Baby shower"}
    assert len(resultat["rdvs_du_jour"]) >= 1
    assert any(facture["jours_restants"] < 0 for facture in resultat["paiements"])


def test_conflit_volontaire_entre_deux_dossiers(tmp_path):
    resultat = demo_du_jour(tmp_path)

    assert [(premier["titre"], second["titre"]) for premier, second in resultat["conflits"]] == [("Essayage robe", "Visite de salle")]
    premier, second = resultat["conflits"][0]
    assert premier["dossier_id"] != second["dossier_id"]


def test_champs_a_definir_dans_a_faire_pour_un_dossier_proche(tmp_path):
    resultat = demo_du_jour(tmp_path)

    mariage = next(element for element in resultat["a_faire"] if "Léa" in element["dossier"])
    assert "lieu" in mariage["a_definir"]
    assert mariage["relances"] == 1


def test_champs_a_definir_ignores_au_dela_de_la_fenetre(tmp_path):
    creer({"noms": "Zoé", "type_evenement": "Anniversaire", "date": str(date.today() + timedelta(days=120))}, tmp_path)

    resultat = synthese(tmp_path)

    assert resultat["a_faire"] == []


def test_double_reservation_d_un_prestataire_le_meme_jour(tmp_path):
    resultat = demo_du_jour(tmp_path)

    assert [double["prestataire"] for double in resultat["doubles_reservations"]] == ["DJ Groove"]
    assert len(resultat["doubles_reservations"][0]["dossiers"]) == 2


def test_la_demo_complete_le_mariage_existant_puis_se_retire_proprement(tmp_path):
    existant = creer({"type_evenement": "Mariage", "noms": "léa et liam", "date": str(date.today() + timedelta(days=32))}, tmp_path)

    creer_demo(tmp_path)

    assert len(lister(tmp_path)) == 3
    assert any(rdv["dossier_id"] == existant for rdv in json.loads((tmp_path / "agenda_data.json").read_text(encoding="utf-8")))

    retirer_demo(tmp_path)

    assert [dossier["id"] for dossier in lister(tmp_path)] == [existant]
    assert json.loads((tmp_path / "agenda_data.json").read_text(encoding="utf-8")) == []
    assert json.loads((tmp_path / "dossiers" / existant / "selection_prestataires.json").read_text(encoding="utf-8")) == []
    assert not demo_active(tmp_path)


def test_demo_creee_une_seule_fois_au_premier_lancement(tmp_path):
    demo_au_premier_lancement(tmp_path)
    retirer_demo(tmp_path)

    demo_au_premier_lancement(tmp_path)

    assert lister(tmp_path) == []
