from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, DateField, TimeField, BooleanField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, ValidationError, Length, Optional, NumberRange, URL
from datetime import date
from wtforms import SelectField

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar de mim')
    submit = SubmitField('Entrar')

class AppointmentForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telefone', validators=[DataRequired(), Length(min=8, max=20)])
    date = DateField('Data', validators=[DataRequired()])
    time = TimeField('Horario', validators=[DataRequired()])
    reason = TextAreaField('Motivo da Consulta', validators=[DataRequired()])
    submit = SubmitField('Agendar Consulta')
    
    def validate_date(self, field):
        if field.data < date.today():
            raise ValidationError('Data nao pode ser no passado.')

class RescheduleForm(FlaskForm):
    date = DateField('Data', validators=[DataRequired()])
    time = TimeField('Horario', validators=[DataRequired()])
    submit = SubmitField('Reagendar')

    def validate_date(self, field):
        if field.data < date.today():
            raise ValidationError('Data nao pode ser no passado.')


class CancelAppointmentForm(FlaskForm):
    submit = SubmitField('Cancelar')


class ContactForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Assunto', validators=[DataRequired(), Length(min=3, max=100)])
    message = TextAreaField('Mensagem', validators=[DataRequired()])
    submit = SubmitField('Enviar Mensagem')

class PatientForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Telefone', validators=[Optional(), Length(max=30)])
    birth_date = DateField('Data de Nascimento', validators=[Optional()])
    notes = TextAreaField('Observacoes', validators=[Optional()])
    submit = SubmitField('Salvar')


class PatientNoteForm(FlaskForm):
    title = StringField('Titulo', validators=[Optional(), Length(max=150)])
    content = TextAreaField('Conteudo', validators=[DataRequired()])
    submit = SubmitField('Adicionar Nota')


class EventForm(FlaskForm):
    title = StringField('Titulo', validators=[DataRequired()])
    description = TextAreaField('Descricao', validators=[DataRequired()])
    start_date = DateField('Data de Inicio', validators=[DataRequired()])
    end_date = DateField('Data de Termino', validators=[DataRequired()])
    location = StringField('Local', validators=[DataRequired()])
    image = FileField('Imagem', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens sao permitidas!')
    ])
    is_active = BooleanField('Evento Ativo', default=True)
    submit = SubmitField('Salvar')

    def validate_end_date(self, field):
        if self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('Data de termino nao pode ser anterior a data de inicio.')


class SettingsSystemForm(FlaskForm):
    site_title = StringField('Titulo do Site', validators=[DataRequired()])
    contact_email = StringField('Email de Contato', validators=[DataRequired(), Email()])
    contact_phone = StringField('Telefone de Contato', validators=[DataRequired()])
    address = TextAreaField('Endereco', validators=[DataRequired()])
    submit = SubmitField('Salvar')


class SettingsGoogleCalendarForm(FlaskForm):
    google_calendar_id = StringField('Google Calendar ID', validators=[Optional(), Length(max=255)])
    google_attendee_emails = TextAreaField('Emails para convites', validators=[Optional(), Length(max=1000)])
    google_sync_enabled = BooleanField('Ativar sincronizacao com Google Agenda')
    submit = SubmitField('Salvar configuracoes')


class GoogleCalendarSyncForm(FlaskForm):
    submit = SubmitField('Sincronizar agora')


class GoogleCalendarResyncForm(FlaskForm):
    days = IntegerField('Dias', validators=[DataRequired(), NumberRange(min=1, max=180)], default=30)
    submit = SubmitField('Reenviar eventos')


class GoogleCalendarTestForm(FlaskForm):
    submit = SubmitField('Criar agendamento de teste')


class SettingsEmailForm(FlaskForm):
    admin_notify_email = StringField('Email de Notificacoes', validators=[Optional(), Email()])
    mail_server = StringField('Servidor SMTP', validators=[Optional()])
    mail_port = IntegerField('Porta SMTP', validators=[Optional(), NumberRange(min=1, max=65535)])
    mail_use_tls = BooleanField('Usar TLS', default=True)
    mail_username = StringField('Usuario SMTP', validators=[Optional()])
    mail_password = PasswordField('Senha SMTP', validators=[Optional()])
    mail_default_sender = StringField('Remetente Padrao', validators=[Optional()])
    submit = SubmitField('Salvar')


class SettingsProfileForm(FlaskForm):
    about_text = TextAreaField('Texto Sobre', validators=[DataRequired()])
    academic_background = TextAreaField('Formacao Academica', validators=[Optional()])
    professional_experience = TextAreaField('Experiencia Profissional', validators=[Optional()])
    submit = SubmitField('Salvar')


class SettingsSocialForm(FlaskForm):
    social_facebook = StringField('Facebook URL', validators=[Optional()])
    social_instagram = StringField('Instagram URL', validators=[Optional()])
    social_youtube = StringField('YouTube URL', validators=[Optional()])
    submit = SubmitField('Salvar')


class SettingsImageForm(FlaskForm):
    about_image = FileField('Imagem Sobre', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens sao permitidas!')
    ])
    submit = SubmitField('Salvar')




class SiteSectionForm(FlaskForm):
    page = StringField('Pagina', validators=[DataRequired(), Length(max=50)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=60)])
    title = TextAreaField('Titulo', validators=[Optional(), Length(max=150)])
    subtitle = StringField('Subtitulo', validators=[Optional(), Length(max=255)])
    sort_order = IntegerField('Ordem', validators=[Optional(), NumberRange(min=0, max=10000)])
    is_active = BooleanField('Ativa', default=True)
    submit = SubmitField('Salvar')


class SiteSectionItemForm(FlaskForm):
    title = StringField('Titulo', validators=[DataRequired(), Length(max=150)])
    body = TextAreaField('Texto', validators=[Optional()])
    icon = StringField('Icone (Font Awesome)', validators=[Optional(), Length(max=100)])
    sort_order = IntegerField('Ordem', validators=[Optional(), NumberRange(min=0, max=10000)])
    is_active = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')


class SiteSectionSeedForm(FlaskForm):
    submit = SubmitField('Carregar secoes padrao')


class EmailTestForm(FlaskForm):
    submit = SubmitField('Enviar e-mail de teste')


class GalleryForm(FlaskForm):
    title = StringField('Titulo', validators=[DataRequired()])
    description = TextAreaField('Descricao', validators=[Optional()])
    media_file = FileField('Arquivo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'mp4'], 'Somente imagens e videos sao permitidos!')
    ])
    media_type = SelectField('Tipo de Midia', choices=[('image', 'Imagem'), ('video', 'Video')], validators=[DataRequired()])
    categoria = SelectField('Categoria', choices=[
        ('palestras', 'Palestras'),
        ('consultorio', 'Consultorio'),
        ('eventos', 'Eventos'),
        ('videos', 'Videos')
    ], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class BillingRecordForm(FlaskForm):
    patient_name = StringField('Paciente', validators=[DataRequired()])
    description = TextAreaField('Descricao', validators=[Optional()])
    amount = FloatField('Valor', validators=[DataRequired()])
    status = SelectField('Status', choices=[('pending', 'Pendente'), ('paid', 'Pago'), ('cancelled', 'Cancelado')], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class InvoiceForm(FlaskForm):
    number = StringField('Numero', validators=[DataRequired()])
    amount = FloatField('Valor', validators=[DataRequired()])
    due_date = DateField('Vencimento', validators=[DataRequired()])
    status = SelectField('Status', choices=[('pending', 'Pendente'), ('paid', 'Pago'), ('cancelled', 'Cancelado')], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class ConvenioForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    details = TextAreaField('Detalhes', validators=[Optional()])
    status = SelectField('Status', choices=[('active', 'Ativo'), ('inactive', 'Inativo')], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class CourseForm(FlaskForm):
    title = StringField('Titulo', validators=[DataRequired()])
    description = TextAreaField('Descricao', validators=[DataRequired()])
    image = FileField('Imagem', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens sao permitidas!')])
    price = FloatField('Preco', validators=[DataRequired(), NumberRange(min=0)])
    access_url = StringField('URL de Acesso', validators=[Optional()])
    purchase_link = StringField('Link do curso', validators=[Optional(), URL()])
    is_active = BooleanField('Curso Ativo', default=True)
    submit = SubmitField('Salvar')

