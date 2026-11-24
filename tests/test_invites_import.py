import pytest

from donnees.stockage import Emplacement
from metier.invites import ListeInvites, entier, lire_contacts, nettoyer


VCF = "BEGIN:VCARD\nFN:Paul Martin\nTEL;TYPE=CELL:0601020304\nTEL:0999\nEMAIL:paul@exemple.fr\nEND:VCARD\nBEGIN:VCARD\nTEL:06\nEND:VCARD\n"


def test_contacts_vcf():
    assert lire_contacts("contacts.VCF", VCF.encode()) == [{"nom": "Paul Martin", "telephone": "0601020304", "email": "paul@exemple.fr"}]


@pytest.mark.parametrize("contenu", [
    "Nom;Prénom;Téléphone;Email\nMartin;Zoé;06;zoe@exemple.fr\n".encode(),
    "Nom;Prénom;Téléphone;Email\nMartin;Zoé;06;zoe@exemple.fr\n".encode("latin-1"),
    b"First Name,Last Name,Phone,E-mail\nZo\xc3\xa9,Martin,06,zoe@exemple.fr\n"
])
def test_contacts_csv(contenu):
    assert lire_contacts("contacts.csv", contenu) == [{"nom": "Zoé Martin", "telephone": "06", "email": "zoe@exemple.fr"}]


@pytest.mark.parametrize(("valeur", "attendu"), [("2", 2), (None, 0), (float("nan"), 0), ("x", 0)])
def test_entiers(valeur, attendu):
    assert entier(valeur) == attendu


def test_nettoyer_ignore_les_lignes_vides_et_les_choix_inconnus():
    invites = nettoyer([{"nom": "paul", "groupe": "Martiens", "regime": "Végan"}, {"nom": " "}, {}])

    assert [(invite["nom"], invite["groupe"], invite["regime"]) for invite in invites] == [("Paul", "Famille", "Végan")]


def test_statuts_faire_part_et_couverts(tmp_path):
    liste = ListeInvites(Emplacement(tmp_path, "test", "invites"))
    liste.remplacer(nettoyer([
        {"id": "a", "nom": "Paul", "accompagnants": 1, "statut": "Confirmé", "regime": "Halal", "allergies": "noix"},
        {"id": "b", "nom": "Zoé", "statut": "Invité"}
    ]))
    liste.definir_faire_part("Venez !")
    liste.valider_faire_part()

    assert liste.recap_traiteur() == {"couverts_confirmes": 2, "couverts_attendus": 3, "regimes": {"Halal": 1}, "allergies": {"Paul": "noix"}}
    assert ListeInvites(liste.emplacement).faire_part_valide

    liste.definir_faire_part("Corrigé")
    liste.changer_statut("b", "Confirmé")

    assert not liste.faire_part_valide
    assert liste.compter_par_statut() == {"Confirmé": 2}
