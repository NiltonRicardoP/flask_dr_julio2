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
Na primeira execução o script também cria automaticamente um usuário administrador e configurações iniciais.

Para produção é possível utilizar o `Procfile` com Gunicorn. O arquivo `runtime.txt` define a versão do Python.

### Migrações


As migrações do banco ficam na pasta `migrations/`.
Depois de clonar o projeto execute `flask db upgrade` para criar todas as tabelas.
Com o ambiente virtual ativo e `FLASK_APP` apontando para `app.py`, gere uma nova migração sempre que modificar os modelos e aplique-a:

```bash
export FLASK_APP=app.py
flask db migrate -m "Nova migração"
flask db upgrade
```

Se estiver apenas atualizando o repositório execute `flask db upgrade` para aplicar as migrações existentes.

### Após atualizar o código

Sempre que fizer pull de novas alterações do repositório execute:

```bash
flask db upgrade
```

Isso mantém o banco de dados alinhado com os modelos mais recentes e evita erros em funcionalidades como o gerenciamento de cursos.
## Variáveis de ambiente

Crie um arquivo `.env` para definir as configurações sensíveis utilizadas pelo
Flask e pelo envio de emails. As principais variáveis são:

- `SECRET_KEY` – chave secreta da aplicação.
- `DATABASE_URL` – URL do banco de dados (padrão `sqlite:///dr_julio.db`).
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_DEFAULT_SENDER` – dados para o servidor de email.

Além das chaves do Stripe é necessário definir `PAGARME_API_KEY` para habilitar
o processamento de pagamentos via Pagar.me. Opcionalmente é possível alterar o
endereço da API com `PAGARME_BASE_URL`.

## Cursos

Os cursos disponíveis são exibidos na página `/cursos` (ou `/courses` em inglês).
Cada curso tem uma página de detalhes onde o visitante pode se inscrever informando nome, e‑mail e
telefone. Após o envio, a inscrição é registrada no banco de dados.

Para visualizar a lista de cursos basta iniciar a aplicação e acessar:

```
http://localhost:5000/courses
```
O cadastro de cursos é representado pelo modelo `Course`, que armazena título,
descrição, imagem, preço, link de acesso e se o curso está ativo.

### Administração de cursos

No painel administrativo existem opções para **Cursos** e **Inscrições**.
Para cadastrar um novo curso acesse `/admin/courses` e clique em **Adicionar**
ou vá diretamente para `/admin/courses/add`. Preencha os campos do formulário e
salve. Para editar um curso existente utilize `/admin/courses/edit/<id>` a
partir da lista. A exclusão pode ser feita enviando um POST para
`/admin/courses/delete/<id>`.

### Pagamentos

Após se inscrever em um curso o usuário é direcionado para uma página de pagamento.
O processo é simulado e, quando confirmado, o status da inscrição muda para **paid**
e é criado um registro em `PaymentTransaction`. Em seguida é apresentado o link de
acesso ao material configurado para o curso.

Também é possível comprar o curso diretamente via Stripe no endpoint `/course/<id>/buy`.
Para isso defina `STRIPE_SECRET_KEY` e `STRIPE_PUBLIC_KEY` no arquivo `.env`.
As compras realizadas por esse fluxo são registradas no modelo `CoursePurchase`.

