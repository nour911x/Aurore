from datetime import date, datetime, time, timedelta

from agenda import Agenda
from budget import Budget, POSTE_ORGANISATION
from dossiers import RACINE, FICHIER_FICHE, chemin, chemin_agenda, creer, lister, supprimer
from event_state import EventSheet
from messages import Messagerie, destinataire_prestataire, suggestion
from prestataires import Carnet


def a_heure(jour, heure, minute=0):
    return datetime.combine(jour, time(heure, minute)).isoformat()


def nouveau_dossier(fiche, racine):
    dossier_id = creer({**fiche, "demo": True}, racine)
    EventSheet(chemin(dossier_id, FICHIER_FICHE, racine)).remplacer(fiche)
    return dossier_id


def ajouter_rdvs(racine, dossier_id, rdvs):
    agenda = Agenda(chemin_agenda(racine), dossier_id)

    for titre, debut, duree, lieu, avec, confirme in rdvs:
        agenda.tous.append({
            "titre": titre, "date_heure": debut, "duree_minutes": duree, "lieu": lieu, "avec": avec,
            "dossier_id": dossier_id, "type": None, "confirme": confirme
        })

    agenda.save()


def mariage(racine, aujourd_hui):
    dossier_id = nouveau_dossier({
        "type_evenement": "Mariage", "noms": "camille et hugo", "date": str(aujourd_hui + timedelta(days=45)),
        "lieu": "Château de Vaux", "budget": 22000, "nombre_invites": 120, "theme": "Champêtre chic",
        "allergies_interdits": ["arachides"], "preferences_musicales": ["soul", "disco"],
        "ceremonie": "Laïque, dans le parc à 15h", "reception": "Dîner assis dans l'orangerie"
    }, racine)

    carnet = Carnet(chemin(dossier_id, "prestataires_data.json", racine))
    carnet.add_prestataire("Saveurs d'Orient", "Traiteur", "Nadia", "06 12 34 56 78", "contact@saveurs.fr", "", 9500, "Traiteur", "")
    carnet.add_prestataire("Studio Lumière", "Photographe", "Julien", "06 98 76 54 32", "", "", 2400, "Photographe", "")
    carnet.changer_statut(carnet.trouver_par_nom("Saveurs d'Orient")["id"], "Réservé")
    photographe = carnet.trouver_par_nom("Studio Lumière")
    photographe["statut"] = "Devis demandé"
    photographe["statut_depuis"] = str(aujourd_hui - timedelta(days=8))
    carnet.save()

    budget = Budget(chemin(dossier_id, "budget_data.json", racine))
    budget.add_poste("Traiteur", 9500)
    budget.add_poste(POSTE_ORGANISATION, 3500)
    budget.add_facture("Traiteur", "Acompte Saveurs d'Orient", 2850, str(aujourd_hui - timedelta(days=3)), False)
    budget.add_facture(POSTE_ORGANISATION, "Acompte organisation", 1050, str(aujourd_hui + timedelta(days=2)), False)

    traiteur = carnet.trouver_par_nom("Saveurs d'Orient")
    Messagerie(chemin(dossier_id, "messages_data.json", racine)).ajouter(
        suggestion("demo_menu", "libre", destinataire_prestataire(traiteur), {}),
        "Bonjour Nadia, pourriez-vous nous envoyer la version finale du menu avec l'option sans arachides ? Merci !"
    )

    ajouter_rdvs(racine, dossier_id, [
        ("Dégustation du menu", a_heure(aujourd_hui, 10), 90, "Saveurs d'Orient", "Saveurs d'Orient", True),
        ("Essayage robe", a_heure(aujourd_hui, 15), 60, "Atelier Blanche", "Camille", False),
        ("Visite technique du château", a_heure(aujourd_hui + timedelta(days=2), 11), 60, "Château de Vaux", "Studio Lumière", False)
    ])


def baby_shower(racine, aujourd_hui):
    dossier_id = nouveau_dossier({
        "type_evenement": "Baby shower", "noms": "inès et malik", "date": str(aujourd_hui + timedelta(days=20)),
        "nombre_invites": 25, "allergies_interdits": ["lactose"], "gender_reveal": True,
        "date_naissance": str(aujourd_hui + timedelta(days=60))
    }, racine)

    ajouter_rdvs(racine, dossier_id, [
        ("Visite de salle", a_heure(aujourd_hui, 15, 30), 60, "Salle des Tilleuls", "Inès", False)
    ])


def anniversaire(racine, aujourd_hui):
    nouveau_dossier({
        "type_evenement": "Anniversaire", "noms": "Tom", "date": str(aujourd_hui + timedelta(days=75)),
        "lieu": "Rooftop Le Perchoir", "budget": 4000, "nombre_invites": 60,
        "personne_fetee": "Tom", "age": 40, "surprise": True
    }, racine)


def creer_demo(racine=RACINE, aujourd_hui=None):
    aujourd_hui = aujourd_hui or date.today()

    for creer_dossier in (mariage, baby_shower, anniversaire):
        creer_dossier(racine, aujourd_hui)


def dossiers_demo(racine=RACINE):
    return [dossier["id"] for dossier in lister(racine) if dossier.get("demo")]


def retirer_demo(racine=RACINE):
    for dossier_id in dossiers_demo(racine):
        supprimer(dossier_id, racine)
