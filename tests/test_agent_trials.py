import copy
import hashlib
import importlib
import io
import json
import unittest
from contextlib import redirect_stdout


class AgentTrialsTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('benchmarks.agent_trials')
        except ImportError:
            self.fail('Provider-independent trial protocol is missing')

    def record(self, passed=True):
        m = self.module()
        pack = m.prepare('python', 17)
        return {'task':'counter-four', 'language':'python', 'model':'provider/model',
                'model_version':'pinned-version', 'attempt':1, 'pass':passed,
                'latency_ms':123.5, 'input_tokens':100, 'output_tokens':25,
                'provider_usage':{'input_tokens':100, 'output_tokens':25},
                'settings':{'temperature':0}, 'seed':23,
                'budget':{'max_output_tokens':1000, 'max_latency_ms':60000},
                'order_index':next(x['order_index'] for x in pack['trial_order'] if x['language']=='python' and x['attempt']==1),
                'trial_plan_seed':17, 'prompt_sha256':pack['prompt']['sha256'],
                'context_sha256':pack['context']['sha256'], 'candidate_sha256':'a'*64,
                'verifier':{'command':'external-isolated-verifier candidate',
                            'revision':'verifier-v1', 'log_sha256':'b'*64}}

    def test_common_prompt_exact_bytes_and_frozen_independent_oracle(self):
        m = self.module()
        packs = [m.prepare(language, 17) for language in m.LANGUAGES]
        self.assertEqual(len({p['prompt']['text'] for p in packs}), 1)
        self.assertEqual(len({p['context']['sha256'] for p in packs}), 4)
        self.assertEqual(len(packs[0]['trial_order']), 20)
        self.assertEqual(packs[0]['trial_order'], m.prepare('python',17)['trial_order'])
        oracle = packs[0]['oracle']
        state = [2147483646, -2147483647]
        for case in oracle['cases']:
            index, amount = case['args']
            valid = 0 <= index < 2
            if valid:
                state[index] = (state[index] + 4*amount + 2**31) % 2**32 - 2**31
            self.assertEqual(case['status'], 'ok' if valid else 'bounds')
            self.assertEqual(case['counter'], state)
        self.assertFalse(packs[0]['automated_grading_implemented'])

    def test_records_external_provenance_and_retains_failures(self):
        m = self.module()
        record = self.record()
        self.assertEqual(m.validate_records([record]), [record])
        failed = copy.deepcopy(record)
        failed['attempt'] = 2
        failed['order_index'] = next(x['order_index'] for x in m.prepare('python',17)['trial_order'] if x['language']=='python' and x['attempt']==2)
        failed['pass'] = False
        summary = m.summarize([record, failed])['groups'][0]
        self.assertEqual(summary['success_rate'], .5)
        self.assertEqual(summary['total_tokens'], 250)
        self.assertEqual(summary['tokens_per_successful_task'], 250)
        self.assertEqual(summary['failed_trials'], 1)
        failed['attempt'] = 1
        failed['order_index'] = record['order_index']
        empty = m.summarize([failed])['groups'][0]
        self.assertIsNone(empty['tokens_per_successful_task'])
        self.assertFalse(empty['complete_five_trial_group'])

    def test_rejects_invalid_and_duplicate_external_measurements(self):
        m = self.module()
        base = self.record()
        changes = [('language','rust'), ('task','unknown'), ('attempt',True),
                   ('attempt',6), ('latency_ms',-1), ('input_tokens',True),
                   ('output_tokens',-1), ('pass',1), ('latency_ms',float('nan')),
                   ('context_sha256','0'*64), ('order_index',99), ('seed',False),
                   ('settings',{'temperature':float('inf')})]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                row=copy.deepcopy(base); row[key]=value
                with self.assertRaises(ValueError): m.validate_records([row])
        for key in base:
            with self.subTest(missing=key):
                row=copy.deepcopy(base); del row[key]
                with self.assertRaises(ValueError): m.validate_records([row])
        for mutate in (lambda r:r.update(extra='x'), lambda r:r['verifier'].update(log_sha256=''),
                       lambda r:r['provider_usage'].update(input_tokens=99)):
            row=copy.deepcopy(base); mutate(row)
            with self.assertRaises(ValueError): m.validate_records([row])
        with self.assertRaises(ValueError): m.validate_records([base,base])

    def test_prepare_cli_emits_material_without_trial_results(self):
        m=self.module(); output=io.StringIO()
        with redirect_stdout(output): self.assertEqual(m.main(['prepare','--language','c','--plan-seed','17']),0)
        pack=json.loads(output.getvalue())
        self.assertEqual(pack['language'],'c')
        self.assertNotIn('results',pack)
        self.assertEqual(pack['prompt']['sha256'],hashlib.sha256(pack['prompt']['text'].encode()).hexdigest())

    def test_success_cannot_exceed_declared_budgets_but_failures_retain_costs(self):
        m = self.module()
        for field, limit in [('output_tokens', 'max_output_tokens'), ('latency_ms', 'max_latency_ms')]:
            with self.subTest(field=field):
                row = self.record()
                row[field] = row['budget'][limit] + 1
                if field == 'output_tokens': row['provider_usage'][field] = row[field]
                with self.assertRaisesRegex(ValueError, 'budget'):
                    m.validate_records([row])
                row['pass'] = False
                summary = m.summarize([row])['groups'][0]
                self.assertEqual(summary['budget_exceeded_trials'], 1)
                self.assertEqual(summary['total_tokens'], row['input_tokens'] + row['output_tokens'])
                self.assertEqual(summary['total_latency_ms'], row['latency_ms'])
        row = self.record()
        row['output_tokens'] = row['budget']['max_output_tokens']
        row['provider_usage']['output_tokens'] = row['output_tokens']
        row['latency_ms'] = row['budget']['max_latency_ms']
        self.assertEqual(m.summarize([row])['groups'][0].get('budget_exceeded_trials'), 0)

    def different_language(self, row, language='c'):
        result = copy.deepcopy(row)
        result['language'] = language
        pack = self.module().prepare(language, result['trial_plan_seed'])
        result['context_sha256'] = pack['context']['sha256']
        result['order_index'] = next(x['order_index'] for x in pack['trial_order']
                                     if x['language'] == language and x['attempt'] == result['attempt'])
        return result

    def test_summary_requires_common_configuration_and_paired_seeds_across_languages(self):
        m = self.module()
        first = self.record()
        other = self.different_language(first)
        groups = m.summarize([first, other])['groups']
        for group in groups:
            for field in ('settings', 'budget', 'trial_plan_seed'):
                self.assertEqual(group.get(field), first[field])
        for field, value in [('settings', {'temperature': 1}),
                             ('budget', {'max_output_tokens': 999, 'max_latency_ms': 60000}),
                             ('trial_plan_seed', 18), ('seed', 24)]:
            with self.subTest(field=field):
                row = copy.deepcopy(other)
                row[field] = value
                if field == 'trial_plan_seed':
                    row = self.different_language(row)
                with self.assertRaises(ValueError): m.summarize([first, row])
        # Generation seeds may differ between attempts, but must pair across languages.
        second = copy.deepcopy(first)
        second['attempt'] = 2
        second['seed'] = 24
        second = self.different_language(second, 'python')
        self.assertEqual(len(m.summarize([first, second, self.different_language(second)])['groups']), 2)
