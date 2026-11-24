"""Acceptance workflow configuration regression tests."""
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    """Load workflow preserving the on key."""
    return yaml.load((ROOT / '.github/workflows' / name).read_text(
        encoding='utf-8'), Loader=yaml.BaseLoader)


class WorkflowConfigurationTests(unittest.TestCase):
    """Check runtime context placement and evidence retention."""

    def test_acceptance(self):
        """Verify triggers, runtime paths and independent jobs."""
        workflow = load('scanner-acceptance.yml')
        job = workflow['jobs']['real-scanners']
        self.assertIn('main', workflow['on']['push']['branches'])
        self.assertIn('feature/**', workflow['on']['push']['branches'])
        self.assertIn('workflow_dispatch', workflow['on'])
        self.assertEqual(job['strategy']['fail-fast'], 'false')
        for value in job.get('env', {}).values():
            for context in ('runner.', 'steps.', 'job.', 'env.'):
                self.assertNotIn(context, str(value))
        steps = {step.get('name', step.get('uses')): step
                 for step in job['steps']}
        for name in ('Stage acceptance evidence',
                     'Display sanitized platform results'):
            step = steps[name]
            self.assertEqual(step['if'], 'always()')
            self.assertIn('runner.temp', step['env']['QG_EVIDENCE_DIR'])
        upload = steps['actions/upload-artifact@v4']
        self.assertEqual(upload['if'], 'always()')
        self.assertEqual(upload['with']['if-no-files-found'], 'error')
        self.assertIn('runner.temp', upload['with']['path'])

    def test_actionlint(self):
        """Require semantic validation in CI."""
        job = load('framework-tests.yml')['jobs']['workflow-validation']
        commands = '\n'.join(step.get('run', '') for step in job['steps'])
        self.assertIn('actionlint@v1.7.7', commands)
        self.assertIn('bin/actionlint', commands)
