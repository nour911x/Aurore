from groq import Groq

from dotenv import load_dotenv
import os
import json
import re


class ConversationAgent:
    def __init__(self):
        load_dotenv()
        self.groq_client = Groq(api_key=os.environ["GROQ_KEY"])
        self.conversation_history = [
                {
                    "role": "system",
                    "content": self.read_file(file_path="./context.txt")
                }
            ]


    @staticmethod
    def read_file(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()


    def get_conversation_history(self):
        return self.conversation_history[1: ]


    def update_conversation_history(self, role, content):
        self.conversation_history.append(
            {
            "role": role,
            "content": content,
            }
        )


    def ask_llm(self, text_interaction):

        self.update_conversation_history(role="user", content=text_interaction)

        response = self.groq_client.chat.completions.create(
            messages=self.conversation_history,
            model="openai/gpt-oss-120b",
            include_reasoning=False,
        ).choices[0].message.content


        self.update_conversation_history(role="assistant", content=response)

        return response


    def extract_event_info(self, current_data):
        instruction = (
            "Voici la fiche actuelle de l'événement au format JSON :\n"
            f"{json.dumps(current_data, ensure_ascii=False)}\n\n"
            "En te basant sur toute la conversation, renvoie cette fiche mise à jour. "
            "Réponds UNIQUEMENT avec le JSON, sans aucun texte autour. "
            "Garde exactement les mêmes clés. "
            "Garde les valeurs déjà connues sauf si la conversation les contredit. "
            "budget et nombre_invites sont des nombres, date au format AAAA-MM-JJ, "
            "allergies_interdits et prestataires sont des listes de textes courts."
        )

        response = self.groq_client.chat.completions.create(
            messages=self.conversation_history + [{"role": "user", "content": instruction}],
            model="openai/gpt-oss-120b",
            include_reasoning=False,
        ).choices[0].message.content

        match = re.search(r"\{.*\}", response, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return {}

        return {}


    def suggest_budget_postes(self, event_data):
        instruction = (
            "Voici la fiche de l'événement :\n"
            f"{json.dumps(event_data, ensure_ascii=False)}\n\n"
            "Propose une répartition du budget total en postes adaptés à ce type d'événement "
            "(par exemple lieu, traiteur, décoration, animation...). "
            "Réponds UNIQUEMENT avec un JSON : une liste d'objets ayant les clés "
            "nom (texte court) et montant_prevu (nombre entier). "
            "La somme des montant_prevu doit être égale au budget de la fiche."
        )

        response = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": instruction}],
            model="openai/gpt-oss-120b",
            include_reasoning=False,
        ).choices[0].message.content

        match = re.search(r"\[.*\]", response, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return []

        return []





























if __name__ == "__main__":
    agent = ConversationAgent()
    question = input("Pose ta question :\n")
    response = agent.ask_llm(question)
    print("\n")
    print(response)