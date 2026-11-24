from pathlib import Path

from llm.base import Agent


DOSSIER_PROMPTS = Path(__file__).with_name("prompts")


class AgentRag(Agent):
    fichier_prompt = ""


    def repondre(self, contenu, **options):
        messages = [
            {"role": "system", "content": self.lire_fichier(DOSSIER_PROMPTS / self.fichier_prompt)},
            {"role": "user", "content": contenu}
        ]

        return self.completer(messages, temperature=0, **options) or ""


    def repondre_en_json(self, contenu):
        return self.extraire_json(self.repondre(contenu, response_format={"type": "json_object"}), r"\{.*\}", {})
