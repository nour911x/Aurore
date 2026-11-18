from datetime import datetime, timedelta

from storage import load_json, save_json


TYPES_RDV = {
    "Essayage": ["essayage"],
    "Visite": ["visite"],
    "Dégustation": ["dégustation", "degustation"],
    "Réunion": ["réunion", "reunion", "point", "brief"],
    "Appel": ["appel", "visio"]
}

AUTRE_TYPE = "Autre"


def deviner_type(titre):
    texte = (titre or "").lower()

    for type_rdv, mots in TYPES_RDV.items():
        if any(mot in texte for mot in mots):
            return type_rdv

    return AUTRE_TYPE


def type_rdv(rdv):
    return rdv.get("type") or deviner_type(rdv["titre"])


def bornes(rdv):
    debut = datetime.fromisoformat(rdv["date_heure"])
    return debut, debut + timedelta(minutes=rdv["duree_minutes"])


def conflits(rdvs):
    tries = sorted(rdvs, key=lambda rdv: rdv["date_heure"])
    paires = []

    for index, rdv in enumerate(tries):
        fin = bornes(rdv)[1]

        for suivant in tries[index + 1:]:
            if bornes(suivant)[0] >= fin:
                break

            paires.append((rdv, suivant))

    return paires


class Agenda:
    def __init__(self, file_path="./agenda_data.json", dossier_id=None):
        self.file_path = file_path
        self.dossier_id = dossier_id
        self.tous = []
        self.load()

    @property
    def rdvs(self):
        return [rdv for rdv in self.tous if rdv.get("dossier_id") == self.dossier_id]

    def pour_dossier(self, dossier_id):
        self.dossier_id = dossier_id

    def load(self):
        self.tous = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.tous)

    def detecter_conflit(self, date_heure, duree_minutes):
        debut = datetime.fromisoformat(date_heure)
        fin = debut + timedelta(minutes=duree_minutes)

        for rdv in self.tous:
            autre_debut, autre_fin = bornes(rdv)

            if debut < autre_fin and autre_debut < fin:
                return rdv

        return None

    def add_rdv(self, titre, date_heure, duree_minutes, lieu, avec, type_choisi=None):
        conflit = self.detecter_conflit(date_heure, duree_minutes)

        if conflit:
            return conflit

        self.tous.append({
            "titre": titre,
            "date_heure": date_heure,
            "duree_minutes": duree_minutes,
            "lieu": lieu,
            "avec": avec,
            "dossier_id": self.dossier_id,
            "type": type_choisi or deviner_type(titre),
            "confirme": False
        })
        self.save()

        return None

    def supprimer_rdv(self, titre, date_heure):
        self.tous = [
            rdv for rdv in self.tous
            if not (rdv["titre"] == titre and rdv["date_heure"] == date_heure and rdv.get("dossier_id") == self.dossier_id)
        ]
        self.save()

    def trouver(self, titre, date_heure, dossier_id):
        for rdv in self.tous:
            if rdv["titre"] == titre and rdv["date_heure"] == date_heure and rdv.get("dossier_id") == dossier_id:
                return rdv

        return None

    def confirmer(self, titre, date_heure, dossier_id):
        rdv = self.trouver(titre, date_heure, dossier_id)

        if rdv:
            rdv["confirme"] = True
            self.save()

    def rdvs_a_venir(self):
        maintenant = datetime.now()
        futurs = [
            rdv for rdv in self.rdvs
            if datetime.fromisoformat(rdv["date_heure"]) >= maintenant
        ]

        return sorted(futurs, key=lambda rdv: rdv["date_heure"])

    def rdvs_proches(self, jours=7):
        limite = datetime.now() + timedelta(days=jours)

        return [
            rdv for rdv in self.rdvs_a_venir()
            if datetime.fromisoformat(rdv["date_heure"]) <= limite
        ]

    def export_ics(self, rdvs=None):
        lignes = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AURORE//Event Planner//FR"
        ]

        for rdv in self.rdvs if rdvs is None else rdvs:
            debut = datetime.fromisoformat(rdv["date_heure"])
            fin = debut + timedelta(minutes=rdv["duree_minutes"])
            lignes += [
                "BEGIN:VEVENT",
                f"DTSTART:{debut.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{fin.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{rdv['titre']}",
                f"LOCATION:{rdv['lieu']}",
                f"DESCRIPTION:Avec {rdv['avec']} - organisé par AURORE",
                "END:VEVENT"
            ]

        lignes.append("END:VCALENDAR")

        return "\n".join(lignes)
