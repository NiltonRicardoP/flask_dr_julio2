from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    current_app,
    request,
)
from datetime import datetime
import hmac
import hashlib
import json
from flask_mail import Message

from forms import (
    ContactForm,
    AppointmentForm,
    RescheduleForm,
    CancelAppointmentForm,
)
from appointments_api import create_pending_appointment
from availability_service import get_slot_config, is_slot_available
from google_calendar import upsert_appointment_event, cancel_appointment_event
from models import (
    db,
    Event,
    Appointment,
    Settings,
    Course,
    ContactMessage,
    SiteSection,
)

# Create a Blueprint for the main routes
main_bp = Blueprint("main_bp", __name__)


def _get_sections_for_page(page: str):
    sections = (
        SiteSection.query.filter_by(page=page, is_active=True)
        .order_by(SiteSection.sort_order.asc(), SiteSection.id.asc())
        .all()
    )
    return {section.slug: section for section in sections}


@main_bp.route("/")
def index():
    settings = Settings.query.first()
    upcoming_events = Event.get_upcoming_events()[:3]  # Limit to 3 events
    sections = _get_sections_for_page("index")
    return render_template(
        "index.html",
        settings=settings,
        events=upcoming_events,
        sections=sections,
    )


@main_bp.route("/about")
def about():
    settings = Settings.query.first()
    sections = _get_sections_for_page("about")
    return render_template("about.html", settings=settings, sections=sections)


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
    slot_config = get_slot_config()

    if form.validate_on_submit():
        try:
            appt = create_pending_appointment(
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data,
                date_s=form.date.data.strftime("%Y-%m-%d"),
                time_s=form.time.data.strftime("%H:%M"),
                reason=form.reason.data,
            )
            flash(
                "Consulta agendada com sucesso! Voce recebera uma confirmacao por email.",
                "success",
            )
            return redirect(url_for("main_bp.appointment_manage", token=appt.manage_token))
        except Exception as e:
            db.session.rollback()
            form.time.errors.append(str(e))

    return render_template(
        "appointment.html",
        form=form,
        settings=settings,
        slot_config=slot_config,
    )


@main_bp.route("/appointment/manage/<token>", methods=["GET", "POST"])
def appointment_manage(token):
    settings = Settings.query.first()
    slot_config = get_slot_config()
    appointment_item = Appointment.query.filter_by(manage_token=token).first_or_404()
    reschedule_form = RescheduleForm()
    cancel_form = CancelAppointmentForm()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        if action == "cancel" and cancel_form.validate_on_submit():
            if appointment_item.status not in ("cancelled", "canceled"):
                appointment_item.status = "cancelled"
                appointment_item.cancelled_at = datetime.utcnow()
                db.session.commit()
                cancel_appointment_event(appointment_item)
                flash("Agendamento cancelado com sucesso.", "success")
            else:
                flash("Agendamento ja esta cancelado.", "info")
            return redirect(url_for("main_bp.appointment_manage", token=token))

        if action == "reschedule" and reschedule_form.validate_on_submit():
            new_day = reschedule_form.date.data
            new_time = reschedule_form.time.data
            if appointment_item.status in ("cancelled", "canceled"):
                flash("Agendamento cancelado nao pode ser reagendado.", "warning")
            elif datetime.combine(new_day, new_time) < datetime.now():
                reschedule_form.time.errors.append("Data e horario nao podem ser no passado.")
            elif not is_slot_available(new_day, new_time, exclude_id=appointment_item.id):
                reschedule_form.time.errors.append("Horario indisponivel.")
            else:
                appointment_item.date = new_day
                appointment_item.time = new_time
                appointment_item.status = "pending"
                appointment_item.rescheduled_at = datetime.utcnow()
                appointment_item.reminder_sent_at = None
                db.session.commit()
                upsert_appointment_event(appointment_item)
                flash("Agendamento reagendado com sucesso.", "success")
                return redirect(url_for("main_bp.appointment_manage", token=token))

    return render_template(
        "appointment_manage.html",
        appointment=appointment_item,
        reschedule_form=reschedule_form,
        cancel_form=cancel_form,
        settings=settings,
        slot_config=slot_config,
    )


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


@main_bp.route("/courses/<int:id>/register")
def course_register(id):
    """Redirect legacy register route to external purchase link."""
    course = Course.query.get_or_404(id)
    if course.purchase_link:
        return redirect(course.purchase_link)
    return redirect(url_for("main_bp.course_page", id=id))


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

    mail = current_app.extensions.get("mail")
    if mail:
        try:
            body = f'Você agora tem acesso ao curso {course.title}. Link: {course.access_url or ""}'
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
