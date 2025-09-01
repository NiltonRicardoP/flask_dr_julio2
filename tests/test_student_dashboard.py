from models import db, User


def create_user(username, role='student'):
    user = User(username=username, email=f"{username}@example.com", role=role)
    user.set_password('pass')
    db.session.add(user)
    db.session.commit()
    return user


def login_user(client, user_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True


def test_dashboard_requires_login(client):
    resp = client.get('/student/dashboard')
    assert resp.status_code == 302


def test_dashboard_rejects_admin(client):
    with client.application.app_context():
        admin = create_user('admin', role='admin')
        admin_id = admin.id
    login_user(client, admin_id)
    resp = client.get('/student/dashboard')
    assert resp.status_code == 302


def test_dashboard_allows_student(client):
    with client.application.app_context():
        student = create_user('stud', role='student')
        student_id = student.id
    login_user(client, student_id)
    resp = client.get('/student/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Área do Aluno' in html
