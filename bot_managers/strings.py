"""
strings.py — Dizionario multilingua per purpleGPT
Lingue supportate: en (default), it, es, pt, fr, de

Uso:
    from bot_managers.strings import t, get_lang
    lang = get_lang(uid, user_cfg)    # legge da user_settings
    await interaction.followup.send(t("chat.error_generic", lang))
    await interaction.followup.send(t("draw.error_format", lang, mime=mime))

Note:
    - La lingua è impostata per utente in user_settings (colonna 'language', default 'en')
    - get_lang(uid, cfg) accetta il dict settings già recuperato — zero query extra
    - t() non solleva mai eccezioni: fallback a 'en' (DEFAULT_LANG), poi alla chiave stessa
    - Le descrizioni dei comandi Discord NON sono qui: richiedono l'API di localizzazione Discord
"""
from __future__ import annotations

SUPPORTED_LANGS = ("it", "en", "es", "pt", "fr", "de")
DEFAULT_LANG = "en"

STRINGS: dict[str, dict[str, str]] = {

    # ── TOS ───────────────────────────────────────────────────────────────────
    "tos.first_use": {
        "it": "Continuando, accetti di parlare con un chatbot AI basato su Gemini. Maggiori informazioni su https://example.com/purplegpt-tos. Rifai la richiesta per continuare.",
        "en": "By continuing, you agree to interact with a Gemini-based AI chatbot. More info at https://example.com/purplegpt-tos. Repeat your request to continue.",
        "es": "Al continuar, aceptas interactuar con un chatbot de IA basado en Gemini. Más información en https://example.com/purplegpt-tos. Repite tu solicitud para continuar.",
        "pt": "Ao continuar, você aceita interagir com um chatbot de IA baseado no Gemini. Mais informações em https://example.com/purplegpt-tos. Repita o seu pedido para continuar.",
        "fr": "En continuant, vous acceptez d'interagir avec un chatbot IA basé sur Gemini. Plus d'informations sur https://example.com/purplegpt-tos. Répétez votre demande pour continuer.",
        "de": "Indem du fortfährst, stimmst du zu, mit einem KI-Chatbot auf Gemini-Basis zu interagieren. Mehr Infos unter https://example.com/purplegpt-tos. Wiederhole deine Anfrage, um fortzufahren.",
    },

    # ── COOLDOWN ──────────────────────────────────────────────────────────────
    "cooldown.message": {
        "it": "⏳ Stai andando troppo veloce! Attendi ancora **{remaining}s** prima di usare {command} di nuovo.",
        "en": "⏳ You're going too fast! Wait **{remaining}s** before using {command} again.",
        "es": "⏳ ¡Vas demasiado rápido! Espera **{remaining}s** antes de usar {command} de nuevo.",
        "pt": "⏳ Você está indo rápido demais! Aguarde **{remaining}s** antes de usar {command} novamente.",
        "fr": "⏳ Tu vas trop vite ! Attends encore **{remaining}s** avant d'utiliser {command} à nouveau.",
        "de": "⏳ Du bist zu schnell! Warte noch **{remaining}s**, bevor du {command} erneut verwendest.",
    },
    "cooldown.bugreport": {
        "it": "⏳ Hai già inviato un report di recente. Riprova tra **{remaining}s**.",
        "en": "⏳ You've already submitted a report recently. Try again in **{remaining}s**.",
        "es": "⏳ Ya enviaste un reporte recientemente. Inténtalo de nuevo en **{remaining}s**.",
        "pt": "⏳ Você já enviou um relatório recentemente. Tente novamente em **{remaining}s**.",
        "fr": "⏳ Tu as déjà envoyé un rapport récemment. Réessaie dans **{remaining}s**.",
        "de": "⏳ Du hast kürzlich bereits einen Bericht gesendet. Versuche es in **{remaining}s** erneut.",
    },

    # ── QUOTA ─────────────────────────────────────────────────────────────────
    "quota.exceeded": {
        "it": "⚠️ Hai raggiunto il limite giornaliero di **{limit} utilizzi** per {command}.\nIl limite si resetta ogni giorno a mezzanotte UTC.",
        "en": "⚠️ You've reached the daily limit of **{limit} uses** for {command}.\nThe limit resets every day at midnight UTC.",
        "es": "⚠️ Has alcanzado el límite diario de **{limit} usos** para {command}.\nEl límite se restablece cada día a medianoche UTC.",
        "pt": "⚠️ Você atingiu o limite diário de **{limit} usos** para {command}.\nO limite é redefinido todos os dias à meia-noite UTC.",
        "fr": "⚠️ Tu as atteint la limite journalière de **{limit} utilisations** pour {command}.\nLa limite est réinitialisée chaque jour à minuit UTC.",
        "de": "⚠️ Du hast das Tageslimit von **{limit} Nutzungen** für {command} erreicht.\nDas Limit wird täglich um Mitternacht UTC zurückgesetzt.",
    },
    "quota.secret_vote_tip": {
        "it": "🤫 **Tip segreto:** se voti con `/vote`, sblocchi **1 generazione immagine extra** per oggi.",
        "en": "🤫 **Secret tip:** vote with `/vote` to unlock **1 extra image generation** for today.",
        "es": "🤫 **Tip secreto:** vota con `/vote` para desbloquear **1 generación de imagen extra** por hoy.",
        "pt": "🤫 **Dica secreta:** vota com `/vote` para desbloquear **1 geração de imagem extra** para hoje.",
        "fr": "🤫 **Astuce secrète :** vote avec `/vote` pour débloquer **1 génération d'image en plus** aujourd'hui.",
        "de": "🤫 **Geheimer Tipp:** Stimme mit `/vote` ab, um heute **1 zusätzliche Bildgenerierung** freizuschalten.",
    },

    # ── ERRORI GENERICI ───────────────────────────────────────────────────────
    "error.generic": {
        "it": "⚠️ Si è verificato un errore tecnico. Riprova tra qualche secondo.",
        "en": "⚠️ A technical error occurred. Please try again in a few seconds.",
        "es": "⚠️ Se produjo un error técnico. Por favor, inténtalo de nuevo en unos segundos.",
        "pt": "⚠️ Ocorreu um erro técnico. Por favor, tente novamente em alguns segundos.",
        "fr": "⚠️ Une erreur technique s'est produite. Réessaie dans quelques secondes.",
        "de": "⚠️ Ein technischer Fehler ist aufgetreten. Bitte versuche es in ein paar Sekunden erneut.",
    },
    "error.format_not_supported": {
        "it": "Formato non supportato: `{mime}`.",
        "en": "Unsupported format: `{mime}`.",
        "es": "Formato no compatible: `{mime}`.",
        "pt": "Formato não suportado: `{mime}`.",
        "fr": "Format non pris en charge : `{mime}`.",
        "de": "Nicht unterstütztes Format: `{mime}`.",
    },
    "error.file_too_large": {
        "it": "File troppo grande. Carica un'immagine sotto i **{mb} MB**.",
        "en": "File too large. Upload an image under **{mb} MB**.",
        "es": "Archivo demasiado grande. Sube una imagen de menos de **{mb} MB**.",
        "pt": "Ficheiro demasiado grande. Envia uma imagem com menos de **{mb} MB**.",
        "fr": "Fichier trop volumineux. Envoie une image de moins de **{mb} MB**.",
        "de": "Datei zu groß. Lade ein Bild unter **{mb} MB** hoch.",
    },

    # ── MENZIONE ──────────────────────────────────────────────────────────────
    "mention.hello": {
        "it": "Dimmi pure! 👋",
        "en": "Go ahead! 👋",
        "es": "¡Dime! 👋",
        "pt": "Pode falar! 👋",
        "fr": "Dis-moi ! 👋",
        "de": "Nur zu! 👋",
    },
    "mention.error_no_response": {
        "it": "Non ho ricevuto una risposta valida. Riprova.",
        "en": "I didn't receive a valid response. Please try again.",
        "es": "No recibí una respuesta válida. Inténtalo de nuevo.",
        "pt": "Não recebi uma resposta válida. Por favor, tente novamente.",
        "fr": "Je n'ai pas reçu de réponse valide. Réessaie.",
        "de": "Ich habe keine gültige Antwort erhalten. Bitte versuche es erneut.",
    },

    # ── /chat ─────────────────────────────────────────────────────────────────
    "chat.error_no_response": {
        "it": "Non ho ricevuto una risposta valida da Gemini. Riprova.",
        "en": "I didn't receive a valid response from Gemini. Please try again.",
        "es": "No recibí una respuesta válida de Gemini. Inténtalo de nuevo.",
        "pt": "Não recebi uma resposta válida do Gemini. Por favor, tente novamente.",
        "fr": "Je n'ai pas reçu de réponse valide de Gemini. Réessaie.",
        "de": "Ich habe keine gültige Antwort von Gemini erhalten. Bitte versuche es erneut.",
    },

    # ── /draw ─────────────────────────────────────────────────────────────────
    "draw.caption": {
        "it": "Ecco il tuo disegno: **{prompt}**",
        "en": "Here's your drawing: **{prompt}**",
        "es": "Aquí está tu dibujo: **{prompt}**",
        "pt": "Aqui está o seu desenho: **{prompt}**",
        "fr": "Voici ton dessin : **{prompt}**",
        "de": "Hier ist dein Bild: **{prompt}**",
    },
    "draw.size_label": {
        "it": "📐 Formato: `{size}`",
        "en": "📐 Size: `{size}`",
        "es": "📐 Formato: `{size}`",
        "pt": "📐 Formato: `{size}`",
        "fr": "📐 Format : `{size}`",
        "de": "📐 Format: `{size}`",
    },
    "draw.from_reference": {
        "it": "🖼️ Generato da immagine di riferimento",
        "en": "🖼️ Generated from reference image",
        "es": "🖼️ Generado desde imagen de referencia",
        "pt": "🖼️ Gerado a partir de imagem de referência",
        "fr": "🖼️ Généré depuis une image de référence",
        "de": "🖼️ Aus Referenzbild generiert",
    },
    "draw.error_text_only": {
        "it": "Non ho potuto disegnare:\n{reason}",
        "en": "I couldn't draw:\n{reason}",
        "es": "No pude dibujar:\n{reason}",
        "pt": "Não consegui desenhar:\n{reason}",
        "fr": "Je n'ai pas pu dessiner :\n{reason}",
        "de": "Ich konnte nicht zeichnen:\n{reason}",
    },
    "draw.error_no_content": {
        "it": "Gemini non ha restituito alcun contenuto valido.",
        "en": "Gemini returned no valid content.",
        "es": "Gemini no devolvió ningún contenido válido.",
        "pt": "O Gemini não retornou nenhum conteúdo válido.",
        "fr": "Gemini n'a renvoyé aucun contenu valide.",
        "de": "Gemini hat keinen gültigen Inhalt zurückgegeben.",
    },

    # ── /edit ─────────────────────────────────────────────────────────────────
    "edit.no_image_found": {
        "it": "Non ho trovato immagini generate per te in questo canale.\nUsa prima `/draw` oppure allega un'immagine al comando `/edit`.",
        "en": "I couldn't find any images generated for you in this channel.\nUse `/draw` first, or attach an image to the `/edit` command.",
        "es": "No encontré imágenes generadas para ti en este canal.\nUsa `/draw` primero o adjunta una imagen al comando `/edit`.",
        "pt": "Não encontrei imagens geradas para você neste canal.\nUse `/draw` primeiro ou anexe uma imagem ao comando `/edit`.",
        "fr": "Je n'ai pas trouvé d'images générées pour toi dans ce canal.\nUtilise d'abord `/draw` ou joins une image à la commande `/edit`.",
        "de": "Ich habe keine für dich generierten Bilder in diesem Kanal gefunden.\nVerwende zuerst `/draw` oder füge dem `/edit`-Befehl ein Bild hinzu.",
    },
    "edit.image_deleted": {
        "it": "Non riesco a trovare l'immagine originale (potrebbe essere stata eliminata).\nAllega manualmente l'immagine.",
        "en": "I can't find the original image (it may have been deleted).\nPlease attach the image manually.",
        "es": "No puedo encontrar la imagen original (puede haber sido eliminada).\nAdjunta la imagen manualmente.",
        "pt": "Não consigo encontrar a imagem original (pode ter sido excluída).\nAnexe a imagem manualmente.",
        "fr": "Je ne trouve pas l'image originale (elle a peut-être été supprimée).\nJoins l'image manuellement.",
        "de": "Ich kann das Originalbild nicht finden (es wurde möglicherweise gelöscht).\nBitte füge das Bild manuell hinzu.",
    },
    "edit.no_attachment": {
        "it": "Il messaggio salvato non contiene immagini. Allega manualmente l'immagine.",
        "en": "The saved message contains no images. Please attach the image manually.",
        "es": "El mensaje guardado no contiene imágenes. Adjunta la imagen manualmente.",
        "pt": "A mensagem salva não contém imagens. Anexe a imagem manualmente.",
        "fr": "Le message enregistré ne contient pas d'images. Joins l'image manuellement.",
        "de": "Die gespeicherte Nachricht enthält keine Bilder. Bitte füge das Bild manuell hinzu.",
    },
    "edit.caption": {
        "it": "Ecco l'immagine modificata!",
        "en": "Here's your edited image!",
        "es": "¡Aquí está tu imagen modificada!",
        "pt": "Aqui está a sua imagem editada!",
        "fr": "Voici ton image modifiée !",
        "de": "Hier ist dein bearbeitetes Bild!",
    },
    "edit.error_text_only": {
        "it": "Non ho potuto modificare l'immagine:\n{reason}",
        "en": "I couldn't edit the image:\n{reason}",
        "es": "No pude modificar la imagen:\n{reason}",
        "pt": "Não consegui modificar a imagem:\n{reason}",
        "fr": "Je n'ai pas pu modifier l'image :\n{reason}",
        "de": "Ich konnte das Bild nicht bearbeiten:\n{reason}",
    },
    "edit.error_no_content": {
        "it": "Gemini non ha restituito un'immagine modificata.",
        "en": "Gemini didn't return an edited image.",
        "es": "Gemini no devolvió una imagen modificada.",
        "pt": "O Gemini não retornou uma imagem editada.",
        "fr": "Gemini n'a pas renvoyé d'image modifiée.",
        "de": "Gemini hat kein bearbeitetes Bild zurückgegeben.",
    },

    # ── /compose ──────────────────────────────────────────────────────────────
    "compose.status_generating": {
        "it": "🎵 Sto componendo... `{style}` • {bpm} BPM • {duration}s{video}",
        "en": "🎵 Composing... `{style}` • {bpm} BPM • {duration}s{video}",
        "es": "🎵 Componiendo... `{style}` • {bpm} BPM • {duration}s{video}",
        "pt": "🎵 Compondo... `{style}` • {bpm} BPM • {duration}s{video}",
        "fr": "🎵 En train de composer... `{style}` • {bpm} BPM • {duration}s{video}",
        "de": "🎵 Komponiere... `{style}` • {bpm} BPM • {duration}s{video}",
    },
    "compose.status_video_suffix": {
        "it": " • 🎬 video attivo",
        "en": " • 🎬 video enabled",
        "es": " • 🎬 video activado",
        "pt": " • 🎬 vídeo ativo",
        "fr": " • 🎬 vidéo activée",
        "de": " • 🎬 Video aktiviert",
    },
    "compose.status_parallel": {
        "it": "🎵 Genero musica e immagine in parallelo... `{style}` • {bpm} BPM • {duration}s • 🎬",
        "en": "🎵 Generating music and image in parallel... `{style}` • {bpm} BPM • {duration}s • 🎬",
        "es": "🎵 Generando música e imagen en paralelo... `{style}` • {bpm} BPM • {duration}s • 🎬",
        "pt": "🎵 Gerando música e imagem em paralelo... `{style}` • {bpm} BPM • {duration}s • 🎬",
        "fr": "🎵 Génération de la musique et de l'image en parallèle... `{style}` • {bpm} BPM • {duration}s • 🎬",
        "de": "🎵 Generiere Musik und Bild parallel... `{style}` • {bpm} BPM • {duration}s • 🎬",
    },
    "compose.status_assembling": {
        "it": "🎬 Assemblo il video... `{style}` • {bpm} BPM • {duration}s",
        "en": "🎬 Assembling the video... `{style}` • {bpm} BPM • {duration}s",
        "es": "🎬 Ensamblando el video... `{style}` • {bpm} BPM • {duration}s",
        "pt": "🎬 Montando o vídeo... `{style}` • {bpm} BPM • {duration}s",
        "fr": "🎬 Assemblage de la vidéo... `{style}` • {bpm} BPM • {duration}s",
        "de": "🎬 Video wird zusammengesetzt... `{style}` • {bpm} BPM • {duration}s",
    },
    "compose.result_video": {
        "it": "🎬 Ecco la tua composizione!",
        "en": "🎬 Here's your composition!",
        "es": "🎬 ¡Aquí está tu composición!",
        "pt": "🎬 Aqui está a sua composição!",
        "fr": "🎬 Voici ta composition !",
        "de": "🎬 Hier ist deine Komposition!",
    },
    "compose.result_audio": {
        "it": "🎵 Ecco la tua composizione!",
        "en": "🎵 Here's your composition!",
        "es": "🎵 ¡Aquí está tu composición!",
        "pt": "🎵 Aqui está a sua composição!",
        "fr": "🎵 Voici ta composition !",
        "de": "🎵 Hier ist deine Komposition!",
    },
    "compose.result_image_failed": {
        "it": "🎵 Generazione immagine non riuscita — ecco solo l'audio!",
        "en": "🎵 Image generation failed — here's the audio only!",
        "es": "🎵 La generación de imagen falló — ¡aquí solo el audio!",
        "pt": "🎵 A geração de imagem falhou — aqui está apenas o áudio!",
        "fr": "🎵 La génération d'image a échoué — voici l'audio uniquement !",
        "de": "🎵 Bildgenerierung fehlgeschlagen — hier ist nur das Audio!",
    },
    "compose.result_video_failed": {
        "it": "🎵 Assemblaggio video non riuscito — ecco solo l'audio!",
        "en": "🎵 Video assembly failed — here's the audio only!",
        "es": "🎵 El ensamblado del video falló — ¡aquí solo el audio!",
        "pt": "🎵 A montagem do vídeo falhou — aqui está apenas o áudio!",
        "fr": "🎵 L'assemblage de la vidéo a échoué — voici l'audio uniquement !",
        "de": "🎵 Videomontage fehlgeschlagen — hier ist nur das Audio!",
    },

    # ── /help ─────────────────────────────────────────────────────────────────
    "help.title": {
        "it": "purpleGPT 🧪 Beta", "en": "purpleGPT 🧪 Beta", "es": "purpleGPT 🧪 Beta",
        "pt": "purpleGPT 🧪 Beta", "fr": "purpleGPT 🧪 Beta", "de": "purpleGPT 🧪 Beta",
    },
    "help.description": {
        "it": "Ciao! Sono **purpleGPT**, un'IA basata su **Gemini** di Google, creata da **justmarcolin**.\nEcco cosa posso fare:\n\n> Sei in una **beta pubblica** — usa `/bugreport` per segnalare problemi!",
        "en": "Hello! I'm **purpleGPT**, an AI based on Google's **Gemini**, created by **justmarcolin**.\nHere's what I can do:\n\n> You're in a **public beta** — use `/bugreport` to report any issues!",
        "es": "¡Hola! Soy **purpleGPT**, una IA basada en **Gemini** de Google, creada por **justmarcolin**.\nEsto es lo que puedo hacer:\n\n> Estás en una **beta pública** — usa `/bugreport` para reportar problemas.",
        "pt": "Olá! Sou o **purpleGPT**, uma IA baseada no **Gemini** do Google, criada por **justmarcolin**.\nEis o que posso fazer:\n\n> Você está numa **beta pública** — use `/bugreport` para reportar problemas!",
        "fr": "Bonjour ! Je suis **purpleGPT**, une IA basée sur **Gemini** de Google, créée par **justmarcolin**.\nVoici ce que je peux faire :\n\n> Tu es en **bêta publique** — utilise `/bugreport` pour signaler des problèmes !",
        "de": "Hallo! Ich bin **purpleGPT**, eine KI basierend auf Googles **Gemini**, erstellt von **justmarcolin**.\nHier ist, was ich kann:\n\n> Du bist in einer **öffentlichen Beta** — nutze `/bugreport`, um Probleme zu melden!",
    },
    "help.footer": {
        "it": "TOS: https://example.com/purplegpt-tos  •  🧪 Beta pubblica",
        "en": "TOS: https://example.com/purplegpt-tos  •  🧪 Public beta",
        "es": "TOS: https://example.com/purplegpt-tos  •  🧪 Beta pública",
        "pt": "TOS: https://example.com/purplegpt-tos  •  🧪 Beta pública",
        "fr": "CGU : https://example.com/purplegpt-tos  •  🧪 Bêta publique",
        "de": "TOS: https://example.com/purplegpt-tos  •  🧪 Öffentliche Beta",
    },
    "help.field.chat.name":    {"it": "/chat <prompt> [image]", "en": "/chat <prompt> [image]", "es": "/chat <prompt> [image]", "pt": "/chat <prompt> [image]", "fr": "/chat <prompt> [image]", "de": "/chat <prompt> [image]"},
    "help.field.chat.value":   {"it": "Chatta con me. Puoi allegare immagini. Puoi anche taggami direttamente con o senza foto!", "en": "Chat with me. You can attach images. You can also mention me directly with or without a photo!", "es": "Chatea conmigo. Puedes adjuntar imágenes. ¡También puedes mencionarme directamente con o sin foto!", "pt": "Converse comigo. Você pode anexar imagens. Também pode me mencionar diretamente com ou sem foto!", "fr": "Discute avec moi. Tu peux joindre des images. Tu peux aussi me mentionner directement avec ou sans photo !", "de": "Chatte mit mir. Du kannst Bilder anhängen. Du kannst mich auch direkt mit oder ohne Foto erwähnen!"},
    "help.field.draw.name":    {"it": "/draw <prompt> [image]", "en": "/draw <prompt> [image]", "es": "/draw <prompt> [image]", "pt": "/draw <prompt> [image]", "fr": "/draw <prompt> [image]", "de": "/draw <prompt> [image]"},
    "help.field.draw.value":   {"it": "Genera immagini.", "en": "Generate images.", "es": "Genera imágenes.", "pt": "Gera imagens.", "fr": "Génère des images.", "de": "Bilder generieren."},
    "help.field.edit.name":    {"it": "/edit <instructions> [image]", "en": "/edit <instructions> [image]", "es": "/edit <instructions> [image]", "pt": "/edit <instructions> [image]", "fr": "/edit <instructions> [image]", "de": "/edit <instructions> [image]"},
    "help.field.edit.value":   {"it": "Modifica un'immagine.", "en": "Edit an image.", "es": "Modifica una imagen.", "pt": "Edita uma imagem.", "fr": "Modifie une image.", "de": "Ein Bild bearbeiten."},
    "help.field.compose.name": {"it": "/compose <style> [bpm] [duration] [video]", "en": "/compose <style> [bpm] [duration] [video]", "es": "/compose <style> [bpm] [duration] [video]", "pt": "/compose <style> [bpm] [duration] [video]", "fr": "/compose <style> [bpm] [duration] [video]", "de": "/compose <style> [bpm] [duration] [video]"},
    "help.field.compose.value":{"it": "Genera musica AI.", "en": "Generate AI music.", "es": "Genera música con IA.", "pt": "Gera música com IA.", "fr": "Génère de la musique IA.", "de": "KI-Musik generieren."},
    "help.field.settings.name":{"it": "/settings", "en": "/settings", "es": "/settings", "pt": "/settings", "fr": "/settings", "de": "/settings"},
    "help.field.settings.value":{"it": "Personalizza temperatura e prompt.", "en": "Customize temperature and prompt.", "es": "Personaliza temperatura y prompt.", "pt": "Personalize temperatura e prompt.", "fr": "Personnalise la température et le prompt.", "de": "Temperatur und Prompt anpassen."},
    "help.field.stats.name":   {"it": "/stats", "en": "/stats", "es": "/stats", "pt": "/stats", "fr": "/stats", "de": "/stats"},
    "help.field.stats.value":  {"it": "Le tue statistiche personali.", "en": "Your personal statistics.", "es": "Tus estadísticas personales.", "pt": "As suas estatísticas pessoais.", "fr": "Tes statistiques personnelles.", "de": "Deine persönlichen Statistiken."},
    "help.field.history.name": {"it": "/history", "en": "/history", "es": "/history", "pt": "/history", "fr": "/history", "de": "/history"},
    "help.field.history.value":{"it": "[Admin] Gestisci la memoria del canale.", "en": "[Admin] Manage channel memory.", "es": "[Admin] Gestiona la memoria del canal.", "pt": "[Admin] Gere a memória do canal.", "fr": "[Admin] Gère la mémoire du canal.", "de": "[Admin] Kanalgedächtnis verwalten."},
    "help.field.bugreport.name":{"it": "/bugreport", "en": "/bugreport", "es": "/bugreport", "pt": "/bugreport", "fr": "/bugreport", "de": "/bugreport"},
    "help.field.bugreport.value":{"it": "Segnala un bug o un problema.", "en": "Report a bug or an issue.", "es": "Reporta un error o un problema.", "pt": "Reporta um bug ou um problema.", "fr": "Signale un bug ou un problème.", "de": "Einen Fehler oder ein Problem melden."},
    "help.field.delete.name":  {"it": "/delete_user_data", "en": "/delete_user_data", "es": "/delete_user_data", "pt": "/delete_user_data", "fr": "/delete_user_data", "de": "/delete_user_data"},
    "help.field.delete.value": {"it": "Cancella tutti i tuoi dati personali.", "en": "Delete all your personal data.", "es": "Elimina todos tus datos personales.", "pt": "Apaga todos os seus dados pessoais.", "fr": "Supprime toutes tes données personnelles.", "de": "Alle deine persönlichen Daten löschen."},
    "help.field.export.name":  {"it": "/export_data", "en": "/export_data", "es": "/export_data", "pt": "/export_data", "fr": "/export_data", "de": "/export_data"},
    "help.field.export.value": {"it": "Esporta i tuoi dati in un file JSON.", "en": "Export your data as a JSON file.", "es": "Exporta tus datos en un archivo JSON.", "pt": "Exporta os seus dados num ficheiro JSON.", "fr": "Exporte tes données en fichier JSON.", "de": "Deine Daten als JSON-Datei exportieren."},
    "help.field.help.name":    {"it": "/help", "en": "/help", "es": "/help", "pt": "/help", "fr": "/help", "de": "/help"},
    "help.field.help.value":   {"it": "Mostra questo messaggio.", "en": "Show this message.", "es": "Muestra este mensaje.", "pt": "Mostra esta mensagem.", "fr": "Affiche ce message.", "de": "Diese Nachricht anzeigen."},

    # ── /stats ────────────────────────────────────────────────────────────────
    "stats.title":          {"it": "📊 Le tue statistiche", "en": "📊 Your statistics", "es": "📊 Tus estadísticas", "pt": "📊 As suas estatísticas", "fr": "📊 Tes statistiques", "de": "📊 Deine Statistiken"},
    "stats.field.since":    {"it": "📅 Membro dal", "en": "📅 Member since", "es": "📅 Miembro desde", "pt": "📅 Membro desde", "fr": "📅 Membre depuis", "de": "📅 Mitglied seit"},
    "stats.field.messages": {"it": "💬 Messaggi inviati", "en": "💬 Messages sent", "es": "💬 Mensajes enviados", "pt": "💬 Mensagens enviadas", "fr": "💬 Messages envoyés", "de": "💬 Gesendete Nachrichten"},
    "stats.field.images":   {"it": "🎨 Immagini generate", "en": "🎨 Images generated", "es": "🎨 Imágenes generadas", "pt": "🎨 Imagens geradas", "fr": "🎨 Images générées", "de": "🎨 Generierte Bilder"},
    "stats.field.total_value": {"it": "**{n}** totali", "en": "**{n}** total", "es": "**{n}** en total", "pt": "**{n}** no total", "fr": "**{n}** au total", "de": "**{n}** insgesamt"},
    "stats.field.today":    {"it": "⚡ Utilizzo oggi", "en": "⚡ Today's usage", "es": "⚡ Uso de hoy", "pt": "⚡ Uso de hoje", "fr": "⚡ Utilisation aujourd'hui", "de": "⚡ Heutige Nutzung"},
    "stats.field.history":  {"it": "📈 Utilizzo totale storico", "en": "📈 All-time usage", "es": "📈 Uso histórico total", "pt": "📈 Uso histórico total", "fr": "📈 Utilisation totale historique", "de": "📈 Gesamte bisherige Nutzung"},
    "stats.footer":         {"it": "purpleGPT 🟣 — jLabs by justmarcolin", "en": "purpleGPT 🟣 — jLabs by justmarcolin", "es": "purpleGPT 🟣 — jLabs by justmarcolin", "pt": "purpleGPT 🟣 — jLabs by justmarcolin", "fr": "purpleGPT 🟣 — jLabs by justmarcolin", "de": "purpleGPT 🟣 — jLabs by justmarcolin"},

    # ── /history ──────────────────────────────────────────────────────────────
    "history.no_permission":       {"it": "Serve il permesso **Gestisci canali** per usare questo comando.", "en": "You need the **Manage Channels** permission to use this command.", "es": "Necesitas el permiso **Gestionar canales** para usar este comando.", "pt": "Precisas da permissão **Gerir Canais** para usar este comando.", "fr": "Tu as besoin de la permission **Gérer les salons** pour utiliser cette commande.", "de": "Du benötigst die Berechtigung **Kanäle verwalten**, um diesen Befehl zu nutzen."},
    "history.title":               {"it": "Gestione **history del canale**:", "en": "**Channel history** management:", "es": "Gestión del **historial del canal**:", "pt": "Gestão do **histórico do canal**:", "fr": "Gestion de l'**historique du canal** :", "de": "**Kanalverlauf**-Verwaltung:"},
    "history.select.placeholder":  {"it": "Gestione memoria del canale...", "en": "Channel memory management...", "es": "Gestión de la memoria del canal...", "pt": "Gestão da memória do canal...", "fr": "Gestion de la mémoire du canal...", "de": "Kanalgedächtnis verwalten..."},
    "history.option.enable":       {"it": "Attiva memoria", "en": "Enable memory", "es": "Activar memoria", "pt": "Ativar memória", "fr": "Activer la mémoire", "de": "Gedächtnis aktivieren"},
    "history.option.disable":      {"it": "Disattiva memoria", "en": "Disable memory", "es": "Desactivar memoria", "pt": "Desativar memória", "fr": "Désactiver la mémoire", "de": "Gedächtnis deaktivieren"},
    "history.option.clear":        {"it": "Cancella memoria", "en": "Clear memory", "es": "Borrar memoria", "pt": "Limpar memória", "fr": "Effacer la mémoire", "de": "Gedächtnis löschen"},
    "history.enabled":             {"it": "🟢 Memoria canale **attivata**.", "en": "🟢 Channel memory **enabled**.", "es": "🟢 Memoria del canal **activada**.", "pt": "🟢 Memória do canal **ativada**.", "fr": "🟢 Mémoire du canal **activée**.", "de": "🟢 Kanalgedächtnis **aktiviert**."},
    "history.disabled":            {"it": "🔴 Memoria canale **disattivata**.", "en": "🔴 Channel memory **disabled**.", "es": "🔴 Memoria del canal **desactivada**.", "pt": "🔴 Memória do canal **desativada**.", "fr": "🔴 Mémoire du canal **désactivée**.", "de": "🔴 Kanalgedächtnis **deaktiviert**."},
    "history.cleared":             {"it": "🗑️ Memoria canale **cancellata**.", "en": "🗑️ Channel memory **cleared**.", "es": "🗑️ Memoria del canal **borrada**.", "pt": "🗑️ Memória do canal **limpa**.", "fr": "🗑️ Mémoire du canal **effacée**.", "de": "🗑️ Kanalgedächtnis **gelöscht**."},

    # ── /settings ─────────────────────────────────────────────────────────────
    "settings.embed.title":              {"it": "⚙️ Le tue impostazioni purpleGPT", "en": "⚙️ Your purpleGPT settings", "es": "⚙️ Tu configuración de purpleGPT", "pt": "⚙️ As suas definições do purpleGPT", "fr": "⚙️ Tes paramètres purpleGPT", "de": "⚙️ Deine purpleGPT-Einstellungen"},
    "settings.field.plan":               {"it": "💳 Piano", "en": "💳 Plan", "es": "💳 Plan", "pt": "💳 Plano", "fr": "💳 Formule", "de": "💳 Plan"},
    "settings.field.plan.free":          {"it": "🆓 Free", "en": "🆓 Free", "es": "🆓 Free", "pt": "🆓 Free", "fr": "🆓 Free", "de": "🆓 Free"},
    "settings.field.plan.trial":         {"it": "🎁 {plan} (Prova) - termina tra **{duration}** (`{date}`)", "en": "🎁 {plan} (Trial) - ends in **{duration}** (`{date}`)", "es": "🎁 {plan} (Prueba) - termina en **{duration}** (`{date}`)", "pt": "🎁 {plan} (Teste) - termina em **{duration}** (`{date}`)", "fr": "🎁 {plan} (Essai) - se termine dans **{duration}** (`{date}`)", "de": "🎁 {plan} (Testphase) - endet in **{duration}** (`{date}`)"},
    "settings.field.plan.active":        {"it": "{emoji} {plan} - scade tra **{duration}** (`{date}`)", "en": "{emoji} {plan} - expires in **{duration}** (`{date}`)", "es": "{emoji} {plan} - vence en **{duration}** (`{date}`)", "pt": "{emoji} {plan} - expira em **{duration}** (`{date}`)", "fr": "{emoji} {plan} - expire dans **{duration}** (`{date}`)", "de": "{emoji} {plan} - läuft ab in **{duration}** (`{date}`)"},
    "settings.field.temperature":        {"it": "🌡️ Temperatura", "en": "🌡️ Temperature", "es": "🌡️ Temperatura", "pt": "🌡️ Temperatura", "fr": "🌡️ Température", "de": "🌡️ Temperatur"},
    "settings.field.temperature.value":  {"it": "`{value}`  —  creatività e variabilità delle risposte", "en": "`{value}`  —  creativity and variability of responses", "es": "`{value}`  —  creatividad y variabilidad de las respuestas", "pt": "`{value}`  —  criatividade e variabilidade das respostas", "fr": "`{value}`  —  créativité et variabilité des réponses", "de": "`{value}`  —  Kreativität und Variabilität der Antworten"},
    "settings.field.image_size":         {"it": "📐 Formato immagine", "en": "📐 Image size", "es": "📐 Formato de imagen", "pt": "📐 Formato de imagem", "fr": "📐 Format d'image", "de": "📐 Bildformat"},
    "settings.field.image_size.value":   {"it": "`{value}`  —  aspect ratio per `/draw` e `/edit`", "en": "`{value}`  —  aspect ratio for `/draw` and `/edit`", "es": "`{value}`  —  relación de aspecto para `/draw` y `/edit`", "pt": "`{value}`  —  proporção para `/draw` e `/edit`", "fr": "`{value}`  —  rapport d'aspect pour `/draw` et `/edit`", "de": "`{value}`  —  Seitenverhältnis für `/draw` und `/edit`"},
    "settings.field.custom_prompt":      {"it": "✏️ Prompt personalizzato", "en": "✏️ Custom prompt", "es": "✏️ Prompt personalizado", "pt": "✏️ Prompt personalizado", "fr": "✏️ Prompt personnalisé", "de": "✏️ Benutzerdefinierter Prompt"},
    "settings.field.custom_prompt.none": {"it": "*Nessuno impostato*", "en": "*None set*", "es": "*Ninguno configurado*", "pt": "*Nenhum definido*", "fr": "*Aucun défini*", "de": "*Keiner gesetzt*"},
    "settings.footer":                   {"it": "Impostazioni di {username}  •  Si applicano solo alle tue conversazioni", "en": "Settings for {username}  •  Apply only to your conversations", "es": "Configuración de {username}  •  Se aplican solo a tus conversaciones", "pt": "Definições de {username}  •  Aplicam-se apenas às suas conversas", "fr": "Paramètres de {username}  •  S'appliquent uniquement à tes conversations", "de": "Einstellungen von {username}  •  Gelten nur für deine Gespräche"},
    "settings.temperature.placeholder":  {"it": "Temperatura...", "en": "Temperature...", "es": "Temperatura...", "pt": "Temperatura...", "fr": "Température...", "de": "Temperatur..."},
    "settings.temperature.saved":        {"it": "Temperatura impostata a **{value}**.", "en": "Temperature set to **{value}**.", "es": "Temperatura establecida a **{value}**.", "pt": "Temperatura definida para **{value}**.", "fr": "Température définie à **{value}**.", "de": "Temperatur auf **{value}** gesetzt."},
    "settings.image_size.placeholder":   {"it": "Formato immagine...", "en": "Image size...", "es": "Formato de imagen...", "pt": "Formato de imagem...", "fr": "Format d'image...", "de": "Bildformat..."},
    "settings.image_size.saved":         {"it": "Formato immagine impostato a **{value}**.", "en": "Image size set to **{value}**.", "es": "Formato de imagen establecido a **{value}**.", "pt": "Formato de imagem definido para **{value}**.", "fr": "Format d'image défini à **{value}**.", "de": "Bildformat auf **{value}** gesetzt."},
    "settings.button.edit_prompt":       {"it": "Modifica prompt personalizzato", "en": "Edit custom prompt", "es": "Editar prompt personalizado", "pt": "Editar prompt personalizado", "fr": "Modifier le prompt personnalisé", "de": "Benutzerdefinierten Prompt bearbeiten"},
    "settings.button.reset":             {"it": "Reset impostazioni", "en": "Reset settings", "es": "Restablecer configuración", "pt": "Repor definições", "fr": "Réinitialiser les paramètres", "de": "Einstellungen zurücksetzen"},
    "settings.reset.done":               {"it": "Impostazioni ripristinate ai valori di default.", "en": "Settings reset to default values.", "es": "Configuración restablecida a los valores predeterminados.", "pt": "Definições repostas aos valores predefinidos.", "fr": "Paramètres réinitialisés aux valeurs par défaut.", "de": "Einstellungen auf Standardwerte zurückgesetzt."},
    "settings.modal.prompt.label":       {"it": "Istruzioni extra per purpleGPT", "en": "Extra instructions for purpleGPT", "es": "Instrucciones extra para purpleGPT", "pt": "Instruções extra para o purpleGPT", "fr": "Instructions supplémentaires pour purpleGPT", "de": "Zusätzliche Anweisungen für purpleGPT"},
    "settings.modal.prompt.placeholder": {"it": "Es: Rispondimi sempre in modo molto formale e usa termini tecnici.", "en": "E.g.: Always reply in a very formal tone and use technical terms.", "es": "Ej: Respóndeme siempre de forma muy formal y usa términos técnicos.", "pt": "Ex: Responde-me sempre de forma muito formal e usa termos técnicos.", "fr": "Ex : Réponds-moi toujours de manière très formelle et utilise des termes techniques.", "de": "Bsp: Antworte mir immer sehr förmlich und verwende Fachbegriffe."},
    "settings.prompt.saved":             {"it": "Prompt personalizzato salvato.", "en": "Custom prompt saved.", "es": "Prompt personalizado guardado.", "pt": "Prompt personalizado guardado.", "fr": "Prompt personnalisé enregistré.", "de": "Benutzerdefinierter Prompt gespeichert."},
    "settings.prompt.removed":           {"it": "Prompt personalizzato rimosso.", "en": "Custom prompt removed.", "es": "Prompt personalizado eliminado.", "pt": "Prompt personalizado removido.", "fr": "Prompt personnalisé supprimé.", "de": "Benutzerdefinierter Prompt entfernt."},

    # ── /delete_user_data ─────────────────────────────────────────────────────
    "delete.modal.label":    {"it": "Scrivi 'Conferma' per cancellare i tuoi dati", "en": "Type 'Confirm' to delete your data", "es": "Escribe 'Confirmar' para eliminar tus datos", "pt": "Escreve 'Confirmar' para apagar os teus dados", "fr": "Écris 'Confirmer' pour supprimer tes données", "de": "Schreibe 'Bestätigen' um deine Daten zu löschen"},
    "delete.modal.placeholder": {"it": "Conferma", "en": "Confirm", "es": "Confirmar", "pt": "Confirmar", "fr": "Confirmer", "de": "Bestätigen"},
    "delete.confirm_word":   {"it": "Conferma", "en": "Confirm", "es": "Confirmar", "pt": "Confirmar", "fr": "Confirmer", "de": "Bestätigen"},
    "delete.confirm_failed": {"it": "Conferma fallita. Cancellazione annullata.", "en": "Confirmation failed. Deletion cancelled.", "es": "Confirmación fallida. Eliminación cancelada.", "pt": "Confirmação falhou. Eliminação cancelada.", "fr": "Confirmation échouée. Suppression annulée.", "de": "Bestätigung fehlgeschlagen. Löschung abgebrochen."},
    "delete.success":        {"it": "Tutti i tuoi dati sono stati cancellati permanentemente.", "en": "All your data has been permanently deleted.", "es": "Todos tus datos han sido eliminados permanentemente.", "pt": "Todos os seus dados foram eliminados permanentemente.", "fr": "Toutes tes données ont été supprimées définitivement.", "de": "Alle deine Daten wurden dauerhaft gelöscht."},

    # ── /export_data ──────────────────────────────────────────────────────────
    "export.preparing":    {"it": "Preparazione esportazione... Riceverai il file in DM.", "en": "Preparing export... You'll receive the file via DM.", "es": "Preparando exportación... Recibirás el archivo por DM.", "pt": "A preparar exportação... Receberás o ficheiro por DM.", "fr": "Préparation de l'export... Tu recevras le fichier en MP.", "de": "Export wird vorbereitet... Du erhältst die Datei per DM."},
    "export.dm_message":   {"it": "Ecco il tuo file di esportazione dei dati personali:", "en": "Here is your personal data export file:", "es": "Aquí está tu archivo de exportación de datos personales:", "pt": "Aqui está o teu ficheiro de exportação de dados pessoais:", "fr": "Voici ton fichier d'export de données personnelles :", "de": "Hier ist deine persönliche Datei mit exportierten Daten:"},
    "export.dm_closed":    {"it": "Impossibile inviare il file in DM. Assicurati di avere i DM aperti.", "en": "Couldn't send the file via DM. Make sure your DMs are open.", "es": "No se pudo enviar el archivo por DM. Asegúrate de tener los DM abiertos.", "pt": "Não foi possível enviar o ficheiro por DM. Certifica-te de que tens os DM abertos.", "fr": "Impossible d'envoyer le fichier en MP. Assure-toi d'avoir les MP ouverts.", "de": "Datei konnte nicht per DM gesendet werden. Stelle sicher, dass deine DMs geöffnet sind."},
    "export.error_corrupt":{"it": "Il file generato risulta corrotto. Riprova.", "en": "The generated file appears to be corrupted. Please try again.", "es": "El archivo generado parece estar corrupto. Inténtalo de nuevo.", "pt": "O ficheiro gerado parece estar corrompido. Por favor, tente novamente.", "fr": "Le fichier généré semble être corrompu. Réessaie.", "de": "Die generierte Datei scheint beschädigt zu sein. Bitte versuche es erneut."},

    # ── /server_prompt ────────────────────────────────────────────────────────
    "server_prompt.dm_title":       {"it": "🟣 Questo comando richiede un server", "en": "🟣 This command requires a server", "es": "🟣 Este comando requiere un servidor", "pt": "🟣 Este comando requer um servidor", "fr": "🟣 Cette commande nécessite un serveur", "de": "🟣 Dieser Befehl erfordert einen Server"},
    "server_prompt.dm_description": {"it": "Il comando `/server_prompt` permette agli admin di personalizzare il comportamento di purpleGPT per tutti gli utenti del server.\n\nAggiungimi a un server per usarlo!", "en": "The `/server_prompt` command lets admins customize purpleGPT's behavior for all users in the server.\n\nAdd me to a server to use it!", "es": "El comando `/server_prompt` permite a los admins personalizar el comportamiento de purpleGPT para todos los usuarios del servidor.\n\n¡Agrégame a un servidor para usarlo!", "pt": "O comando `/server_prompt` permite aos admins personalizar o comportamento do purpleGPT para todos os utilizadores do servidor.\n\nAdiciona-me a um servidor para o usar!", "fr": "La commande `/server_prompt` permet aux admins de personnaliser le comportement de purpleGPT pour tous les utilisateurs du serveur.\n\nAjoute-moi à un serveur pour l'utiliser !", "de": "Der Befehl `/server_prompt` ermöglicht Admins, das Verhalten von purpleGPT für alle Nutzer des Servers anzupassen.\n\nFüge mich einem Server hinzu, um ihn zu verwenden!"},
    "server_prompt.no_permission":  {"it": "Serve il permesso **Gestisci server** per usare questo comando.", "en": "You need the **Manage Server** permission to use this command.", "es": "Necesitas el permiso **Gestionar servidor** para usar este comando.", "pt": "Precisas da permissão **Gerir Servidor** para usar este comando.", "fr": "Tu as besoin de la permission **Gérer le serveur** pour utiliser cette commande.", "de": "Du benötigst die Berechtigung **Server verwalten**, um diesen Befehl zu nutzen."},
    "server_prompt.show_current":   {"it": "📋 Prompt attuale del server:\n```{prompt}```", "en": "📋 Current server prompt:\n```{prompt}```", "es": "📋 Prompt actual del servidor:\n```{prompt}```", "pt": "📋 Prompt atual do servidor:\n```{prompt}```", "fr": "📋 Prompt actuel du serveur :\n```{prompt}```", "de": "📋 Aktueller Server-Prompt:\n```{prompt}```"},
    "server_prompt.show_none":      {"it": "ℹ️ Nessun prompt personalizzato impostato per questo server.", "en": "ℹ️ No custom prompt set for this server.", "es": "ℹ️ No hay ningún prompt personalizado configurado para este servidor.", "pt": "ℹ️ Nenhum prompt personalizado definido para este servidor.", "fr": "ℹ️ Aucun prompt personnalisé défini pour ce serveur.", "de": "ℹ️ Kein benutzerdefinierter Prompt für diesen Server gesetzt."},
    "server_prompt.updated":        {"it": "✅ Prompt del server aggiornato!\n```{prompt}```\n-# Verrà applicato a tutti gli utenti di questo server.", "en": "✅ Server prompt updated!\n```{prompt}```\n-# Will be applied to all users of this server.", "es": "✅ ¡Prompt del servidor actualizado!\n```{prompt}```\n-# Se aplicará a todos los usuarios de este servidor.", "pt": "✅ Prompt do servidor atualizado!\n```{prompt}```\n-# Será aplicado a todos os utilizadores deste servidor.", "fr": "✅ Prompt du serveur mis à jour !\n```{prompt}```\n-# Sera appliqué à tous les utilisateurs de ce serveur.", "de": "✅ Server-Prompt aktualisiert!\n```{prompt}```\n-# Wird auf alle Nutzer dieses Servers angewendet."},
    "server_prompt.removed":        {"it": "🗑️ Prompt del server rimosso. purpleGPT tornerà al comportamento predefinito.", "en": "🗑️ Server prompt removed. purpleGPT will revert to default behavior.", "es": "🗑️ Prompt del servidor eliminado. purpleGPT volverá al comportamiento predeterminado.", "pt": "🗑️ Prompt do servidor removido. O purpleGPT voltará ao comportamento predefinido.", "fr": "🗑️ Prompt du serveur supprimé. purpleGPT reviendra au comportement par défaut.", "de": "🗑️ Server-Prompt entfernt. purpleGPT kehrt zum Standardverhalten zurück."},
    "server_prompt.add_bot_button": {"it": "Aggiungi purpleGPT a un server", "en": "Add purpleGPT to a server", "es": "Agregar purpleGPT a un servidor", "pt": "Adicionar purpleGPT a um servidor", "fr": "Ajouter purpleGPT à un serveur", "de": "purpleGPT zu einem Server hinzufügen"},

    # ── /bugreport ────────────────────────────────────────────────────────────
    "bugreport.modal.title":               {"it": "🐛 Segnala un bug — purpleGPT Beta", "en": "🐛 Report a bug — purpleGPT Beta", "es": "🐛 Reportar un bug — purpleGPT Beta", "pt": "🐛 Reportar um bug — purpleGPT Beta", "fr": "🐛 Signaler un bug — purpleGPT Beta", "de": "🐛 Fehler melden — purpleGPT Beta"},
    "bugreport.modal.description.label":   {"it": "Descrizione del problema", "en": "Problem description", "es": "Descripción del problema", "pt": "Descrição do problema", "fr": "Description du problème", "de": "Problembeschreibung"},
    "bugreport.modal.description.placeholder": {"it": "Cosa è successo? Descrivi il comportamento inatteso.", "en": "What happened? Describe the unexpected behavior.", "es": "¿Qué pasó? Describe el comportamiento inesperado.", "pt": "O que aconteceu? Descreve o comportamento inesperado.", "fr": "Que s'est-il passé ? Décris le comportement inattendu.", "de": "Was ist passiert? Beschreibe das unerwartete Verhalten."},
    "bugreport.modal.steps.label":         {"it": "Come riprodurlo", "en": "How to reproduce it", "es": "Cómo reproducirlo", "pt": "Como reproduzi-lo", "fr": "Comment le reproduire", "de": "Wie es zu reproduzieren ist"},
    "bugreport.modal.steps.placeholder":   {"it": "Es: Ho usato /draw con il parametro contesto=True e...", "en": "E.g.: I used /draw with contesto=True and...", "es": "Ej: Usé /draw con el parámetro contesto=True y...", "pt": "Ex: Usei /draw com o parâmetro contesto=True e...", "fr": "Ex : J'ai utilisé /draw avec le paramètre contesto=True et...", "de": "Bsp: Ich habe /draw mit dem Parameter contesto=True verwendet und..."},
    "bugreport.modal.command.label":       {"it": "Comando coinvolto (opzionale)", "en": "Command involved (optional)", "es": "Comando involucrado (opcional)", "pt": "Comando envolvido (opcional)", "fr": "Commande concernée (facultatif)", "de": "Betroffener Befehl (optional)"},
    "bugreport.modal.command.placeholder": {"it": "Es: /draw, /chat, menzione...", "en": "E.g.: /draw, /chat, mention...", "es": "Ej: /draw, /chat, mención...", "pt": "Ex: /draw, /chat, menção...", "fr": "Ex : /draw, /chat, mention...", "de": "Bsp: /draw, /chat, Erwähnung..."},
    "bugreport.success":                   {"it": "✅ **Report inviato!** Grazie per aiutarci a migliorare purpleGPT 🟣\n-# Stai usando una versione beta — ogni segnalazione ci aiuta tantissimo.", "en": "✅ **Report sent!** Thanks for helping us improve purpleGPT 🟣\n-# You're using a beta version — every report helps us a lot.", "es": "✅ **¡Reporte enviado!** Gracias por ayudarnos a mejorar purpleGPT 🟣\n-# Estás usando una versión beta — cada reporte nos ayuda mucho.", "pt": "✅ **Relatório enviado!** Obrigado por nos ajudares a melhorar o purpleGPT 🟣\n-# Estás a usar uma versão beta — cada relato ajuda-nos muito.", "fr": "✅ **Rapport envoyé !** Merci de nous aider à améliorer purpleGPT 🟣\n-# Tu utilises une version bêta — chaque signalement nous aide énormément.", "de": "✅ **Bericht gesendet!** Danke, dass du uns hilfst, purpleGPT zu verbessern 🟣\n-# Du verwendest eine Beta-Version — jeder Bericht hilft uns sehr."},

    # ── /vote ─────────────────────────────────────────────────────────────────
    "vote.embed.title":       {"it": "🗳️ Vota purpleGPT su top.gg", "en": "🗳️ Vote for purpleGPT on top.gg", "es": "🗳️ Vota por purpleGPT en top.gg", "pt": "🗳️ Vota no purpleGPT no top.gg", "fr": "🗳️ Vote pour purpleGPT sur top.gg", "de": "🗳️ Stimme für purpleGPT auf top.gg ab"},
    "vote.embed.description": {"it": "Supporta il bot votando su top.gg — è gratuito e richiede solo 10 secondi!\n\nOgni voto ci aiuta a crescere e a migliorare il servizio. 🟣", "en": "Support the bot by voting on top.gg — it's free and takes only 10 seconds!\n\nEvery vote helps us grow and improve the service. 🟣", "es": "Apoya el bot votando en top.gg — ¡es gratis y solo tarda 10 segundos!\n\nCada voto nos ayuda a crecer y mejorar el servicio. 🟣", "pt": "Apoia o bot votando no top.gg — é gratuito e demora apenas 10 segundos!\n\nCada voto ajuda-nos a crescer e a melhorar o serviço. 🟣", "fr": "Soutiens le bot en votant sur top.gg — c'est gratuit et ça prend seulement 10 secondes !\n\nChaque vote nous aide à grandir et à améliorer le service. 🟣", "de": "Unterstütze den Bot, indem du auf top.gg abstimmst — es ist kostenlos und dauert nur 10 Sekunden!\n\nJede Stimme hilft uns zu wachsen und den Dienst zu verbessern. 🟣"},
    "vote.button.vote":       {"it": "Vota su top.gg", "en": "Vote on top.gg", "es": "Votar en top.gg", "pt": "Votar no top.gg", "fr": "Voter sur top.gg", "de": "Auf top.gg abstimmen"},
    "vote.button.voted":      {"it": "Ho votato!", "en": "I voted!", "es": "¡Voté!", "pt": "Votei!", "fr": "J'ai voté !", "de": "Ich habe abgestimmt!"},
    "vote.button.not_yours":  {"it": "Questo bottone non è tuo!", "en": "This button isn't yours!", "es": "¡Este botón no es tuyo!", "pt": "Este botão não é teu!", "fr": "Ce bouton n'est pas le tien !", "de": "Dieser Button gehört nicht dir!"},
    "vote.button.verifying":  {"it": "Bonus in arrivo...", "en": "Bonus incoming...", "es": "Bonus en camino...", "pt": "Bónus a caminho...", "fr": "Bonus en approche...", "de": "Bonus kommt..."},
    "vote.waiting":           {"it": "⏳ Attendi **1 minuto** mentre preparo il tuo bonus voto...", "en": "⏳ Wait **1 minute** while I prepare your vote bonus...", "es": "⏳ Espera **1 minuto** mientras preparo tu bonus de voto...", "pt": "⏳ Aguarda **1 minuto** enquanto preparo o teu bónus de voto...", "fr": "⏳ Attends **1 minute** pendant que je prépare ton bonus de vote...", "de": "⏳ Warte **1 Minute**, während ich deinen Vote-Bonus vorbereite..."},
    "vote.confirmed":         {"it": "✅ Voto confermato! Grazie per il supporto 🟣", "en": "✅ Vote confirmed! Thanks for the support 🟣", "es": "✅ ¡Voto confirmado! Gracias por el apoyo 🟣", "pt": "✅ Voto confirmado! Obrigado pelo apoio 🟣", "fr": "✅ Vote confirmé ! Merci pour le soutien 🟣", "de": "✅ Stimme bestätigt! Danke für deine Unterstützung 🟣"},
    "vote.thanks":            {"it": "🎉 Grazie per aver votato purpleGPT!", "en": "🎉 Thanks for voting for purpleGPT!", "es": "🎉 ¡Gracias por votar por purpleGPT!", "pt": "🎉 Obrigado por votar no purpleGPT!", "fr": "🎉 Merci d'avoir voté pour purpleGPT !", "de": "🎉 Danke für deine Stimme für purpleGPT!"},
    # ── /settings — selettore lingua ─────────────────────────────────────────
    "settings.field.language": {
        "it": "🌍 Lingua",
        "en": "🌍 Language",
        "es": "🌍 Idioma",
        "pt": "🌍 Idioma",
        "fr": "🌍 Langue",
        "de": "🌍 Sprache",
    },
    "settings.field.language.value": {
        "it": "`{value}`  —  lingua dell'interfaccia di purpleGPT",
        "en": "`{value}`  —  purpleGPT interface language",
        "es": "`{value}`  —  idioma de la interfaz de purpleGPT",
        "pt": "`{value}`  —  idioma da interface do purpleGPT",
        "fr": "`{value}`  —  langue de l'interface purpleGPT",
        "de": "`{value}`  —  Sprache der purpleGPT-Oberfläche",
    },
    "settings.language.placeholder": {
        "it": "Lingua...",
        "en": "Language...",
        "es": "Idioma...",
        "pt": "Idioma...",
        "fr": "Langue...",
        "de": "Sprache...",
    },
    "settings.language.saved": {
        "it": "🌍 Lingua impostata su **{value}**.",
        "en": "🌍 Language set to **{value}**.",
        "es": "🌍 Idioma establecido en **{value}**.",
        "pt": "🌍 Idioma definido para **{value}**.",
        "fr": "🌍 Langue définie sur **{value}**.",
        "de": "🌍 Sprache auf **{value}** gesetzt.",
    },
    "settings.button.language": {
        "it": "🌍 Cambia lingua",
        "en": "🌍 Change language",
        "es": "🌍 Cambiar idioma",
        "pt": "🌍 Alterar idioma",
        "fr": "🌍 Changer la langue",
        "de": "🌍 Sprache ändern",
    },


    # ── Opzioni temperatura (dropdown /settings) ──────────────────────────────
    "temp.0.1": {
        "it": "Molto preciso e deterministico",
        "en": "Very precise and deterministic",
        "es": "Muy preciso y determinista",
        "pt": "Muito preciso e determinista",
        "fr": "Très précis et déterministe",
        "de": "Sehr präzise und deterministisch",
    },
    "temp.0.4": {
        "it": "Preciso, poca variabilità",
        "en": "Precise, low variability",
        "es": "Preciso, poca variabilidad",
        "pt": "Preciso, pouca variabilidade",
        "fr": "Précis, peu de variabilité",
        "de": "Präzise, geringe Variabilität",
    },
    "temp.0.7": {
        "it": "Bilanciato (consigliato)",
        "en": "Balanced (recommended)",
        "es": "Equilibrado (recomendado)",
        "pt": "Equilibrado (recomendado)",
        "fr": "Équilibré (recommandé)",
        "de": "Ausgewogen (empfohlen)",
    },
    "temp.1.0": {
        "it": "Creativo (default)",
        "en": "Creative (default)",
        "es": "Creativo (por defecto)",
        "pt": "Criativo (padrão)",
        "fr": "Créatif (défaut)",
        "de": "Kreativ (Standard)",
    },
    "temp.1.4": {
        "it": "Molto creativo",
        "en": "Very creative",
        "es": "Muy creativo",
        "pt": "Muito criativo",
        "fr": "Très créatif",
        "de": "Sehr kreativ",
    },
    "temp.2.0": {
        "it": "Massima creatività",
        "en": "Maximum creativity",
        "es": "Máxima creatividad",
        "pt": "Máxima criatividade",
        "fr": "Créativité maximale",
        "de": "Maximale Kreativität",
    },

    # ── Opzioni formato immagine (dropdown /settings) ─────────────────────────
    "size.1:1": {
        "it": "Quadrato 1:1 — profilo, avatar",
        "en": "Square 1:1 — profile, avatar",
        "es": "Cuadrado 1:1 — perfil, avatar",
        "pt": "Quadrado 1:1 — perfil, avatar",
        "fr": "Carré 1:1 — profil, avatar",
        "de": "Quadratisch 1:1 — Profil, Avatar",
    },
    "size.16:9": {
        "it": "Landscape 16:9 — schermo, banner",
        "en": "Landscape 16:9 — screen, banner",
        "es": "Horizontal 16:9 — pantalla, banner",
        "pt": "Paisagem 16:9 — tela, banner",
        "fr": "Paysage 16:9 — écran, bannière",
        "de": "Querformat 16:9 — Bildschirm, Banner",
    },
    "size.9:16": {
        "it": "Portrait 9:16 — stories, reel",
        "en": "Portrait 9:16 — stories, reel",
        "es": "Vertical 9:16 — stories, reel",
        "pt": "Retrato 9:16 — stories, reel",
        "fr": "Portrait 9:16 — stories, reel",
        "de": "Hochformat 9:16 — Stories, Reel",
    },
    "size.4:3": {
        "it": "Landscape 4:3 — foto classica",
        "en": "Landscape 4:3 — classic photo",
        "es": "Horizontal 4:3 — foto clásica",
        "pt": "Paisagem 4:3 — foto clássica",
        "fr": "Paysage 4:3 — photo classique",
        "de": "Querformat 4:3 — klassisches Foto",
    },
    "size.3:4": {
        "it": "Portrait 3:4 — foto classica verticale",
        "en": "Portrait 3:4 — classic vertical photo",
        "es": "Vertical 3:4 — foto clásica vertical",
        "pt": "Retrato 3:4 — foto clássica vertical",
        "fr": "Portrait 3:4 — photo classique verticale",
        "de": "Hochformat 3:4 — klassisches Hochformat-Foto",
    },


    # ── Messaggi di progresso /draw ───────────────────────────────────────────
    # Lista ordinata — il bot cicla tra questi durante la generazione
    "draw.progress.0": {
        "it": "🎨 Sto generando la tua immagine...",
        "en": "🎨 Generating your image...",
        "es": "🎨 Generando tu imagen...",
        "pt": "🎨 A gerar a tua imagem...",
        "fr": "🎨 Génération de ton image en cours...",
        "de": "🎨 Dein Bild wird generiert...",
    },
    "draw.progress.1": {
        "it": "✨ Quasi pronto, sto perfezionando i dettagli...",
        "en": "✨ Almost there, perfecting the details...",
        "es": "✨ Casi listo, perfeccionando los detalles...",
        "pt": "✨ Quase pronto, a aperfeiçoar os detalhes...",
        "fr": "✨ Presque prêt, je peaufine les détails...",
        "de": "✨ Fast fertig, Details werden verfeinert...",
    },
    "draw.progress.2": {
        "it": "🖌️ Ancora un momento, ci siamo quasi...",
        "en": "🖌️ Just a moment, almost there...",
        "es": "🖌️ Un momento más, ya casi está...",
        "pt": "🖌️ Mais um momento, já quase acabou...",
        "fr": "🖌️ Encore un instant, on y est presque...",
        "de": "🖌️ Noch einen Moment, fast fertig...",
    },

    # ── Messaggi di progresso /edit ───────────────────────────────────────────
    "edit.progress.0": {
        "it": "✏️ Sto modificando la tua immagine...",
        "en": "✏️ Editing your image...",
        "es": "✏️ Modificando tu imagen...",
        "pt": "✏️ A modificar a tua imagem...",
        "fr": "✏️ Modification de ton image en cours...",
        "de": "✏️ Dein Bild wird bearbeitet...",
    },
    "edit.progress.1": {
        "it": "🔍 Sto applicando le modifiche richieste...",
        "en": "🔍 Applying the requested changes...",
        "es": "🔍 Aplicando los cambios solicitados...",
        "pt": "🔍 A aplicar as alterações solicitadas...",
        "fr": "🔍 Application des modifications demandées...",
        "de": "🔍 Die gewünschten Änderungen werden angewendet...",
    },
    "edit.progress.2": {
        "it": "🖼️ Rifinitura finale, quasi pronto...",
        "en": "🖼️ Final touches, almost ready...",
        "es": "🖼️ Toques finales, casi listo...",
        "pt": "🖼️ Retoques finais, quase pronto...",
        "fr": "🖼️ Dernières retouches, presque prêt...",
        "de": "🖼️ Letzte Schliffe, fast fertig...",
    },


    # ── Messaggi di progresso /chat ───────────────────────────────────────────
    "chat.progress.0": {
        "it": "💬 Sto elaborando la tua risposta...",
        "en": "💬 Processing your response...",
        "es": "💬 Procesando tu respuesta...",
        "pt": "💬 A processar a tua resposta...",
        "fr": "💬 Traitement de ta réponse en cours...",
        "de": "💬 Deine Antwort wird verarbeitet...",
    },
    "chat.progress.1": {
        "it": "🧠 Ci sto pensando, un momento...",
        "en": "🧠 Thinking about it, one moment...",
        "es": "🧠 Estoy pensando, un momento...",
        "pt": "🧠 A pensar, um momento...",
        "fr": "🧠 J'y réfléchis, un instant...",
        "de": "🧠 Ich denke nach, einen Moment...",
    },
    "chat.progress.2": {
        "it": "⏳ Ancora un secondo...",
        "en": "⏳ Just a second...",
        "es": "⏳ Solo un segundo...",
        "pt": "⏳ Só um segundo...",
        "fr": "⏳ Encore une seconde...",
        "de": "⏳ Noch eine Sekunde...",
    },


    # ── /broadcast (comando server admin) ────────────────────────────────────
    "broadcast_cmd.dm_title": {
        "it": "🟣 Questo comando richiede un server",
        "en": "🟣 This command requires a server",
        "es": "🟣 Este comando requiere un servidor",
        "pt": "🟣 Este comando requer um servidor",
        "fr": "🟣 Cette commande nécessite un serveur",
        "de": "🟣 Dieser Befehl erfordert einen Server",
    },
    "broadcast_cmd.dm_description": {
        "it": "Usa `/broadcast` in un server per configurare le notifiche di aggiornamento.",
        "en": "Use `/broadcast` in a server to configure update notifications.",
        "es": "Usa `/broadcast` en un servidor para configurar las notificaciones.",
        "pt": "Usa `/broadcast` num servidor para configurar as notificações.",
        "fr": "Utilise `/broadcast` dans un serveur pour configurer les notifications.",
        "de": "Nutze `/broadcast` auf einem Server, um Benachrichtigungen zu konfigurieren.",
    },
    "broadcast_cmd.no_permission": {
        "it": "Serve il permesso **Gestisci server** per usare questo comando.",
        "en": "You need the **Manage Server** permission to use this command.",
        "es": "Necesitas el permiso **Gestionar servidor** para usar este comando.",
        "pt": "Precisas da permissão **Gerir servidor** para usar este comando.",
        "fr": "Tu as besoin de la permission **Gérer le serveur** pour utiliser cette commande.",
        "de": "Du benötigst die Berechtigung **Server verwalten** für diesen Befehl.",
    },
    "broadcast_cmd.embed.title": {
        "it": "📣 Impostazioni Broadcast",
        "en": "📣 Broadcast Settings",
        "es": "📣 Configuración de difusión",
        "pt": "📣 Configurações de transmissão",
        "fr": "📣 Paramètres de diffusion",
        "de": "📣 Broadcast-Einstellungen",
    },
    "broadcast_cmd.embed.description": {
        "it": "Configura come purpleGPT invia avvisi e aggiornamenti in questo server.",
        "en": "Configure how purpleGPT sends announcements and updates in this server.",
        "es": "Configura cómo purpleGPT envía avisos y actualizaciones en este servidor.",
        "pt": "Configura como o purpleGPT envia avisos e atualizações neste servidor.",
        "fr": "Configure comment purpleGPT envoie des annonces et mises à jour sur ce serveur.",
        "de": "Konfiguriere, wie purpleGPT Ankündigungen und Updates auf diesem Server sendet.",
    },
    "broadcast_cmd.field.status": {
        "it": "📡 Stato notifiche",
        "en": "📡 Notification status",
        "es": "📡 Estado de notificaciones",
        "pt": "📡 Estado das notificações",
        "fr": "📡 État des notifications",
        "de": "📡 Benachrichtigungsstatus",
    },
    "broadcast_cmd.field.status.enabled": {
        "it": "✅ Attive",
        "en": "✅ Enabled",
        "es": "✅ Activadas",
        "pt": "✅ Ativas",
        "fr": "✅ Activées",
        "de": "✅ Aktiviert",
    },
    "broadcast_cmd.field.status.disabled": {
        "it": "🔕 Disattivate",
        "en": "🔕 Disabled",
        "es": "🔕 Desactivadas",
        "pt": "🔕 Desativadas",
        "fr": "🔕 Désactivées",
        "de": "🔕 Deaktiviert",
    },
    "broadcast_cmd.field.channel": {
        "it": "📌 Canale notifiche",
        "en": "📌 Notification channel",
        "es": "📌 Canal de notificaciones",
        "pt": "📌 Canal de notificações",
        "fr": "📌 Canal de notifications",
        "de": "📌 Benachrichtigungskanal",
    },
    "broadcast_cmd.field.channel.none": {
        "it": "*Non impostato — verrà usato il canale di sistema*",
        "en": "*Not set — system channel will be used*",
        "es": "*No establecido — se usará el canal del sistema*",
        "pt": "*Não definido — será usado o canal do sistema*",
        "fr": "*Non défini — le canal système sera utilisé*",
        "de": "*Nicht gesetzt — Systemkanal wird verwendet*",
    },
    "broadcast_cmd.footer": {
        "it": "Impostazioni broadcast di {guild}",
        "en": "Broadcast settings for {guild}",
        "es": "Configuración de difusión de {guild}",
        "pt": "Configurações de transmissão de {guild}",
        "fr": "Paramètres de diffusion de {guild}",
        "de": "Broadcast-Einstellungen für {guild}",
    },
    "broadcast_cmd.select.channel.placeholder": {
        "it": "Seleziona canale notifiche...",
        "en": "Select notification channel...",
        "es": "Selecciona el canal de notificaciones...",
        "pt": "Seleciona o canal de notificações...",
        "fr": "Sélectionne le canal de notifications...",
        "de": "Benachrichtigungskanal auswählen...",
    },
    "broadcast_cmd.button.enable": {
        "it": "✅ Attiva",
        "en": "✅ Enable",
        "es": "✅ Activar",
        "pt": "✅ Ativar",
        "fr": "✅ Activer",
        "de": "✅ Aktivieren",
    },
    "broadcast_cmd.button.disable": {
        "it": "🔕 Disattiva",
        "en": "🔕 Disable",
        "es": "🔕 Desactivar",
        "pt": "🔕 Desativar",
        "fr": "🔕 Désactiver",
        "de": "🔕 Deaktivieren",
    },
    "broadcast_cmd.enabled.ok": {
        "it": "✅ Notifiche broadcast **attivate** per questo server.",
        "en": "✅ Broadcast notifications **enabled** for this server.",
        "es": "✅ Notificaciones de difusión **activadas** para este servidor.",
        "pt": "✅ Notificações de transmissão **ativadas** para este servidor.",
        "fr": "✅ Notifications de diffusion **activées** pour ce serveur.",
        "de": "✅ Broadcast-Benachrichtigungen für diesen Server **aktiviert**.",
    },
    "broadcast_cmd.disabled.ok": {
        "it": "🔕 Notifiche broadcast **disattivate** per questo server.",
        "en": "🔕 Broadcast notifications **disabled** for this server.",
        "es": "🔕 Notificaciones de difusión **desactivadas** para este servidor.",
        "pt": "🔕 Notificações de transmissão **desativadas** para este servidor.",
        "fr": "🔕 Notifications de diffusion **désactivées** pour ce serveur.",
        "de": "🔕 Broadcast-Benachrichtigungen für diesen Server **deaktiviert**.",
    },
    "broadcast_cmd.channel.set": {
        "it": "📌 Canale notifiche impostato su {channel}.",
        "en": "📌 Notification channel set to {channel}.",
        "es": "📌 Canal de notificaciones establecido en {channel}.",
        "pt": "📌 Canal de notificações definido para {channel}.",
        "fr": "📌 Canal de notifications défini sur {channel}.",
        "de": "📌 Benachrichtigungskanal auf {channel} gesetzt.",
    },


    # ── /help — campi aggiuntivi ──────────────────────────────────────────────
    "help.field.premium.name": {
        "it": "/premium",
        "en": "/premium",
        "es": "/premium",
        "pt": "/premium",
        "fr": "/premium",
        "de": "/premium",
    },
    "help.field.premium.value": {
        "it": "Visualizza il tuo piano attuale e scopri i vantaggi di Starter e Pro.",
        "en": "View your current plan and explore Starter and Pro benefits.",
        "es": "Consulta tu plan actual y descubre las ventajas de Starter y Pro.",
        "pt": "Vê o teu plano atual e descobre as vantagens do Starter e Pro.",
        "fr": "Consulte ton abonnement actuel et découvre les avantages de Starter et Pro.",
        "de": "Sieh dir deinen aktuellen Plan an und entdecke die Vorteile von Starter und Pro.",
    },
    "help.field.vote.name": {
        "it": "/vote",
        "en": "/vote",
        "es": "/vote",
        "pt": "/vote",
        "fr": "/vote",
        "de": "/vote",
    },
    "help.field.vote.value": {
        "it": "Vota purpleGPT su top.gg e supporta il progetto.",
        "en": "Vote for purpleGPT on top.gg and support the project.",
        "es": "Vota por purpleGPT en top.gg y apoya el proyecto.",
        "pt": "Vota no purpleGPT no top.gg e apoia o projeto.",
        "fr": "Vote pour purpleGPT sur top.gg et soutiens le projet.",
        "de": "Stimme für purpleGPT auf top.gg und unterstütze das Projekt.",
    },
    "help.field.server_prompt.name": {
        "it": "/server_prompt",
        "en": "/server_prompt",
        "es": "/server_prompt",
        "pt": "/server_prompt",
        "fr": "/server_prompt",
        "de": "/server_prompt",
    },
    "help.field.server_prompt.value": {
        "it": "[Admin] Imposta un prompt personalizzato per il server.",
        "en": "[Admin] Set a custom prompt for the server.",
        "es": "[Admin] Establece un prompt personalizado para el servidor.",
        "pt": "[Admin] Define um prompt personalizado para o servidor.",
        "fr": "[Admin] Définit un prompt personnalisé pour le serveur.",
        "de": "[Admin] Legt einen benutzerdefinierten Prompt für den Server fest.",
    },
    "help.field.broadcast.name": {
        "it": "/broadcast",
        "en": "/broadcast",
        "es": "/broadcast",
        "pt": "/broadcast",
        "fr": "/broadcast",
        "de": "/broadcast",
    },
    "help.field.broadcast.value": {
        "it": "[Admin] Configura le notifiche di aggiornamento del server.",
        "en": "[Admin] Configure server update notifications.",
        "es": "[Admin] Configura las notificaciones de actualización del servidor.",
        "pt": "[Admin] Configura as notificações de atualização do servidor.",
        "fr": "[Admin] Configure les notifications de mise à jour du serveur.",
        "de": "[Admin] Konfiguriert Server-Update-Benachrichtigungen.",
    },
    "help.field.genserver.name": {
        "it": "/genserver <description>",
        "en": "/genserver <description>",
        "es": "/genserver <description>",
        "pt": "/genserver <description>",
        "fr": "/genserver <description>",
        "de": "/genserver <description>",
    },
    "help.field.genserver.value": {
        "it": "[Admin] Genera ruoli, categorie e canali Discord da zero con l'AI.",
        "en": "[Admin] Generate Discord roles, categories and channels from scratch using AI.",
        "es": "[Admin] Genera roles, categorías y canales de Discord desde cero con IA.",
        "pt": "[Admin] Gera cargos, categorias e canais Discord do zero com IA.",
        "fr": "[Admin] Génère des rôles, catégories et salons Discord de zéro avec l'IA.",
        "de": "[Admin] Erstellt Discord-Rollen, Kategorien und Kanäle von Grund auf mit KI.",
    },

    # ── /genserver ────────────────────────────────────────────────────────────
    "genserver.progress": {
        "it": "🧠 Sto progettando la struttura del server...",
        "en": "🧠 Designing the server structure...",
        "es": "🧠 Diseñando la estructura del servidor...",
        "pt": "🧠 A desenhar a estrutura do servidor...",
        "fr": "🧠 Conception de la structure du serveur en cours...",
        "de": "🧠 Serverstruktur wird entworfen...",
    },
    "genserver.no_permission": {
        "it": "Serve il permesso **Gestisci Server** per usare questo comando.",
        "en": "You need the **Manage Server** permission to use this command.",
        "es": "Necesitas el permiso **Gestionar servidor** para usar este comando.",
        "pt": "Precisas da permissão **Gerir servidor** para usar este comando.",
        "fr": "Tu as besoin de la permission **Gérer le serveur** pour utiliser cette commande.",
        "de": "Du benötigst die Berechtigung **Server verwalten** für diesen Befehl.",
    },
    "genserver.no_roles_permission": {
        "it": "Per generare ruoli serve anche il permesso **Gestisci ruoli**. Riprova con `roles: false` oppure chiedi a un admin con quel permesso.",
        "en": "To generate roles, you also need the **Manage Roles** permission. Try again with `roles: false` or ask an admin with that permission.",
        "es": "Para generar roles, también necesitas el permiso **Gestionar roles**. Prueba con `roles: false` o pide ayuda a un admin con ese permiso.",
        "pt": "Para gerar cargos, também precisas da permissão **Gerir cargos**. Tenta com `roles: false` ou pede ajuda a um admin com essa permissão.",
        "fr": "Pour générer des rôles, tu as aussi besoin de la permission **Gérer les rôles**. Réessaie avec `roles: false` ou demande à un admin qui l'a.",
        "de": "Zum Erstellen von Rollen brauchst du zusätzlich die Berechtigung **Rollen verwalten**. Versuche es mit `roles: false` oder frage einen Admin mit dieser Berechtigung.",
    },
    "genserver.bot_no_permission": {
        "it": "⚠️ Il bot non ha il permesso di gestire i canali in questo server.",
        "en": "⚠️ The bot doesn't have permission to manage channels in this server.",
        "es": "⚠️ El bot no tiene permiso para gestionar canales en este servidor.",
        "pt": "⚠️ O bot não tem permissão para gerir canais neste servidor.",
        "fr": "⚠️ Le bot n'a pas la permission de gérer les salons sur ce serveur.",
        "de": "⚠️ Der Bot hat keine Berechtigung, Kanäle auf diesem Server zu verwalten.",
    },
    "genserver.bot_no_roles_permission": {
        "it": "⚠️ Per generare ruoli, il bot deve avere il permesso **Gestisci ruoli**. Riprova con `roles: false` oppure aggiorna i permessi del bot.",
        "en": "⚠️ To generate roles, the bot needs the **Manage Roles** permission. Try again with `roles: false` or update the bot permissions.",
        "es": "⚠️ Para generar roles, el bot necesita el permiso **Gestionar roles**. Prueba de nuevo con `roles: false` o actualiza los permisos del bot.",
        "pt": "⚠️ Para gerar cargos, o bot precisa da permissão **Gerir cargos**. Tenta novamente com `roles: false` ou atualiza as permissões do bot.",
        "fr": "⚠️ Pour générer des rôles, le bot a besoin de la permission **Gérer les rôles**. Réessaie avec `roles: false` ou mets à jour ses permissions.",
        "de": "⚠️ Zum Erstellen von Rollen benötigt der Bot die Berechtigung **Rollen verwalten**. Versuche es mit `roles: false` erneut oder aktualisiere die Bot-Berechtigungen.",
    },
    "genserver.dm_title": {
        "it": "🟣 Questo comando richiede un server",
        "en": "🟣 This command requires a server",
        "es": "🟣 Este comando requiere un servidor",
        "pt": "🟣 Este comando requer um servidor",
        "fr": "🟣 Cette commande nécessite un serveur",
        "de": "🟣 Dieser Befehl erfordert einen Server",
    },
    "genserver.dm_description": {
        "it": "Usa `/genserver` in un server per generare ruoli, canali e categorie con l'AI.",
        "en": "Use `/genserver` in a server to generate roles, channels and categories with AI.",
        "es": "Usa `/genserver` en un servidor para generar roles, canales y categorías con IA.",
        "pt": "Usa `/genserver` num servidor para gerar cargos, canais e categorias com IA.",
        "fr": "Utilise `/genserver` dans un serveur pour générer des rôles, salons et catégories avec l'IA.",
        "de": "Nutze `/genserver` auf einem Server, um Rollen, Kanäle und Kategorien mit KI zu erstellen.",
    },
    "genserver.error_parse": {
        "it": "❌ Non sono riuscito a interpretare la risposta dell'AI. Prova a riformulare la descrizione del server.",
        "en": "❌ I couldn't interpret the AI response. Try rephrasing the server description.",
        "es": "❌ No pude interpretar la respuesta de la IA. Intenta reformular la descripción del servidor.",
        "pt": "❌ Não consegui interpretar a resposta da IA. Tenta reformular a descrição do servidor.",
        "fr": "❌ Je n'ai pas pu interpréter la réponse de l'IA. Essaie de reformuler la description.",
        "de": "❌ Ich konnte die KI-Antwort nicht verarbeiten. Versuche, die Beschreibung umzuformulieren.",
    },
    "genserver.error_empty": {
        "it": "❌ L'AI non ha generato una struttura valida. Riprova con una descrizione più dettagliata.",
        "en": "❌ The AI didn't generate a valid structure. Try again with a more detailed description.",
        "es": "❌ La IA no generó una estructura válida. Intenta con una descripción más detallada.",
        "pt": "❌ A IA não gerou uma estrutura válida. Tenta com uma descrição mais detalhada.",
        "fr": "❌ L'IA n'a pas généré une structure valide. Réessaie avec une description plus détaillée.",
        "de": "❌ Die KI hat keine gültige Struktur generiert. Versuche es mit einer detaillierteren Beschreibung.",
    },
    "genserver.confirm.title": {
        "it": "🏗️ Struttura proposta da purpleGPT",
        "en": "🏗️ Structure proposed by purpleGPT",
        "es": "🏗️ Estructura propuesta por purpleGPT",
        "pt": "🏗️ Estrutura proposta pelo purpleGPT",
        "fr": "🏗️ Structure proposée par purpleGPT",
        "de": "🏗️ Von purpleGPT vorgeschlagene Struktur",
    },
    "genserver.confirm.description": {
        "it": "Ecco cosa verrà creato nel server. Conferma per procedere o annulla.",
        "en": "Here's what will be created in the server. Confirm to proceed or cancel.",
        "es": "Esto es lo que se creará en el servidor. Confirma para continuar o cancela.",
        "pt": "Isto é o que será criado no servidor. Confirma para continuar ou cancela.",
        "fr": "Voici ce qui sera créé sur le serveur. Confirme pour continuer ou annule.",
        "de": "Das wird auf dem Server erstellt. Bestätige zum Fortfahren oder brich ab.",
    },
    "genserver.confirm.roles": {
        "it": "Ruoli",
        "en": "Roles",
        "es": "Roles",
        "pt": "Cargos",
        "fr": "Rôles",
        "de": "Rollen",
    },
    "genserver.preflight.title": {
        "it": "⚠️ Prima di generare i ruoli",
        "en": "⚠️ Before generating roles",
        "es": "⚠️ Antes de generar roles",
        "pt": "⚠️ Antes de gerar cargos",
        "fr": "⚠️ Avant de générer les rôles",
        "de": "⚠️ Vor dem Erstellen von Rollen",
    },
    "genserver.preflight.description": {
        "it": "purpleGPT può creare ruoli solo con i permessi che il bot possiede davvero e solo sotto il suo ruolo più alto.\n\nSe alcuni ruoli sembrano \"rotti\" o troppo semplici, ad esempio un ruolo amministratore senza permessi admin, significa che il bot non può concedere quei permessi in questo server.\n\nSe vuoi ruoli completi, controlla prima che il ruolo del bot sia abbastanza in alto e abbia i permessi necessari. Se continui, verranno usati solo i permessi sicuri e disponibili.",
        "en": "purpleGPT can only create roles with permissions the bot actually has, and only below its highest role.\n\nIf some roles look \"broken\" or too basic, for example an administrator role without admin permissions, it means the bot cannot grant those permissions in this server.\n\nIf you want full roles, first check that the bot role is high enough and has the needed permissions. If you continue, only safe and available permissions will be used.",
        "es": "purpleGPT solo puede crear roles con los permisos que el bot realmente tiene y solo por debajo de su rol más alto.\n\nSi algunos roles parecen \"rotos\" o demasiado básicos, por ejemplo un rol de administrador sin permisos de admin, significa que el bot no puede conceder esos permisos en este servidor.\n\nSi quieres roles completos, comprueba primero que el rol del bot esté lo bastante alto y tenga los permisos necesarios. Si continúas, solo se usarán permisos seguros y disponibles.",
        "pt": "O purpleGPT só pode criar cargos com permissões que o bot realmente tem e apenas abaixo do cargo mais alto dele.\n\nSe alguns cargos parecerem \"quebrados\" ou demasiado básicos, por exemplo um cargo de administrador sem permissões de admin, significa que o bot não pode conceder essas permissões neste servidor.\n\nSe quiseres cargos completos, confirma primeiro que o cargo do bot está alto o suficiente e tem as permissões necessárias. Se continuares, só serão usadas permissões seguras e disponíveis.",
        "fr": "purpleGPT ne peut créer des rôles qu'avec les permissions que le bot possède réellement, et uniquement sous son rôle le plus élevé.\n\nSi certains rôles semblent \"cassés\" ou trop basiques, par exemple un rôle administrateur sans permissions admin, cela signifie que le bot ne peut pas accorder ces permissions sur ce serveur.\n\nSi tu veux des rôles complets, vérifie d'abord que le rôle du bot est assez haut et possède les permissions nécessaires. Si tu continues, seules les permissions sûres et disponibles seront utilisées.",
        "de": "purpleGPT kann Rollen nur mit Berechtigungen erstellen, die der Bot wirklich besitzt, und nur unterhalb seiner höchsten Rolle.\n\nWenn manche Rollen \"kaputt\" oder zu einfach wirken, zum Beispiel eine Administrator-Rolle ohne Admin-Berechtigungen, bedeutet das, dass der Bot diese Berechtigungen auf diesem Server nicht vergeben kann.\n\nWenn du vollständige Rollen möchtest, prüfe zuerst, ob die Bot-Rolle hoch genug ist und die nötigen Berechtigungen hat. Wenn du fortfährst, werden nur sichere und verfügbare Berechtigungen verwendet.",
    },
    "genserver.preflight.continue": {
        "it": "Continua",
        "en": "Continue",
        "es": "Continuar",
        "pt": "Continuar",
        "fr": "Continuer",
        "de": "Fortfahren",
    },
    "genserver.preflight.cancel": {
        "it": "Annulla",
        "en": "Cancel",
        "es": "Cancelar",
        "pt": "Cancelar",
        "fr": "Annuler",
        "de": "Abbrechen",
    },
    "genserver.confirm.footer": {
        "it": "Ruoli e canali esistenti non verranno eliminati",
        "en": "Existing roles and channels will not be deleted",
        "es": "Los roles y canales existentes no serán eliminados",
        "pt": "Os cargos e canais existentes não serão eliminados",
        "fr": "Les rôles et salons existants ne seront pas supprimés",
        "de": "Bestehende Rollen und Kanäle werden nicht gelöscht",
    },
    "genserver.button.confirm": {
        "it": "✅ Crea struttura",
        "en": "✅ Create structure",
        "es": "✅ Crear estructura",
        "pt": "✅ Criar estrutura",
        "fr": "✅ Créer la structure",
        "de": "✅ Struktur erstellen",
    },
    "genserver.button.cancel": {
        "it": "❌ Annulla",
        "en": "❌ Cancel",
        "es": "❌ Cancelar",
        "pt": "❌ Cancelar",
        "fr": "❌ Annuler",
        "de": "❌ Abbrechen",
    },
    "genserver.cancelled": {
        "it": "❌ Creazione annullata.",
        "en": "❌ Creation cancelled.",
        "es": "❌ Creación cancelada.",
        "pt": "❌ Criação cancelada.",
        "fr": "❌ Création annulée.",
        "de": "❌ Erstellung abgebrochen.",
    },
    "genserver.building": {
        "it": "⚙️ Sto costruendo la struttura del server...",
        "en": "⚙️ Building the server structure...",
        "es": "⚙️ Construyendo la estructura del servidor...",
        "pt": "⚙️ A construir a estrutura do servidor...",
        "fr": "⚙️ Construction de la structure du serveur...",
        "de": "⚙️ Serverstruktur wird erstellt...",
    },
    "genserver.done": {
        "it": "✅ Struttura creata! **{roles}** ruoli, **{categories}** categorie e **{channels}** canali aggiunti al server.",
        "en": "✅ Structure created! **{roles}** roles, **{categories}** categories and **{channels}** channels added to the server.",
        "es": "✅ ¡Estructura creada! **{roles}** roles, **{categories}** categorías y **{channels}** canales añadidos al servidor.",
        "pt": "✅ Estrutura criada! **{roles}** cargos, **{categories}** categorias e **{channels}** canais adicionados ao servidor.",
        "fr": "✅ Structure créée! **{roles}** rôles, **{categories}** catégories et **{channels}** salons ajoutés au serveur.",
        "de": "✅ Struktur erstellt! **{roles}** Rollen, **{categories}** Kategorien und **{channels}** Kanäle zum Server hinzugefügt.",
    },
    "genserver.error_create": {
        "it": "⚠️ Creazione completata parzialmente. Alcuni ruoli, categorie o canali potrebbero non essere stati creati.",
        "en": "⚠️ Creation partially completed. Some roles, categories or channels may not have been created.",
        "es": "⚠️ Creación completada parcialmente. Es posible que algunos roles, categorías o canales no se hayan creado.",
        "pt": "⚠️ Criação parcialmente concluída. Alguns cargos, categorias ou canais podem não ter sido criados.",
        "fr": "⚠️ Création partiellement terminée. Certains rôles, catégories ou salons n'ont peut-être pas été créés.",
        "de": "⚠️ Erstellung teilweise abgeschlossen. Einige Rollen, Kategorien oder Kanäle wurden möglicherweise nicht erstellt.",
    },
    "genserver.not_yours": {
        "it": "Questo pannello non è tuo.",
        "en": "This panel is not yours.",
        "es": "Este panel no es tuyo.",
        "pt": "Este painel não é teu.",
        "fr": "Ce panneau n'est pas le tien.",
        "de": "Dieses Panel gehört nicht dir.",
    },


    # ── /welcome (server admin) ───────────────────────────────────────────────
    "welcome_cmd.dm_title": {
        "it": "🟣 Questo comando richiede un server",
        "en": "🟣 This command requires a server",
        "es": "🟣 Este comando requiere un servidor",
        "pt": "🟣 Este comando requer um servidor",
        "fr": "🟣 Cette commande nécessite un serveur",
        "de": "🟣 Dieser Befehl erfordert einen Server",
    },
    "welcome_cmd.dm_description": {
        "it": "Usa `/welcome` in un server per configurare i messaggi di benvenuto.",
        "en": "Use `/welcome` in a server to configure welcome messages.",
        "es": "Usa `/welcome` en un servidor para configurar los mensajes de bienvenida.",
        "pt": "Usa `/welcome` num servidor para configurar as mensagens de boas-vindas.",
        "fr": "Utilise `/welcome` dans un serveur pour configurer les messages de bienvenue.",
        "de": "Nutze `/welcome` auf einem Server, um Willkommensnachrichten zu konfigurieren.",
    },
    "welcome_cmd.no_permission": {
        "it": "Serve il permesso **Gestisci server** per usare questo comando.",
        "en": "You need the **Manage Server** permission to use this command.",
        "es": "Necesitas el permiso **Gestionar servidor** para usar este comando.",
        "pt": "Precisas da permissão **Gerir servidor** para usar este comando.",
        "fr": "Tu as besoin de la permission **Gérer le serveur** pour utiliser cette commande.",
        "de": "Du benötigst die Berechtigung **Server verwalten** für diesen Befehl.",
    },
    "welcome_cmd.embed.title": {
        "it": "👋 Impostazioni Benvenuto",
        "en": "👋 Welcome Settings",
        "es": "👋 Configuración de bienvenida",
        "pt": "👋 Configurações de boas-vindas",
        "fr": "👋 Paramètres de bienvenue",
        "de": "👋 Willkommens-Einstellungen",
    },
    "welcome_cmd.embed.description": {
        "it": "Configura i messaggi di benvenuto AI per i nuovi membri di questo server.",
        "en": "Configure AI-powered welcome messages for new members of this server.",
        "es": "Configura los mensajes de bienvenida IA para los nuevos miembros de este servidor.",
        "pt": "Configura as mensagens de boas-vindas IA para os novos membros deste servidor.",
        "fr": "Configure les messages de bienvenue IA pour les nouveaux membres de ce serveur.",
        "de": "Konfiguriere KI-Willkommensnachrichten für neue Mitglieder dieses Servers.",
    },
    "welcome_cmd.field.status": {
        "it": "✨ Stato",
        "en": "✨ Status",
        "es": "✨ Estado",
        "pt": "✨ Estado",
        "fr": "✨ Statut",
        "de": "✨ Status",
    },
    "welcome_cmd.field.status.enabled": {
        "it": "✅ Attivo",
        "en": "✅ Enabled",
        "es": "✅ Activado",
        "pt": "✅ Ativo",
        "fr": "✅ Activé",
        "de": "✅ Aktiviert",
    },
    "welcome_cmd.field.status.disabled": {
        "it": "🔕 Disattivato",
        "en": "🔕 Disabled",
        "es": "🔕 Desactivado",
        "pt": "🔕 Desativado",
        "fr": "🔕 Désactivé",
        "de": "🔕 Deaktiviert",
    },
    "welcome_cmd.field.channel": {
        "it": "📌 Canale benvenuto",
        "en": "📌 Welcome channel",
        "es": "📌 Canal de bienvenida",
        "pt": "📌 Canal de boas-vindas",
        "fr": "📌 Salon de bienvenue",
        "de": "📌 Willkommenskanal",
    },
    "welcome_cmd.field.channel.none": {
        "it": "*Non impostato — verrà usato il canale di sistema*",
        "en": "*Not set — system channel will be used*",
        "es": "*No establecido — se usará el canal del sistema*",
        "pt": "*Não definido — será usado o canal do sistema*",
        "fr": "*Non défini — le canal système sera utilisé*",
        "de": "*Nicht gesetzt — Systemkanal wird verwendet*",
    },
    "welcome_cmd.footer": {
        "it": "Impostazioni benvenuto di {guild}",
        "en": "Welcome settings for {guild}",
        "es": "Configuración de bienvenida de {guild}",
        "pt": "Configurações de boas-vindas de {guild}",
        "fr": "Paramètres de bienvenue de {guild}",
        "de": "Willkommens-Einstellungen für {guild}",
    },
    "welcome_cmd.select.placeholder": {
        "it": "Seleziona canale benvenuto...",
        "en": "Select welcome channel...",
        "es": "Selecciona el canal de bienvenida...",
        "pt": "Seleciona o canal de boas-vindas...",
        "fr": "Sélectionne le salon de bienvenue...",
        "de": "Willkommenskanal auswählen...",
    },
    "welcome_cmd.button.enable": {
        "it": "✅ Attiva",
        "en": "✅ Enable",
        "es": "✅ Activar",
        "pt": "✅ Ativar",
        "fr": "✅ Activer",
        "de": "✅ Aktivieren",
    },
    "welcome_cmd.button.disable": {
        "it": "🔕 Disattiva",
        "en": "🔕 Disable",
        "es": "🔕 Desactivar",
        "pt": "🔕 Desativar",
        "fr": "🔕 Désactiver",
        "de": "🔕 Deaktivieren",
    },
    "welcome_cmd.enabled.ok": {
        "it": "✅ Messaggi di benvenuto **attivati** per questo server.",
        "en": "✅ Welcome messages **enabled** for this server.",
        "es": "✅ Mensajes de bienvenida **activados** para este servidor.",
        "pt": "✅ Mensagens de boas-vindas **ativadas** para este servidor.",
        "fr": "✅ Messages de bienvenue **activés** pour ce serveur.",
        "de": "✅ Willkommensnachrichten für diesen Server **aktiviert**.",
    },
    "welcome_cmd.disabled.ok": {
        "it": "🔕 Messaggi di benvenuto **disattivati** per questo server.",
        "en": "🔕 Welcome messages **disabled** for this server.",
        "es": "🔕 Mensajes de bienvenida **desactivados** para este servidor.",
        "pt": "🔕 Mensagens de boas-vindas **desativadas** para este servidor.",
        "fr": "🔕 Messages de bienvenue **désactivés** pour ce serveur.",
        "de": "🔕 Willkommensnachrichten für diesen Server **deaktiviert**.",
    },
    "welcome_cmd.channel.set": {
        "it": "📌 Canale benvenuto impostato su {channel}.",
        "en": "📌 Welcome channel set to {channel}.",
        "es": "📌 Canal de bienvenida establecido en {channel}.",
        "pt": "📌 Canal de boas-vindas definido para {channel}.",
        "fr": "📌 Salon de bienvenue défini sur {channel}.",
        "de": "📌 Willkommenskanal auf {channel} gesetzt.",
    },
    "welcome_cmd.not_yours": {
        "it": "Questo pannello non è tuo.",
        "en": "This panel is not yours.",
        "es": "Este panel no es tuyo.",
        "pt": "Este painel não é teu.",
        "fr": "Ce panneau n'est pas le tien.",
        "de": "Dieses Panel gehört nicht dir.",
    },
    "welcome.message": {
        "it": "👋 Benvenuto/a in **{server}**, {user}!\n\n{ai_message}",
        "en": "👋 Welcome to **{server}**, {user}!\n\n{ai_message}",
        "es": "👋 ¡Bienvenido/a a **{server}**, {user}!\n\n{ai_message}",
        "pt": "👋 Bem-vindo/a a **{server}**, {user}!\n\n{ai_message}",
        "fr": "👋 Bienvenue sur **{server}**, {user} !\n\n{ai_message}",
        "de": "👋 Willkommen auf **{server}**, {user}!\n\n{ai_message}",
    },

    # ── help fields for new commands ──────────────────────────────────────────
    "help.field.welcome.name": {
        "it": "/welcome",
        "en": "/welcome",
        "es": "/welcome",
        "pt": "/welcome",
        "fr": "/welcome",
        "de": "/welcome",
    },
    "help.field.welcome.value": {
        "it": "[Admin] Configura i messaggi di benvenuto AI per i nuovi membri.",
        "en": "[Admin] Configure AI welcome messages for new members.",
        "es": "[Admin] Configura los mensajes de bienvenida IA para nuevos miembros.",
        "pt": "[Admin] Configura as mensagens de boas-vindas IA para novos membros.",
        "fr": "[Admin] Configure les messages de bienvenue IA pour les nouveaux membres.",
        "de": "[Admin] Konfiguriert KI-Willkommensnachrichten für neue Mitglieder.",
    },

    # ── /premium command ──────────────────────────────────────────────────────
    "premium.cmd.title": {
        "en": "✨ purpleGPT Premium",
        "it": "✨ purpleGPT Premium",
        "es": "✨ purpleGPT Premium",
        "pt": "✨ purpleGPT Premium",
        "fr": "✨ purpleGPT Premium",
        "de": "✨ purpleGPT Premium",
    },
    "premium.cmd.desc": {
        "en": "Unlock more from purpleGPT. You can subscribe through Discord too, but using the Stripe buttons supports the team more directly and includes a **7-day free trial**.",
        "it": "Sblocca di più da purpleGPT. Puoi abbonarti anche da Discord, ma usando i bottoni Stripe supporti il team più direttamente e hai una **prova gratuita di 7 giorni**.",
        "es": "Desbloquea más de purpleGPT. También puedes suscribirte desde Discord, pero usar los botones de Stripe apoya más directamente al equipo e incluye una **prueba gratuita de 7 días**.",
        "pt": "Desbloqueia mais do purpleGPT. Também podes subscrever pelo Discord, mas usar os botões da Stripe apoia a equipa mais diretamente e inclui **7 dias de trial gratuito**.",
        "fr": "Débloquez plus de purpleGPT. Vous pouvez aussi vous abonner via Discord, mais utiliser les boutons Stripe soutient plus directement l'équipe et inclut un **essai gratuit de 7 jours**.",
        "de": "Hol mehr aus purpleGPT heraus. Du kannst auch über Discord abonnieren, aber mit den Stripe-Buttons unterstützt du das Team direkter und bekommst **7 Tage kostenlos testen**.",
    },
    "premium.current.title": {
        "en": "Your current plan",
        "it": "Il tuo piano attuale",
        "es": "Tu plan actual",
        "pt": "O teu plano atual",
        "fr": "Ton plan actuel",
        "de": "Dein aktueller Plan",
    },
    "premium.current.free": {
        "en": "**Free** — upgrade to unlock more images, music and /genserver uses.",
        "it": "**Free** — fai upgrade per sbloccare più immagini, musica e utilizzi di /genserver.",
        "es": "**Free** — actualiza para desbloquear más imágenes, música y usos de /genserver.",
        "pt": "**Free** — faz upgrade para desbloquear mais imagens, música e usos de /genserver.",
        "fr": "**Free** — passez à un plan supérieur pour débloquer plus d'images, musique et /genserver.",
        "de": "**Free** — upgrade für mehr Bilder, Musik und /genserver-Nutzungen.",
    },
    "premium.current.starter": {
        "en": "**Starter** — active until {expires}",
        "it": "**Starter** — attivo fino al {expires}",
        "es": "**Starter** — activo hasta el {expires}",
        "pt": "**Starter** — ativo até {expires}",
        "fr": "**Starter** — actif jusqu'au {expires}",
        "de": "**Starter** — aktiv bis {expires}",
    },
    "premium.current.pro": {
        "en": "**Pro** — active until {expires}",
        "it": "**Pro** — attivo fino al {expires}",
        "es": "**Pro** — activo hasta el {expires}",
        "pt": "**Pro** — ativo até {expires}",
        "fr": "**Pro** — actif jusqu'au {expires}",
        "de": "**Pro** — aktiv bis {expires}",
    },
    "premium.current.starter_trial": {
        "en": "🎁 **Starter — Free trial** · ends on {expires}",
        "it": "🎁 **Starter — Prova gratuita** · termina il {expires}",
        "es": "🎁 **Starter — Prueba gratuita** · termina el {expires}",
        "pt": "🎁 **Starter — Trial gratuito** · termina a {expires}",
        "fr": "🎁 **Starter — Essai gratuit** · se termine le {expires}",
        "de": "🎁 **Starter — Kostenloser Test** · endet am {expires}",
    },
    "premium.current.pro_trial": {
        "en": "🎁 **Pro — Free trial** · ends on {expires}",
        "it": "🎁 **Pro — Prova gratuita** · termina il {expires}",
        "es": "🎁 **Pro — Prueba gratuita** · termina el {expires}",
        "pt": "🎁 **Pro — Trial gratuito** · termina a {expires}",
        "fr": "🎁 **Pro — Essai gratuit** · se termine le {expires}",
        "de": "🎁 **Pro — Kostenloser Test** · endet am {expires}",
    },
    "premium.trial.hint": {
        "en": "You're on a free trial — your card will be charged when it ends, or cancel anytime from the Stripe email.",
        "it": "Sei in prova gratuita — la carta verrà addebitata alla scadenza, oppure cancella dall'email Stripe.",
        "es": "Estás en prueba gratuita — tu tarjeta se cobrará al terminar, o cancela desde el email de Stripe.",
        "pt": "Estás em trial gratuito — o cartão será cobrado no final, ou cancela do email da Stripe.",
        "fr": "Tu es en essai gratuit — ta carte sera débitée à la fin, ou annule depuis l'email Stripe.",
        "de": "Du bist im Gratis-Test — deine Karte wird am Ende belastet, oder kündige über die Stripe-E-Mail.",
    },
    "premium.plan.free.name": {
        "en": "Free — €0/month",
        "it": "Free — €0/mese",
        "es": "Free — €0/mes",
        "pt": "Free — €0/mês",
        "fr": "Free — €0/mois",
        "de": "Free — €0/Monat",
    },
    "premium.plan.free.benefits": {
        "en": "• 20 Flash chats/day\n• 1 image/day (+1 with /vote)\n• 1 music/day\n• 1 /genserver/month\n• No Pro model",
        "it": "• 20 chat Flash/giorno\n• 1 immagine/giorno (+1 con /vote)\n• 1 brano musicale/giorno\n• 1 /genserver/mese\n• Nessun modello Pro",
        "es": "• 20 chats Flash/día\n• 1 imagen/día (+1 con /vote)\n• 1 composición/día\n• 1 /genserver/mes\n• Sin modelo Pro",
        "pt": "• 20 chats Flash/dia\n• 1 imagem/dia (+1 com /vote)\n• 1 composição/dia\n• 1 /genserver/mês\n• Sem modelo Pro",
        "fr": "• 20 chats Flash/jour\n• 1 image/jour (+1 avec /vote)\n• 1 musique/jour\n• 1 /genserver/mois\n• Pas de modèle Pro",
        "de": "• 20 Flash-Chats/Tag\n• 1 Bild/Tag (+1 mit /vote)\n• 1 Musikstück/Tag\n• 1 /genserver/Monat\n• Kein Pro-Modell",
    },
    "premium.plan.starter.name": {
        "en": "⚡ Starter — €1.99/month",
        "it": "⚡ Starter — €1.99/mese",
        "es": "⚡ Starter — €1.99/mes",
        "pt": "⚡ Starter — €1.99/mês",
        "fr": "⚡ Starter — €1.99/mois",
        "de": "⚡ Starter — €1.99/Monat",
    },
    "premium.plan.starter.benefits": {
        "en": "• **150 Flash chats**/day\n• **8 images**/day\n• **3 music**/day\n• **1 /genserver**/month\n• No Pro model",
        "it": "• **150 chat Flash**/giorno\n• **8 immagini**/giorno\n• **3 brani musicali**/giorno\n• **1 /genserver**/mese\n• Nessun modello Pro",
        "es": "• **150 chats Flash**/día\n• **8 imágenes**/día\n• **3 composiciones**/día\n• **1 /genserver**/mes\n• Sin modelo Pro",
        "pt": "• **150 chats Flash**/dia\n• **8 imagens**/dia\n• **3 composições**/dia\n• **1 /genserver**/mês\n• Sem modelo Pro",
        "fr": "• **150 chats Flash**/jour\n• **8 images**/jour\n• **3 musiques**/jour\n• **1 /genserver**/mois\n• Pas de modèle Pro",
        "de": "• **150 Flash-Chats**/Tag\n• **8 Bilder**/Tag\n• **3 Musikstücke**/Tag\n• **1 /genserver**/Monat\n• Kein Pro-Modell",
    },
    "premium.plan.pro.name": {
        "en": "🚀 Pro — €3.99/month",
        "it": "🚀 Pro — €3.99/mese",
        "es": "🚀 Pro — €3.99/mes",
        "pt": "🚀 Pro — €3.99/mês",
        "fr": "🚀 Pro — €3.99/mois",
        "de": "🚀 Pro — €3.99/Monat",
    },
    "premium.plan.pro.benefits": {
        "en": "• **Unlimited Flash usage**\n• **50 Pro chats**/month\n• **20 images**/day\n• **10 music**/day\n• **Unlimited /genserver**",
        "it": "• **Utilizzo Flash illimitato**\n• **50 chat Pro**/mese\n• **20 immagini**/giorno\n• **10 brani musicali**/giorno\n• **/genserver illimitato**",
        "es": "• **Uso ilimitado de Flash**\n• **50 chats Pro**/mes\n• **20 imágenes**/día\n• **10 composiciones**/día\n• **/genserver ilimitado**",
        "pt": "• **Uso ilimitado do Flash**\n• **50 chats Pro**/mês\n• **20 imagens**/dia\n• **10 composições**/dia\n• **/genserver ilimitado**",
        "fr": "• **Utilisation illimitée de Flash**\n• **50 chats Pro**/mois\n• **20 images**/jour\n• **10 musiques**/jour\n• **/genserver illimité**",
        "de": "• **Unbegrenzte Flash-Nutzung**\n• **50 Pro-Chats**/Monat\n• **20 Bilder**/Tag\n• **10 Musikstücke**/Tag\n• **Unbegrenztes /genserver**",
    },
    "premium.btn.starter": {
        "en": "Try Starter — 7 days free",
        "it": "Prova Starter — 7 giorni gratis",
        "es": "Prueba Starter — 7 días gratis",
        "pt": "Experimenta Starter — 7 dias grátis",
        "fr": "Essayer Starter — 7 jours gratuits",
        "de": "Starter testen — 7 Tage gratis",
    },
    "premium.btn.pro": {
        "en": "Subscribe to Pro",
        "it": "Abbonati a Pro",
        "es": "Suscribirse a Pro",
        "pt": "Subscrever Pro",
        "fr": "S'abonner à Pro",
        "de": "Pro abonnieren",
    },
    "premium.footer": {
        "en": "Secure payment handled by Stripe · Cancel anytime",
        "it": "Pagamento sicuro gestito da Stripe · Cancella quando vuoi",
        "es": "Pago seguro gestionado por Stripe · Cancela cuando quieras",
        "pt": "Pagamento seguro gerido pela Stripe · Cancela quando quiseres",
        "fr": "Paiement sécurisé par Stripe · Annulez à tout moment",
        "de": "Sichere Zahlung über Stripe · Jederzeit kündbar",
    },
    "premium.btn.manage": {
        "en": "Manage subscription",
        "it": "Gestisci abbonamento",
        "es": "Gestionar suscripción",
        "pt": "Gerir subscrição",
        "fr": "Gérer l'abonnement",
        "de": "Abonnement verwalten",
    },

    # ── Quota exhausted hint (shown when free users hit the limit) ────────────
    "quota.hint.upgrade": {
        "en": "You can unlock more with purpleGPT Premium. Starter includes a 7-day free trial — use `/premium` to upgrade.",
        "it": "Puoi sbloccare di più con purpleGPT Premium. Starter include una prova gratuita di 7 giorni — usa `/premium` per fare upgrade.",
        "es": "Puedes desbloquear más con purpleGPT Premium. Starter incluye una prueba gratuita de 7 días — usa `/premium` para mejorar.",
        "pt": "Podes desbloquear mais com purpleGPT Premium. O Starter inclui 7 dias de trial gratuito — usa `/premium` para fazer upgrade.",
        "fr": "Débloque plus avec purpleGPT Premium. Le Starter inclut 7 jours d'essai gratuit — utilise `/premium` pour passer à la version supérieure.",
        "de": "Mit purpleGPT Premium kannst du mehr freischalten. Starter enthält 7 Tage kostenlos — nutze `/premium` für ein Upgrade.",
    },

    # ── /vote bonus feedback ──────────────────────────────────────────────────
    "vote.bonus.granted": {
        "en": "🎉 Thanks for voting! You unlocked **+{img} extra image generation** for today.",
        "it": "🎉 Grazie per aver votato! Hai sbloccato **+{img} generazione immagine extra** per oggi.",
        "es": "🎉 ¡Gracias por votar! Has desbloqueado **+{img} generación de imagen extra** por hoy.",
        "pt": "🎉 Obrigado por votares! Desbloqueaste **+{img} geração de imagem extra** para hoje.",
        "fr": "🎉 Merci d'avoir voté ! Tu as débloqué **+{img} génération d'image en plus** aujourd'hui.",
        "de": "🎉 Danke fürs Voten! Du hast heute **+{img} zusätzliche Bildgenerierung** freigeschaltet.",
    },
    "vote.bonus.max_reached": {
        "en": "You've already claimed today's vote bonus! Come back tomorrow for another extra image.",
        "it": "Hai già riscattato il bonus voto di oggi! Torna domani per un'altra immagine extra.",
        "es": "¡Ya has reclamado el bonus de voto de hoy! Vuelve mañana para otra imagen extra.",
        "pt": "Já resgataste o bónus de voto de hoje! Volta amanhã para outra imagem extra.",
        "fr": "Tu as déjà réclamé le bonus de vote d'aujourd'hui ! Reviens demain pour une autre image en plus.",
        "de": "Du hast den heutigen Vote-Bonus bereits eingelöst! Komm morgen für ein weiteres Extra-Bild zurück.",
    },

    # ── Welcome setup premium hint ────────────────────────────────────────────
    "setup.premium.title": {
        "en": "💎 Premium plans available",
        "it": "💎 Piani premium disponibili",
        "es": "💎 Planes premium disponibles",
        "pt": "💎 Planos premium disponíveis",
        "fr": "💎 Plans premium disponibles",
        "de": "💎 Premium-Pläne verfügbar",
    },
    "setup.premium.value": {
        "en": "Unlock more images, music and /genserver uses. **Starter includes a 7-day free trial** — cancel anytime. Use `/premium` to see plans.",
        "it": "Sblocca più immagini, musica e utilizzi di /genserver. **Starter include una prova gratuita di 7 giorni** — cancella quando vuoi. Usa `/premium` per vedere i piani.",
        "es": "Desbloquea más imágenes, música y usos de /genserver. **Starter incluye prueba gratuita de 7 días** — cancela cuando quieras. Usa `/premium` para ver los planes.",
        "pt": "Desbloqueia mais imagens, música e usos de /genserver. **Starter inclui 7 dias de trial gratuito** — cancela quando quiseres. Usa `/premium` para ver os planos.",
        "fr": "Débloque plus d'images, musique et /genserver. **Le Starter inclut 7 jours d'essai gratuit** — annule à tout moment. Utilise `/premium` pour voir les plans.",
        "de": "Schalte mehr Bilder, Musik und /genserver-Nutzungen frei. **Starter mit 7 Tage Gratis-Test** — jederzeit kündbar. Verwende `/premium` um Pläne zu sehen.",
    },

    # ── /premium command description (for slash command metadata) ─────────────
    "cmd.premium.description": {
        "en": "View your current plan and upgrade options (Starter includes a 7-day free trial).",
        "it": "Vedi il tuo piano attuale e le opzioni di upgrade (Starter include una prova gratuita 7 giorni).",
        "es": "Ver tu plan actual y las opciones de mejora (Starter incluye prueba gratuita de 7 días).",
        "pt": "Ver o teu plano atual e as opções de upgrade (Starter inclui trial gratuito de 7 dias).",
        "fr": "Voir ton plan actuel et les options d'upgrade (Starter inclut un essai gratuit de 7 jours).",
        "de": "Zeige deinen aktuellen Plan und Upgrade-Optionen (Starter mit 7 Tage Gratis-Test).",
    },


    # ── Quota remaining display (shown after /draw, /edit, /compose) ─────────
    "quota.remaining.image": {
        "en": "-# \U0001f193 Images remaining today: **{remaining}/{limit}**{vote_hint}",
        "it": "-# \U0001f193 Immagini rimanenti oggi: **{remaining}/{limit}**{vote_hint}",
        "es": "-# \U0001f193 Imágenes restantes hoy: **{remaining}/{limit}**{vote_hint}",
        "pt": "-# \U0001f193 Imagens restantes hoje: **{remaining}/{limit}**{vote_hint}",
        "fr": "-# \U0001f193 Images restantes aujourd'hui : **{remaining}/{limit}**{vote_hint}",
        "de": "-# \U0001f193 Bilder verbleibend heute: **{remaining}/{limit}**{vote_hint}",
    },
    "quota.remaining.image.vote_hint": {
        "en": "  \u2022  Vote with `/vote` for +1 \U0001f5f3\ufe0f",
        "it": "  \u2022  Vota con `/vote` per +1 \U0001f5f3\ufe0f",
        "es": "  \u2022  Vota con `/vote` para +1 \U0001f5f3\ufe0f",
        "pt": "  \u2022  Vota com `/vote` para +1 \U0001f5f3\ufe0f",
        "fr": "  \u2022  Vote avec `/vote` pour +1 \U0001f5f3\ufe0f",
        "de": "  \u2022  Vote mit `/vote` für +1 \U0001f5f3\ufe0f",
    },
    "quota.remaining.compose": {
        "en": "-# \U0001f193 Compositions remaining today: **{remaining}/{limit}**",
        "it": "-# \U0001f193 Composizioni rimanenti oggi: **{remaining}/{limit}**",
        "es": "-# \U0001f193 Composiciones restantes hoy: **{remaining}/{limit}**",
        "pt": "-# \U0001f193 Composições restantes hoje: **{remaining}/{limit}**",
        "fr": "-# \U0001f193 Compositions restantes aujourd'hui : **{remaining}/{limit}**",
        "de": "-# \U0001f193 Kompositionen verbleibend heute: **{remaining}/{limit}**",
    },
    "quota.genserver.exceeded": {
        "en": "\u26a0\ufe0f You've used all **{limit}** /genserver uses for this month (plan: {plan}).",
        "it": "\u26a0\ufe0f Hai esaurito tutti i **{limit}** utilizzi di /genserver per questo mese (piano: {plan}).",
        "es": "\u26a0\ufe0f Has usado todos los **{limit}** usos de /genserver de este mes (plan: {plan}).",
        "pt": "\u26a0\ufe0f Usaste todos os **{limit}** usos de /genserver deste mês (plano: {plan}).",
        "fr": "\u26a0\ufe0f Tu as utilisé les **{limit}** utilisations de /genserver de ce mois (plan : {plan}).",
        "de": "\u26a0\ufe0f Du hast alle **{limit}** /genserver-Nutzungen diesen Monat verbraucht (Plan: {plan}).",
    },
    "quota.chat_pro.exceeded": {
        "en": "\u26a0\ufe0f You've used all {limit} Pro-model /chat messages for this month. Falling back to Flash.\n\n",
        "it": "\u26a0\ufe0f Hai esaurito tutti i {limit} messaggi /chat con modello Pro di questo mese. Uso Flash.\n\n",
        "es": "\u26a0\ufe0f Has usado todos los {limit} mensajes /chat con modelo Pro de este mes. Usando Flash.\n\n",
        "pt": "\u26a0\ufe0f Usaste todos os {limit} mensagens /chat com modelo Pro deste mês. A usar Flash.\n\n",
        "fr": "\u26a0\ufe0f Tu as utilisé les {limit} messages /chat avec le modèle Pro de ce mois. Utilisation de Flash.\n\n",
        "de": "\u26a0\ufe0f Du hast alle {limit} Pro-Modell /chat-Nachrichten diesen Monat verbraucht. Wechsel zu Flash.\n\n",
    },
    "quota.chat_pro.not_available": {
        "en": "\u26a0\ufe0f The Pro model is available only on the **Pro plan** ({price}/month). Your message was processed with the free Flash model.\n\u2192 Use `/premium` to see plans.\n\n",
        "it": "\u26a0\ufe0f Il modello Pro è disponibile solo con il piano **Pro** ({price}/mese). Il tuo messaggio è stato elaborato con il modello Flash gratuito.\n\u2192 Usa `/premium` per vedere i piani.\n\n",
        "es": "\u26a0\ufe0f El modelo Pro solo está disponible en el plan **Pro** ({price}/mes). Tu mensaje fue procesado con el modelo Flash gratuito.\n\u2192 Usa `/premium` para ver los planes.\n\n",
        "pt": "\u26a0\ufe0f O modelo Pro está disponível apenas no plano **Pro** ({price}/mês). A tua mensagem foi processada com o modelo Flash gratuito.\n\u2192 Usa `/premium` para ver os planos.\n\n",
        "fr": "\u26a0\ufe0f Le modèle Pro n'est disponible que sur le plan **Pro** ({price}/mois). Ton message a été traité avec le modèle Flash gratuit.\n\u2192 Utilise `/premium` pour voir les plans.\n\n",
        "de": "\u26a0\ufe0f Das Pro-Modell ist nur im **Pro-Plan** verfügbar ({price}/Monat). Deine Nachricht wurde mit dem kostenlosen Flash-Modell verarbeitet.\n\u2192 Nutze `/premium` für Planoptionen.\n\n",
    },


}


# ══════════════════════════════════════════════════════════════════════════════
# API PUBBLICA
# ══════════════════════════════════════════════════════════════════════════════

def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Ritorna la stringa tradotta per la chiave e la lingua fornite.
    Fallback: lingua richiesta → inglese (DEFAULT_LANG) → chiave stessa.
    Non solleva mai eccezioni.

    Esempi:
        t("error.generic", "en")
        t("cooldown.message", lang, remaining=30, command="/chat")
        t("draw.size_label", lang, size="16:9")
    """
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def get_lang(uid: str, settings: dict | None = None) -> str:
    """
    Ritorna il codice lingua per l'utente.
    Accetta il dict di settings già recuperato dal DB per evitare query extra.

    Uso tipico:
        user_cfg = settings_manager.get_settings(uid)
        lang = get_lang(uid, user_cfg)
    """
    if settings is None:
        return DEFAULT_LANG
    lang = settings.get("language", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
