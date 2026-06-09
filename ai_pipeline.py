import base64
import json
import os

import requests as http_requests
from openai import OpenAI


class AIPipeline:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = "gpt-4.1"

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str | dict:
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        return json.loads(content) if json_mode else content

    def brainstorm_pains(self, keyword: str) -> str:
        return self._chat(
            "You are a veteran market-research copywriter who uncovers deep customer pains and frustrations with clear, bullet-point precision.",
            f'List the 10 biggest pains and frustrations people have around "{keyword}". Return each as a concise bullet.',
        )

    def generate_solutions(self, keyword: str, pains: str) -> str:
        return self._chat(
            "You are a seasoned problem-solving strategist who turns customer pains into clear, actionable solutions.",
            f'Below are the top pains people face around "{keyword}":\n\n{pains}\n\nFor each pain, write one concise solution that directly addresses it. Return as a numbered list, one sentence each.',
        )

    def create_offer(self, keyword: str, pains: str) -> str:
        return self._chat(
            "You are an expert direct-response strategist who crafts irresistible offers using Alex Hormozi's $100M Offers framework.",
            f'Topic: "{keyword}"\n\nTop customer pains:\n{pains}\n\nApply Alex Hormozi\'s $100M Offers framework and craft a single compelling offer.\n\nReturn in this exact format:\n\n• **Offer Title:** …\n• **Dream Outcome:** …\n• **Perceived Likelihood:** …\n• **Time Delay:** …\n• **Effort & Sacrifice:** …\n• **Key Features & Bonuses:** (3–5 bullets)',
        )

    def create_title(self, offer: str) -> dict:
        return self._chat(
            "You are a seasoned marketing copywriter who crafts scroll-stopping ebook titles that promise a clear, tangible result.",
            f'Here\'s the offer:\n\n{offer}\n\n1. Propose three punchy ebook titles (each under 12 words) that convey the core outcome and spark curiosity.\n2. Pick the single best title.\n\nReturn strict JSON:\n{{"titles": ["Title 1", "Title 2", "Title 3"], "selectedTitle": "The winner", "rationale": "Why this one converts best"}}',
            json_mode=True,
        )

    def build_outline(self, title: str, keyword: str) -> str:
        return self._chat(
            "You are an expert ebook outline strategist and educational content architect. You design structures that flow logically, teach clearly, and drive action.",
            f'We\'re writing an ebook titled "{title}".\n\nCreate a detailed outline:\n1. Introduction — hook readers with the core promise and explain why this matters for the {keyword} niche\n2. Section 1–6 — bold benefit-driven headings, 3–5 bullet sub-topics each\n3. Conclusion & 3-Step Action Plan\n\nReturn as a numbered list with sub-bullets.',
        )

    def generate_cover(
        self, title: str, keyword: str, session_id: str, output_dir: str
    ) -> str:
        prompt = (
            f'Award-winning ebook cover for "{title}", targeting people interested in "{keyword}". '
            "Central figure representing the primary demographic. "
            "Visual metaphors tied to the core offer. "
            "Bold legible typography with the title prominently displayed. "
            "High-contrast palette: black & white plus one high-converting accent color. "
            "Modern minimalist layout. Portrait orientation."
        )
        resp = self.client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1536",
            n=1,
        )
        img = resp.data[0]
        if img.b64_json:
            image_bytes = base64.b64decode(img.b64_json)
        else:
            image_bytes = http_requests.get(img.url, timeout=60).content
        cover_path = os.path.join(output_dir, f"cover_{session_id}.png")
        with open(cover_path, "wb") as f:
            f.write(image_bytes)
        return cover_path

    def write_ebook(self, title: str, keyword: str, outline: str) -> str:
        return self._chat(
            "You are a veteran nonfiction ghostwriter who turns outlines into engaging, easy-to-read ebooks at a 6th-grade reading level while still sounding professional and motivating.",
            f'Title: "{title}"\nTarget niche: "{keyword}"\n\nOutline:\n{outline}\n\nWrite the full ebook following that structure:\n• Keep every heading exactly as listed.\n• Expand each section to 300–500 words of clear prose.\n• Tone: friendly, confident, action-oriented.\n• Short paragraphs with occasional bold phrases for emphasis.\n• After the Conclusion, include the 3-step action plan as a numbered list.\n\nReturn the completed manuscript as plain text only — no additional commentary or JSON.',
        )

    def create_value_enhancer(self, title: str, keyword: str, offer: str) -> dict:
        return self._chat(
            "You are a product strategist who creates high-perceived-value bonuses and upsells.",
            f'Title: "{title}"\nTopic: "{keyword}"\nOffer summary:\n{offer}\n\n1. Propose 5 high-value bonuses — name, format (template/checklist/etc.), benefit under 20 words.\n2. Suggest a paid One-Time Offer ($97–$297) — name, price, description, 3–5 deliverables.\n3. Create a 5-section workbook outline — section name and description.\n\nReturn strict JSON:\n{{"bonuses": [{{"name": "", "format": "", "benefit": ""}}], "oto": {{"name": "", "price": 97, "description": "", "deliverables": []}}, "workbookOutline": [{{"section": "", "description": ""}}]}}',
            json_mode=True,
        )
