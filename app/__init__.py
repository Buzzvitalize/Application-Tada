from flask import Flask
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
    class CSRFProtect:
        def __init__(self, app=None):
            if app:
                self.init_app(app)
        def init_app(self, app):
            pass

migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    from config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .auth.routes import auth_bp
    from .clientes.routes import clientes_bp
    from .productos.routes import productos_bp
    from .cotizaciones.routes import cotizaciones_bp
    from .facturas.routes import facturas_bp
    from .reportes.routes import reportes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(cotizaciones_bp)
    app.register_blueprint(facturas_bp)
    app.register_blueprint(reportes_bp)

    @app.route('/')
    def index():
        return 'OK'

    return app
