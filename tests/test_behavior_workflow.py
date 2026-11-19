"""The new report remains subordinate to the original coordinator's gates."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import test_behavior_coverage as fixtures
from bo_observer.workflow.behavior_iteration import finalize, previous_evidence
from bo_observer.workflow.change_sync import review_errors
from bo_observer.workflow.iteration_recall import recall


class BehaviorWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.BehaviorCoverageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.current=deepcopy(self.fixture.snapshot)
        self.current.update(id='candidate',files={'application.py':'one'},tools={},
            intent={'requirements':[{'id':'R1','status':'confirmed'}]},
            source_inventory={'files':{'application.py':{}}})
        self.current['model'].update(edges=[],intent='intent.json')
        self.report={'valid':True,'errors':[],'reports':self.fixture.original,'observations_hash':'a'*64}

    def test_original_failure_is_never_replaced_by_good_coverage(self):
        self.report.update(valid=False,errors=['existing independent check failed'])
        finalize(self.current,self.report)
        self.assertFalse(self.report['valid'])
        self.assertIn('existing independent check failed',self.report['errors'])
        self.assertEqual(self.report['behavior_coverage']['blocking'],[])

    def test_missing_capture_blocks_finalization_and_produces_no_success_receipt(self):
        self.report['reports']['mapping'].pop('behavior')
        finalize(self.current,self.report)
        self.assertFalse(self.report['valid'])
        self.assertNotIn('native_runtime',self.report['behavior_receipts'])

    def test_current_native_evidence_expires_on_source_change(self):
        finalize(self.current,self.report)
        self.assertTrue(previous_evidence(self.report,self.current)['native_runtime']['current'])
        self.current['files']['application.py']='two'
        self.assertFalse(previous_evidence(self.report,self.current)['native_runtime']['current'])

    def test_coordinator_review_rejects_changed_behavior_without_per_record_request(self):
        before=deepcopy(self.current)
        self.current['behavior']['actions'][0]['completion']['meaning']='Return early'
        before['acceptance']={'checks':[]}
        self.current['acceptance']={'checks':[]}
        changes={'unmapped_changed_symbols':[]}
        review={'candidate_id':'candidate','decisions':{k:{'action':'unchanged','reason':'Native source unchanged'}
            for k in ('business','state_machine','abstraction','probes')}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'review.json').write_text(json.dumps(review),encoding='utf-8')
            errors=review_errors(path,before,self.current,changes)
        self.assertIn('behavior_meaning_change_unreviewed',{e.get('code') for e in errors if isinstance(e,dict)})

    def test_existing_recall_persists_behavior_inventory_without_starting_an_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cfg={'model':'project.json','acceptance':'acceptance.json','observations_command':['python','test.py']}
            result=recall(root,cfg,self.current,self.current)
            saved=json.loads((root/'.stategraph/iteration-recall.json').read_text())
            self.assertEqual(result['behavior'],saved['behavior'])
            self.assertEqual(saved['behavior']['models'],['state-model:grant','state-model:archive'])
            self.assertEqual(saved['verification'],'not_run')


if __name__=='__main__':
    unittest.main()
