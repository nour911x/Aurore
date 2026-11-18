from datetime import date, datetime, time, timedelta

from donnees.dossiers import (FICHIER_FICHE, FICHIER_SELECTION, RACINE, chemin, chemin_agenda, chemin_annuaire, creer,
                              ecrire_etat, lire_etat, lister, supprimer)
from donnees.event_state import EventSheet
from donnees.storage import load_json, save_json
from metier.agenda import Agenda
from metier.budget import Budget
from metier.devis import CarnetDevis
from metier.messages import Messagerie, destinataire_prestataire, suggestion
from metier.prestataires import Annuaire, Carnet, meme_nom
from metier.rgpd import consentement


NOMS_MARIAGE = "Léa et Liam"

FICHIERS_MARQUES = ["budget_data.json", "messages_data.json", "devis_data.json", FICHIER_SELECTION]


def a_heure(jour, heure, minute=0):
    return datetime.combine(jour, time(heure, minute)).isoformat()


def marquer(element):
    element["demo"] = True
    return element


def nouveau_dossier(fiche, racine):
    dossier_id = creer({**fiche, "demo": True}, racine)
    EventSheet(chemin(dossier_id, FICHIER_FICHE, racine)).remplacer(fiche)
    return dossier_id


def ajouter_rdvs(racine, dossier_id, rdvs):
    agenda = Agenda(chemin_agenda(racine), dossier_id)

    for titre, debut, duree, lieu, avec, confirme in rdvs:
        agenda.tous.append(marquer({
            "titre": titre, "date_heure": debut, "duree_minutes": duree, "lieu": lieu, "avec": avec,
            "dossier_id": dossier_id, "type": None, "confirme": confirme
        }))

    agenda.save()


def choisir(carnet, fiche, statut, tarif=0, poste=None, depuis=None):
    prestataire_id = carnet.annuaire.ajouter(fiche)
    nouveau = not carnet.choix(prestataire_id)
    carnet.selectionner(prestataire_id, tarif, poste)

    if nouveau:
        marquer(carnet.choix(prestataire_id))
        carnet.changer_statut(prestataire_id, statut, depuis)

    return carnet.trouver(prestataire_id)


def dossier_mariage(racine, aujourd_hui):
    for dossier in lister(racine):
        if meme_nom(dossier.get("noms") or "", NOMS_MARIAGE):
            return dossier["id"]

    return nouveau_dossier({
        "type_evenement": "Mariage", "noms": NOMS_MARIAGE, "date": str(aujourd_hui + timedelta(days=32)),
        "budget": 15000, "nombre_invites": 25, "allergies_interdits": ["fruits à coque"], "preferences_musicales": ["soul"]
    }, racine)


def poste(budget, nom, montant):
    for existant in budget.postes:
        if meme_nom(existant["nom"].split(" (")[0], nom):
            return existant["nom"]

    budget.add_poste(nom, montant)
    marquer(budget.postes[-1])
    budget.save()

    return nom


def mariage(racine, annuaire, aujourd_hui):
    dossier_id = dossier_mariage(racine, aujourd_hui)
    carnet = Carnet(annuaire, chemin(dossier_id, FICHIER_SELECTION, racine))
    traiteur = choisir(carnet, {"nom": "Saveurs d'Orient", "categorie": "Traiteur"}, "Réservé", 9500, "Traiteur")
    choisir(carnet, {"nom": "DJ Groove", "categorie": "DJ / Musiciens", "contact": "Yanis", "telephone": "06 45 67 89 10"}, "Réservé", 1200, "Musique")
    choisir(carnet, {"nom": "Studio Lumière", "categorie": "Photographe", "contact": "Julien", "telephone": "06 98 76 54 32"}, "Devis demandé", 2400, "Photographe", str(aujourd_hui - timedelta(days=8)))
    fleuriste = choisir(carnet, {"nom": "Fleurs de Lune", "categorie": "Fleuriste", "contact": "Léna", "telephone": "06 11 22 33 44"}, "Devis reçu", 1500, "Fleuriste")

    budget = Budget(chemin(dossier_id, "budget_data.json", racine))
    poste_traiteur = poste(budget, "Traiteur", 9500)
    poste(budget, "Fleuriste", 1500)
    budget.add_facture(poste_traiteur, "Acompte Saveurs d'Orient", 2850, str(aujourd_hui - timedelta(days=3)), False)
    marquer(next(element for element in budget.postes if element["nom"] == poste_traiteur)["factures"][-1])
    budget.save()

    devis = CarnetDevis(chemin(dossier_id, "devis_data.json", racine))
    devis.add_devis(
        "Fleurs de Lune", fleuriste["id"], NOMS_MARIAGE,
        [{"designation": "Arche de cérémonie", "quantite": 1, "prix_unitaire": 650},
         {"designation": "Centres de table", "quantite": 12, "prix_unitaire": 55}],
        20.0, 30, 30, "Acompte à la signature, solde le jour de l'événement."
    )
    marquer(devis.devis[-1])
    devis.changer_statut(devis.devis[-1]["numero"], "Envoyé")

    messagerie = Messagerie(chemin(dossier_id, "messages_data.json", racine))
    messagerie.ajouter(
        suggestion("demo_menu", "libre", destinataire_prestataire(traiteur), {}),
        "Bonjour Nadia, pourriez-vous nous envoyer la version finale du menu ? Merci !"
    )
    marquer(messagerie.messages[-1])
    messagerie.save()

    ajouter_rdvs(racine, dossier_id, [
        ("Dégustation du menu", a_heure(aujourd_hui, 10), 90, "Saveurs d'Orient", "Saveurs d'Orient", True),
        ("Essayage robe", a_heure(aujourd_hui, 15), 60, "Atelier Blanche", "Léa", False)
    ])

    return EventSheet(chemin(dossier_id, FICHIER_FICHE, racine)).data["date"]


def anniversaire(racine, annuaire, date_mariage):
    dossier_id = nouveau_dossier({
        "type_evenement": "Anniversaire", "noms": "Tom", "date": date_mariage,
        "lieu": "Rooftop Le Perchoir", "budget": 4000, "nombre_invites": 60,
        "personne_fetee": "Tom", "age": 40, "surprise": True
    }, racine)
    carnet = Carnet(annuaire, chemin(dossier_id, FICHIER_SELECTION, racine))
    choisir(carnet, {"nom": "DJ Groove", "categorie": "DJ / Musiciens"}, "Réservé", 800, "Musique")


def baby_shower(racine, aujourd_hui):
    dossier_id = nouveau_dossier({
        "type_evenement": "Baby shower", "noms": "Inès et Malik", "date": str(aujourd_hui + timedelta(days=20)),
        "nombre_invites": 25, "allergies_interdits": ["lactose"], "gender_reveal": True,
        "date_naissance": str(aujourd_hui + timedelta(days=60))
    }, racine)
    EventSheet(chemin(dossier_id, FICHIER_FICHE, racine)).set_consentement("consentement_sante", consentement(True))
    ajouter_rdvs(racine, dossier_id, [
        ("Visite de salle", a_heure(aujourd_hui, 15, 30), 60, "Salle des Tilleuls", "Inès", False)
    ])


def creer_demo(racine=RACINE, aujourd_hui=None):
    aujourd_hui = aujourd_hui or date.today()
    annuaire = Annuaire(chemin_annuaire(racine))
    date_mariage = mariage(racine, annuaire, aujourd_hui)
    anniversaire(racine, annuaire, date_mariage)
    baby_shower(racine, aujourd_hui)
    ecrire_etat("demo_active", True, racine)


def demo_active(racine=RACINE):
    return bool(lire_etat(racine).get("demo_active"))


def demo_au_premier_lancement(racine=RACINE):
    if lire_etat(racine).get("demo_initialisee"):
        return

    creer_demo(racine)
    ecrire_etat("demo_initialisee", True, racine)


def sans_marques(donnees):
    if isinstance(donnees, list):
        return [sans_marques(element) for element in donnees if not (isinstance(element, dict) and element.get("demo"))]

    if isinstance(donnees, dict):
        return {cle: sans_marques(valeur) for cle, valeur in donnees.items()}

    return donnees


def retirer_demo(racine=RACINE):
    for dossier in lister(racine):
        if dossier.get("demo"):
            supprimer(dossier["id"], racine)
            continue

        for fichier in FICHIERS_MARQUES:
            chemin_fichier = chemin(dossier["id"], fichier, racine)
            donnees = load_json(chemin_fichier, None)

            if donnees is not None:
                save_json(chemin_fichier, sans_marques(donnees))

    save_json(chemin_agenda(racine), sans_marques(load_json(chemin_agenda(racine), [])))
    ecrire_etat("demo_active", False, racine)
