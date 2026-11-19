"""Evidence freshness follows meaning and native inputs, independently of IDs."""
from copy import deepcopy
import unittest

from test_behavior_contract import fixture
from bo_observer.behavior.dependencies import dependency_index, impact
from bo_observer.behavior.evidence import issue, applicability
from bo_observer.concepts.common import digest


def snapshot():
    contract, discovery = fixture()
    return {'behavior': contract, 'behavior_discovery': discovery,
            'analysis_profiles': [], 'model': {'nodes': [], 'edges': []},
            'structure': {'symbols': {'app.py:share': {'kind':'function','ast_hash':'one'}},
                          'edges':[], 'errors':[]},
            'source_inventory': {'files': {'app.py': {}}, 'scope_inputs':{}},
            'files': {'app.py':'source-one'}, 'tools':{'adapter.py':'adapter-one'},
            'verification_contract':{}, 'acceptance':{'checks':[]}}


class BehaviorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.before = snapshot()

    def receipt(self, subject='design_model', roots=None):
        return issue(self.before, subject, roots or ['action/grant-share'],
                     outcome='pass', artifacts={'result':'a'*64},
                     tool_identity={'compiler':'one','engine':'sha256:one'})

    def test_display_locale_and_layout_do_not_change_meaning(self):
        after=deepcopy(self.before)
        after['behavior_discovery']['state_models'][0]['label']='授权'
        after['model']['nodes']=[{'id':'display','label':'Shared','position':[5,9]}]
        # Physical model additions are native changes, but do not change a design.
        result=applicability(self.receipt(),after,tool_identity={'compiler':'one','engine':'sha256:one'})
        self.assertTrue(result['current'],result)

    def test_source_refactor_invalidates_native_not_design(self):
        after=deepcopy(self.before)
        after['files']['app.py']='source-two'
        for subject,expected in [('design_model',True),('native_mapping',False),('native_runtime',False)]:
            result=applicability(self.receipt(subject),after,tool_identity={'compiler':'one','engine':'sha256:one'})
            self.assertEqual(result['current'],expected,result)

    def test_adapter_changes_invalidate_native_and_compiler_changes_invalidate_analysis(self):
        after=deepcopy(self.before)
        after['tools']['adapter.py']='adapter-two'
        self.assertFalse(applicability(self.receipt('native_runtime'),after,tool_identity={'compiler':'one','engine':'sha256:one'})['current'])
        self.assertFalse(applicability(self.receipt(),self.before,tool_identity={'compiler':'two','engine':'sha256:one'})['current'])

    def test_same_id_changed_action_requires_new_evidence(self):
        after=deepcopy(self.before)
        after['behavior']['actions'][0]['completion']['meaning']='A different durable effect'
        result=applicability(self.receipt(),after,tool_identity={'compiler':'one','engine':'sha256:one'})
        self.assertFalse(result['current'])
        self.assertIn('action/grant-share',result['changed'])

    def test_unchanged_independent_model_retains_its_scoped_design_evidence(self):
        receipt=self.receipt(roots=['concept/state-model:archive'])
        after=deepcopy(self.before)
        after['behavior']['actions'][0]['completion']['meaning']='Changed grant completion'
        self.assertTrue(applicability(receipt,after,tool_identity={'compiler':'one','engine':'sha256:one'})['current'])

    def test_shared_rule_change_reaches_all_consumers_through_typed_dependencies(self):
        after=deepcopy(self.before)
        node=next(n for n in after['behavior_discovery']['policy']['nodes'] if n['id']=='is_owner')
        node['arguments']={'left':'owner','right':'actor'}
        result=impact(self.before,after)
        self.assertIn('concept/policy-operation:manage',result['affected'])
        self.assertIn('concept/share',result['affected'])
        self.assertIn('concept/revoke',result['affected'])
        self.assertNotIn('concept/policy-operation:read',result['affected'])
        self.assertIn('action/grant-share',result['affected'])

    def test_profile_bounds_and_property_changes_are_dependencies(self):
        self.before['analysis_profiles']=[{'id':'small','model_refs':['state-model:grant'],
            'property_refs':['archive-unchanged'],'bounds':{'count':{'max':2}}}]
        receipt=self.receipt(roots=['profile/small'])
        after=deepcopy(self.before)
        after['analysis_profiles'][0]['bounds']['count']['max']=3
        self.assertFalse(applicability(receipt,after,tool_identity={'compiler':'one','engine':'sha256:one'})['current'])
        after=deepcopy(self.before)
        after['behavior']['properties'][0]['expression']['op']='ne'
        self.assertFalse(applicability(receipt,after,tool_identity={'compiler':'one','engine':'sha256:one'})['current'])

    def test_removed_dependencies_cannot_be_hidden_by_resigning_receipt(self):
        receipt=self.receipt()
        receipt['dependencies'].pop(next(k for k in receipt['dependencies'] if k!='action/grant-share'))
        receipt['fingerprint']=digest({k:v for k,v in receipt.items() if k!='fingerprint'})
        result=applicability(receipt,self.before,tool_identity={'compiler':'one','engine':'sha256:one'})
        self.assertFalse(result['current'])
        self.assertEqual(result['reason'],'dependency_set_changed')

    def test_missing_root_and_unknown_receipt_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown dependency'):
            self.receipt(roots=['action/missing'])
        receipt=self.receipt()
        receipt['approve_everything']=True
        self.assertFalse(applicability(receipt,self.before)['current'])

    def test_explicit_error_or_incomplete_result_never_becomes_a_pass(self):
        for outcome in ('error','incomplete','unsupported','fail'):
            receipt=issue(self.before,'design_model',['action/grant-share'],outcome=outcome,artifacts={})
            result=applicability(receipt,self.before)
            self.assertTrue(result['current'])
            self.assertFalse(result['passed'])

    def test_payload_keys_named_label_are_preserved(self):
        after=deepcopy(self.before)
        # Unknown domain payloads are still fingerprinted exactly; semantic validation
        # is a preceding gate and this index never silently drops business values.
        self.before['behavior']['domains'][0]['values']=[{'label':'first'}]
        after['behavior']['domains'][0]['values']=[{'label':'second'}]
        self.assertNotEqual(dependency_index(self.before)['domain/status']['hash'],
                            dependency_index(after)['domain/status']['hash'])

    def test_native_receipt_survives_display_only_changes_to_existing_identities(self):
        self.before['model'].update(nodes=[{'id':'share','label':'Share','type':'business'}],
            edges=[{'id':'next','from':'share','to':'read','label':'Continue'}])
        after=deepcopy(self.before)
        after['model']['nodes'][0]['label']='共享'
        after['model']['edges'][0]['label']='继续'
        after['model']['nodes'][0]['presentation']={'color':'blue','position':[5,9]}
        for subject in ('native_mapping','native_runtime'):
            receipt=self.receipt(subject)
            self.assertTrue(applicability(receipt,after,tool_identity=receipt['tool_identity'])['current'])

    def test_bad_roots_and_artifacts_fail_without_a_partial_receipt(self):
        for roots in (None,[],['a',None],['a','a'],{'a':1}):
            with self.subTest(roots=roots), self.assertRaises(ValueError):
                issue(self.before,'design_model',roots,outcome='pass',artifacts={'result':'a'*64})
        receipt=self.receipt()
        receipt['artifacts']['result']='missing'
        receipt['fingerprint']=digest({k:v for k,v in receipt.items() if k!='fingerprint'})
        self.assertFalse(applicability(receipt,self.before)['current'])

    def test_native_machine_labels_do_not_change_state_values_or_receipt(self):
        self.before['model']['machines']={'grant':{'values':['active','inactive'],
            'labels':{'active':'Shared','inactive':'Unshared'},'transitions':[]}}
        after=deepcopy(self.before)
        after['model']['machines']['grant']['labels']['active']='已共享'
        receipt=self.receipt('native_runtime')
        self.assertTrue(applicability(receipt,after,tool_identity=receipt['tool_identity'])['current'])
        after['model']['machines']['grant']['values'].append('expired')
        self.assertFalse(applicability(receipt,after,tool_identity=receipt['tool_identity'])['current'])


if __name__=='__main__':
    unittest.main()
