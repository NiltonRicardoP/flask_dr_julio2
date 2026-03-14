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

3. Execute o bootstrap de deploy:
   ```bash
   flask deploy
   ```

## Como executar

A aplicação pode ser iniciada diretamente usando `run.py`:

```bash
python run.py
```

Isso criará a pasta `static/uploads` caso não exista e rodará o servidor em `http://localhost:5000`.

Para produção é possível utilizar o `Procfile` com Gunicorn. O arquivo `runtime.txt` define a versão do Python.

### Execução em produção

Para subir em produção, defina pelo menos:

- `APP_ENV=production`
- `SECRET_KEY` com valor forte
- `DATABASE_URL`
- `ADMIN_PASSWORD` para o bootstrap do admin

Opcionalmente:

- `HEALTHCHECK_TOKEN` para liberar detalhes do endpoint `/api/health/db`
- `ADMIN_API_KEY` para os endpoints administrativos em `/api/appointments`
- `ENABLE_DEBUG_ROUTES=false` para manter rotas de debug desabilitadas

Com isso, a aplicação pode ser iniciada com Gunicorn:

```bash
gunicorn app:app
```

### Migrações


As migrações do banco ficam na pasta `migrations/`.
Depois de clonar o projeto execute `flask deploy` para aplicar as migrações e garantir `Settings` e o usuário administrador.
Com o ambiente virtual ativo e `FLASK_APP` apontando para `app.py`, gere uma nova migração sempre que modificar os modelos e aplique-a:

```bash
export FLASK_APP=app.py
flask db migrate -m "Nova migração"
flask db upgrade
```

Se estiver apenas atualizando o repositório execute `flask deploy`.
## Variáveis de ambiente

Crie um arquivo `.env` para definir as configurações sensíveis utilizadas pelo
Flask e pelo envio de emails. As principais variáveis são:

- `SECRET_KEY` – chave secreta da aplicação.
- `DATABASE_URL` – URL do banco de dados (padrão `sqlite:///dr_julio.db`).
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_DEFAULT_SENDER` – dados para o servidor de email.
- `GOOGLE_CREDENTIALS_FILE` – fallback opcional para o Google Calendar. O painel admin aceita upload do JSON do service account.
- `CHATBOT_MAX_MESSAGE_LENGTH`, `CHATBOT_MAX_HISTORY_ITEMS` – limites de payload do chatbot.

- `HOTMART_WEBHOOK_SECRET` – segredo para validar notificações do Hotmart.
- `HOTMART_CLIENT_ID` e `HOTMART_CLIENT_SECRET` – credenciais OAuth da API do Hotmart.
- `HOTMART_USE_SANDBOX` – define se a API do Hotmart deve utilizar o ambiente de testes.

As credenciais do Hotmart podem ser geradas no [Painel de Desenvolvedor do Hotmart](https://developers.hotmart.com/).
Crie uma nova aplicação para obter o Client ID e o Client Secret e então defina-os no arquivo `.env`.

## Cursos

Os cursos disponíveis são exibidos na página `/cursos` (ou `/courses`).
Cada curso apresenta um link de compra ou acesso via Hotmart, onde todo o conteúdo é hospedado e gerenciado.
Não há área do aluno ou registro de matrículas neste projeto; o acesso é feito exclusivamente pela plataforma Hotmart.

Para visualizar a lista de cursos basta iniciar a aplicação e acessar:

```
http://localhost:5000/courses
```
O cadastro de cursos é representado pelo modelo `Course`, que armazena título,
descrição, imagem, preço, link de acesso e se o curso está ativo.

### Administração de cursos

No painel administrativo existe a opção **Cursos**.
Para cadastrar um novo curso acesse `/admin/courses` e clique em **Adicionar**
ou vá diretamente para `/admin/courses/add`. Preencha os campos do formulário e
salve. Para editar um curso existente utilize `/admin/courses/edit/<id>` a
partir da lista. A exclusão pode ser feita enviando um POST para
`/admin/courses/delete/<id>`.

