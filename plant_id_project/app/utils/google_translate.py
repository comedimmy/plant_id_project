import os
from google.cloud import translate_v2 as translate
from dotenv import load_dotenv

load_dotenv()

# 自動根據 GOOGLE_APPLICATION_CREDENTIALS 讀取金鑰 JSON 路徑
translate_client = translate.Client()

def translate_to_chinese(text):
    try:
        result = translate_client.translate(text, target_language='zh-TW')
        return result['translatedText']
    except Exception as e:
        print("Google 翻譯錯誤：", e)
        return text  # 若失敗則回傳原文字
