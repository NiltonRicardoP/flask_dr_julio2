from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, DateField, TimeField, BooleanField, SubmitField, FloatField
from wtforms.validators import DataRequired, Email, ValidationError, Length, Optional
from datetime import date
from wtforms import SelectField

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar de mim')
    submit = SubmitField('Entrar')

class AppointmentForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Telefone', validators=[DataRequired(), Length(min=8, max=20)])
    date = DateField('Data', validators=[DataRequired()])
    time = TimeField('Horário', validators=[DataRequired()])
    reason = TextAreaField('Motivo da Consulta', validators=[DataRequired()])
    submit = SubmitField('Agendar Consulta')
    
    def validate_date(self, field):
        if field.data < date.today():
            raise ValidationError('Data não pode ser no passado.')

class ContactForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Assunto', validators=[DataRequired(), Length(min=3, max=100)])
    message = TextAreaField('Mensagem', validators=[DataRequired()])
    submit = SubmitField('Enviar Mensagem')

class EventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[DataRequired()])
    start_date = DateField('Data de Início', validators=[DataRequired()])
    end_date = DateField('Data de Término', validators=[DataRequired()])
    location = StringField('Local', validators=[DataRequired()])
    image = FileField('Imagem', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens são permitidas!')
    ])
    is_active = BooleanField('Evento Ativo', default=True)
    submit = SubmitField('Salvar')


class CourseForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[DataRequired()])
    price = FloatField('Preço', validators=[DataRequired()])
    start_date = DateField('Data de Início', validators=[DataRequired()])
    end_date = DateField('Data de Término', validators=[DataRequired()])
    location = StringField('Local', validators=[DataRequired()])
    image = FileField('Imagem', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens são permitidas!')
    ])
    is_active = BooleanField('Curso Ativo', default=True)
    submit = SubmitField('Salvar')


class SettingsForm(FlaskForm):
    site_title = StringField('Título do Site', validators=[DataRequired()])
    contact_email = StringField('Email de Contato', validators=[DataRequired(), Email()])
    contact_phone = StringField('Telefone de Contato', validators=[DataRequired()])
    address = TextAreaField('Endereço', validators=[DataRequired()])
    about_text = TextAreaField('Texto Sobre', validators=[DataRequired()])
    academic_background = TextAreaField('Formação Acadêmica', validators=[Optional()])
    professional_experience = TextAreaField('Experiência Profissional', validators=[Optional()])
    social_facebook = StringField('Facebook URL', validators=[Optional()])
    social_instagram = StringField('Instagram URL', validators=[Optional()])
    social_youtube = StringField('YouTube URL', validators=[Optional()])

    # Novo campo para imagem
    about_image = FileField('Imagem Sobre', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')
    ])

    submit = SubmitField('Salvar')

class GalleryForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])
    media_file = FileField('Arquivo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'mp4'], 'Somente imagens e vídeos são permitidos!')
    ])
    media_type = SelectField('Tipo de Mídia', choices=[('image', 'Imagem'), ('video', 'Vídeo')], validators=[DataRequired()])
    categoria = SelectField('Categoria', choices=[
        ('palestras', 'Palestras'),
        ('consultorio', 'Consultório'),
        ('eventos', 'Eventos'),
        ('videos', 'Vídeos')
    ], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class BillingRecordForm(FlaskForm):
    patient_name = StringField('Paciente', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])
    amount = FloatField('Valor', validators=[DataRequired()])
    status = SelectField('Status', choices=[('pending', 'Pendente'), ('paid', 'Pago'), ('cancelled', 'Cancelado')], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class InvoiceForm(FlaskForm):
    number = StringField('Número', validators=[DataRequired()])
    amount = FloatField('Valor', validators=[DataRequired()])
    due_date = DateField('Vencimento', validators=[DataRequired()])
    status = SelectField('Status', choices=[('pending', 'Pendente'), ('paid', 'Pago'), ('cancelled', 'Cancelado')], validators=[DataRequired()])
    submit = SubmitField('Salvar')


class ConvenioForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    details = TextAreaField('Detalhes', validators=[Optional()])
    status = SelectField('Status', choices=[('active', 'Ativo'), ('inactive', 'Inativo')], validators=[DataRequired()])
    submit = SubmitField('Salvar')

