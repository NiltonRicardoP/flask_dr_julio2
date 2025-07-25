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

## Cursos

Os cursos disponíveis são exibidos na página `/cursos`. Cada curso tem uma
página de detalhes onde o visitante pode se inscrever informando nome, e‑mail e
telefone. Após o envio, a inscrição é registrada no banco de dados.

### Administração de cursos

No painel administrativo existem novas opções para **Cursos** e **Inscrições**.
Usuários administradores podem criar, editar e remover cursos, além de
acompanhar todas as inscrições recebidas.

### Pagamentos

Após se inscrever em um curso o usuário é direcionado para uma página de pagamento.
O processo é simulado e, quando confirmado, o status da inscrição muda para **paid**
e é criado um registro em `PaymentTransaction`. Em seguida é apresentado o link de
acesso ao material configurado para o curso.

