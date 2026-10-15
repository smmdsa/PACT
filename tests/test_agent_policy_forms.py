"""Static checks for the explicitly registered counter-four alternative forms."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.agent_candidate_policy import audit_candidate
from pact.compact import loads

ROOT=Path(__file__).resolve().parents[1]
PROFILE='counter-four-forms/0.2'
EXTENSIONS={'pact':'pact','python':'py','javascript':'mjs','c':'c'}


class PolicyFormsTests(unittest.TestCase):
    def source(self,language):
        path=ROOT/'benchmarks/agent_trials/policy_forms/0.2'/('counter.unrolled.'+EXTENSIONS[language])
        self.assertTrue(path.exists(),'Registered unrolled fixture is missing')
        return path.read_bytes()

    def test_unrolled_forms_require_the_explicit_new_profile(self):
        for language in EXTENSIONS:
            candidate=self.source(language)
            self.assertFalse(audit_candidate(candidate,language)['policy_pass'])
            result=audit_candidate(candidate,language,profile=PROFILE)
            self.assertTrue(result['policy_pass'],result)
            self.assertEqual(result['accepted_form'],'unrolled')
            self.assertEqual(result['profile'],PROFILE)
            self.assertEqual(len(result['contract_sha256']),64)
            self.assertFalse(result['runtime_executed'])
            self.assertIsNone(result['candidate_pass'])

    def test_ir_and_ast_formatting_remain_distinct_from_byte_policies(self):
        pact=loads(self.source('pact').decode())
        self.assertTrue(audit_candidate(json.dumps(pact).encode(),'pact',profile=PROFILE)['policy_pass'])
        self.assertTrue(audit_candidate(b'# comment\n'+self.source('python'),'python',profile=PROFILE)['policy_pass'])
        for language in ('c','javascript'):
            source=self.source(language)
            self.assertTrue(audit_candidate(source.replace(b'\n',b'\r\n'),language,profile=PROFILE)['policy_pass'])
            self.assertFalse(audit_candidate(source+b'\n// comment\n',language,profile=PROFILE)['policy_pass'])

    def test_unapproved_changes_still_reject_in_every_language(self):
        for language in EXTENSIONS:
            source=self.source(language)
            for changed in (source.replace(b'2147483646',b'0',1),b'broken',b'\xff',b'x'*1048577,None):
                self.assertFalse(audit_candidate(changed,language,profile=PROFILE)['policy_pass'])
        document=loads(self.source('pact').decode())
        for change in ('identity','version','tests','effect'):
            changed=copy.deepcopy(document)
            if change=='identity':changed['tests'][0]['id']='renamed'
            if change=='version':changed['format']='pact.module/0.2.0'
            if change=='tests':changed['tests']=[]
            if change=='effect':changed['functions'][0]['writes']=[]
            self.assertFalse(audit_candidate(json.dumps(changed).encode(),'pact',profile=PROFILE)['policy_pass'])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):audit_candidate(b'irrelevant','pact',profile='unknown')

    def test_contract_tampering_rejects_before_candidate_check(self):
        from unittest.mock import patch
        import benchmarks.agent_candidate_policy as policy
        original=policy.snapshot
        def changed(path):
            value=original(path)
            return value+b' ' if path==policy.FORMS_CONTRACT else value
        with patch.object(policy,'snapshot',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'contract identity'):
                audit_candidate(self.source('pact'),'pact',profile=PROFILE)

    def test_canonical_forms_are_registered_in_the_new_profile(self):
        from benchmarks.agent_candidate_policy import expected_document
        from pact.compact import dumps
        for language,extension in EXTENSIONS.items():
            baseline=(ROOT/'benchmarks/agent_trials'/('counter.'+extension)).read_bytes()
            candidate=(dumps(expected_document()).encode() if language=='pact' else
                       baseline.replace(b'range(3)',b'range(4)') if language=='python' else
                       baseline.replace(b'i < 3',b'i < 4'))
            result=audit_candidate(candidate,language,profile=PROFILE)
            self.assertTrue(result['policy_pass'],result)
            self.assertEqual(result['accepted_form'],'canonical')

    def test_bounds_and_wrapping_edits_are_not_registered_forms(self):
        changes={'python':[(b'raise IndexError',b'raise ValueError'),(b'amount + 2**31',b'amount + 2**30')],
                 'javascript':[(b'RangeError',b'Error'),(b'amount) | 0',b'amount) >>> 0')],
                 'c':[(b'return 0;',b'return 1;'),(b'4294967296LL',b'4294967295LL')]}
        for language,replacements in changes.items():
            source=self.source(language)
            for old,new in replacements:
                self.assertIn(old,source)
                self.assertFalse(audit_candidate(source.replace(old,new),language,profile=PROFILE)['policy_pass'])
