import io
from datetime import date

import pytest
from pypdf import PdfReader

from donnees.stockage import Emplacement
from metier.devis import CarnetDevis, generer_pdf, lignes_valides, texte_pdf, totaux
from metier.galerie import generer_autorisation_pdf
from metier.inspiration import COULEUR_PAR_DEFAUT, generer_moodboard_pdf, nettoyer_moodboard
from metier.invites import generer_faire_part_pdf, message_personnel, nouvel_invite
from metier.jour_j import generer_deroule_pdf, generer_plan_table_pdf, nettoyer_deroule


EVENEMENT = {"type_evenement": "Mariage", "noms": "Léa et Liam", "date": "2026-12-20", "lieu": "Domaine des Lys"}

SANS_INFOS = {"type_evenement": "Mariage", "noms": None, "date": None, "lieu": None}

LIGNES = [{"designation": "Arche", "quantite": 1, "prix_unitaire": 650}, {"designation": "Centres", "quantite": 12, "prix_unitaire": 55}]


def lire(pdf):
    return " ".join(" ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages).split())


@pytest.fixture
def carnet(tmp_path):
    carnet = CarnetDevis(Emplacement(tmp_path, "test", "devis"))

    for _ in range(2):
        carnet.ajouter_devis("Fleurs de Lune", "f1", "Léa et Liam", LIGNES, 20.0, 30, 30, "Solde le jour J")

    return carnet


def test_totaux_du_devis(carnet):
    assert totaux(carnet.devis[0]) == {"ht": 1310, "tva": 262, "ttc": 1572, "acompte": 471.6}


def test_lignes_de_devis_nettoyees():
    lignes = [{"designation": " Arche ", "quantite": "2", "prix_unitaire": None}, {"designation": "", "quantite": 1}, {"designation": None}]

    assert lignes_valides(lignes) == [{"designation": "Arche", "quantite": 2.0, "prix_unitaire": 0.0}]


def test_numero_de_devis_jamais_reutilise(carnet):
    annee = date.today().year
    carnet.supprimer(f"DEV-{annee}-001")
    carnet.ajouter_devis("AURORE", None, "Léa et Liam", LIGNES, 20.0, 30, 30, "")

    assert [devis["numero"] for devis in carnet.devis] == [f"DEV-{annee}-002", f"DEV-{annee}-003"]


def test_pdf_du_devis(carnet):
    texte = lire(generer_pdf(carnet.devis[0], EVENEMENT))

    for attendu in ["Fleurs de Lune", "20/12/2026", "Domaine des Lys", "1 572,00 EUR", "471,60 EUR", "Solde le jour J"]:
        assert attendu in texte

    assert "None" not in lire(generer_pdf({**carnet.devis[0], "notes": ""}, SANS_INFOS))


def test_caracteres_non_imprimables_remplaces():
    assert texte_pdf("L’œuvre – 5 €… 🎉") == "L'oeuvre - 5 EUR... ?"


def test_pdf_du_droit_a_l_image():
    assert "20/12/2026" in lire(generer_autorisation_pdf(EVENEMENT))
    assert "les clients" in lire(generer_autorisation_pdf(SANS_INFOS))


def test_pdf_du_faire_part():
    texte = lire(generer_faire_part_pdf("Nous nous marions !", EVENEMENT))

    assert "Nous nous marions" in texte
    assert "20/12/2026 - Domaine des Lys" in texte
    assert message_personnel(nouvel_invite("zoé martin"), "Venez !") == "Bonjour Zoé,\n\nVenez !"


def test_pdf_du_deroule():
    deroule = nettoyer_deroule([{"heure": "14h30", "moment": "Cérémonie", "intervenants": "DJ Groove"}])

    assert "14:30" in lire(generer_deroule_pdf(deroule, EVENEMENT))
    assert generer_deroule_pdf([], SANS_INFOS).startswith(b"%PDF")


def test_pdf_du_plan_de_table():
    paul = nouvel_invite("Paul", accompagnants=1, regime="Végan", allergies="gluten")
    texte = lire(generer_plan_table_pdf({"Table 1": [paul], "Table 2": []}, EVENEMENT))

    for attendu in ["Table 1 (2 couverts)", "Paul", "Végan", "gluten", "Table 2 (0 couverts)"]:
        assert attendu in texte


def test_moodboard_nettoye_et_imprime():
    moodboard = nettoyer_moodboard({
        "titre": "Bohème", "ambiance": "Douce", "couleurs": [{"nom": "Terracotta", "hex": "#CC6644"}, {"nom": "Faux", "hex": "rouge"}, "x"],
        "mots_cles": ["lin", 3], "recherches": {"Fleurs": "bouquet bohème", "Table": None}
    })

    assert [couleur["hex"] for couleur in moodboard["couleurs"]] == ["#CC6644", COULEUR_PAR_DEFAUT]
    assert moodboard["mots_cles"] == ["lin"]
    assert list(moodboard["liens"]) == ["Fleurs"]
    assert "Terracotta" in lire(generer_moodboard_pdf(moodboard, "Léa et Liam"))
    assert "Pinterest" not in lire(generer_moodboard_pdf(moodboard, "", avec_liens=False))
    assert nettoyer_moodboard({})["titre"] == "Moodboard"
