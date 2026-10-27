import os
import subprocess
import numpy as np
import cv2
import json
import uuid
import time
import re
import PIL.Image
import wave
import socket

# Configurar timeout global de socket para evitar bloqueos indefinidos en llamadas de red
socket.setdefaulttimeout(180)

# === OPTIMIZACIÓN DE RECURSOS Y TEMPERATURA (ANTI-FREEZE) ===
try:
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass

try:
    import torch
    # Limitar PyTorch a 4 hilos en vez de los 14 núcleos de la laptop para evitar congelamiento de Windows
    torch.set_num_threads(4)
except Exception:
    pass



_INSULT_PATTERNS = [
    (r"(?i)\bde\s+la\s+concha\s+de\s+(?:la\s+lora|su\s+madre|tu\s+madre|la\s+mona|mi\s+hermana)\b", "tremendo"),
    (r"(?i)\bla\s+concha\s+de\s+(?:la\s+lora|su\s+madre|tu\s+madre|la\s+mona|mi\s+hermana)\b", ""),
    (r"(?i)\bhijo\s+de\s+(?:mil\s+)?(?:puta|perra|su\s+madre)\b", ""),
    (r"(?i)\bla\s+puta\s+madre\b", ""),
    (r"(?i)\bde\s+mierda\b", ""),
    (r"(?i)\bal\s+pedo\b", "de gusto"),
    (r"(?i)\bcag(?:ó|o)\s+a\s+palos\b", "mató a golpes"),
    (r"(?i)\bcagazo\b", "susto"),
    (r"(?i)\bme\s+cagu[eé]\s+todo\b", "me pegué un susto bárbaro"),
    (r"(?i)\bme\s+cago\b", ""),
    (r"(?i)\bwhat\s+the\s+fuck\b", ""),
    (r"(?i)\b(?:boludo|boluda|pelotudo|pelotuda|mierda|carajo|concha|puta|puto|verga|orto|pija|choto|chota|wtf|fuck|joder|coño)\b", ""),
]


def extract_game_title(video_path_or_name: str) -> str:
    if not video_path_or_name:
        return "Gaming"
    norm = str(video_path_or_name).replace("\\", "/").strip("/")
    parts = [p.strip() for p in norm.split("/") if p.strip()]
    ignore_dirs = {"complete games", "exports", "obs grabaciones", "gourmet", "raiz", "raíz", "videos", "clips", "db"}
    raw = ""
    if len(parts) >= 2 and parts[-2].lower() not in ignore_dirs:
        raw = parts[-2]
    else:
        base = os.path.splitext(parts[-1])[0] if parts else "Gaming"
        while base.lower().endswith((".mkv", ".mp4", ".json")):
            base = os.path.splitext(base)[0]
        base = re.sub(r"^\d+(?:\.\d+)?\s*-\s*", "", base)
        base = re.sub(r"[\s_-]*\d{4}-\d{2}-\d{2}[_\s]\d{2}-\d{2}-\d{2}.*$", "", base)
        base = re.sub(r"(?i)[\s_-]+(?:resumen|directo\s*\d*|leito\w*(?:\s+hablado\s*\d*)?|final\s*\w*).*$", "", base)
        base = re.sub(r"[_\s-]+\d+$", "", base)
        raw = base.strip()

    raw = raw.replace("_", " ").replace("-", " ").strip()
    raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    low = raw.lower()
    known_map = {
        "rerequiem": "Resident Evil Requiem",
        "re requiem": "Resident Evil Requiem",
        "resident evil requiem": "Resident Evil Requiem",
        "silent hill town fall": "Silent Hill Townfall",
        "silent hill townfall": "Silent Hill Townfall",
        "the closing shift": "The Closing Shift",
        "sons of the forest": "Sons of the Forest",
        "zelda echoes of wisdom": "Zelda Echoes of Wisdom",
        "zelda echoes of wisdon": "Zelda Echoes of Wisdom",
        "walking dead": "The Walking Dead",
        "rusty lake hotel": "Rusty Lake Hotel",
        "hell mart": "HellMart",
        "hellmart": "HellMart",
        "tenebris somnia": "Tenebris Somnia",
        "bad cheese": "Bad Cheese",
        "bad parenting": "Bad Parenting",
        "fear the timeloop": "Fear the Timeloop",
        "fran bow": "Fran Bow",
        "phonopolis": "Phonopolis",
        "photomaly": "Photomaly",
        "a game about digging a hole": "A Game About Digging a Hole",
    }
    for k, v in known_map.items():
        if k in low:
            return v
    if not raw or re.match(r"^[\d\.\s_-]+$", raw):
        return "Gaming"
    return raw


def clean_insults_and_tone(text: str, is_title: bool = False) -> str:
    if not text:
        return ""
    s = str(text).strip()
    for pat, rep in _INSULT_PATTERNS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\s+([,\.\?!])", r"\1", s)
    s = re.sub(r",(\s*,)+", ",", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;-")
    alpha_chars = [c for c in s if c.isalpha()]
    if len(alpha_chars) > 10 and sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) > 0.75:
        s = s.capitalize()
    if s.startswith("¡") and s.endswith("!") and s.count("!") == 1:
        s = s[1:-1].strip()
        if not is_title and s and not s.endswith("."):
            s += "."
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def sanitize_and_format_metadata(clip: dict, video_path_or_name: str = "") -> dict:
    if not isinstance(clip, dict):
        return clip
    game_title = extract_game_title(video_path_or_name)
    game_hashtag = "#" + re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]", "", game_title.title())
    if game_hashtag == "#":
        game_hashtag = "#Gaming"

    # 1. Títulos limpios, naturales y sin insultos
    st = clean_insults_and_tone(clip.get("social_title", ""), is_title=True)
    yt_t = clean_insults_and_tone(clip.get("yt_title", "") or st, is_title=True)
    if st:
        clip["social_title"] = st
    if yt_t:
        clip["yt_title"] = yt_t

    # 2. Descripción de redes: natural, sin insultos y SIEMPRE con hashtags bien formados
    raw_desc = str(clip.get("social_desc", "") or "").strip()
    existing_hashtags = re.findall(r"#[\wáéíóúÁÉÍÓÚñÑ]+", raw_desc)
    body = re.sub(r"#[\wáéíóúÁÉÍÓÚñÑ]+", "", raw_desc).strip()
    body = re.sub(r"\b[A-Za-z0-9]+_[A-Za-z0-9_]+\s*$", "", body).strip()
    body = clean_insults_and_tone(body, is_title=False)
    if body and body[-1] not in ".?!":
        body += "."

    clean_ht = []
    seen_ht = set()

    def _add_ht(h: str):
        h_clean = "#" + re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]", "", h)
        if len(h_clean) <= 2:
            return
        if clean_insults_and_tone(h_clean[1:], is_title=True).lower() != h_clean[1:].lower():
            return
        if h_clean.lower() not in seen_ht:
            seen_ht.add(h_clean.lower())
            clean_ht.append(h_clean)

    _add_ht(game_hashtag)
    for h in existing_hashtags:
        _add_ht(h)
    cat = str(clip.get("category", "")).lower()
    if cat == "susto":
        _add_ht("#Terror")
    elif cat == "humor":
        _add_ht("#Humor")
    _add_ht("#Gaming")
    _add_ht("#Leito4Gaming")
    hashtags_str = " ".join(clean_ht[:4])

    if body:
        clip["social_desc"] = f"{body} {hashtags_str}".strip()
    elif clip.get("social_title"):
        clip["social_desc"] = f"{clip['social_title']}. {hashtags_str}".strip()
    else:
        clip["social_desc"] = hashtags_str

    if clip.get("yt_desc"):
        clip["yt_desc"] = clean_insults_and_tone(clip.get("yt_desc", ""), is_title=False)
    else:
        clip["yt_desc"] = body or clip.get("social_title", "")

    # 3. Tags de YouTube: SIEMPRE separados por comas, sin '#', sin insultos, e incluyendo Leito4Gaming y el juego
    raw_tags = str(clip.get("yt_tags", "") or "").strip()
    raw_tags = raw_tags.replace("#", "")
    if "," in raw_tags:
        candidates = [t.strip() for t in raw_tags.split(",") if t.strip()]
    else:
        rem = raw_tags
        if game_title.lower() != "gaming":
            rem = re.sub(re.escape(game_title), "", rem, flags=re.IGNORECASE).strip()
        candidates = [w.strip() for w in rem.split() if len(w.strip()) >= 3]

    final_tags = []
    seen_tags = set()

    def _add_tag(t: str):
        t_clean = clean_insults_and_tone(t, is_title=True).strip(" .,;#-_")
        if re.search(r"_\d+$", t_clean):
            return
        if len(t_clean) < 2:
            return
        if t_clean.lower() not in seen_tags:
            seen_tags.add(t_clean.lower())
            final_tags.append(t_clean)

    _add_tag("Leito4Gaming")
    if game_title.lower() != "gaming":
        _add_tag(game_title)
        _add_tag(f"{game_title} gameplay")
        _add_tag(f"{game_title} español")
    _add_tag("Leito4GamingPlus")

    for c_tag in candidates:
        _add_tag(c_tag)

    fallbacks = ["gameplay español", "clips gaming", "streamer argentino"]
    if cat == "susto":
        fallbacks = ["juego de terror", "survival horror", "reaccion"] + fallbacks
    elif cat == "humor":
        fallbacks = ["momentos divertidos", "clips graciosos"] + fallbacks
    for fb in fallbacks:
        if len(final_tags) >= 10:
            break
        _add_tag(fb)

    clip["yt_tags"] = ", ".join(final_tags[:12])
    return clip


def get_feedback_injection(video_basename: str = "", api_key: str = "") -> str:
    """Perfil de gusto aprendido + ejemplos (priorizando el mismo juego)."""
    profile_txt = ""
    if api_key:
        try:
            profile = get_taste_profile(api_key)
            if profile:
                profile_txt = (
                    "\n\n--- PERFIL DE GUSTO DE LEITO (APRENDIDO DE SUS APROBADOS Y RECHAZADOS REALES) ---\n"
                    f"{profile}\n"
                    "Usa este perfil como criterio PRINCIPAL. Ante la duda, RECHAZA: es preferible entregar pocos clips excelentes que muchos mediocres.\n"
                )
        except Exception as e:
            print(f"Aviso perfil de gusto: {e}")
    return profile_txt + _get_feedback_examples(video_basename)


def _game_key(name: str) -> str:
    base = os.path.splitext(os.path.basename(str(name)))[0]
    if base.endswith(".mkv") or base.endswith(".mp4"):
        base = os.path.splitext(base)[0]
    for tok in re.split(r"[_\-\s\.\d]+", base.lower()):
        if len(tok) >= 3:
            return tok
    return ""


def _words_to_text(words_list) -> str:
    if not words_list or not isinstance(words_list, list):
        return ""
    parts = []
    for w in words_list:
        if isinstance(w, dict):
            t = str(w.get("text", w.get("word", ""))).strip()
            if t:
                parts.append(t)
    return " ".join(parts).strip()


def _word_overlap(a: str, b: str) -> float:
    ta = set(w for w in re.findall(r"\w+", str(a).lower()) if len(w) > 3)
    tb = set(w for w in re.findall(r"\w+", str(b).lower()) if len(w) > 3)
    if not ta or not tb:
        return 1.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def load_learning_data():
    """
    Devuelve (aprobados_reales, rechazados_y_descartados, recortes_de_leito):
    - En completed_proposals, si el clip tiene 'words' (subtítulos finales que Leito exportó),
      ESA es la transcripción real del buen clip.
    - Si el 'transcript' original de la IA tiene < 22% de coincidencia con 'words', significa
      que el clip original de la IA era MALO y Leito tuvo que armar otro clip a mano usando ese slot:
      entonces 'words' va a APROBADOS y el 'transcript' original de la IA va a RECHAZADOS.
    - Si tiene entre 22% y 55% de coincidencia, Leito tuvo que recortar relleno o correr el clip:
      guardamos el par (antes_ia -> despues_leito) para enseñarle a la IA cómo cortar bien.
    """
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    approved, rejected, trim_fixes = [], [], []
    seen = set()
    if not os.path.isdir(db_dir):
        return approved, rejected
    for fn in os.listdir(db_dir):
        if not fn.endswith(".json") or fn.endswith("_transcript.json"):
            continue
        if fn in ("feedback_ia.json", "cost_history.json", "vocals_cache.json", "taste_profile.json"):
            continue
        try:
            with open(os.path.join(db_dir, fn), "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        game_name = fn.replace(".json", "")

        for c in d.get("completed_proposals", []):
            if c.get("category") in ("manual", "chat"):
                continue
            ai_tr = str(c.get("original_ai_transcript") or c.get("transcript", "")).strip()
            final_tr = _words_to_text(c.get("words", []))
            real_tr = final_tr if len(final_tr) >= 25 else ai_tr
            if len(real_tr) < 25:
                continue

            # Si Leito editó el clip y hay tanto transcripción original de la IA como palabras finales:
            if len(ai_tr) >= 25 and len(final_tr) >= 25:
                ov = _word_overlap(ai_tr, final_tr)
                if ov < 0.22 and ai_tr not in seen:
                    seen.add(ai_tr)
                    rejected.append({
                        "game": game_name,
                        "category": c.get("category", ""),
                        "reason": f"CLIP MALO REEMPLAZADO A MANO POR LEITO (decía: {str(c.get('reason',''))[:120]})",
                        "transcript": ai_tr,
                        "duration": 0,
                    })
                elif 0.22 <= ov < 0.55:
                    trim_fixes.append({
                        "game": game_name,
                        "ai_bad_cut": ai_tr[:260],
                        "user_good_cut": final_tr[:260],
                    })

            if real_tr not in seen:
                seen.add(real_tr)
                approved.append({
                    "game": game_name,
                    "category": c.get("category", ""),
                    "reason": str(c.get("reason", ""))[:200],
                    "transcript": real_tr,
                    "duration": round(float(c.get("end", 0)) - float(c.get("start", 0)), 1),
                })

        for c in d.get("rejected_proposals", []):
            tr = str(c.get("transcript", "")).strip()
            if len(tr) < 25 or tr in seen or c.get("category") in ("manual", "chat"):
                continue
            seen.add(tr)
            rejected.append({
                "game": game_name,
                "category": c.get("category", ""),
                "reason": str(c.get("reason", ""))[:200],
                "transcript": tr,
                "duration": round(float(c.get("end", 0)) - float(c.get("start", 0)), 1),
            })

    fb_file = os.path.join(db_dir, "feedback_ia.json")
    if os.path.exists(fb_file):
        try:
            with open(fb_file, "r", encoding="utf-8") as f:
                for d in json.load(f):
                    tr = str(d.get("transcript", "")).strip()
                    if len(tr) < 25 or tr in seen:
                        continue
                    seen.add(tr)
                    item = {"game": "", "category": d.get("category", ""), "reason": str(d.get("reason", ""))[:200], "transcript": tr, "duration": 0}
                    (approved if d.get("feedback") == "up" else rejected).append(item)
        except Exception:
            pass
    return approved, rejected


def get_taste_profile(api_key: str, force: bool = False) -> str:
    """
    Genera (y cachea en db/taste_profile.json) un perfil escrito de qué clips aprueba y rechaza Leito,
    usando los subtítulos finales reales ('words') de los clips que Leito armó/aprobó y tratando
    como negativos los clips donde Leito tuvo que descartar la propuesta original y rearmarla a mano.
    """
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    cache_file = os.path.join(db_dir, "taste_profile.json")
    approved, rejected = load_learning_data()
    total = len(approved) + len(rejected)
    cached = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except Exception:
            cached = {}
    if not force and cached.get("profile") and total - int(cached.get("n_decisions", 0)) < 5:
        return cached["profile"]
    if len(approved) < 5 or len(rejected) < 3 or not api_key:
        return cached.get("profile", "")

    import random
    rnd = random.Random(42)
    ap = rnd.sample(approved, min(45, len(approved)))
    rj = rnd.sample(rejected, min(45, len(rejected)))

    def fmt(items):
        return "\n".join(
            f"- [{i.get('game','')[:28]}] ({i.get('category') or 's/cat'}, {i.get('duration')}s) \"{i['transcript'][:360]}\""
            for i in items
        )

    prompt = (
        "Sos un director y editor experto en clips virales de gaming (TikTok/Reels/Shorts). "
        "Abajo tenés los clips REALES que Leito4Gaming (streamer argentino de terror/indies/acción) "
        "terminó editando y exportando a mano (APROBADOS REALES) vs los clips que la IA le había propuesto mal y él "
        "RECHAZÓ o tuvo que TIRAR Y REARMAR A MANO porque eran aburridos, no tenían sentido o estaban mal cortados.\n"
        "Analizá profundamente las diferencias y escribí una GUÍA DE DETECCIÓN Y CORTE de máximo 14 viñetas accionables:\n"
        "1. Qué hace que un momento tenga SENTIDO COMPLETO (cómo empieza el gancho, qué pasa en el clímax y cómo cierra el remate).\n"
        "2. Cómo corta Leito los clips: dónde arranca exactamente (sin relleno previo de caminata/menú) y dónde termina.\n"
        "3. Qué momentos son FALSOS POSITIVOS que la IA suele elegir mal (leer carteles/notas, divagar sin remate, empezar 25s antes del susto, cortar antes de la reacción/pelea).\n"
        "Respondé SOLO con las viñetas concretas.\n\n"
        f"=== CLIPS REALES ARMADOS Y EXPORTADOS POR LEITO ({len(approved)} total) ===\n{fmt(ap)}\n\n"
        f"=== CLIPS MALOS DE LA IA QUE LEITO RECHAZÓ O TUVO QUE REHACER A MANO ({len(rejected)} total) ===\n{fmt(rj)}\n"
    )
    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip(), http_options={'timeout': 120000})
        resp = client.models.generate_content(
            model='gemini-3.5-flash-lite', contents=[prompt], config={"temperature": 0.2}
        )
        profile = (resp.text or "").strip()
        if profile:
            os.makedirs(db_dir, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "profile": profile,
                    "n_decisions": total,
                    "n_approved": len(approved),
                    "n_rejected": len(rejected),
                    "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, indent=2, ensure_ascii=False)
            print(f"Perfil de gusto actualizado ({len(approved)} aprobados reales / {len(rejected)} rechazados+reemplazados).")
            return profile
    except Exception as e:
        print(f"No se pudo generar el perfil de gusto: {e}")
    return cached.get("profile", "")


def rank_and_select_best(candidates, api_key, video_basename, top_n=6, min_score=65):
    """
    TORNEO FINAL + AUDITORÍA DE SENTIDO Y CORTE:
    Evalúa todos los candidatos juntos verificando:
    1) Que el clip tenga SENTIDO PROPIO (Inicio/Gancho -> Clímax -> Remate) y no sea una charla cortada o aburrida.
    2) Que el pico acústico coincida con una reacción real (y no solo leer fuerte).
    3) Permite ajustar 'trimmed_start' y 'trimmed_end' si al candidato le sobran segundos aburridos al inicio/final.
    """
    if not candidates:
        return [], [], 0, 0
    top_n = max(1, int(top_n))
    tin = tout = 0
    evals = {}

    lines = []
    for i, c in enumerate(candidates):
        s_t = round(float(c.get("start", 0)), 1)
        e_t = round(float(c.get("end", 0)), 1)
        dur = round(e_t - s_t, 1)
        lines.append(
            f"#{i} | tiempo={s_t}s-{e_t}s ({dur}s) | cat={c.get('category','?')} | origen={c.get('_source','?')}"
            f" | contraste_voz={c.get('_spike','-')}\n"
            f"   razón propuesta: {str(c.get('reason',''))[:220]}\n"
            f"   transcripción: \"{str(c.get('transcript',''))[:700]}\""
        )

    sys_prompt = (
        "Sos el Editor Jefe de Leito4Gaming. Leito se queja de que muchos clips propuestos por la IA son ABURRIDOS, "
        "NO TIENEN SENTIDO por sí solos, o empiezan con 20 segundos de caminata/lectura antes de que pase algo.\n"
        f"De esta lista solo se entregarán los {top_n} MEJORES. Sé implacable:\n"
        "1. SENTIDO COMPLETO (ESTRUCTURA): Un buen clip DEBE tener Gancho claro (qué está por pasar), Clímax (susto real, pelea caótica, bug bizarro, carcajada o remate gracioso) y Cierre. Si la transcripción es una charla a medias sin remate, lectura de un cartel/documento, menú/inventario, o caminata sin gracia -> poné score < 40.\n"
        "2. DETECCIÓN DE RELLENO: Si el clip es muy bueno pero en la transcripción se nota que los primeros 10-20 segundos son relleno aburrido antes del momento real, podés sugerir 'trim_start_add' (segundos a recortar del inicio, entre 0 y 20).\n"
        "3. ESCALA ESTRICTA: < 50 = malo/aburrido/sin sentido (se descarta); 50-64 = flojo; 65-79 = buen clip; 80-100 = clip excelente que Leito sube directo sin tener que rehacerlo a mano."
    )
    sys_prompt += get_feedback_injection(video_basename, api_key)
    user_prompt = (
        f"JUEGO: {video_basename}\nCANDIDATOS ({len(candidates)}):\n\n" + "\n\n".join(lines) +
        "\n\nDevolvé SOLO una lista JSON con TODOS los candidatos: "
        "[{\"idx\": int, \"score\": int, \"trim_start_add\": float, \"why\": \"máx 14 palabras explicando el gancho y remate o por qué falla\"}]"
    )

    try:
        from google import genai
        import concurrent.futures
        client = genai.Client(api_key=api_key.strip(), http_options={'timeout': 180000})

        def _call():
            return client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=[sys_prompt, user_prompt],
                config={"temperature": 0.1, "response_mime_type": "application/json"},
            )
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            resp = ex.submit(_call).result(timeout=150)
        finally:
            ex.shutdown(wait=False)
        um = getattr(resp, "usage_metadata", None)
        if um:
            tin += getattr(um, "prompt_token_count", 0) or 0
            tout += (getattr(um, "candidates_token_count", 0) or 0) + (getattr(um, "thoughts_token_count", 0) or 0)
        m = re.search(r"\[.*\]", resp.text or "", re.DOTALL)
        if m:
            for r in json.loads(m.group(0)):
                try:
                    evals[int(r["idx"])] = (
                        int(r.get("score", 0)),
                        float(r.get("trim_start_add", 0) or 0),
                        str(r.get("why", ""))[:140],
                    )
                except Exception:
                    pass
    except Exception as e:
        print(f"Torneo final falló, uso virality_score como respaldo: {e}")

    for i, c in enumerate(candidates):
        if i in evals:
            sc, trim_add, why = evals[i]
            c["rank_score"] = sc
            c["rank_why"] = why
            if 3.0 <= trim_add <= 22.0 and (c["end"] - (c["start"] + trim_add)) >= 32.0:
                c["start"] = round(c["start"] + trim_add, 2)
        else:
            c["rank_score"] = int(c.get("virality_score", 0) or 0) - 25
            c["rank_why"] = c.get("rank_why", "Sin puntaje del torneo")

    ordered = sorted(candidates, key=lambda c: c["rank_score"], reverse=True)
    winners, losers = [], []
    for c in ordered:
        overlaps = any(max(c["start"], w["start"]) < min(c["end"], w["end"]) for w in winners)
        if len(winners) < top_n and c["rank_score"] >= min_score and not overlaps:
            winners.append(c)
        else:
            if overlaps:
                c["rank_why"] = "Se solapa con un clip mejor. " + c.get("rank_why", "")
            losers.append(c)
    for pos, w in enumerate(winners, 1):
        w["rank_position"] = pos
    print(f"Torneo: {len(winners)} ganadores de {len(candidates)} candidatos (corte {min_score}).")
    return winners, losers, tin, tout


def _get_feedback_examples(video_basename: str = "") -> str:
    approved, rejected = load_learning_data()
    gk = _game_key(video_basename)

    try:
        import random
        def pick(pool, n):
            same = [x for x in pool if gk and _game_key(x.get("game", "")) == gk]
            other = [x for x in pool if x not in same]
            out = random.sample(same, min(n, len(same))) if same else []
            if len(out) < n and other:
                out += random.sample(other, min(n - len(out), len(other)))
            return out
        positives, negatives = approved, rejected
        pos_sample = pick(positives, 4)
        neg_susto = [
            n for n in negatives
            if str(n.get("category", "")).lower() == "susto"
            or "susto" in str(n.get("reason", "")).lower()
            or "REEMPLAZADO A MANO" in str(n.get("reason", ""))
        ]
        neg_other = [n for n in negatives if n not in neg_susto]
        neg_sample = pick(neg_susto, 3) + pick(neg_other, 2)
        for x in pos_sample + neg_sample:
            x["transcript"] = str(x.get("transcript", ""))[:500]

        if not pos_sample and not neg_sample:
            return ""

        inj = "\n\n--- INYECCIÓN DE APRENDIZAJE (HISTORIAL REAL DE CLIPS EDITADOS VS DESCARTADOS POR LEITO) ---\n"
        if pos_sample:
            inj += "\nEjemplos de CLIPS REALES que Leito armó/aprobó y exportó (notá cómo arrancan directo en la situación y tienen clímax + remate):\n"
            for i, p in enumerate(pos_sample):
                inj += f"[BUENO {i+1}] Razón: \"{p.get('reason', '')}\" | Transcripción final exportada: \"{p.get('transcript')}\"\n"

        if neg_sample:
            inj += "\nEjemplos RECHAZADOS o que Leito tuvo que TIRAR Y REHACER A MANO porque eran aburridos, sin sentido o mal cortados:\n"
            for i, n in enumerate(neg_sample):
                cat_str = f" (Categoría: {n.get('category')})" if n.get("category") else ""
                inj += f"[MALO {i+1}]{cat_str} {n.get('reason', '')} | Texto malo descartado: \"{n.get('transcript')}\"\n"

        inj += "-------------------------------------------------------------------\n"
        return inj
    except Exception as e:
        print(f"Error building feedback injection: {e}")
        return ""


def _extract_voice_or_mix_wav(video_path: str, temp_wav_voice: str, temp_wav_mix: str) -> str:
    """
    Intenta extraer primero el Track 2 de OBS (0:a:1 = micrófono puro del streamer)
    para detectar reacciones/gritos reales sin ruido de disparos o música del juego.
    Si el video no tiene Track 2 o está vacío, usa la pista general (0:a:0).
    """
    if os.path.exists(temp_wav_voice) and os.path.getsize(temp_wav_voice) > 1000:
        try:
            with wave.open(temp_wav_voice, "rb") as wf:
                sample_bytes = wf.readframes(min(wf.getnframes(), 16000 * 120))
                arr = np.frombuffer(sample_bytes, dtype=np.int16).astype(np.float64)
                if len(arr) > 0 and np.max(np.abs(arr)) > 200:
                    print("Audio de voz (Track 2) en caché válido.")
                    return temp_wav_voice
        except Exception:
            pass

    try:
        res = subprocess.run([
            "ffmpeg", "-i", video_path,
            "-map", "0:a:1",
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-y", temp_wav_voice
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(temp_wav_voice) and os.path.getsize(temp_wav_voice) > 1000:
            with wave.open(temp_wav_voice, "rb") as wf:
                sample_bytes = wf.readframes(min(wf.getnframes(), 16000 * 120))
                arr = np.frombuffer(sample_bytes, dtype=np.int16).astype(np.float64)
                if len(arr) > 0 and np.max(np.abs(arr)) > 200:
                    print("Audio de micrófono aislado (Track 2 / 0:a:1) extraído con éxito.")
                    return temp_wav_voice
    except Exception:
        pass

    if os.path.exists(temp_wav_mix) and os.path.getsize(temp_wav_mix) > 1000:
        print("Audio general ya extraído, utilizando caché...")
        return temp_wav_mix

    print("Extrayendo audio general (Track 1) para análisis RMS...")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        "-y", temp_wav_mix
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return temp_wav_mix


ANTI_FALSE_SUSTO_RULES = (
    "\n\nREGLAS ESTRICTAS ANTIFALSOS POSITIVOS (ESPECIALMENTE EN CATEGORÍA 'susto'):\n"
    "1. PROHIBIDO INVENTAR O EXAGERAR SUSTOS: Que el streamer hable fuerte, eleve el tono de voz, lea con énfasis, diga '¡uh!', '¡ah, mirá!', '¡ah, no, ya entendí!', festeje resolver algo o putee por un menú NO ES UN SUSTO.\n"
    "2. CUÁNDO USAR 'category': 'susto': ÚNICAMENTE cuando haya un JUMPSCARE REAL, un grito brusco de pánico/terror genuino, la aparición repentina de un enemigo/monstruo que asuste de verdad al streamer, o una persecución desesperada con pánico real.\n"
    "3. SITUACIONES QUE DEBES RECHAZAR SIEMPRE (NO SON CLIPS NI SUSTOS):\n"
    "   - Leer cartas, notas, archivos médicos o documentos del juego en voz alta (aunque el texto sea macabro o el streamer diga '¡uh!').\n"
    "   - Resolver cajas fuertes, combinaciones, acertijos o puzzles diciendo números en voz alta sin que ocurra un ataque o susto real.\n"
    "   - Ordenar el inventario, combinar objetos, guardar partida o quejarse de que no hay espacio en el inventario.\n"
    "   - Configurar el stream, OBS, sonidos o alertas (ej. decir 'no deberíamos tener ningún susto con las alertas').\n"
    "4. PROHIBIDO MENTIR EN 'reason', 'social_title' O 'yt_title': Jamás escribas 'Me pegué un susto...' si en el audio/transcripción el streamer solo estaba abriendo una caja fuerte, leyendo una nota o hablando fuerte. Si el momento no tiene un susto real ni es genuinamente gracioso/épico, RECHÁZALO.\n"
)


def analyze_video_local_first(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise Exception("La librería google-genai no está instalada.")

    client = genai.Client(api_key=api_key.strip(), http_options={'timeout': 180000})

    video_basename = extract_game_title(video_path)

    if progress_callback:
        progress_callback(10, "Extrayendo pista de voz para análisis...")

    safe_name = "".join(c for c in os.path.basename(video_path) if c.isalnum() or c in " _-")
    temp_wav_voice = os.path.join(temp_dir, f"{safe_name}_voice_temp.wav")
    temp_wav_mix = os.path.join(temp_dir, f"{safe_name}_audio_temp.wav")
    active_wav = _extract_voice_or_mix_wav(video_path, temp_wav_voice, temp_wav_mix)

    if progress_callback:
        progress_callback(20, "Calculando mapa de picos y contraste acústico (RMS + Crest)...")
    print("Analizando picos de volumen y contraste brusco de voz...")
    with wave.open(active_wav, "rb") as wf:
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        audio_data = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float64)

    chunk_samples = framerate if framerate > 0 else 16000
    rms_values = []
    peak_values = []
    for i in range(0, len(audio_data), chunk_samples):
        chunk = audio_data[i:i+chunk_samples]
        if len(chunk) == 0:
            rms_values.append(0.0)
            peak_values.append(0.0)
            continue
        rms = float(np.sqrt(np.mean(chunk**2)))
        pk = float(np.max(np.abs(chunk)))
        rms_values.append(rms)
        peak_values.append(pk)

    rms_array = np.array(rms_values, dtype=np.float64)
    peak_array = np.array(peak_values, dtype=np.float64)

    # Calcular línea base local (mediana móvil de 30s) ANTES de anular zonas excluidas
    active_nonzero = rms_array[rms_array > 50]
    global_median = float(np.median(active_nonzero)) if len(active_nonzero) > 0 else 100.0
    baseline_floor = max(80.0, global_median * 0.6)

    spike_ratio_array = np.zeros_like(rms_array)
    n_secs = len(rms_array)
    for s_i in range(n_secs):
        w_start = max(0, s_i - 15)
        w_end = min(n_secs, s_i + 16)
        window_vals = rms_array[w_start:w_end]
        active_win = window_vals[window_vals > 40]
        local_med = float(np.median(active_win)) if len(active_win) > 0 else global_median
        denom = max(local_med, baseline_floor)
        spike_ratio_array[s_i] = rms_array[s_i] / denom

    # === IGNORAR ZONAS YA PROCESADAS ===
    if exclusion_zones:
        if progress_callback:
            progress_callback(25, "Filtrando fragmentos ya procesados...")
        for ex_start, ex_end in exclusion_zones:
            s_idx = max(0, int(ex_start) - 15)
            e_idx = min(len(rms_array), int(ex_end) + 15)
            rms_array[s_idx:e_idx] = 0.0
            spike_ratio_array[s_idx:e_idx] = 0.0

    nonzero_rms = rms_array[rms_array > 0]
    if len(nonzero_rms) > 0:
        threshold_90 = float(np.percentile(nonzero_rms, 90))
        threshold_95 = float(np.percentile(nonzero_rms, 95))
    else:
        threshold_90 = 999999.0
        threshold_95 = 999999.0

    # Detectar segundos fuertes: ya sea por volumen alto (p90) con contraste, o por pico súbito agudo (grito corto)
    loud_seconds = np.where(
        (rms_array > threshold_90) | ((rms_array > threshold_90 * 0.85) & (spike_ratio_array >= 2.5))
    )[0]

    segments = []
    current_segment = []
    for s in loud_seconds:
        if not current_segment:
            current_segment = [int(s)]
        else:
            if int(s) - current_segment[-1] <= 5:
                current_segment.append(int(s))
            else:
                segments.append((current_segment[0], current_segment[-1]))
                current_segment = [int(s)]
    if current_segment:
        segments.append((current_segment[0], current_segment[-1]))

    candidate_segments = []
    for raw_start, raw_end in segments:
        s_raw = int(raw_start)
        e_raw = int(raw_end) + 1
        length = e_raw - s_raw

        seg_rms = rms_array[s_raw:e_raw]
        seg_spikes = spike_ratio_array[s_raw:e_raw]
        seg_peaks = peak_array[s_raw:e_raw]
        if len(seg_rms) == 0:
            continue

        max_rms_val = float(np.max(seg_rms))
        max_spike_val = float(np.max(seg_spikes))
        peak_rel_idx = int(np.argmax(seg_rms * np.maximum(seg_spikes, 1.0)))
        peak_sec = s_raw + peak_rel_idx

        # Filtrar falsos positivos de lectura en voz alta monótona vs gritos/reacciones reales:
        # 1) Grito o susto corto (1 a 4 segs): requiere pico intenso (>= p95 o salto brusco >= 2.3x sobre la base local)
        if length < 4:
            if max_rms_val < threshold_95 and max_spike_val < 2.3:
                continue
        else:
            # 2) Habla fuerte sostenida (>= 4 segs): descartar si es volumen plano/monótono sin picos expresivos
            if max_spike_val < 1.75 and max_rms_val < threshold_95:
                continue

        pad_before = 18  # 18s previos (setup directo sin 40s de caminata aburrida)
        pad_after = 42   # 42s posteriores (captura toda la reacción, pelea y remate completo)

        clip_start = max(0, s_raw - pad_before)
        clip_end = min(n_secs, e_raw + pad_after)

        if clip_end - clip_start > 120:
            clip_end = clip_start + 120

        # Puntaje combinado que premia contrastes bruscos (gritos/risas explosivas) por encima de hablar fuerte constante
        reaction_score = max_rms_val * min(max(max_spike_val, 1.0), 4.5)
        candidate_segments.append({
            "start": clip_start,
            "end": clip_end,
            "peak_sec": peak_sec,
            "max_spike": round(max_spike_val, 2),
            "raw_len": length,
            "score": reaction_score
        })

    print(f"Se detectaron {len(candidate_segments)} picos acústicos con contraste de reacción.")

    valid_segments_filtered = []
    for seg_info in candidate_segments:
        start, end = seg_info["start"], seg_info["end"]
        is_excluded = False
        if exclusion_zones:
            for ez_start, ez_end in exclusion_zones:
                if max(start, ez_start) < min(end, ez_end):
                    is_excluded = True
                    break
        if not is_excluded:
            valid_segments_filtered.append(seg_info)

    print(f"Tras aplicar filtros de tiempo quedan {len(valid_segments_filtered)} picos.")

    if len(valid_segments_filtered) > 0:
        valid_segments_filtered.sort(key=lambda seg: seg["score"], reverse=True)
        limit = max_clips if max_clips > 0 else 18
        deduped_segments = []
        for seg in valid_segments_filtered:
            s, e = seg["start"], seg["end"]
            if any(max(s, ds["start"]) < min(e, ds["end"]) - 15 for ds in deduped_segments):
                continue
            deduped_segments.append(seg)
            if len(deduped_segments) >= limit:
                break
        deduped_segments.sort(key=lambda x: x["start"])
        valid_segments_filtered = deduped_segments

    valid_segments = valid_segments_filtered
    print(f"Tras aplicar zonas de exclusión y deduplicación, quedan {len(valid_segments)} segmentos únicos a evaluar.")

    if len(valid_segments) == 0:
        return [], 0, 0

    total_input_tokens = 0
    total_output_tokens = 0

    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""
    sys_prompt = (
        f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. "
        f"Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). "
        f"CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. "
        f"NUNCA uses la palabra o conjugaciones de 'tú' (ej: nunca digas 'Te ha pasado', debes decir 'Te pasó', 'Mirá', 'Fijate'). "
        f"Habla siempre tratando de VOS. Habla con tu tono natural y cotidiano de todos los días. PROHIBIDO usar insultos o malas palabras en títulos, descripciones o tags (nunca escribas 'boludo', 'la puta madre', 'concha', 'mierda', 'carajo', 'cagazo', 'wtf'). PROHIBIDO escribir frases tontas, infantiles o con signos de exclamación falsos ('¡Un bicho me quiso matar!'). "
        f"NUNCA asumas que no jugaste el juego ('Me contaron'). Escribe como un gamer con actitud, en PRIMERA PERSONA. "
        f"Recibes el audio del segmento y una imagen collage (3x2) con 6 fotogramas clave concentrados alrededor del pico de voz. "
        f"Evalúa con criterio estricto si el segmento realmente vale la pena como clip viral según el prompt.\n"
        f"CÓMO RECHAZAR SEGMENTOS SIN VALOR (MUY IMPORTANTE): Como respondes en formato JSON, si el segmento es silencio, charla rutinaria, "
        f"lectura de documentos/notas, resolución tranquila de puzzles/cajas fuertes, ordenar inventario, configurar alertas, o simplemente hablar fuerte "
        f"SIN un susto real, chiste gracioso o jugada épica, DEBES RECHAZARLO devolviendo exactamente este JSON:\n"
        f"{{\"rejected\": true, \"reason\": \"Explicación breve de por qué se rechaza\"}}\n"
        f"Si y solo si el clip tiene verdadero valor viral (virality_score >= 78), devuelve JSON con: "
        f"'rejected' (false), 'start' (float, inicio relativo al video original), 'end' (float, fin relativo al video original), "
        f"'category' (string: 'susto' SOLO si hay miedo/grito/jumpscare real, 'streamer' si es charla/anécdota/explicación/lore interesante, "
        f"'humor' si es chiste/broma/fail gracioso, 'gameplay' si es jugada/combate/boss/muerte épica), "
        f"'reason' (string honesto describiendo qué pasa realmente), 'virality_score' (int 78-99), 'transcript' (string), "
        f"'social_title' (string, Título ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip), "
        f"'social_desc' (string, descripción normal y conversacional (1 o 2 oraciones cortas, 10 a 22 palabras), SIN insultos y sin sonar exagerado, contando como hablarías vos qué pasó en el clip. {link_instruction} Luego pon solo 3 hashtags populares del juego), "
        f"'yt_title' (string, llamativo para YT Shorts), 'yt_desc' (string, descripción CORTA), "
        f"'yt_tags' (string, separadas por coma, incluye 'Leito4Gaming' y 'Leito4GamingPlus' y tags del juego real). "
        f"IMPORTANTE: Clip entre 35 y 75 segundos. DEBES RETROCEDER LO SUFICIENTE para incluir TODO el contexto previo necesario (la preparación del chiste o susto). No cortes las oraciones a la mitad. "
        f"FUNDAMENTAL: Los títulos y descripciones DEBEN referirse ESTRICTAMENTE a lo que se dice o pasa en el clip. Usa frases de tu propio diálogo en la descripción para que no suene genérico."
    )
    sys_prompt += ANTI_FALSE_SUSTO_RULES
    sys_prompt += get_feedback_injection(video_basename, api_key)

    final_clips = []
    cap = cv2.VideoCapture(video_path)

    for idx, seg_info in enumerate(valid_segments):
        start = seg_info["start"]
        end = seg_info["end"]
        peak_sec = seg_info["peak_sec"]
        max_spike = seg_info["max_spike"]
        raw_len = seg_info["raw_len"]

        base_percent = 30 + int(60 * (idx / len(valid_segments)))
        if progress_callback:
            progress_callback(base_percent, f"Extrayendo audio y collage {idx+1}/{len(valid_segments)}...")
        print(f"--> Extrayendo audio ligero y collage 3x2 del segmento: {start}s - {end}s (Pico en {peak_sec}s, contraste {max_spike}x)")
        temp_audio_clip = os.path.join(temp_dir, f"temp_audio_{idx}.mp3")

        duration = end - start
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
            "-i", video_path, "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "libmp3lame", "-b:a", "32k",
            temp_audio_clip
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Crear 1 sola imagen Collage 3x2 (768x288) concentrada alrededor del segundo exacto del pico (peak_sec)
        collage_img = None
        try:
            tile_w, tile_h = 256, 144
            grid_canvas = np.zeros((tile_h * 2, tile_w * 3, 3), dtype=np.uint8)
            offsets = [-8, -3, -1, 0, 2, 6]
            sample_times = [min(max(start + 1, peak_sec + off), max(start + 2, end - 1)) for off in offsets]
            for f_i, t_sec in enumerate(sample_times):
                cap.set(cv2.CAP_PROP_POS_MSEC, float(t_sec) * 1000.0)
                ret, frame = cap.read()
                if ret and frame is not None:
                    resized = cv2.resize(frame, (tile_w, tile_h))
                    label = f"{int(t_sec)}s (PICO)" if off_idx_is_peak(f_i) else f"{int(t_sec)}s"
                    cv2.putText(resized, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                    r_idx = f_i // 3
                    c_idx = f_i % 3
                    grid_canvas[r_idx*tile_h:(r_idx+1)*tile_h, c_idx*tile_w:(c_idx+1)*tile_w] = resized
            collage_img = PIL.Image.fromarray(cv2.cvtColor(grid_canvas, cv2.COLOR_BGR2RGB))
        except Exception as e_img:
            print(f"Aviso generando collage del clip {idx}: {e_img}")
            collage_img = None

        if progress_callback:
            progress_callback(base_percent + 3, f"Preparando mini-audio {idx+1} para Gemini...")
        with open(temp_audio_clip, "rb") as f_aud:
            audio_part = types.Part.from_bytes(data=f_aud.read(), mime_type="audio/mp3")

        if progress_callback:
            progress_callback(base_percent + 4, f"Evaluando clip {idx+1}/{len(valid_segments)} con Gemini Flash-Lite...")
        print(f"Evaluando clip {idx} con Gemini 3.5 Flash-Lite...")

        rel_peak = max(0, peak_sec - start)
        # Construir mini-mapa de energía de voz cada 3 segundos para que Gemini ubique exactamente el inicio y fin de la reacción
        energy_timeline = []
        for t_s in range(int(start), int(end), 3):
            if t_s < len(spike_ratio_array):
                sp_v = float(spike_ratio_array[t_s])
                tag = "🔥PICO" if sp_v >= 2.2 else ("⚡ALTO" if sp_v >= 1.4 else "·calma")
                energy_timeline.append(f"{t_s}s:{tag}({sp_v:.1f}x)")
        energy_map_str = ", ".join(energy_timeline[:24])
        spike_note = (
            f"MAPA DE ENERGÍA DE VOZ (segundos reales del video): [{energy_map_str}]\n"
            f"El pico principal ocurre en el segundo {peak_sec} del video (segundo {rel_peak} de este audio, contraste {max_spike}x).\n"
            f"REGLA DE ENCUADRE (START y END):\n"
            f"- NO pongas 'start' 30 segundos antes mientras camina en silencio o lotea. Poné 'start' entre 5 y 14 segundos ANTES del pico ({max(start, peak_sec - 12)}s a {max(start, peak_sec - 5)}s), justo cuando empieza la frase o situación que desencadena el momento.\n"
            f"- Poné 'end' cuando TERMINE la reacción, pelea o remate cómico (no lo cortes en medio del grito o combate; duración total ideal 35 a 55s).\n"
            f"- SENTIDO COMPLETO: Si al escuchar el audio ves que no pasa nada interesante, es una conversación sin remate, lee un cartel/nota, o no se entiende qué pasa, devuelve {{\"rejected\": true, \"reason\": \"...\"}}."
        )
        prompt_text = (
            f"OFFSET ORIGINAL: Este clip empieza en el segundo {start} del video original y termina en {end}. "
            f"Si lo apruebas, tienes que devolver tu 'start' y 'end' entre {start} y {end}.\n"
            f"{spike_note}\n\nPROMPT DEL USUARIO: {prompt}"
        )

        response = None
        for attempt in range(4):
            try:
                import concurrent.futures

                def call_api1():
                    contents_payload = [audio_part]
                    if collage_img is not None:
                        contents_payload.append(collage_img)
                    contents_payload.extend([sys_prompt, prompt_text])
                    return client.models.generate_content(
                        model='gemini-3.5-flash-lite',
                        contents=contents_payload,
                        config={
                            "temperature": 0.25,
                            "safety_settings": [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                            ],
                            "response_mime_type": "application/json",
                        }
                    )

                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(call_api1)
                    response = future.result(timeout=120)
                except concurrent.futures.TimeoutError:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise Exception("Gemini API timeout: La IA no respondió en 2 minutos.")
                except Exception:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                else:
                    executor.shutdown(wait=False)
                break
            except Exception as e:
                err_str = str(e)
                if "spending cap" in err_str.lower() or "ai.studio/spend" in err_str.lower():
                    cap.release()
                    raise Exception("TOPE DE GASTO MENSUAL ALCANZADO: Tu proyecto en Google AI Studio superó el límite de gasto mensual ('Monthly Spend Cap'). Entra a https://ai.studio/spend para subir tu tope mensual o usa otra API Key en Ajustes.")
                if "402" in err_str or "prepayment credits are depleted" in err_str or "prepay" in err_str:
                    cap.release()
                    raise Exception("CRÉDITOS DE PREPAGO AGOTADOS (Error 402): Tu saldo prepago en Google AI Studio se ha terminado. Por favor recarga saldo en https://ai.studio/projects o ingresa una nueva API Key en Ajustes.")
                if "limit: 0" in err_str:
                    cap.release()
                    raise Exception("QUOTA_AGOTADA: Has superado el límite gratuito diario o Google aún no procesa tu prepago. Debes esperar.")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if progress_callback:
                        progress_callback(base_percent + 4, "Límite API alcanzado. Pausando 30s...")
                    print(f"Límite de API alcanzado (429). Esperando 30 segundos... (Intento {attempt+1})")
                    time.sleep(30)
                elif "timeout" in err_str.lower():
                    print(f"Timeout evaluando clip {idx} (intento {attempt+1}/4). Esperando 6s...")
                    time.sleep(6)
                else:
                    print(f"Error evaluando clip {idx}: {e}")
                    break

        if response is None:
            print(f"Omitiendo clip {idx} debido a errores continuos de API.")
        else:
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    total_input_tokens += (getattr(response.usage_metadata, 'prompt_token_count', 0) or 0)
                    total_output_tokens += (getattr(response.usage_metadata, 'candidates_token_count', 0) or 0) + (getattr(response.usage_metadata, 'thoughts_token_count', 0) or 0)

                txt = response.text
                if txt and "RECHAZADO" not in txt.upper():
                    match = re.search(r'\{.*\}', txt, re.DOTALL)
                    if match:
                        c = json.loads(match.group(0))
                        if isinstance(c, list):
                            c = c[0] if len(c) > 0 else {"rejected": True}
                        if (
                            c.get("rejected") is True
                            or str(c.get("category", "")).lower() in ("rechazado", "rejected", "none", "null")
                            or str(c.get("reason", "")).strip().upper().startswith("RECHAZADO")
                        ):
                            print(f"Clip {idx} RECHAZADO por la IA: {c.get('reason', 'Sin valor viral')}")
                        elif int(c.get("virality_score", 0) or 0) < 75:
                            print(f"Clip {idx} descartado por virality_score bajo ({c.get('virality_score')}): {c.get('reason')}")
                        else:
                            c.pop("rejected", None)
                            if c.get('start', 0) < start:
                                c['start'] += start
                                c['end'] += start

                            # Garantizar longitud mínima de 35s
                            c_start = c.get('start', 0)
                            c_end = c.get('end', 0)
                            if (c_end - c_start) < 35:
                                diff = 35 - (c_end - c_start)
                                c['start'] = max(0, c_start - (diff / 2))
                                c['end'] = c_end + (diff / 2)

                            c["id"] = "ai_" + str(uuid.uuid4())[:4]
                            c["_source"] = "volumen"
                            c["_spike"] = max_spike
                            sanitize_and_format_metadata(c, video_path)
                            final_clips.append(c)
                            if incremental_save_cb:
                                incremental_save_cb(c)
                            print(f"¡Clip Aprobado! [{c.get('category')}] {c.get('reason')} - Duración final: {c['end'] - c['start']}s")
                    else:
                        print(f"Rechazado o formato inválido: {txt}")
                else:
                    print("Clip RECHAZADO por la IA.")
            except Exception as e:
                print(f"Error procesando la respuesta del clip {idx}: {e}")

        try:
            if os.path.exists(temp_audio_clip):
                os.remove(temp_audio_clip)
        except Exception:
            pass
        time.sleep(0.3)  # Pausa ligera para disipar calor
        import gc
        gc.collect()

    cap.release()
    return final_clips, total_input_tokens, total_output_tokens


def off_idx_is_peak(idx: int) -> bool:
    return idx == 3


def analyze_video_semantic(video_path, prompt, api_key, temp_dir, progress_callback=None, exclusion_zones=None, incremental_save_cb=None, max_clips=15, keywords=''):
    try:
        from google import genai
        import whisper
    except ImportError as e:
        raise Exception(f"Falta una librería requerida: {e}")

    client = genai.Client(api_key=api_key.strip(), http_options={'timeout': 180000})
    video_basename = extract_game_title(video_path)

    # Directorio de caché para transcripciones
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    os.makedirs(db_dir, exist_ok=True)
    raw_vbase = os.path.basename(video_path)
    transcript_file = os.path.join(db_dir, f"{raw_vbase}_transcript.json")

    safe_name = "".join(c for c in raw_vbase if c.isalnum() or c in " _-")
    temp_wav_voice = os.path.join(temp_dir, f"{safe_name}_voice_temp.wav")
    temp_wav_full = os.path.join(temp_dir, f"{raw_vbase}_full.wav")

    if os.path.exists(transcript_file):
        if progress_callback:
            progress_callback(20, "Cargando transcripción previa de la caché...")
        print("Cargando transcripción cacheada...")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_segments = json.load(f)
    else:
        if progress_callback:
            progress_callback(10, "Extrayendo audio de voz para transcripción...")
        active_wav = _extract_voice_or_mix_wav(video_path, temp_wav_voice, temp_wav_full)
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "small" if device == "cuda" else "base"
        if progress_callback:
            progress_callback(30, f"Transcribiendo audio con Whisper en {device.upper()} ({model_name})...")
        print(f"Cargando modelo Whisper en {device} ({model_name})...")
        model = whisper.load_model(model_name, device=device)
        print(f"Transcribiendo audio en {device}...")
        result = model.transcribe(active_wav, word_timestamps=False, verbose=False)
        transcript_segments = result["segments"]
        if device == "cuda":
            del model
            torch.cuda.empty_cache()

        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_segments, f, indent=4, ensure_ascii=False)

    # Calcular mapa rápido de energía vocal para fusionar Audio + Texto en la transcripción
    sem_spike_array = None
    sem_rms_p92 = 999999.0
    try:
        wav_for_energy = temp_wav_voice if os.path.exists(temp_wav_voice) and os.path.getsize(temp_wav_voice) > 1000 else (
            temp_wav_full if os.path.exists(temp_wav_full) and os.path.getsize(temp_wav_full) > 1000 else _extract_voice_or_mix_wav(video_path, temp_wav_voice, temp_wav_full)
        )
        with wave.open(wav_for_energy, "rb") as wf:
            fr = wf.getframerate() or 16000
            aud = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float64)
        rms_list = [float(np.sqrt(np.mean(aud[i:i+fr]**2))) if len(aud[i:i+fr]) > 0 else 0.0 for i in range(0, len(aud), fr)]
        sem_rms = np.array(rms_list, dtype=np.float64)
        nz = sem_rms[sem_rms > 50]
        g_med = float(np.median(nz)) if len(nz) > 0 else 100.0
        sem_rms_p92 = float(np.percentile(nz, 92)) if len(nz) > 0 else 999999.0
        b_floor = max(80.0, g_med * 0.6)
        sem_spike_array = np.zeros_like(sem_rms)
        for s_i in range(len(sem_rms)):
            win = sem_rms[max(0, s_i - 15):min(len(sem_rms), s_i + 16)]
            awin = win[win > 40]
            l_med = float(np.median(awin)) if len(awin) > 0 else g_med
            sem_spike_array[s_i] = sem_rms[s_i] / max(l_med, b_floor)
    except Exception as e_en:
        print(f"Aviso calculando energía vocal para modo semántico: {e_en}")

    if progress_callback:
        progress_callback(70, "Analizando transcripción + energía vocal con Gemini Flash-Lite...")

    CHUNK_DUR = 1200  # 20 minutos por bloque de texto
    chunks = []
    current_chunk_text = ""
    current_chunk_start = 0.0
    current_chunk_end = 0.0

    for seg in transcript_segments:
        start = seg['start']
        end = seg['end']
        is_excluded = False
        if exclusion_zones:
            for ez_start, ez_end in exclusion_zones:
                if max(start, ez_start) < min(end, ez_end):
                    is_excluded = True
                    break
        if not is_excluded:
            if not current_chunk_text:
                current_chunk_start = start
            if start - current_chunk_start > CHUNK_DUR:
                chunks.append({"start": current_chunk_start, "end": current_chunk_end, "text": current_chunk_text})
                current_chunk_text = ""
                current_chunk_start = start
            energy_tag = ""
            if sem_spike_array is not None and int(start) < len(sem_spike_array):
                s_slice = sem_spike_array[max(0, int(start)):min(len(sem_spike_array), int(end) + 1)]
                r_slice = sem_rms[max(0, int(start)):min(len(sem_rms), int(end) + 1)]
                if len(s_slice) > 0:
                    mx_sp = float(np.max(s_slice))
                    mx_rm = float(np.max(r_slice))
                    if mx_sp >= 2.4 or mx_rm >= sem_rms_p92:
                        energy_tag = f" [🔥GRITO/REACCIÓN {mx_sp:.1f}x]"
                    elif mx_sp >= 1.65:
                        energy_tag = f" [⚡VOZ ALTA {mx_sp:.1f}x]"
                    elif mx_sp < 1.15:
                        energy_tag = " [voz plana]"
            current_chunk_text += f"[{seg['start']:.1f} - {seg['end']:.1f}]{energy_tag} {seg['text']}\n"
            current_chunk_end = end

    if current_chunk_text.strip():
        chunks.append({"start": current_chunk_start, "end": current_chunk_end, "text": current_chunk_text})

    if not chunks:
        print("Todo el texto está excluido por clips anteriores. No hay nada nuevo que analizar.")
        return [], 0, 0

    link_instruction = "que SIEMPRE termine con 'Podes ver el video completo haciendo click en el link' seguida de los " if "gourmet" in video_path.lower() else ""

    total_input_tokens = 0
    total_output_tokens = 0
    final_clips = []

    if max_clips == 0:
        clips_instruction = "Encuentra SOLO los clips que realmente sean MUY DIVERTIDOS, INTERESANTES o TENGAN SUSTOS REALES en este bloque (entre 0 y 5 por bloque; si el bloque es rutinario devuelve [])"
    else:
        clips_per_chunk = max(2, int(max_clips / len(chunks)) + 1)
        clips_instruction = f"Encuentra hasta {clips_per_chunk} clips que realmente valgan la pena (si hay menos o ninguno bueno en este bloque, devuelve menos o [])"

    feedback_block = get_feedback_injection(video_basename, api_key)
    for chunk_idx, chunk_data in enumerate(chunks):
        chunk_start = chunk_data["start"]
        chunk_end = chunk_data["end"]
        chunk_text = chunk_data["text"]

        pct_base = 70 + int(25 * (chunk_idx / len(chunks)))
        if progress_callback:
            progress_callback(pct_base, f"Analizando bloque {chunk_idx+1}/{len(chunks)} con Gemini Flash-Lite...")

        sys_prompt = (
            f"Eres Leito4Gaming, un streamer y creador de videos virales de gaming de Argentina. "
            f"Estás creando metadatos para tus propios clips, de juegos que TÚ MISMO jugaste (NOMBRE DEL JUEGO: {video_basename}). "
            f"CRÍTICO: Escribe SIEMPRE en Español Argentino auténtico (rioplatense). NO uses español neutro. "
            f"NUNCA uses la palabra o conjugaciones de 'tú'. Habla siempre tratando de VOS. "
            f"Habla con tu tono natural y cotidiano de todos los días. PROHIBIDO usar insultos o malas palabras en títulos, descripciones o tags (nunca escribas 'boludo', 'la puta madre', 'concha', 'mierda', 'carajo', 'cagazo', 'wtf'). PROHIBIDO escribir frases tontas, infantiles o con signos de exclamación falsos ('¡Un bicho me quiso matar!'). "
            f"NUNCA asumas que no jugaste el juego. Escribe como un gamer con actitud, en PRIMERA PERSONA. "
            f"Recibes la transcripción de una sección de {CHUNK_DUR/60:.0f} minutos enriquecida con ETIQUETAS DE ENERGÍA VOCAL ([🔥GRITO/REACCIÓN], [⚡VOZ ALTA], [voz plana]). Úsalas para distinguir dónde hubo una reacción real vs dónde habla en tono plano/aburrido. REGLA DE ORO DE ESTRUCTURA Y CORTE: Cada clip DEBE tener sentido completo por sí solo (1. Gancho/Situación clara -> 2. Clímax/Reacción -> 3. Remate/Cierre). NO empieces el clip 20 segundos antes mientras lee un cartel o camina en silencio: pon el 'start' justo en la frase donde arranca la situación (5 a 10s antes del clímax) y el 'end' cuando termina el remate. "
            f"PRIORIZA LAS REACCIONES REALES, CHISTES, ANÉCDOTAS INTERESANTES, SUSTOS VERDADEROS Y MUERTES ÉPICAS. "
            f"{clips_instruction} basándote en el prompt. "
            f"IMPORTANTE: Clips entre 35 y 75 segundos. Asegúrate de abarcar TODO el contexto (el inicio de la anécdota o preparación del susto/chiste) para que tenga sentido. "
            f"Devuelve ÚNICAMENTE una lista JSON válida (puede ser [] si todo el bloque es lectura de notas, inventario o exploración tranquila). "
            f"Formato: [{{\"start\": float, \"end\": float, \"category\": \"susto\"|\"streamer\"|\"humor\"|\"gameplay\", \"reason\": \"string corto y honesto\", \"virality_score\": int (78-99), \"transcript\": \"string\", \"social_title\": \"Título ingenioso y directo que resuma EXACTAMENTE lo que pasa o se dice en el clip\", \"social_desc\": \"Descripción normal y conversacional (1 o 2 oraciones cortas, 10 a 22 palabras), SIN insultos y sin sonar exagerado, contando como hablarías vos qué pasó en el clip. {link_instruction} Luego pon solo 3 hashtags populares del juego\", \"yt_title\": \"Título super llamativo para YouTube Shorts\", \"yt_desc\": \"Descripción CORTA en PRIMERA PERSONA\", \"yt_tags\": \"8 a 12 etiquetas separadas por COMA, SIN hashtag, incluyendo SIEMPRE Leito4Gaming y el nombre del videojuego\"}}]. "
            f"Respeta estrictamente JSON. FUNDAMENTAL: EL BLOQUE COMIENZA EN EL SEGUNDO {chunk_start}. Los tiempos 'start' y 'end' que devuelvas en el JSON deben ser RELATIVOS AL VIDEO ORIGINAL, es decir, usa exactamente las marcas de tiempo que aparecen en la transcripción."
        )
        sys_prompt += ANTI_FALSE_SUSTO_RULES
        sys_prompt += feedback_block

        prompt_text = f"PROMPT DEL USUARIO: {prompt}\n\nAquí tienes la transcripción del bloque {chunk_idx+1} (Comienza en {chunk_start:.1f}s y termina en {chunk_end:.1f}s):\n\n{chunk_text}"

        try:
            response = None
            for attempt in range(4):
                try:
                    import concurrent.futures

                    def call_api_target():
                        return client.models.generate_content(
                            model='gemini-3.5-flash-lite',
                            contents=[sys_prompt, prompt_text],
                            config={
                                "temperature": 0.25,
                                "safety_settings": [
                                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                                ],
                                "response_mime_type": "application/json",
                            }
                        )

                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    try:
                        future = executor.submit(call_api_target)
                        response = future.result(timeout=90)
                    except concurrent.futures.TimeoutError:
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise Exception("Gemini API timeout: La IA tardó demasiado en responder este bloque.")
                    except Exception:
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise
                    else:
                        executor.shutdown(wait=False)
                    break
                except Exception as e:
                    err_str = str(e)
                    if "spending cap" in err_str.lower() or "ai.studio/spend" in err_str.lower():
                        raise Exception("TOPE DE GASTO MENSUAL ALCANZADO: Tu proyecto en Google AI Studio superó el límite de gasto mensual ('Monthly Spend Cap'). Entra a https://ai.studio/spend para subir tu tope mensual o usa otra API Key en Ajustes.")
                    if "402" in err_str or "prepayment credits are depleted" in err_str or "prepay" in err_str:
                        raise Exception("CRÉDITOS DE PREPAGO AGOTADOS (Error 402): Tu saldo prepago en Google AI Studio se ha terminado. Por favor recarga saldo en https://ai.studio/projects o ingresa una nueva API Key en Ajustes.")
                    if "limit: 0" in err_str:
                        raise Exception("QUOTA_AGOTADA: Has superado el limite gratuito diario o Google aun no procesa tu prepago. Debes esperar.")
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        if progress_callback:
                            progress_callback(pct_base, "Límite API alcanzado. Pausando 30s...")
                        print(f"Límite de API alcanzado (429). Esperando 30 segundos... (Intento {attempt+1})")
                        time.sleep(30)
                    elif "timeout" in err_str.lower():
                        print(f"Timeout en bloque {chunk_idx+1} (intento {attempt+1}/4). Reintentando...")
                        time.sleep(5)
                    else:
                        print(f"Error en bloque {chunk_idx+1} (intento {attempt+1}/4): {e}")
                        time.sleep(3)

            if response is None:
                print(f"No se pudo procesar el bloque {chunk_idx+1} tras reintentos. Continuando con el siguiente...")
                continue

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                total_input_tokens += (getattr(response.usage_metadata, 'prompt_token_count', 0) or 0)
                total_output_tokens += (getattr(response.usage_metadata, 'candidates_token_count', 0) or 0) + (getattr(response.usage_metadata, 'thoughts_token_count', 0) or 0)

            txt = response.text
            match = re.search(r'\[.*\]', txt, re.DOTALL)
            if match:
                clips_list = json.loads(match.group(0))
                for c in clips_list:
                    if not isinstance(c, dict):
                        continue
                    if (
                        c.get("rejected") is True
                        or str(c.get("category", "")).lower() in ("rechazado", "rejected", "none", "null")
                        or int(c.get("virality_score", 0) or 0) < 75
                    ):
                        continue
                    c.pop("rejected", None)
                    start = c.get('start', 0)
                    end = c.get('end', 0)
                    if (end - start) < 35:
                        diff = 35 - (end - start)
                        c['start'] = max(0, start - (diff / 2))
                        c['end'] = end + (diff / 2)
                        start = c['start']
                        end = c['end']

                    is_excluded = False
                    if exclusion_zones:
                        for ez_start, ez_end in exclusion_zones:
                            if ez_start <= start <= ez_end or ez_start <= end <= ez_end or start <= ez_start <= end:
                                is_excluded = True
                                break
                    if not is_excluded:
                        c["id"] = "ai_" + str(uuid.uuid4())[:4]
                        c["_source"] = "historia"
                        sanitize_and_format_metadata(c, video_path)
                        final_clips.append(c)
                        if incremental_save_cb:
                            incremental_save_cb(c)
                print(f"Bloque {chunk_idx+1}/{len(chunks)} terminado con éxito. Clips totales detectados: {len(final_clips)}")
            else:
                print(f"Gemini no devolvió JSON en bloque {chunk_idx+1}: {txt[:200]}")
        except Exception as e:
            print(f"Error procesando bloque {chunk_idx+1}: {e}")
            if "CRÉDITOS DE PREPAGO AGOTADOS" in str(e) or "QUOTA_AGOTADA" in str(e) or "TOPE DE GASTO MENSUAL ALCANZADO" in str(e):
                raise e
        finally:
            time.sleep(0.5)  # Pausa ligera
            import gc
            gc.collect()

    if not final_clips:
        print("Modo semántico: ningún bloque tuvo clips que valgan la pena.")

    if progress_callback:
        progress_callback(100, "¡Proceso semántico terminado!")
    return final_clips, total_input_tokens, total_output_tokens
