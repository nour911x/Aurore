from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from donnees.dossiers import (
    NOM_FICHE,
    NOM_SELECTION,
    RACINE,
    creer,
    ecrire_etat,
    emplacement,
    emplacement_agenda,
    emplacement_annuaire,
    lire_etat,
    lister,
    supprimer,
)
from donnees.fiche_evenement import FicheEvenement
from donnees.stockage import charger_donnees, sauvegarder_donnees
from metier.agenda import Agenda
from metier.budget import Budget
from metier.devis import CarnetDevis
from metier.messages import Messagerie, destinataire_prestataire, suggestion
from metier.prestataires import Annuaire, Carnet, meme_nom
from metier.rgpd import consentement


if TYPE_CHECKING:
    from metier.budget import Budget
    from metier.prestataires import Annuaire, Carnet


NOMS_MARIAGE = "Léa et Liam"

NOMS_MARQUES = ["budget_data", "messages_data", "devis_data", NOM_SELECTION]


def a_heure(jour: date, heure: int, minute: int = 0) -> str:
    return datetime.combine(jour, time(heure, minute)).isoformat()


def marquer(element: dict) -> dict:
    element["demo"] = True
    return element


def nouveau_dossier(fiche: dict, racine: Path) -> str:
    dossier_id = creer({**fiche, "demo": True}, racine)
    FicheEvenement(emplacement(dossier_id, NOM_FICHE, racine)).remplacer(fiche)
    return dossier_id


def ajouter_rdvs(racine: Path, dossier_id: str, rdvs: list[tuple]) -> None:
    agenda = Agenda(emplacement_agenda(racine), dossier_id)

    for titre, debut, duree, lieu, avec, confirme in rdvs:
        agenda.tous.append(marquer({
            "titre": titre, "date_heure": debut, "duree_minutes": duree, "lieu": lieu, "avec": avec,
            "dossier_id": dossier_id, "type": None, "confirme": confirme
        }))

    agenda.sauvegarder()


def choisir(carnet: "Carnet", fiche: dict, statut: str, tarif: float = 0, poste: str | None = None, depuis: str | None = None) -> dict:
    prestataire_id = carnet.annuaire.ajouter(fiche)
    nouveau = not carnet.choix(prestataire_id)
    carnet.selectionner(prestataire_id, tarif, poste)
    choix = carnet.choix(prestataire_id)

    if nouveau and choix:
        marquer(choix)
        carnet.changer_statut(prestataire_id, statut, depuis)

    prestataire = carnet.trouver(prestataire_id)

    if prestataire is None:
        raise ValueError(f"Prestataire introuvable : {prestataire_id}")

    return prestataire


def dossier_mariage(racine: Path, aujourd_hui: date) -> str:
    for dossier in lister(racine):
        if meme_nom(dossier.get("noms") or "", NOMS_MARIAGE):
            return dossier["id"]

    return nouveau_dossier({
        "type_evenement": "Mariage", "noms": NOMS_MARIAGE, "date": str(aujourd_hui + timedelta(days=32)),
        "budget": 15000, "nombre_invites": 25, "allergies_interdits": ["fruits à coque"], "preferences_musicales": ["soul"]
    }, racine)


def poste(budget: "Budget", nom: str, montant: float) -> str:
    for existant in budget.postes:
        if meme_nom(existant["nom"].split(" (")[0], nom):
            return existant["nom"]

    budget.ajouter_poste(nom, montant)
    marquer(budget.postes[-1])
    budget.sauvegarder()

    return nom


def mariage(racine: Path, annuaire: "Annuaire", aujourd_hui: date) -> str:
    dossier_id = dossier_mariage(racine, aujourd_hui)
    carnet = Carnet(annuaire, emplacement(dossier_id, NOM_SELECTION, racine))
    traiteur = choisir(carnet, {"nom": "Saveurs d'Orient", "categorie": "Traiteur"}, "Réservé", 9500, "Traiteur")
    choisir(carnet, {"nom": "DJ Groove", "categorie": "DJ / Musiciens", "contact": "Yanis", "telephone": "06 45 67 89 10"}, "Réservé", 1200, "Musique")
    photographe = {"nom": "Studio Lumière", "categorie": "Photographe", "contact": "Julien", "telephone": "06 98 76 54 32"}
    choisir(carnet, photographe, "Devis demandé", 2400, "Photographe", str(aujourd_hui - timedelta(days=8)))
    fiche_fleuriste = {"nom": "Fleurs de Lune", "categorie": "Fleuriste", "contact": "Léna", "telephone": "06 11 22 33 44"}
    fleuriste = choisir(carnet, fiche_fleuriste, "Devis reçu", 1500, "Fleuriste")

    budget = Budget(emplacement(dossier_id, "budget_data", racine))
    poste_traiteur = poste(budget, "Traiteur", 9500)
    poste(budget, "Fleuriste", 1500)
    budget.ajouter_facture(poste_traiteur, "Acompte Saveurs d'Orient", 2850, str(aujourd_hui - timedelta(days=3)), False)
    marquer(next(element for element in budget.postes if element["nom"] == poste_traiteur)["factures"][-1])
    budget.sauvegarder()

    devis = CarnetDevis(emplacement(dossier_id, "devis_data", racine))
    devis.ajouter_devis(
        "Fleurs de Lune", fleuriste["id"], NOMS_MARIAGE,
        [{"designation": "Arche de cérémonie", "quantite": 1, "prix_unitaire": 650},
         {"designation": "Centres de table", "quantite": 12, "prix_unitaire": 55}],
        20.0, 30, 30, "Acompte à la signature, solde le jour de l'événement."
    )
    marquer(devis.devis[-1])
    devis.changer_statut(devis.devis[-1]["numero"], "Envoyé")

    messagerie = Messagerie(emplacement(dossier_id, "messages_data", racine))
    messagerie.ajouter(
        suggestion("demo_menu", "libre", destinataire_prestataire(traiteur), {}),
        "Bonjour Nadia, pourriez-vous nous envoyer la version finale du menu ? Merci !"
    )
    marquer(messagerie.messages[-1])
    messagerie.sauvegarder()

    ajouter_rdvs(racine, dossier_id, [
        ("Dégustation du menu", a_heure(aujourd_hui, 10), 90, "Saveurs d'Orient", "Saveurs d'Orient", True),
        ("Essayage robe", a_heure(aujourd_hui, 15), 60, "Atelier Blanche", "Léa", False)
    ])

    return FicheEvenement(emplacement(dossier_id, NOM_FICHE, racine)).donnees["date"]


def anniversaire(racine: Path, annuaire: "Annuaire", date_mariage: str) -> None:
    dossier_id = nouveau_dossier({
        "type_evenement": "Anniversaire", "noms": "Tom", "date": date_mariage,
        "lieu": "Rooftop Le Perchoir", "budget": 4000, "nombre_invites": 60,
        "personne_fetee": "Tom", "age": 40, "surprise": True
    }, racine)
    carnet = Carnet(annuaire, emplacement(dossier_id, NOM_SELECTION, racine))
    choisir(carnet, {"nom": "DJ Groove", "categorie": "DJ / Musiciens"}, "Réservé", 800, "Musique")


def baby_shower(racine: Path, aujourd_hui: date) -> None:
    dossier_id = nouveau_dossier({
        "type_evenement": "Baby shower", "noms": "Inès et Malik", "date": str(aujourd_hui + timedelta(days=20)),
        "nombre_invites": 25, "allergies_interdits": ["lactose"], "gender_reveal": True,
        "date_naissance": str(aujourd_hui + timedelta(days=60))
    }, racine)
    FicheEvenement(emplacement(dossier_id, NOM_FICHE, racine)).definir_consentement("consentement_sante", consentement(True))
    ajouter_rdvs(racine, dossier_id, [
        ("Visite de salle", a_heure(aujourd_hui, 15, 30), 60, "Salle des Tilleuls", "Inès", False)
    ])


def creer_demo(racine: Path = RACINE, aujourd_hui: date | None = None) -> None:
    aujourd_hui = aujourd_hui or date.today()
    annuaire = Annuaire(emplacement_annuaire(racine))
    date_mariage = mariage(racine, annuaire, aujourd_hui)
    anniversaire(racine, annuaire, date_mariage)
    baby_shower(racine, aujourd_hui)
    ecrire_etat("demo_active", True, racine)


def demo_active(racine: Path = RACINE) -> bool:
    return bool(lire_etat(racine).get("demo_active"))


def demo_au_premier_lancement(racine: Path = RACINE) -> None:
    if lire_etat(racine).get("demo_initialisee"):
        return

    creer_demo(racine)
    ecrire_etat("demo_initialisee", True, racine)


def actualiser_rdvs(racine: Path = RACINE, aujourd_hui: date | None = None) -> bool:
    jour = (aujourd_hui or date.today()).isoformat()
    rdvs = charger_donnees(emplacement_agenda(racine), [])
    passes = [rdv for rdv in rdvs if rdv.get("demo") and rdv["date_heure"][:10] < jour]

    for rdv in passes:
        rdv["date_heure"] = jour + rdv["date_heure"][10:]

    if passes:
        sauvegarder_donnees(emplacement_agenda(racine), rdvs)

    return bool(passes)


def sans_marques(donnees: Any) -> Any:
    if isinstance(donnees, list):
        return [sans_marques(element) for element in donnees if not (isinstance(element, dict) and element.get("demo"))]

    if isinstance(donnees, dict):
        return {cle: sans_marques(valeur) for cle, valeur in donnees.items()}

    return donnees


def retirer_demo(racine: Path = RACINE) -> None:
    for dossier in lister(racine):
        if dossier.get("demo"):
            supprimer(dossier["id"], racine)
            continue

        for nom in NOMS_MARQUES:
            cible = emplacement(dossier["id"], nom, racine)
            donnees = charger_donnees(cible, None)

            if donnees is not None:
                sauvegarder_donnees(cible, sans_marques(donnees))

    sauvegarder_donnees(emplacement_agenda(racine), sans_marques(charger_donnees(emplacement_agenda(racine), [])))
    ecrire_etat("demo_active", False, racine)
