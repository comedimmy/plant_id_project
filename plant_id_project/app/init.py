from flask import Flask, redirect, url_for  # 加入這行

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    app.secret_key = 'your_secret_key'

    from .utils.db import init_db
    from .routes.auth_routes import auth_bp
    from .routes.identify_routes import identify_bp

    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(identify_bp)

    # ✅ 新增首頁轉跳到登入頁
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
