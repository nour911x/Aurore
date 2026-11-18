from config import features
from outils import OUTILS_PAR_ESPACE
from user_interface import ESPACES, UserInterface


def test_sections_masquees_selon_les_flags():
    assert ("salle_3d" in UserInterface.sections("planning")) == features.DIGITAL_EVENT_REPRESENTATION
    assert ("instagram" in UserInterface.sections("inspiration")) == features.INSTAGRAM_FEEDBACK
    assert ("adresses" in UserInterface.sections("inspiration")) == features.VENDOR_RECOMMENDATIONS


def test_aucun_envoi_whatsapp_automatique():
    assert features.WHATSAPP_AUTO_SEND is False


def test_vues_partagees_en_lecture_seule():
    for espace in ("Mariés", "Prestataire"):
        assert all(outil.startswith("consulter_") for outil in OUTILS_PAR_ESPACE[espace])


def test_organisateur_garde_au_plus_huit_onglets():
    assert len(ESPACES["Wedding planner"]) <= 8
