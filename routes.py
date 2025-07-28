from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from datetime import datetime


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


