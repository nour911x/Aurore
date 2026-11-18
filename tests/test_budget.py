from datetime import date, timedelta

from budget import Budget


def budget_traiteur(tmp_path):
    budget = Budget(str(tmp_path / "budget.json"))
    budget.add_poste("Traiteur", 5000)
    return budget


def test_engage_additionne_les_factures_du_poste(tmp_path):
    budget = budget_traiteur(tmp_path)
    budget.add_facture("Traiteur", "Acompte", 1500, "2026-12-01", True)
    budget.add_facture("Traiteur", "Solde", 3500, "2026-12-20", False)

    assert budget.engage_du_poste(budget.postes[0]) == 5000
    assert budget.depense_du_poste(budget.postes[0]) == 1500
    assert budget.total_engage() == 5000


def test_factures_a_payer_triees_par_echeance(tmp_path):
    budget = budget_traiteur(tmp_path)
    dans_dix_jours = (date.today() + timedelta(days=10)).isoformat()
    hier = (date.today() - timedelta(days=1)).isoformat()
    budget.add_facture("Traiteur", "Solde", 3500, dans_dix_jours, False)
    budget.add_facture("Traiteur", "Acompte", 1500, hier, False)
    budget.add_facture("Traiteur", "Déjà payée", 100, hier, True)

    a_payer = budget.factures_a_payer()

    assert [facture["libelle"] for facture in a_payer] == ["Acompte", "Solde"]
    assert a_payer[0]["jours_restants"] == -1


def test_marquer_payee(tmp_path):
    budget = budget_traiteur(tmp_path)
    budget.add_facture("Traiteur", "Acompte", 1500, "2026-12-01", False)

    budget.marquer_payee("Traiteur", "Acompte")

    assert budget.factures_a_payer() == []
