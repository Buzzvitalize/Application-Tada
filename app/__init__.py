from flask import Flask, redirect, url_for
from .models import db
try:
    from flask_migrate import Migrate
except ModuleNotFoundError:  # pragma: no cover
    class Migrate:
        def __init__(self, *a, **k):
            pass
        def init_app(self, *a, **k):
            pass
try:
    from flask_wtf import CSRFProtect
except ModuleNotFoundError:  # pragma: no cover
    from flask import session, request, abort

    class CSRFProtect:
        def __init__(self, app=None):
            if app:
                self.init_app(app)

        def init_app(self, app):
            app.before_request(self._check)
            app.jinja_env.globals['csrf_token'] = self.generate_csrf

        def generate_csrf(self):
            token = session.get('csrf_token', 'stub-token')
            session['csrf_token'] = token
            return token

        def _check(self):
            if request.method == 'POST':
                token = session.get('csrf_token')
                form_token = request.form.get('csrf_token')
                if not token or token != form_token:
                    abort(400)

migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    from config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    app.jinja_env.filters.setdefault('money', lambda v: f"{v:.2f}")
    app.jinja_env.filters.setdefault('id_doc', lambda v: v)
    app.jinja_env.filters.setdefault('phone', lambda v: v)

    from .auth.routes import auth_bp
    from .clientes.routes import clientes_bp
    from .productos.routes import productos_bp
    from .cotizaciones.routes import cotizaciones_bp
    from .facturas.routes import facturas_bp
    from .reportes.routes import reportes_bp
    from .misc.routes import misc_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(cotizaciones_bp)
    app.register_blueprint(facturas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(misc_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
