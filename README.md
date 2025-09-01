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

3. Execute as migrações e crie o usuário administrador:
   ```bash
   flask db upgrade
   python create_admin.py
   ```

## Como executar

A aplicação pode ser iniciada diretamente usando `run.py`:

```bash
python run.py
```

Isso criará a pasta `static/uploads` caso não exista e rodará o servidor em `http://localhost:5000`.

Para produção é possível utilizar o `Procfile` com Gunicorn. O arquivo `runtime.txt` define a versão do Python.

### Migrações


As migrações do banco ficam na pasta `migrations/`.
Depois de clonar o projeto execute `flask db upgrade` para criar todas as tabelas e em seguida `python create_admin.py` para inserir ou atualizar o usuário administrador.
Com o ambiente virtual ativo e `FLASK_APP` apontando para `app.py`, gere uma nova migração sempre que modificar os modelos e aplique-a:

```bash
export FLASK_APP=app.py
flask db migrate -m "Nova migração"
flask db upgrade
```

Se estiver apenas atualizando o repositório execute `flask db upgrade` para aplicar as migrações existentes.
## Variáveis de ambiente

Crie um arquivo `.env` para definir as configurações sensíveis utilizadas pelo
Flask e pelo envio de emails. As principais variáveis são:

- `SECRET_KEY` – chave secreta da aplicação.
- `DATABASE_URL` – URL do banco de dados (padrão `sqlite:///dr_julio.db`).
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_DEFAULT_SENDER` – dados para o servidor de email.

- `HOTMART_WEBHOOK_SECRET` – segredo para validar notificações do Hotmart.
- `HOTMART_CLIENT_ID` e `HOTMART_CLIENT_SECRET` – credenciais OAuth da API do Hotmart.
- `HOTMART_USE_SANDBOX` – define se a API do Hotmart deve utilizar o ambiente de testes.

As credenciais do Hotmart podem ser geradas no [Painel de Desenvolvedor do Hotmart](https://developers.hotmart.com/).
Crie uma nova aplicação para obter o Client ID e o Client Secret e então defina-os no arquivo `.env`.

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

### Upload de vídeos do curso

Os materiais em vídeo devem ser enviados pelo painel administrativo ao editar ou criar um curso. Cada arquivo é armazenado na pasta `course_content/<id_do_curso>` e fica disponível apenas para alunos matriculados.

1. Acesse **Admin > Cursos** e escolha **Adicionar** ou **Editar**.
2. Utilize o campo **Vídeo** para selecionar o arquivo desejado e salve o formulário.
3. O vídeo poderá ser reproduzido pelos alunos na página do curso através de um `<video>` protegido por token temporário.

Caso prefira hospedar os vídeos em serviços externos (como S3/CloudFront ou Vimeo), basta preencher o campo **URL de Acesso** do curso com o link correspondente.

