import os
from datetime import datetime, timedelta


DOSSIER_CALENDRIER = 9
DOSSIER_BROUILLONS = 16
ELEMENT_RDV = 1
ELEMENT_MAIL = 0
FORMAT_FILTRE = "%d/%m/%Y %H:%M"


def outlook_disponible():
    try:
        import winreg
        import win32com.client
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Outlook.Application"))
    except (ImportError, OSError):
        return False

    return True


def dossier(numero):
    import win32com.client

    namespace = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    compte = os.environ.get("OUTLOOK_ACCOUNT", "").strip().lower()

    if not compte:
        return namespace.GetDefaultFolder(numero)

    for store in namespace.Stores:
        if store.DisplayName.lower() == compte:
            return store.GetDefaultFolder(numero)

    raise ValueError(f"Compte Outlook introuvable : {compte}")


def evenements(jours=7):
    debut = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fin = debut + timedelta(days=jours)
    elements = dossier(DOSSIER_CALENDRIER).Items
    elements.Sort("[Start]")
    elements.IncludeRecurrences = True
    filtre = f"[Start] >= '{debut:{FORMAT_FILTRE}}' AND [Start] < '{fin:{FORMAT_FILTRE}}'"

    return [
        {"titre": element.Subject, "debut": f"{element.Start:%Y-%m-%d %H:%M}", "lieu": element.Location}
        for element in elements.Restrict(filtre)
    ]


def creer_evenement(titre, debut, duree_minutes, lieu=""):
    rdv = dossier(DOSSIER_CALENDRIER).Items.Add(ELEMENT_RDV)
    rdv.Subject = titre
    rdv.Start = debut.strftime("%Y-%m-%d %H:%M")
    rdv.Duration = duree_minutes
    rdv.Location = lieu
    rdv.ReminderSet = True
    rdv.ReminderMinutesBeforeStart = 60
    rdv.Save()


def creer_brouillon(destinataires, objet, corps):
    mail = dossier(DOSSIER_BROUILLONS).Items.Add(ELEMENT_MAIL)
    mail.To = destinataires
    mail.Subject = objet
    mail.Body = corps
    mail.Save()
