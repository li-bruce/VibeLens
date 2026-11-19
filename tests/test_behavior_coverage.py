"""Real captured values feed separate coverage, domain and business reports."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from test_native_behavior_runtime import fixture, run_native, BUILD, assess_runtime
from bo_observer.behavior.coverage import reports, key
from bo_observer.concepts.common import canonical_id
from bo_observer.behavior.evidence import issue


class BehaviorCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        contract,discovery,model,index,app=fixture(Path(self.temp.name))
        self.snapshot={'behavior':contract,'behavior_discovery':discovery,'model':model,
                       'structure':index,'analysis_profiles':[],
                       'verification_contract':{'probe_modes':['on','off','fault'],'test_commands':[['python','test.py']]},
                       'acceptance':{'checks':[{'id':'allowed','case':'share'},{'id':'denied','case':'error'}]}}
        self.payload={'build_id':BUILD,'runs':[run_native(model,app,True),run_native(model,app,False)]}
        self.native=assess_runtime(contract,discovery,model,self.payload,index=index,case_ids={'share','error'})
        self.assertTrue(self.native['valid'],self.native['errors'])
        self.original={'concepts':{'status':'passed','errors':[]},
            'mapping':{'status':'passed','errors':[],'behavior':self.native},
            'state_rules':{'status':'passed','errors':[]},
            'business':{'status':'passed','errors':[],'assertions':{'executed':6}},
            'project_checks':{'status':'passed','errors':[]}}

    def result(self):
        return reports(self.snapshot,self.original)

    def test_complete_real_capture_keeps_independent_categories_and_denominators(self):
        result=self.result()
        self.assertEqual(result['blocking'],[])
        self.assertEqual(result['categories']['business']['coverage'],{'required':6,'checked':6})
        self.assertEqual(result['categories']['state_rules']['coverage'],{'required':2,'checked':2})
        self.assertGreater(result['categories']['capture']['coverage']['required'],8)
        self.assertEqual(result['categories']['formal_analysis']['status'],'not_configured')

    def test_missing_runtime_is_pending_even_with_valid_bindings(self):
        self.original['mapping'].pop('behavior')
        result=self.result()
        self.assertEqual(result['categories']['mapping']['status'],'passed')
        self.assertEqual(result['categories']['capture']['status'],'pending')
        self.assertIn('capture',result['blocking'])

    def test_accurate_invalid_native_value_is_a_state_finding_not_mapping_failure(self):
        self.native['domain_findings']=[{'status':'outside_application_domain','actual':None,'binding':'variable:grant-status'}]
        result=self.result()['categories']
        self.assertEqual(result['mapping']['status'],'passed')
        self.assertEqual(result['capture']['status'],'passed')
        self.assertEqual(result['state_rules']['status'],'failed')
        self.assertIsNone(result['state_rules']['errors'][0]['actual'])

    def test_analysis_only_bound_does_not_reject_native_value(self):
        self.native['domain_findings']=[{'status':'outside_analysis_domain','actual':50}]
        self.assertEqual(self.result()['blocking'],[])

    def test_missing_case_and_second_model_read_cannot_hide_behind_one_good_route(self):
        self.native['values']=[v for v in self.native['values'] if v['id']!='variable:archive-status']
        result=self.result()['categories']['capture']
        self.assertEqual(result['status'],'pending')
        self.assertIn('variable/archive-status',result['missing'])

    def test_business_failure_is_independent_of_correct_observation(self):
        self.original['business'].update(status='failed',errors=['Permission read too early'])
        result=self.result()
        self.assertEqual(result['categories']['capture']['status'],'passed')
        self.assertEqual(result['blocking'],['business'])

    def test_mandatory_profile_needs_current_executed_evidence(self):
        profile={'id':'small','model_refs':['state-model:grant'],'property_refs':['archive-unchanged'],
                 'assumption_refs':[],'required_for_acceptance':True,'bounds':{}}
        self.snapshot['analysis_profiles']=[profile]
        self.assertIn('formal_analysis/small',self.result()['blocking'])
        receipt=issue(self.snapshot,'design_model',['profile/small'],outcome='pass',artifacts={'result':'a'*64})
        result=reports(self.snapshot,self.original,formal_results=[receipt])
        self.assertEqual(result['blocking'],[])
        self.snapshot['analysis_profiles'][0]['bounds']={'cap':2}
        self.assertIn('formal_analysis/small',reports(self.snapshot,self.original,formal_results=[receipt])['blocking'])

    def test_optional_profile_is_visible_without_blocking_native_work(self):
        self.snapshot['analysis_profiles']=[{'id':'optional','model_refs':['state-model:grant'],
            'property_refs':['archive-unchanged'],'required_for_acceptance':False}]
        result=self.result()
        self.assertEqual(result['blocking'],[])
        self.assertEqual(result['categories']['formal_analysis']['profiles']['optional']['status'],'pending')

    def test_current_failed_or_conflicting_analysis_cannot_be_hidden_by_an_old_pass(self):
        self.snapshot['analysis_profiles']=[{'id':'small','model_refs':['state-model:grant'],
            'property_refs':['archive-unchanged'],'required_for_acceptance':True}]
        failed=issue(self.snapshot,'design_model',['profile/small'],outcome='fail',artifacts={'result':'a'*64})
        passed=issue(self.snapshot,'design_model',['profile/small'],outcome='pass',artifacts={'result':'b'*64})
        for values in ([failed],[passed,failed]):
            result=reports(self.snapshot,self.original,formal_results=values)
            self.assertEqual(result['categories']['formal_analysis']['profiles']['small']['status'],'failed')
            self.assertIn('formal_analysis/small',result['blocking'])

    def test_no_contract_keeps_legacy_checks_in_the_original_coordinator(self):
        self.assertEqual(reports({},self.original),{'configured':False,'categories':{},'blocking':[]})

    def test_design_result_never_satisfies_implementation_subject(self):
        self.snapshot['analysis_profiles']=[{'id':'native','subject':'implementation_model',
            'model_refs':['state-model:grant'],'property_refs':['archive-unchanged'],
            'required_for_acceptance':True}]
        receipt=issue(self.snapshot,'design_model',['profile/native'],outcome='pass',artifacts={'result':'a'*64})
        result=reports(self.snapshot,self.original,formal_results=[receipt])
        self.assertEqual(result['categories']['formal_analysis']['profiles']['native']['status'],'unsupported')
        self.assertIn('formal_analysis/native',result['blocking'])

    def test_separator_characters_do_not_merge_distinct_obligations(self):
        self.assertNotEqual(key('value','variable:a/b','case'),key('value','variable:a','b/case'))
        self.assertNotEqual(canonical_id('parameter','a:b','c'),canonical_id('parameter','a','b:c'))


if __name__=='__main__':
    unittest.main()
