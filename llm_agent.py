from groq import Groq, APIError, BadRequestError
from PIL import Image, ImageOps

from dotenv import load_dotenv
from datetime import datetime
import base64
import io
import os
import json
import re


MODELE = "openai/gpt-oss-120b"
MODELE_VISION = "qwen/qwen3.8-27b"
MODELE_TRANSCRIPTION = "whisper-large-v3-turbo"
MAX_TOURS_OUTILS = 6
TAILLE_IMAGE_MAX = 1024
MAX_JETONS_DESCRIPTION = 350
MAX_JETONS_ANALYSE = 120
TEXTE_PHOTO_SEULE = "Voici une photo pour notre projet, qu'en penses-tu ?"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

PROFILS = {
    "Wedding planner": "un ou une wedding planner professionnel(le) qui gère le mariage de ses clients. Vouvoie-le ou la, ton professionnel.",
    "Mariés": "les futurs mariés qui organisent eux-mêmes leur mariage. Tutoie-les, ton chaleureux et complice.",
    "Prestataire": "un prestataire (traiteur, DJ, domaine...) qui travaille sur ce mariage. Vouvoie-le ou la, ton professionnel."
}


def date_du_jour():
    maintenant = datetime.now()
    return f"{JOURS[maintenant.weekday()]} {maintenant.day} {MOIS[maintenant.month - 1]} {maintenant.year}, {maintenant:%H:%M}"


def preparer_image(contenu):
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(contenu))).convert("RGB")
    image.thumbnail((TAILLE_IMAGE_MAX, TAILLE_IMAGE_MAX))
    tampon = io.BytesIO()
    image.save(tampon, format="JPEG", quality=85)

    return base64.b64encode(tampon.getvalue()).decode("utf-8")


def message_avec_image(texte, image):
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": texte},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}
        ]
    }


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


    def update_conversation_history(self, role, content, image=None, description=None):
        message = {"role": role, "content": content}

        if image:
            message["image"] = image
            message["description"] = description

        self.conversation_history.append(message)


    def historique_api(self):
        return [
            {
                "role": message["role"],
                "content": message["content"] + (f"\n\n[Photo jointe : {message['description']}]" if message.get("description") else "")
            }
            for message in self.conversation_history
        ]


    def decrire_image(self, image, question):
        instruction = (
            "Décris précisément cette photo envoyée pour l'organisation d'un événement : objets, couleurs, "
            "matières, style, ambiance, dimensions apparentes et texte visible. "
            f"Question de l'utilisateur à garder en tête : {question}"
        )

        return self.appel([message_avec_image(instruction, image)], modele=MODELE_VISION, max_tokens=MAX_JETONS_DESCRIPTION).content


    def transcribe(self, audio):
        return self.groq_client.audio.transcriptions.create(
            file=("audio.wav", audio),
            model=MODELE_TRANSCRIPTION,
            language="fr"
        ).text


    @staticmethod
    def consignes_session(profil, avec_outils):
        consignes = f"Nous sommes le {date_du_jour()}. Tu parles à {PROFILS[profil]}"

        if avec_outils:
            consignes += (
                " Tu as des outils pour agir sur l'agenda, le budget, les prestataires, les invités, "
                "les messages et les devis. Consulte avant d'agir (par exemple le carnet pour retrouver "
                "le nom exact d'un prestataire). Avant toute création, modification "
                "ou suppression, annonce précisément ce que tu vas faire et attends un « oui » explicite."
            )

        prestataire = getattr(avec_outils, "prestataire", None)
        fiche = None

        if prestataire:
            fiche = avec_outils.event_sheet.infos_pour_prestataire()
            consignes += (
                f" Ce prestataire est {prestataire['nom']} ({prestataire['categorie']}). "
                "Ne lui révèle jamais le budget du mariage, les autres prestataires, les notes internes "
                "ni les coordonnées des mariés. Tu ne vois et ne gères que ses propres rendez-vous et devis."
            )
        elif avec_outils:
            fiche = avec_outils.event_sheet.infos_sans_historique()

        if fiche:
            consignes += (
                f" Fiche actuelle de l'événement (à jour, utilise-la sans redemander ce qui y figure) : "
                f"{json.dumps(fiche, ensure_ascii=False)}"
            )

        return {"role": "system", "content": consignes}


    def ask_llm(self, text_interaction, profil="Mariés", outils=None, image=None):

        texte = text_interaction or TEXTE_PHOTO_SEULE
        image = preparer_image(image) if image else None
        description = self.decrire_image(image, texte) if image else None
        self.update_conversation_history(role="user", content=texte, image=image, description=description)
        historique = self.historique_api()
        messages = historique[:1] + [self.consignes_session(profil, outils)] + historique[1:]
        response = "Je n'ai pas réussi à terminer : trop d'actions à la suite. Peux-tu reformuler ?"

        for _ in range(MAX_TOURS_OUTILS):
            try:
                message = self.appel(messages, tools=outils.schemas() if outils else None)
            except BadRequestError:
                continue
            except APIError:
                self.conversation_history.pop()
                raise

            if not message.tool_calls:
                response = message.content
                break

            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [appel_outil.model_dump() for appel_outil in message.tool_calls]
            })

            for appel_outil in message.tool_calls:
                arguments = self.parse_json(appel_outil.function.arguments or "{}", r"\{.*\}", {})
                messages.append({
                    "role": "tool",
                    "tool_call_id": appel_outil.id,
                    "content": outils.executer(appel_outil.function.name, arguments)
                })

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
            "noms est un texte avec les prénoms du couple ou des personnes fêtées (ex : \"Léa et Karim\"), "
            "telephone et email sont des textes, "
            "allergies_interdits, preferences, preferences_musicales et prestataires "
            "sont des listes de textes courts."
        )

        response = self.complete(self.historique_api() + [{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\{.*\}", {})


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

        response = self.complete([{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\[.*\]", [])


    def suggest_devis_lignes(self, emetteur, categorie, event_data):
        instruction = (
            f"Tu prépares un brouillon de devis émis par : {emetteur} ({categorie}).\n\n"
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            "Propose les lignes de prestations adaptées à cet émetteur et à l'événement "
            "(nombre d'invités, allergies, préférences...). Les prix sont indicatifs, hors taxes, "
            "réalistes pour la France et cohérents avec le budget. "
            "Réponds UNIQUEMENT avec un JSON : une liste d'objets ayant les clés "
            "designation (texte court), quantite (nombre) et prix_unitaire (nombre)."
        )

        response = self.complete([{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\[.*\]", [])


    def analyser_photo(self, contenu, categories):
        instruction = (
            "Analyse cette photo prise lors d'un mariage. Réponds UNIQUEMENT avec un JSON ayant les clés : "
            f"categorie (une valeur parmi {json.dumps(categories, ensure_ascii=False)}), "
            "personnes (true si au moins un visage ou une personne est reconnaissable, sinon false), "
            "description (une phrase courte)."
        )
        message = self.appel([message_avec_image(instruction, preparer_image(contenu))], modele=MODELE_VISION, max_tokens=MAX_JETONS_ANALYSE)

        return self.parse_json(message.content or "", r"\{.*\}", {})


    def write_legende(self, sujet, event_data, consigne=""):
        instruction = (
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            f"Sujet du post : {sujet}\n\n{consigne}\n\n"
            "Rédige la légende d'un post Instagram pour le compte d'AURORE, organisatrice d'événements : "
            "2 à 4 phrases élégantes et chaleureuses, quelques emojis, puis une ligne de 6 à 10 hashtags en français. "
            "Ne donne aucun montant, aucune information privée, ni le nom des invités. "
            "Réponds uniquement avec la légende."
        )

        return self.complete([{"role": "user", "content": instruction}])


    def suggest_deroule(self, event_data, prestataires, rdvs):
        instruction = (
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            f"Prestataires réservés : {json.dumps(prestataires, ensure_ascii=False)}\n\n"
            f"Rendez-vous déjà prévus le jour J : {json.dumps(rdvs, ensure_ascii=False)}\n\n"
            "Construis le déroulé heure par heure du jour J, des préparatifs à la fin de soirée "
            "(12 à 18 moments), adapté à ce type d'événement, au lieu et aux prestataires réservés. "
            "Pour un mariage en France, repères habituels : préparatifs le matin, cérémonie vers 15h-16h, "
            "vin d'honneur ensuite pendant 2h environ, entrée des mariés et dîner vers 19h30-20h30, "
            "discours entre les plats, dessert et pièce montée vers 23h, ouverture du bal après le dessert, "
            "fin de soirée vers 3h-4h. Les prestataires arrivent avant les invités pour l'installation. "
            "Réponds UNIQUEMENT avec un JSON : une liste d'objets ayant les clés heure (format HH:MM), "
            "moment (titre court), lieu, intervenants (noms exacts des prestataires concernés, séparés par des virgules, "
            "ou les rôles comme « mariés », « témoins ») et details (une phrase)."
        )

        response = self.complete([{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\[.*\]", [])


    def write_faire_part(self, event_data):
        instruction = (
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            "Rédige le texte d'un faire-part élégant et chaleureux, écrit par les personnes fêtées, "
            "en 5 à 8 lignes : l'annonce, la date, le lieu, le thème s'il y en a un, "
            "et une demande de confirmation de présence. "
            "Ne commence pas par une formule d'adresse (le prénom de chaque invité sera ajouté avant). "
            "N'invente aucune information absente de la fiche. "
            "Réponds uniquement avec le texte, sans emoji ni markdown."
        )

        return self.complete([{"role": "user", "content": instruction}])


    def suggest_moodboard(self, event_data, elements):
        instruction = (
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            "À partir de toute la conversation et de la fiche, crée le moodboard du projet "
            "(style, saison, couleurs et goûts exprimés). "
            "Réponds UNIQUEMENT avec un JSON ayant les clés : "
            "titre (nom court du style, ex : \"Bohème champêtre\"), "
            "ambiance (2 ou 3 phrases), "
            "couleurs (liste de 5 objets avec nom et hex au format #RRGGBB), "
            "mots_cles (liste de 6 à 8 mots), "
            f"recherches (objet avec exactement les clés {json.dumps(elements, ensure_ascii=False)}, "
            "chaque valeur est une recherche Pinterest précise en français, ex : \"centre de table mariage bohème terracotta\")."
        )

        response = self.complete(self.historique_api() + [{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\{.*\}", {})


    def recommend_adresses(self, categorie, event_data, postes_budget):
        instruction = (
            f"Les mariés cherchent : {categorie}.\n\n"
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            f"Budget par poste : {json.dumps(postes_budget, ensure_ascii=False)}\n\n"
            "Conseille-les selon leur style et leur budget. Ne cite AUCUN nom de boutique ou de personne réelle. "
            "Réponds UNIQUEMENT avec un JSON ayant les clés : "
            "fourchette (texte, ex : \"800 - 1 500 €\"), "
            "conseil (2 phrases), "
            "types (liste de 3 ou 4 objets avec type, pourquoi et recherche : "
            "une recherche Google Maps courte, ex : \"créatrice robe de mariée bohème\"), "
            "questions (liste de 4 questions à poser)."
        )

        response = self.complete([{"role": "user", "content": instruction}])

        return self.parse_json(response, r"\{.*\}", {})


    @staticmethod
    def parse_json(response, pattern, default):
        match = re.search(pattern, response, re.DOTALL)

        if not match:
            return default

        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return default


    def appel(self, messages, tools=None, modele=MODELE, **options):
        if tools:
            options["tools"] = tools

        return self.groq_client.chat.completions.create(
            messages=messages,
            model=modele,
            include_reasoning=False,
            **options
        ).choices[0].message


    def complete(self, messages):
        return self.appel(messages).content


    def summarize_conversation(self):
        instruction = (
            "Résume cette conversation pour l'historique du dossier client, en 3 à 6 puces markdown : "
            "les décisions prises, les nouvelles informations sur le couple et ce qu'il reste à faire. "
            "Réponds uniquement avec les puces."
        )

        return self.complete(self.historique_api() + [{"role": "user", "content": instruction}])


    def prepare_briefing(self, rdv, event_data, historique, postes_budget, prestataire=None):
        instruction = (
            "Tu prépares le briefing d'AURORE juste avant un rendez-vous, pour arriver "
            "en connaissant parfaitement le dossier.\n\n"
            f"Rendez-vous : {json.dumps(rdv, ensure_ascii=False)}\n\n"
            f"Fiche du prestataire rencontré : {json.dumps(prestataire, ensure_ascii=False)}\n\n"
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            f"Historique des échanges : {json.dumps(historique, ensure_ascii=False)}\n\n"
            f"Budget par poste (prévu et déjà engagé) : {json.dumps(postes_budget, ensure_ascii=False)}\n\n"
            "Rédige en français et en markdown, court et concret, avec ces sections :\n"
            "### 👥 Le dossier en bref\n"
            "### 🎯 Ce qui compte pour ce rendez-vous\n"
            "(seulement les infos utiles ici : allergies pour une dégustation, goûts musicaux pour le DJ, "
            "style pour un essayage, nombre d'invités pour une visite de salle...)\n"
            "### 💶 Budget du poste concerné\n"
            "### ❓ Questions à poser\n"
            "### ⚠️ Points de vigilance\n\n"
            "N'invente rien : si une information manque, dis-le et propose de la demander pendant le rendez-vous."
        )

        return self.complete([{"role": "user", "content": instruction}])


    def write_message(self, type_message, destinataire, contexte, event_data, consigne=""):
        instruction = (
            f"Tu es AURORE, wedding planner. Rédige un message de type « {type_message} » "
            f"à envoyer par WhatsApp ou email à : {destinataire}.\n\n"
            f"Contexte : {json.dumps(contexte, ensure_ascii=False)}\n\n"
            f"Fiche de l'événement : {json.dumps(event_data, ensure_ascii=False)}\n\n"
            f"{consigne}\n\n"
            "Le message est court, chaleureux et professionnel, en français, prêt à être envoyé. "
            "Vouvoie le destinataire, n'invente aucune information absente du contexte "
            "et signe « AURORE - Organisation d'événements ». "
            "Pour un prestataire, ne cite aucun budget ni montant, sauf budget_prestation s'il figure dans la fiche. "
            "Réponds uniquement avec le texte du message."
        )

        return self.complete([{"role": "user", "content": instruction}])





























if __name__ == "__main__":
    agent = ConversationAgent()
    question = input("Pose ta question :\n")
    response = agent.ask_llm(question)
    print("\n")
    print(response)