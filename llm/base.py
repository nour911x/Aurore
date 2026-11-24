import json
import os
import re

from dotenv import load_dotenv
from groq import Groq


MODELE = "openai/gpt-oss-120b"
DELAI_REPONSE = 30
NOMBRE_ESSAIS = 3


class CleGroqManquante(RuntimeError):
    pass


class Agent:
    def __init__(self):
        load_dotenv()
        cle = os.environ.get("GROQ_KEY")

        if not cle:
            raise CleGroqManquante

        self.client_groq = Groq(api_key=cle, timeout=DELAI_REPONSE, max_retries=NOMBRE_ESSAIS)


    @staticmethod
    def lire_fichier(chemin_fichier):
        with open(chemin_fichier, encoding="utf-8") as fichier:
            return fichier.read()


    @staticmethod
    def extraire_json(reponse, motif, defaut):
        trouve = re.search(motif, reponse, re.DOTALL)

        if not trouve:
            return defaut

        try:
            return json.loads(trouve.group())
        except json.JSONDecodeError:
            return defaut


    def appel(self, messages, tools=None, modele=MODELE, **options):
        if tools:
            options["tools"] = tools

        return self.client_groq.chat.completions.create(
            messages=messages,
            model=modele,
            include_reasoning=False,
            **options
        ).choices[0].message


    def completer(self, messages, **options):
        return self.appel(messages, **options).content or ""
