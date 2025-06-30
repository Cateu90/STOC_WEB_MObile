from fastapi import FastAPI, Request, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from repo.user_repo import UserRepo
from repo.categoria_repo import CategoriaRepo
from repo.produto_repo import ProdutoRepo
from repo.impressora_repo import ImpressoraRepo
from repo.comanda_repo import ComandaRepo
from repo.mesa_repo import MesaRepo
from repo.item_comanda_repo import ItemComandaRepo
from models.user import User
from models.categoria import Categoria
from models.produto import Produto
from models.impressora import Impressora
from models.comanda import Comanda
from models.item_comanda import ItemComanda
from util.auth import hash_password, verify_password
from util.permissions import require_role
from itsdangerous import URLSafeSerializer
import os
from data.db import get_db
from datetime import date, datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from util.init_db import executar_sqls_iniciais
from jose import jwt
from fastapi.staticfiles import StaticFiles
from decimal import Decimal
from fastapi import Body
from typing import Any, Dict, List
from pydantic import BaseModel
import asyncio
import os
import platform
from services.print_service import PrintService
import traceback
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from util.network_info import get_ip_and_port


def json_serializable(data):
    if isinstance(data, list):
        return [json_serializable(item) for item in data]
    if isinstance(data, dict):
        return {key: json_serializable(value) for key, value in data.items()}
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    return data

app = FastAPI()

# Adiciona CORS para permitir requisições do app mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou especifique o IP do app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)

app.mount("/static", StaticFiles(directory="static"), name="static")
api_router = APIRouter(prefix="/api")

SECRET_KEY = os.getenv("SECRET_KEY", "stoc-secret-key")
JWT_SECRET = os.getenv("JWT_SECRET", "stoc-jwt-secret")
JWT_ALGORITHM = "HS256"
session_serializer = URLSafeSerializer(SECRET_KEY)

templates = Jinja2Templates(directory="templates")

executar_sqls_iniciais("sql")

try:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT IGNORE INTO categorias (nome, impressora_id) VALUES ('PDV', NULL)")
    db.commit()
    cursor.close()
    db.close()
except Exception as e:
    print(f"[INFO] Categoria PDV já existe ou erro: {e}")

def criar_mesas_padrao(user_email):
    """Função mantida para compatibilidade, mas não cria mesas automaticamente"""
    try:
        from repo.mesa_repo import MesaRepo
        mesas_existentes = MesaRepo.listar_mesas(user_email=user_email)
        
        print(f"[INFO] {len(mesas_existentes)} mesas encontradas para {user_email}")
        print(f"[INFO] Garçom pode cadastrar suas próprias mesas pelo app mobile")
        
        # Não criar mesas automaticamente - deixar o garçom cadastrar pelo app
        
    except Exception as e:
        print(f"[WARNING] Erro ao verificar mesas para {user_email}: {e}")
        # Não é um erro crítico - garçom pode trabalhar sem mesas

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": None, "success": None})

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": None, "success": None})

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    if not name.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Nome é obrigatório!", "success": None})
    
    if not email.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail é obrigatório!", "success": None})
    
    if len(password) < 6:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha deve ter pelo menos 6 caracteres!", "success": None})
    
    if password != confirm:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "As senhas não coincidem!", "success": None})
    
    existing_user = UserRepo.get_user_by_email(email.lower())
    if existing_user:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": f"E-mail {email} já está cadastrado! Use outro e-mail ou faça login.", "success": None})
    
    try:
        hashed = hash_password(password)
        user = User(name=name.strip(), email=email.lower().strip(), password=hashed, role="admin")
        UserRepo.create_user(user)
        from data.db import ensure_user_database_exists
        from util.init_db import executar_sqls_iniciais
        ensure_user_database_exists(email.lower().strip())
        executar_sqls_iniciais("sql", user_email=email.lower().strip())
        return RedirectResponse("/login?success=1", status_code=303)
    except Exception as e:
        print(f"[ERROR] Erro ao criar usuário: {e}")
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Erro interno. Tente novamente.", "success": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    if not email.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail é obrigatório!", "success": None})
    
    if not password.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha é obrigatória!", "success": None})
    
    user = UserRepo.get_user_by_email(email.lower().strip())
    if not user:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail não encontrado! Verifique o e-mail ou crie uma conta.", "success": None})
    
    if not verify_password(password, user['password']):
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha incorreta! Tente novamente.", "success": None})
    
    try:
        from data.db import ensure_user_database_exists
        from util.init_db import executar_sqls_iniciais
        ensure_user_database_exists(user['email'])
        executar_sqls_iniciais("sql", user_email=user['email'])
        # Criar mesas padrão se não existirem
        criar_mesas_padrao(user['email'])
    except Exception as e:
        print(f"[ERROR] Falha ao inicializar DB para {user['email']} no login: {e}")
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Ocorreu um erro ao preparar sua conta. Tente novamente.", "success": None})

    session_data = session_serializer.dumps(user)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("session", session_data, max_age=86400, httponly=True)
    return response

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE status='aberta'")
    comandas_abertas = cursor.fetchone()["total"]
    hoje = date.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(total) as vendas_hoje FROM comandas WHERE status='fechada' AND DATE(created_at) = %s", (hoje,))
    vendas_hoje = cursor.fetchone()["vendas_hoje"] or 0
    cursor.execute("SELECT COUNT(*) as total FROM produtos")
    produtos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM impressoras")
    impressoras = cursor.fetchone()["total"]
    cursor.close()
    db.close()
    dashboard = {
        "comandas_abertas": comandas_abertas,
        "vendas_hoje": vendas_hoje,
        "produtos": produtos,
        "impressoras": impressoras
    }
    from datetime import datetime
    now = datetime.now()
    ip, port = get_ip_and_port()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "dashboard": dashboard,
        "now": now,
        "backend_ip": ip,
        "backend_port": port
    })


@app.get("/pdv", response_class=HTMLResponse)
def pdv(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    if not any(cat['id'] == 0 for cat in categorias_unicas):
        categorias_unicas.insert(0, {"id": 0, "nome": "Sem Categoria"})
    
    comandas_abertas = ComandaRepo.listar_comandas_abertas(user_email=user['email'])

    return templates.TemplateResponse("pdv.html", {
        "request": request,
        "user": user,
        "categorias": categorias_unicas,
        "comandas_abertas": comandas_abertas,
        "active_page": "pdv"
    })


@app.get("/produtos", response_class=HTMLResponse)
def produtos(request: Request, page: int = 1, success: int = 0, deleted: int = 0):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    page_size = 20
    offset = (page - 1) * page_size
    produtos = ProdutoRepo.listar_produtos(offset=offset, limit=page_size, user_email=user['email'])
    total_produtos = ProdutoRepo.contar_produtos(user_email=user['email'])
    total_pages = (total_produtos + page_size - 1) // page_size
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_ids = set()
    for cat in categorias:
        if cat['id'] not in seen_ids:
            categorias_unicas.append(cat)
            seen_ids.add(cat['id'])
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produtos.html", {
        "request": request,
        "produtos": produtos,
        "user": user,
        "active_page": "produtos",
        "page": page,
        "total_pages": total_pages,
        "success": success,
        "deleted": deleted,
        "categorias": categorias_unicas
    })

@app.get("/produtos/novo", response_class=HTMLResponse)
def produto_novo_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'].lower() == 'pdv':
            continue
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produto_novo.html", {"request": request, "categorias": categorias_unicas, "user": user})

@app.post("/produtos/novo", response_class=HTMLResponse)
def produto_novo(request: Request, nome: str = Form(...), preco: float = Form(...), categoria_id: int = Form(...), tipo: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    produto = Produto(nome=nome, preco=preco, categoria_id=categoria_id, tipo=tipo)
    try:
        ProdutoRepo.criar_produto(produto, user_email=user['email'])
        return RedirectResponse("/produtos?success=1", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao criar produto: {e}")
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        return templates.TemplateResponse("produto_novo.html", {"request": request, "categorias": categorias, "user": user, "error": "Erro ao criar produto!"})

@app.post("/produtos/{produto_id}/excluir", response_class=HTMLResponse)
def produto_excluir(request: Request, produto_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        from repo.produto_repo import ProdutoRepo
        ProdutoRepo.excluir_produto(produto_id, user_email=user['email'])
        return RedirectResponse("/produtos?deleted=1", status_code=302)
    except Exception as e:
        error_message = f"Erro ao excluir produto: {e}"
        print(f"[ERROR] {error_message}")
        page_size = 20
        page = 1
        offset = (page - 1) * page_size
        produtos = ProdutoRepo.listar_produtos(offset=offset, limit=page_size, user_email=user['email'])
        total_produtos = ProdutoRepo.contar_produtos(user_email=user['email'])
        total_pages = (total_produtos + page_size - 1) // page_size
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        categorias_unicas = []
        seen_ids = set()
        for cat in categorias:
            if cat['id'] not in seen_ids:
                categorias_unicas.append(cat)
                seen_ids.add(cat['id'])
    return templates.TemplateResponse("produtos.html", {
        "request": request, 
        "produtos": produtos, 
        "user": user, 
        "active_page": "produtos", 
        "error": error_message,
        "page": page,
        "total_pages": total_pages,
        "categorias": categorias_unicas,
        "success": 0,
        "deleted": 0
    })

@app.get("/produtos/{produto_id}/editar", response_class=HTMLResponse)
def produto_editar_form(request: Request, produto_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
    if not produto:
        return RedirectResponse("/produtos", status_code=302)
    
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'].lower() == 'pdv':
            continue
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produto_editar.html", {
        "request": request, 
        "produto": produto,
        "categorias": categorias_unicas, 
        "user": user
    })

@app.post("/produtos/{produto_id}/editar", response_class=HTMLResponse)
def produto_editar(request: Request, produto_id: int, nome: str = Form(...), preco: float = Form(...), categoria_id: int = Form(...), tipo: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        ProdutoRepo.editar_produto(produto_id, nome, preco, categoria_id, tipo, user_email=user['email'])
        return RedirectResponse("/produtos", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao editar produto: {e}")
        produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        return templates.TemplateResponse("produto_editar.html", {"request": request, "produto": produto, "categorias": categorias, "user": user, "error": "Erro ao editar produto!"})

@app.get("/categorias", response_class=HTMLResponse)
def categorias(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    categorias = [
        {"id": 1, "nome": "Comida"},
        {"id": 2, "nome": "Bebida"},
        {"id": 3, "nome": "Sobremesa"},
        {"id": 4, "nome": "PDV"},
        {"id": 5, "nome": "Outros"}
    ]
    return templates.TemplateResponse("categorias.html", {"request": request, "categorias": categorias, "user": user})

@app.get("/categorias/novo", response_class=HTMLResponse)
def categoria_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse("/categorias", status_code=302)

@app.post("/categorias/novo", response_class=HTMLResponse)
def categoria_nova(request: Request, nome: str = Form(...), impressora_id: str = Form(None)):
    return RedirectResponse("/categorias", status_code=302)

@app.get("/impressoras", response_class=HTMLResponse)
def impressoras(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    impressoras = ImpressoraRepo.listar_impressoras(user_email=user['email'])
    return templates.TemplateResponse("impressoras.html", {"request": request, "impressoras": impressoras, "user": user})

@app.get("/impressoras/novo", response_class=HTMLResponse)
def impressora_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        import win32print
        printers = [p[2] for p in win32print.EnumPrinters(2)]
    except ImportError:
        printers = ["Impressora1", "Impressora2"]
    categorias = [
        {"id": 1, "nome": "Comida"},
        {"id": 2, "nome": "Bebida"},
        {"id": 3, "nome": "Sobremesa"},
        {"id": 4, "nome": "PDV"},
        {"id": 5, "nome": "Outros"}
    ]
    return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "printers": printers, "categorias": categorias})

@app.post("/impressoras/novo", response_class=HTMLResponse)
def impressora_nova(request: Request, nome: str = Form(...), setor: str = Form(...), printer_name: str = Form(...), categorias: list = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not nome or not setor or not printer_name or not categorias:
        categorias_fixas = [
            {"id": 1, "nome": "Comida"},
            {"id": 2, "nome": "Bebida"},
            {"id": 3, "nome": "Sobremesa"},
            {"id": 4, "nome": "PDV"},
            {"id": 5, "nome": "Outros"}
        ]
        return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "error": "Preencha todos os campos!", "printers": [], "categorias": categorias_fixas})
    try:
        impressora = Impressora(nome=nome, setor=setor)
        impressora_id = ImpressoraRepo.criar_impressora_retorna_id(impressora, printer_name, user_email=user['email'])
        db = get_db(user['email'])
        cursor = db.cursor()
        for cat_id in categorias:
            cursor.execute("INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)", (impressora_id, int(cat_id)))
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        categorias_fixas = [
            {"id": 1, "nome": "Comida"},
            {"id": 2, "nome": "Bebida"},
            {"id": 3, "nome": "Sobremesa"},
            {"id": 4, "nome": "PDV"},
            {"id": 5, "nome": "Outros"}
        ]
        return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "error": f"Erro ao adicionar impressora: {e}", "printers": [], "categorias": categorias_fixas})
    return RedirectResponse("/impressoras", status_code=302)

@app.post("/impressoras/{impressora_id}/excluir", response_class=HTMLResponse)
def impressora_excluir(request: Request, impressora_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        ImpressoraRepo.excluir_impressora(impressora_id, user_email=user['email'])
    except Exception as e:
        pass
    return RedirectResponse("/impressoras", status_code=302)

@app.get("/comandas", response_class=HTMLResponse)
def comandas(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    require_role(request, ["admin", "garcom"])
    comandas = ComandaRepo.listar_todas_comandas(user_email=user['email'])
    usuarios = UserRepo.listar_usuarios()
    garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
    for c in comandas:
        c['garcom_nome'] = garcons_dict.get(c['garcom_id'], '---')
    return templates.TemplateResponse("comandas.html", {"request": request, "comandas": comandas, "user": user, "active_page": "comandas"})

@app.get("/comandas/nova", response_class=HTMLResponse)
def comanda_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    mesas = MesaRepo.listar_mesas(user_email=user['email'])
    garcons = [u for u in UserRepo.listar_usuarios() if u['role'] == 'garcom']
    return templates.TemplateResponse("comanda_nova.html", {"request": request, "mesas": mesas, "garcons": garcons, "user": user})

@app.post("/comandas/nova", response_class=HTMLResponse)
def comanda_nova(request: Request, mesa_id: int = Form(...), garcom_id: int = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    comanda = Comanda(mesa_id=mesa_id, garcom_id=garcom_id, status="aberta")
    ComandaRepo.abrir_comanda(comanda, user_email=user['email'])
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse("/comandas", status_code=302)

@app.get("/comandas/{comanda_id}", response_class=HTMLResponse)
def comanda_itens(request: Request, comanda_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        comanda = ComandaRepo.get_comanda_por_id(comanda_id, user_email=user['email'])
        if not comanda:
            return RedirectResponse("/comandas", status_code=302)
        from repo.user_repo import UserRepo
        usuarios = UserRepo.listar_usuarios()
        garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
        comanda['garcom_nome'] = garcons_dict.get(comanda.get('garcom_id'), '---')
        itens = ItemComandaRepo.listar_itens(comanda_id, user_email=user['email']) or []
        print(f"[DEBUG] Itens da comanda {comanda_id}: {itens}")
        produtos = ProdutoRepo.listar_produtos(user_email=user['email']) or []
        for item in itens:
            if 'produto_id' not in item:
                item['produto_id'] = None
            if 'quantidade' not in item:
                item['quantidade'] = 0
            if 'preco_unitario' not in item:
                item['preco_unitario'] = 0.0
        return templates.TemplateResponse("comanda_itens.html", {"request": request, "comanda": comanda, "itens": itens, "produtos": produtos, "user": user, "error": None, "status": comanda.get('status', '')})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return templates.TemplateResponse("comanda_itens.html", {"request": request, "comanda": {}, "itens": [], "produtos": [], "user": user, "error": f"Erro interno: {e}\n{tb}"})

@app.post("/comandas/{comanda_id}", response_class=HTMLResponse)
def comanda_adicionar_item(request: Request, comanda_id: int, produto_id: int = Form(...), quantidade: int = Form(...)):
    print(f"[DEBUG] POST /comandas/{comanda_id} chamado com produto_id={produto_id}, quantidade={quantidade}")
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    produtos = ProdutoRepo.listar_produtos(user_email=user['email'])
    produto = next((p for p in produtos if p['id'] == produto_id), None)
    if not produto:
        return RedirectResponse(f"/comandas/{comanda_id}", status_code=302)
    item = ItemComanda(comanda_id=comanda_id, produto_id=produto_id, quantidade=quantidade, preco_unitario=produto['preco'])
    ItemComandaRepo.adicionar_item(item, user_email=user['email'])
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse(f"/comandas/{comanda_id}", status_code=302)

@app.get("/comandas/{comanda_id}/fechar", response_class=HTMLResponse)
def comanda_fechar_form(request: Request, comanda_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    comandas = ComandaRepo.listar_comandas_abertas(user_email=user['email'])
    comanda = next((c for c in comandas if c['id'] == comanda_id), None)
    if not comanda:
        return RedirectResponse("/comandas", status_code=302)
    itens = ItemComandaRepo.listar_itens(comanda_id, user_email=user['email'])
    return templates.TemplateResponse("comanda_fechar.html", {"request": request, "comanda": comanda, "itens": itens, "user": user})

@app.post("/comandas/{comanda_id}/fechar", response_class=HTMLResponse)
def comanda_fechar(request: Request, comanda_id: int, pagamento: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT SUM(quantidade * preco_unitario) as total 
        FROM itens_comanda 
        WHERE comanda_id = %s
    """, (comanda_id,))
    
    result = cursor.fetchone()
    total = result['total'] if result and result['total'] else 0.0
    
    cursor.execute("""
        UPDATE comandas 
        SET status='fechada', total=%s, pagamento=%s 
        WHERE id=%s
    """, (total, pagamento, comanda_id))
    
    db.commit()
    cursor.close()
    db.close()
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse("/comandas", status_code=302)

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios(request: Request, inicio: str = None, fim: str = None):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not inicio or not fim:
        hoje = date.today()
        inicio = hoje.strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
    
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT c.id, c.garcom_id, c.pagamento, c.total, c.created_at 
        FROM comandas c 
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        ORDER BY c.created_at DESC
    """, (inicio, fim))
    comandas = cursor.fetchall()
    
    cursor.execute("""
        SELECT p.nome as produto_nome, SUM(ic.quantidade) as total_vendido, 
               SUM(ic.quantidade * ic.preco_unitario) as total_faturado
        FROM itens_comanda ic 
        JOIN comandas c ON ic.comanda_id = c.id 
        JOIN produtos p ON ic.produto_id = p.id
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        GROUP BY ic.produto_id, p.nome 
        ORDER BY total_vendido DESC 
        LIMIT 10
    """, (inicio, fim))
    mais_vendidos = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.garcom_id, COUNT(*) as comandas, SUM(c.total) as total_vendas 
        FROM comandas c 
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        GROUP BY c.garcom_id 
        ORDER BY total_vendas DESC
    """, (inicio, fim))
    ranking = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_comandas,
            SUM(total) as faturamento_total,
            AVG(total) as ticket_medio
        FROM comandas 
        WHERE status='fechada' AND DATE(created_at) BETWEEN %s AND %s
    """, (inicio, fim))
    estatisticas = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    from repo.user_repo import UserRepo
    usuarios = UserRepo.listar_usuarios()
    garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
    for c in comandas:
        c['garcom_nome'] = garcons_dict.get(c['garcom_id'], '---')
    for r in ranking:
        r['garcom_nome'] = garcons_dict.get(r['garcom_id'], '---')
    
    return templates.TemplateResponse("relatorios.html", {
        "request": request, 
        "comandas": comandas,
        "mais_vendidos": mais_vendidos,
        "ranking": ranking,
        "estatisticas": estatisticas,
        "inicio": inicio,
        "fim": fim,
        "user": user
    })

@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user['role'] == 'admin':
        usuarios = [u for u in UserRepo.listar_usuarios() if u.get('admin_id') == user['id'] and u['role'] == 'garcom']
    else:
        usuarios = [user]
    return templates.TemplateResponse("usuarios.html", {"request": request, "usuarios": usuarios, "user": user, "active_page": "usuarios"})

@app.get("/usuarios/novo", response_class=HTMLResponse)
def usuario_novo_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios"})

@app.post("/usuarios/novo", response_class=HTMLResponse)
def usuario_novo(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not name or not email or not password:
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": "Preencha todos os campos!"})
    if UserRepo.get_user_by_email(email.lower()):
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": "E-mail já cadastrado!"})
    from util.auth import hash_password
    hashed = hash_password(password)
    admin_id = user['id'] if user['role'] == 'admin' else None
    novo = User(name=name, email=email.lower(), password=hashed, role="garcom", admin_id=admin_id)
    try:
        UserRepo.create_user(novo)
    except Exception as e:
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": f"Erro ao cadastrar usuário: {e}"})
    return RedirectResponse("/usuarios", status_code=302)

@app.post("/usuarios/{usuario_id}/excluir", response_class=HTMLResponse)
def usuario_excluir(request: Request, usuario_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    UserRepo.excluir_usuario(usuario_id)
    return RedirectResponse("/usuarios", status_code=302)


def get_logged_user_api(request: Request) -> Dict[str, Any]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_data = session_serializer.loads(session_token)
        return user_data
    except Exception:
        return None

class ItemVenda(BaseModel):
    id: int
    qtd: int
    preco: float

class Venda(BaseModel):
    itens: List[ItemVenda]
    pagamento: str

@api_router.delete("/produtos/{produto_id}")
def api_delete_produto(request: Request, produto_id: int):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"success": False, "message": "Não autorizado"})
    
    try:
        produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
        if not produto:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"success": False, "message": "Produto não encontrado"})

        ProdutoRepo.excluir_produto(produto_id, user_email=user['email'])
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": "Produto desativado com sucesso"})
    except Exception as e:
        print(f"[ERROR] Erro ao desativar produto via API: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"success": False, "message": f"Erro interno no servidor: {e}"})

@api_router.post("/pdv/venda")
async def api_pdv_venda(request: Request, venda: Venda):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Não autorizado"})

    print(f"[DEBUG] Venda recebida: {venda}")
    print(f"[DEBUG] Itens recebidos: {getattr(venda, 'itens', None)}")

    db = None
    try:
        impressora_pdv = ImpressoraRepo.get_impressora_por_nome_categoria("PDV", user_email=user['email'])
        if not impressora_pdv:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Impressora não configurada para o PDV. Por favor, cadastre uma impressora e associe-a à categoria 'PDV' nas configurações."}
            )

        db = get_db(user['email'])
        cursor = db.cursor(dictionary=True)
        db.start_transaction()

        pdv_user = UserRepo.get_user_by_name("PDV", user_email=user['email'])
        garcom_id = pdv_user['id'] if pdv_user else None
        if not garcom_id:
            garcom_id = user['id']
        comanda = Comanda(mesa_id=None, garcom_id=garcom_id, status="aberta")
        sql_comanda = "INSERT INTO comandas (garcom_id, status) VALUES (%s, %s)"
        cursor.execute(sql_comanda, (comanda.garcom_id, comanda.status))
        comanda_id = cursor.lastrowid

        total_venda = Decimal(0)
        itens_para_impressao = []
        for item in venda.itens:
            produto_db = ProdutoRepo.get_produto_por_id(item.id, user_email=user['email'])
            if not produto_db:
                db.rollback()
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": f"Produto com ID {item.id} não encontrado."})
            preco_unitario = Decimal(produto_db['preco'])
            item_comanda = ItemComanda(
                comanda_id=comanda_id,
                produto_id=item.id,
                quantidade=item.qtd,
                preco_unitario=preco_unitario
            )
            ItemComandaRepo.adicionar_item(item_comanda, db=db, cursor=cursor)
            total_venda += item.qtd * preco_unitario
            itens_para_impressao.append({"nome": produto_db['nome'], "qtd": item.qtd, "preco": preco_unitario})

        ComandaRepo.fechar_comanda(comanda_id, total_venda, venda.pagamento, db=db, cursor=cursor)
        db.commit()

        texto_comprovante = gerar_texto_comprovante(comanda_id, itens_para_impressao, total_venda, venda.pagamento)
        resultado_impressao = PrintService.imprimir_texto(texto_comprovante, impressora_pdv['printer_name'])
        status_impressao = ""
        if resultado_impressao["status"] == "success":
            status_impressao = "Comprovante impresso com sucesso"
            print(f"[INFO] Comprovante da venda {comanda_id} enviado para a impressora {impressora_pdv['printer_name']}.")
        else:
            status_impressao = f"Falha ao imprimir: {resultado_impressao['message']}"
            print(f"[ERROR] Falha ao imprimir comprovante da venda {comanda_id}: {resultado_impressao['message']}")

        return JSONResponse(content={"success": True, "comanda_id": comanda_id, "message": "Venda finalizada com sucesso.", "print_status": status_impressao})

    except Exception as e:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        print(f"[ERROR] Erro ao finalizar venda direta no PDV: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Erro interno ao processar a venda."})
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if db is not None and db.is_connected():
                db.close()
        except Exception:
            pass

def gerar_texto_comprovante(comanda_id, itens, total, pagamento):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto = f"COMPROVANTE DE VENDA\n"
    texto += f"Data: {now}\n"
    texto += "-" * 30 + "\n"
    texto += "Qtd  Produto             Preco\n"
    for item in itens:
        nome_produto = item['nome'][:18].ljust(18)
        preco_str = f"R$ {item['preco']:.2f}".rjust(7)
        texto += f"{item['qtd']:<3} {nome_produto} {preco_str}\n"
    texto += "-" * 30 + "\n"
    texto += f"TOTAL: R$ {total:.2f}\n"
    texto += f"PAGAMENTO: {pagamento.upper()}\n\n"
    texto += "Obrigado!\n"
    return texto

@api_router.get("/produtos/{categoria_id}")
def api_get_produtos_por_categoria(request: Request, categoria_id: str):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Não autorizado"})
    
    try:
        if categoria_id.lower() == 'all':
            produtos = ProdutoRepo.listar_produtos(user_email=user['email'])
        elif categoria_id.lower() == 'sem-categoria':
            produtos = ProdutoRepo.listar_produtos_sem_categoria(user_email=user['email'])
        else:
            produtos = ProdutoRepo.listar_produtos_por_categoria(int(categoria_id), user_email=user['email'])
        
        return JSONResponse(content=json_serializable(produtos))
    except Exception as e:
        print(f"[ERROR] Erro ao buscar produtos por categoria via API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

@api_router.post("/login")
async def api_login(login_data: LoginRequest):
    try:
        print(f"[INFO] Tentativa de login para: {login_data.email}")
        
        user = UserRepo.get_user_by_email(login_data.email)
        from util.auth import verify_password
        
        if not user:
            print(f"[WARNING] Usuário não encontrado: {login_data.email}")
            return JSONResponse({"error": "Credenciais inválidas."}, status_code=401)
        
        if not verify_password(login_data.password, user['password']):
            print(f"[WARNING] Senha incorreta para: {login_data.email}")
            return JSONResponse({"error": "Credenciais inválidas."}, status_code=401)
        
        if user['role'] not in ['admin', 'garcom']:
            print(f"[WARNING] Role não autorizado: {user['role']} para {login_data.email}")
            return JSONResponse({"error": "Usuário não autorizado para o app mobile."}, status_code=401)
        
        # Para garçons, garantir que o banco de dados existe
        if user['role'] == 'garcom':
            try:
                print(f"[INFO] Inicializando ambiente para garçom: {login_data.email}")
                from data.db import ensure_user_database_exists
                from util.init_db import executar_sqls_iniciais
                
                # Garantir que o banco de dados existe
                ensure_user_database_exists(user['email'])
                
                # Executar SQLs iniciais
                executar_sqls_iniciais("sql", user_email=user['email'])
                
                # Verificar mesas existentes (não criar automaticamente)
                criar_mesas_padrao(user['email'])
                
                print(f"[SUCCESS] Ambiente inicializado para garçom: {login_data.email}")
                print(f"[INFO] Garçom pode cadastrar mesas pelo app mobile")
                
            except Exception as e:
                print(f"[ERROR] Erro ao inicializar ambiente para garçom {login_data.email}: {e}")
                import traceback
                traceback.print_exc()
                return JSONResponse({"error": "Erro ao preparar seu ambiente. Tente novamente."}, status_code=500)
        
        # Gera um token JWT simples
        token = jwt.encode({"id": user['id'], "email": user['email'], "role": user['role']}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        print(f"[SUCCESS] Login bem-sucedido para: {login_data.email}")
        return {"token": token, "id": user['id'], "name": user['name'], "role": user['role']}
        
    except Exception as e:
        print(f"[ERROR] Erro no login para {login_data.email}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.get("/mesas")
def api_listar_mesas(request: Request):
    # Verificar se o usuário está autenticado
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_email = payload.get("email")
        
        print(f"[INFO] Listando mesas para usuário: {user_email}")
        
        # Garantir que o ambiente está configurado, mas permitir que funcione mesmo com erros
        try:
            from data.db import ensure_user_database_exists
            from util.init_db import executar_sqls_iniciais
            
            ensure_user_database_exists(user_email)
            executar_sqls_iniciais("sql", user_email=user_email)
            
        except Exception as setup_error:
            print(f"[WARNING] Erro ao configurar ambiente para {user_email}: {setup_error}")
            # Continuar mesmo com erro de configuração
        
        # Tentar listar mesas, mas retornar lista vazia se houver erro
        try:
            from repo.mesa_repo import MesaRepo
            mesas = MesaRepo.listar_mesas(user_email=user_email)
            print(f"[SUCCESS] {len(mesas)} mesas encontradas para {user_email}")
            return mesas
        except Exception as mesa_error:
            print(f"[WARNING] Erro ao listar mesas para {user_email}: {mesa_error}")
            print(f"[INFO] Retornando lista vazia - garçom pode cadastrar mesas pelo app")
            # Retornar lista vazia em caso de erro - não impedir o login
            return []
        
    except jwt.JWTError:
        return JSONResponse({"error": "Token inválido"}, status_code=401)
    except Exception as e:
        print(f"[ERROR] Erro crítico ao listar mesas: {e}")
        import traceback
        traceback.print_exc()
        # Retornar lista vazia mesmo em caso de erro crítico
        print("[INFO] Retornando lista vazia devido a erro crítico")
        return []

@api_router.post("/mesas")
async def api_cadastrar_mesa(request: Request, nome: str = Form(...)):
    """API para cadastrar uma nova mesa pelo app mobile"""
    # Verificar se o usuário está autenticado
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_email = payload.get("email")
        
        print(f"[INFO] Cadastrando nova mesa '{nome}' para usuário: {user_email}")
        
        # Validar nome da mesa
        if not nome or not nome.strip():
            return JSONResponse({"error": "Nome da mesa é obrigatório"}, status_code=400)
        
        nome = nome.strip()
        
        # Garantir que o ambiente está configurado antes de cadastrar
        try:
            from data.db import ensure_user_database_exists
            from util.init_db import executar_sqls_iniciais
            
            ensure_user_database_exists(user_email)
            executar_sqls_iniciais("sql", user_email=user_email)
            
        except Exception as setup_error:
            print(f"[ERROR] Erro crítico ao configurar ambiente para {user_email}: {setup_error}")
            return JSONResponse({"error": "Erro ao configurar ambiente. Tente novamente."}, status_code=500)
        
        # Verificar se já existe uma mesa com esse nome
        try:
            from repo.mesa_repo import MesaRepo
            mesas_existentes = MesaRepo.listar_mesas(user_email=user_email)
            
            for mesa in mesas_existentes:
                if mesa['nome'].lower() == nome.lower():
                    return JSONResponse({"error": f"Já existe uma mesa com o nome '{nome}'"}, status_code=400)
        except Exception as check_error:
            print(f"[WARNING] Erro ao verificar mesas existentes: {check_error}")
            # Continuar mesmo com erro - pode ser a primeira mesa
        
        # Criar a nova mesa
        try:
            db = get_db(user_email)
            cursor = db.cursor()
            cursor.execute("INSERT INTO mesas (nome) VALUES (%s)", (nome,))
            mesa_id = cursor.lastrowid
            db.commit()
            cursor.close()
            db.close()
            
            print(f"[SUCCESS] Mesa '{nome}' cadastrada com sucesso para {user_email}")
            
            return JSONResponse({
                "success": True,
                "message": f"Mesa '{nome}' cadastrada com sucesso!",
                "mesa": {
                    "id": mesa_id,
                    "nome": nome
                }
            })
        except Exception as db_error:
            print(f"[ERROR] Erro ao cadastrar mesa no banco: {db_error}")
            return JSONResponse({"error": "Erro ao salvar mesa no banco de dados"}, status_code=500)
        
    except jwt.JWTError:
        return JSONResponse({"error": "Token inválido"}, status_code=401)
    except Exception as e:
        print(f"[ERROR] Erro ao cadastrar mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.delete("/mesas/{mesa_id}")
async def api_excluir_mesa(request: Request, mesa_id: int):
    """API para excluir uma mesa pelo app mobile"""
    # Verificar se o usuário está autenticado
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_email = payload.get("email")
        
        print(f"[INFO] Excluindo mesa ID {mesa_id} para usuário: {user_email}")
        
        # Verificar se a mesa existe
        from repo.mesa_repo import MesaRepo
        mesas = MesaRepo.listar_mesas(user_email=user_email)
        mesa_encontrada = None
        
        for mesa in mesas:
            if mesa['id'] == mesa_id:
                mesa_encontrada = mesa
                break
        
        if not mesa_encontrada:
            return JSONResponse({"error": "Mesa não encontrada"}, status_code=404)
        
        # Verificar se há comandas abertas nesta mesa
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE mesa_id = %s AND status = 'aberta'", (mesa_id,))
        result = cursor.fetchone()
        
        if result and result['total'] > 0:
            cursor.close()
            db.close()
            return JSONResponse({"error": "Não é possível excluir uma mesa com comandas abertas"}, status_code=400)
        
        # Excluir a mesa
        cursor.execute("DELETE FROM mesas WHERE id = %s", (mesa_id,))
        db.commit()
        cursor.close()
        db.close()
        
        print(f"[SUCCESS] Mesa '{mesa_encontrada['nome']}' excluída com sucesso para {user_email}")
        
        return JSONResponse({
            "success": True,
            "message": f"Mesa '{mesa_encontrada['nome']}' excluída com sucesso!"
        })
        
    except jwt.JWTError:
        return JSONResponse({"error": "Token inválido"}, status_code=401)
    except Exception as e:
        print(f"[ERROR] Erro ao excluir mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.get("/categorias")
def api_listar_categorias():
    from repo.categoria_repo import CategoriaRepo
    categorias = CategoriaRepo.listar_categorias()
    return categorias

@api_router.get("/comandas/{garcom_id}")
def api_listar_comandas(garcom_id: int):
    from repo.comanda_repo import ComandaRepo
    comandas = ComandaRepo.listar_comandas_por_garcom(garcom_id)
    return comandas

@api_router.post("/comandas/abrir")
def api_abrir_comanda(mesa_id: int = Form(...), garcom_id: int = Form(...)):
    from models.comanda import Comanda
    from repo.comanda_repo import ComandaRepo
    comanda = Comanda(mesa_id=mesa_id, garcom_id=garcom_id, status="aberta")
    comanda_id = ComandaRepo.abrir_comanda(comanda)
    return {"success": True, "comanda_id": comanda_id}

@api_router.post("/comandas/{comanda_id}/item")
def api_adicionar_item(comanda_id: int, produto_id: int = Form(...), quantidade: int = Form(...)):
    from repo.produto_repo import ProdutoRepo
    from repo.item_comanda_repo import ItemComandaRepo
    from models.item_comanda import ItemComanda
    produtos = ProdutoRepo.listar_produtos()
    produto = next((p for p in produtos if p['id'] == produto_id), None)
    if not produto:
        return JSONResponse({"error": "Produto não encontrado."}, status_code=404)
    item = ItemComanda(comanda_id=comanda_id, produto_id=produto_id, quantidade=quantidade, preco_unitario=produto['preco'])
    ItemComandaRepo.adicionar_item(item)
    return {"success": True}

@api_router.get("/produtos")
def api_listar_produtos():
    from repo.produto_repo import ProdutoRepo
    produtos = ProdutoRepo.listar_produtos(offset=0, limit=1000)
    def decimal_to_float(obj):
        if isinstance(obj, list):
            return [decimal_to_float(item) for item in obj]
        if isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        if isinstance(obj, Decimal):
            return float(obj)
        return obj
    return decimal_to_float(produtos)

app.include_router(api_router)

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/comandas")
async def websocket_comandas(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("update")

async def notify_comandas_update():
    await manager.broadcast("update")

def get_logged_user(request: Request):
    if 'user' in request.scope:
        return request.scope.get('user')
    
    session_data = request.cookies.get("session")
    if not session_data:
        request.scope['user'] = None
        return None
    try:
        user_data = session_serializer.loads(session_data)
        request.scope['user'] = user_data
        return user_data
    except Exception:
        request.scope['user'] = None
        return None

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Detecta automaticamente o IP da rede local
    ip, port = get_ip_and_port()
    port = int(port)
    
    print("🚀 Iniciando servidor STOC...")
    print("=" * 50)
    print(f"📡 IP detectado automaticamente: {ip}")
    print(f"🔌 Porta: {port}")
    print("=" * 50)
    print(f"🌐 Para acessar via app mobile use:")
    print(f"   http://{ip}:{port}/api")
    print(f"💻 Para acessar via web use:")
    print(f"   http://{ip}:{port}")
    print("=" * 50)
    print("💡 Dica: No app Flutter, use exatamente:")
    print(f"   http://{ip}:{port}/api")
    print("=" * 50)
    
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
