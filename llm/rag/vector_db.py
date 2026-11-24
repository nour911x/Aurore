import chromadb


MODELE_EMBEDDING = "distiluse-base-multilingual-cased-v2"

COLLECTION = "documents"

NOMBRE_EXTRAITS = 20


def charger_modele():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELE_EMBEDDING)


class VectorDB:
    def __init__(self, chemin, modele=None):
        self.modele = modele or charger_modele()
        self.collection = ouvrir_collection(chemin)


    def vectoriser(self, textes):
        return self.modele.encode(textes, batch_size=64, normalize_embeddings=True).tolist()


    def ajouter_document(self, dossier_id, document_id, extraits):
        textes = [extrait["texte"] for extrait in extraits]
        self.collection.add(
            ids=[f"{document_id}_{numero}" for numero in range(len(extraits))],
            documents=textes,
            embeddings=self.vectoriser(textes),
            metadatas=[
                {"dossier_id": dossier_id, "document_id": document_id, "document": extrait["document"], "page": extrait["page"]}
                for extrait in extraits
            ]
        )


    def supprimer_document(self, document_id):
        self.collection.delete(where={"document_id": document_id})


    def chercher(self, question, dossier_id, nombre=NOMBRE_EXTRAITS):
        resultats = self.collection.query(
            query_embeddings=self.vectoriser([question]), n_results=nombre, where={"dossier_id": dossier_id}
        )

        return [
            {"texte": texte, "document": infos["document"], "page": infos["page"]}
            for texte, infos in zip(resultats["documents"][0], resultats["metadatas"][0], strict=True)
        ]


def ouvrir_collection(chemin):
    return chromadb.PersistentClient(path=str(chemin)).get_or_create_collection(
        name=COLLECTION, metadata={"modele": MODELE_EMBEDDING}
    )


def supprimer_dossiers_absents(chemin, dossiers_presents):
    collection = ouvrir_collection(chemin)
    indexes = {infos["dossier_id"] for infos in collection.get(include=["metadatas"])["metadatas"]}

    for dossier_id in indexes - set(dossiers_presents):
        collection.delete(where={"dossier_id": dossier_id})
