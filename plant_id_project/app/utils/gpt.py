import os
from openai import OpenAI
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate

# 載入 .env 環境變數
load_dotenv()

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- GPT 模型切分 ----------
def ask_gpt_3_5(messages):
    """使用 GPT-3.5-Turbo 回答問題（聊天用）"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT-3.5 錯誤：", e)
        return "GPT 回覆失敗，請稍後再試。"

def ask_gpt_4(messages):
    """使用 GPT-4-Turbo 處理翻譯（學名用）"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT-4 錯誤：", e)
        return "GPT 翻譯失敗，請稍後再試。"

# ---------- 專用功能 ----------
def translate_scientific_name(name):
    """翻譯學名 → 中文名（使用 GPT-4）"""
    try:
        messages = [
            {"role": "system", "content": "你是一位植物學家，請協助將植物學名翻譯成簡單易懂的中文名稱。只回傳名稱，不要多餘說明。"},
            {"role": "user", "content": f"請將植物學名「{name}」翻譯成中文名稱。"}
        ]
        result = ask_gpt_4(messages)
        return result
    except Exception as e:
        print("❌ GPT 翻譯學名錯誤：", e)
        return name  # fallback 回傳原本學名

def ask_gpt_with_context(messages):
    """聊天功能（使用 GPT-3.5）"""
    return ask_gpt_3_5(messages)

# ---------- Google 翻譯備用 ----------
def translate_to_chinese(text):
    try:
        client = translate.Client()
        result = client.translate(text, target_language='zh-TW')
        return result['translatedText']
    except Exception as e:
        print("❌ Google 翻譯錯誤：", e)
        return text
