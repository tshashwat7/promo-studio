"""Gemini AI Copywriter & Composer for Siddhanta.

Acts strictly as Composer & Writer:
- Crafts concise, culturally rich, authentic Vedic captions tailored to the
  *single selected post type* (Panchang, Plan Day, Festival, Kundli, Chakra, or Transit)
- Ingests authoritative Shastric and astronomical principles from Siddhanta core documentation
- Generates 8-12 high-intent, targeted hashtags
- Embeds upfront Google Play Store download links and link-in-bio CTAs
- Does NOT act as designer or invent astrological claims
"""
from __future__ import annotations

import json
from promo_studio.ai.gemini import GeminiProvider
from promo_studio.automation.panchang_engine import DailyPanchang

PLAY_STORE_URL = "https://bit.ly/47HN61M"

SYSTEM_PROMPT = f"""You are a reverent, knowledgeable Vedic astrology copywriter for 'Siddhanta', a premier astronomical Panchang and Kundli app rooted in authentic tradition.

AUTHENTIC SIDDHANTA SHASTRA & ASTRONOMICAL PRINCIPLES (Core Knowledge Base):
1. Astronomical Foundation:
   - True sidereal calculations with Lahiri (Chitra Paksha) Ayanamsha.
   - Calculations use topocentric true sunrise based on exact coordinates (Ujjain astronomical baseline 23.1765° N, 75.7885° E).
   - High-precision planetary theory without approximations.
2. The Five Limbs of Panchang (Pancha-Anga):
   - Tithi (Lunar Phase): 12° angular distance between Sun and Moon. 30 Tithis across Shukla (waxing) & Krishna (waning) pakshas.
   - Vara (Solar Day): Ruled by classical planetary devatas (Sun: Surya, Moon: Chandra, Mars: Mangala, Mercury: Budha, Jupiter: Brihaspati, Venus: Shukra, Saturn: Shani).
   - Nakshatra (Lunar Mansion): 27 stellar segments of 13°20' mapping the Moon's daily celestial transit.
   - Yoga (Luni-Solar Harmony): 27 mathematical yogas formed by adding Sun and Moon longitudes (e.g. Ayushman, Saubhagya, Parigha, Shubha, Shiva).
   - Karana (Half Tithi): 11 karanas (7 movable chara: Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti/Bhadra; 4 fixed sthira: Shakuni, Chatushpada, Naga, Kintughna).
3. Sacred Kaal & Muhurta Windows:
   - Abhijit Muhurta: The auspicious 8th daytime muhurta (~48 mins around midday), ideal for victorious beginnings (except Wednesdays).
   - Brahma Muhurta: 96 to 48 minutes prior to sunrise; supreme window for meditation, dhyana & spiritual awakening.
   - Godhuli Muhurta: Auspicious twilight sandhya for peace, lighting lamps, and prayer.
   - Rahu Kaal: 1/8th daytime division ruled by Rahu; reserved for contemplative devotion and avoiding new material contracts.
   - Nishita Kaal: Midnight 2-ghati window sacred for Lord Shiva (Shivratri) and Krishna Janmashtami.
   - Pradosha Kaal: Sunset sandhya window dedicated to Lord Shiva worship.
4. Fasting & Vrat Shastra:
   - Ekadashi: Sacred Vishnu fast observed with Arunodaya purity; broken during Dwadashi Parana window after sunrise and Harivasara.
5. Kundli & Subtle Energy:
   - D1 Lagna: Outer life path, vitality, and physical foundation.
   - D9 Navamsha: Dharmic destiny, inner soul strength, and subtle fruits of karma.
   - Vimshottari Dasha: 120-year planetary progression timing life chapters.
   - 7 Chakras: Energy centers balancing prana with cosmic frequencies (Muladhara to Sahasrara).

Rules:
- Act strictly as a Composer and Writer: write an engaging, structured bilingual Instagram caption (Hindi Devanagari section followed by English section).
- Honor the sacred Vedic tradition with genuine cultural warmth, precision, and clarity.
- Never make superstitious fear-based claims, medical guarantees, or false promises.
- Frame astrological advice as mindfulness, spiritual reflection, and mindful timing (Muhurta).
- Keep the caption well-structured (around 180-240 words total), clean formatting with emojis.
- Include 10-15 high-intent hashtags in Hindi and English.
- Always include the upfront Google Play Store download link:
  {PLAY_STORE_URL}
  and mention '(Direct link also in bio @siddhanta.app)'.
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
        "day_of_week_en": p.vara_en,
        "day_of_week_hi": p.vara_hi,
        "vara_sanskrit": p.vara_sa,
        "deity": p.deity,
        "deity_hi": p.deity_hi,
        "samvat": p.samvat_info or "Vikram Samvat 2083",
        "tithi": f"{p.tithi_name} ({p.tithi_name_hi})",
        "tithi_end": p.tithi_end if p.tithi_end else "Through the day",
        "paksha": p.paksha,
        "masa": f"{p.masa_name} ({p.masa_name_hi})",
        "nakshatra": f"{p.nakshatra_name} ({p.nakshatra_name_hi})",
        "nakshatra_end": p.nakshatra_end if p.nakshatra_end else "Through the day",
        "yoga": f"{p.yoga_name} ({p.yoga_name_hi})" if p.yoga_name else "Parigha (परिघ)",
        "karana": f"{p.karana_name} ({p.karana_name_hi})" if p.karana_name else "Taitila (तैतिल)",
        "moon_rashi": f"{p.moon_rashi} ({p.moon_rashi_hi})",
        "sun_rashi": f"{p.sun_rashi} ({p.sun_rashi_hi})",
        "sunrise": p.sunrise_str,
        "sunset": p.sunset_str,
        "abhijit_muhurta": p.abhijit_muhurta,
        "brahma_muhurta": p.brahma_muhurta if p.brahma_muhurta else "4:43 AM – 5:31 AM",
        "godhuli_muhurta": p.godhuli_muhurta if p.godhuli_muhurta else "5:48 PM – 6:36 PM",
        "rahu_kaal": p.rahu_kaal,
        "choghadiya": f"{p.choghadiya_name} ({p.choghadiya_time})",
        "is_festival": p.is_festival,
        "festival_name": p.festival_name,
        "festival_note": p.festival_note,
        "daily_remedy": p.remedy,
        "app_download_link": PLAY_STORE_URL,
    }

    user_prompt = f"""
Write a structured BILINGUAL (Hindi + English) Instagram carousel caption for: '{post_type.upper()}'.
Astrological & Vedic context (authentic Siddhanta computation):
{json.dumps(context, indent=2, ensure_ascii=False)}

CRITICAL LANGUAGE RULE:
- In the English section, ALWAYS use the standard English day name '{p.vara_en}' (e.g. 'Sunday', 'Monday', 'Tuesday'). Do NOT use Sanskrit transliterations like 'Ravivara' or 'Somavara' in the English text.
- In the Hindi section, ALWAYS use the authentic Hindi day name '{p.vara_hi}' (e.g. 'रविवार', 'सोमवार').

Format structure:
1. Hindi Section (Devanagari):
   - Devotional hook with emoji (e.g. 🌸 दैनिक पंचांग • {p.date_formatted_hi})
   - Today's Pancha-Anga (Tithi, Nakshatra, Yoga, Karana) and spiritual significance in pure, culturally rich Hindi
   - Auspicious muhurtas (Abhijit, Brahma Muhurta) and Rahu Kaal
2. English Section:
   - Cosmic insights & mindful timing guidance in clean English (using '{p.vara_en}')
   - Practical alignment guidance based on the day's Nakshatra ruler and deity
3. Call-to-Action (Include the upfront link):
   📲 Download Siddhanta on Google Play:
   {PLAY_STORE_URL}
   (Direct link also available in bio @siddhanta.app)
4. 10-15 relevant hashtags (mix of Hindi & English)

Output JSON schema:
{{
  "instagram_caption": "Bilingual caption text formatted with line breaks...",
  "hashtags": ["Panchang", "SiddhantaApp", "VedicAstrology", "पंचांग"]
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
    """Returns a structured bilingual fallback caption tailored to post_type."""
    cta_block = (
        f"📲 Download Siddhanta on Google Play:\n"
        f"{PLAY_STORE_URL}\n"
        f"(Direct link also in bio @siddhanta.app)"
    )

    if post_type == "festival" or (p.is_festival and p.festival_name):
        fest_name = p.festival_name or "Sacred Festival"
        clean_name = fest_name.split("(")[0].strip().replace(" ", "")
        caption = (
            f"🕉️ {fest_name} • {p.date_formatted_hi}\n\n"
            f"हार्दिक शुभकामनाएं एवं पावन बधाई।\n"
            f"✨ तिथि: {p.tithi_name_hi} ({p.tithi_name})\n"
            f"⭐ नक्षत्र: {p.nakshatra_name_hi} ({p.nakshatra_name})\n"
            f"🌟 शुभ मुहूर्त: {p.abhijit_muhurta}\n"
            f"📜 {p.festival_note or 'पावन पर्व की पूजा एवं संकल्प विधि का पालन करें।'}\n\n"
            f"✨ Sacred Observance Guidance:\n"
            f"Celebrate {fest_name} with devotion, mental clarity, and sacred timing. Align your day with Vedic rituals and mindful intention.\n\n"
            f"{cta_block}"
        )
        tags = [clean_name, "VedicFestival", "HinduFestival", "Panchang", "SiddhantaApp", "Vrat", "Muhurta", "सनातन_धर्म"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "plan_day":
        caption = (
            f"⏳ Plan Your Day Wisely • {p.date_formatted_hi}\n\n"
            f"महत्वपूर्ण कार्यों के लिए आज के वैदिक समय:\n"
            f"🌟 अभिजीत मुहूर्त: {p.abhijit_muhurta} (श्रेष्ठ समय)\n"
            f"🌅 ब्रह्म मुहूर्त: {p.brahma_muhurta or 'सूर्योदय से पूर्व'}\n"
            f"⚠️ राहुकाल: {p.rahu_kaal} (महत्वपूर्ण निर्णय टालें)\n"
            f"☀️ चौघड़िया: {p.choghadiya_name} ({p.choghadiya_time})\n\n"
            f"✨ Cosmic Timing Insights:\n"
            f"Schedule pivotal beginnings during Abhijit Muhurta and practice mindful reflection during Rahu Kaal. Let authentic celestial rhythms optimize your day on {p.vara_en}.\n\n"
            f"{cta_block}"
        )
        tags = ["Muhurta", "AbhijitMuhurta", "RahuKaal", "Choghadiya", "SiddhantaApp", "VedicAstrology", "मुहूर्त", "पंचांग"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "kundli":
        caption = (
            f"📜 Your Kundli & Karmic Map • {p.date_formatted_hi}\n\n"
            f"जन्म कुंडली आपकी चेतना और कर्म पथ का दिव्य मानचित्र है।\n"
            f"🔹 D1 लग्न चक्र: शारीरिक संरचना, स्वास्थ्य और जीवन दिशा\n"
            f"🔹 D9 नवांश: आत्मिक सामर्थ्य, धर्म और आंतरिक सामंजस्य\n"
            f"🔹 विंशोत्तरी दशा: 120-वर्षीय कर्म चक्र और समय चक्र\n\n"
            f"✨ Understanding Your Vedic Chart:\n"
            f"Your astrological blueprint reveals planetary strengths and favorable periods for spiritual, career, and personal growth.\n\n"
            f"{cta_block}"
        )
        tags = ["Kundli", "VedicAstrology", "BirthChart", "Lagna", "Dashas", "SiddhantaApp", "कुंडली", "ज्योतिष"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "chakra":
        caption = (
            f"🌿 Balance Your Inner Energy • {p.date_formatted_hi}\n\n"
            f"सात चक्र हमारे सूक्ष्म शरीर के प्राण केंद्र हैं। जब चक्र संतुलित होते हैं, तो विचार, स्वास्थ्य और संकल्प में सहज समन्वय स्थापित होता है।\n"
            f"✨ मूलाधार से सहस्रार तक — ध्यान, प्राणायाम और ग्रहों की ऊर्जा से आंतरिक सामंजस्य प्राप्त करें।\n\n"
            f"✨ Aligning The 7 Energy Centers:\n"
            f"Restore vital prana through conscious meditation and mindful awareness aligned with sidereal planetary harmonies.\n\n"
            f"{cta_block}"
        )
        tags = ["ChakraBalance", "SevenChakras", "Meditation", "Pranayama", "InnerPeace", "SiddhantaApp", "Kundalini", "VedicWisdom"]
        return {"instagram_caption": caption, "hashtags": tags}

    elif post_type == "jyotish":
        caption = (
            f"🪐 Today's Sky & Planetary Transits • {p.date_formatted_hi}\n\n"
            f"ग्रह गोचर हमें ब्रह्मांडीय लय और समय के स्वभाव से जोड़ता है।\n"
            f"✨ प्रमुख ग्रहों की स्थिति और चंद्रमा का संचरण विचार और ऊर्जा को प्रभावित करता है।\n"
            f"🌟 अध्ययन, शोध और सकारात्मक कर्म हेतु यह समय विशेष फलदायी है।\n\n"
            f"✨ Planetary Transit Wisdom:\n"
            f"Observe how planetary motions influence daily energies. Align your intentions with sidereal transits for greater clarity and focus on {p.vara_en}.\n\n"
            f"{cta_block}"
        )
        tags = ["TransitAstrology", "Gochar", "VedicAstrology", "SiddhantaApp", "Jyotish", "ग्रहगोचर", "पंचांग"]
        return {"instagram_caption": caption, "hashtags": tags}

    else:  # default panchang
        yoga_str = f"🧘 योग: {p.yoga_name_hi} ({p.yoga_name})\n" if p.yoga_name else ""
        karana_str = f"⚡ करण: {p.karana_name_hi} ({p.karana_name})\n" if p.karana_name else ""
        brahma_str = f"🌅 ब्रह्म मुहूर्त: {p.brahma_muhurta}\n" if p.brahma_muhurta else ""

        caption = (
            f"🌸 आज का पंचांग • {p.date_formatted_hi}\n\n"
            f"आज {p.vara_hi} ({p.vara_en}) है, {p.deity_hi} की आराधना का पावन दिन।\n"
            f"✨ तिथि: {p.tithi_name_hi} ({p.tithi_name})\n"
            f"⭐ नक्षत्र: {p.nakshatra_name_hi} ({p.nakshatra_name})\n"
            f"{yoga_str}"
            f"{karana_str}"
            f"🌟 अभिजीत मुहूर्त: {p.abhijit_muhurta}\n"
            f"{brahma_str}"
            f"⚠️ राहुकाल: {p.rahu_kaal}\n"
            f"☀️ सूर्योदय: {p.sunrise_str} | सूर्यास्त: {p.sunset_str}\n"
            f"🙏 दैनिक संकल्प: {p.remedy}\n\n"
            f"✨ Daily Vedic Overview:\n"
            f"Begin your {p.vara_en} aligned with the cosmos. Tap into the energy of {p.nakshatra_name} nakshatra, utilize Abhijit Muhurta for auspicious undertakings, and maintain mindfulness during Rahu Kaal.\n\n"
            f"{cta_block}"
        )
        tags = ["Panchang", "DailyPanchang", "VedicAstrology", "Tithi", "Nakshatra", "SiddhantaApp", "पंचांग", "शुभमुहूर्त"]
        return {"instagram_caption": caption, "hashtags": tags}
