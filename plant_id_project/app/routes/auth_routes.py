from flask import Blueprint, request, render_template, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import mysql.connector
from ..utils.db import get_db

auth_bp = Blueprint('auth', __name__)

# 登入頁面
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash('登入成功', 'success')
            return redirect(url_for('identify.upload_image'))
        else:
            flash('帳號或密碼錯誤', 'danger')

    return render_template('login.html')

# 註冊頁面
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash('帳號已存在', 'danger')
            return redirect(url_for('auth.register'))

        hashed_pw = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, usage_count, last_used_date)
            VALUES (%s, %s, 0, %s)
        """, (username, hashed_pw, date.today()))
        db.commit()

        flash('註冊成功，請登入', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

# 登出
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('您已登出', 'info')
    return redirect(url_for('auth.login'))

# 使用次數檢查（可在辨識前呼叫）
def check_usage_limit(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT usage_count, last_used_date FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    today = date.today()
    if user['last_used_date'] != today:
        cursor.execute("UPDATE users SET usage_count=1, last_used_date=%s WHERE user_id=%s", (today, user_id))
        db.commit()
        return True
    elif user['usage_count'] < 10:
        cursor.execute("UPDATE users SET usage_count=usage_count+1 WHERE user_id=%s", (user_id,))
        db.commit()
        return True
    else:
        return False
