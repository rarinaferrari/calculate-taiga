import asyncio
import itertools
import time

import aiohttp

from taiga_api import Taiga
import logging.handlers
import smtplib
import datetime
from aiohttp import web


console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)

logfile = logging.handlers.RotatingFileHandler(
    "server.log", maxBytes=1024 * 1024, backupCount=5
)
logfile.setLevel(logging.INFO)
logfile.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[console, logfile])
smtp_msg = """"""


def send_email(body_text):
    """
    Отправка письма админам
    """
    to_addr = 'admin@calculate.ru'
    subject = 'failed to complite microservice action'
    host = "mail.dmz.calculate.ru"
    from_addr = "ah@calculate.ru"
    BODY = "\r\n".join((
        "From: %s" % from_addr,
        "To: %s" % to_addr,
        "Subject: %s" % subject,
        "Date: %s" % datetime.datetime.now(),
        "",
        body_text
    ))
    server = smtplib.SMTP(host)
    server.sendmail(from_addr, [to_addr], BODY.encode('utf-8'))
    server.quit()

class Abcd(Taiga):
    ip = '10.2.0.13'
    #ip = '0.0.0.0'

    async def create_user(self, person):
        bio = f"{person['position']}; {person['subdivision']}; Рабочий телефон: {person['work_tel']}"

        register_data = {'accepted_terms': ['True'], 'username': [f'{person["login"]}'],
                         'full_name': [f'{person["fio"]}'], 'email': [f'{person["email"]}'],
                         'password': [person["password"]], 'type': ['public'], 'bio': bio}
        res = []

        register = await self.post('/auth/register', data=register_data)
        if register:
            logging.info(f"Регистрация успешна.\nПароль: {person['password']}")
            for project_id, role_id in person["roles"].items():
                project = await self.get(f'/projects/{project_id}')
                if not project:
                    logging.info(f'Проект {project_id} не найден')
                    res.append(False)
                    continue
                role = await self.get(f'/roles/{role_id}')
                if not role:
                    logging.info('нет такой роли')
                    continue
                await self.join_to_project(project_id, role_id, person['email'])
            await self.update_users(ids=register["id"])
        else:
            logging.info(f"Пользователь не создан")
            return False
        return True

    async def update_projects(self, indata):
        projects = await self.get('/projects')
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{self.ip}:41324/service_taiga/update_projects", json={"projects": projects}) as resp:
                if resp.status not in range(200, 300):
                    return False
        return True

    async def update_users(self, indata=None, ids=None):
        if not ids:
            users = await self.get('/users')
            for user in users:
                user['login'] = user['username']
        else:
            users = await self.get(f'/users/{ids}')
            users['login'] = users['username']
            users = {'users': users}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{self.ip}:41324/service_taiga/update_users", json={"users": users}) as resp:
                if resp.status not in range(200, 300):
                    return False
        return True

    async def update_roles(self, role):
        roles = await self.get(f'/roles/{role}')
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{self.ip}:41324/service_taiga/update_roles", json={"roles": [roles]}) as resp:
                if resp.status not in range(200, 300):
                    return False
        return True

    async def update_data(self, indata):
        roles = await self.get('/roles')
        users = await self.get('/users')
        projects = await self.get('/projects')
        roles = {x["id"]: x for x in roles}
        users = {x["id"]: x for x in users}

        # тайга падает при asyncio.gather, поэтому запросы идут последовательно
        tasks = [self.get(f"/projects/{project['id']}") for project in projects]
        projects_data = await asyncio.gather(*tasks)
        for proj_data in projects_data:
            for member in proj_data["members"]:
                if not member['id'] in users:
                    continue
                if users[member['id']].get('roles_id'):
                    users[member['id']]['roles_id'].append(member['role'])
                else:
                    users[member['id']]['roles_id'] = [member['role']]
                if users[member['id']].get('projects'):
                    users[member['id']]['projects'].append(proj_data['id'])
                else:
                    users[member['id']]['projects'] = [proj_data['id']]
        async with aiohttp.ClientSession(f'http://{self.ip}:41324') as session:
            async with session.post("/service_taiga/update_projects", json={"projects": projects}) as resp:
                if resp.status not in range(200, 300):
                    return False
            async with session.post(f"/service_taiga/update_users", json={"users": users}) as resp:
                if resp.status not in range(200, 300):
                    return False
            async with session.post(f"/service_taiga/update_roles", json={"roles": roles}) as resp:
                if resp.status not in range(200, 300):
                    return False
        return True

    async def delete_user(self, indata):
        res = await self.delete_user_by_id(indata["id"])
        if not res:
            return False
        return True

    async def create_project(self, indata):
        res = await self.add_project(indata)
        return res

    async def change_user(self, indata):
        delete_from = indata.get('remove_from')
        add_to = indata.get('add_to')
        user_id = indata.get('id')
        fio = indata.get('fio')
        new_password = indata.get('new_password')
        old_password = indata.get('old_password')
        login = indata.get('login')
        email = indata.get('email')

        user_membership = []
        if delete_from:
            roles_obj = await asyncio.gather(*[self.get(f"/roles/{role_id}") for role_id in delete_from])
            proj_memberhips = await asyncio.gather(*[self.get_memberships(project=x['project']) for x in roles_obj])
            user_membership = list(itertools.chain(*[[x for x in proj if x['user'] == user_id] for proj in proj_memberhips]))
            for role_id in delete_from:
                role_obj = await self.get(f"/roles/{role_id}")
                proj_memberships = await self.get_memberships(project=role_obj["project"])
                user_membership = user_membership + [x for x in proj_memberships if x['user'] == user_id]
            for i in user_membership:
                await self.delete(f'/memberships/{i["id"]}')
        if add_to:
            for role_id in add_to:
                role_obj = await self.get(f"/roles/{role_id}")
                await self.join_to_project(role_obj['project'], role_obj['id'], email)

        if fio:
            user = await self.get(f'/users/{user_id}')
            user["full_name"] = fio
            user["full_name_display"] = fio
            res = await self.put(f"/users/{user_id}", data=user)

        if old_password and new_password and login:
            prev_auth = taiga.auth
            taiga.auth = await taiga.get_auth(login=login, password=old_password)
            res = await self.post(f"/users/change_password", data={"current_password": old_password,
                                                                   "password": new_password})
            taiga.auth = prev_auth
        await self.update_users(ids=user_id)
        return True

    async def create_role(self, indata):
        role_data = {"name": indata.get('name'), "project": indata.get('project'),
                     "permissions": indata.get('permissions')}
        res = await self.create_project_role(role_data)
        if res:
            await self.update_roles(res)
            return True
        return False

    async def delete_role(self, indata):
        role_id = indata.get('role_id')
        moveto = indata.get('moveto')
        res = await self.delete_role(role_id, moveto)
        if res:
            return True
        return False

    async def add_to_queue(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{self.ip}:41324/service_taiga/add_to_queue", json={"port": '44114'}) as resp:
                pass


class TaigaError(Exception):
    """"""


taiga = Abcd('https://boards.calculate.ru', 'admin', 'admin_password')
app = web.Application()
routes = web.RouteTableDef()


@routes.post('/make_task')
async def task_maker(request):

    data = await request.json()
    task = data['args'][0]
    #try:
    func = taiga.__getattribute__(task["action"])
    logging.info(f"processing {task['action']}")
    await taiga.get_auth()
    # несколько попыток на случай бага тайги
    for i in range(5):
        res = await func(task)
        if res:
            logging.info("Успешно выполнено")
            break
        time.sleep(5)
    else:
        await taiga.get_auth()
        res = await func(task)
        if res:
            logging.info("Успешно выполнено")
        else:
            send_email(f"Не удалось выполнить действие {task['action']}.\nПараметры: {str(task)}")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{taiga.ip}:41324/service_taiga/finished_task", json={'uid': data['id']}) as resp:
            if resp.status not in range(200, 300):
                return False
    # except Exception as e:
    #     logging.error(f'error - {e}')
    #     time.sleep(60)


if __name__ == "__main__":
    logging.info("-----Новый цикл-----")
    asyncio.run(taiga.add_to_queue())
    t = datetime.datetime.now()
    app.add_routes(routes)
    web.run_app(app, port=44114)
