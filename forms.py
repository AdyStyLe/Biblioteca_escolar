
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, TextAreaField, DateField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError
from models import Livro, Aluno, Usuario

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class UsuarioForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    tipo = SelectField('Tipo de Usuário', choices=[
        ('admin', 'Administrador'),
        ('bibliotecario', 'Bibliotecário'),
        ('aluno', 'Aluno')
    ], validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')

    def validate_email(self, email):
        usuario = Usuario.query.filter_by(email=email.data).first()
        if usuario:
            raise ValidationError('Este email já está cadastrado.')

class LivroForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    autor = StringField('Autor', validators=[DataRequired(), Length(max=100)])
    editora = StringField('Editora', validators=[Optional(), Length(max=100)])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=20)])
    ano_publicacao = IntegerField('Ano de Publicação', validators=[Optional(), NumberRange(min=1000, max=2100)])
    categoria = SelectField('Categoria', choices=[
        ('', 'Selecione...'),
        ('Literatura', 'Literatura'),
        ('Ciências', 'Ciências'),
        ('Matemática', 'Matemática'),
        ('História', 'História'),
        ('Geografia', 'Geografia'),
        ('Biologia', 'Biologia'),
        ('Física', 'Física'),
        ('Química', 'Química'),
        ('Filosofia', 'Filosofia'),
        ('Artes', 'Artes'),
        ('Educação Física', 'Educação Física'),
        ('Inglês', 'Inglês'),
        ('Outros', 'Outros')
    ], validators=[Optional()])
    quantidade_total = IntegerField('Quantidade Total', validators=[DataRequired(), NumberRange(min=1)], default=1)
    descricao = TextAreaField('Descrição', validators=[Optional()])
    submit = SubmitField('Salvar')

class AlunoForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    turma = StringField('Turma', validators=[Optional(), Length(max=50)])
    serie = SelectField('Série', choices=[
        ('', 'Selecione...'),
        ('1º Ano', '1º Ano'),
        ('2º Ano', '2º Ano'),
        ('3º Ano', '3º Ano'),
        ('4º Ano', '4º Ano'),
        ('5º Ano', '5º Ano'),
        ('6º Ano', '6º Ano'),
        ('7º Ano', '7º Ano'),
        ('8º Ano', '8º Ano'),
        ('9º Ano', '9º Ano'),
        ('1º EM', '1º Ensino Médio'),
        ('2º EM', '2º Ensino Médio'),
        ('3º EM', '3º Ensino Médio')
    ], validators=[Optional()])
    data_nascimento = DateField('Data de Nascimento', validators=[Optional()], format='%Y-%m-%d')
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')

    def validate_matricula(self, matricula):
        aluno = Aluno.query.filter_by(matricula=matricula.data).first()
        if aluno:
            raise ValidationError('Esta matrícula já está cadastrada.')

class EmprestimoForm(FlaskForm):
    livro_id = SelectField('Livro', coerce=int, validators=[DataRequired()])
    aluno_id = SelectField('Aluno', coerce=int, validators=[DataRequired()])
    dias_prazo = IntegerField('Prazo (dias)', validators=[DataRequired(), NumberRange(min=1, max=60)], default=14)
    observacoes = TextAreaField('Observações', validators=[Optional()])
    submit = SubmitField('Registrar Empréstimo')

class DevolucaoForm(FlaskForm):
    observacoes = TextAreaField('Observações da Devolução', validators=[Optional()])
    pagar_multa = BooleanField('Multa Paga')
    submit = SubmitField('Confirmar Devolução')

class BuscaForm(FlaskForm):
    busca = StringField('Buscar', validators=[DataRequired()])
    submit = SubmitField('Buscar')
