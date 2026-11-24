from llm.rag.agent_rag import AgentRag
from llm.rag.extraits import baliser


class RerankingAgent(AgentRag):
    fichier_prompt = "reclassement.txt"


    def trier(self, question, extraits):
        if not extraits:
            return []

        numeros = self.repondre_en_json(f"Question : {question}\n\n{baliser(extraits)}").get("numeros")

        if not isinstance(numeros, list):
            return []

        valides = [numero for numero in numeros if type(numero) is int and 1 <= numero <= len(extraits)]

        return [extraits[numero - 1] for numero in dict.fromkeys(valides)]
