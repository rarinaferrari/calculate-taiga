import pytest
import os
import random
from taiga import Abcd


taiga_url = os.environ.get("TAIGA_URL") or "http://10.2.2.153:9000"
taiga_admin = os.environ.get("TAIGA_ADMIN_LOGIN") or "admin"
taiga_pass = os.environ.get("TAIGA_ADMIN_PASS") or "taiga"



async def mock_for_update_data(*args, **kwargs):
    return True


@pytest.fixture()
@pytest.mark.asyncio
async def auth_fixture():
    taiga = Abcd(taiga_url, taiga_admin, taiga_pass)
    await taiga.get_auth()
    return taiga


@pytest.mark.parametrize("user, email, url",
                         [("testovich", "taiga@calculate.ru", taiga_url),
                          ("testovich2", "ah@calculate.ru", taiga_url)])
@pytest.mark.asyncio
async def test_create_user(user, email, url, auth_fixture):
    taiga = await auth_fixture
    taiga.update_users = mock_for_update_data
    person = {"fio": 'Testik Testovik',
              "work_tel": '666',
              "subdivision": '133',
              "position": '331',
              "login": user,
              "password": 'QweQweQwe1',
              "email": email,
              "roles": {}}
    res = await taiga.create_user(person)
    assert res


@pytest.mark.parametrize("email", ["taiga@calculate.ru", "ah@calculate.ru"])
@pytest.mark.asyncio
async def test_add_to_project(auth_fixture, email):
    taiga = await auth_fixture
    project = await taiga.create_project({"name": "test_proj", "description": "some description"})
    assert project
    res = await taiga.join_to_project(project['id'], random.choice(project['roles'])['id'], email)
    assert res


@pytest.mark.parametrize("user", ["testovich", "testovich2"])
@pytest.mark.asyncio
async def test_delete_from_project(auth_fixture, user):
    taiga = await auth_fixture
    taiga.update_users = mock_for_update_data
    result = []
    projects = await taiga.get('/projects')
    users = await taiga.get('/users')
    users = {x['id']: x['username'] for x in users}
    for project in projects:
        for member in project['members']:
            if member in users and users[member] == user:
                res = await taiga.change_user({"remove_from": [project['id']], "id": member})
                result.append(res)
    assert all(result)


@pytest.mark.parametrize("user", ["testovich", "testovich2"])
@pytest.mark.asyncio
async def test_delete_user(auth_fixture, user):
    taiga = await auth_fixture
    users = await taiga.get('/users')
    user_to_delete = [x for x in users if x['username'] == user]
    if not user_to_delete:
        pytest.skip('skip due to no user where found')
    user_to_delete = user_to_delete[0]
    res = await taiga.delete_user(user_to_delete)
    assert res






