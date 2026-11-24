from llm.rag.agent_rag import AgentRag
from llm.rag.atomic_question_agent import AtomicQuestionAgent
from llm.rag.extraits import baliser
from llm.rag.reranking_agent import RerankingAgent


REPONSE_INTROUVABLE = "Cette information ne figure pas dans les documents du dossier."


class Rag(AgentRag):
    fichier_prompt = "rag.txt"


    def __init__(self, vector_db):
        super().__init__()
        self.vector_db = vector_db
        self.agent_questions = AtomicQuestionAgent()
        self.agent_reclassement = RerankingAgent()


    def repondre_a_une_question(self, question, dossier_id):
        candidats = self.vector_db.chercher(question, dossier_id)
        extraits = self.agent_reclassement.trier(question, candidats)

        if not extraits:
            return {"question": question, "reponse": REPONSE_INTROUVABLE, "sources": []}

        reponse = self.repondre(f"Question : {question}\n\n{baliser(extraits)}")

        return {"question": question, "reponse": reponse, "sources": extraits}


    def interroger(self, demande, dossier_id):
        return [
            self.repondre_a_une_question(question, dossier_id)
            for question in self.agent_questions.decouper(demande)
        ]
