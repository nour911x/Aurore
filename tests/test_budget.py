from datetime import date, timedelta

from metier.budget import Budget


def budget_traiteur(tmp_path):
    budget = Budget(str(tmp_path / "budget.json"))
    budget.ajouter_poste("Traiteur", 5000)
    return budget


def test_engage_additionne_les_factures_du_poste(tmp_path):
    budget = budget_traiteur(tmp_path)
    budget.ajouter_facture("Traiteur", "Acompte", 1500, "2026-12-01", True)
    budget.ajouter_facture("Traiteur", "Solde", 3500, "2026-12-20", False)

    assert budget.engage_du_poste(budget.postes[0]) == 5000
    assert budget.depense_du_poste(budget.postes[0]) == 1500
    assert budget.total_engage() == 5000


def test_factures_a_payer_triees_par_echeance(tmp_path):
    budget = budget_traiteur(tmp_path)
    dans_dix_jours = (date.today() + timedelta(days=10)).isoformat()
    hier = (date.today() - timedelta(days=1)).isoformat()
    budget.ajouter_facture("Traiteur", "Solde", 3500, dans_dix_jours, False)
    budget.ajouter_facture("Traiteur", "Acompte", 1500, hier, False)
    budget.ajouter_facture("Traiteur", "Déjà payée", 100, hier, True)

    a_payer = budget.factures_a_payer()

    assert [facture["libelle"] for facture in a_payer] == ["Acompte", "Solde"]
    assert a_payer[0]["jours_restants"] == -1


def test_marquer_payee(tmp_path):
    budget = budget_traiteur(tmp_path)
    budget.ajouter_facture("Traiteur", "Acompte", 1500, "2026-12-01", False)

    budget.marquer_payee("Traiteur", "Acompte")

    assert budget.factures_a_payer() == []


def test_devis_accepte_cree_acompte_et_solde_sans_doublon(tmp_path):
    budget = budget_traiteur(tmp_path)
    montants = {"ttc": 1000, "acompte": 300}

    budget.enregistrer_devis("DEV-2026-001", montants, "Fleuriste", date(2027, 1, 5))
    budget.enregistrer_devis("DEV-2026-001", montants, "Fleuriste", date(2027, 1, 5))

    fleuriste = next(poste for poste in budget.postes if poste["nom"] == "Fleuriste")
    assert fleuriste["montant_prevu"] == 1000
    assert [(facture["libelle"], facture["montant"]) for facture in fleuriste["factures"]] == [
        ("Acompte DEV-2026-001", 300), ("Solde DEV-2026-001", 700)
    ]


def test_budget_et_factures_d_un_prestataire(tmp_path):
    budget = budget_traiteur(tmp_path)
    budget.ajouter_poste("Organisation", 2000)
    budget.ajouter_facture("Traiteur", "Acompte", 1500, "2026-12-01", False)
    budget.ajouter_facture("Organisation", "Frais Saveurs d'Orient", 50, "2026-12-01", False)
    traiteur = {"nom": "Saveurs d'Orient", "categorie": "Traiteur", "poste_budget": None}

    assert budget.prevu_pour(traiteur) == 5000
    assert [facture["libelle"] for facture in budget.factures_de(traiteur)] == ["Acompte", "Frais Saveurs d'Orient"]
    assert budget.resume()[0] == {"nom": "Traiteur", "montant_prevu": 5000, "engage": 1500}
