"""Gemini AI Copywriter & Composer for Siddhanta.

Acts strictly as Composer & Writer:
- Crafts concise, culturally rich, authentic Vedic captions tailored to the
  *single selected post type* (Panchang, Plan Day, Festival, Kundli, Chakra, or Transit)
- Generates 8-12 high-intent, targeted hashtags
- Does NOT act as designer or invent astrological claims
"""
from __future__ import annotations

import json
from promo_studio.ai.gemini import GeminiProvider
from promo_studio.automation.panchang_engine import DailyPanchang

SYSTEM_PROMPT = """You are a reverent, knowledgeable Vedic astrology copywriter for 'Siddhanta', a modern Panchang and Kundli app rooted in authentic tradition.
Rules:
- Act strictly as a Composer and Writer: write an engaging, concise Instagram caption tailored specifically to the post type requested.
- Honor the sacred Vedic tradition with genuine cultural warmth and clarity.
- Never make superstitious fear-based claims, medical guarantees, or false promises.
- Frame astrological advice as mindfulness, spiritual reflection, and mindful timing (Muhurta).
- Keep the caption focused (under 220 words) with clean Devanagari Hindi and English sub-labels.
- Include 8-12 high-intent hashtags in Hindi and English.
- Return ONLY valid JSON matching the schema provided.
"""

def generate_cosmic_caption(
    p: DailyPanchang,
    gemini: GeminiProvider,
    api_key: str = "",
    post_type: str = "panchang"
) -> dict:
    """Prompts Gemini to draft the daily caption and hashtags tailored to post_type."""
    
    context = {
        "post_type": post_type,
        "date": p.date_formatted,
        "vara": f"{p.vara_sa} ({p.vara_en})",
        "deity": p.deity,
        "tithi": f"{p.tithi_name} ({p.tithi_name_hi})",
        "paksha": p.paksha,
        "nakshatra": f"{p.nakshatra_name} ({p.nakshatra_name_hi})",
        "moon_rashi": p.moon_rashi,
        "sunrise": p.sunrise_str,
        "sunset": p.sunset_str,
        "abhijit_muhurta": p.abhijit_muhurta,
        "rahu_kaal": p.rahu_kaal,
        "is_festival": p.is_festival,
        "festival_name": p.festival_name,
        "festival_note": p.festival_note,
        "daily_remedy": p.remedy,
    }

    user_prompt = f"""
Write an Instagram feed post caption for the following post type: '{post_type.upper()}'.
Astrological & Vedic context:
{json.dumps(context, indent=2, ensure_ascii=False)}

Content Focus based on post_type:
- If 'festival': Celebrate {p.festival_name or 'the sacred festival'}, explain the spiritual significance ({p.festival_note}), puja muhurta, and fasting rules.
- If 'plan_day': Highlight mindful timing today: Abhijit Muhurta ({p.abhijit_muhurta}), Rahu Kaal ({p.rahu_kaal}), and Choghadiya principles.
- If 'kundli': Focus on how the birth chart (D1/D9), planetary positions, and active Vimshottari Dasha illuminate one's life purpose.
- If 'chakra': Discuss the seven energy centers, Jyotish balance, and inner alignment through pranayama and meditation.
- If 'jyotish': Highlight current planetary movements and transit wisdom for intellectual expansion and mindfulness.
- If 'panchang': Provide a clean, devotional overview of today's Tithi, Nakshatra, and Sun/Moon vitality.

Include:
1. Inspiring Devotional Opening
2. Key Vedic insights (2-3 bullet points)
3. Gentle call-to-action inviting users to explore in the Siddhanta app
4. 8-12 relevant hashtags (mix of Hindi & English)

Output JSON schema:
{{
  "instagram_caption": "Caption text with tasteful formatting and emojis...",
  "hashtags": ["Panchang", "SiddhantaApp", "VedicAstrology"]
}}
"""

    raw_json = None
    try:
        raw_json = gemini.generate(SYSTEM_PROMPT, user_prompt, temperature=0.7)
    except Exception:
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

    return get_devotional_fallback_copy(p, post_type=post_type)


def get_devotional_fallback_copy(p: DailyPanchang, post_type: str = "panchang") -> dict:
    """Returns a focused fallback caption tailored to post_type."""
    if post_type == "festival" or (p.is_festival and p.festival_name):
        fest_name = p.festival_name or "Jivitputrika Vrat"
        clean_name = fest_name.split("(")[0].strip().replace(" ", "")
        caption = (
            f"🕉️ {fest_name} • {p.date_formatted}\n\n"
            f"हार्दिक शुभकामनाएं एवं पावन बधाई।\n\n"
            f"✨ तिथि: {p.tithi_name_hi} ({p.tithi_name})\n"
            f"⭐ नक्षत्र: {p.nakshatra_name_hi} ({p.nakshatra_name})\n"
            f"🌟 शुभ मुहूर्त: {p.abhijit_muhurta}\n\n"
            f"📜 {p.festival_note or 'पावन पर्व की पूजा एवं संकल्प विधि का पालन करें।'}\n\n"
            f"विस्तृत मुहूर्त और व्रत कथा के लिए Siddhanta ऐप देखें। (Link in bio)"
        )
        tags = [clean_name, "VedicFestival", "HinduFestival", "Panchang", "SiddhantaApp", "Vrat", "Muhurta", "सनातन_धर्म"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "plan_day":
        caption = (
            f"⏳ Plan Your Day Wisely • {p.date_formatted}\n\n"
            f"महत्वपूर्ण कार्यों के लिए आज के वैदिक समय:\n\n"
            f"🌟 अभिजीत मुहूर्त: {p.abhijit_muhurta} (शुभ कार्यों की शुरुआत हेतु श्रेष्ठ)\n"
            f"⚠️ राहुकाल: {p.rahu_kaal} (नए कार्य एवं महत्वपूर्ण निर्णय टालें)\n"
            f"☀️ चौघड़िया: शुभ वेलाओं का सदुपयोग करें\n\n"
            f"दैनिक चौघड़िया और संपूर्ण मुहूर्त चक्र के लिए Siddhanta ऐप डाउनलोड करें। (Link in bio)"
        )
        tags = ["Muhurta", "AbhijitMuhurta", "RahuKaal", "Choghadiya", "SiddhantaApp", "VedicAstrology", "मुहूर्त", "पंचांग"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "kundli":
        caption = (
            f"📜 Your Kundli & Karmic Map • {p.date_formatted}\n\n"
            f"जन्म कुंडली केवल भविष्य की भविष्यवाणी नहीं, बल्कि आपकी चेतना और कर्म का दर्पण है।\n\n"
            f"🔹 D1 लग्न चक्र: आपकी शारीरिक संरचना और जीवन दिशा\n"
            f"🔹 D9 नवांश: आत्मिक सामर्थ्य और भाग्य की गहराई\n"
            f"🔹 विंशोत्तरी महादशा: जीवन के विभिन्न सोपान और समयावधि\n\n"
            f"अपनी सटीक वैदिक जन्म कुंडली और दशा विश्लेषण के लिए Siddhanta ऐप का अनुभव करें। (Link in bio)"
        )
        tags = ["Kundli", "VedicAstrology", "BirthChart", "Lagna", "Dashas", "SiddhantaApp", "कुंडली", "ज्योतिष"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "chakra":
        caption = (
            f"🌿 Balance Your Inner Energy • {p.date_formatted}\n\n"
            f"सात चक्र हमारे सूक्ष्म शरीर के ऊर्जा केंद्र हैं। जब चक्र संतुलित होते हैं, तो विचार, प्राण और स्वास्थ्य में सहज सामंजस्य स्थापित होता है।\n\n"
            f"✨ मूलाधार से सहस्रार तक — ध्यान और प्राणायाम द्वारा अपनी आंतरिक ऊर्जा को जागृत करें।\n\n"
            f"ज्योतिष और चक्र सामंजस्य की जानकारी के लिए Siddhanta ऐप देखें। (Link in bio)"
        )
        tags = ["ChakraBalance", "SevenChakras", "Meditation", "Pranayama", "InnerPeace", "SiddhantaApp", "Kundalini", "VedicWisdom"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "jyotish":
        caption = (
            f"🪐 Jyotish Transit Insight • {p.date_formatted}\n\n"
            f"ग्रह गोचर हमें समय के स्वभाव और ब्रह्मांडीय लय को समझने में सहायता करता है।\n\n"
            f"✨ बृहस्पति (गुरु) का मिथुन राशि में संचरण ज्ञान, संवाद और बौद्धिक विस्तार का सुंदर अवसर लाता है।\n"
            f"🌟 अध्ययन, शोध और सकारात्मक चिंतन हेतु यह समय विशेष रूप से फलदायी है।\n\n"
            f"अपने लग्न के अनुसार सटीक गोचर प्रभाव जानने के लिए Siddhanta ऐप देखें। (Link in bio)"
        )
        tags = ["TransitAstrology", "JupiterTransit", "GuruGochar", "VedicAstrology", "SiddhantaApp", "Jyotish", "ग्रहगोचर"]
        return {"instagram_caption": caption, "hashtags": tags}

    else:  # default panchang
        caption = (
            f"🕉️ Today's Panchang • {p.date_formatted}\n\n"
            f"आज {p.vara_hi} ({p.vara_en}) है, {p.deity_hi} की आराधना का दिन।\n\n"
            f"✨ तिथि: {p.tithi_name_hi} ({p.tithi_name})\n"
            f"⭐ नक्षत्र: {p.nakshatra_name_hi} ({p.nakshatra_name})\n"
            f"🌟 अभिजीत मुहूर्त: {p.abhijit_muhurta}\n"
            f"⚠️ राहुकाल: {p.rahu_kaal}\n\n"
            f"☀️ सूर्योदय: {p.sunrise_str} | सूर्यास्त: {p.sunset_str}\n"
            f"🙏 दैनिक संकल्प: {p.remedy}\n\n"
            f"सटीक दैनिक पंचांग और मुहूर्त के लिए Siddhanta ऐप का उपयोग करें। (Link in bio)"
        )
        tags = ["Panchang", "DailyPanchang", "VedicAstrology", "Tithi", "Nakshatra", "SiddhantaApp", "पंचांग", "शुभमुहूर्त"]
        return {"instagram_caption": caption, "hashtags": tags}
