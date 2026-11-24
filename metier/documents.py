import uuid
from datetime import date
from pathlib import Path
from typing import Any

from donnees.stockage import Emplacement, charger_donnees, premier, sauvegarder_donnees


class Documents:
    def __init__(self, emplacement: Emplacement, dossier: str | Path) -> None:
        self.emplacement = emplacement
        self.dossier = Path(dossier)
        self.documents: list[dict] = []
        self.charger()

    def charger(self) -> None:
        self.documents = charger_donnees(self.emplacement, [])

    def sauvegarder(self) -> None:
        sauvegarder_donnees(self.emplacement, self.documents)

    @staticmethod
    def nouvel_id() -> str:
        return uuid.uuid4().hex[:8]

    def verifier_nom(self, nom: str) -> None:
        if premier(self.documents, nom=nom):
            raise ValueError(f"« {nom} » est déjà dans ce dossier. Supprimez l'ancienne version d'abord.")

    def ajouter(self, document_id: str, nom: str, contenu: bytes, nombre_extraits: int) -> dict:
        self.verifier_nom(nom)
        self.dossier.mkdir(parents=True, exist_ok=True)
        document: dict[str, Any] = {
            "id": document_id, "nom": nom, "fichier": document_id + Path(nom).suffix.lower(),
            "date": date.today().isoformat(), "extraits": nombre_extraits
        }
        (self.dossier / document["fichier"]).write_bytes(contenu)
        self.documents.append(document)
        self.sauvegarder()

        return document

    def supprimer(self, document_id: str) -> None:
        document = premier(self.documents, id=document_id)

        if document is None:
            raise ValueError(f"Document introuvable : {document_id}")

        (self.dossier / document["fichier"]).unlink(missing_ok=True)
        self.documents.remove(document)
        self.sauvegarder()
