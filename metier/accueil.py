from datetime import date, datetime, timedelta

from metier.agenda import Agenda, bornes, conflits, type_rdv
from metier.budget import Budget, POSTE_ORGANISATION
from config.evenements import CHAMPS_ESSENTIELS
from donnees.dossiers import RACINE, FICHIER_FICHE, FICHIER_SELECTION, chemin, chemin_agenda, chemin_annuaire, lister, libelle_dossier
from donnees.event_state import EventSheet, renseigne
from metier.messages import MODIFIABLES, Messagerie, detecter_messages
from metier.prestataires import Annuaire, Carnet, reservations_en_double


JOURS_SURVEILLANCE = 45

JOURS_PAIEMENT = 7

JOURS_CONFIRMATION = 7


def champs_a_definir(fiche):
    return [libelle.lower() for cle, libelle in CHAMPS_ESSENTIELS.items() if not renseigne(fiche.get(cle))]


def jours_avant(fiche, aujourd_hui):
    try:
        return (date.fromisoformat(fiche["date"]) - aujourd_hui).days
    except (TypeError, ValueError, KeyError):
        return None


def a_surveiller(fiche, aujourd_hui):
    jours = jours_avant(fiche, aujourd_hui)
    return jours is not None and 0 <= jours <= JOURS_SURVEILLANCE


def sens_facture(facture):
    return "client" if facture["poste"] == POSTE_ORGANISATION else "prestataire"


def confirmations_attendues(rdvs, maintenant):
    limite = maintenant + timedelta(days=JOURS_CONFIRMATION)
    return [
        rdv for rdv in rdvs
        if rdv["avec"] and not rdv.get("confirme") and maintenant <= bornes(rdv)[0] <= limite
    ]


def avec_dossier(rdv, libelles):
    return {**rdv, "type": type_rdv(rdv), "dossier": libelles.get(rdv.get("dossier_id"), "Sans dossier")}


def reservations(carnet, fiche, origine):
    return [
        {"prestataire_id": prestataire["id"], "nom": prestataire["nom"], "date": fiche.get("date"), **origine}
        for prestataire in carnet.prestataires if prestataire["statut"] == "Réservé"
    ]


def doubles_reservations(racine=RACINE):
    annuaire = Annuaire(chemin_annuaire(racine))
    toutes = []

    for dossier in lister(racine):
        carnet = Carnet(annuaire, chemin(dossier["id"], FICHIER_SELECTION, racine))
        toutes += reservations(carnet, dossier, {"dossier_id": dossier["id"], "dossier": libelle_dossier(dossier)})

    return reservations_en_double(toutes)


def synthese(racine=RACINE, maintenant=None):
    maintenant = maintenant or datetime.now()
    aujourd_hui = maintenant.date()
    agenda = Agenda(chemin_agenda(racine))
    annuaire = Annuaire(chemin_annuaire(racine))
    libelles = {}
    toutes_reservations = []
    resultat = {"rdvs_du_jour": [], "a_faire": [], "paiements": [], "a_surveiller": [], "conflits": [], "doubles_reservations": []}

    for dossier in lister(racine):
        dossier_id = dossier["id"]
        fiche = EventSheet(chemin(dossier_id, FICHIER_FICHE, racine)).data
        libelles[dossier_id] = libelle_dossier(fiche)
        agenda.pour_dossier(dossier_id)
        budget = Budget(chemin(dossier_id, "budget_data.json", racine))
        messagerie = Messagerie(chemin(dossier_id, "messages_data.json", racine))
        carnet = Carnet(annuaire, chemin(dossier_id, FICHIER_SELECTION, racine))
        suggestions = messagerie.a_preparer(detecter_messages(fiche, carnet, agenda, budget))
        origine = {"dossier_id": dossier_id, "dossier": libelles[dossier_id]}
        toutes_reservations += reservations(carnet, fiche, origine)

        resultat["a_faire"].append({
            **origine,
            "a_valider": len(messagerie.par_statut(*MODIFIABLES)),
            "a_envoyer": len(messagerie.par_statut("validé")),
            "relances": sum(suggestion["type"] == "relance" for suggestion in suggestions),
            "a_preparer": sum(suggestion["type"] != "relance" for suggestion in suggestions),
            "confirmations": confirmations_attendues(agenda.rdvs, maintenant),
            "a_definir": champs_a_definir(fiche) if a_surveiller(fiche, aujourd_hui) else []
        })

        resultat["paiements"] += [
            {**facture, **origine, "sens": sens_facture(facture)}
            for facture in budget.factures_a_payer()
            if facture["jours_restants"] <= JOURS_PAIEMENT
        ]

        if a_surveiller(fiche, aujourd_hui):
            resultat["a_surveiller"].append({
                **origine, "jours": jours_avant(fiche, aujourd_hui), "manquants": champs_a_definir(fiche)
            })

    resultat["a_faire"] = [
        element for element in resultat["a_faire"]
        if any(element[cle] for cle in ("a_valider", "a_envoyer", "relances", "a_preparer", "confirmations", "a_definir"))
    ]
    resultat["doubles_reservations"] = reservations_en_double(toutes_reservations)
    resultat["a_surveiller"].sort(key=lambda element: element["jours"])

    resultat["rdvs_du_jour"] = [
        avec_dossier(rdv, libelles) for rdv in sorted(agenda.tous, key=lambda rdv: rdv["date_heure"])
        if bornes(rdv)[0].date() == aujourd_hui
    ]
    resultat["conflits"] = [
        (avec_dossier(premier, libelles), avec_dossier(second, libelles))
        for premier, second in conflits(agenda.tous)
        if bornes(second)[1] >= maintenant
    ]

    return resultat
