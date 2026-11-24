import hashlib
import hmac
import secrets
import time
import uuid
from collections.abc import Callable
from datetime import date, timedelta
from typing import NamedTuple

from config.profils import ORGANISATEUR
from donnees.stockage import Emplacement, charger_donnees, sauvegarder_donnees


LONGUEUR_MOT_DE_PASSE = 12

PARAMETRES_SCRYPT = {"n": 2**15, "r": 8, "p": 1, "maxmem": 2**26}

DUREE_LIEN = timedelta(days=90)

ECHECS_AUTORISES = 5

DUREE_BLOCAGE = 60


class Acces(NamedTuple):
    profil: str
    dossier_id: str | None = None
    prestataire_id: str | None = None

    @property
    def par_lien(self) -> bool:
        return self.profil != ORGANISATEUR


def hacher(mot_de_passe: str, sel: bytes | None = None) -> str:
    sel = sel or secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mot_de_passe.encode(), salt=sel, **PARAMETRES_SCRYPT)

    return f"{sel.hex()}:{empreinte.hex()}"


def verifier(mot_de_passe: str, hache: str) -> bool:
    try:
        sel = bytes.fromhex(hache.split(":")[0])
    except ValueError:
        return False

    return bool(sel) and hmac.compare_digest(hacher(mot_de_passe, sel), hache)


def empreinte_jeton(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


class Tentatives:
    def __init__(self, horloge: Callable[[], float] = time.monotonic) -> None:
        self.horloge = horloge
        self.echecs = 0
        self.bloque_jusqu_a = 0.0

    def secondes_restantes(self) -> int:
        return max(0, round(self.bloque_jusqu_a - self.horloge()))

    def echec(self) -> None:
        self.echecs += 1

        if self.echecs >= ECHECS_AUTORISES:
            self.echecs = 0
            self.bloque_jusqu_a = self.horloge() + DUREE_BLOCAGE

    def reussite(self) -> None:
        self.echecs = 0


class LiensAcces:
    def __init__(self, emplacement: Emplacement) -> None:
        self.emplacement = emplacement
        self.liens: list[dict] = []
        self.charger()

    def charger(self) -> None:
        self.liens = charger_donnees(self.emplacement, [])

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.liens)

    def creer(self, profil: str, dossier_id: str, prestataire_id: str | None = None, aujourd_hui: date | None = None) -> str:
        jeton = secrets.token_urlsafe(32)
        self.liens.append({
            "id": uuid.uuid4().hex[:8], "empreinte": empreinte_jeton(jeton), "profil": profil,
            "dossier_id": dossier_id, "prestataire_id": prestataire_id,
            "expire_le": ((aujourd_hui or date.today()) + DUREE_LIEN).isoformat()
        })
        self.sauvegarder()

        return jeton

    def du_dossier(self, dossier_id: str, aujourd_hui: date | None = None) -> list[dict]:
        jour = (aujourd_hui or date.today()).isoformat()
        return [lien for lien in self.liens if lien["dossier_id"] == dossier_id and lien["expire_le"] >= jour]

    def acces(self, jeton: str, aujourd_hui: date | None = None) -> Acces | None:
        empreinte = empreinte_jeton(jeton)
        jour = (aujourd_hui or date.today()).isoformat()

        for lien in self.liens:
            if hmac.compare_digest(lien["empreinte"], empreinte) and lien["expire_le"] >= jour:
                return Acces(lien["profil"], lien["dossier_id"], lien["prestataire_id"])

        return None

    def revoquer(self, lien_id: str) -> None:
        self.liens = [lien for lien in self.liens if lien["id"] != lien_id]
        self.sauvegarder()
