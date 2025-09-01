from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    current_app,
    request,
    send_from_directory,
    abort,
)
from flask_login import login_required, current_user, login_user
from datetime import datetime
import hmac
import hashlib
import secrets
import os
import json
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_mail import Message

from forms import (
    ContactForm,
    AppointmentForm,
)
from models import (
    db,
    Event,
    Appointment,
    Settings,
    Course,
    CourseEnrollment,
    ContactMessage,
    User,
)

# Create a Blueprint for the main routes
main_bp = Blueprint("main_bp", __name__)


def generate_media_token(path):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(path)


@main_bp.route("/media/<path:filename>")
@login_required
def media(filename):
    token = request.args.get("token", "")
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = serializer.loads(token, max_age=3600)
        if data != filename:
            abort(403)
    except (BadSignature, SignatureExpired):
        abort(403)
    course_id = filename.split("/")[0]
    if current_user.role != "admin":
        enrollment = CourseEnrollment.query.filter_by(
            course_id=course_id, user_id=current_user.id
        ).first()
        now = datetime.utcnow()
        if not enrollment or not (
            enrollment.access_start
            and enrollment.access_end
            and enrollment.access_start <= now <= enrollment.access_end
        ):
            abort(403)
    base_dir = current_app.config["COURSE_CONTENT_FOLDER"]
    return send_from_directory(base_dir, filename)


@main_bp.route("/")
def index():
    settings = Settings.query.first()
    upcoming_events = Event.get_upcoming_events()[:3]  # Limit to 3 events
    return render_template("index.html", settings=settings, events=upcoming_events)


@main_bp.route("/about")
def about():
    settings = Settings.query.first()
    return render_template("about.html", settings=settings)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    settings = Settings.query.first()

    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data,
        )
        try:
            db.session.add(message)
            db.session.commit()

            # Send email functionality would go here

            flash(
                "Sua mensagem foi enviada com sucesso! Entraremos em contato em breve.",
                "success",
            )
            return redirect(url_for("main_bp.contact"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocorreu um erro ao enviar sua mensagem: {str(e)}", "danger")

    return render_template("contact.html", form=form, settings=settings)


@main_bp.route("/appointment", methods=["GET", "POST"])
def appointment():
    form = AppointmentForm()
    settings = Settings.query.first()

    if form.validate_on_submit():
        new_appointment = Appointment(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            date=form.date.data,
            time=form.time.data,
            reason=form.reason.data,
            status="pending",
        )

        try:
            db.session.add(new_appointment)
            db.session.commit()

            # Send email notification functionality would go here

            flash(
                "Consulta agendada com sucesso! Você receberá uma confirmação por email.",
                "success",
            )
            return redirect(url_for("main_bp.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocorreu um erro ao agendar sua consulta: {str(e)}", "danger")

    return render_template("appointment.html", form=form, settings=settings)


@main_bp.route("/events")
def events():
    settings = Settings.query.first()
    upcoming_events = Event.get_upcoming_events()
    past_events = Event.get_past_events()
    return render_template(
        "events.html",
        settings=settings,
        upcoming_events=upcoming_events,
        past_events=past_events,
    )


@main_bp.route("/courses", endpoint="courses")
def list_courses():
    """List active courses ordered by creation date."""
    settings = Settings.query.first()
    courses = Course.query.filter_by(is_active=True).order_by(Course.created_at).all()
    return render_template("public_courses.html", courses=courses, settings=settings)


# New route listing active courses ordered by start_date
@main_bp.route("/active-courses")
def active_courses():
    """List upcoming courses using Course helper methods."""
    settings = Settings.query.first()
    courses = Course.get_upcoming_courses()
    return render_template("public_courses.html", courses=courses, settings=settings)


@main_bp.route("/cursos")
def cursos():
    """Portuguese alias for the courses page."""
    return list_courses()


@main_bp.route("/courses/<int:id>")
def course_page(id):
    """Show course details with a link to purchase."""
    course = Course.query.get_or_404(id)
    settings = Settings.query.first()
    return render_template(
        "public_course_detail.html", course=course, settings=settings
    )


@main_bp.route("/curso/acesso/<int:enrollment_id>")
@login_required
def course_access(enrollment_id):
    enrollment = CourseEnrollment.query.get_or_404(enrollment_id)
    if enrollment.user_id != current_user.id:
        flash("Você não tem permissão para acessar este curso.", "danger")
        return redirect(url_for("student_bp.dashboard"))
    if enrollment.payment_status != "paid":
        flash("Pagamento não identificado para esta inscrição.", "warning")
        return redirect(url_for("main_bp.course_page", id=enrollment.course_id))
    now = datetime.utcnow()
    if not (
        enrollment.access_start
        and enrollment.access_end
        and enrollment.access_start <= now <= enrollment.access_end
    ):
        flash("Seu acesso a este curso expirou ou ainda não foi liberado.", "warning")
        return redirect(url_for("student_bp.dashboard"))
    videos = []
    content_folder = current_app.config["COURSE_CONTENT_FOLDER"]
    course_folder = os.path.join(content_folder, str(enrollment.course_id))
    if os.path.isdir(course_folder):
        for fname in os.listdir(course_folder):
            if fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                path = f"{enrollment.course_id}/{fname}"
                token = generate_media_token(path)
                videos.append(url_for("main_bp.media", filename=path, token=token))
    return render_template("course_access.html", enrollment=enrollment, videos=videos)


@main_bp.route("/webhook/hotmart", methods=["POST"])
def hotmart_webhook():
    """Handle Hotmart purchase notifications."""
    secret = current_app.config.get("HOTMART_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-HOTMART-HMAC-SHA256", "")
    if not secret or not signature:
        current_app.logger.warning("Hotmart webhook missing credentials")
        return "Unauthorized", 403
    expected = hmac.new(secret.encode(), request.data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        current_app.logger.warning("Hotmart webhook invalid signature")
        return "Unauthorized", 403

    try:
        payload = json.loads(request.data.decode("utf-8") or "{}")
    except (ValueError, AttributeError):
        payload = {}
    status = payload.get("status")
    product_id = (
        payload.get("product_id")
        or payload.get("id")
        or payload.get("product", {}).get("id")
    )
    email = payload.get("email") or payload.get("buyer", {}).get("email")
    txn_id = (
        payload.get("transaction")
        or payload.get("transaction_id")
        or payload.get("purchase", {}).get("id")
    )

    current_app.logger.info(
        "Hotmart webhook received: status=%s product_id=%s email=%s transaction=%s",
        status,
        product_id,
        email,
        txn_id,
    )

    if not all([status, product_id, email, txn_id]):
        current_app.logger.warning("Hotmart webhook missing fields")
        return "Invalid payload", 400

    if status != "approved":
        current_app.logger.info(
            "Ignoring Hotmart transaction %s with status %s", txn_id, status
        )
        return "", 200

    course = Course.query.filter_by(id=product_id).first()
    if not course:
        current_app.logger.warning("Hotmart course %s not found", product_id)
        return "Course not found", 404

    user = User.query.filter_by(email=email).first()
    new_user = False
    temp_password = None
    if not user:
        username = email.split("@")[0]
        user = User(username=username, email=email, role="student")
        temp_password = secrets.token_urlsafe(8)
        user.set_password(temp_password)
        db.session.add(user)
        db.session.flush()
        new_user = True
        current_app.logger.info("Created user %s for transaction %s", user.id, txn_id)

    enrollment = CourseEnrollment.query.filter_by(
        course_id=course.id, user_id=user.id
    ).first()
    if not enrollment:
        enrollment = CourseEnrollment(
            course_id=course.id,
            user_id=user.id,
            name=user.username,
            email=email,
            payment_status="paid",
            transaction_id=txn_id,
        )
        db.session.add(enrollment)
        db.session.flush()
        current_app.logger.info(
            "Created enrollment %s for user %s", enrollment.id, user.id
        )
    else:
        enrollment.payment_status = "paid"
        enrollment.transaction_id = txn_id
        current_app.logger.info(
            "Updated enrollment %s for user %s", enrollment.id, user.id
        )
    if not enrollment.access_start:
        enrollment.activate_access()

    db.session.commit()

    mail = current_app.extensions.get("mail")
    if mail:
        try:
            login_link = url_for("student_bp.login", _external=True)
            body = f'Você agora tem acesso ao curso {course.title}. Link: {course.access_url or ""}'
            if new_user and temp_password:
                body += (
                    f"\n\nFaça login em {login_link} com o usuário {user.username} e a senha temporária {temp_password}. "
                    "Altere sua senha após o primeiro acesso."
                )
            else:
                body += f"\n\nAcesse {login_link} para entrar no curso."
            msg = Message(subject="Acesso ao curso", recipients=[email], body=body)
            mail.send(msg)
        except Exception:
            current_app.logger.exception(
                "Failed to send email for transaction %s", txn_id
            )

    return "", 200


# Public catalog of courses
@main_bp.route("/catalogo-cursos")
def course_catalog():
    """Display all active courses for visitors."""
    settings = Settings.query.first()
    courses = Course.query.filter_by(is_active=True).all()
    return render_template("course_catalog.html", courses=courses, settings=settings)


# Details of a single course without enrollment form
@main_bp.route("/catalogo-cursos/<int:course_id>")
def course_catalog_detail(course_id):
    """Show public details for a course."""
    course = Course.query.get_or_404(course_id)
    settings = Settings.query.first()
    return render_template(
        "course_catalog_detail.html", course=course, settings=settings
    )


@main_bp.route("/galeria")
def gallery():
    from models import GalleryItem  # (após criarmos a model)

    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    settings = Settings.query.first()
    return render_template("gallery.html", items=items, settings=settings)
