import json
from datetime import datetime

import outlook
from devis import totaux, lignes_valides
from invites import GROUPES, STATUTS_INVITE, REGIMES, nouvel_invite
from messages import TYPES_MESSAGE, destinataire_maries, destinataire_prestataire, suggestion
from prestataires import CATEGORIES, STATUTS, appliquer_statut, meme_nom


FORMAT_DATE = "%Y-%m-%d %H:%M"

TEXTE = {"type": "string"}
NOMBRE = {"type": "number"}
ENTIER = {"type": "integer"}
DATE_HEURE = {"type": "string", "description": "Date et heure au format AAAA-MM-JJ HH:MM"}
DATE = {"type": "string", "description": "Date au format AAAA-MM-JJ"}


def choix_parmi(options, description=""):
    return {"type": "string", "enum": options, "description": description}


def facultatif(schema):
    schema = {**schema, "type": [schema["type"], "null"]}

    if "enum" in schema:
        schema["enum"] = schema["enum"] + [None]

    return schema


def outil(nom, description, proprietes, requis=()):
    proprietes = {
        cle: schema if cle in requis else facultatif(schema)
        for cle, schema in proprietes.items()
    }

    return {
        "type": "function",
        "function": {
            "name": nom,
            "description": description,
            "parameters": {"type": "object", "properties": proprietes, "required": list(requis)}
        }
    }


CONFIRMATION = " À n'appeler qu'après confirmation explicite de l'utilisateur."

OUTILS = [
    outil("consulter_agenda", "Liste les rendez-vous à venir.", {"jours": ENTIER}),
    outil(
        "creer_rdv",
        "Crée un rendez-vous (essayage, visite, dégustation...). Refusé s'il chevauche un autre rendez-vous." + CONFIRMATION,
        {"titre": TEXTE, "date_heure": DATE_HEURE, "duree_minutes": ENTIER, "lieu": TEXTE, "avec": TEXTE},
        ["titre", "date_heure"]
    ),
    outil(
        "supprimer_rdv",
        "Supprime un rendez-vous retrouvé au préalable avec consulter_agenda." + CONFIRMATION,
        {"titre": TEXTE, "date_heure": DATE_HEURE},
        ["titre", "date_heure"]
    ),
    outil("consulter_budget", "Donne les postes de budget (prévu, engagé) et les factures à payer.", {}),
    outil(
        "ajouter_facture",
        "Ajoute une facture ou un acompte à un poste de budget existant." + CONFIRMATION,
        {"poste": TEXTE, "libelle": TEXTE, "montant": NOMBRE, "echeance": DATE, "payee": {"type": "boolean"}},
        ["poste", "libelle", "montant", "echeance"]
    ),
    outil("consulter_prestataires", "Liste les prestataires du carnet avec leur statut.", {"categorie": choix_parmi(CATEGORIES)}),
    outil(
        "ajouter_prestataire",
        "Ajoute un prestataire au carnet." + CONFIRMATION,
        {
            "nom": TEXTE, "categorie": choix_parmi(CATEGORIES), "telephone": TEXTE,
            "email": TEXTE, "tarif_indicatif": NOMBRE, "notes": TEXTE
        },
        ["nom", "categorie"]
    ),
    outil(
        "changer_statut_prestataire",
        "Change le statut d'un prestataire du carnet." + CONFIRMATION,
        {"nom": TEXTE, "statut": choix_parmi(STATUTS)},
        ["nom", "statut"]
    ),
    outil("consulter_deroule", "Donne le déroulé heure par heure du jour J (moments, lieux, intervenants).", {}),
    outil("consulter_invites","Donne les réponses des invités, le nombre de couverts, les régimes et les allergies.", {}),
    outil(
        "ajouter_invite",
        "Ajoute un invité à la liste." + CONFIRMATION,
        {"nom": TEXTE, "groupe": choix_parmi(GROUPES), "telephone": TEXTE, "email": TEXTE, "accompagnants": ENTIER},
        ["nom"]
    ),
    outil(
        "noter_reponse_invite",
        "Enregistre la réponse d'un invité (statut, régime, allergies)." + CONFIRMATION,
        {"nom": TEXTE, "statut": choix_parmi(STATUTS_INVITE), "regime": choix_parmi(REGIMES), "allergies": TEXTE},
        ["nom", "statut"]
    ),
    outil(
        "preparer_message",
        "Range un message rédigé dans l'onglet Messages, prêt à être envoyé par l'utilisateur. "
        "Le destinataire est le nom d'un prestataire du carnet, ou « mariés »." + CONFIRMATION,
        {"destinataire": TEXTE, "type": choix_parmi(list(TYPES_MESSAGE)), "contenu": TEXTE},
        ["destinataire", "contenu"]
    ),
    outil(
        "creer_devis",
        "Crée un devis (téléchargeable en PDF dans l'onglet Devis). L'émetteur est « AURORE » ou le nom d'un prestataire. "
        "N'invente jamais un prix : demande-le s'il manque." + CONFIRMATION,
        {
            "emetteur": TEXTE,
            "lignes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"designation": TEXTE, "quantite": NOMBRE, "prix_unitaire": NOMBRE},
                    "required": ["designation", "quantite", "prix_unitaire"]
                }
            },
            "tva": NOMBRE, "acompte_pourcent": NOMBRE, "validite_jours": ENTIER, "notes": TEXTE
        },
        ["emetteur", "lignes"]
    )
]

OUTILS_OUTLOOK = [
    outil("outlook_agenda", "Liste les événements du vrai calendrier Outlook de l'utilisateur.", {"jours": ENTIER}),
    outil(
        "outlook_creer_rdv",
        "Crée un rendez-vous dans le calendrier Outlook (vérifie d'abord outlook_agenda)." + CONFIRMATION,
        {"titre": TEXTE, "date_heure": DATE_HEURE, "duree_minutes": ENTIER, "lieu": TEXTE},
        ["titre", "date_heure"]
    ),
    outil(
        "outlook_brouillon",
        "Enregistre un mail en BROUILLON dans Outlook, jamais envoyé : l'utilisateur le relit et l'envoie lui-même." + CONFIRMATION,
        {"destinataires": TEXTE, "objet": TEXTE, "corps": TEXTE},
        ["destinataires", "objet", "corps"]
    )
]


OUTILS_PAR_ESPACE = {
    "Mariés": {schema["function"]["name"] for schema in OUTILS} - {"creer_devis"},
    "Prestataire": {"consulter_agenda", "creer_rdv", "supprimer_rdv", "consulter_invites", "consulter_deroule", "creer_devis"}
}


def lire_date_heure(texte):
    return datetime.strptime(texte.strip()[:16].replace("T", " "), FORMAT_DATE)


def chercher_par_nom(elements, nom):
    for element in elements:
        if meme_nom(element["nom"], nom):
            return element

    raise ValueError(f"« {nom} » est introuvable. Consulte d'abord la liste.")


class Outils:
    def __init__(self, event_sheet, agenda, budget, carnet, liste_invites, messagerie, carnet_devis, jour_j):
        self.jour_j = jour_j
        self.event_sheet = event_sheet
        self.agenda = agenda
        self.budget = budget
        self.carnet = carnet
        self.liste_invites = liste_invites
        self.messagerie = messagerie
        self.carnet_devis = carnet_devis
        self.avec_outlook = outlook.outlook_disponible()
        self.espace = "Wedding planner"
        self.prestataire = None

    def pour_espace(self, espace, prestataire=None):
        self.espace = espace
        self.prestataire = prestataire

    def schemas(self):
        schemas = OUTILS + (OUTILS_OUTLOOK if self.avec_outlook and self.espace != "Prestataire" else [])
        autorises = OUTILS_PAR_ESPACE.get(self.espace)

        return [schema for schema in schemas if autorises is None or schema["function"]["name"] in autorises]

    def executer(self, nom, arguments):
        noms_autorises = {schema["function"]["name"] for schema in self.schemas()}

        if nom not in noms_autorises:
            return json.dumps({"erreur": f"outil non disponible dans cet espace : {nom}"}, ensure_ascii=False)

        arguments = {cle: valeur for cle, valeur in arguments.items() if valeur is not None}

        if self.prestataire and nom in ("creer_rdv", "creer_devis"):
            arguments["avec" if nom == "creer_rdv" else "emetteur"] = self.prestataire["nom"]

        try:
            resultat = getattr(self, nom)(**arguments)
        except Exception as erreur:
            resultat = {"erreur": str(erreur)}

        return json.dumps(resultat, ensure_ascii=False, default=str)

    def rdvs_visibles(self):
        if not self.prestataire:
            return self.agenda.rdvs

        return [rdv for rdv in self.agenda.rdvs if meme_nom(rdv["avec"], self.prestataire["nom"])]

    def consulter_agenda(self, jours=30):
        visibles = self.rdvs_visibles()
        return [rdv for rdv in self.agenda.rdvs_proches(jours=jours) if rdv in visibles]

    def creer_rdv(self, titre, date_heure, duree_minutes=60, lieu="", avec=""):
        debut = lire_date_heure(date_heure).isoformat()
        conflit = self.agenda.add_rdv(titre, debut, duree_minutes, lieu, avec)

        if conflit and self.prestataire:
            return {"erreur": "ce créneau est déjà pris dans l'agenda du mariage, propose un autre horaire"}

        if conflit:
            return {"erreur": "conflit d'horaire", "rdv_existant": conflit}

        return {"statut": "rendez-vous créé", "titre": titre, "debut": debut}

    def supprimer_rdv(self, titre, date_heure):
        debut = lire_date_heure(date_heure)

        for rdv in self.rdvs_visibles():
            if meme_nom(rdv["titre"], titre) and lire_date_heure(rdv["date_heure"]) == debut:
                self.agenda.supprimer_rdv(rdv["titre"], rdv["date_heure"])
                return {"statut": "rendez-vous supprimé", "titre": rdv["titre"]}

        raise ValueError("Aucun rendez-vous ne correspond à ce titre et à cette heure.")

    def consulter_budget(self):
        return {
            "budget_total": self.event_sheet.data["budget"],
            "postes": [
                {"nom": poste["nom"], "prevu": poste["montant_prevu"], "engage": self.budget.engage_du_poste(poste)}
                for poste in self.budget.postes
            ],
            "factures_a_payer": self.budget.factures_a_payer()
        }

    def ajouter_facture(self, poste, libelle, montant, echeance, payee=False):
        poste_trouve = chercher_par_nom(self.budget.postes, poste)
        self.budget.add_facture(poste_trouve["nom"], libelle, montant, echeance, payee)

        return {"statut": "facture ajoutée", "poste": poste_trouve["nom"]}

    def consulter_prestataires(self, categorie=None):
        return [
            {key: prestataire[key] for key in ["nom", "categorie", "statut", "telephone", "email", "tarif_indicatif", "notes"]}
            for prestataire in self.carnet.prestataires
            if categorie in (None, prestataire["categorie"])
        ]

    def ajouter_prestataire(self, nom, categorie, telephone="", email="", tarif_indicatif=0, notes=""):
        self.carnet.add_prestataire(nom, categorie, "", telephone, email, "", tarif_indicatif, None, notes)

        return {"statut": "prestataire ajouté", "nom": nom}

    def changer_statut_prestataire(self, nom, statut):
        prestataire = chercher_par_nom(self.carnet.prestataires, nom)
        appliquer_statut(self.carnet, self.event_sheet, prestataire, statut)

        return {"statut": f"{prestataire['nom']} est maintenant « {statut} »"}

    def consulter_deroule(self):
        return self.jour_j.deroule or {"info": "le déroulé du jour J n'a pas encore été construit"}

    def consulter_invites(self):
        return {"par_statut": dict(self.liste_invites.compter_par_statut()), **self.liste_invites.recap_traiteur()}

    def ajouter_invite(self, nom, groupe="Autre", telephone="", email="", accompagnants=0):
        self.liste_invites.remplacer(self.liste_invites.invites + [nouvel_invite(nom, groupe, telephone, email, accompagnants)])

        return {"statut": "invité ajouté", "nom": nom}

    def noter_reponse_invite(self, nom, statut, regime=None, allergies=None):
        invite = chercher_par_nom(self.liste_invites.invites, nom)
        invite["statut"] = statut
        invite["regime"] = regime or invite["regime"]
        invite["allergies"] = allergies or invite["allergies"]
        self.liste_invites.save()

        return {"statut": "réponse enregistrée", "invite": invite}

    def preparer_message(self, destinataire, contenu, type="libre"):
        if destinataire.strip().lower() in ("mariés", "maries", "les mariés"):
            contact = destinataire_maries(self.event_sheet.data)
        else:
            contact = destinataire_prestataire(chercher_par_nom(self.carnet.prestataires, destinataire))

        cle = f"agent_{datetime.now():%Y%m%d%H%M%S}_{contact['destinataire']}"
        self.messagerie.ajouter(suggestion(cle, type, contact, {}), contenu)

        return {"statut": "message prêt dans l'onglet Messages", "destinataire": contact["destinataire"]}

    def creer_devis(self, emetteur, lignes, tva=20, acompte_pourcent=30, validite_jours=30, notes=""):
        prestataire = None if emetteur.strip().upper() == "AURORE" else chercher_par_nom(self.carnet.prestataires, emetteur)
        nom_emetteur = prestataire["nom"] if prestataire else "AURORE - Wedding planner"
        lignes = lignes_valides(lignes)

        if not lignes:
            raise ValueError("Le devis doit contenir au moins une ligne avec une désignation.")

        self.carnet_devis.add_devis(
            nom_emetteur,
            prestataire["id"] if prestataire else None,
            self.event_sheet.data["noms"] or "Les mariés",
            lignes, tva, acompte_pourcent, validite_jours, notes
        )
        devis = self.carnet_devis.devis[-1]

        return {"statut": "devis créé, PDF dans l'onglet Devis", "numero": devis["numero"], **totaux(devis)}

    def synchroniser_outlook(self):
        a_envoyer = [rdv for rdv in self.agenda.rdvs_a_venir() if not rdv.get("outlook")]

        for rdv in a_envoyer:
            outlook.creer_evenement(rdv["titre"], lire_date_heure(rdv["date_heure"]), rdv["duree_minutes"], rdv["lieu"])
            rdv["outlook"] = True

        self.agenda.save()

        return len(a_envoyer)

    def outlook_agenda(self, jours=7):
        return outlook.evenements(jours)

    def outlook_creer_rdv(self, titre, date_heure, duree_minutes=60, lieu=""):
        outlook.creer_evenement(titre, lire_date_heure(date_heure), duree_minutes, lieu)

        return {"statut": "rendez-vous créé dans Outlook", "titre": titre}

    def outlook_brouillon(self, destinataires, objet, corps):
        outlook.creer_brouillon(destinataires, objet, corps)

        return {"statut": "brouillon enregistré dans Outlook, non envoyé"}
