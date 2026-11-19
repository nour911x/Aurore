from metier.agenda import Agenda


def agenda_vide(tmp_path, dossier_id="a"):
    return Agenda(str(tmp_path / "agenda.json"), dossier_id)


def test_conflit_quand_les_creneaux_se_chevauchent(tmp_path):
    agenda = agenda_vide(tmp_path)
    agenda.ajouter_rdv("Dégustation", "2026-12-03T14:00:00", 60, "", "")

    conflit = agenda.ajouter_rdv("Essayage", "2026-12-03T14:30:00", 30, "", "")

    assert conflit["titre"] == "Dégustation"
    assert len(agenda.rdvs) == 1


def test_pas_de_conflit_quand_un_rdv_finit_avant_le_suivant(tmp_path):
    agenda = agenda_vide(tmp_path)
    agenda.ajouter_rdv("Dégustation", "2026-12-03T14:00:00", 60, "", "")

    assert agenda.ajouter_rdv("Essayage", "2026-12-03T15:00:00", 30, "", "") is None
    assert len(agenda.rdvs) == 2


def test_conflit_entre_deux_dossiers(tmp_path):
    agenda = agenda_vide(tmp_path, "a")
    agenda.ajouter_rdv("Visite de salle", "2026-12-03T10:00:00", 90, "", "")
    agenda.pour_dossier("b")

    conflit = agenda.ajouter_rdv("Appel traiteur", "2026-12-03T11:00:00", 30, "", "")

    assert conflit["dossier_id"] == "a"


def test_chaque_dossier_ne_voit_que_ses_rdvs(tmp_path):
    agenda = agenda_vide(tmp_path, "a")
    agenda.ajouter_rdv("Visite de salle", "2026-12-03T10:00:00", 60, "", "")
    agenda.pour_dossier("b")
    agenda.ajouter_rdv("Essayage", "2026-12-04T10:00:00", 60, "", "")

    assert [rdv["titre"] for rdv in agenda.rdvs] == ["Essayage"]
    assert len(Agenda(agenda.chemin_fichier).tous) == 2


def test_supprimer_ne_touche_pas_les_autres_dossiers(tmp_path):
    agenda = agenda_vide(tmp_path, "a")
    agenda.ajouter_rdv("Rdv", "2026-12-03T10:00:00", 60, "", "")
    agenda.pour_dossier("b")
    agenda.ajouter_rdv("Rdv", "2026-12-04T10:00:00", 60, "", "")

    agenda.supprimer_rdv("Rdv", "2026-12-03T10:00:00")

    assert len(agenda.tous) == 2
