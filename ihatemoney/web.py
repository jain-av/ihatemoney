import datetime
from functools import wraps
import hashlib
import json
import os
from urllib.parse import urlparse, urlunparse

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from flask_babel import gettext as _
from flask_mail import Message
import qrcode
import qrcode.image.svg
from sqlalchemy_continuum import Operation
from werkzeug.exceptions import NotFound
from werkzeug.security import check_password_hash

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.emails import send_creation_email
from ihatemoney.forms import (
    AdminAuthenticationForm,
    AuthenticationForm,
    DestructiveActionProjectForm,
    EditProjectForm,
    EmptyForm,
    ImportProjectForm,
    InviteForm,
    LogoutForm,
    MemberForm,
    PasswordReminder,
    ProjectForm,
    ProjectFormWithCaptcha,
    ResetPasswordForm,
    SettlementForm,
    get_billform_for,
)
from ihatemoney.history import get_history, get_history_queries, purge_history
from ihatemoney.models import Bill, BillType, LoggingMode, Person, Project, db
from ihatemoney.utils import (
    Redirect303,
    csv2list_of_dicts,
    flash_email_error,
    format_form_errors,
    generate_password_hash,
    limiter,
    list_of_dicts2csv,
    list_of_dicts2json,
    render_localized_template,
    send_email,
)

main = Blueprint("main", __name__)


def requires_admin(bypass=None):
    def check_admin(f):
        @wraps(f)
        def admin_auth(*args, **kws):
            is_admin_auth_bypassed = False
            if bypass is not None and current_app.config.get(bypass[0]) == bypass[1]:
                is_admin_auth_bypassed = True
            is_admin = session.get("is_admin")
            if is_admin or is_admin_auth_bypassed:
                return f(*args, **kws)
            raise Redirect303(url_for(".admin", goto=request.path))

        return admin_auth

    return check_admin


@main.url_defaults
def add_project_id(endpoint, values):
    if "project_id" in values or not hasattr(g, "project"):
        return
    if current_app.url_map.is_endpoint_expecting(endpoint, "project_id"):
        values["project_id"] = g.project.id


@main.url_value_preprocessor
def migrate_session(endpoint, values):
    if "projects" in session and isinstance(session["projects"], list):
        session["projects"] = {id: name for (id, name) in session["projects"]}


@main.url_value_preprocessor
def set_show_admin_dashboard_link(endpoint, values):
    g.show_admin_dashboard_link = (
        current_app.config["ACTIVATE_ADMIN_DASHBOARD"]
        and current_app.config["ADMIN_PASSWORD"]
    )
    g.logout_form = LogoutForm()


@main.context_processor
def add_template_variables():
    return {"SITE_NAME": current_app.config.get("SITE_NAME")}


@main.url_value_preprocessor
def pull_project(endpoint, values):
    if endpoint == "authenticate":
        return
    if not values:
        values = {}
    entered_project_id = values.pop("project_id", None)
    if entered_project_id:
        project_id = entered_project_id.lower()
        project = Project.query.get(project_id)
        if not project:
            raise Redirect303(url_for(".create_project", project_id=project_id))

        is_admin = session.get("is_admin")
        is_invitation = endpoint == "main.join_project"
        is_feed = endpoint == "main.feed"
        if session.get(project.id) or is_admin or is_invitation or is_feed:
            g.project = project
        else:
            raise Redirect303(url_for(".authenticate", project_id=project_id))


@main.route("/healthcheck", methods=["GET"])
def health():
    return "OK"


def admin_limit(limit):
    return make_response(
        render_template(
            "admin.html",
            breached_limit=limit,
            limit_message=_("Too many failed login attempts."),
        )
    )


@main.route("/admin", methods=["GET", "POST"])
@limiter.limit(
    "3/minute",
    on_breach=admin_limit,
    methods=["POST"],
)
def admin():
    form = AdminAuthenticationForm()
    goto = request.args.get("goto", url_for(".home"))
    is_admin_auth_enabled = bool(current_app.config["ADMIN_PASSWORD"])
    if request.method == "POST" and form.validate():
        if check_password_hash(
            current_app.config["ADMIN_PASSWORD"], form.admin_password.data
        ):
            session["is_admin"] = True
            session.update()
            return redirect(goto)
        if limiter.current_limit is not None:
            msg = _(
                "This admin password is not the right one. Only %(num)d attempts left.",
                num=limiter.current_limit.remaining,
            )
            form["admin_password"].errors = [msg]
    return render_template(
        "admin.html",
        form=form,
        admin_auth=True,
        is_admin_auth_enabled=is_admin_auth_enabled,
    )


def set_authorized_project(project: Project):
    new_project = {project.id: project.name}
    if "projects" not in session:
        session["projects"] = new_project
    else:
        session["projects"] = {**new_project, **session["projects"]}
    session[project.id] = True
    session.permanent = True
    session.update()


@main.route("/<project_id>/join/<string:token>", methods=["GET"])
def join_project(token):
    project_id = g.project.id
    verified_project_id = Project.verify_token(
        token, token_type="auth", project_id=project_id
    )
    if verified_project_id != project_id:
        flash(_("Provided token is invalid"), "danger")
        return redirect("/")

    set_authorized_project(g.project)
    return redirect(url_for(".list_bills"))


@main.route("/authenticate", methods=["GET", "POST"])
def authenticate(project_id=None):
    form = AuthenticationForm()

    if not form.id.data and request.args.get("project_id"):
        form.id.data = request.args["project_id"]
    project_id = form.id.data.lower() if form.id.data else None

    project = Project.query.get(project_id) if project_id is not None else None
    if not project:
        return render_template(
            "authenticate.html", form=form, create_project=project_id
        )

    if session.get(project_id):
        setattr(g, "project", project)
        return redirect(url_for(".list_bills"))

    is_post_auth = request.method == "POST" and form.validate()
    if is_post_auth and check_password_hash(project.password, form.password.data):
        set_authorized_project(project)
        setattr(g, "project", project)
        return redirect(url_for(".list_bills"))
    if is_post_auth and not check_password_hash(project.password, form.password.data):
        msg = _("This private code is not the right one")
        form["password"].errors = [msg]

    return render_template("authenticate.html", form=form)


def get_project_form():
    if current_app.config.get("ENABLE_CAPTCHA", False):
        return ProjectFormWithCaptcha()
    return ProjectForm()


@main.route("/", strict_slashes=False)
def home():
    project_form = get_project_form()
    auth_form = AuthenticationForm()
    is_demo_project_activated = current_app.config["ACTIVATE_DEMO_PROJECT"]
    is_public_project_creation_allowed = current_app.config[
        "ALLOW_PUBLIC_PROJECT_CREATION"
    ]

    return render_template(
        "home.html",
        project_form=project_form,
        is_demo_project_activated=is_demo_project_activated,
        is_public_project_creation_allowed=is_public_project_creation_allowed,
        auth_form=auth_form,
        session=session,
    )


@main.route("/mobile")
def mobile():
    return render_template("download_mobile_app.html")


@main.route("/create", methods=["GET", "POST"])
@requires_admin(bypass=("ALLOW_PUBLIC_PROJECT_CREATION", True))
def create_project():
    form = get_project_form()
    if request.method == "GET" and "project_id" in request.values:
        form.name.data = request.values["project_id"]

    if request.method == "POST":
        if not form.id.data:
            form.id.data = form.name.data
        if form.validate():
            project = form.save()
            db.session.add(project)
            db.session.commit()

            set_authorized_project(project)

            g.project = project
            success = send_creation_email(project)
            if success:
                flash(
                    _("A reminder email has just been sent to you"), category="success"
                )
            else:
                flash_email_error(
                    _(
                        "We tried to send you an reminder email, but there was an error. "
                        "You can still use the project normally."
                    ),
                    category="info",
                )
            return redirect(url_for(".list_bills", project_id=project.id))

    return render_template("create_project.html", form=form)


@main.route("/password-reminder", methods=["GET", "POST"])
def remind_password():
    form = PasswordReminder()
    if request.method == "POST":
        if form.validate():
            project = Project.query.get(form.id.data)
            remind_message = Message(
                "password recovery",
                body=render_localized_template("password_reminder", project=project),
                recipients=[project.contact_email],
            )
            success = send_email(remind_message)
            if success:
                return redirect(url_for(".password_reminder_sent"))
            else:
                flash_email_error(
                    _(
                        "Sorry, there was an error while sending you an email with "
                        "password reset instructions."
                    )
                )
    return render_template("password_reminder.html", form=form)


@main.route("/password-reminder-sent", methods=["GET"])
def password_reminder_sent():
    return render_template("password_reminder_sent.html")


@main.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    form = ResetPasswordForm()
    token = request.args.get("token")
    if not token:
        return render_template(
            "reset_password.html", form=form, error=_("No token provided")
        )
    project_id = Project.verify_token(token, token_type="reset")
    if not project_id:
        return render_template(
            "reset_password.html", form=form, error=_("Invalid token")
        )
    project = Project.query.get(project_id)
    if not project:
        return render_template(
            "reset_password.html", form=form, error=_("Unknown project")
        )

    if request.method == "POST" and form.validate():
        project.password = generate_password_hash(form.password.data)
        db.session.add(project)
        db.session.commit()
        flash(_("Password successfully reset."))
        return redirect(url_for(".home"))
    return render_template("reset_password.html", form=form)


@main.route("/<project_id>/edit", methods=["GET", "POST"])
def edit_project():
    edit_form = EditProjectForm(id=g.project.id)
    import_form = ImportProjectForm(id=g.project.id)
    delete_form = DestructiveActionProjectForm(id=g.project.id)

    if edit_form.validate_on_submit():
        project = edit_form.update(g.project)

        db.session.add(project)
        db.session.commit()

        flash(_("Project settings have been changed successfully."))
        return redirect(url_for("main.edit_project"))
    else:
        edit_form.name.data = g.project.name

        if g.project.logging_preference != LoggingMode.DISABLED:
            edit_form.project_history.data = True
            if g.project.logging_preference == LoggingMode.RECORD_IP:
                edit_form.ip_recording.data = True

        edit_form.contact_email.data = g.project.contact_email
        edit_form.default_currency.data = g.project.default_currency

    return render_template(
        "edit_project.html",
        edit_form=edit_form,
        import_form=import_form,
        delete_form=delete_form,
        current_view="edit_project",
    )


@main.route("/<project_id>/import", methods=["POST"])
def import_project():
    form = ImportProjectForm()
    if form.validate():
        try:
            data = form.file.data
            if data.mimetype == "application/json":
                bills = json.load(data.stream)
            elif data.mimetype == "text/csv":
                try:
                    bills = csv2list_of_dicts(data)
                except Exception:
                    raise ValueError(_("Unable to parse CSV"))
            else:
                raise ValueError("Unsupported file type")

            attr = [
                "amount",
                "bill_type",
                "currency",
                "date",
                "owers",
                "payer_name",
                "payer_weight",
                "what",
            ]
            currencies = set()
            for b in bills:
                if b.get("currency", "") in ["", "XXX"]:
                    b["currency"] = g.project.default_currency
                for a in attr:
                    if a not in b:
                        raise ValueError(
                            _("Missing attribute: %(attribute)s", attribute=a)
                        )
                currencies.add(b["currency"])

            if g.project.default_currency == CurrencyConverter.no_currency:
                if len(currencies - {CurrencyConverter.no_currency}) >= 2:
                    raise ValueError(
                        _(
                            "Cannot add bills in multiple currencies to a project without default "
                            "currency"
                        )
                    )
                for b in bills:
                    b["currency"] = CurrencyConverter.no_currency

            g.project.import_bills(bills)

            flash(_("Project successfully uploaded"))
            return redirect(url_for("main.list_bills"))
        except ValueError as b:
            flash(b.args[0], category="danger")
    else:
        for component, errors in form.errors.items():
            flash(component + ": " + ", ".join(errors), category="danger")
    return redirect(request.headers.get("Referer") or url_for(".edit_project"))


@main.route("/<project_id>/delete", methods=["POST"])
def delete_project():
    form = DestructiveActionProjectForm(id=g.project.id)
    if form.validate():
        g.project.remove_project()
        flash(_("Project successfully deleted"))
        return redirect(url_for(".home"))
    else:
        flash(
            format_form_errors(form, _("Error deleting project")),
            category="danger",
        )
    return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/<project_id>/export/<string:file>.<string:format>")
def export_project(file, format):
    if file == "transactions":
        export = g.project.get_transactions_to_settle_bill(pretty_output=True)
    elif file == "bills":
        export = g.project.get_pretty_bills(export_format=format)
    else:
        abort(404, "No such export type")

    if format == "json":
        file2export = list_of_dicts2json(export)
    elif format == "csv":
        file2export = list_of_dicts2csv(export)
    else:
        abort(404, "No such export format")

    return send_file(
        file2export,
        download_name=f"{g.project.id}-{file}.{format}",
        as_attachment=True,
    )


@main.route("/exit", methods=["GET", "POST"])
def exit():
    if request.method == "GET":
        abort(405)

    form = LogoutForm()
    if form.validate():
        session.clear()
        return redirect(url_for(".home"))
    else:
        flash(
            format_form_errors(form, _("Unable to logout")),
            category="danger",
        )
        return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/demo")
def demo():
    is_demo_project_activated = current_app.config["ACTIVATE_DEMO_PROJECT"]
    project = Project.query.get("demo")

    if not project and not is_demo_project_activated:
        raise Redirect303(url_for(".create_project", project_id="demo"))
    if not project and is_demo_project_activated:
        project = Project.create_demo_project()
    session[project.id] = True
    return redirect(url_for(".list_bills", project_id=project.id))


@main.route("/<project_id>/invite", methods=["GET", "POST"])
def invite():

    form = InviteForm()

    if request.method == "POST":
        if form.validate():
            message_body = render_localized_template("invitation_mail")
            message_title = _(
                "You have been invited to share your expenses for %(project)s",
                project=g.project.name,
            )
            msg = Message(
                message_title,
                body=message_body,
                recipients=[email.strip() for email in form.emails.data.split(",")],
            )
            success = send_email(msg)
            if success:
                flash(_("Your invitations have been sent"), category="success")
                return redirect(url_for(".list_bills"))
            else:
                flash_email_error(
                    _(
                        "Sorry, there was an error while trying to send the invitation emails."
                    )
                )

    invite_link = url_for(
        ".join_project",
        project_id=g.project.id,
        token=g.project.generate_token(),
        _external=True,
    )
    invite_link = urlunparse(urlparse(invite_link)._replace(scheme="ihatemoney"))
    qr = qrcode.QRCode(image_factory=qrcode.image.svg.SvgPathImage)
    qr.add_data(invite_link)
    qr.make(fit=True)
    img = qr.make_image(attrib={"class": "qrcode"})
    qrcode_svg = img.to_string().decode()

    return render_template("send_invites.html", form=form, qrcode=qrcode_svg)


@main.route("/<project_id>/")
def list_bills():
    bill_form = get_billform_for(g.project)
    csrf_form = EmptyForm()
    if "last_selected_payer_per_project" in session:
        if g.project.id in session["last_selected_payer_per_project"]:
            bill_form.payer.data = session["last_selected_payer_per_project"][
                g.project.id
            ]
    else:
        if "last_selected_payer" in session:
            bill_form.payer.data = session["last_selected_payer"]
    if (
        "last_selected_payed_for" in session
        and g.project.id in session["last_selected_payed_for"]
    ):
        bill_form.payed_for.data = session["last_selected_payed_for"][g.project.id]

    weighted_bills = g.project.get_bill_weights_ordered().paginate(
        per_page=100, error_out=True
    )

    return render_template(
        "list_bills.html",
        bills=weighted_bills,
        member_form=MemberForm(g.project),
        bill_form=bill_form,
        csrf_form=csrf_form,
        add_bill=request.values.get("add_bill", False),
        current_view="list_bills",
    )


@main.route("/<project_id>/members/add", methods=["GET", "POST"])
def add_member():
    form = MemberForm(g.project)
    if request.method == "POST":
        if form.validate():
            member = form.save(g.project, Person())
            db.session.commit()
            flash(_("%(member)s has been added", member=member.name))
            return redirect(url_for(".list_bills"))

    return render_template("add_member.html", form=form)


@main.route("/<project_id>/members/<member_id>/reactivate", methods=["POST"])
def reactivate(member_id):
    form = EmptyForm()
    if not form.validate():
        flash(
            format_form_errors(form, _("Error activating participant")),
            category="danger",
        )
        return redirect(url_for(".list_bills"))

    person = (
        Person.query.filter(Person.id == member_id)
        .filter(Project.id == g.project.id)
        .all()
    )
    if person:
        person[0].activated = True
        db.session.commit()
        flash(_("%(name)s is part of this project again", name=person[0].name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/delete", methods=["POST"])
def remove_member(member_id):
    form = EmptyForm()
    if not form.validate():
        flash(
            format_form_errors(form, _("Error removing participant")), category="danger"
        )
        return redirect(url_for(".list_bills"))

    member = g.project.remove_member(member_id)
    if member:
        if not member.activated:
            flash(
                _(
                    "Participant '%(name)s' has been deactivated. It will still "
                    "appear in the list until its balance reach zero.",
                    name=member.name,
                )
            )
        else:
            flash(_("Participant '%(name)s' has been removed", name=member.name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/edit", methods=["POST", "GET"])
def edit_member(member_id):
    member = Person.query.get(member_id, g.project)
    if not member:
        raise NotFound()
    form = MemberForm(g.project, edit=True)

    if request.method == "POST" and form.validate():
        form.save(g.project, member)
        db.session.commit()
        flash(_("Participant '%(name)s' has been modified", name=member.name))
        return redirect(url_for(".list_bills"))

    form.fill(member)
    return render_template("edit_member.html", form=form, edit=True)


@main.route("/<project_id>/add", methods=["GET", "POST"])
def add_bill():
    form = get_billform_for(g.project)
    if request.method == "POST":
        if form.validate():
            if "last_selected_payer_per_project" not in session:
                session["last_selected_payer_per_project"] = {}
            session["last_selected_payer_per_project"][g.project.id] = form.payer.data
            if "last_selected_payed_for" not in session:
                session["last_selected_payed_for"] = {}
            session["last_selected_payed_for"][g.project.id] = form.payed_for.data
            session.update()

            db.session.add(form.export(g.project))
            db.session.commit()

            flash(_("The bill has been added"))

            args = {}
            if form.submit2.data:
                args["add_bill"] = True

            return redirect(url_for(".list_bills", **args))

    return render_template("add_bill.html", form=form)


@main.route("/<project_id>/delete/<int:bill_id>", methods=["POST"])
def delete_bill(bill_id):
    form = EmptyForm()
    if not form.validate():
        flash(format_form_errors(form, _("Error deleting bill")), category="danger")
        return redirect(url_for(".list_bills"))

    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        return redirect(url_for(".list_bills"))

    db.session.delete(bill)
    db.session.commit()
    flash(_("The bill has been deleted"))

    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
def edit_bill(bill_id):
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise NotFound()

    form = get_billform_for(g.project, set_default=False)

    if request.method == "POST" and form.validate():
        form.save(bill, g.project)
        db.session.commit()

        flash(_("The bill has been modified"))
        return redirect(url_for(".list_bills"))

    if not form.errors:
        form.fill(bill, g.project)

    return render_template("add_bill.html", form=form, edit=True)


@main.route("/lang/<lang>")
def change_lang(lang):
    if lang in current_app.config["SUPPORTED_LANGUAGES"]:
        session["lang"] = lang
        session.update()
    else:
        flash(
            _("%(lang)s is not a supported language", lang=lang),
            category="warning",
        )

    return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/<project_id>/settle_bills")
def settle_bill():
    transactions = g.project.get_transactions_to_settle_bill()
    settlement_form = SettlementForm()
    return render_template(
        "settle_bills.html",
        transactions=transactions,
        settlement_form=settlement_form,
        current_view="settle_bill",
    )


@main.route("/<project_id>/settle", methods=["POST"])
def add_settlement_bill():
    form = SettlementForm(id=g.project.id)
    if not form.validate():
        flash(
            format_form_errors(form, _("Error creating settlement bill")),
            category="danger",
        )
        return redirect(url_for(".settle_bill"))

    receiver_id = form.receiver_id.data
    sender_id = form.sender_id.data

    if not g.project.has_member(sender_id):
        return redirect(url_for(".settle_bill"))

    settlement = Bill(
        amount=form.amount.data,
        date=datetime.datetime.today(),
        owers=[Person.query.get(receiver_id, g.project)],
        payer_id=sender_id,
        project_default_currency=g.project.default_currency,
        bill_type=BillType.REIMBURSEMENT,
        what=_("Settlement"),
    )
    session.update()

    db.session.add(settlement)
    db.session.commit()

    flash(_("Settlement bill has been successfully added"), category="success")
    return redirect(url_for(".settle_bill"))


@main.route("/<project_id>/history")
def history():
    history = get_history(g.project, human_readable_names=True)

    any_ip_addresses = any(event["ip"] for event in history)

    delete_form = DestructiveActionProjectForm()
    return render_template(
        "history.html",
        current_view="history",
        history=history,
        any_ip_addresses=any_ip_addresses,
        LoggingMode=LoggingMode,
        OperationType=Operation,
        current_log_pref=g.project.logging_preference,
        delete_form=delete_form,
    )


@main.route("/<project_id>/erase_history", methods=["POST"])
def erase_history():
    form = DestructiveActionProjectForm(id=g.project.id)
    if not form.validate():
        flash(
            format_form_errors(form, _("Error deleting project history")),
            category="danger",
        )
        return redirect(url_for(".history"))

    purge_history(g.project)

    db.session.commit()
    flash(_("Deleted project history."))
    return redirect(url_for(".history"))


@main.route("/<project_id>/strip_ip_addresses", methods=["POST"])
def strip_ip_addresses():
    form = DestructiveActionProjectForm(id=g.project.id)
    if not form.validate():
        flash(
            format_form_errors(form, _("Error deleting recorded IP addresses")),
            category="danger",
        )
        return redirect(url_for(".history"))

    for query in get_history_queries(g.project):
        for version_object in query.all():
            version_object.transaction.remote_addr = None

    db.session.commit()
    flash(_("Deleted recorded IP addresses in project history."))
    return redirect(url_for(".history"))


@main.route("/<project_id>/statistics")
def statistics():
    months = g.project.active_months_range()
    return render_template(
        "statistics.html",
        members_stats=g.project.members_stats,
        monthly_stats=g.project.monthly_stats,
        months=months,
        current_view="statistics",
    )


def build_etag(project_id, last_modified):
    return hashlib.md5(
        (current_app.config["SECRET_KEY"] + project_id + last_modified).encode()
    ).hexdigest()


@main.route("/<project_id>/feed/<string:token>.xml")
def feed(token):
    verified_project_id = Project.verify_token(
        token, token_type="feed", project_id=g.project.id
    )
    if verified_project_id != g.project.id:
        abort(404)

    weighted_bills = g.project.get_bill_weights_ordered().paginate(
        per_page=100, error_out=True
    )

    bills_last_modified = [
        bill.versions[0].transaction.issued_at for _, bill in weighted_bills.items
    ]
    project_last_modified = g.project.versions[0].transaction.issued_at
    last_modified = max(bills_last_modified + [project_last_modified])
    etag = build_etag(g.project.id, last_modified.isoformat())

    if request.if_none_match and etag in request.if_none_match:
        return "", 304

    if (
        request.if_modified_since
        and request.if_modified_since.replace(tzinfo=None) >= last_modified
    ):
        return "", 304

    return Response(
        render_template("project_feed.xml", bills=weighted_bills),
        mimetype="application/rss+xml",
        headers={
            "ETag": etag,
            "Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S UTC"),
        },
    )


@main.route("/dashboard")
@requires_admin()
def dashboard():
    is_admin_dashboard_activated = current_app.config["ACTIVATE_ADMIN_DASHBOARD"]
    return render_template(
        "dashboard.html",
        projects=Project.query.all(),
        delete_project_form=DestructiveActionProjectForm,
        is_admin_dashboard_activated=is_admin_dashboard_activated,
    )


@main.route("/dashboard/<project_id>/delete", methods=["POST"])
@requires_admin()
def dashboard_delete_project():
    g.project.remove_project()
    flash(_("Project successfully deleted"))
    return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(main.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )
