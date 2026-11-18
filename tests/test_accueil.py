from datetime import date, datetime, time, timedelta

from accueil import champs_a_definir, confirmations_attendues, synthese
from agenda import conflits, deviner_type
from demo import creer_demo, dossiers_demo, retirer_demo
from dossiers import lister


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


def test_synthese_sur_les_donnees_de_demo(tmp_path):
    aujourd_hui = date.today()
    creer_demo(tmp_path, aujourd_hui)

    resultat = synthese(tmp_path, datetime.combine(aujourd_hui, time(8)))

    assert [element["titre"] for element in resultat["rdvs_du_jour"]] == ["Dégustation du menu", "Essayage robe", "Visite de salle"]
    assert [(premier["titre"], second["titre"]) for premier, second in resultat["conflits"]] == [("Essayage robe", "Visite de salle")]
    assert [element["jours"] for element in resultat["a_surveiller"]] == [20, 45]
    assert resultat["a_surveiller"][0]["manquants"] == ["lieu", "budget"]
    assert sorted(facture["sens"] for facture in resultat["paiements"]) == ["client", "prestataire"]

    mariage = next(element for element in resultat["a_faire"] if "Camille" in element["dossier"])
    assert mariage["a_valider"] == 1
    assert mariage["a_envoyer"] == 0
    assert mariage["relances"] == 1
    assert [element["titre"] for element in mariage["confirmations"]] == ["Essayage robe", "Visite technique du château"]


def test_retirer_la_demo(tmp_path):
    creer_demo(tmp_path, date.today() + timedelta(days=1))
    assert len(dossiers_demo(tmp_path)) == 3

    retirer_demo(tmp_path)

    assert lister(tmp_path) == []
