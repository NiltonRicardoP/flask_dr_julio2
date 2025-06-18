from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import GalleryItem
from forms import GalleryForm
from forms import LoginForm, EventForm, SettingsForm
from models import db, User, Event, Appointment, Settings

# Create Blueprint for the admin routes
admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_bp.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('admin_bp.login'))
            
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('admin_bp.dashboard'))
        
    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))

@admin_bp.route('/')
@login_required
def dashboard():
    # Get recent appointments
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    
    # Get upcoming events
    upcoming_events = Event.get_upcoming_events()[:5]
    
    return render_template('admin/dashboard.html', 
                          appointments=appointments, 
                          upcoming_events=upcoming_events)

@admin_bp.route('/appointments')
@login_required
def appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments)

@admin_bp.route('/appointment/<int:id>/status/<status>')
@login_required
def update_appointment_status(id, status):
    appointment = Appointment.query.get_or_404(id)
    
    if status in ['pending', 'confirmed', 'cancelled']:
        appointment.status = status
        db.session.commit()
        flash('Status do agendamento atualizado com sucesso!', 'success')
    else:
        flash('Status inválido', 'danger')
        
    return redirect(url_for('admin_bp.appointments'))

@admin_bp.route('/events')
@login_required
def events():
    events = Event.query.order_by(Event.start_date.desc()).all()
    return render_template('admin/events.html', events=events)

@admin_bp.route('/events/add', methods=['GET', 'POST'])
@login_required
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
@login_required
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

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    form = SettingsForm(obj=settings)

    if form.validate_on_submit():
        form.populate_obj(settings)

        # Só tenta salvar a imagem se for um upload válido
        if form.about_image.data and hasattr(form.about_image.data, 'filename'):
            filename = secure_filename(form.about_image.data.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.about_image.data.save(upload_path)
            settings.about_image = filename

        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_bp.settings'))

    return render_template('admin/settings.html', form=form, settings=settings)

@admin_bp.route('/gallery', methods=['GET', 'POST'])
@login_required
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
@login_required
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
