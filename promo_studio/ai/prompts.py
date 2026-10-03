from __future__ import annotations

import json

ANGLES = {
    "feature_spotlight": "Spotlight one feature and the concrete benefit it gives the user.",
    "problem_solution": "Name a real user pain point, then show how the app helps.",
    "tip": "Give a genuinely useful tip related to the app's topic; mention the app lightly.",
    "behind_the_scenes": "Share a short, honest development story or decision.",
    "update": "Announce an update or release in plain language, using only the facts in the note.",
    "social_proof": "Use only real user feedback supplied in the note. Never invent quotes.",
}

SYSTEM_PROMPT = """You are a careful app-marketing copywriter for an independent developer.
Rules:
- Use only facts found in the app profile or the note. Never invent features, statistics, awards, reviews or prices.
- No medical, health-outcome or guaranteed-result claims.
- Write naturally and specifically. Avoid filler like "game-changer" and "revolutionary".
- Give each variant a genuinely different hook, not a reword of the same sentence.
- Hashtags: specific and relevant, without the # symbol.
- Return ONLY valid JSON matching the requested shape. No markdown fences, no commentary.

Platform guidance:
- x: under 250 characters before hashtags. One idea, one call to action.
- facebook: 300 to 500 characters, friendly, short paragraphs, include the store link if given.
- instagram: strong first line, caption under 600 characters, link-in-bio style call to action (links are not clickable).
- reddit: honest title under 100 characters, plain body, disclose that you are the developer, no hype, no hashtags.
"""

_SHAPES = {
    "x": '"x": {"text": "...", "hashtags": ["..."]}',
    "facebook": '"facebook": {"text": "...", "hashtags": ["..."]}',
    "instagram": '"instagram": {"caption": "...", "hashtags": ["..."]}',
    "reddit": '"reddit": {"title": "...", "body": "...", "suggested_subreddits": ["..."]}',
}


def build_user_prompt(profile, angle: str, base_text: str, note: str, n: int, platforms) -> str:
    facts = {
        "name": profile.name, "pitch": profile.pitch, "description": profile.description,
        "audience": profile.audience, "key_features": profile.features, "tone": profile.tone,
        "store_links": profile.store_links, "seed_keywords": profile.seed_keywords,
    }
    shape = ", ".join(_SHAPES[p] for p in platforms)
    example = '{"variants": [{"angle": "%s", %s}]}' % (angle, shape)
    parts = [
        "APP PROFILE:", json.dumps(facts, ensure_ascii=False, indent=2),
        f"CONTENT ANGLE: {angle} - {ANGLES.get(angle, angle)}",
    ]
    if base_text.strip():
        parts += ["BASE IDEA FROM THE DEVELOPER (build on it):", base_text.strip()]
    if note.strip():
        parts += ["EXTRA NOTE:", note.strip()]
    parts += [
        f"Write {n} distinct variants. Use this exact JSON shape (repeat the variant object {n} times):",
        example,
    ]
    return "\n\n".join(parts)
