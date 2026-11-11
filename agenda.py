from datetime import datetime, timedelta

from storage import load_json, save_json


class Agenda:
    def __init__(self, file_path="./agenda_data.json"):
        self.file_path = file_path
        self.rdvs = []
        self.load()

    def load(self):
        self.rdvs = load_json(self.file_path, [])

    def save(self):
        save_json(self.file_path, self.rdvs)

    def detecter_conflit(self, date_heure, duree_minutes):
        debut = datetime.fromisoformat(date_heure)
        fin = debut + timedelta(minutes=duree_minutes)

        for rdv in self.rdvs:
            autre_debut = datetime.fromisoformat(rdv["date_heure"])
            autre_fin = autre_debut + timedelta(minutes=rdv["duree_minutes"])

            if debut < autre_fin and autre_debut < fin:
                return rdv

        return None

    def add_rdv(self, titre, date_heure, duree_minutes, lieu, avec):
        conflit = self.detecter_conflit(date_heure, duree_minutes)

        if conflit:
            return conflit

        self.rdvs.append({
            "titre": titre,
            "date_heure": date_heure,
            "duree_minutes": duree_minutes,
            "lieu": lieu,
            "avec": avec
        })
        self.save()

        return None

    def supprimer_rdv(self, titre, date_heure):
        self.rdvs = [
            rdv for rdv in self.rdvs
            if not (rdv["titre"] == titre and rdv["date_heure"] == date_heure)
        ]
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
