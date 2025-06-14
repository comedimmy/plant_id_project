import os
import mysql.connector
import requests
from flask import Blueprint, request, render_template, redirect, session, url_for, flash
from datetime import datetime
from app.routes.auth_routes import check_usage_limit
from ..utils.gpt import translate_scientific_name, ask_gpt_with_context, translate_to_chinese,ask_gpt_4,ask_gpt_3_5
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
from ..utils.db import get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'static', 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

load_dotenv()

identify_bp = Blueprint('identify', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'webp'}

PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def translate_with_gpt_fallback(scientific_name, common_names):
    try:
        # 1. 優先使用 GPT-4 翻譯學名
        translated = translate_scientific_name(scientific_name)

        # 2. 若 GPT-4 回傳內容和原本學名一樣（表示失敗），再試著翻譯英文俗名
        if translated.strip() == scientific_name and common_names:
            print("⚠️ GPT 翻譯學名無效，嘗試使用 common name:", common_names[0])
            messages = [
                {"role": "system", "content": "你是一位植物分類專家，請根據提供的英文俗名翻譯為常見中文名稱。"},
                {"role": "user", "content": f"請將植物英文名稱「{common_names[0]}」翻譯成常見中文名稱，只回答繁體中文名稱"}
            ]
            translated = ask_gpt_4(messages)

        # 3. 如果仍然失敗（回傳空值或錯誤字眼），改用 Google 翻譯備援
        if "失敗" in translated or not translated.strip():
            raise ValueError("GPT 翻譯結果異常")

        return translated

    except Exception as e:
        print("⚠️ GPT翻譯失敗：", e)
        return translate_to_chinese(common_names[0] if common_names else scientific_name)


@identify_bp.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_input = request.form['user_input']
        plant_name = session.get('plant_name')
        plant_name_zh = session.get('plant_name_zh')
        username = session.get('username')

        if not plant_name or not plant_name_zh or not username:
            flash("植物資料遺失或未登入", "danger")
            return redirect(url_for('identify.upload_image'))

        # 新增訊息至 session chat_history
        chat_history = session.get('chat_history', [])
        chat_history.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": f"你是一位植物專家，請針對植物「{plant_name_zh}（{plant_name}）」回答問題。"}]
        messages.extend(chat_history)

        gpt_reply = ask_gpt_with_context(messages)
        chat_history.append({"role": "assistant", "content": gpt_reply})
        session['chat_history'] = chat_history
        
    if 'chat_history' not in session:
        session['chat_history'] = []

    return render_template('chat.html',
        plant_name=session.get('plant_name'),
        plant_name_zh=session.get('plant_name_zh'),
        plant_name_en=session.get('plant_name_en'),
        image_url=session.get('plant_image_url'),
        messages=session.get('chat_history', []))

@identify_bp.route('/reset_chat')
def reset_chat():
    session.pop('chat_history', None)
    session.pop('plant_name', None)
    session.pop('plant_name_zh', None)
    session.pop('plant_name_en',None)
    session.pop('plant_image_url', None)
    session.pop('plant_filename', None)
    return redirect(url_for('identify.upload_image'))

@identify_bp.route('/upload', methods=['GET', 'POST'])
def upload_image():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if not check_usage_limit(session['user_id']):
            flash('今日已達辨識上限（10次）', 'warning')
            return redirect(url_for('identify.upload_image'))

        if 'image' not in request.files:
            flash('請選擇圖片', 'danger')
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            flash('未選擇檔案', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            try:
                file.save(filepath)
            except Exception as e:
                print("❌ 圖片儲存失敗：", e)
                flash('圖片儲存失敗', 'danger')
                return redirect(url_for('identify.upload_image'))

            if not os.path.exists(filepath):
                print("❌ 圖片儲存後找不到檔案！", filepath)
                flash('圖片找不到', 'danger')
                return redirect(url_for('identify.upload_image'))

            print("✅ 儲存圖片成功，檔案路徑：", filepath)

            try:
                with open(filepath, 'rb') as image_file:
                    files = [('images', (filename, image_file, 'image/jpeg'))]
                    response = requests.post(
                        f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}",
                        files=files
                    )

                print("🌱 PlantNet 狀態碼：", response.status_code)

                if response.status_code != 200:
                    flash("辨識失敗，請重新上傳圖片", "danger")
                    print("❌ 錯誤內容：", response.text)
                    return redirect(url_for('identify.upload_image'))

                result = response.json()
                print("🌿 回傳結果：", result)

                if not result.get('results') or len(result['results']) == 0:
                    flash("辨識失敗，無植物結果", "danger")
                    return redirect(url_for('identify.upload_image'))

                plant_name = result['results'][0]['species']['scientificNameWithoutAuthor']
                print("✅ 辨識植物：", plant_name)

                common_names = result['results'][0]['species'].get('commonNames', [])
                plant_name_zh = translate_with_gpt_fallback(plant_name, common_names)

            except Exception as e:
                print("❌ 辨識過程中出錯：", e)
                flash("辨識過程中出錯", "danger")
                return redirect(url_for('identify.upload_image'))

            session['plant_name'] = plant_name
            session['plant_name_zh'] = plant_name_zh
            session['plant_filename'] = filename
            session['plant_image_url'] = url_for('static', filename='uploads/' + filename)
            session['chat_history'] = []
            session['plant_name_en'] = common_names[0] if common_names else ''
            return redirect(url_for('identify.chat'))
        return render_template('upload.html')

    if request.method == 'GET':
        db = get_db()
        user_id = session['user_id']  # user_id 是主鍵
        username = session['username']
        usage_count = 0
        recent_history = []

        try:
            cursor = db.cursor(dictionary=True)
            # 查詢 usage_count
            cursor.execute("SELECT usage_count FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result:
                usage_count = result['usage_count']

            # 查詢最近紀錄
            cursor.execute("""
                SELECT flower_name AS plant_name_zh, add_time AS timestamp
                FROM history
                WHERE users = %s
                ORDER BY add_time DESC
                LIMIT 3
            """, (username,))
            recent_history = cursor.fetchall()
        except Exception as e:
            print("❌ 查詢使用者紀錄錯誤：", e)

        return render_template("upload.html", recent_history=recent_history, usage_count=usage_count)

@identify_bp.route('/end_chat')
def end_chat():
    plant_name = session.get('plant_name')
    plant_name_zh = session.get('plant_name_zh')
    username = session.get('username')
    chat_history = session.get('chat_history', [])

    if not plant_name or not plant_name_zh or not username:
        flash("資料遺失，無法儲存紀錄", "warning")
        return redirect(url_for('identify.upload_image'))

    try:
        if len(chat_history) > 2:
            summary_prompt = [
                {"role": "system", "content": "你是一位植物專家，請彙整以下使用者與你的對話重點。"},
                {"role": "user", "content": f"以下是使用者與你的聊天記錄，請簡潔整理出這些關於植物「{plant_name_zh}（{plant_name}）」的問答重點。如果沒有具體問題，也請你主動補充這植物的常見知識。\n\n{chat_history}"}
            ]
            summary = ask_gpt_4(summary_prompt)

            insert_sql = """
            INSERT INTO history (users, text, flower_name, add_time)
            VALUES (%s, %s, %s, %s)
            """
            values = (username, summary, plant_name_zh, datetime.now())
            db = get_db()
            cursor = db.cursor()
            cursor.execute(insert_sql, values)
            db.commit()

            flash("✅ 對話紀錄已整理並儲存", "success")
        else:
            flash("尚未有足夠對話內容，無需彙整", "info")

    except Exception as e:
        print("❌ 儲存對話摘要失敗：", e)
        flash("❌ 對話摘要儲存失敗", "danger")

    # 清除 session 對話資料
    session.pop('chat_history', None)
    session.pop('plant_name', None)
    session.pop('plant_name_zh', None)
    session.pop('plant_name_en', None)
    session.pop('plant_image_url', None)
    session.pop('plant_filename', None)

    return redirect(url_for('identify.upload_image'))

@identify_bp.route('/history')
def history():
    username = session.get('username') 
    if not username:
        flash("請先登入", "warning")
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT flower_name AS plant_name_zh, text AS summary, add_time AS timestamp
        FROM history
        WHERE users = %s
        ORDER BY add_time DESC
    """, (username,))
    history_list = cursor.fetchall()

    return render_template('history.html', history_list=history_list)
