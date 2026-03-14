from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from datetime import datetime, date, timedelta
from sqlalchemy import or_
from flask_mail import Message
from flask_login import login_user, logout_user, current_user
from functools import wraps
from werkzeug.utils import secure_filename
import json
import os
from models import (
    GalleryItem,
    BillingRecord,
    Invoice,
    Convenio,
    Course,
    ContactMessage,
)
from forms import GalleryForm, BillingRecordForm, InvoiceForm, ConvenioForm, CourseForm
from forms import (
    LoginForm,
    EventForm,
    AppointmentForm,
    EmailTestForm,
    SettingsSystemForm,
    SettingsGoogleCalendarForm,
    GoogleCalendarSyncForm,
    GoogleCalendarResyncForm,
    GoogleCalendarTestForm,
    SettingsEmailForm,
    SettingsProfileForm,
    SettingsSocialForm,
    SettingsImageForm,
    SiteSectionForm,
    SiteSectionItemForm,
    SiteSectionSeedForm,
    PatientForm,
    PatientNoteForm,
)
from appointments_api import create_pending_appointment
from google_calendar import (
    sync_google_calendar,
    upsert_appointment_event,
    cancel_appointment_event,
    upsert_calendar_event,
    cancel_calendar_event,
)
from availability_service import get_working_hours, get_slot_minutes, is_slot_available
from models import (
    db,
    User,
    Event,
    Appointment,
    CalendarEvent,
    Settings,
    Course,
    SiteSection,
    SiteSectionItem,
    Patient,
    PatientNote,
)

# Create Blueprint for the admin routes
admin_bp = Blueprint('admin_bp', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso restrito aos administradores', 'danger')
            return redirect(url_for('admin_bp.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_bp.dashboard'))
        return redirect(url_for('main_bp.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('admin_bp.login'))

        login_user(user, remember=form.remember_me.data)
        if user.role == 'admin':
            return redirect(url_for('admin_bp.dashboard'))
        logout_user()
        flash('Acesso restrito aos administradores', 'danger')
        return redirect(url_for('admin_bp.login'))

    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))

@admin_bp.route('/')
@admin_required
def dashboard():
    # Get recent appointments
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()

    appointments_count = Appointment.query.count()
    events_count = Event.query.count()
    gallery_count = GalleryItem.query.count()

    # Get upcoming events
    upcoming_events = Event.get_upcoming_events()[:5]

    contacts_count = ContactMessage.query.count()
    recent_contacts = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                          appointments_count=appointments_count,
                          events_count=events_count,
                          gallery_count=gallery_count,
                          recent_appointments=recent_appointments,
                          upcoming_events=upcoming_events,
                          contacts_count=contacts_count,
                          recent_contacts=recent_contacts)

@admin_bp.route('/appointments')
@admin_required
def appointments():
    settings = _get_settings()
    sync_google_calendar(settings=settings)
    status = (request.args.get('status') or '').strip()
    query = Appointment.query
    if status:
        query = query.filter(Appointment.status == status)
    appointments = query.order_by(Appointment.date.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments, status=status)


@admin_bp.route('/calendar')
@admin_required
def calendar():
    settings = _get_settings()
    status = _calendar_sync_status(settings)
    sync_form = GoogleCalendarSyncForm()
    return render_template(
        'admin/calendar.html',
        settings=settings,
        status=status,
        sync_form=sync_form,
    )


@admin_bp.route('/api/calendar/events', methods=['GET'])
@admin_required
def calendar_events():
    settings = _get_settings()
    status = _calendar_sync_status(settings)
    if status.get("ready"):
        sync_google_calendar(settings=settings, force=False)

    start = _parse_iso_datetime(request.args.get("start"))
    end = _parse_iso_datetime(request.args.get("end"))

    show_appointments = (request.args.get("appointments") or "1") == "1"
    show_manual = (request.args.get("manual") or "1") == "1"
    show_cancelled = (request.args.get("cancelled") or "0") == "1"

    items = []
    if show_appointments:
        appt_query = Appointment.query
        if start and end:
            appt_query = appt_query.filter(
                Appointment.date >= start.date(),
                Appointment.date <= end.date(),
            )
        if not show_cancelled:
            appt_query = appt_query.filter(~Appointment.status.in_(["cancelled", "canceled"]))
        duration = int(current_app.config.get("GOOGLE_APPT_DURATION_MINUTES", 50) or 50)
        for appt in appt_query.all():
            items.append(_appointment_to_calendar_item(appt, duration))

    if show_manual:
        evt_query = CalendarEvent.query
        if start and end:
            evt_query = evt_query.filter(
                CalendarEvent.start_at < end,
                CalendarEvent.end_at > start,
            )
        if not show_cancelled:
            evt_query = evt_query.filter(CalendarEvent.status != "cancelled")
        for evt in evt_query.all():
            items.append(_event_to_calendar_item(evt))

    return current_app.response_class(
        response=json.dumps(items),
        status=200,
        mimetype='application/json',
    )


@admin_bp.route('/api/calendar/events', methods=['POST'])
@admin_required
def calendar_event_create():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return current_app.response_class(
            response=json.dumps({"ok": False, "error": "Titulo e obrigatorio."}),
            status=400,
            mimetype='application/json',
        )

    start_dt = _parse_iso_datetime(data.get("start"))
    end_dt = _parse_iso_datetime(data.get("end"))
    all_day = bool(data.get("allDay"))
    if not start_dt:
        return current_app.response_class(
            response=json.dumps({"ok": False, "error": "Data de inicio invalida."}),
            status=400,
            mimetype='application/json',
        )

    if not end_dt or end_dt <= start_dt:
        if all_day:
            end_dt = start_dt + timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(minutes=60)

    evt = CalendarEvent(
        title=title,
        description=(data.get("description") or "").strip() or None,
        start_at=start_dt,
        end_at=end_dt,
        all_day=all_day,
        status="active",
        source="system",
    )
    db.session.add(evt)
    db.session.commit()

    settings = _get_settings()
    sync_ok = upsert_calendar_event(evt, settings=settings)

    payload = _event_to_calendar_item(evt)
    payload["sync_ok"] = sync_ok
    return current_app.response_class(
        response=json.dumps(payload),
        status=201,
        mimetype='application/json',
    )


@admin_bp.route('/api/calendar/events/<int:event_id>', methods=['PUT'])
@admin_required
def calendar_event_update(event_id):
    data = request.get_json(silent=True) or {}
    evt = CalendarEvent.query.get_or_404(event_id)

    title = (data.get("title") or "").strip()
    if title:
        evt.title = title
    description = (data.get("description") or "").strip()
    evt.description = description or None

    start_dt = _parse_iso_datetime(data.get("start"))
    end_dt = _parse_iso_datetime(data.get("end"))
    all_day = bool(data.get("allDay"))

    if start_dt:
        evt.start_at = start_dt
    if end_dt:
        if end_dt <= evt.start_at:
            evt.end_at = evt.start_at + (timedelta(days=1) if all_day else timedelta(minutes=60))
        else:
            evt.end_at = end_dt
    elif evt.end_at <= evt.start_at:
        evt.end_at = evt.start_at + (timedelta(days=1) if all_day else timedelta(minutes=60))

    evt.all_day = all_day
    if evt.status != "active":
        evt.status = "active"

    db.session.commit()

    settings = _get_settings()
    sync_ok = upsert_calendar_event(evt, settings=settings)

    payload = _event_to_calendar_item(evt)
    payload["sync_ok"] = sync_ok
    return current_app.response_class(
        response=json.dumps(payload),
        status=200,
        mimetype='application/json',
    )


@admin_bp.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
@admin_required
def calendar_event_delete(event_id):
    evt = CalendarEvent.query.get_or_404(event_id)
    evt.status = "cancelled"
    db.session.commit()

    settings = _get_settings()
    cancel_calendar_event(evt, settings=settings)

    return current_app.response_class(
        response=json.dumps({"ok": True}),
        status=200,
        mimetype='application/json',
    )


@admin_bp.route('/appointments/add', methods=['GET', 'POST'])
@admin_required
def add_appointment():
    form = AppointmentForm()
    if form.validate_on_submit():
        try:
            create_pending_appointment(
                name=form.name.data.strip(),
                email=form.email.data.strip(),
                phone=form.phone.data.strip(),
                date_s=form.date.data.strftime("%Y-%m-%d"),
                time_s=form.time.data.strftime("%H:%M"),
                reason=form.reason.data.strip(),
            )
            flash('Agendamento criado com sucesso.', 'success')
            return redirect(url_for('admin_bp.appointments'))
        except ValueError as exc:
            form.time.errors.append(str(exc))
    return render_template('admin/appointment_form.html', form=form, title='Novo Agendamento')

@admin_bp.route('/patients')
@admin_required
def patients():
    search = (request.args.get('q') or '').strip()
    query = Patient.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Patient.name.ilike(like),
                Patient.email.ilike(like),
                Patient.phone.ilike(like),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).all()
    return render_template('admin/patients.html', patients=patients, search=search)


@admin_bp.route('/patients/add', methods=['GET', 'POST'])
@admin_required
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient(
            name=form.name.data.strip(),
            email=form.email.data.strip() if form.email.data else None,
            phone=form.phone.data.strip() if form.phone.data else None,
            birth_date=form.birth_date.data,
            notes=form.notes.data.strip() if form.notes.data else None,
        )
        db.session.add(patient)
        db.session.commit()
        flash('Paciente criado com sucesso.', 'success')
        return redirect(url_for('admin_bp.patients'))
    return render_template('admin/patient_form.html', form=form, title='Novo Paciente')


@admin_bp.route('/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@admin_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = PatientForm(obj=patient)
    if form.validate_on_submit():
        patient.name = form.name.data.strip()
        patient.email = form.email.data.strip() if form.email.data else None
        patient.phone = form.phone.data.strip() if form.phone.data else None
        patient.birth_date = form.birth_date.data
        patient.notes = form.notes.data.strip() if form.notes.data else None
        db.session.commit()
        flash('Paciente atualizado com sucesso.', 'success')
        return redirect(url_for('admin_bp.patients'))
    return render_template('admin/patient_form.html', form=form, title='Editar Paciente', patient=patient)


@admin_bp.route('/patients/<int:patient_id>', methods=['GET', 'POST'])
@admin_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    note_form = PatientNoteForm()
    if note_form.validate_on_submit():
        note = PatientNote(
            patient_id=patient.id,
            title=note_form.title.data.strip() if note_form.title.data else None,
            content=note_form.content.data.strip(),
        )
        db.session.add(note)
        db.session.commit()
        flash('Nota adicionada com sucesso.', 'success')
        return redirect(url_for('admin_bp.patient_detail', patient_id=patient.id))
    return render_template('admin/patient_detail.html', patient=patient, note_form=note_form)


@admin_bp.route('/patients/delete/<int:patient_id>', methods=['POST'])
@admin_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash('Paciente removido com sucesso.', 'success')
    return redirect(url_for('admin_bp.patients'))


@admin_bp.route('/patients/<int:patient_id>/notes/<int:note_id>/delete', methods=['POST'])
@admin_required
def delete_patient_note(patient_id, note_id):
    note = PatientNote.query.filter_by(id=note_id, patient_id=patient_id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    flash('Nota removida com sucesso.', 'success')
    return redirect(url_for('admin_bp.patient_detail', patient_id=patient_id))




@admin_bp.route('/appointment/<int:id>/status/<status>')
@admin_required
def update_appointment_status(id, status):
    appointment = Appointment.query.get_or_404(id)
    
    if status in ['pending', 'confirmed', 'cancelled']:
        appointment.status = status
        if status == 'cancelled':
            appointment.cancelled_at = datetime.utcnow()
        else:
            appointment.cancelled_at = None
        db.session.commit()
        if status == 'cancelled':
            cancel_appointment_event(appointment)
        else:
            upsert_appointment_event(appointment)
        flash('Status do agendamento atualizado com sucesso!', 'success')
    else:
        flash('Status inválido', 'danger')
        
    return redirect(url_for('admin_bp.appointments'))

@admin_bp.route('/events')
@admin_required
def events():
    events = Event.query.order_by(Event.start_date.desc()).all()
    return render_template('admin/events.html', events=events)

@admin_bp.route('/events/add', methods=['GET', 'POST'])
@admin_required
def add_event():
    form = EventForm()
    
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
        event = Event(
            title=form.title.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            location=form.location.data,
            image=filename,
            is_active=form.is_active.data
        )
        
        db.session.add(event)
        db.session.commit()
        flash('Evento adicionado com sucesso!', 'success')
        return redirect(url_for('admin_bp.events'))
        
    return render_template('admin/event_form.html', form=form, title='Adicionar Evento')

@admin_bp.route('/events/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_event(id):
    event = Event.query.get_or_404(id)
    form = EventForm(obj=event)
    
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.start_date = form.start_date.data
        event.end_date = form.end_date.data
        event.location = form.location.data
        event.is_active = form.is_active.data
        
        if form.image.data:
            if event.image:
                # Delete old image
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], event.image))
                except:
                    pass
                    
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            event.image = filename
            
        db.session.commit()
        flash('Evento atualizado com sucesso!', 'success')
        return redirect(url_for('admin_bp.events'))
        
    return render_template('admin/event_form.html', form=form, title='Editar Evento')

def _get_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    return settings


def _read_service_account_email(creds_path: str | None) -> str | None:
    if not creds_path:
        return None
    try:
        with open(creds_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        value = data.get("client_email")
        return value.strip() if isinstance(value, str) and value.strip() else None
    except Exception:
        return None


def _calendar_sync_status(settings: Settings) -> dict:
    creds_path = (current_app.config.get("GOOGLE_CREDENTIALS_FILE") or "").strip()
    creds_exists = bool(creds_path) and os.path.exists(creds_path)
    calendar_id_db = (settings.google_calendar_id or "").strip() if settings else ""
    calendar_id_env = (current_app.config.get("GOOGLE_CALENDAR_ID") or "").strip()
    calendar_id = calendar_id_db or calendar_id_env
    calendar_source = "db" if calendar_id_db else ("env" if calendar_id_env else "none")
    tz = current_app.config.get("GOOGLE_CALENDAR_TZ", "America/Sao_Paulo")
    duration = current_app.config.get("GOOGLE_APPT_DURATION_MINUTES", 50)
    min_interval = current_app.config.get("GOOGLE_SYNC_MIN_INTERVAL_MIN", 2)
    service_email = _read_service_account_email(creds_path)
    ready = bool(settings.google_sync_enabled and calendar_id and creds_exists)
    return {
        "creds_path": creds_path,
        "creds_exists": creds_exists,
        "creds_display": os.path.basename(creds_path) if creds_path else "",
        "calendar_id": calendar_id,
        "calendar_source": calendar_source,
        "tz": tz,
        "duration": duration,
        "min_interval": min_interval,
        "service_email": service_email,
        "ready": ready,
    }


def _calendar_missing_requirements(settings: Settings, status: dict) -> list[str]:
    missing = []
    if not settings.google_sync_enabled:
        missing.append("ativar sincronizacao")
    if not status.get("calendar_id"):
        missing.append("definir o Google Calendar ID")
    if not status.get("creds_exists"):
        missing.append("configurar o arquivo de credenciais")
    return missing


def _iter_day_slots(day: date):
    start, end = get_working_hours()
    slot_minutes = get_slot_minutes()
    cur = datetime.combine(day, start)
    end_dt = datetime.combine(day, end)
    while cur < end_dt:
        yield cur.time()
        cur += timedelta(minutes=slot_minutes)


def _find_next_available_slot(days: int = 14):
    start_day = date.today() + timedelta(days=1)
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        for slot_time in _iter_day_slots(day):
            if is_slot_available(day, slot_time):
                return day, slot_time
    return None, None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _appointment_color(status: str | None) -> str:
    status = (status or "").lower()
    if status == "confirmed":
        return "#10b981"
    if status in ("cancelled", "canceled"):
        return "#6b7280"
    return "#f59e0b"


def _calendar_event_color(status: str | None, source: str | None) -> str:
    status = (status or "").lower()
    if status == "cancelled":
        return "#6b7280"
    if (source or "").lower() == "google":
        return "#38bdf8"
    return "#14b8a6"


def _event_to_calendar_item(item: CalendarEvent) -> dict:
    color = _calendar_event_color(item.status, item.source)
    return {
        "id": f"evt-{item.id}",
        "title": item.title,
        "start": item.start_at.isoformat(),
        "end": item.end_at.isoformat() if item.end_at else None,
        "allDay": bool(item.all_day),
        "editable": item.status != "cancelled",
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "#0b1120" if item.status != "cancelled" else "#e5e7eb",
        "extendedProps": {
            "kind": "calendar_event",
            "item_id": item.id,
            "status": item.status,
            "source": item.source,
            "description": item.description or "",
        },
    }


def _appointment_to_calendar_item(appointment: Appointment, duration_minutes: int) -> dict:
    start_dt = datetime.combine(appointment.date, appointment.time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    color = _appointment_color(appointment.status)
    return {
        "id": f"appt-{appointment.id}",
        "title": f"Consulta - {appointment.name}",
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "allDay": False,
        "editable": False,
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "#0b1120" if appointment.status != "cancelled" else "#e5e7eb",
        "extendedProps": {
            "kind": "appointment",
            "item_id": appointment.id,
            "status": appointment.status,
            "phone": appointment.phone,
            "email": appointment.email,
            "reason": appointment.reason,
        },
    }


def _seed_site_sections():
    defaults = [
        {
            "page": "index",
            "slug": "index-hero",
            "title": "DR. JULIO\nVASCONCELOS",
            "subtitle": "Neuropsicologia",
            "sort_order": 0,
            "is_active": True,
            "items": [],
        },
        {
            "page": "index",
            "slug": "index-about",
            "title": "Sobre",
            "subtitle": None,
            "sort_order": 10,
            "is_active": True,
            "items": [
                {
                    "title": "Formacao",
                    "body": "Psicologo, especialista em Neuropsicologia pela Santa Casa de Misericordia do RJ",
                    "icon": "fas fa-graduation-cap",
                    "sort_order": 0,
                },
                {
                    "title": "Especialidades",
                    "body": "Transtornos do Neurodesenvolvimento (Autismo, TDAH)",
                    "icon": "fas fa-brain",
                    "sort_order": 1,
                },
                {
                    "title": "Publico Atendido",
                    "body": "Criancas, Adolescentes e Adultos",
                    "icon": "fas fa-users",
                    "sort_order": 2,
                },
                {
                    "title": "Atuacao Profissional",
                    "body": "Alem da clinica, atua no campo da pesquisa e docencia em cursos presenciais e a distancia",
                    "icon": "fas fa-book",
                    "sort_order": 3,
                },
            ],
        },
        {
            "page": "index",
            "slug": "index-services",
            "title": "Servicos",
            "subtitle": None,
            "sort_order": 20,
            "is_active": True,
            "items": [
                {
                    "title": "Avaliacao Neuropsicologica",
                    "body": "Avaliacao completa das funcoes cognitivas, comportamentais e emocionais.",
                    "icon": "fas fa-clipboard-check",
                    "sort_order": 0,
                },
                {
                    "title": "Psicoterapia",
                    "body": "Atendimento psicologico individualizado com abordagem integrativa.",
                    "icon": "fas fa-comments",
                    "sort_order": 1,
                },
                {
                    "title": "Palestras e Workshops",
                    "body": "Eventos educativos sobre temas relacionados a neuropsicologia e saude mental.",
                    "icon": "fas fa-chalkboard-teacher",
                    "sort_order": 2,
                },
            ],
        },
        {
            "page": "about",
            "slug": "about-areas",
            "title": "Areas de Atuacao",
            "subtitle": None,
            "sort_order": 0,
            "is_active": True,
            "items": [
                {
                    "title": "Neuropsicologia",
                    "body": "Avaliacao e reabilitacao neuropsicologica para criancas, adolescentes e adultos.",
                    "icon": "fas fa-brain",
                    "sort_order": 0,
                },
                {
                    "title": "Psicologia Clinica",
                    "body": "Atendimento psicologico com abordagem integrativa para diversas questoes emocionais e comportamentais.",
                    "icon": "fas fa-comments",
                    "sort_order": 1,
                },
                {
                    "title": "Docencia",
                    "body": "Atuacao como professor e palestrante em cursos de graduacao e pos-graduacao em Psicologia.",
                    "icon": "fas fa-chalkboard-teacher",
                    "sort_order": 2,
                },
            ],
        },
    ]
    created_sections = 0
    created_items = 0

    for data in defaults:
        section = SiteSection.query.filter_by(slug=data["slug"]).first()
        created = False
        if not section:
            section = SiteSection(
                page=data["page"],
                slug=data["slug"],
                title=data["title"],
                subtitle=data["subtitle"],
                sort_order=data["sort_order"],
                is_active=data["is_active"],
            )
            db.session.add(section)
            db.session.flush()
            created_sections += 1
            created = True

        items = data["items"]
        if items:
            has_items = SiteSectionItem.query.filter_by(section_id=section.id).count() > 0
            if created or not has_items:
                for item in items:
                    db.session.add(
                        SiteSectionItem(
                            section_id=section.id,
                            title=item["title"],
                            body=item["body"],
                            icon=item["icon"],
                            sort_order=item["sort_order"],
                            is_active=True,
                        )
                    )
                    created_items += 1

    db.session.commit()
    return created_sections, created_items


@admin_bp.route('/settings')
@admin_required
def settings():
    return redirect(url_for('admin_bp.settings_system'))


@admin_bp.route('/settings/system', methods=['GET', 'POST'])
@admin_required
def settings_system():
    settings = _get_settings()
    form = SettingsSystemForm(obj=settings)

    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings_system'))

    return render_template('admin/settings_system.html', form=form, settings=settings)


@admin_bp.route('/settings/google-calendar', methods=['GET', 'POST'])
@admin_required
def settings_google_calendar():
    settings = _get_settings()
    form = SettingsGoogleCalendarForm(obj=settings)
    sync_form = GoogleCalendarSyncForm()
    resync_form = GoogleCalendarResyncForm()
    test_form = GoogleCalendarTestForm()

    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('Configuracoes atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    status = _calendar_sync_status(settings)
    today = date.today()

    upcoming_appointments = (
        Appointment.query
        .filter(Appointment.date >= today)
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .limit(10)
        .all()
    )

    sync_candidates = Appointment.query.filter(
        Appointment.date >= today,
        Appointment.status.in_(["pending", "confirmed"]),
    )
    sync_total = sync_candidates.count()
    sync_synced = sync_candidates.filter(Appointment.google_event_id.isnot(None)).count()
    sync_unsynced = max(0, sync_total - sync_synced)

    return render_template(
        'admin/google_calendar.html',
        form=form,
        sync_form=sync_form,
        resync_form=resync_form,
        test_form=test_form,
        settings=settings,
        status=status,
        upcoming_appointments=upcoming_appointments,
        sync_total=sync_total,
        sync_synced=sync_synced,
        sync_unsynced=sync_unsynced,
    )


@admin_bp.route('/settings/google-calendar/sync', methods=['POST'])
@admin_required
def google_calendar_sync():
    form = GoogleCalendarSyncForm()
    if not form.validate_on_submit():
        flash('Solicitacao invalida.', 'danger')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    settings = _get_settings()
    status = _calendar_sync_status(settings)
    missing = _calendar_missing_requirements(settings, status)
    if missing:
        flash('Sincronizacao nao configurada: ' + ', '.join(missing) + '.', 'warning')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    ok = sync_google_calendar(settings=settings, force=True)
    if ok:
        flash('Sincronizacao concluida com sucesso.', 'success')
    else:
        flash('Nao foi possivel sincronizar agora. Verifique as credenciais.', 'warning')
    return redirect(url_for('admin_bp.settings_google_calendar'))


@admin_bp.route('/settings/google-calendar/resync', methods=['POST'])
@admin_required
def google_calendar_resync():
    form = GoogleCalendarResyncForm()
    if not form.validate_on_submit():
        flash('Solicitacao invalida.', 'danger')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    settings = _get_settings()
    status = _calendar_sync_status(settings)
    missing = _calendar_missing_requirements(settings, status)
    if missing:
        flash('Sincronizacao nao configurada: ' + ', '.join(missing) + '.', 'warning')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    days = form.days.data or 30
    days = max(1, min(180, days))
    today = date.today()
    end_day = today + timedelta(days=days)

    appts = (
        Appointment.query
        .filter(Appointment.date >= today, Appointment.date <= end_day)
        .filter(Appointment.status.in_(["pending", "confirmed"]))
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .all()
    )

    if not appts:
        flash('Nenhum agendamento encontrado no periodo informado.', 'info')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    updated = 0
    for appt in appts:
        if upsert_appointment_event(appt, settings=settings):
            updated += 1

    if updated:
        flash(f'Reenvio concluido: {updated}/{len(appts)} eventos atualizados.', 'success')
    else:
        flash('Nao foi possivel reenviar eventos no periodo.', 'warning')
    return redirect(url_for('admin_bp.settings_google_calendar'))


@admin_bp.route('/settings/google-calendar/test', methods=['POST'])
@admin_required
def google_calendar_test():
    form = GoogleCalendarTestForm()
    if not form.validate_on_submit():
        flash('Solicitacao invalida.', 'danger')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    settings = _get_settings()
    status = _calendar_sync_status(settings)
    missing = _calendar_missing_requirements(settings, status)
    if missing:
        flash('Sincronizacao nao configurada: ' + ', '.join(missing) + '.', 'warning')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    day, slot_time = _find_next_available_slot()
    if not day or not slot_time:
        flash('Nao encontrei horario disponivel para o teste. Tente novamente mais tarde.', 'warning')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    email = settings.admin_notify_email or settings.contact_email or 'teste@drjulio.com'
    try:
        appt = create_pending_appointment(
            name='Teste Google Agenda',
            phone='21999999999',
            email=email,
            date_s=day.strftime('%Y-%m-%d'),
            time_s=slot_time.strftime('%H:%M'),
            reason='Teste automatico de sincronizacao.',
        )
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin_bp.settings_google_calendar'))

    if appt.google_event_id:
        flash(
            f'Agendamento de teste criado (ID {appt.id}) em {day.strftime("%d/%m/%Y")} {slot_time.strftime("%H:%M")}.',
            'success',
        )
    else:
        flash('Agendamento de teste criado, mas nao consegui confirmar o evento no Google.', 'warning')
    return redirect(url_for('admin_bp.settings_google_calendar'))


@admin_bp.route('/settings/email', methods=['GET', 'POST'])
@admin_required
def settings_email():
    settings = _get_settings()
    form = SettingsEmailForm(obj=settings)
    test_form = EmailTestForm()

    if request.method == "GET" and hasattr(form, "mail_password"):
        form.mail_password.data = ""

    if form.validate_on_submit():
        existing_mail_password = getattr(settings, "mail_password", None)
        form.populate_obj(settings)
        if not getattr(form, "mail_password", None) or not form.mail_password.data:
            settings.mail_password = existing_mail_password
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings_email'))

    return render_template('admin/settings_email.html', form=form, settings=settings, test_form=test_form)


@admin_bp.route('/settings/profile', methods=['GET', 'POST'])
@admin_required
def settings_profile():
    settings = _get_settings()
    form = SettingsProfileForm(obj=settings)

    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings_profile'))

    return render_template('admin/settings_profile.html', form=form, settings=settings)


@admin_bp.route('/settings/social', methods=['GET', 'POST'])
@admin_required
def settings_social():
    settings = _get_settings()
    form = SettingsSocialForm(obj=settings)

    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings_social'))

    return render_template('admin/settings_social.html', form=form, settings=settings)


@admin_bp.route('/settings/image', methods=['GET', 'POST'])
@admin_required
def settings_image():
    settings = _get_settings()
    form = SettingsImageForm(obj=settings)

    if form.validate_on_submit():
        if form.about_image.data and hasattr(form.about_image.data, 'filename') and form.about_image.data.filename:
            filename = secure_filename(form.about_image.data.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.about_image.data.save(upload_path)
            settings.about_image = filename
            db.session.commit()
            flash('Imagem atualizada com sucesso!', 'success')
        else:
            flash('Selecione uma imagem válida para salvar.', 'warning')
        return redirect(url_for('admin_bp.settings_image'))

    return render_template('admin/settings_image.html', form=form, settings=settings)


def _apply_mail_settings_for_test(settings: Settings | None) -> None:
    if not settings:
        return
    cfg = current_app.config
    if settings.mail_server:
        cfg["MAIL_SERVER"] = settings.mail_server
    if settings.mail_port:
        cfg["MAIL_PORT"] = settings.mail_port
    if settings.mail_use_tls is not None:
        cfg["MAIL_USE_TLS"] = bool(settings.mail_use_tls)
    if settings.mail_username:
        cfg["MAIL_USERNAME"] = settings.mail_username
    if settings.mail_password:
        cfg["MAIL_PASSWORD"] = settings.mail_password
    if settings.mail_default_sender:
        cfg["MAIL_DEFAULT_SENDER"] = settings.mail_default_sender

    mail = current_app.extensions.get("mail") if current_app else None
    if not mail:
        return
    if hasattr(mail, "init_app"):
        mail.init_app(current_app)
        return
    for attr, key in (
        ("server", "MAIL_SERVER"),
        ("port", "MAIL_PORT"),
        ("use_tls", "MAIL_USE_TLS"),
        ("username", "MAIL_USERNAME"),
        ("password", "MAIL_PASSWORD"),
        ("default_sender", "MAIL_DEFAULT_SENDER"),
    ):
        if hasattr(mail, attr) and key in cfg:
            setattr(mail, attr, cfg[key])


@admin_bp.route('/settings/test-email', methods=['POST'])
@admin_required
def test_email_settings():
    form = EmailTestForm()
    if not form.validate_on_submit():
        flash('Solicitação inválida.', 'danger')
        return redirect(url_for('admin_bp.settings_email'))

    settings = Settings.query.first()
    if not settings:
        flash('Configure o sistema antes de testar o e-mail.', 'warning')
        return redirect(url_for('admin_bp.settings_email'))

    to_email = (settings.admin_notify_email or settings.contact_email or "").strip()
    if not to_email:
        flash('Defina o Email de Notificações (ou Email de Contato) para testar.', 'warning')
        return redirect(url_for('admin_bp.settings_email'))

    _apply_mail_settings_for_test(settings)
    mail = current_app.extensions.get("mail") if current_app else None
    if not mail:
        flash('Flask-Mail não está inicializado.', 'danger')
        return redirect(url_for('admin_bp.settings_email'))

    try:
        msg = Message(
            subject="Teste de e-mail do sistema",
            recipients=[to_email],
            body="Este é um e-mail de teste enviado pelo sistema.",
        )
        mail.send(msg)
        flash(f'E-mail de teste enviado para {to_email}.', 'success')
    except Exception as e:
        current_app.logger.exception("Falha ao enviar e-mail de teste: %s", e)
        flash('Não foi possível enviar o e-mail de teste. Verifique as configurações SMTP.', 'danger')

    return redirect(url_for('admin_bp.settings_email'))


@admin_bp.route('/site-sections')
@admin_required
def site_sections():
    sections = SiteSection.query.order_by(
        SiteSection.page.asc(),
        SiteSection.sort_order.asc(),
        SiteSection.title.asc(),
    ).all()
    if not sections:
        created_sections, created_items = _seed_site_sections()
        sections = SiteSection.query.order_by(
            SiteSection.page.asc(),
            SiteSection.sort_order.asc(),
            SiteSection.title.asc(),
        ).all()
        if created_sections or created_items:
            flash('Secoes padrao carregadas automaticamente.', 'info')
    seed_form = SiteSectionSeedForm()
    return render_template('admin/site_sections.html', sections=sections, seed_form=seed_form)


@admin_bp.route('/site-sections/seed', methods=['POST'])
@admin_required
def seed_site_sections():
    form = SiteSectionSeedForm()
    if not form.validate_on_submit():
        flash('Solicitacao invalida.', 'danger')
        return redirect(url_for('admin_bp.site_sections'))

    created_sections, created_items = _seed_site_sections()
    if created_sections == 0 and created_items == 0:
        flash('Nenhuma secao nova criada (conteudo ja existe).', 'info')
    else:
        flash(
            f'Secoes padrao carregadas: {created_sections} secoes, {created_items} itens.',
            'success',
        )
    return redirect(url_for('admin_bp.site_sections'))


@admin_bp.route('/site-sections/add', methods=['GET', 'POST'])
@admin_required
def add_site_section():
    form = SiteSectionForm()
    if form.validate_on_submit():
        slug = form.slug.data.strip().lower()
        if SiteSection.query.filter_by(slug=slug).first():
            flash('Slug ja existe. Escolha outro.', 'danger')
            return render_template('admin/site_section_form.html', form=form, title='Nova Secao')

        section = SiteSection(
            page=form.page.data.strip().lower(),
            slug=slug,
            title=form.title.data.strip() if form.title.data else None,
            subtitle=form.subtitle.data.strip() if form.subtitle.data else None,
            sort_order=form.sort_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(section)
        db.session.commit()
        flash('Secao criada com sucesso.', 'success')
        return redirect(url_for('admin_bp.site_sections'))

    return render_template('admin/site_section_form.html', form=form, title='Nova Secao')


@admin_bp.route('/site-sections/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_site_section(id):
    section = SiteSection.query.get_or_404(id)
    form = SiteSectionForm(obj=section)
    if form.validate_on_submit():
        slug = form.slug.data.strip().lower()
        exists = SiteSection.query.filter(
            SiteSection.slug == slug,
            SiteSection.id != section.id,
        ).first()
        if exists:
            flash('Slug ja existe. Escolha outro.', 'danger')
            return render_template(
                'admin/site_section_form.html',
                form=form,
                title='Editar Secao',
                section=section,
            )

        section.page = form.page.data.strip().lower()
        section.slug = slug
        section.title = form.title.data.strip() if form.title.data else None
        section.subtitle = form.subtitle.data.strip() if form.subtitle.data else None
        section.sort_order = form.sort_order.data or 0
        section.is_active = form.is_active.data
        db.session.commit()
        flash('Secao atualizada com sucesso.', 'success')
        return redirect(url_for('admin_bp.site_sections'))

    return render_template(
        'admin/site_section_form.html',
        form=form,
        title='Editar Secao',
        section=section,
    )


@admin_bp.route('/site-sections/delete/<int:id>', methods=['POST'])
@admin_required
def delete_site_section(id):
    section = SiteSection.query.get_or_404(id)
    db.session.delete(section)
    db.session.commit()
    flash('Secao removida com sucesso.', 'success')
    return redirect(url_for('admin_bp.site_sections'))


@admin_bp.route('/site-sections/<int:section_id>/items')
@admin_required
def site_section_items(section_id):
    section = SiteSection.query.get_or_404(section_id)
    items = SiteSectionItem.query.filter_by(section_id=section.id).order_by(
        SiteSectionItem.sort_order.asc(),
        SiteSectionItem.id.asc(),
    ).all()
    return render_template('admin/site_section_items.html', section=section, items=items)


@admin_bp.route('/site-sections/<int:section_id>/items/add', methods=['GET', 'POST'])
@admin_required
def add_site_section_item(section_id):
    section = SiteSection.query.get_or_404(section_id)
    form = SiteSectionItemForm()
    if form.validate_on_submit():
        item = SiteSectionItem(
            section_id=section.id,
            title=form.title.data.strip(),
            body=form.body.data.strip() if form.body.data else None,
            icon=form.icon.data.strip() if form.icon.data else None,
            sort_order=form.sort_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(item)
        db.session.commit()
        flash('Item criado com sucesso.', 'success')
        return redirect(url_for('admin_bp.site_section_items', section_id=section.id))

    return render_template(
        'admin/site_section_item_form.html',
        form=form,
        section=section,
        title='Novo Item',
    )


@admin_bp.route('/site-sections/items/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_site_section_item(item_id):
    item = SiteSectionItem.query.get_or_404(item_id)
    section = item.section
    form = SiteSectionItemForm(obj=item)
    if form.validate_on_submit():
        item.title = form.title.data.strip()
        item.body = form.body.data.strip() if form.body.data else None
        item.icon = form.icon.data.strip() if form.icon.data else None
        item.sort_order = form.sort_order.data or 0
        item.is_active = form.is_active.data
        db.session.commit()
        flash('Item atualizado com sucesso.', 'success')
        return redirect(url_for('admin_bp.site_section_items', section_id=section.id))

    return render_template(
        'admin/site_section_item_form.html',
        form=form,
        section=section,
        title='Editar Item',
        item=item,
    )


@admin_bp.route('/site-sections/items/<int:item_id>/delete', methods=['POST'])
@admin_required
def delete_site_section_item(item_id):
    item = SiteSectionItem.query.get_or_404(item_id)
    section_id = item.section_id
    db.session.delete(item)
    db.session.commit()
    flash('Item removido com sucesso.', 'success')
    return redirect(url_for('admin_bp.site_section_items', section_id=section_id))


@admin_bp.route('/gallery', methods=['GET', 'POST'])
@admin_required
def gallery():
    form = GalleryForm()
    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()

    if form.validate_on_submit():
        file = form.media_file.data
        filename = secure_filename(file.filename)
        gallery_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery')
        os.makedirs(gallery_folder, exist_ok=True)  # cria a pasta se não existir
        filepath = os.path.join(gallery_folder, filename)
        file.save(filepath)

        item = GalleryItem(
            title=form.title.data,
            description=form.description.data,
            filename=filename,
            media_type=form.media_type.data,
            categoria=form.categoria.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Item adicionado à galeria com sucesso!', 'success')
        return redirect(url_for('admin_bp.gallery'))

    return render_template('admin/gallery.html', form=form, items=items)



@admin_bp.route('/gallery/delete/<int:item_id>', methods=['POST'])
@admin_required
def delete_gallery_item(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    gallery_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery')
    filepath = os.path.join(gallery_folder, item.filename)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        flash(f'Erro ao excluir o arquivo: {str(e)}', 'danger')

    db.session.delete(item)
    db.session.commit()
    flash('Item removido com sucesso!', 'success')
    return redirect(url_for('admin_bp.gallery'))


@admin_bp.route('/billings')
@admin_required
def billings():
    records = BillingRecord.query.order_by(BillingRecord.created_at.desc()).all()
    return render_template('admin/billings.html', records=records)


@admin_bp.route('/billings/add', methods=['GET', 'POST'])
@admin_required
def add_billing():
    form = BillingRecordForm()
    if form.validate_on_submit():
        record = BillingRecord(
            patient_name=form.patient_name.data,
            description=form.description.data,
            amount=form.amount.data,
            status=form.status.data
        )
        db.session.add(record)
        db.session.commit()
        flash('Registro de faturamento adicionado!', 'success')
        return redirect(url_for('admin_bp.billings'))
    return render_template('admin/billing_form.html', form=form, title='Novo Faturamento')


@admin_bp.route('/billings/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_billing(id):
    record = BillingRecord.query.get_or_404(id)
    form = BillingRecordForm(obj=record)
    if form.validate_on_submit():
        record.patient_name = form.patient_name.data
        record.description = form.description.data
        record.amount = form.amount.data
        record.status = form.status.data
        db.session.commit()
        flash('Registro atualizado!', 'success')
        return redirect(url_for('admin_bp.billings'))
    return render_template('admin/billing_form.html', form=form, title='Editar Faturamento')


@admin_bp.route('/invoices')
@admin_required
def invoices():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('admin/invoices.html', invoices=invoices)


@admin_bp.route('/invoices/add', methods=['GET', 'POST'])
@admin_required
def add_invoice():
    form = InvoiceForm()
    if form.validate_on_submit():
        invoice = Invoice(
            number=form.number.data,
            amount=form.amount.data,
            due_date=form.due_date.data,
            status=form.status.data
        )
        db.session.add(invoice)
        db.session.commit()
        flash('Nota fiscal adicionada!', 'success')
        return redirect(url_for('admin_bp.invoices'))
    return render_template('admin/invoice_form.html', form=form, title='Nova Nota Fiscal')


@admin_bp.route('/invoices/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    form = InvoiceForm(obj=invoice)
    if form.validate_on_submit():
        invoice.number = form.number.data
        invoice.amount = form.amount.data
        invoice.due_date = form.due_date.data
        invoice.status = form.status.data
        db.session.commit()
        flash('Nota fiscal atualizada!', 'success')
        return redirect(url_for('admin_bp.invoices'))
    return render_template('admin/invoice_form.html', form=form, title='Editar Nota Fiscal')


@admin_bp.route('/convenios')
@admin_required
def convenios():
    convenios = Convenio.query.order_by(Convenio.created_at.desc()).all()
    return render_template('admin/convenios.html', convenios=convenios)


@admin_bp.route('/convenios/add', methods=['GET', 'POST'])
@admin_required
def add_convenio():
    form = ConvenioForm()
    if form.validate_on_submit():
        convenio = Convenio(
            name=form.name.data,
            details=form.details.data,
            status=form.status.data
        )
        db.session.add(convenio)
        db.session.commit()
        flash('Convênio adicionado!', 'success')
        return redirect(url_for('admin_bp.convenios'))
    return render_template('admin/convenio_form.html', form=form, title='Novo Convênio')


@admin_bp.route('/convenios/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_convenio(id):
    convenio = Convenio.query.get_or_404(id)
    form = ConvenioForm(obj=convenio)
    if form.validate_on_submit():
        convenio.name = form.name.data
        convenio.details = form.details.data
        convenio.status = form.status.data
        db.session.commit()
        flash('Convênio atualizado!', 'success')
        return redirect(url_for('admin_bp.convenios'))
    return render_template('admin/convenio_form.html', form=form, title='Editar Convênio')


@admin_bp.route('/courses')
@admin_required
def courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)


@admin_bp.route('/courses/add', methods=['GET', 'POST'])
@admin_required
def add_course():
    form = CourseForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            course_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'courses')
            os.makedirs(course_folder, exist_ok=True)
            form.image.data.save(os.path.join(course_folder, filename))
        course = Course(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            access_url=form.access_url.data,
            purchase_link=form.purchase_link.data,
            image=filename,
            is_active=form.is_active.data
        )
        db.session.add(course)
        db.session.commit()
        flash('Curso adicionado!', 'success')
        return redirect(url_for('admin_bp.courses'))
    return render_template('admin/course_form.html', form=form, title='Novo Curso')


@admin_bp.route('/courses/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_course(id):
    course = Course.query.get_or_404(id)
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.price = form.price.data
        course.access_url = form.access_url.data
        course.purchase_link = form.purchase_link.data
        course.is_active = form.is_active.data
        if form.image.data:
            if course.image:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', 'uploads', 'courses', course.image))
                except Exception:
                    pass
            filename = secure_filename(form.image.data.filename)
            course_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'courses')
            os.makedirs(course_folder, exist_ok=True)
            form.image.data.save(os.path.join(course_folder, filename))
            course.image = filename
        db.session.commit()
        flash('Curso atualizado!', 'success')
        return redirect(url_for('admin_bp.courses'))
    return render_template('admin/course_form.html', form=form, title='Editar Curso', course=course)


@admin_bp.route('/courses/delete/<int:id>', methods=['POST'])
@admin_required
def delete_course(id):
    course = Course.query.get_or_404(id)
    if course.image:
        try:
            os.remove(os.path.join(current_app.root_path, 'static', 'uploads', 'courses', course.image))
        except Exception:
            pass
    db.session.delete(course)
    db.session.commit()
    flash('Curso removido!', 'success')
    return redirect(url_for('admin_bp.courses'))


@admin_bp.route('/messages')
@admin_required
def messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)


@admin_bp.route('/messages/<int:id>/delete', methods=['POST'])
@admin_required
def delete_message(id):
    message = ContactMessage.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    flash('Mensagem removida!', 'success')
    return redirect(url_for('admin_bp.messages'))
