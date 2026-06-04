
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from functools import wraps
import os

from config import Config
from models import db, Usuario, Livro, Aluno, Emprestimo, LogAtividade
from forms import LoginForm, UsuarioForm, LivroForm, AlunoForm, EmprestimoForm, DevolucaoForm, BuscaForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'

# ==================== UTILITÁRIOS ====================

def log_acao(acao, detalhes=None):
    log = LogAtividade(
        usuario_id=current_user.id if current_user.is_authenticated else None,
        acao=acao,
        detalhes=detalhes,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

def requer_bibliotecario(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_bibliotecario():
            flash('Acesso negado. Permissão de bibliotecário necessária.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def requer_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acesso negado. Permissão de administrador necessária.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario and usuario.check_password(form.senha.data) and usuario.ativo:
            login_user(usuario, remember=True)
            log_acao('Login', f'Usuário {usuario.nome} fez login')
            flash(f'Bem-vindo, {usuario.nome}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos.', 'danger')

    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    log_acao('Logout', f'Usuário {current_user.nome} fez logout')
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    total_livros = Livro.query.filter_by(ativo=True).count()
    total_alunos = Aluno.query.filter_by(ativo=True).count()
    emprestimos_ativos = Emprestimo.query.filter_by(status='emprestado').count()
    emprestimos_atrasados = Emprestimo.query.filter_by(status='atrasado').count()

    # Últimos empréstimos
    ultimos_emprestimos = Emprestimo.query.order_by(Emprestimo.created_at.desc()).limit(5).all()

    # Livros mais emprestados
    livros_populares = db.session.query(
        Livro.titulo, Livro.autor, db.func.count(Emprestimo.id).label('total')
    ).join(Emprestimo).group_by(Livro.id).order_by(db.desc('total')).limit(5).all()

    # Atualizar multas
    for emp in Emprestimo.query.filter_by(status='emprestado').all():
        emp.atualizar_status()
    db.session.commit()

    return render_template('dashboard.html',
                         total_livros=total_livros,
                         total_alunos=total_alunos,
                         emprestimos_ativos=emprestimos_ativos,
                         emprestimos_atrasados=emprestimos_atrasados,
                         ultimos_emprestimos=ultimos_emprestimos,
                         livros_populares=livros_populares)

# ==================== LIVROS ====================

@app.route('/livros')
@login_required
def listar_livros():
    pagina = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '')
    categoria = request.args.get('categoria', '')

    query = Livro.query.filter_by(ativo=True)

    if busca:
        query = query.filter(
            db.or_(
                Livro.titulo.ilike(f'%{busca}%'),
                Livro.autor.ilike(f'%{busca}%'),
                Livro.isbn.ilike(f'%{busca}%')
            )
        )

    if categoria:
        query = query.filter_by(categoria=categoria)

    livros = query.order_by(Livro.titulo).paginate(page=pagina, per_page=12, error_out=False)
    categorias = db.session.query(Livro.categoria).distinct().filter(Livro.categoria != None).all()

    return render_template('livros/listar.html', livros=livros, busca=busca, 
                         categoria=categoria, categorias=categorias)

@app.route('/livros/novo', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def novo_livro():
    form = LivroForm()
    if form.validate_on_submit():
        livro = Livro(
            titulo=form.titulo.data,
            autor=form.autor.data,
            editora=form.editora.data,
            isbn=form.isbn.data,
            ano_publicacao=form.ano_publicacao.data,
            categoria=form.categoria.data,
            quantidade_total=form.quantidade_total.data,
            quantidade_disponivel=form.quantidade_total.data,
            descricao=form.descricao.data
        )
        db.session.add(livro)
        db.session.commit()
        log_acao('Cadastro de Livro', f'Livro: {livro.titulo}')
        flash('Livro cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_livros'))

    return render_template('livros/form.html', form=form, titulo='Novo Livro')

@app.route('/livros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def editar_livro(id):
    livro = Livro.query.get_or_404(id)
    form = LivroForm(obj=livro)

    if form.validate_on_submit():
        livro.titulo = form.titulo.data
        livro.autor = form.autor.data
        livro.editora = form.editora.data
        livro.isbn = form.isbn.data
        livro.ano_publicacao = form.ano_publicacao.data
        livro.categoria = form.categoria.data
        livro.descricao = form.descricao.data

        # Ajustar disponibilidade se quantidade mudou
        diferenca = form.quantidade_total.data - livro.quantidade_total
        livro.quantidade_total = form.quantidade_total.data
        livro.quantidade_disponivel += diferenca

        db.session.commit()
        log_acao('Edição de Livro', f'Livro ID: {id}')
        flash('Livro atualizado com sucesso!', 'success')
        return redirect(url_for('listar_livros'))

    return render_template('livros/form.html', form=form, livro=livro, titulo='Editar Livro')

@app.route('/livros/excluir/<int:id>', methods=['POST'])
@login_required
@requer_bibliotecario
def excluir_livro(id):
    livro = Livro.query.get_or_404(id)

    # Verificar se há empréstimos ativos
    emprestimos_ativos = Emprestimo.query.filter_by(livro_id=id, status='emprestado').count()
    if emprestimos_ativos > 0:
        flash('Não é possível excluir livro com empréstimos ativos.', 'danger')
        return redirect(url_for('listar_livros'))

    livro.ativo = False
    db.session.commit()
    log_acao('Exclusão de Livro', f'Livro: {livro.titulo}')
    flash('Livro removido com sucesso!', 'success')
    return redirect(url_for('listar_livros'))

@app.route('/livros/<int:id>')
@login_required
def detalhes_livro(id):
    livro = Livro.query.get_or_404(id)
    emprestimos = Emprestimo.query.filter_by(livro_id=id).order_by(Emprestimo.created_at.desc()).limit(10).all()
    return render_template('livros/detalhes.html', livro=livro, emprestimos=emprestimos)

# ==================== ALUNOS ====================

@app.route('/alunos')
@login_required
def listar_alunos():
    pagina = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '')
    serie = request.args.get('serie', '')

    query = Aluno.query.filter_by(ativo=True)

    if busca:
        query = query.filter(
            db.or_(
                Aluno.nome.ilike(f'%{busca}%'),
                Aluno.matricula.ilike(f'%{busca}%'),
                Aluno.email.ilike(f'%{busca}%')
            )
        )

    if serie:
        query = query.filter_by(serie=serie)

    alunos = query.order_by(Aluno.nome).paginate(page=pagina, per_page=12, error_out=False)
    series = db.session.query(Aluno.serie).distinct().filter(Aluno.serie != None).all()

    return render_template('alunos/listar.html', alunos=alunos, busca=busca,
                         serie=serie, series=series)

@app.route('/alunos/novo', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def novo_aluno():
    form = AlunoForm()
    if form.validate_on_submit():
        aluno = Aluno(
            nome=form.nome.data,
            matricula=form.matricula.data,
            email=form.email.data,
            telefone=form.telefone.data,
            turma=form.turma.data,
            serie=form.serie.data,
            data_nascimento=form.data_nascimento.data,
            endereco=form.endereco.data
        )
        db.session.add(aluno)
        db.session.commit()
        log_acao('Cadastro de Aluno', f'Aluno: {aluno.nome}')
        flash('Aluno cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_alunos'))

    return render_template('alunos/form.html', form=form, titulo='Novo Aluno')

@app.route('/alunos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def editar_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    form = AlunoForm(obj=aluno)

    # Remover validação de matrícula única na edição
    if form.validate_on_submit():
        aluno.nome = form.nome.data
        aluno.email = form.email.data
        aluno.telefone = form.telefone.data
        aluno.turma = form.turma.data
        aluno.serie = form.serie.data
        aluno.data_nascimento = form.data_nascimento.data
        aluno.endereco = form.endereco.data
        aluno.ativo = form.ativo.data

        db.session.commit()
        log_acao('Edição de Aluno', f'Aluno ID: {id}')
        flash('Aluno atualizado com sucesso!', 'success')
        return redirect(url_for('listar_alunos'))

    return render_template('alunos/form.html', form=form, aluno=aluno, titulo='Editar Aluno')

@app.route('/alunos/excluir/<int:id>', methods=['POST'])
@login_required
@requer_bibliotecario
def excluir_aluno(id):
    aluno = Aluno.query.get_or_404(id)

    emprestimos_ativos = Emprestimo.query.filter_by(aluno_id=id, status='emprestado').count()
    if emprestimos_ativos > 0:
        flash('Não é possível excluir aluno com empréstimos ativos.', 'danger')
        return redirect(url_for('listar_alunos'))

    aluno.ativo = False
    db.session.commit()
    log_acao('Exclusão de Aluno', f'Aluno: {aluno.nome}')
    flash('Aluno removido com sucesso!', 'success')
    return redirect(url_for('listar_alunos'))

@app.route('/alunos/<int:id>')
@login_required
def detalhes_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    emprestimos = Emprestimo.query.filter_by(aluno_id=id).order_by(Emprestimo.created_at.desc()).all()
    return render_template('alunos/detalhes.html', aluno=aluno, emprestimos=emprestimos)

# ==================== EMPRÉSTIMOS ====================

@app.route('/emprestimos')
@login_required
def listar_emprestimos():
    pagina = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    busca = request.args.get('busca', '')

    # Atualizar status de atrasados
    for emp in Emprestimo.query.filter_by(status='emprestado').all():
        emp.atualizar_status()
    db.session.commit()

    query = Emprestimo.query

    if status:
        query = query.filter_by(status=status)

    if busca:
        query = query.join(Livro).join(Aluno).filter(
            db.or_(
                Livro.titulo.ilike(f'%{busca}%'),
                Aluno.nome.ilike(f'%{busca}%')
            )
        )

    emprestimos = query.order_by(Emprestimo.created_at.desc()).paginate(page=pagina, per_page=15, error_out=False)

    return render_template('emprestimos/listar.html', emprestimos=emprestimos, status=status, busca=busca)

@app.route('/emprestimos/novo', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def novo_emprestimo():
    form = EmprestimoForm()

    # Popular selects
    form.livro_id.choices = [(l.id, f'{l.titulo} - {l.autor} (Disp: {l.quantidade_disponivel})') 
                             for l in Livro.query.filter_by(ativo=True).filter(Livro.quantidade_disponivel > 0).order_by(Livro.titulo).all()]
    form.aluno_id.choices = [(a.id, f'{a.nome} - {a.matricula}') 
                             for a in Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()]

    if form.validate_on_submit():
        livro = Livro.query.get(form.livro_id.data)
        aluno = Aluno.query.get(form.aluno_id.data)

        if livro.quantidade_disponivel <= 0:
            flash('Livro não disponível para empréstimo.', 'danger')
            return redirect(url_for('novo_emprestimo'))

        # Verificar multas pendentes
        multas_pendentes = Emprestimo.query.filter_by(aluno_id=aluno.id, multa_paga=False).filter(Emprestimo.multa > 0).count()
        if multas_pendentes > 0:
            flash('Aluno possui multas pendentes. Regularize antes de fazer novo empréstimo.', 'warning')

        emprestimo = Emprestimo(
            livro_id=form.livro_id.data,
            aluno_id=form.aluno_id.data,
            usuario_id=current_user.id,
            data_devolucao_prevista=datetime.utcnow() + timedelta(days=form.dias_prazo.data),
            observacoes=form.observacoes.data
        )

        livro.quantidade_disponivel -= 1
        db.session.add(emprestimo)
        db.session.commit()

        log_acao('Novo Empréstimo', f'Livro: {livro.titulo} | Aluno: {aluno.nome}')
        flash('Empréstimo registrado com sucesso!', 'success')
        return redirect(url_for('listar_emprestimos'))

    return render_template('emprestimos/form.html', form=form, titulo='Novo Empréstimo')

@app.route('/emprestimos/devolver/<int:id>', methods=['GET', 'POST'])
@login_required
@requer_bibliotecario
def devolver_emprestimo(id):
    emprestimo = Emprestimo.query.get_or_404(id)
    form = DevolucaoForm()

    if form.validate_on_submit():
        emprestimo.data_devolucao_real = datetime.utcnow()
        emprestimo.status = 'devolvido'
        emprestimo.observacoes = form.observacoes.data or emprestimo.observacoes
        emprestimo.multa_paga = form.pagar_multa.data

        # Devolver livro
        livro = Livro.query.get(emprestimo.livro_id)
        livro.quantidade_disponivel += 1

        db.session.commit()
        log_acao('Devolução', f'Empréstimo ID: {id} | Livro: {livro.titulo}')
        flash('Devolução registrada com sucesso!', 'success')
        return redirect(url_for('listar_emprestimos'))

    # Calcular multa atual
    emprestimo.atualizar_status()

    return render_template('emprestimos/devolucao.html', emprestimo=emprestimo, form=form)

@app.route('/emprestimos/renovar/<int:id>', methods=['POST'])
@login_required
@requer_bibliotecario
def renovar_emprestimo(id):
    emprestimo = Emprestimo.query.get_or_404(id)

    if emprestimo.status != 'emprestado':
        flash('Apenas empréstimos ativos podem ser renovados.', 'danger')
        return redirect(url_for('listar_emprestimos'))

    emprestimo.data_devolucao_prevista += timedelta(days=Config.DIAS_EMPRESTIMO)
    emprestimo.status = 'emprestado'
    emprestimo.multa = 0.0
    db.session.commit()

    log_acao('Renovação', f'Empréstimo ID: {id}')
    flash('Empréstimo renovado com sucesso!', 'success')
    return redirect(url_for('listar_emprestimos'))

# ==================== RELATÓRIOS ====================

@app.route('/relatorios')
@login_required
@requer_bibliotecario
def relatorios():
    # Estatísticas gerais
    total_livros = Livro.query.filter_by(ativo=True).count()
    total_alunos = Aluno.query.filter_by(ativo=True).count()
    total_emprestimos = Emprestimo.query.count()
    emprestimos_ativos = Emprestimo.query.filter_by(status='emprestado').count()
    emprestimos_atrasados = Emprestimo.query.filter_by(status='atrasado').count()
    emprestimos_devolvidos = Emprestimo.query.filter_by(status='devolvido').count()

    # Multas pendentes
    multas_pendentes = db.session.query(db.func.sum(Emprestimo.multa)).filter(
        Emprestimo.multa_paga == False
    ).scalar() or 0.0

    # Empréstimos por mês (últimos 6 meses)
    hoje = datetime.utcnow()
    meses = []
    for i in range(5, -1, -1):
        mes = hoje - timedelta(days=i*30)
        inicio_mes = mes.replace(day=1, hour=0, minute=0, second=0)
        if i < 5:
            fim_mes = (hoje - timedelta(days=(i-1)*30)).replace(day=1, hour=0, minute=0, second=0)
        else:
            fim_mes = hoje

        count = Emprestimo.query.filter(
            Emprestimo.created_at >= inicio_mes,
            Emprestimo.created_at < fim_mes
        ).count()
        meses.append({
            'mes': inicio_mes.strftime('%b/%Y'),
            'total': count
        })

    # Categorias mais populares
    categorias_populares = db.session.query(
        Livro.categoria, db.func.count(Emprestimo.id).label('total')
    ).join(Emprestimo).filter(Livro.categoria != None).group_by(Livro.categoria).order_by(db.desc('total')).limit(5).all()

    # Alunos com mais empréstimos
    alunos_top = db.session.query(
        Aluno.nome, Aluno.matricula, db.func.count(Emprestimo.id).label('total')
    ).join(Emprestimo).group_by(Aluno.id).order_by(db.desc('total')).limit(10).all()

    return render_template('relatorios/geral.html',
                         total_livros=total_livros,
                         total_alunos=total_alunos,
                         total_emprestimos=total_emprestimos,
                         emprestimos_ativos=emprestimos_ativos,
                         emprestimos_atrasados=emprestimos_atrasados,
                         emprestimos_devolvidos=emprestimos_devolvidos,
                         multas_pendentes=multas_pendentes,
                         meses=meses,
                         categorias_populares=categorias_populares,
                         alunos_top=alunos_top)

@app.route('/relatorios/multas')
@login_required
@requer_bibliotecario
def relatorio_multas():
    emprestimos = Emprestimo.query.filter(Emprestimo.multa > 0).order_by(Emprestimo.created_at.desc()).all()
    total_multas = sum(emp.multa for emp in emprestimos if not emp.multa_paga)
    return render_template('relatorios/multas.html', emprestimos=emprestimos, total_multas=total_multas)

# ==================== USUÁRIOS (ADMIN) ====================

@app.route('/usuarios')
@login_required
@requer_admin
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template('usuarios/listar.html', usuarios=usuarios)

@app.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@requer_admin
def novo_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            tipo=form.tipo.data,
            ativo=form.ativo.data
        )
        usuario.set_password(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        log_acao('Cadastro de Usuário', f'Usuário: {usuario.nome}')
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))

    return render_template('usuarios/form.html', form=form, titulo='Novo Usuário')

# ==================== API JSON ====================

@app.route('/api/livros/disponiveis')
@login_required
def api_livros_disponiveis():
    livros = Livro.query.filter_by(ativo=True).filter(Livro.quantidade_disponivel > 0).all()
    return jsonify([{
        'id': l.id,
        'titulo': l.titulo,
        'autor': l.autor,
        'disponivel': l.quantidade_disponivel
    } for l in livros])

@app.route('/api/alunos/busca')
@login_required
def api_alunos_busca():
    q = request.args.get('q', '')
    alunos = Aluno.query.filter(
        db.or_(
            Aluno.nome.ilike(f'%{q}%'),
            Aluno.matricula.ilike(f'%{q}%')
        )
    ).filter_by(ativo=True).limit(10).all()
    return jsonify([{
        'id': a.id,
        'nome': a.nome,
        'matricula': a.matricula
    } for a in alunos])

# ==================== INICIALIZAÇÃO ====================

def criar_admin():
    with app.app_context():
        db.create_all()

        # Criar usuário admin padrão se não existir
        admin = Usuario.query.filter_by(email='admin@biblioteca.com').first()
        if not admin:
            admin = Usuario(
                nome='Administrador',
                email='admin@biblioteca.com',
                tipo='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Usuário admin criado: admin@biblioteca.com / admin123')

        # Criar bibliotecário de teste
        bib = Usuario.query.filter_by(email='bib@biblioteca.com').first()
        if not bib:
            bib = Usuario(
                nome='Bibliotecário',
                email='bib@biblioteca.com',
                tipo='bibliotecario'
            )
            bib.set_password('bib123')
            db.session.add(bib)
            db.session.commit()
            print('Usuário bibliotecário criado: bib@biblioteca.com / bib123')

if __name__ == '__main__':
    criar_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)
