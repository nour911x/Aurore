from datetime import datetime, timedelta

from donnees.stockage import charger_json, premier, sauvegarder_json


TYPES_RDV = {
    "Essayage": ["essayage"],
    "Visite": ["visite"],
    "Dégustation": ["dégustation", "degustation"],
    "Réunion": ["réunion", "reunion", "point", "brief"],
    "Appel": ["appel", "visio"]
}

AUTRE_TYPE = "Autre"


def deviner_type(titre: str) -> str:
    texte = (titre or "").lower()

    for type_rdv, mots in TYPES_RDV.items():
        if any(mot in texte for mot in mots):
            return type_rdv

    return AUTRE_TYPE


def type_rdv(rdv: dict) -> str:
    return rdv.get("type") or deviner_type(rdv["titre"])


def bornes(rdv: dict) -> tuple:
    debut = datetime.fromisoformat(rdv["date_heure"])
    return debut, debut + timedelta(minutes=rdv["duree_minutes"])


def conflits(rdvs: list[dict]) -> list[tuple]:
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
    def __init__(self, chemin_fichier: str, dossier_id: str | None = None) -> None:
        self.chemin_fichier = chemin_fichier
        self.dossier_id = dossier_id
        self.tous: list[dict] = []
        self.charger()

    @property
    def rdvs(self) -> list[dict]:
        return [rdv for rdv in self.tous if rdv.get("dossier_id") == self.dossier_id]

    def pour_dossier(self, dossier_id: str) -> None:
        self.dossier_id = dossier_id

    def charger(self) -> None:
        self.tous = charger_json(self.chemin_fichier, [])

    def sauvegarder(self) -> None:
        sauvegarder_json(self.chemin_fichier, self.tous)

    def detecter_conflit(self, date_heure: str, duree_minutes: int) -> dict | None:
        debut = datetime.fromisoformat(date_heure)
        fin = debut + timedelta(minutes=duree_minutes)

        for rdv in self.tous:
            autre_debut, autre_fin = bornes(rdv)

            if debut < autre_fin and autre_debut < fin:
                return rdv

        return None

    def ajouter_rdv(self, titre: str, date_heure: str, duree_minutes: int, lieu: str, avec: str, type_choisi: str | None = None) -> dict | None:
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
        self.sauvegarder()

        return None

    def supprimer_rdv(self, titre: str, date_heure: str) -> None:
        self.tous = [
            rdv for rdv in self.tous
            if not (rdv["titre"] == titre and rdv["date_heure"] == date_heure and rdv.get("dossier_id") == self.dossier_id)
        ]
        self.sauvegarder()

    def trouver(self, titre: str, date_heure: str, dossier_id: str | None) -> dict | None:
        return premier(self.tous, titre=titre, date_heure=date_heure, dossier_id=dossier_id)

    def confirmer(self, titre: str, date_heure: str, dossier_id: str | None) -> None:
        rdv = self.trouver(titre, date_heure, dossier_id)

        if rdv:
            rdv["confirme"] = True
            self.sauvegarder()

    def rdvs_a_venir(self) -> list[dict]:
        maintenant = datetime.now()
        futurs = [
            rdv for rdv in self.rdvs
            if datetime.fromisoformat(rdv["date_heure"]) >= maintenant
        ]

        return sorted(futurs, key=lambda rdv: rdv["date_heure"])

    def rdvs_proches(self, jours: int = 7) -> list[dict]:
        limite = datetime.now() + timedelta(days=jours)

        return [
            rdv for rdv in self.rdvs_a_venir()
            if datetime.fromisoformat(rdv["date_heure"]) <= limite
        ]

    def exporter_ics(self, rdvs: list[dict] | None = None) -> str:
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
