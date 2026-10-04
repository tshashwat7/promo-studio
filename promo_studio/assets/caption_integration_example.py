"""Example adapter boundary; replace `call_gemini` with your existing client."""

from promo_studio import PromoStudio
from promo_studio.caption import CaptionInput

def build_caption_request(result: dict) -> dict:
    """Return exactly the two fields allowed across the AI boundary."""
    return {
        "system": result["caption_system_prompt"],
        "input": result["caption_input"],
    }

# Example:
#
# result = PromoStudio("output").generate(payload)
# request = build_caption_request(result)
# caption = call_gemini(system=request["system"], user=request["input"])
#
# Do NOT pass `payload` to the caption model.
