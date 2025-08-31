from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from datetime import datetime
import hmac
import hashlib
import secrets
from flask_mail import Message

from forms import (
    ContactForm,
    AppointmentForm,
    CourseEnrollmentForm,
    ConfirmPaymentForm,
    RegistrationForm,
    CourseRegistrationForm,
)
from models import (
    db,
    Event,
    Appointment,
    Settings,
    Course,
    CourseEnrollment,
    PaymentTransaction,
    CoursePurchase,
    CourseRegistration,
    Payment,
    ContactMessage,
    User,
)

try:
    import stripe
except ImportError:  # pragma: no cover - Stripe optional for tests
    stripe = None

# Create a Blueprint for the main routes
main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def index():
    settings = Settings.query.first()
    upcoming_events = Event.get_upcoming_events()[:3]  # Limit to 3 events
    return render_template('index.html', settings=settings, events=upcoming_events)

@main_bp.route('/about')
def about():
    settings = Settings.query.first()
    return render_template('about.html', settings=settings)

@main_bp.route('/contact', methods=['GET', 'POST'])
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

            flash('Sua mensagem foi enviada com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('main_bp.contact'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao enviar sua mensagem: {str(e)}', 'danger')
            
    return render_template('contact.html', form=form, settings=settings)

@main_bp.route('/appointment', methods=['GET', 'POST'])
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
            status='pending'
        )
        
        try:
            db.session.add(new_appointment)
            db.session.commit()
            
            # Send email notification functionality would go here
            
            flash('Consulta agendada com sucesso! Você receberá uma confirmação por email.', 'success')
            return redirect(url_for('main_bp.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao agendar sua consulta: {str(e)}', 'danger')
    
    return render_template('appointment.html', form=form, settings=settings)

@main_bp.route('/events')
def events():
    settings = Settings.query.first()
    upcoming_events = Event.get_upcoming_events()
    past_events = Event.get_past_events()
    return render_template('events.html',
                          settings=settings,
                          upcoming_events=upcoming_events,
                          past_events=past_events)


@main_bp.route('/courses', endpoint='courses')
def list_courses():
    """List active courses ordered by creation date."""
    settings = Settings.query.first()
    courses = (
        Course.query.filter_by(is_active=True)
        .order_by(Course.created_at)
        .all()
    )
    return render_template('public_courses.html', courses=courses, settings=settings)


# New route listing active courses ordered by start_date
@main_bp.route('/active-courses')
def active_courses():
    """List upcoming courses using Course helper methods."""
    settings = Settings.query.first()
    courses = Course.get_upcoming_courses()
    return render_template('public_courses.html', courses=courses, settings=settings)


@main_bp.route('/cursos')
def cursos():
    """Portuguese alias for the courses page."""
    return list_courses()


@main_bp.route('/courses/<int:id>')
def course_page(id):
    """Show course details with a link to register."""
    course = Course.query.get_or_404(id)
    settings = Settings.query.first()
    return render_template('public_course_detail.html', course=course, settings=settings)


@main_bp.route('/courses/<int:id>/register', methods=['GET', 'POST'])
def register_course(id):
    """Process course registration and payment via Stripe."""
    course = Course.query.get_or_404(id)
    settings = Settings.query.first()
    form = CourseRegistrationForm()

    if current_user.is_authenticated:
        form.participant_name.data = current_user.username
        form.participant_email.data = current_user.email

    def _finalize_enrollment(registration, transaction_id=None):
        if current_user.is_authenticated:
            user = current_user
        else:
            user = User.query.filter_by(email=registration.participant_email).first()
            if not user:
                username = registration.participant_email.split('@')[0]
                user = User(username=username, email=registration.participant_email, role='student')
                user.set_password(secrets.token_urlsafe(8))
                db.session.add(user)
                db.session.flush()

        enrollment = CourseEnrollment.query.filter_by(course_id=course.id, user_id=user.id).first()
        if not enrollment:
            enrollment = CourseEnrollment(
                course_id=course.id,
                user_id=user.id,
                name=registration.participant_name,
                email=registration.participant_email,
                payment_status='paid'
            )
            db.session.add(enrollment)
            db.session.flush()
        else:
            enrollment.payment_status = 'paid'

        transaction = PaymentTransaction(
            enrollment_id=enrollment.id,
            amount=course.price,
            provider_id=transaction_id or 'manual',
            status='paid'
        )
        db.session.add(transaction)
        db.session.commit()

    if form.validate_on_submit():
        registration = CourseRegistration(
            course_id=course.id,
            participant_name=form.participant_name.data,
            participant_email=form.participant_email.data,
        )
        db.session.add(registration)
        db.session.commit()

        if stripe and current_app.config.get('STRIPE_SECRET_KEY'):
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {'name': course.title},
                        'unit_amount': int(course.price * 100)
                    },
                    'quantity': 1
                }],
                mode='payment',
                success_url=url_for('main_bp.registration_success', registration_id=registration.id, _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('main_bp.register_course', id=id, _external=True)
            )
            payment = Payment(
                registration_id=registration.id,
                amount=course.price,
                provider='stripe',
                status='pending',
                transaction_id=session.id,
            )
            db.session.add(payment)
            db.session.commit()
            return redirect(session.url, code=303)
        else:
            registration.payment_status = 'paid'
            db.session.commit()
            _finalize_enrollment(registration)
            return redirect(url_for('main_bp.registration_success', registration_id=registration.id))

    return render_template('course_register.html', course=course, form=form, settings=settings)


@main_bp.route('/cursos/<int:id>', methods=['GET', 'POST'])
def course_detail(id):
    course = Course.query.get_or_404(id)
    settings = Settings.query.first()
    form = CourseEnrollmentForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            username = form.email.data.split('@')[0]
            user = User(username=username, email=form.email.data, role='student')
            user.set_password(secrets.token_urlsafe(8))
            db.session.add(user)
            db.session.flush()

        enrollment = CourseEnrollment(
            course_id=course.id,
            user_id=user.id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
        )
        try:
            db.session.add(enrollment)
            db.session.commit()
            flash('Inscrição enviada com sucesso!', 'success')
            return redirect(url_for('main_bp.pay_course', enrollment_id=enrollment.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao registrar sua inscrição: {e}', 'danger')
    return render_template('course_enrollment.html', course=course, form=form, settings=settings)


@main_bp.route('/pagamento/<int:enrollment_id>', methods=['GET', 'POST'])
@login_required
def pay_course(enrollment_id):
    enrollment = CourseEnrollment.query.get_or_404(enrollment_id)
    form = ConfirmPaymentForm()
    if enrollment.payment_status == 'paid':
        return redirect(url_for('main_bp.course_access', enrollment_id=enrollment.id))
    if form.validate_on_submit():
        try:
            enrollment.payment_status = 'paid'
            transaction = PaymentTransaction(
                enrollment_id=enrollment.id,
                amount=enrollment.course.price,
                provider_id='SIMULATED'
            )
            db.session.add(transaction)
            db.session.commit()
            flash('Pagamento realizado', 'success')
            return redirect(url_for('student_bp.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro no pagamento: {e}', 'danger')
    return render_template('pay_course.html', enrollment=enrollment, form=form)


@main_bp.route('/course/<int:id>/buy')
def buy_course(id):
    course = Course.query.get_or_404(id)
    if stripe is None or not current_app.config.get('STRIPE_SECRET_KEY'):
        flash('Sistema de pagamento indisponível.', 'danger')
        return redirect(url_for('main_bp.course_detail', id=id))

    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'brl',
                'product_data': {'name': course.title},
                'unit_amount': int(course.price * 100)
            },
            'quantity': 1
        }],
        mode='payment',
        success_url=url_for('main_bp.purchase_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('main_bp.course_detail', id=id, _external=True)
    )

    purchase = CoursePurchase(course_id=course.id, amount=course.price, stripe_session_id=session.id)
    db.session.add(purchase)
    db.session.commit()
    return redirect(session.url, code=303)


@main_bp.route('/purchase/success')
def purchase_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Sessão inválida.', 'danger')
        return redirect(url_for('main_bp.courses'))

    purchase = CoursePurchase.query.filter_by(stripe_session_id=session_id).first_or_404()
    if purchase.status != 'paid':
        purchase.status = 'paid'
        db.session.commit()

    return render_template('purchase_success.html', purchase=purchase)


@main_bp.route('/registration/<int:registration_id>/success')
def registration_success(registration_id):
    registration = CourseRegistration.query.get_or_404(registration_id)
    settings = Settings.query.first()
    if registration.payment_status != 'paid' and stripe and registration.payments:
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        session = stripe.checkout.Session.retrieve(registration.payments[0].transaction_id)
        if session and session.payment_status == 'paid':
            registration.payment_status = 'paid'
            registration.payments[0].status = 'paid'
            db.session.commit()

    if registration.payment_status == 'paid':
        user = User.query.filter_by(email=registration.participant_email).first()
        if not user:
            username = registration.participant_email.split('@')[0]
            user = User(username=username, email=registration.participant_email, role='student')
            user.set_password(secrets.token_urlsafe(8))
            db.session.add(user)
            db.session.flush()

        enrollment = CourseEnrollment.query.filter_by(course_id=registration.course_id, user_id=user.id).first()
        if not enrollment:
            enrollment = CourseEnrollment(
                course_id=registration.course_id,
                user_id=user.id,
                name=registration.participant_name,
                email=registration.participant_email,
                payment_status='paid'
            )
            db.session.add(enrollment)
            db.session.flush()
        else:
            enrollment.payment_status = 'paid'

        provider_id = registration.payments[0].transaction_id if registration.payments else 'manual'
        existing_txn = PaymentTransaction.query.filter_by(enrollment_id=enrollment.id, provider_id=provider_id).first()
        if not existing_txn:
            txn = PaymentTransaction(
                enrollment_id=enrollment.id,
                amount=registration.course.price,
                provider_id=provider_id,
                status='paid'
            )
            db.session.add(txn)
        db.session.commit()

    return render_template('registration_success.html', registration=registration, settings=settings)


@main_bp.route('/curso/acesso/<int:enrollment_id>')
@login_required
def course_access(enrollment_id):
    enrollment = CourseEnrollment.query.get_or_404(enrollment_id)
    if enrollment.user_id != current_user.id:
        flash('Você não tem permissão para acessar este curso.', 'danger')
        return redirect(url_for('student_bp.dashboard'))
    if enrollment.payment_status != 'paid':
        flash('Pagamento não identificado para esta inscrição.', 'warning')
        return redirect(url_for('main_bp.course_detail', id=enrollment.course_id))
    return render_template('course_access.html', enrollment=enrollment)


@main_bp.route('/webhook/hotmart', methods=['POST'])
def hotmart_webhook():
    """Handle Hotmart purchase notifications."""
    secret = current_app.config.get('HOTMART_WEBHOOK_SECRET', '')
    signature = request.headers.get('X-HOTMART-HMAC-SHA256', '')
    if not secret or not signature:
        return 'Unauthorized', 403
    expected = hmac.new(secret.encode(), request.data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return 'Unauthorized', 403

    payload = request.get_json(silent=True) or {}
    status = payload.get('status')
    product_id = payload.get('id') or payload.get('product', {}).get('id')
    email = payload.get('email') or payload.get('buyer', {}).get('email')
    name = payload.get('name') or payload.get('buyer', {}).get('name') or (email.split('@')[0] if email else '')
    amount = float(payload.get('amount') or payload.get('price') or 0)
    txn_id = payload.get('transaction_id') or payload.get('purchase', {}).get('id')

    if not status or not product_id or not email:
        return 'Invalid payload', 400

    course = Course.query.filter_by(id=product_id).first()
    if not course:
        return 'Course not found', 404

    user = User.query.filter_by(email=email).first()
    new_user = False
    temp_password = None
    if not user:
        username = email.split('@')[0]
        user = User(username=username, email=email, role='student')
        temp_password = secrets.token_urlsafe(8)
        user.set_password(temp_password)
        db.session.add(user)
        db.session.flush()
        new_user = True

    enrollment = CourseEnrollment.query.filter_by(course_id=course.id, user_id=user.id).first()
    if not enrollment:
        enrollment = CourseEnrollment(
            course_id=course.id,
            user_id=user.id,
            name=name,
            email=email,
            payment_status=status,
        )
        db.session.add(enrollment)
    else:
        enrollment.payment_status = status

    db.session.flush()

    transaction = PaymentTransaction(
        enrollment_id=enrollment.id,
        amount=amount or course.price,
        provider_id=txn_id,
        status=status,
    )
    db.session.add(transaction)
    db.session.commit()

    mail = current_app.extensions.get('mail')
    if mail:
        try:
            login_link = url_for('student_bp.login', _external=True)
            body = f'Você agora tem acesso ao curso {course.title}. Link: {course.access_url or ""}'
            if new_user and temp_password:
                body += (
                    f"\n\nFaça login em {login_link} com o usuário {user.username} e a senha temporária {temp_password}. "
                    "Altere sua senha após o primeiro acesso."
                )
            else:
                body += f"\n\nAcesse {login_link} para entrar no curso."
            msg = Message(
                subject='Acesso ao curso',
                recipients=[email],
                body=body
            )
            mail.send(msg)
        except Exception:
            pass

    return '', 200


# Public catalog of courses
@main_bp.route('/catalogo-cursos')
def course_catalog():
    """Display all active courses for visitors."""
    settings = Settings.query.first()
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('course_catalog.html', courses=courses, settings=settings)


# Details of a single course without enrollment form
@main_bp.route('/catalogo-cursos/<int:course_id>')
def course_catalog_detail(course_id):
    """Show public details for a course."""
    course = Course.query.get_or_404(course_id)
    settings = Settings.query.first()
    return render_template('course_catalog_detail.html', course=course, settings=settings)

@main_bp.context_processor
def inject_settings():
    settings = Settings.query.first()
    # Add current_year to the context for use in all templates
    return dict(settings=settings or {}, current_year=datetime.now().year)


@main_bp.route('/galeria')
def gallery():
    from models import GalleryItem  # (após criarmos a model)
    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    settings = Settings.query.first()
    return render_template('gallery.html', items=items, settings=settings)


