"""Independent business, HTTP, transaction and declaration tests using synthetic data."""

from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]

from app.storage import Store
from app.service import Service,BusinessError
from app.web import create_app
from bo_stategraph import BOStateGraph
from bo_stategraph.native_executor import BOExecutor
from bo_observer.data.catalog import collect,export_sqlalchemy_metadata
from bo_observer.data.schema_compare import structure_differences
from app.models import metadata


class SharingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="unittest-",dir=ROOT/"review")
        self.project=json.loads((ROOT/"bo_stategraph/project.json").read_text(encoding="utf-8"))
        self.store=Store(self.temp.name)
        self.store.initialize()
        self.service=Service(self.store,self.project,ROOT)
        self.file=self.service.upload("owner","notes.txt",b"Private synthetic content")
        self.share=self.service.request_share("owner",self.file["id"],"recipient","reviewer")

    def tearDown(self):
        self.store.engine.dispose()
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to((ROOT/"review").resolve()))
        self.temp.cleanup()

    def state(self):
        return self.store.snapshot("test")["instances"][0]["state"]

    def test_login_and_bad_password(self):
        self.assertEqual(self.service.login("owner","TrialOnly!2026")["id"],"owner")
        with self.assertRaises(BusinessError):
            self.service.login("owner","incorrect")

    def test_selected_reviewer_and_three_party_messages(self):
        with self.assertRaises(BusinessError):
            self.service.change_share("other",self.share["id"],"approve")
        self.service.change_share("reviewer",self.share["id"],"approve")
        snapshot=self.store.snapshot("test")
        self.assertEqual(snapshot["instances"][0]["state"],"approved")
        for kind in ["review_result","shared"]:
            self.assertEqual(sorted(message["user_id"] for message in snapshot["messages"] if message["kind"]==kind),["owner","recipient","reviewer"])
        self.assertEqual(self.service.download("recipient",self.file["id"])[1],b"Private synthetic content")

    def test_pending_and_rejected_have_no_recipient_access(self):
        self.assertEqual(self.service.dashboard("recipient")["received"],[])
        with self.assertRaises(BusinessError):
            self.service.download("recipient",self.file["id"])
        self.service.change_share("reviewer",self.share["id"],"reject")
        self.assertEqual(self.service.dashboard("recipient")["received"],[])
        with self.assertRaises(BusinessError):
            self.service.download("recipient",self.file["id"])
        self.assertEqual(len(self.store.snapshot("test")["messages"]),3)

    def test_cancel_blocks_late_approval(self):
        self.service.change_share("owner",self.share["id"],"cancel")
        with self.assertRaises(BusinessError):
            self.service.change_share("reviewer",self.share["id"],"approve")
        self.assertEqual(self.state(),"cancelled")
        self.assertEqual(self.store.snapshot("test")["messages"],[])

    def test_nonowner_cannot_cancel_or_revoke(self):
        with self.assertRaises(BusinessError):
            self.service.change_share("other",self.share["id"],"cancel")
        self.service.change_share("reviewer",self.share["id"],"approve")
        with self.assertRaises(BusinessError):
            self.service.change_share("recipient",self.share["id"],"revoke")
        self.assertEqual(self.state(),"approved")

    def test_stale_browser_download_after_revocation(self):
        self.service.change_share("reviewer",self.share["id"],"approve")
        application=create_app(self.service)
        client=application.test_client()
        with client.session_transaction() as session:
            session["user"]={"id":"recipient","name":"Xu"}
        old_page=client.get("/")
        url="/download/"+self.file["id"]
        self.assertIn(url.encode(),old_page.data)
        downloaded=client.get(url)
        self.assertEqual(downloaded.status_code,200)
        self.service.change_share("owner",self.share["id"],"revoke")
        self.assertEqual(client.get(url).status_code,403)
        self.assertEqual(downloaded.data,b"Private synthetic content")
        self.assertEqual(self.service.dashboard("recipient")["received"],[])

    def test_notification_is_private(self):
        self.service.change_share("reviewer",self.share["id"],"approve")
        message=self.service.dashboard("recipient")["messages"][0]
        with self.assertRaises(BusinessError):
            self.service.read_notification("other",message["id"])
        self.service.read_notification("recipient",message["id"])
        self.assertEqual(next(row for row in self.service.dashboard("recipient")["messages"] if row["id"]==message["id"])["is_read"],1)

    def test_failed_message_write_rolls_back_state_and_all_messages(self):
        original=self.service._messages
        def fail_after_insert(*args):
            original(*args)
            raise OSError("synthetic transaction failure")
        with patch.object(self.service,"_messages",fail_after_insert):
            with self.assertRaises(OSError):
                self.service.change_share("reviewer",self.share["id"],"approve")
        snapshot=self.store.snapshot("test")
        self.assertEqual(snapshot["instances"][0]["state"],"pending")
        self.assertEqual(snapshot["messages"],[])
        self.assertEqual(len(snapshot["instances"][0]["journal"]),1)

    def test_cancel_approve_race_has_one_authoritative_result(self):
        barrier=threading.Barrier(2)
        results=[]
        def act(actor,event):
            barrier.wait()
            try:
                results.append(self.service.change_share(actor,self.share["id"],event)["state"])
            except BusinessError:
                results.append("denied")
        threads=[threading.Thread(target=act,args=("owner","cancel")),threading.Thread(target=act,args=("reviewer","approve"))]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5)
        self.assertEqual(len(results),2)
        self.assertEqual(results.count("denied"),1)
        self.assertIn(self.state(),{"approved","cancelled"})
        self.assertEqual(len(self.store.snapshot("test")["messages"]),6 if self.state()=="approved" else 0)

    def test_http_csrf_and_anonymous_download(self):
        application=create_app(self.service)
        client=application.test_client()
        client.get("/")
        client.post("/",data={"action":"login","username":"owner","password":"TrialOnly!2026","csrf":"incorrect"})
        with client.session_transaction() as session:
            self.assertNotIn("user",session)
        self.assertEqual(client.get("/download/"+self.file["id"]).status_code,401)

    def test_native_executor_rejects_unsupported_semantics(self):
        invalid=deepcopy(self.project["model"]["machine"])
        invalid["queued"]=True
        with self.assertRaises(ValueError):
            BOExecutor(invalid,{"authorized":lambda context,payload:True})

    def test_real_schema_change_is_detected_without_mutating_application_schema(self):
        import os
        os.environ["TEST_TRIAL_DB"]="sqlite:///"+self.store.database.as_posix()
        config={"id":"application","engine":"sqlalchemy","url_env":"TEST_TRIAL_DB"}
        before=collect(config,root=ROOT)
        with closing(sqlite3.connect(self.store.database)) as connection:
            connection.execute("ALTER TABLE shares ADD COLUMN review_note TEXT")
            connection.commit()
        after=collect(config,root=ROOT)
        self.assertNotEqual(before,after)
        share_table=next(table for table in after["resources"] if table["key"]=="table:shares")
        self.assertIn("review_note",[field["name"] for field in share_table["fields"]])


if __name__=="__main__":
    unittest.main()
