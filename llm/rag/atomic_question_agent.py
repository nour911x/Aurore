from llm.rag.agent_rag import AgentRag


MAX_QUESTIONS = 5


class AtomicQuestionAgent(AgentRag):
    fichier_prompt = "questions_atomiques.txt"


    def decouper(self, demande):
        questions = self.repondre_en_json(demande).get("questions")

        if not isinstance(questions, list):
            return [demande]

        return [question for question in questions if isinstance(question, str)][:MAX_QUESTIONS] or [demande]
