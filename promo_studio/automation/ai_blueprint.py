"""Gemini AI copywriter for the Daily Cosmic Blueprint.

Generates culturally rich, authentic Vedic captions adhering to the
7-day rotation and Siddhanta's app tone:
- Mon-Fri: Daily Panchang + Abhijit/Rahu Kaal
- Saturday: Shani transit, Sade Sati & karma cleansing
- Sunday: Astro-Numerology & Surya vitality
- Festival Days: High-alert celebration & observance rules
"""
from __future__ import annotations

import json
from promo_studio.ai.gemini import GeminiProvider
from promo_studio.automation.panchang_engine import DailyPanchang

SYSTEM_PROMPT = """You are a reverent, knowledgeable Vedic astrology copywriter for 'Siddhanta', a modern Panchang and Kundli app rooted in authentic tradition.
Rules:
- Honor the sacred Vedic tradition with genuine cultural warmth and clarity.
- Never make superstitious fear-based claims, medical guarantees, or false promises.
- Frame all astrological advice as mindfulness, spiritual reflection, and mindful timing (Muhurta).
- Output must be engaging, readable, structured with tasteful emojis and line breaks.
- Return ONLY valid JSON matching the schema provided.
"""

def generate_cosmic_caption(p: DailyPanchang, gemini: GeminiProvider, api_key: str = "") -> dict:
    """Prompts Gemini to draft the daily caption and hashtags."""
    
    gochar_info = None
    if p.gochar:
        gochar_info = {
            "current_transits": {
                "Jupiter (Guru)": p.gochar.jupiter_sign,
                "Saturn (Shani)": p.gochar.saturn_sign,
                "Rahu": p.gochar.rahu_sign,
                "Ketu": p.gochar.ketu_sign,
            },
            "rashis_with_favorable_transits": p.gochar.favorable_rashis,
            "rashis_advised_mindfulness": p.gochar.caution_rashis,
            "dasha_spotlight": {
                "title": p.gochar.dasha_spotlight_title,
                "explanation": p.gochar.dasha_spotlight_desc
            }
        }

    context = {
        "date": p.date_formatted,
        "vara": f"{p.vara_sa} ({p.vara_en})",
        "deity": p.deity,
        "tithi": p.tithi_name,
        "paksha": p.paksha,
        "masa": p.masa_name,
        "nakshatra": p.nakshatra_name,
        "moon_rashi": p.moon_rashi,
        "sunrise": p.sunrise_str,
        "sunset": p.sunset_str,
        "abhijit_muhurta": p.abhijit_muhurta,
        "rahu_kaal": p.rahu_kaal,
        "theme": p.content_theme,
        "is_festival": p.is_festival,
        "festival_name": p.festival_name,
        "festival_note": p.festival_note,
        "spiritual_significance": p.significance,
        "daily_remedy": p.remedy,
        "planetary_transits_gochar": gochar_info,
        "numerology": p.numerology_focus if p.content_theme == "sunday_numerology" else None,
    }

    user_prompt = f"""
Write today's 'Daily Cosmic Blueprint' social post using the following astronomical & Vedic data:
{json.dumps(context, indent=2, ensure_ascii=False)}

CONTENT ROTATION THEME: {p.content_theme.upper()}

Requirements for Instagram Caption:
1. Language: Culturally rich, respectful Hindi (Devanagari script) with clean English sub-labels for maximum Instagram and WhatsApp story resonance.
2. Hook: 
   - An inspiring devotional opening honoring {p.vara_hi} ({p.vara_en}), {p.masa_name_hi} मास, and active deity ({p.deity_hi} / {p.deity}).
3. Cosmic Blueprint Summary (दैनिक पंचांग सारांश):
   - तिथि: {p.tithi_name_hi} ({p.tithi_name})
   - नक्षत्र: {p.nakshatra_name_hi} ({p.nakshatra_name})
   - ⭐ शुभ अभिजीत मुहूर्त: {p.abhijit_muhurta} (श्रेष्ठ समय शुभ कार्यों हेतु)
   - ⚠️ राहुकाल: {p.rahu_kaal} (इस काल में नए कार्य व समझौते टालें)
4. Planetary Transit Radar (दैनिक ग्रह गोचर रडार):
   - Highlight the current planetary positions: Guru in {p.gochar.jupiter_sign if p.gochar else 'Karka'}, Shani in {p.gochar.saturn_sign if p.gochar else 'Meena'}.
   - Mention favorable rashis: {', '.join(p.gochar.favorable_rashis) if p.gochar else 'Cancer, Scorpio'}.
   - Brief Dasha educational tip in Hindi: {p.gochar.dasha_spotlight_title if p.gochar else 'विंशोत्तरी महादशा'}.
5. Spiritual Remedy (दैनिक वैदिक उपाय एवं सकारात्मक संकल्प):
   - {p.remedy}
6. The App Lead-Magnet Hook (ऐप डाउनलोड कॉल-टू-एक्शन):
   - "📲 क्या आप जानते हैं कि आपकी व्यक्तिगत जन्म कुंडली में वर्तमान में कौन सी महादशा अथवा अंतर्दशा चल रही है? आज का ग्रह गोचर आपके जीवन को कैसे प्रभावित कर रहा है? अपनी सटीक जन्म कुंडली और व्यक्तिगत मार्गदर्शन के लिए आज ही 'Siddhanta' ऐप डाउनलोड करें! (Link in bio)"
7. Hashtags: 15 to 18 high-performing Vedic hashtags in Hindi and English (e.g. ["पंचांग", "Panchang", "VedicAstrology", "Kundli", "SiddhantaApp", "राशिफल", "महादशा", "DailyHoroscope", "ज्योतिष", ...]).

Output JSON format:
{{
  "instagram_caption": "Full Instagram caption text here in Hindi/English with beautiful emojis...",
  "facebook_text": "Full Facebook post text with Play Store link (https://play.google.com/store/apps/details?id=com.tshashwat.panchang)...",
  "hashtags": ["Panchang", "VedicAstrology", "Kundli", "Muhurta", "SiddhantaApp", "Jyotish", "पंचांग", "कुंडली"]
}}
"""

    raw_json = None
    # Try preferred model first
    try:
        raw_json = gemini.generate(SYSTEM_PROMPT, user_prompt, temperature=0.7)
    except Exception:
        # Fallback to ultra-reliable flash alias
        fallback_models = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]
        for fb_model in fallback_models:
            if gemini.model != fb_model and api_key:
                try:
                    fb_provider = GeminiProvider(api_key, fb_model)
                    raw_json = fb_provider.generate(SYSTEM_PROMPT, user_prompt, temperature=0.7)
                    if raw_json:
                        break
                except Exception:
                    continue

    if raw_json:
        try:
            clean = raw_json.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.endswith("```"):
                clean = clean[:-3]
            parsed = json.loads(clean.strip())
            if isinstance(parsed, dict) and "instagram_caption" in parsed:
                return parsed
        except Exception:
            pass

    # Reliable Vedic fallback template if API call fails
    return get_devotional_fallback_copy(p)


def get_devotional_fallback_copy(p: DailyPanchang) -> dict:
    """Returns a culturally rich, devotional fallback caption and hashtags."""
    return {
        "instagram_caption": (
            f"🕉️ Daily Cosmic Blueprint • {p.date_formatted}\n\n"
            f"Today is {p.vara_sa} ({p.vara_en}), dedicated to {p.deity}.\n\n"
            f"✨ Tithi: {p.tithi_name} ({p.masa_name} Masa)\n"
            f"⭐ Nakshatra: {p.nakshatra_name}\n\n"
            f"🌟 Auspicious Abhijit Muhurta: {p.abhijit_muhurta}\n"
            f"⚠️ Rahu Kaal (Caution Window): {p.rahu_kaal}\n\n"
            f"🪔 Daily Spiritual Focus: {p.remedy}\n\n"
            f"📲 Calculate your personalized Kundli and exact city-wise muhurtas on the Siddhanta App (Link in bio)!"
        ),
        "facebook_text": (
            f"🕉️ Daily Cosmic Blueprint • {p.date_formatted}\n\n"
            f"Today is {p.vara_sa} ({p.vara_en}), dedicated to {p.deity}.\n\n"
            f"• Tithi: {p.tithi_name} ({p.masa_name} Masa)\n"
            f"• Nakshatra: {p.nakshatra_name}\n"
            f"• Auspicious Abhijit Muhurta: {p.abhijit_muhurta}\n"
            f"• Rahu Kaal: {p.rahu_kaal}\n\n"
            f"Daily Remedy: {p.remedy}\n\n"
            f"Download the Siddhanta App for offline Vedic Panchang and Kundli:\n"
            f"https://play.google.com/store/apps/details?id=com.tshashwat.panchang"
        ),
        "hashtags": ["Panchang", "VedicAstrology", "Kundli", "Muhurta", "SiddhantaApp", "HinduCalendar", "Tithi", "Nakshatra"]
    }
