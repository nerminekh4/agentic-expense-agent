import os
import json
import base64
from groq import Groq
from dotenv import load_dotenv


class ExpenseAgent:
    def __init__(self):
        load_dotenv()

        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

        base_dir = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(base_dir, "context.txt"), "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        with open(os.path.join(base_dir, "prompt.txt"), "r", encoding="utf-8") as f:
            self.user_prompt = f.read()

    def extract_from_bytes(self, image_bytes: bytes, media_type: str) -> dict:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{media_type};base64,{b64_image}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_content = response.choices[0].message.content

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            data = {}

        result = {
            "type_document": data.get("type_document"),
            "fournisseur": data.get("fournisseur"),
            "date": data.get("date"),
            "montant_ttc": data.get("montant_ttc"),
            "tva": data.get("tva"),
            "devise": data.get("devise") or "EUR",
            "description": data.get("description"),
            "confiance": data.get("confiance"),
        }

        return result


if __name__ == "__main__":
    image_path = "test_ticket.jpg"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    agent = ExpenseAgent()
    result = agent.extract_from_bytes(image_bytes, media_type="image/jpeg")

    print(json.dumps(result, indent=2, ensure_ascii=False))