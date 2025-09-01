from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user
from functools import wraps
from werkzeug.utils import secure_filename
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
from forms import LoginForm, EventForm, SettingsForm
from models import (
    db,
    User,
    Event,
    Appointment,
    Settings,
    Course,
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
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()

    # Get upcoming events
    upcoming_events = Event.get_upcoming_events()[:5]

    contacts_count = ContactMessage.query.count()
    recent_contacts = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                          appointments=appointments,
                          upcoming_events=upcoming_events,
                          contacts_count=contacts_count,
                          recent_contacts=recent_contacts)

@admin_bp.route('/appointments')
@admin_required
def appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments)

@admin_bp.route('/appointment/<int:id>/status/<status>')
@admin_required
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

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
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
