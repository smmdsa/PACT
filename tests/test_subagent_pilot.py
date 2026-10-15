import copy
import importlib
from pathlib import Path
import unittest


class SubagentPilotTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('tools.check_subagent_pilot')

    def test_archived_trials_keep_missing_usage_and_excluded_attempt(self):
        manifest=self.module().load_pilot()
        self.assertEqual(len(manifest['trials']),8)
        self.assertEqual(len(manifest['excluded_attempts']),1)
        self.assertEqual({row['model_alias'] for row in manifest['trials']},{'gpt-6.1-sol','gpt-6-astra'})
        for row in manifest['trials']:
            self.assertIsNone(row['provider_usage'])
            self.assertIsNone(row['immutable_model_version'])
        self.assertFalse(manifest['formal_benchmark'])

    def test_hash_mismatch_rejects_before_candidate_execution(self):
        module=self.module();manifest=module.load_pilot()
        broken=copy.deepcopy(manifest)
        broken['trials'][0]['candidate_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):
            module.validate_pilot(broken)
        broken=copy.deepcopy(manifest)
        broken['excluded_attempts'][0]['response_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):
            module.validate_pilot(broken)

    def test_source_extraction_is_only_one_final_newline(self):
        module=self.module();manifest=module.load_pilot()
        for row in manifest['trials']:
            response=(module.ROOT/row['response_path']).read_bytes()
            candidate=(module.ROOT/row['candidate_path']).read_bytes()
            self.assertEqual(candidate,response+b'\n')
