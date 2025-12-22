from datetime import datetime
import os
import os.path
import warnings

from babel.dates import LOCALTZ
from flask import Flask, g, render_template, request, session
from flask_babel import Babel, format_currency
from flask_mail import Mail
from flask_migrate import Migrate, stamp, upgrade
from flask_talisman import Talisman
from jinja2 import pass_context
from markupsafe import Markup
import pytz
from werkzeug.middleware.proxy_fix import ProxyFix

from ihatemoney import default_settings
from ihatemoney.api.v1 import api as apiv1
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.models import db
from ihatemoney.utils import (
    IhmJSONEncoder,
    PrefixedWSGI,
    em_surround,
    limiter,
    locale_from_iso,
    localize_list,
    minimal_round,
    static_include,
)
from ihatemoney.web import main as web_interface


def setup_database(app):
    def _pre_alembic_db():
        con = db.engine.connect()
        tables_exist = db.engine.dialect.has_table(con, "project")
        alembic_setup = db.engine.dialect.has_table(con, "alembic_version")
        return tables_exist and not alembic_setup

    sqlalchemy_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if sqlalchemy_url.startswith("sqlite:////tmp"):
        warnings.warn(
            "The database is currently stored in /tmp and might be lost at "
            "next reboot."
        )

    db.init_app(app)
    db.app = app

    Migrate(app, db)
    migrations_path = os.path.join(app.root_path, "migrations")

    if _pre_alembic_db():
        with app.app_context():
            stamp(migrations_path, revision="b9a10d5d63ce")

    with app.app_context():
        upgrade(migrations_path)


def load_configuration(app, configuration=None):
    env_var_config = os.environ.get("IHATEMONEY_SETTINGS_FILE_PATH")
    app.config.from_object("ihatemoney.default_settings")
    if configuration:
        app.config.from_object(configuration)
    elif env_var_config:
        app.config.from_pyfile(env_var_config)
    else:
        app.config.from_pyfile("ihatemoney.cfg", silent=True)
    app.config["RESTFUL_JSON"] = {"cls": IhmJSONEncoder}


def validate_configuration(app):
    if app.config["SECRET_KEY"] == default_settings.SECRET_KEY:
        warnings.warn(
            "Running a server without changing the SECRET_KEY can lead to"
            + " user impersonation. Please update your configuration file.",
            UserWarning,
        )
    if "DEFAULT_MAIL_SENDER" in app.config:
        warnings.warn(
            "DEFAULT_MAIL_SENDER is deprecated in favor of MAIL_DEFAULT_SENDER"
            + " and will be removed in further version",
            UserWarning,
        )
        if "MAIL_DEFAULT_SENDER" not in app.config:
            app.config["MAIL_DEFAULT_SENDER"] = default_settings.DEFAULT_MAIL_SENDER

    if type(app.config["MAIL_DEFAULT_SENDER"]) is tuple:
        (name, address) = app.config["MAIL_DEFAULT_SENDER"]
        app.config["MAIL_DEFAULT_SENDER"] = f"{name} <{address}>"
        warnings.warn(
            "MAIL_DEFAULT_SENDER has been changed from tuple to string."
            + f" It was converted to '{app.config['MAIL_DEFAULT_SENDER']}'."
            + " Auto-conversion will be removed in future version.",
            UserWarning,
        )

    if "pbkdf2:" not in app.config["ADMIN_PASSWORD"] and app.config["ADMIN_PASSWORD"]:
        warnings.warn(
            "The way Ihatemoney stores your ADMIN_PASSWORD has changed. You are using an unhashed"
            + " ADMIN_PASSWORD, which is not supported anymore and won't let you access your admin"
            + " endpoints. Please use the command 'ihatemoney generate_password_hash'"
            + " to generate a proper password HASH and copy the output to the value of"
            + " ADMIN_PASSWORD in your settings file.",
            UserWarning,
        )


def page_not_found(e):
    return render_template("404.html", root="main"), 404


def create_app(
    configuration=None, instance_path="/etc/ihatemoney", instance_relative_config=True
):
    app = Flask(
        __name__,
        instance_path=instance_path,
        instance_relative_config=instance_relative_config,
    )

    csp = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "object-src": "'none'",
        "img-src": ["'self'", "data:"],
        "style-src": ["'self'", "'unsafe-inline'"],
    }

    Talisman(
        app,
        force_https=False,
        session_cookie_secure=False,
        content_security_policy=csp,
    )

    load_configuration(app, configuration)
    app.wsgi_app = PrefixedWSGI(app)

    app.wsgi_app = ProxyFix(app.wsgi_app)

    validate_configuration(app)
    app.register_blueprint(web_interface)
    app.register_blueprint(apiv1)
    app.register_error_handler(404, page_not_found)
    limiter.init_app(app)

    setup_database(app)

    CurrencyConverter()

    mail = Mail()
    mail.init_app(app)
    app.mail = mail

    app.jinja_env.globals["static_include"] = static_include
    app.jinja_env.globals["locale_from_iso"] = locale_from_iso
    app.jinja_env.filters["minimal_round"] = minimal_round
    app.jinja_env.filters["em_surround"] = lambda text: Markup(em_surround(text))
    app.jinja_env.filters["localize_list"] = localize_list
    app.jinja_env.filters["from_timestamp"] = datetime.fromtimestamp

    default_timezone = "UTC"
    try:
        pytz.timezone(str(LOCALTZ))
        default_timezone = str(LOCALTZ)
    except pytz.exceptions.UnknownTimeZoneError:
        pass

    def get_locale():
        lang = session.get(
            "lang",
            request.accept_languages.best_match(app.config["SUPPORTED_LANGUAGES"]),
        )
        setattr(g, "lang", lang)
        return lang

    if hasattr(Babel, "localeselector"):
        babel = Babel(app, default_timezone=default_timezone)
        babel.localeselector(get_locale)
    else:
        Babel(app, default_timezone=default_timezone, locale_selector=get_locale)

    @pass_context
    def currency(context, number, currency=None, *args, **kwargs):
        if currency is None:
            currency = context.get("g").project.default_currency
        return format_currency(
            number,
            currency if currency != CurrencyConverter.no_currency else "",
            *args,
            **kwargs,
        ).strip()

    app.jinja_env.filters["currency"] = currency

    return app


def main():
    app = create_app()
    app.run(host="0.0.0.0", debug=True)


if __name__ == "__main__":
    main()
