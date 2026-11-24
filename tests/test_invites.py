from donnees.stockage import Emplacement
from metier.invites import ListeInvites


def test_modifier_le_faire_part_annule_sa_validation(tmp_path):
    invites = ListeInvites(Emplacement(tmp_path, "test", "invites"))
    invites.definir_faire_part("Nous avons la joie de vous annoncer…")
    invites.valider_faire_part()
    assert ListeInvites(invites.emplacement).faire_part_valide

    invites.definir_faire_part("Nouveau texte")

    assert not invites.faire_part_valide


def test_un_faire_part_vide_ne_peut_pas_etre_valide(tmp_path):
    invites = ListeInvites(Emplacement(tmp_path, "test", "invites"))
    invites.valider_faire_part()

    assert not invites.faire_part_valide
