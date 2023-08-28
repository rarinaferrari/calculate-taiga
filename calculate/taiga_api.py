import traceback
from datetime import datetime
import secrets
import string
from typing import List, Dict

import aiohttp
import logging
import asyncio
import json

alphabet = string.ascii_letters + string.digits


class Taiga:
    def __init__(self, url, login, password):
        self.url = f"{url}/api/v1"
        self.login = login
        self.password = password
        self.auth = {}

    async def get_auth(self, login=None, password=None, id=False):
        if not login and not password:
            data = {"username": self.login, "password": self.password, "type": "normal"}
            root_auth = await self.post(f"/auth", data=data, headers={})
            self.auth = {"Authorization": f"Bearer {root_auth['auth_token']}", "x-disable-pagination": "True"}
            return True

        if not password:
            password = await self._get_user_data(login)
        data = {"username": login, "password": password, "type": "normal"}
        result = await self.post(f"/auth", data=data, headers={})
        if id:
            return {"Authorization": f"Bearer {result['auth_token']}"}, result["id"]
        return {"Authorization": f"Bearer {result['auth_token']}"}

    async def post(self, path, params=None, **kwargs):
        if params is None:
            params = {}
        if "headers" not in kwargs:
            kwargs["headers"] = self.auth
        #try:
        print(f"{params}")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.url}{path}", params=params, **kwargs) as response:
                if response.status not in range(200, 300):
                    text = await response.text()
                    print(f"AJKFNAKJBFAKJBFKAJDBNKAJSDNAJK __________________ {text}")
                    return None
                try:
                    res = await response.json()
                except:
                    res = None
                logging.debug("RestApi GET {}: {}".format(f"{self.url}/{path}", res))
                return res
        # except Exception:
        #     logging.error(traceback.format_exc())
        #     return None

    async def patch(self, path, params=None, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.auth
        #try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{self.url}{path}", params=params, **kwargs) as response:
                if response.status not in range(200, 300):
                    return None
                res = await response.json()
                logging.debug("RestApi GET {}: {}".format(f"{self.url}/{path}", res))
                return res
        # except Exception:
        #     logging.error(traceback.format_exc())
        #     return None

    async def put(self, path, params=None, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.auth
        #try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{self.url}{path}", params=params, **kwargs) as response:
                if response.status not in range(200, 300):
                    return None
                res = await response.json()
                logging.debug("RestApi GET {}: {}".format(f"{self.url}/{path}", res))
                return res
        # except Exception:
        #     logging.error(traceback.format_exc())
        #     return None

    async def get(self, path, params=None, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.auth
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}{path}", params=params, **kwargs) as response:
                    if response.status not in range(200, 300):
                        return None
                    res = await response.json()
                    logging.debug("RestApi GET {}: {}".format(f"{self.url}/{path}", res))
                    return res
        except Exception:
            logging.error(traceback.format_exc())
            return None

    async def delete(self, path, params=None, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.auth
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{self.url}{path}", params=params, **kwargs) as response:
                if response.status != 204:
                    return None
                return True

    async def get_by_slug(self, path, slug, **kwargs):
        return await self.get(f"{path}/by_slug", params={"slug": slug}, **kwargs)

    async def get_by_name(self, path, name, **kwargs):
        res = await self.get(f"{path}", **kwargs)
        for item in res:
            if item.get('name') and item.get('name').lower() == name.lower():
                return item

    async def _write_user_data(self, login, password):
        with open("users_data") as inf:
            data = json.loads(inf.read())
        data[login] = password
        with open("users_data", "w") as ouf:
            ouf.write(json.dumps(data, indent=2))

    async def _get_user_data(self, login):
        with open("users_data") as inf:
            data = json.loads(inf.read())
        if login in data:
            return data[login]
        return ""

    async def join_to_project(self, project, role, email):
        project_data = {"project": project, "role": role, "username": email}
        join = await self.post("/memberships", data=project_data)
        return join

    async def get_memberships(self, project=None):
        res = await self.get('/memberships', params={'project': project} if project else None)
        return res

    async def create_user(self, person):
        password = "".join(secrets.choice(alphabet) for i in range(8))

        register_data = {
            "accepted_terms": ["True"],
            "username": [f'{person["login"]}'],
            "full_name": [f'{person["full_name"]}'],
            "email": [f'{person["email"]}'],
            "password": [password],
            "type": ["public"],
        }
        register = await self.post("/auth/register", data=register_data)
        if register:
            await self._write_user_data(person["login"], password)
            auth_token = register["auth_token"]
        else:
            auth_token = await self.get_auth(
                person["login"], await self._get_user_data(person["login"])
            )
        head = {"Authorization": f"Bearer {auth_token}"}
        try:
            with open(f'photos/{person["inn"]}.jpeg', "rb") as inf:
                photo = inf.read()
            change_avatar = await self.post(
                "/users/change_avatar", files={"avatar": photo}, headers=head
            )
        except Exception:
            print(f"{person['full_name']}")

        await self.join_to_project(2, 19, person["email"])

    # async def change_user(self, person, data):
    #     password = await self._get_user_data(person["login"])
    #     head, id = await self.get_auth(person["login"], password, id=True)
    #     user = await self.get(f"/users/{id}")
    #     user = user | data
    #     update = await self.put(f"/users/{id}", data=user, headers=head)
    #     return update

    async def change_user_avatar(self, person, from_face=False):
        password = await self._get_user_data(person["login"])
        if not password:
            print(f'no pass for {person["login"]}')
            return True
        head = await self.get_auth(person["login"], password)
        prev_avatar = await self.get("/users/me", headers=head)
        if prev_avatar["photo"]:
            print("already have photo")
            return True
        try:
            if from_face:
                with open(f'photos_login/{person["login"]}.face', "rb") as inf:
                    photo = inf.read()
            else:
                with open(f'photos/{person["inn"]}.jpeg', "rb") as inf:
                    photo = inf.read()
            print(f"updating photo for {person['login']}")
            change_avatar = await self.post(
                "/users/change_avatar", files={"avatar": photo}, headers=head
            )
        except Exception:
            print(f"failed {person['login']}")

    async def create_epic(self, data, by=None):
        base_epic = {
            "assigned_to": None,
            "blocked_note": "blocking reason",
            "client_requirement": False,
            "color": "#8151D3",
            "description": "New epic description",
            "is_blocked": False,
            "project": None,
            "subject": "New test epic",
            "tags": [],
            "team_requirement": False,
            "watchers": [],
        }
        epic_data = base_epic | data
        head = await self.get_auth(by) if by else ""
        if epic_data["assigned_to"] and epic_data["project"]:
            users = await self.get(
                "/users", {"project": epic_data["project"]}, headers=head or self.auth
            )
            user = [x["id"] for x in users if x["username"] == epic_data["assigned_to"]]
            if not user:
                raise TaigaError
            epic_data["assigned_to"] = user[0]
        res = await self.post("/epics", data=epic_data, headers=head or self.auth)
        return res

    async def add_task_to_epic(self, epic, task, by=None):
        head = await self.get_auth(by) if by else ""
        if epic is None:
            print("Create Epic")
        else:
            await self.post(
                f"/epics/{epic['id']}/related_userstories",
                data={"epic": epic["id"], "user_story": task["id"]},
                headers=head or self.auth,
            )

    async def create_userstory(self, data, by=None):
        basic_us = {
            "assigned_to": None,
            "description": "Very important description",
            "subject": "test",
            "project": None,
        }
        us_data = basic_us | data
        head = await self.get_auth(by) if by else ""

        res = await self.post("/userstories", json=us_data, headers=head or self.auth)
        return res

    async def change_userstory(self, id, data):
        res = await self.patch(f"/userstories/{id}", json=data, headers=self.auth)
        return res

    async def get_detail_user_story(self, id, params=None):
        res = await self.get(f"/userstories/{id}", params=params)
        return res

    async def take_data_from_user_story(self):
        params = {
            "project": 1,
            "status": 1
        }
        res = await self.get(f"/userstories", params=params)
        lst = [i['subject'] for i in res if i['epics'] != None]
        return lst

    async def get_list_userstory(self):
        params = {
            "project": 1,
            "status": 1,
        }
        res = await self.get(f"/userstories", params=params)
        return res

    async def add_comment_to_userstory(self, id, text, version):
        res = await self.patch(f"/userstories/{id}", data={"version": version, "comment": text})
        return res

    async def add_project(self, data):
        res = await self.post("/projects", data=data)
        return res

    async def get_userstory_history(self, id):
        res = await self.get(f"/history/userstory/{id}", params={"type": "activity"})
        return res

    async def get_user_by_id(self, id):
        res = await self.get(f"/users/{id}")
        return res

    async def get_users_by_role(self, id, project):
        project = await self.get(f"/projects/{project}")
        return [x["id"] for x in project["members"] if x["role"] == id]

    async def get_list_relative_user_story(self, epic_id):
        params = {
            'project': 1,
        }
        res = await self.get(f'/epics/{epic_id}/related_userstories', params=params)
        return res

    async def create_custom_attribute(self):
        attribute_data = {
            "project": 1,
            "name": "My Custom Attribute",
            "description": "Description of my custom attribute",
            "attribute_type": "text",
            "order": 1,
            "is_required": False,
            "is_visible": True,
            "is_filterable": True,
            "is_multivalued": False,
            "extra": {}
        }

        res = await self.post('/userstory-custom-attributes', json=attribute_data)
        return res

    async def take_date_time(self) -> Dict[int, List[str]]:
        list_lst = await self.take_data_from_user_story()
        date_time_dict = dict()
        for i, strg in enumerate(list_lst):
            strg = strg.split(' ')
            date_time_lst = list()
            __indexes = [0, 2]
            try:
                for k in __indexes:
                    if float(strg[k]):
                        date_time_lst.append(strg[k])
                date_time_dict[i] = date_time_lst
            except:
                date_time_dict[i] = date_time_lst
        return date_time_dict

    async def create_filter(self) -> List[int]:
        time_data = await self.take_date_time()
        _filter_list = []
        _lst = []
        __keys = list()
        for k, v in time_data.items():
            if len(v) == 0:
                _filter_list.insert(0, k)
            elif len(v) == 1:
                _filter_list.append(k)
            if len(v) == 2:
                my_str = ' '.join(v)
                date_object = datetime.strptime(my_str + ' ' + str(datetime.now().year), '%d.%m %H.%M %Y')
                new_date_string = date_object.strftime('%d.%m.%Y %H.%M')
                _lst.append((k, new_date_string))
                sorted_lst = sorted(_lst, key=lambda x: datetime.strptime(x[1], '%d.%m.%Y %H.%M'))
                __keys = [x[0] for x in sorted_lst]
        _filter_list.extend(__keys)
        return _filter_list

    async def filter_userstories_status(self):
        params = {
            'project': 1,
        }
        res = await self.get(f"/userstories", params=params)
        for us in res:
            if us['status'] != 1 and us['epics'] != None:
                epics_id = us['epics'][0]['id']
                res = await self.delete(f'/epics/{epics_id}/related_userstories/{us["id"]}')
        return res

    async def get_list_user_story(self, ids=None):
        params = {
            'project': ids or 1,
        }
        res = await self.get(f"/userstories", params=params)
        return res

    async def delete_user_by_id(self, id):
        res = await self.delete(f'/users/{id}')
        return res

    async def delete_role_by_id(self, id, moveto):
        res = await self.delete(f'/roles/{id}/?moveTo={moveto}')
        return res

    async def create_project_role(self, role_data):
        res = await self.post(f'/roles', json=role_data)
        return res


class TaigaError(Exception):
    pass


async def fun():
    t = Taiga('https://boards.calculate.ru', 'admin', 'uRW4oVw0QS4kQ')
    #t = Taiga('http://10.2.2.132', 'admib', 'naljAil5')
    await t.get_auth()
    project_data = {'project': '47', 'role': 395, 'username': 'mz@calculate.ru'}
    res = await t.get("/users", data=project_data)
    for i in res:
        user = await t.get(f'/users/{i["id"]}')
        if user['email'] == 'np@calculate.ru':
            print()


    print()

#asyncio.run(fun())