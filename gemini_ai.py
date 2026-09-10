from groq import Groq
import sqlite3
import re
import time

# ==========================================================
# BASE DE CONNAISSANCES TRIKA
# ==========================================================

with open("trika_knowledge.txt", "r", encoding="utf-8") as f:
    connaissance = f.read()


# ==========================================================
# GROQ
# ==========================================================

# IMPORTANT :
# Mets ici ta NOUVELLE clé API Groq.
# Ne publie jamais cette clé sur GitHub ou dans ton code public.

API_KEY = "TA_NOUVELLE_CLE_GROQ"

client = Groq(
    api_key="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"
)


# ==========================================================
# MODELES GROQ
# ==========================================================

# Le premier est le modèle principal.
# Si celui-ci ne fonctionne plus, TRIKA essaie automatiquement
# les suivants.

MODELES_GROQ = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "groq/compound-mini"
]


# ==========================================================
# MODELE ACTUEL
# ==========================================================

# Le programme commence avec le premier modèle.

MODELE_ACTUEL = MODELES_GROQ[0]


# ==========================================================
# RECHERCHE DANS LE DICTIONNAIRE TRIKA
# ==========================================================

def rechercher_dans_dictionnaire(question):

    conn = None

    try:

        conn = sqlite3.connect(
            "dictionnaire.db",
            timeout=10
        )

        cursor = conn.cursor()

        mots = re.findall(
            r"[a-zA-ZÀ-ÿ'-]+",
            question.lower()
        )

        for mot in mots:

            # ------------------------------------------
            # Recherche Lingala → Français
            # ------------------------------------------

            cursor.execute(
                """
                SELECT francais
                FROM dictionnaire
                WHERE LOWER(lingala)=?
                """,
                (mot,)
            )

            resultat = cursor.fetchone()

            if resultat:

                return (
                    mot,
                    resultat[0],
                    "Lingala"
                )


            # ------------------------------------------
            # Recherche Français → Lingala
            # ------------------------------------------

            cursor.execute(
                """
                SELECT lingala
                FROM dictionnaire
                WHERE LOWER(francais)=?
                """,
                (mot,)
            )

            resultat = cursor.fetchone()

            if resultat:

                return (
                    mot,
                    resultat[0],
                    "Français"
                )


        return None

    except Exception as e:

        print(
            f"[TRIKA] Erreur dictionnaire : {e}"
        )

        return None

    finally:

        if conn:
            conn.close()


# ==========================================================
# APPEL INTELLIGENT À GROQ
# ==========================================================

def appeler_groq(messages):

    global MODELE_ACTUEL

    # ------------------------------------------------------
    # Le modèle qui fonctionne actuellement est essayé
    # en premier.
    # ------------------------------------------------------

    liste_modeles = [
        MODELE_ACTUEL
    ]

    for modele in MODELES_GROQ:

        if modele not in liste_modeles:

            liste_modeles.append(modele)


    # ------------------------------------------------------
    # ESSAI DES MODÈLES
    # ------------------------------------------------------

    for modele in liste_modeles:

        print(
            f"[TRIKA] Tentative avec le modèle : {modele}"
        )


        # --------------------------------------------------
        # 3 tentatives pour les erreurs temporaires
        # --------------------------------------------------

        for tentative in range(3):

            try:

                completion = client.chat.completions.create(

                    model=modele,

                    messages=messages,

                    temperature=0.1,

                    max_completion_tokens=1024,

                    timeout=30
                )


                # ------------------------------------------
                # RÉCUPÉRATION DE LA RÉPONSE
                # ------------------------------------------

                if (
                    completion
                    and completion.choices
                    and completion.choices[0].message
                ):

                    reponse = (
                        completion
                        .choices[0]
                        .message
                        .content
                    )


                    # --------------------------------------
                    # LE MODÈLE FONCTIONNE
                    # --------------------------------------

                    MODELE_ACTUEL = modele


                    print(
                        f"[TRIKA] Modèle utilisé : {modele}"
                    )


                    return reponse


                # ------------------------------------------
                # Réponse vide
                # ------------------------------------------

                print(
                    f"[TRIKA] Réponse vide avec {modele}"
                )

                break


            except Exception as e:

                erreur = str(e)

                erreur_min = erreur.lower()


                print(
                    f"[TRIKA] Erreur avec {modele} "
                    f"(tentative {tentative + 1}/3) : "
                    f"{erreur}"
                )


                # ------------------------------------------
                # MODÈLE SUPPRIMÉ / INDISPONIBLE
                # ------------------------------------------

                modele_indisponible = (

                    "decommissioned" in erreur_min

                    or "model_not_found" in erreur_min

                    or "model not found" in erreur_min

                    or "does not exist" in erreur_min

                    or "unknown model" in erreur_min

                    or "invalid model" in erreur_min

                )


                if modele_indisponible:

                    print(
                        f"[TRIKA] Le modèle {modele} "
                        f"n'est plus disponible."
                    )

                    # On passe directement au modèle suivant.

                    break


                # ------------------------------------------
                # ERREUR D'AUTHENTIFICATION
                # ------------------------------------------

                if (
                    "authentication" in erreur_min
                    or "invalid api key" in erreur_min
                    or "invalid_api_key" in erreur_min
                    or "unauthorized" in erreur_min
                    or "401" in erreur_min
                ):

                    print(
                        "[TRIKA] Problème avec la clé API Groq."
                    )

                    return (
                        "⚠️ Le service IA de TRIKA.TRAD "
                        "est temporairement indisponible.\n\n"
                        "Le problème concerne la connexion "
                        "au service IA."
                    )


                # ------------------------------------------
                # LIMITE DE REQUÊTES
                # ------------------------------------------

                limite = (

                    "rate limit" in erreur_min

                    or "rate_limit" in erreur_min

                    or "429" in erreur_min

                )


                if limite:

                    print(
                        f"[TRIKA] Limite atteinte avec {modele}."
                    )

                    # On passe au modèle suivant.

                    break


                # ------------------------------------------
                # ERREUR SERVEUR
                # ------------------------------------------

                serveur = (

                    "500" in erreur_min

                    or "502" in erreur_min

                    or "503" in erreur_min

                    or "504" in erreur_min

                    or "server error" in erreur_min

                    or "service unavailable" in erreur_min

                )


                if serveur:

                    print(
                        f"[TRIKA] Erreur serveur avec {modele}."
                    )

                    time.sleep(2)

                    continue


                # ------------------------------------------
                # AUTRE ERREUR
                # ------------------------------------------

                # On réessaie après une petite pause.

                if tentative < 2:

                    time.sleep(2)


        # --------------------------------------------------
        # Le modèle actuel n'a pas fonctionné.
        # Passage automatique au suivant.
        # --------------------------------------------------

        print(
            f"[TRIKA] Passage au modèle suivant..."
        )


    # ======================================================
    # TOUS LES MODÈLES ONT ÉCHOUÉ
    # ======================================================

    print(
        "[TRIKA] Aucun modèle Groq disponible."
    )


    return (
        "⚠️ Le service IA de TRIKA.TRAD "
        "est momentanément indisponible.\n\n"
        "Veuillez vérifier votre connexion Internet "
        "et réessayer dans quelques instants."
    )


# ==========================================================
# ASSISTANT TRIKA
# ==========================================================

def demander_a_trika(question):

    try:

        # ==================================================
        # VÉRIFICATION DE LA QUESTION
        # ==================================================

        if question is None:

            return (
                "Veuillez saisir une question."
            )


        question = str(question).strip()


        if not question:

            return (
                "Veuillez saisir une question."
            )


        # ==================================================
        # RECHERCHE DU MOT DANS LE DICTIONNAIRE
        # ==================================================

        info = rechercher_dans_dictionnaire(
            question
        )


        # ==================================================
        # PROMPT PRINCIPAL DE TRIKA
        # ==================================================

        prompt_systeme = """
Tu es TRIKA, l'assistant officiel de TRIKA.TRAD.

Tu réponds toujours en français.

Tu aides les utilisateurs à comprendre et apprendre
le Lingala à partir des informations officielles
de TRIKA.TRAD.

RÈGLES ABSOLUES :

- N'invente JAMAIS une traduction.
- N'invente JAMAIS une phrase d'exemple.
- N'invente JAMAIS une règle de grammaire.
- N'invente JAMAIS une prononciation.
- N'invente JAMAIS une information présentée comme venant de TRIKA.TRAD.
- Ne remplace jamais une information du dictionnaire TRIKA
  par une connaissance générale d'Internet ou du modèle.

Si une phrase d'exemple fiable n'existe pas dans
la base de connaissances, réponds exactement :

"Aucun exemple fiable n'est disponible pour ce mot."

Si tu n'es pas certain d'une traduction, réponds exactement :

"Je ne possède pas cette information dans TRIKA.TRAD."

Si une information n'existe pas dans la base de connaissances,
dis-le clairement.

IMPORTANT :

Les informations fournies par TRIKA.TRAD sont prioritaires
sur tes connaissances générales.

Tu dois considérer le dictionnaire officiel de TRIKA.TRAD
comme la source de référence pour les traductions.

Tu ne dois jamais modifier une traduction fournie
par le dictionnaire.

Tu peux expliquer une information uniquement si cette
explication est compatible avec les connaissances fournies.

Tu dois être gentil, clair, pédagogique et professionnel.
"""


        # ==================================================
        # BASE DE CONNAISSANCES
        # ==================================================

        contexte = prompt_systeme + """

==============================
BASE DE CONNAISSANCES TRIKA
==============================

""" + connaissance


        # ==================================================
        # SI LE MOT EXISTE DANS SQLITE
        # ==================================================

        if info:

            mot, traduction, langue = info

            contexte += f"""

==============================
DICTIONNAIRE OFFICIEL
==============================

Mot trouvé :
{mot}

Langue :
{langue}

Traduction officielle TRIKA.TRAD :
{traduction}

IMPORTANT :

Cette traduction provient directement du dictionnaire
de TRIKA.TRAD.

Tu dois utiliser EXACTEMENT cette traduction.

Tu n'as pas le droit de proposer une autre traduction.

Si l'utilisateur demande une phrase d'exemple et qu'aucune
phrase fiable concernant ce mot n'est présente dans la
base de connaissances, réponds exactement :

"Aucun exemple fiable n'est disponible pour ce mot."
"""


        # ==================================================
        # SI LE MOT N'EST PAS DANS SQLITE
        # ==================================================

        else:

            contexte += """

==============================
MOT NON TROUVÉ
==============================

Le mot ou l'information demandée n'a pas été trouvée
dans le dictionnaire SQLite de TRIKA.TRAD.

Tu ne dois donc PAS inventer une traduction.

Si l'utilisateur demande une traduction que tu ne peux
pas confirmer avec les connaissances de TRIKA.TRAD,
réponds exactement :

"Je ne possède pas cette information dans TRIKA.TRAD."

Ne donne pas une traduction provenant de tes connaissances
générales.
"""


        # ==================================================
        # MESSAGES ENVOYÉS À GROQ
        # ==================================================

        messages = [

            {
                "role": "system",
                "content": contexte
            },

            {
                "role": "user",
                "content": question
            }

        ]


        # ==================================================
        # APPEL SÉCURISÉ À GROQ
        # ==================================================

        reponse = appeler_groq(
            messages
        )


        # ==================================================
        # RETOUR DE LA RÉPONSE
        # ==================================================

        return reponse


    # ======================================================
    # PROTECTION GÉNÉRALE
    # ======================================================

    except Exception as e:

        print(
            f"[TRIKA] Erreur générale : {e}"
        )


        return (
            "⚠️ Une erreur temporaire est survenue.\n\n"
            "Veuillez réessayer."
        )