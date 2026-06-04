
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from config import Config

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='aluno')  # admin, bibliotecario, aluno
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    emprestimos = db.relationship('Emprestimo', backref='usuario', lazy=True)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)

    def is_admin(self):
        return self.tipo == 'admin'

    def is_bibliotecario(self):
        return self.tipo in ['admin', 'bibliotecario']

    def __repr__(self):
        return f'<Usuario {self.nome}>'


class Livro(db.Model):
    __tablename__ = 'livros'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    editora = db.Column(db.String(100))
    isbn = db.Column(db.String(20), unique=True)
    ano_publicacao = db.Column(db.Integer)
    categoria = db.Column(db.String(50))
    quantidade_total = db.Column(db.Integer, default=1)
    quantidade_disponivel = db.Column(db.Integer, default=1)
    descricao = db.Column(db.Text)
    imagem_url = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    emprestimos = db.relationship('Emprestimo', backref='livro', lazy=True)

    def __repr__(self):
        return f'<Livro {self.titulo}>'


class Aluno(db.Model):
    __tablename__ = 'alunos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    telefone = db.Column(db.String(20))
    turma = db.Column(db.String(50))
    serie = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    endereco = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    emprestimos = db.relationship('Emprestimo', backref='aluno', lazy=True)

    def __repr__(self):
        return f'<Aluno {self.nome}>'

    def emprestimos_ativos(self):
        return Emprestimo.query.filter_by(aluno_id=self.id, status='emprestado').count()

    def total_multas(self):
        total = db.session.query(db.func.sum(Emprestimo.multa)).filter(
            Emprestimo.aluno_id == self.id,
            Emprestimo.multa_paga == False
        ).scalar()
        return total or 0.0


class Emprestimo(db.Model):
    __tablename__ = 'emprestimos'

    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livros.id'), nullable=False)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    data_emprestimo = db.Column(db.DateTime, default=datetime.utcnow)
    data_devolucao_prevista = db.Column(db.DateTime)
    data_devolucao_real = db.Column(db.DateTime)

    status = db.Column(db.String(20), default='emprestado')  # emprestado, devolvido, atrasado
    multa = db.Column(db.Float, default=0.0)
    multa_paga = db.Column(db.Boolean, default=False)

    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Emprestimo, self).__init__(**kwargs)
        if not self.data_devolucao_prevista:
            self.data_devolucao_prevista = datetime.utcnow() + timedelta(days=Config.DIAS_EMPRESTIMO)

    def calcular_multa(self):
        if self.status == 'devolvido' or not self.data_devolucao_prevista:
            return 0.0

        hoje = datetime.utcnow()
        if hoje > self.data_devolucao_prevista:
            dias_atraso = (hoje - self.data_devolucao_prevista).days
            return dias_atraso * Config.MULTA_POR_DIA
        return 0.0

    def atualizar_status(self):
        if self.status == 'emprestado':
            if datetime.utcnow() > self.data_devolucao_prevista:
                self.status = 'atrasado'
            self.multa = self.calcular_multa()

    def __repr__(self):
        return f'<Emprestimo {self.id}>'


class LogAtividade(db.Model):
    __tablename__ = 'log_atividades'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
