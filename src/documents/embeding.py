from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

model=OpenAI(
    api_key=os.getenv("LM_STUDIO_API_KEY"),
    base_url=os.getenv("LM_STUDIO_BASE_URL"),
)

def get_embedding(text: str) -> list[float]:
    response = model.embeddings.create(
        input=text,
        model=os.getenv("LM_STUDIO_EMBEDDING_MODEL"),
    )
    return response.data[0].embedding

if __name__ == "__main__":
    print(get_embedding("Hello, world!"))
