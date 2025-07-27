# Flask Dr. Julio

Aplicação web em Flask para gerenciamento de agendamentos, eventos e conteúdo do site do Dr. Julio.

## Instalação

1. Crie um ambiente virtual e ative-o:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Como executar

A aplicação pode ser iniciada diretamente usando `run.py`:

```bash
python run.py
```

Isso criará a pasta `static/uploads` caso não exista e rodará o servidor em `http://localhost:5000`.

Para produção é possível utilizar o `Procfile` com Gunicorn. O arquivo `runtime.txt` define a versão do Python.

### Migrações

As migrações do banco ficam na pasta `migrations/`. Para criar ou atualizar as
tabelas (incluindo as de cursos) execute, com o ambiente virtual ativo e a
variável `FLASK_APP` apontando para `app.py`:

```bash
export FLASK_APP=app.py
flask db upgrade
```

Após atualizar o repositório lembre‑se de rodar `flask db upgrade` para aplicar a nova migração que cria as tabelas de cursos.

## Variáveis de ambiente

Crie um arquivo `.env` para definir as configurações sensíveis utilizadas pelo
Flask e pelo envio de emails. As principais variáveis são:

- `SECRET_KEY` – chave secreta da aplicação.
- `DATABASE_URL` – URL do banco de dados (padrão `sqlite:///dr_julio.db`).
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_DEFAULT_SENDER` – dados para o servidor de email.

Não existem variáveis específicas para cursos ou pagamentos até o momento.

## Cursos

Os cursos disponíveis são exibidos na página `/cursos`. Cada curso tem uma
página de detalhes onde o visitante pode se inscrever informando nome, e‑mail e
telefone. Após o envio, a inscrição é registrada no banco de dados.
O cadastro de cursos é representado pelo modelo `Course`, que armazena título,
descrição, imagem, preço, link de acesso e se o curso está ativo.

### Administração de cursos

No painel administrativo existem novas opções para **Cursos** e **Inscrições**.
Usuários administradores podem criar, editar e remover cursos, além de
acompanhar todas as inscrições recebidas. Os principais caminhos são:
`/admin/courses` (lista), `/admin/courses/add`, `/admin/courses/edit/<id>` e
`/admin/courses/delete/<id>`.

### Pagamentos

Após se inscrever em um curso o usuário é direcionado para uma página de pagamento.
O processo é simulado e, quando confirmado, o status da inscrição muda para **paid**
e é criado um registro em `PaymentTransaction`. Em seguida é apresentado o link de
acesso ao material configurado para o curso.

Também é possível comprar o curso diretamente via Stripe no endpoint `/course/<id>/buy`.
Para isso defina `STRIPE_SECRET_KEY` e `STRIPE_PUBLIC_KEY` no arquivo `.env`.
As compras realizadas por esse fluxo são registradas no modelo `CoursePurchase`.

