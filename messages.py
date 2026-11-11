import uuid
from datetime import date, datetime

from storage import load_json, save_json


TYPES_MESSAGE = {
    "demande_devis": "Demande de devis",
    "relance": "Relance devis",
    "confirmation": "Demande de confirmation",
    "rappel_rdv": "Rappel de rendez-vous",
    "rappel_paiement": "Rappel de paiement",
    "envoi_devis": "Envoi du devis",
    "recap_traiteur": "Récapitulatif invités pour le traiteur",
    "envoi_moodboard": "Envoi du moodboard",
    "libre": "Message libre"
}

DELAI_RELANCE = 5
DELAI_CONFIRMATION = 3
DELAI_RAPPEL = 1
DELAI_PAIEMENT = 3


def destinataire_prestataire(prestataire):
    return {
        "destinataire": prestataire["nom"],
        "prestataire_id": prestataire["id"],
        "telephone": prestataire["telephone"],
        "email": prestataire["email"]
    }


def fiche_publique(prestataire):
    return {"nom": prestataire["nom"], "categorie": prestataire["categorie"], "statut": prestataire["statut"]}


def destinataire_maries(event_data):
    return {
        "destinataire": event_data["noms"] or "Les mariés",
        "prestataire_id": None,
        "telephone": event_data["telephone"],
        "email": event_data["email"]
    }


def suggestion(cle, type_message, destinataire, contexte):
    return {"cle": cle, "type": type_message, "contexte": contexte, **destinataire}


def suggestions_prestataires(carnet):
    aujourd_hui = date.today()
    suggestions = []

    for prestataire in carnet.prestataires:
        destinataire = destinataire_prestataire(prestataire)
        contexte = fiche_publique(prestataire)
        depuis = prestataire.get("statut_depuis", aujourd_hui.isoformat())

        if prestataire["statut"] == "À contacter":
            suggestions.append(suggestion(f"devis_{prestataire['id']}", "demande_devis", destinataire, contexte))

        if prestataire["statut"] == "Devis demandé" and (aujourd_hui - date.fromisoformat(depuis)).days >= DELAI_RELANCE:
            suggestions.append(suggestion(f"relance_{prestataire['id']}_{depuis}", "relance", destinataire, contexte))

    return suggestions


def suggestions_rdvs(agenda, carnet, event_data):
    suggestions = []

    for rdv in agenda.rdvs_proches(jours=DELAI_CONFIRMATION):
        jours_restants = (datetime.fromisoformat(rdv["date_heure"]).date() - date.today()).days
        type_message = "rappel_rdv" if jours_restants <= DELAI_RAPPEL else "confirmation"
        destinataires = [destinataire_maries(event_data)]
        prestataire = carnet.trouver_par_nom(rdv["avec"])

        if prestataire:
            destinataires.append(destinataire_prestataire(prestataire))

        for destinataire in destinataires:
            cle = f"{type_message}_{rdv['titre']}_{rdv['date_heure']}_{destinataire['destinataire']}"
            suggestions.append(suggestion(cle, type_message, destinataire, rdv))

    return suggestions


def suggestions_factures(budget, event_data):
    return [
        suggestion(f"paiement_{facture['poste']}_{facture['libelle']}", "rappel_paiement", destinataire_maries(event_data), facture)
        for facture in budget.factures_a_payer()
        if facture["jours_restants"] <= DELAI_PAIEMENT
    ]


def detecter_messages(event_data, carnet, agenda, budget):
    return (
        suggestions_prestataires(carnet)
        + suggestions_rdvs(agenda, carnet, event_data)
        + suggestions_factures(budget, event_data)
    )


class Messagerie:
    def __init__(self, file_path="./messages_data.json"):
        self.file_path = file_path
        self.messages = []
        self.load()

    def load(self):
        self.messages = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.messages)

    def cles_traitees(self):
        return {message["cle"] for message in self.messages}

    def a_preparer(self, suggestions):
        deja_traitees = self.cles_traitees()
        return [suggestion for suggestion in suggestions if suggestion["cle"] not in deja_traitees]

    def ajouter(self, suggestion, contenu, statut="à envoyer"):
        self.messages.append({
            "id": uuid.uuid4().hex[:8],
            "cle": suggestion["cle"],
            "type": suggestion["type"],
            "destinataire": suggestion["destinataire"],
            "prestataire_id": suggestion["prestataire_id"],
            "telephone": suggestion["telephone"],
            "email": suggestion["email"],
            "contenu": contenu,
            "statut": statut,
            "date": date.today().isoformat()
        })
        self.save()

    def trouver(self, message_id):
        for message in self.messages:
            if message["id"] == message_id:
                return message

        return None

    def modifier(self, message_id, **champs):
        message = self.trouver(message_id)

        if message:
            message.update(champs)
            self.save()

    def par_statut(self, statut):
        return [message for message in self.messages if message["statut"] == statut]
