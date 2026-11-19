"""Semantic changes remain protected while source-only work stays with the agent."""
from copy import deepcopy
import unittest

from test_behavior_evidence import snapshot
from bo_observer.behavior.iteration import protected_errors, recall, meaning_changes


class BehaviorIterationTests(unittest.TestCase):
    def setUp(self):
        self.before=snapshot()
        self.before['intent']={'requirements':[{'id':'R1','status':'confirmed'}]}
        self.after=deepcopy(self.before)

    def test_removing_the_contract_is_not_a_legacy_downgrade(self):
        self.after['behavior']=None
        self.assertEqual(protected_errors(self.before,self.after,{})[0]['code'],'behavior_contract_removed')

    def test_same_id_does_not_approve_changed_completion(self):
        self.after['behavior']['actions'][0]['completion']['meaning']='Return before committing'
        self.assertEqual(protected_errors(self.before,self.after,{})[0]['code'],'behavior_meaning_change_unreviewed')
        self.assertTrue(protected_errors(self.before,self.after,{'requirement_changes':{'R1':'I changed it'}}))
        self.before['requested_requirements']=['R1']
        review={'requirement_changes':{'R1':'Confirmed completion change'}}
        self.assertTrue(protected_errors(self.before,self.after,review))
        review['behavior_changes']={'actions/grant-share':['R1']}
        self.assertEqual(protected_errors(self.before,self.after,review),[])
        self.after['behavior']['properties']=[]
        result=protected_errors(self.before,self.after,review)
        self.assertEqual(result[0]['changed'],['properties/archive-unchanged'])

    def test_source_change_rebinds_without_an_intent_question(self):
        self.after['files']['app.py']='two'
        result=recall(self.before,self.after)
        self.assertEqual(result['meaning_changes']['meaning'],[])
        self.assertIn('$native-source',result['impact']['changed'])
        self.assertFalse(result['integration']['automatic_host_hook'])

    def test_bound_change_is_analysis_work_not_new_business_policy(self):
        value={'id':'number','type':'integer','min':0,'max':2,'bound_origin':'analysis_bound','source_refs':['U1']}
        self.before['behavior']['domains'].append(value)
        self.after=deepcopy(self.before)
        self.after['behavior']['domains'][-1]['max']=3
        changes=meaning_changes(self.before,self.after)
        self.assertEqual(changes['meaning'],[])
        self.assertEqual(changes['analysis'],['domains/number'])

    def test_removing_or_weakening_a_property_requires_request_basis(self):
        self.after['behavior']['properties']=[]
        self.assertTrue(protected_errors(self.before,self.after,{}))

    def test_mandatory_profile_cannot_be_deleted_or_relaxed_by_sync(self):
        self.before['analysis_profiles']=[{'id':'p','required_for_acceptance':True,'bounds':{}}]
        self.assertEqual(protected_errors(self.before,self.after,{})[0]['code'],'required_analysis_changed')
        self.after['analysis_profiles']=[{'id':'p','required_for_acceptance':False,'bounds':{}}]
        self.assertEqual(protected_errors(self.before,self.after,{})[0]['code'],'required_analysis_changed')

    def test_scope_shrink_and_missing_bindings_remain_visible(self):
        result=recall(self.before,self.after)
        self.assertEqual(result['missing_bindings']['variables'],['archive-status','grant-status'])
        self.after['behavior']['scope']['model_refs'].remove('state-model:archive')
        self.assertIn('scope',meaning_changes(self.before,self.after)['meaning'])
        self.assertTrue(protected_errors(self.before,self.after,{}))


if __name__=='__main__':
    unittest.main()
