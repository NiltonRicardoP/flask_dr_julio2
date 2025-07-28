from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from datetime import datetime

from models import db, Course, CourseRegistration
from forms import CourseRegistrationForm, ContactForm, AppointmentForm
from models import Event, ContactMessage, Appointment, Settings


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


@main_bp.route('/courses/<int:id>/register', methods=['GET', 'POST'])
def register_course(id):
    course = Course.query.get_or_404(id)
    if not course.is_active:
        flash('Curso inativo.', 'danger')
        return redirect(url_for('main_bp.courses'))

    form = CourseRegistrationForm()
    if form.validate_on_submit():
        registration = CourseRegistration(
            course_id=id,
            participant_name=form.participant_name.data,
            participant_email=form.participant_email.data,
            payment_method=form.payment_method.data,
        )
        db.session.add(registration)
        db.session.commit()

        try:
            from pagarme_service import create_transaction

            result = create_transaction(
                course.price,
                card_number=form.card_number.data,
                card_expiration_date=form.card_expiration.data,
                card_cvv=form.card_cvv.data,
                card_holder_name=form.participant_name.data,
            )
            registration.transaction_id = str(result.get('id'))
            registration.payment_status = result.get('status', 'pending')
        except Exception:
            registration.payment_status = 'failed'
        finally:
            db.session.commit()

        flash('Inscrição realizada com sucesso!', 'success')
        return redirect(url_for('main_bp.course_page', id=id))

    return render_template('course_register.html', form=form, course=course)


