import base64
import datetime
import json

import pytest

from ihatemoney.tests.common.help_functions import em_surround
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase


class TestAPI(IhatemoneyTestCase):
                       

    def api_create(
        self, name, id=None, password=None, contact=None, default_currency=None
    ):
        id = id or name
        password = password or name
        contact = contact or f"{name}@notmyidea.org"

        data = {
            "name": name,
            "id": id,
            "password": password,
            "contact_email": contact,
        }
        if default_currency:
            data["default_currency"] = default_currency

        return self.client.post(
            "/api/projects",
            data=data,
        )

    def api_add_member(self, project, name, weight=1):
        self.client.post(
            f"/api/projects/{project}/members",
            data={"name": name, "weight": weight},
            headers=self.get_auth(project),
        )

    def get_auth(self, username, password=None):
        password = password or username
        base64string = (
            base64.encodebytes(f"{username}:{password}".encode("utf-8"))              
            .decode("utf-8")
            .replace("\n", "")
        )
        return {"Authorization": f"Basic {base64string}"}

    def test_cors_requests(self):
                                                                               
        resp = self.api_create("raclette")
        self.assertStatus(201, resp)

                                                                           
        resp = self.client.options(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )
        assert resp.headers["Access-Control-Allow-Origin"] == "*"

    def test_basic_auth(self):
                          
        resp = self.api_create("raclette")
        self.assertStatus(201, resp)

                                                                    
        resp = self.client.get("/api/projects/raclette")
        self.assertStatus(401, resp)

                                                              
                                  
        for verb in ("post",):
            for resource in ("/raclette/members", "/raclette/bills"):
                url = "/api/projects" + resource
                self.assertStatus(401, getattr(self.client, verb)(url), verb + resource)

        for verb in ("get", "delete", "put"):
            for resource in ("/raclette", "/raclette/members/1", "/raclette/bills/1"):
                url = "/api/projects" + resource

                self.assertStatus(401, getattr(self.client, verb)(url), verb + resource)

    def test_project(self):
                                            
        resp = self.client.post(
            "/api/projects",
            data={
                "name": "raclette",
                "id": "raclette",
                "password": "raclette",
                "contact_email": "not-an-email",
                "default_currency": "XXX",
            },
        )

        assert 400 == resp.status_code
        assert '{"contact_email": ["Invalid email address."]}\n' == resp.data.decode(
            "utf-8"
        )

                   
        with self.app.mail.record_messages() as outbox:
            resp = self.api_create("raclette")
            assert 201 == resp.status_code

                                                       
            assert len(outbox) == 1
            assert outbox[0].recipients == ["raclette@notmyidea.org"]

                                             
        resp = self.api_create("raclette")

        assert 400 == resp.status_code
        assert "id" in json.loads(resp.data.decode("utf-8"))

                                  
        resp = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )

        assert 200 == resp.status_code
        expected = {
            "members": [],
            "name": "raclette",
            "contact_email": "raclette@notmyidea.org",
            "default_currency": "XXX",
            "id": "raclette",
            "logging_preference": 1,
        }
        decoded_resp = json.loads(resp.data.decode("utf-8"))
        assert decoded_resp == expected

                                                                       
        resp = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "password": "raclette",
                "name": "The raclette party",
                "project_history": "y",
            },
            headers=self.get_auth("raclette"),
        )
        assert 400 == resp.status_code

                                                               
        resp = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "current_password": "fromage aux patates",
                "password": "raclette",
                "name": "The raclette party",
                "project_history": "y",
            },
            headers=self.get_auth("raclette"),
        )
        assert 400 == resp.status_code

                                                        
        resp = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "current_password": "raclette",
                "password": "raclette",
                "name": "The raclette party",
                "project_history": "y",
            },
            headers=self.get_auth("raclette"),
        )
        assert 200 == resp.status_code

        resp = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )

        assert 200 == resp.status_code
        expected = {
            "name": "The raclette party",
            "contact_email": "yeah@notmyidea.org",
            "default_currency": "XXX",
            "members": [],
            "id": "raclette",
            "logging_preference": 1,
        }
        decoded_resp = json.loads(resp.data.decode("utf-8"))
        assert decoded_resp == expected

                                             
        resp = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "current_password": "raclette",
                "password": "tartiflette",
                "name": "The raclette party",
            },
            headers=self.get_auth("raclette"),
        )

        assert 200 == resp.status_code

        resp = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette", "tartiflette")
        )
        assert 200 == resp.status_code

                            
        resp = self.client.delete(
            "/api/projects/raclette", headers=self.get_auth("raclette", "tartiflette")
        )

                                                        
        resp = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )
        assert 401 == resp.status_code

    def test_token_creation(self):
                                                     

                        
        resp = self.api_create("raclette")
        assert 201 == resp.status_code

                   
        resp = self.client.get(
            "/api/projects/raclette/token", headers=self.get_auth("raclette")
        )

        assert 200 == resp.status_code

        decoded_resp = json.loads(resp.data.decode("utf-8"))

                           
        resp = self.client.get(
            "/api/projects/raclette/token",
            headers={"Authorization": f"Basic {decoded_resp['token']}"},
        )
        assert 200 == resp.status_code

                                                                   
        resp = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "password": "tartiflette",
                "name": "The raclette party",
            },
            headers={"Authorization": f"Basic {decoded_resp['token']}"},
        )
        assert 400 == resp.status_code
        expected_resp = {"current_password": ["This field is required."]}
        assert expected_resp == json.loads(resp.data.decode("utf-8"))

    def test_token_login(self):
        resp = self.api_create("raclette")
                   
        resp = self.client.get(
            "/api/projects/raclette/token", headers=self.get_auth("raclette")
        )
        decoded_resp = json.loads(resp.data.decode("utf-8"))
        resp = self.client.get(f"/raclette/join/{decoded_resp['token']}")
                                      
        assert 302 == resp.status_code

    def test_member(self):
                          
        self.api_create("raclette")

                                                        
        req = self.client.get(
            "/api/projects/raclette/members", headers=self.get_auth("raclette")
        )

        self.assertStatus(200, req)
        assert "[]\n" == req.data.decode("utf-8")

                      
        req = self.client.post(
            "/api/projects/raclette/members",
            data={"name": "Zorglub"},
            headers=self.get_auth("raclette"),
        )

                                                     
        self.assertStatus(201, req)
        assert "1\n" == req.data.decode("utf-8")

                                                            
        req = self.client.get(
            "/api/projects/raclette/members", headers=self.get_auth("raclette")
        )

        self.assertStatus(200, req)
        assert len(json.loads(req.data.decode("utf-8"))) == 1

                                                       
        req = self.client.post(
            "/api/projects/raclette/members",
            data={"name": "Zorglub"},
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(400, req)

                              
        req = self.client.put(
            "/api/projects/raclette/members/1",
            data={"name": "Jeanne", "weight": 2},
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(200, req)

                                        
        req = self.client.get(
            "/api/projects/raclette/members/1", headers=self.get_auth("raclette")
        )

        self.assertStatus(200, req)
        assert "Jeanne" == json.loads(req.data.decode("utf-8"))["name"]
        assert 2 == json.loads(req.data.decode("utf-8"))["weight"]

                                                
                                
        req = self.client.put(
            "/api/projects/raclette/members/1",
            data={"name": "Jeanne"},
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(200, req)

                                     
        req = self.client.put(
            "/api/projects/raclette/members/1",
            data={"name": "Jeanne", "activated": False},
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(200, req)

        req = self.client.get(
            "/api/projects/raclette/members/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)
        assert not json.loads(req.data.decode("utf-8"))["activated"]

                                     
        req = self.client.put(
            "/api/projects/raclette/members/1",
            data={"name": "Jeanne", "activated": True},
            headers=self.get_auth("raclette"),
        )

        req = self.client.get(
            "/api/projects/raclette/members/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)
        assert json.loads(req.data.decode("utf-8"))["activated"]

                         

        req = self.client.delete(
            "/api/projects/raclette/members/1", headers=self.get_auth("raclette")
        )

        self.assertStatus(200, req)

                                                  
        req = self.client.get(
            "/api/projects/raclette/members", headers=self.get_auth("raclette")
        )

        self.assertStatus(200, req)
        assert "[]\n" == req.data.decode("utf-8")

    def test_bills(self):
                          
        self.api_create("raclette")

                          
        self.api_add_member("raclette", "zorglub")
        self.api_add_member("raclette", "jeanne")
        self.api_add_member("raclette", "quentin")

                                                 
        req = self.client.get(
            "/api/projects/raclette/bills", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)

        assert "[]\n" == req.data.decode("utf-8")

                    
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
                "external_link": "https://raclette.fr",
            },
            headers=self.get_auth("raclette"),
        )

                              
        self.assertStatus(201, req)
        assert req.data.decode("utf-8") == "1\n"

                               
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )

                                     
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "zorglub", "weight": 1},
                {"activated": True, "id": 2, "name": "jeanne", "weight": 1},
            ],
            "bill_type": "Expense",
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1,
            "converted_amount": 25.0,
            "original_currency": "XXX",
            "external_link": "https://raclette.fr",
        }

        got = json.loads(req.data.decode("utf-8"))
        assert (
            datetime.date.today()
            == datetime.datetime.strptime(got["creation_date"], "%Y-%m-%d").date()
        )
        del got["creation_date"]
        assert expected == got

                                           
        req = self.client.get(
            "/api/projects/raclette/bills", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)
        assert 1 == len(json.loads(req.data.decode("utf-8")))

                                                 
        req = self.client.put(
            "/api/projects/raclette/bills/1",
            data={
                "date": "201111111-08-10",              
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
                "external_link": "https://raclette.fr",
            },
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(400, req)
        assert '{"date": ["This field is required."]}\n' == req.data.decode("utf-8")

                     
        req = self.client.put(
            "/api/projects/raclette/bills/1",
            data={
                "date": "2011-09-10",
                "what": "beer",
                "payer": "2",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
                "external_link": "https://raclette.fr",
            },
            headers=self.get_auth("raclette"),
        )

                          
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        creation_date = datetime.datetime.strptime(
            json.loads(req.data.decode("utf-8"))["creation_date"], "%Y-%m-%d"
        ).date()

        expected = {
            "what": "beer",
            "payer_id": 2,
            "owers": [
                {"activated": True, "id": 1, "name": "zorglub", "weight": 1},
                {"activated": True, "id": 2, "name": "jeanne", "weight": 1},
            ],
            "bill_type": "Expense",
            "amount": 25.0,
            "date": "2011-09-10",
            "external_link": "https://raclette.fr",
            "converted_amount": 25.0,
            "original_currency": "XXX",
            "id": 1,
        }

        got = json.loads(req.data.decode("utf-8"))
        assert (
            creation_date
            == datetime.datetime.strptime(got["creation_date"], "%Y-%m-%d").date()
        )
        del got["creation_date"]
        assert expected == got

                       
        req = self.client.delete(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)

                                        
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(404, req)

    def test_bills_with_calculation(self):
                          
        self.api_create("raclette")

                          
        self.api_add_member("raclette", "zorglub")
        self.api_add_member("raclette", "jeanne")

                       
        input_expected = [
            ("((100 + 200.25) * 2 - 100) / 2", 250.25),
            ("3/2", 1.5),
            ("2 + 1 * 5 - 2 / 1", 5),
        ]

        for i, pair in enumerate(input_expected):
            input_amount, expected_amount = pair
            id = i + 1

            req = self.client.post(
                "/api/projects/raclette/bills",
                data={
                    "date": "2011-08-10",
                    "what": "fromage",
                    "payer": "1",
                    "payed_for": ["1", "2"],
                    "bill_type": "Expense",
                    "amount": input_amount,
                },
                headers=self.get_auth("raclette"),
            )

                                  
            self.assertStatus(201, req)
            assert req.data.decode("utf-8") == "{}\n".format(id)

                                     
            req = self.client.get(
                "/api/projects/raclette/bills/{}".format(id),
                headers=self.get_auth("raclette"),
            )

                                         
            self.assertStatus(200, req)
            expected = {
                "what": "fromage",
                "payer_id": 1,
                "owers": [
                    {"activated": True, "id": 1, "name": "zorglub", "weight": 1},
                    {"activated": True, "id": 2, "name": "jeanne", "weight": 1},
                ],
                "bill_type": "Expense",
                "amount": expected_amount,
                "date": "2011-08-10",
                "id": id,
                "external_link": "",
                "original_currency": "XXX",
                "converted_amount": expected_amount,
            }

            got = json.loads(req.data.decode("utf-8"))
            assert (
                datetime.date.today()
                == datetime.datetime.strptime(got["creation_date"], "%Y-%m-%d").date()
            )
            del got["creation_date"]
            assert expected == got

                             
        erroneous_amounts = [
            "lambda ",           
            "(20 + 2",                      
            "20/0",                
            "9999**99999999999999999",             
            "2" * 201,                           
        ]

        for amount in erroneous_amounts:
            req = self.client.post(
                "/api/projects/raclette/bills",
                data={
                    "date": "2011-08-10",
                    "what": "fromage",
                    "payer": "1",
                    "payed_for": ["1", "2"],
                    "bill_type": "Expense",
                    "amount": amount,
                },
                headers=self.get_auth("raclette"),
            )
            self.assertStatus(400, req)

    @pytest.mark.skip(reason="Currency conversion is broken")
    def test_currencies(self):
                                                            
        resp = self.client.get("/api/currencies")
        assert 200 == resp.status_code
        assert "XXX" in json.loads(resp.data.decode("utf-8"))

                                                
        resp = self.api_create("raclette", default_currency="EUR")
        assert 201 == resp.status_code

                                  
        resp = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )

        assert 200 == resp.status_code
        expected = {
            "members": [],
            "name": "raclette",
            "contact_email": "raclette@notmyidea.org",
            "default_currency": "EUR",
            "id": "raclette",
            "logging_preference": 1,
        }
        decoded_resp = json.loads(resp.data.decode("utf-8"))
        assert decoded_resp == expected

                          
        self.api_add_member("raclette", "zorglub")
        self.api_add_member("raclette", "jeanne")
        self.api_add_member("raclette", "quentin")

                                              
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
                "external_link": "https://raclette.fr",
            },
            headers=self.get_auth("raclette"),
        )

                              
        self.assertStatus(201, req)
        assert req.data.decode("utf-8") == "1\n"

                               
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )

                                     
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "zorglub", "weight": 1},
                {"activated": True, "id": 2, "name": "jeanne", "weight": 1},
            ],
            "bill_type": "Expense",
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1,
            "converted_amount": 25.0,
            "original_currency": "EUR",
            "external_link": "https://raclette.fr",
        }

        got = json.loads(req.data.decode("utf-8"))
        assert (
            datetime.date.today()
            == datetime.datetime.strptime(got["creation_date"], "%Y-%m-%d").date()
        )
        del got["creation_date"]
        assert expected == got

                                         
        req = self.client.put(
            "/api/projects/raclette/bills/1",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "30",
                "external_link": "https://raclette.fr",
                "original_currency": "CAD",
            },
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(200, req)

                      
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)
        expected_amount = self.converter.exchange_currency(30.0, "CAD", "EUR")
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "zorglub", "weight": 1.0},
                {"activated": True, "id": 2, "name": "jeanne", "weight": 1.0},
            ],
            "bill_type": "Expense",
            "amount": 30.0,
            "date": "2011-08-10",
            "id": 1,
            "converted_amount": expected_amount,
            "original_currency": "CAD",
            "external_link": "https://raclette.fr",
        }

        got = json.loads(req.data.decode("utf-8"))
        del got["creation_date"]
        assert expected == got

                                              
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-09-10",
                "what": "Pierogi",
                "payer": "1",
                "payed_for": ["2", "3"],
                "bill_type": "Expense",
                "amount": "80",
                "original_currency": "PLN",
            },
            headers=self.get_auth("raclette"),
        )

                              
        self.assertStatus(201, req)
        assert req.data.decode("utf-8") == "2\n"

                                                                
        req = self.client.put(
            "/api/projects/raclette",
            data={
                "contact_email": "yeah@notmyidea.org",
                "default_currency": "XXX",
                "current_password": "raclette",
                "password": "raclette",
                "name": "The raclette party",
            },
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(400, req)
        assert "This project cannot be set" in req.data.decode("utf-8")
        assert "because it contains bills in multiple currencies" in req.data.decode(
            "utf-8"
        )

    def test_statistics(self):
                          
        self.api_create("raclette")

                          
        self.api_add_member("raclette", "zorglub")
        self.api_add_member("raclette", "jeanne")

                    
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
            },
            headers=self.get_auth("raclette"),
        )

                                                 
        req = self.client.get(
            "/api/projects/raclette/statistics", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)
        received_stats = json.loads(req.data.decode("utf-8"))
        assert received_stats == [
            {
                "balance": 12.5,
                "member": {
                    "activated": True,
                    "id": 1,
                    "name": "zorglub",
                    "weight": 1.0,
                },
                "paid": 25.0,
                "received": 0.0,
                "spent": -12.5,
                "transferred": 0.0,
            },
            {
                "balance": -12.5,
                "member": {
                    "activated": True,
                    "id": 2,
                    "name": "jeanne",
                    "weight": 1.0,
                },
                "paid": 0.0,
                "received": 0.0,
                "spent": -12.5,
                "transferred": 0.0,
            },
        ]

    def test_username_xss(self):
                          
                                     
        self.post_project("raclette")
        self.login("raclette")

                          
        self.api_add_member("raclette", "<script>")

        result = self.client.get("/raclette/")
        assert "<script>" not in result.data.decode("utf-8")

    def test_weighted_bills(self):
                          
        self.api_create("raclette")

                          
        self.api_add_member("raclette", "zorglub")
        self.api_add_member("raclette", "jeannedy familly", 4)
        self.api_add_member("raclette", "quentin")

                    
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1", "2"],
                "bill_type": "Expense",
                "amount": "25",
            },
            headers=self.get_auth("raclette"),
        )

                               
        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        creation_date = datetime.datetime.strptime(
            json.loads(req.data.decode("utf-8"))["creation_date"], "%Y-%m-%d"
        ).date()

                                     
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "zorglub", "weight": 1},
                {"activated": True, "id": 2, "name": "jeannedy familly", "weight": 4},
            ],
            "bill_type": "Expense",
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1,
            "external_link": "",
            "converted_amount": 25.0,
            "original_currency": "XXX",
        }
        got = json.loads(req.data.decode("utf-8"))
        assert (
            creation_date
            == datetime.datetime.strptime(got["creation_date"], "%Y-%m-%d").date()
        )
        del got["creation_date"]
        assert expected == got

                                        
        req = self.client.get(
            "/api/projects/raclette", headers=self.get_auth("raclette")
        )

        expected = {
            "members": [
                {
                    "activated": True,
                    "id": 1,
                    "name": "zorglub",
                    "weight": 1.0,
                    "balance": 20.0,
                },
                {
                    "activated": True,
                    "id": 2,
                    "name": "jeannedy familly",
                    "weight": 4.0,
                    "balance": -20.0,
                },
                {
                    "activated": True,
                    "id": 3,
                    "name": "quentin",
                    "weight": 1.0,
                    "balance": 0,
                },
            ],
            "contact_email": "raclette@notmyidea.org",
            "id": "raclette",
            "name": "raclette",
            "logging_preference": 1,
            "default_currency": "XXX",
        }

        self.assertStatus(200, req)
        decoded_req = json.loads(req.data.decode("utf-8"))
        assert decoded_req == expected

    def test_log_created_from_api_call(self):
                          
        self.api_create("raclette")
        self.login("raclette")

                          
        self.api_add_member("raclette", "zorglub")

        resp = self.client.get("/raclette/history", follow_redirects=True)
        assert resp.status_code == 200
        assert f"Participant {em_surround('zorglub')} added" in resp.data.decode(
            "utf-8"
        )
        assert f"Project {em_surround('raclette')} added" in resp.data.decode("utf-8")
        assert resp.data.decode("utf-8").count("<td> -- </td>") == 2
        assert "127.0.0.1" not in resp.data.decode("utf-8")

    def test_amount_is_null(self):
        self.api_create("raclette")
                          
        self.api_add_member("raclette", "zorglub")

                                
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1"],
                "bill_type": "Expense",
                "amount": "0",
            },
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(201, req)

    def test_project_creation_with_mixed_case(self):
        self.api_create("Raclette")
                                  
        resp = self.client.get(
            "/api/projects/Raclette", headers=self.get_auth("Raclette")
        )
        self.assertStatus(200, resp)

    def test_amount_too_high(self):
        self.api_create("raclette")
                          
        self.api_add_member("raclette", "zorglub")

                                         
                                                              
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1"],
                "bill_type": "Expense",
                "amount": "9347242149381274732472348728748723473278472843.12",
            },
            headers=self.get_auth("raclette"),
        )
        self.assertStatus(400, req)

    def test_validate_bill_type(self):
        self.api_create("raclette")
        self.api_add_member("raclette", "zorglub")

        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1"],
                "bill_type": "wrong_bill_type",
                "amount": "50",
            },
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(400, req)

        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1"],
                "bill_type": "Expense",
                "amount": "50",
            },
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(201, req)

    def test_default_bill_type(self):
        self.api_create("raclette")
        self.api_add_member("raclette", "zorglub")

                                                
        req = self.client.post(
            "/api/projects/raclette/bills",
            data={
                "date": "2011-08-10",
                "what": "fromage",
                "payer": "1",
                "payed_for": ["1"],
                "amount": "50",
            },
            headers=self.get_auth("raclette"),
        )

        self.assertStatus(201, req)

        req = self.client.get(
            "/api/projects/raclette/bills/1", headers=self.get_auth("raclette")
        )
        self.assertStatus(200, req)

                                           
        got = json.loads(req.data.decode("utf-8"))
        assert got["bill_type"] == "Expense"
