from getpass import getpass
from pathlib import Path

from dotenv import set_key

from metier.acces import LONGUEUR_MOT_DE_PASSE, hacher


FICHIER_ENV = Path(__file__).with_name(".env")


def demander_mot_de_passe():
    while True:
        mot_de_passe = getpass("Nouveau mot de passe organisateur (rien ne s'affiche) : ")

        if len(mot_de_passe) < LONGUEUR_MOT_DE_PASSE:
            print(f"Trop court : {LONGUEUR_MOT_DE_PASSE} caractères minimum.")
        elif mot_de_passe != getpass("Confirmez : "):
            print("Les deux saisies sont différentes.")
        else:
            return mot_de_passe


if __name__ == "__main__":
    set_key(FICHIER_ENV, "MOT_DE_PASSE_HACHE", hacher(demander_mot_de_passe()))
    print("Mot de passe enregistré (haché) dans .env. Relancez AURORE.")
