from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "你知道Tulipa gesneriana是甚麼嗎? 與花名有關"}]
)
print(response.choices[0].message.content)
