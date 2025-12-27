from collections import defaultdict
from datetime import datetime, timedelta, date
import re
from urllib.parse import unquote, urlparse, urlunparse

from flask import session, url_for
import pytest
from werkzeug.security import check_password_hash

from ihatemoney import models
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.tests.common.help_functions import extract_link
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.utils import generate_password_hash
from ihatemoney.versioning import LoggingMode
from ihatemoney.web import build_etag


class TestBudget(IhatemoneyTestCase):
    def test_notifications(self):
                   
                                         
        with self.app.mail.record_messages() as outbox:
                              
            self.login("raclette")

            self.post_project("raclette")
            resp = self.client.post(
                "/raclette/invite",
                data={"emails": "zorglub@notmyidea.org"},
                follow_redirects=True,
            )

                                  
            assert "Your invitations have been sent" in resp.data.decode("utf-8")

            assert len(outbox) == 2
            assert outbox[0].recipients == ["raclette@notmyidea.org"]
            assert outbox[1].recipients == ["zorglub@notmyidea.org"]

                                                    
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite",
                data={"emails": "zorglub@notmyidea.org, toto@notmyidea.org"},
            )

                                                               
            assert len(outbox) == 1
            assert outbox[0].recipients == [
                "zorglub@notmyidea.org",
                "toto@notmyidea.org",
            ]

                               
        with self.app.mail.record_messages() as outbox:
            response = self.client.post("/raclette/invite", data={"emails": "toto"})
            assert len(outbox) == 0                   
            assert (
                'The email <em class="font-italic">toto</em> is not valid'
                in response.data.decode("utf-8")
            )

                                            
        with self.app.mail.record_messages() as outbox:
            response = self.client.post(
                "/raclette/invite",
                data={"emails": "<img src=x onerror=alert(document.domain)>"},
            )
            assert len(outbox) == 0                   
            assert (
                'The email <em class="font-italic">'
                "&lt;img src=x onerror=alert(document.domain)&gt;"
                "</em> is not valid" in response.data.decode("utf-8")
            )

                                                                     
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite", data={"emails": "zorglub@notmyidea.org, zorglub"}
            )             

                                                               
            assert len(outbox) == 0

    def test_invite(self):
                                                            
        self.login("raclette")
        self.post_project("raclette")
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite", data={"emails": "toto@notmyidea.org"})
            assert len(outbox) == 1
            url_start = outbox[0].body.find("You can log in using this link: ") + 32
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
        self.client.post("/exit")
                                        
        resp = self.client.get(url, follow_redirects=True)
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in resp.data.decode("utf-8")
        )
                                       
        self.client.post("/exit")
                                
        parsed_url = urlparse(url)
        resp = self.client.get(
            urlunparse(
                parsed_url._replace(
                    path=parsed_url.path.replace("raclette/", "invalid_project/")
                )
            ),
            follow_redirects=True,
        )
        assert "Create a new project" in resp.data.decode("utf-8")

                                                                 
        resp = self.client.get("/raclette/join/token.invalid", follow_redirects=True)
        assert "Provided token is invalid" in resp.data.decode("utf-8")

    def test_create_should_remember_project(self):
                   
        self.login("raclette")
        self.post_project("raclette")
        self.post_project("tartiflette")
        data = self.client.get("/raclette/").data.decode("utf-8")
        assert data.count('href="/tartiflette/"') == 1

    def test_multiple_join(self):
                                                               
        self.login("raclette")
        self.post_project("raclette")
        project = self.get_project("raclette")
        invite_link = url_for(
            ".join_project", project_id="raclette", token=project.generate_token()
        )

        self.post_project("tartiflette")
        self.client.get(invite_link)
        data = self.client.get("/tartiflette/").data.decode("utf-8")
                          
        assert 'href="/raclette/"' in data

                                                 
        self.client.get(invite_link)
        data = self.client.get("/tartiflette/").data.decode("utf-8")
        assert data.count('href="/raclette/"') == 1

    def test_invalid_invite_link_with_feed_token(self):
                                                                     
        self.post_project("raclette")
        project = self.get_project("raclette")
        invite_link = url_for(
            ".join_project", project_id="raclette", token=project.generate_token("feed")
        )
        response = self.client.get(invite_link, follow_redirects=True)
        assert "Provided token is invalid" in response.data.decode()

    def test_invite_code_invalidation(self):
                                                                
        self.login("raclette")
        self.post_project("raclette")
        response = self.client.get("/raclette/invite").data.decode("utf-8")
        link = extract_link(response, "give them the following invitation link")

        self.client.post("/exit")
        response = self.client.get(link)
                       
        assert response.status_code == 302

                                             
                                                           
        response = self.client.post(
            "/raclette/edit",
            data={
                "name": "raclette",
                "contact_email": "zorglub@notmyidea.org",
                "current_password": "raclette",
                "password": "didoudida",
                "default_currency": "XXX",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "alert-danger" not in response.data.decode("utf-8")

        self.client.post("/exit")
        response = self.client.get(link, follow_redirects=True)
                         
        assert "Provided token is invalid" in response.data.decode("utf-8")

    def test_password_reminder(self):
                                                                                
                                                            

        self.create_project("raclette")

        with self.app.mail.record_messages() as outbox:
                                                            
            self.client.post("/password-reminder", data={"id": "unexisting"})
            assert len(outbox) == 0

                                                         
            self.client.post("/password-reminder", data={"id": "raclette"})
            assert len(outbox) == 1
            assert "raclette" in outbox[0].body
            assert "raclette@notmyidea.org" in outbox[0].recipients

    def test_password_reset(self):
                                                                       

        self.create_project("raclette")
                                               
        with self.app.mail.record_messages() as outbox:
            resp = self.client.post(
                "/password-reminder", data={"id": "raclette"}, follow_redirects=True
            )
                                                            
            assert (
                "A link to reset your password has been sent to you"
                in resp.data.decode("utf-8")
            )
                                          
            assert len(outbox) == 1
            url_start = outbox[0].body.find("You can reset it here: ") + 23
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
                                        
        resp = self.client.get(url)
        assert "Password confirmation</label>" in resp.data.decode("utf-8")
                                           
        self.client.post(
            url, data={"password": "pass", "password_confirmation": "pass"}
        )
        resp = self.login("raclette", password="pass")
        assert (
            "<title>I Hate Money — Account manager - raclette</title>"
            in resp.data.decode("utf-8")
        )
                                    
        resp = self.client.get("/reset-password")
        assert "No token provided" in resp.data.decode("utf-8")
        resp = self.client.get("/reset-password?token=token")
        assert "Invalid token" in resp.data.decode("utf-8")

    def test_project_creation(self):
        with self.client as c:
            with self.app.mail.record_messages() as outbox:
                                     
                resp = c.post(
                    "/create",
                    data={
                        "name": "The fabulous raclette party",
                        "id": "raclette",
                        "password": "party",
                        "contact_email": "raclette@notmyidea.org",
                        "default_currency": "USD",
                    },
                    follow_redirects=True,
                )

                                                                                
                assert len(outbox) == 1
                assert outbox[0].recipients == ["raclette@notmyidea.org"]
                assert "A reminder email has just been sent to you" in resp.data.decode(
                    "utf-8"
                )

                                
            assert session["raclette"]

                                
            assert len(models.Project.query.all()) == 1

                                                   
            self.get_project("raclette")

            c.post(
                "/create",
                data={
                    "name": "Another raclette party",
                    "id": "raclette",                  
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

                                  
            assert len(models.Project.query.all()) == 1

    def test_project_creation_without_public_permissions(self):
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = False
        with self.client as c:
                                 
            c.post(
                "/create",
                data={
                    "name": "The fabulous raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

                                    
            assert "raclette" not in session

                                    
            assert len(models.Project.query.all()) == 0

    def test_project_creation_with_public_permissions(self):
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = True
        with self.client as c:
                                 
            c.post(
                "/create",
                data={
                    "name": "The fabulous raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

                                
            assert session["raclette"]

                                
            assert len(models.Project.query.all()) == 1

    def test_project_deletion(self):
        with self.client as c:
            c.post(
                "/create",
                data={
                    "name": "raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

                           
            assert len(models.Project.query.all()) == 1

                                                                     
                                 
            resp = self.client.get("/raclette/delete")
            assert resp.status_code == 405
            self.client.post("/raclette/delete")
            assert len(models.Project.query.all()) == 1

                             
            c.post(
                "/raclette/delete",
                data={"password": "party"},
            )

                             
            assert len(models.Project.query.all()) == 0

    def test_bill_placeholder(self):
        self.post_project("raclette")
        self.login("raclette")

        result = self.client.get("/raclette/")

                                                                                          
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in result.data.decode("utf-8")
        )

        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

        result = self.client.get("/raclette/")

                                                                      
        assert '<a href="/raclette/add"' in result.data.decode("utf-8")
        assert "Add your first bill" in result.data.decode("utf-8")

    def test_membership(self):
        self.post_project("raclette")
        self.login("raclette")

                                       
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        assert len(self.get_project("raclette").members) == 1

                        
        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

                               
        assert len(self.get_project("raclette").members) == 1

                    
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        assert len(self.get_project("raclette").members) == 2

                                                   
        result = self.client.get("/raclette/")
        assert "jeanne" in result.data.decode("utf-8")

                       
        self.client.post(
            "/raclette/members/%s/delete" % self.get_project("raclette").members[-1].id
        )

                                                           
        assert len(self.get_project("raclette").members) == 1

                          
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        jeanne_id = self.get_project("raclette").members[-1].id

                             
        result = self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": jeanne_id,
                "payed_for": [jeanne_id],
                "bill_type": "Expense",
                "amount": "25",
            },
        )

                       
        self.client.post(f"/raclette/members/{jeanne_id}/delete")

                                                         
        assert len(self.get_project("raclette").members) == 2
        assert len(self.get_project("raclette").active_members) == 1

                                                                               
                                          
        result = self.client.get("/raclette/")
        assert (f"/raclette/members/{jeanne_id}/delete") not in result.data.decode(
            "utf-8"
        )

        result = self.client.get("/raclette/add")
        assert "jeanne" not in result.data.decode("utf-8")

                                                
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        assert len(self.get_project("raclette").active_members) == 2

                                                                            
                                               
        self.post_project("randomid")
        self.login("randomid")
        self.client.post("/randomid/members/add", data={"name": "jeanne"})
        assert len(self.get_project("randomid").active_members) == 1

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

                                       
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        zorglub = self.get_project("raclette").members[-1]

                                   
        assert not zorglub.has_bills()

                             
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": zorglub.id,
                "payed_for": [zorglub.id],
                "bill_type": "Expense",
                "amount": "25",
            },
        )

                                
        zorglub = self.get_project("raclette").members[-1]
        assert zorglub.has_bills()

    def test_member_delete_method(self):
        self.post_project("raclette")
        self.login("raclette")

                                       
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

                                                   
        response = self.client.get("/raclette/members/1/delete")
        assert response.status_code == 405

                                       
        self.client.post("/raclette/members/1/delete")
        assert len(self.get_project("raclette").active_members) == 0
                                               
        self.client.post("/raclette/members/1/delete")

    def test_demo(self):
                                                                
        assert [] == models.Project.query.all()
        self.client.get("/demo")
        demo = self.get_project("demo")
        assert demo is not None

        assert ["Amina", "Georg", "Alice"] == [m.name for m in demo.members]
        assert demo.get_bills().count() == 3

    def test_deactivated_demo(self):
        self.app.config["ACTIVATE_DEMO_PROJECT"] = False

                                                                              
        resp = self.client.get("/demo")
        assert '<a href="/create?project_id=demo">' in resp.data.decode("utf-8")

    def test_authentication(self):
                                                                 
                                    
        resp = self.client.post("/authenticate")
        assert "Authentication" in resp.data.decode("utf-8")

                                                        
        self.create_project("raclette")

                                                                              
                                    
        resp = self.client.get("/raclette", follow_redirects=True)
        assert "Authentication" in resp.data.decode("utf-8")

                                                               
        with self.client as c:
            resp = c.post("/authenticate", data={"id": "raclette", "password": "nope"})

            assert "Authentication" in resp.data.decode("utf-8")
            assert "raclette" not in session

                                                               
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "raclette", "password": "raclette"}
            )

            assert "Authentication" not in resp.data.decode("utf-8")
            assert "raclette" in session
            assert session["raclette"]

                                               
            resp = c.get("/exit")
            self.assertStatus(405, resp)

                                                
            c.post("/exit")
            assert "raclette" not in session

                                                                        
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
        with self.client as c:
            resp = c.post("/admin?goto=%2Fraclette", data={"admin_password": "pass"})
            assert "Authentication" not in resp.data.decode("utf-8")
            assert session["is_admin"]

    def test_authentication_with_upper_case(self):
        self.post_project("Raclette")

                                                               
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "Raclette", "password": "Raclette"}
            )

            assert "Authentication" not in resp.data.decode("utf-8")
            assert "raclette" in session
            assert session["raclette"]

    def test_admin_authentication(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
                                                                              
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = False

                                                                                               
        resp = self.client.get("/create")
        assert "/admin?goto=/create" in unquote(resp.location)

                             
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "pass"}
        )
        assert '<a href="/create">/create</a>' in resp.data.decode("utf-8")

                             
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )
        assert '<a href="/create">/create</a>' not in resp.data.decode("utf-8")

                             
        resp = self.client.post("/admin?goto=%2Fcreate", data={"admin_password": ""})
        assert '<a href="/create">/create</a>' not in resp.data.decode("utf-8")

    def test_login_throttler(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")

                                                                                          
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )

        assert "Too many failed login attempts." in resp.data.decode("utf-8")
                                   
        from ihatemoney.utils import limiter

        try:
            limiter.enabled = False
            resp = self.client.post(
                "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
            )
            assert "Too many failed login attempts." not in resp.data.decode("utf-8")
        finally:
            limiter.enabled = True

    def test_manage_bills(self):
        self.post_project("raclette")

                              
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})

        members_ids = [m.id for m in self.get_project("raclette").members]

                       
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "25",
            },
        )
        self.get_project("raclette")
        bill = models.Bill.query.one()
        assert bill.amount == 25

                       
        self.client.post(
            f"/raclette/edit/{bill.id}",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "10",
            },
        )

        bill = models.Bill.query.one()
        assert bill.amount == 10, "bill edition"

                                                           
        response = self.client.get(f"/raclette/delete/{bill.id}")
        assert response.status_code == 405
        assert 1 == len(models.Bill.query.all()), "bill deletion"
                                
        self.client.post(f"/raclette/delete/{bill.id}")
        assert 0 == len(models.Bill.query.all()), "bill deletion"

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "19",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids[0],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "17",
            },
        )

        balance = self.get_project("raclette").balance
        assert set(balance.values()) == set([19.0, -19.0])

                                   
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-12",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "-25",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2011-08-12")[0]
        assert bill.amount == -25

                                 
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-01",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "25,02",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2011-08-01")[0]
        assert bill.amount == 25.02

                                               
        self.client.post(
            "/raclette/add",
            data={
                "date": "2015-05-05",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "42",
                "external_link": "https://example.com/fromage",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2015-05-05")[0]
        assert bill.external_link == "https://example.com/fromage"

                                                  
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2015-05-06",
                "what": "mauvais fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "42000",
                "external_link": "javascript:alert('Tu bluffes, Martoni.')",
            },
        )
        assert "Invalid URL" in resp.data.decode("utf-8")

    def test_reimbursement_bill(self):
        self.post_project("rent")

                              
        self.client.post("/rent/members/add", data={"name": "bob"})
        self.client.post("/rent/members/add", data={"name": "alice"})

        everybody = [m.id for m in self.get_project("rent").members]
        bob = everybody[0]
        alice = everybody[1]

                       
        self.client.post(
            "/rent/add",
            data={
                "date": "2022-12-12",
                "what": "december rent",
                "payer": bob,
                "payed_for": everybody,
                "bill_type": "Expense",
                "amount": "1000",
            },
        )
                       
        balance = self.get_project("rent").balance
        assert set(balance.values()), set([500 == -500])

        project = self.get_project("rent")
        bob_paid = project.full_balance[2][bob]
        alice_paid = project.full_balance[2][alice]
        assert bob_paid == 1000
        assert alice_paid == 0

                            
        self.client.post(
            "/rent/add",
            data={
                "date": "2022-12-13",
                "what": "reimbursement for rent",
                "payer": alice,
                "payed_for": bob,
                "bill_type": "Reimbursement",
                "amount": "500",
            },
        )

        balance = project.balance
        assert set(balance.values()), set([0 == 0])

                                                                            
                        
        bob_paid = project.full_balance[2][bob]
        alice_paid = project.full_balance[2][alice]
        assert bob_paid == 1000
        assert alice_paid == 0

        bob_received = project.full_balance[4][bob]
        alice_transferred = project.full_balance[3][alice]
        assert bob_received == 500
        assert alice_transferred == 500

    def test_weighted_balance(self):
        self.post_project("raclette")

                              
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post(
            "/raclette/members/add", data={"name": "jeannedy familly", "weight": 4}
        )

        members_ids = [m.id for m in self.get_project("raclette").members]

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "10",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "pommes de terre",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "bill_type": "Expense",
                "amount": "10",
            },
        )

        balance = self.get_project("raclette").balance
        assert set(balance.values()) == set([6, -6])

    def test_trimmed_members(self):
        self.post_project("raclette")

                                                                  
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "zorglub "})
        members = self.get_project("raclette").members

        assert len(members) == 1

    def test_weighted_members_list(self):
        self.post_project("raclette")

                              
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "tata", "weight": 1})

        resp = self.client.get("/raclette/")
        assert "extra-info" in resp.data.decode("utf-8")

        self.client.post(
            "/raclette/members/add", data={"name": "jeannedy familly", "weight": 4}
        )

        resp = self.client.get("/raclette/")
        assert "extra-info" not in resp.data.decode("utf-8")

    def test_negative_weight(self):
        self.post_project("raclette")

                                                           
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        resp = self.client.post(
            "/raclette/members/1/edit", data={"name": "zorglub", "weight": -1}
        )

                                                                         
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")
        assert len(self.get_project("raclette").members) == 1
        assert self.get_project("raclette").members[0].weight == 1

    def test_rounding(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "24.36",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "19.12",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "22",
            },
        )

        balance = self.get_project("raclette").balance
        result = {}
        result[self.get_project("raclette").members[0].id] = 8.12
        result[self.get_project("raclette").members[1].id] = 0.0
        result[self.get_project("raclette").members[2].id] = -8.12
                                                                              
                                                         
                                                                                 
                                              
        for key, value in balance.items():
            assert round(value, 2) == result[key]

    def test_edit_project(self):
                                      

        self.post_project("raclette")
        new_data = {
            "name": "Super raclette party!",
            "contact_email": "zorglub@notmyidea.org",
            "password": "didoudida",
            "logging_preference": LoggingMode.ENABLED.value,
            "default_currency": "USD",
        }

                                                                 
        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=False)
        assert "This field is required" in resp.data.decode("utf-8")
        project = self.get_project("raclette")
        assert project.name != new_data["name"]
        assert project.contact_email != new_data["contact_email"]
        assert project.default_currency != new_data["default_currency"]
        assert not check_password_hash(project.password, new_data["password"])

                                                                 
        new_data["current_password"] = "patates au fromage"
        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=False)
        assert "Invalid private code" in resp.data.decode("utf-8")
        project = self.get_project("raclette")
        assert project.name != new_data["name"]
        assert project.contact_email != new_data["contact_email"]
        assert project.default_currency != new_data["default_currency"]
        assert not check_password_hash(project.password, new_data["password"])

                                                            
        new_data["current_password"] = "raclette"
        resp = self.client.post("/raclette/edit", data=new_data)
        assert resp.status_code == 302
        project = self.get_project("raclette")
        assert project.name == new_data["name"]
        assert project.contact_email == new_data["contact_email"]
        assert project.default_currency == new_data["default_currency"]
        assert check_password_hash(project.password, new_data["password"])

                                                                  
        new_data["contact_email"] = "wrong_email"

        resp = self.client.post("/raclette/edit", data=new_data)
        assert "Invalid email address" in resp.data.decode("utf-8")

    def test_dashboard(self):
                                                           
        resp = self.client.post(
            "/admin?goto=%2Fdashboard",
            data={"admin_password": "adminpass"},
            follow_redirects=True,
        )
        assert '<div class="alert alert-danger">' in resp.data.decode("utf-8")

                                                           
        self.enable_admin()
        resp = self.client.get("/dashboard")
        assert """<thead>
        <tr>
            <th>Project</th>
            <th>Number of participants</th>""" in resp.data.decode("utf-8")

    def test_dashboard_project_deletion(self):
        self.post_project("raclette")
        self.enable_admin()
        resp = self.client.get("/dashboard")
        pattern = re.compile(r"<form id=\"delete-project\" [^>]*?action=\"(.*?)\"")
        match = pattern.search(resp.data.decode("utf-8"))
        assert match is not None
        assert match.group(1) is not None

        resp = self.client.post(match.group(1))

                         
        assert len(models.Project.query.all()) == 0

    def test_statistics_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/statistics")
        assert response.status_code == 200

    def test_statistics(self):
                                             
        self.post_project("raclette", default_currency="USD")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
                                                 
        self.client.post("/raclette/members/add", data={"name": "pépé"})

                                                                         
        project = self.get_project("raclette")
        assert len(project.active_months_range()) == 0
        assert len(project.monthly_stats) == 0

                                                        
                       
        response = self.client.get("/raclette/statistics")

        regex = (
            r'<table id="monthly_stats" class="table table-striped">\n'
            r"    <thead>\n"
            r"      <tr>\n"
            r"        <th>Period</th>\n"
            r"        <th>Expenses</th>\n"
            r"      </tr>\n"
            r"    </thead>\n"
            r"    <tbody>\n"
            r"      \n"
            r"    </tbody>\n"
            r"  </table>"
        )

        assert re.search(regex, response.data.decode("utf-8"))
                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10",
            },
        )

        response = self.client.get("/raclette/statistics")
        html = response.data.decode("utf-8")

        def stat_entry(name, paid, spent, transferred=None, received=None):
            return (
                f'<td class="d-md-none">{name}</td>\n'
                f"        <td>{paid}</td>\n"
                f"        <td>{spent}</td>\n"
                                                
                                                    
            )

                             

                           
                                                           
                                         
                                         
                   

        assert stat_entry("zorglub", "$20.00", "-$31.67") in html
        assert stat_entry("jeanne", "$20.00", "-$5.83") in html
        assert stat_entry("tata", "$0.00", "-$2.50") in html
        assert stat_entry("pépé", "$0.00", "-$0.00") in html
                                                                          
                                    
        order = ["jeanne", "pépé", "tata", "zorglub"]
        regex1 = r".*".join(
            r"<td class=\"balance-name\">{}</td>".format(name) for name in order
        )
        regex2 = r".*".join(
            r"<td class=\"d-md-none\">{}</td>".format(name) for name in order
        )
                                                                       
                                         
        assert re.search(re.compile(regex1, re.DOTALL), response.data.decode("utf-8"))
        assert re.search(re.compile(regex2, re.DOTALL), response.data.decode("utf-8"))

                                                                                            
        august = date(year=2011, month=8, day=1)
        assert project.active_months_range() == [august]
        assert dict(project.monthly_stats[2011]) == {8: 40.0}

                                                                     
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-12-20",
                "what": "fromage à raclette",
                "payer": 2,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "30",
            },
        )
        months = [
            date(year=2011, month=12, day=1),
            date(year=2011, month=11, day=1),
            date(year=2011, month=10, day=1),
            date(year=2011, month=9, day=1),
            date(year=2011, month=8, day=1),
        ]
        amounts_2011 = {
            12: 30.0,
            8: 40.0,
        }
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

                                                                   
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-01",
                "what": "ice cream",
                "payer": 2,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10",
            },
        )
        amounts_2011[8] += 10.0
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

                                          
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-12-31",
                "what": "champomy",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10",
            },
        )
        amounts_2011[12] += 10.0
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

                                          
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-07-31",
                "what": "smoothie",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "20",
            },
        )
        months.append(date(year=2011, month=7, day=1))
        amounts_2011[7] = 20.0
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

                                           
        self.client.post(
            "/raclette/add",
            data={
                "date": "2012-01-01",
                "what": "more champomy",
                "payer": 2,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "30",
            },
        )
        months.insert(0, date(year=2012, month=1, day=1))
        amounts_2012 = {1: 30.0}
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011
        assert dict(project.monthly_stats[2012]) == amounts_2012

    def test_settle_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/settle_bills")
        assert response.status_code == 200

    def test_settle(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
                                                 
        self.client.post("/raclette/members/add", data={"name": "pépé"})

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10",
            },
        )
        project = self.get_project("raclette")
        transactions = project.get_transactions_to_settle_bill()
        members = defaultdict(int)
                                                                                  
        for t in transactions:
            members[t["ower"]] -= t["amount"]
            members[t["receiver"]] += t["amount"]
        balance = self.get_project("raclette").balance
        for m, a in members.items():
            assert abs(a - balance[m.id]) < 0.01
        return

    def test_settle_button(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
                                                 
        self.client.post("/raclette/members/add", data={"name": "pépé"})

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10",
            },
        )
        project = self.get_project("raclette")
        transactions = project.get_transactions_to_settle_bill()

        count = 0
        for t in transactions:
            count += 1
            self.client.post(
                "/raclette/settle",
                data={
                    "amount": t["amount"],
                    "sender_id": t["ower"].id,
                    "receiver_id": t["receiver"].id,
                },
            )
            temp_transactions = project.get_transactions_to_settle_bill()
                                             
            assert len(temp_transactions) == len(transactions) - count

                                                                     
            bill = project.get_newest_bill()
            assert bill.bill_type == models.BillType.REIMBURSEMENT

                                                             
        transactions = project.get_transactions_to_settle_bill()
        assert len(transactions) == 0

    def test_settle_zero(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1, 3],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "refund",
                "payer": 3,
                "payed_for": [2],
                "bill_type": "Expense",
                "amount": "13.33",
            },
        )
        project = self.get_project("raclette")
        transactions = project.get_transactions_to_settle_bill()

                                                                     
        for t in transactions:
            rounded_amount = round(t["amount"], 2)
            assert (
                0.0 != rounded_amount
            ), f"{t['amount']} is equal to zero after rounding"

    def test_access_other_projects(self):
                                                                                              
                        
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

                     
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3, 4],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )
                                    
        raclette = self.get_project("raclette")
        assert raclette.get_bills().count() == 1

                 
        self.client.post("/exit")

                                              
        self.post_project("tartiflette")

                                                  
        self.client.post("/tartiflette/members/add", data={"name": "pirate"})
        pirate = models.Person.query.filter(models.Person.id == 5).one()
        assert pirate.name == "pirate"

                                                  
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "fromage frelaté",
                "payer": 2,
                "payed_for": [2, 3, 4],
                "bill_type": "Expense",
                "amount": "100.0",
            },
        )
                                        
        raclette = self.get_project("raclette")
        assert raclette.get_bills().count() == 1

                                                                                          
                                           
        resp = self.client.post(
            "/tartiflette/add",
            data={
                "date": "2017-01-01",
                "what": "soupe",
                "payer": 5,
                "payed_for": [3],
                "bill_type": "Expense",
                "amount": "5000.0",
            },
        )
                                        
        piratebill = models.Bill.query.filter(models.Bill.what == "soupe").one_or_none()
        assert piratebill is None, "piratebill 1 should not exist"

                                    
        self.client.post(
            "/tartiflette/add",
            data={
                "date": "2017-02-01",
                "what": "pain",
                "payer": 3,
                "payed_for": [5],
                "bill_type": "Expense",
                "amount": "5000.0",
            },
        )
                                        
        piratebill = models.Bill.query.filter(models.Bill.what == "pain").one_or_none()
        assert piratebill is None, "piratebill 2 should not exist"

                                                      
        self.client.post(
            "/tartiflette/add",
            data={
                "date": "2017-03-01",
                "what": "baguette",
                "payer": 5,
                "payed_for": [5],
                "bill_type": "Expense",
                "amount": "5.0",
            },
        )
                                    
        okbill = models.Bill.query.filter(models.Bill.what == "baguette").one_or_none()
        assert okbill is not None, "Bill baguette should exist"
        assert okbill.what == "baguette"

                                                     
        modified_bill = {
            "date": "2018-12-31",
            "what": "roblochon",
            "payer": 2,
            "payed_for": [1, 3, 4],
            "bill_type": "Expense",
            "amount": "100.0",
        }
                                               
        resp = self.client.get("/raclette/edit/1")
        self.assertStatus(303, resp)
                                                     
        resp = self.client.get("/tartiflette/edit/1")
        self.assertStatus(404, resp)
                          
        resp = self.client.post("/raclette/edit/1", data=modified_bill)
        self.assertStatus(303, resp)
                                
        resp = self.client.post("/tartiflette/edit/1", data=modified_bill)
        self.assertStatus(404, resp)
                            
        resp = self.client.post("/raclette/delete/1")
        self.assertStatus(303, resp)
                                  
        resp = self.client.post("/tartiflette/delete/1")
        self.assertStatus(302, resp)

                                                                           
        bill = models.Bill.query.filter(models.Bill.id == 1).one()
        assert bill.what == "fromage à raclette"

                                                                    
                                                                             

        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/edit/1", data=modified_bill)
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        assert bill is not None, "bill not found"
        assert bill.what == "roblochon"
        self.client.post("/raclette/delete/1")
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        assert bill is None

                                           
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "tartiflette", "password": "tartiflette"}
        )
        modified_member = {
            "name": "bulgroz",
            "weight": 42,
        }
                                                   
        resp = self.client.get("/raclette/members/1/edit")
        self.assertStatus(303, resp)
                                    
        resp = self.client.get("/tartiflette/members/1/edit")
        self.assertStatus(404, resp)
                            
        resp = self.client.post("/raclette/members/1/edit", data=modified_member)
        self.assertStatus(303, resp)
                                  
        resp = self.client.post("/tartiflette/members/1/edit", data=modified_member)
        self.assertStatus(404, resp)
                              
        resp = self.client.post("/raclette/members/1/delete")
        self.assertStatus(303, resp)
                                    
        resp = self.client.post("/tartiflette/members/1/delete")
        self.assertStatus(302, resp)

                                                                             
        member = models.Person.query.filter(models.Person.id == 1).one_or_none()
        assert member is not None, "member not found"
        assert member.name == "zorglub"
        assert member.activated

                                                                      
                                                                               
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/members/1/edit", data=modified_member)
        member = models.Person.query.filter(models.Person.id == 1).one()
        assert member.name == "bulgroz"
        self.client.post("/raclette/members/1/delete")
        member = models.Person.query.filter(models.Person.id == 1).one_or_none()
        assert member is None

                                                              
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "tartiflette", "password": "tartiflette"}
        )
        self.client.post(
            "/tartiflette/settle",
            data={
                "sender_id": 4,
                "receiver_id": 5,
                "amount": "42.0",
            },
        )
        piratebill = models.Bill.query.filter(
            models.Bill.bill_type == models.BillType.REIMBURSEMENT
        ).one_or_none()
        assert piratebill is None, "piratebill 3 should not exist"

    @pytest.mark.skip(reason="Currency conversion is broken")
    def test_currency_switch(self):
                                      
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

                      
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "bill_type": "Expense",
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1, 3],
                "bill_type": "Expense",
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "refund",
                "payer": 3,
                "payed_for": [2],
                "bill_type": "Expense",
                "amount": "13.33",
            },
        )

        project = self.get_project("raclette")

                                                                                   
        for bill in project.get_bills():
            assert bill.original_currency == CurrencyConverter.no_currency
            assert bill.amount == bill.converted_amount

                                                                                
        project.switch_currency("EUR")
        for bill in project.get_bills():
            assert bill.original_currency == "EUR"
            assert bill.amount == bill.converted_amount

                                                         
        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "refund from EUR",
                "payer": 3,
                "payed_for": [2],
                "bill_type": "Expense",
                "amount": "20",
                "original_currency": "EUR",
            },
        )
        last_bill = project.get_bills().first()
        assert last_bill.converted_amount == last_bill.amount

                              
        project.switch_currency(CurrencyConverter.no_currency)
        for bill in project.get_bills():
            assert bill.original_currency == CurrencyConverter.no_currency
            assert bill.amount == bill.converted_amount

                                                 
        project.switch_currency("EUR")
                               
        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "Poutine",
                "payer": 3,
                "payed_for": [2],
                "bill_type": "Expense",
                "amount": "18",
                "original_currency": "CAD",
            },
        )
        last_bill = project.get_bills().first()
        expected_amount = self.converter.exchange_currency(
            last_bill.amount, "CAD", "EUR"
        )
        assert last_bill.converted_amount == expected_amount

                                                                                         
        project.switch_currency("USD")
        for bill in project.get_bills():
            assert bill.original_currency != "USD"
            expected_amount = self.converter.exchange_currency(
                bill.amount, bill.original_currency, "USD"
            )
            assert bill.converted_amount == expected_amount

                                                 
        with pytest.raises(ValueError):
            project.switch_currency(CurrencyConverter.no_currency)

                                                             
        resp = self.client.post(
            "/raclette/edit",
            data={
                "name": "demonstration",
                "password": "demo",
                "contact_email": "demo@notmyidea.org",
                "project_history": "y",
                "default_currency": CurrencyConverter.no_currency,
            },
        )
                                                                                          
        self.assertStatus(200, resp)
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")
        assert self.get_project("raclette").default_currency == "USD"

    @pytest.mark.skip(reason="Currency conversion is broken")
    def test_currency_switch_to_bill_currency(self):
                                                                                       
        self.post_project("raclette", default_currency="USD")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})

                                                               
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        project = self.get_project("raclette")

        bill = project.get_bills().first()
        assert (
            self.converter.exchange_currency(bill.amount, "EUR", "USD")
            == bill.converted_amount
        )

                                                                     
        project.switch_currency("EUR")
        bill = project.get_bills().first()
        assert bill.converted_amount == bill.amount

    @pytest.mark.skip(reason="Currency conversion is broken")
    def test_currency_switch_to_no_currency(self):
                                                                                       
        self.post_project("raclette", default_currency="USD")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})

                                                                
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "aspirine",
                "payer": 2,
                "payed_for": [1, 2],
                "bill_type": "Expense",
                "amount": "5.0",
                "original_currency": "EUR",
            },
        )

        project = self.get_project("raclette")

        for bill in project.get_bills_unordered():
            assert (
                self.converter.exchange_currency(bill.amount, "EUR", "USD")
                == bill.converted_amount
            )

                                                                                         
        project.switch_currency(CurrencyConverter.no_currency)
        no_currency_bills = [
            (bill.amount, bill.converted_amount) for bill in project.get_bills()
        ]
        assert no_currency_bills == [(5.0, 5.0), (10.0, 10.0)]

    def test_amount_is_null(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

                     
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "0",
                "original_currency": "XXX",
            },
        )

                                        
        project = self.get_project("raclette")
        assert project.get_bills().count() == 1
        last_bill = project.get_bills().first()
        assert last_bill.amount == 0

    def test_decimals_on_weighted_members_list(self):
        self.post_project("raclette")

                                                
        self.client.post(
            "/raclette/members/add", data={"name": "zorglub", "weight": 1.0}
        )
        self.client.post("/raclette/members/add", data={"name": "tata", "weight": 1.10})
        self.client.post(
            "/raclette/members/add", data={"name": "jeanne", "weight": 1.15}
        )

                                                                     
        resp = self.client.get("/raclette/")
        assert 'zorglub<span class="light">(x1)</span>' in resp.data.decode("utf-8")
        assert 'tata<span class="light">(x1.1)</span>' in resp.data.decode("utf-8")
        assert 'jeanne<span class="light">(x1.15)</span>' in resp.data.decode("utf-8")

    def test_amount_too_high(self):
        self.post_project("raclette")

                          
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

                                         
                                                              
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "bill_type": "Expense",
                "amount": "9347242149381274732472348728748723473278472843.12",
                "original_currency": "EUR",
            },
        )
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")

                                                             
        resp = self.client.get("/raclette/")
                                                  
        assert "No bills" in resp.data.decode("utf-8")

    def test_session_projects_migration_to_list(self):
                   
        self.post_project("raclette")
        self.client.get("/exit")

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert session["raclette"]
                          
            assert isinstance(session["projects"], dict)
                                      
            with c.session_transaction() as sess:
                sess["projects"] = [("raclette", "raclette")]
                                             
            c.get("/")
            assert isinstance(session["projects"], dict)
            assert "raclette" in session["projects"]

    def test_rss_feed(self):
                   
        self.post_project("raclette", default_currency="EUR")
        self.client.post("/raclette/members/add", data={"name": "george"})
        self.client.post("/raclette/members/add", data={"name": "peter"})
        self.client.post("/raclette/members/add", data={"name": "steven"})

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "amount": "12",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-30",
                "what": "charcuterie",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "15",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-29",
                "what": "vin blanc",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "10",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )

        project = self.get_project("raclette")
        token = project.generate_token("feed")
        resp = self.client.get(f"/raclette/feed/{token}.xml")

        content = resp.data.decode()

        assert (
            f"""<channel>
        <title>I Hate Money — raclette</title>
        <description>Latest bills from raclette</description>
        <atom:link href="http://localhost/raclette/feed/{token}.xml" rel="self" type="application/rss+xml" />
        <link>http://localhost/raclette/</link>
        <item>
            <title>fromage à raclette - €12.00</title>
            <guid isPermaLink="false">1</guid>
            <dc:creator>george</dc:creator>
            <description>December 31, 2016 - george, peter, steven : €4.00</description>
        """
            in content
        )

        assert """<title>charcuterie - €15.00</title>""" in content
        assert """<title>vin blanc - €10.00</title>""" in content

    def test_rss_feed_history_disabled(self):
                   
        self.post_project("raclette", default_currency="EUR", project_history=False)
        self.client.post("/raclette/members/add", data={"name": "george"})
        self.client.post("/raclette/members/add", data={"name": "peter"})
        self.client.post("/raclette/members/add", data={"name": "steven"})

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "amount": "12",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-30",
                "what": "charcuterie",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "15",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-29",
                "what": "vin blanc",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "10",
                "original_currency": "EUR",
                "bill_type": "Expense",
            },
        )

        project = self.get_project("raclette")
        token = project.generate_token("feed")
        resp = self.client.get(f"/raclette/feed/{token}.xml")

        content = resp.data.decode()
        assert """<title>charcuterie - €15.00</title>""" in content
        assert """<title>vin blanc - €10.00</title>""" in content

    def test_rss_if_modified_since_header(self):
                          
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "george"})
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 200
        assert "Last-Modified" in resp.headers.keys()
        last_modified = resp.headers.get("Last-Modified")

                                                         
        before = datetime.strptime(
            last_modified, "%a, %d %b %Y %H:%M:%S %Z"
        ) - timedelta(hours=1)
        before_str = before.strftime("%a, %d %b %Y %H:%M:%S %Z")

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": before_str},
        )
        assert resp.status_code == 200

        after = datetime.strptime(
            last_modified, "%a, %d %b %Y %H:%M:%S %Z"
        ) + timedelta(hours=1)
        after_str = after.strftime("%a, %d %b %Y %H:%M:%S %Z")

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": after_str},
        )
        assert resp.status_code == 304

                  
        self.login("raclette")
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "12",
                "original_currency": "XXX",
                "bill_type": "Expense",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "The bill has been added" in resp.data.decode()

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": before_str},
        )
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": after_str},
        )
        assert resp.status_code == 304

    def test_rss_etag_headers(self):
                          
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "george"})
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        etag = resp.headers.get("ETag")
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": etag,
            },
        )
        assert resp.status_code == 304

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": build_etag(project.id, "2023-07-26T13:00:00"),
            },
        )
        assert resp.status_code == 200

                  
        self.login("raclette")
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "12",
                "bill_type": "Expense",
                "original_currency": "XXX",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "The bill has been added" in resp.data.decode()
        etag = resp.headers.get("ETag")

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-None-Match": etag},
        )
        assert resp.status_code == 200
        new_etag = resp.headers.get("ETag")

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": new_etag,
            },
        )
        assert resp.status_code == 304

    def test_rss_feed_bad_token(self):
        self.post_project("raclette")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 200
        resp = self.client.get("/raclette/feed/invalid-token.xml")
        assert resp.status_code == 404

    def test_rss_feed_different_project_with_same_password(
        self,
    ):
                   
        self.post_project("raclette", password="password")
        self.post_project("reblochon", password="password")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/reblochon/feed/{token}.xml")
        assert resp.status_code == 404

    def test_rss_feed_different_project_with_different_password(
        self,
    ):
                   
        self.post_project("raclette", password="password")
        self.post_project("reblochon", password="another-password")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/reblochon/feed/{token}.xml")
        assert resp.status_code == 404

    def test_rss_feed_invalidated_token(self):
                   
        self.post_project("raclette")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 200

        self.client.post(
            "/raclette/edit",
            data={
                "name": "raclette",
                "contact_email": "zorglub@notmyidea.org",
                "current_password": "raclette",
                "password": "didoudida",
                "default_currency": "XXX",
            },
            follow_redirects=True,
        )

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 404

    def test_remember_payer_per_project(self):
                   
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        members_ids = [m.id for m in self.get_project("raclette").members]
                       
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "amount": "25",
                "bill_type": "Expense",
            },
        )

        self.post_project("tartiflette")
        self.client.post("/tartiflette/members/add", data={"name": "pluton"})
        self.client.post("/tartiflette/members/add", data={"name": "mars"})
        self.client.post("/tartiflette/members/add", data={"name": "venus"})
        members_ids_tartif = [m.id for m in self.get_project("tartiflette").members]
                       
        self.client.post(
            "/tartiflette/add",
            data={
                "date": "2011-08-12",
                "what": "fromage à tartiflette spatial",
                "payer": members_ids_tartif[2],
                "payed_for": members_ids_tartif,
                "amount": "24",
                "bill_type": "Expense",
            },
        )

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert isinstance(session["last_selected_payer_per_project"], dict)
            assert "raclette" in session["last_selected_payer_per_project"]
            assert "tartiflette" in session["last_selected_payer_per_project"]
            assert (
                session["last_selected_payer_per_project"]["raclette"] == members_ids[1]
            )
            assert (
                session["last_selected_payer_per_project"]["tartiflette"]
                == members_ids_tartif[2]
            )

    def test_remember_payed_for(self):
                   
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "pipistrelle"})
        members_ids = [m.id for m in self.get_project("raclette").members]
                       
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids[1:],
                "amount": "25",
                "bill_type": "Expense",
            },
        )

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert isinstance(session["last_selected_payed_for"], dict)
            assert "raclette" in session["last_selected_payed_for"]
            assert session["last_selected_payed_for"]["raclette"] == members_ids[1:]
