"""Network-free regression tests; CI separately checks the real scholarly import."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / 'bin/update_scholar_citations.py'


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        Path('_data').mkdir()
        Path('_data/socials.yml').write_text('scholar_userid: test-author\n')
        self.output = Path('_data/citations.yml')
        self.client = Mock()
        self.client.fill.return_value = {'publications': [
            {'author_pub_id': 'test-author:paper1', 'bib': {'title': 'Paper', 'pub_year': '2024'}, 'num_citations': 7}
        ]}
        module = types.ModuleType('scholarly')
        module.scholarly = self.client
        with patch.dict(sys.modules, scholarly=module):
            spec = importlib.util.spec_from_file_location('citation_updater', SCRIPT)
            self.updater = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.updater)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def seed(self, date='2000-01-01', papers=None):
        self.output.write_text(yaml.safe_dump({'metadata': {'last_updated': date}, 'papers': papers or {}}))

    def test_missing_output_created(self):
        self.updater.get_scholar_citations()
        data = yaml.safe_load(self.output.read_text())
        self.assertEqual(data['papers']['test-author:paper1']['citations'], 7)

    def test_empty_same_day_data_is_refetched(self):
        self.seed(datetime.now().strftime('%Y-%m-%d'))
        self.updater.get_scholar_citations()
        self.client.fill.assert_called_once()
        self.assertTrue(yaml.safe_load(self.output.read_text())['papers'])

    def test_valid_same_day_data_is_reused(self):
        self.seed(datetime.now().strftime('%Y-%m-%d'), {'old': {'citations': 2}})
        self.updater.get_scholar_citations()
        self.client.fill.assert_not_called()

    def test_empty_response_preserves_file(self):
        self.seed(papers={'old': {'citations': 2}})
        before = self.output.read_bytes()
        self.client.fill.return_value = {'publications': []}
        with self.assertRaises(SystemExit):
            self.updater.get_scholar_citations()
        self.assertEqual(before, self.output.read_bytes())

    def test_unusable_ids_preserve_file(self):
        self.seed(papers={'old': {'citations': 2}})
        before = self.output.read_bytes()
        self.client.fill.return_value = {'publications': [{'bib': {'title': 'No ID'}}]}
        with self.assertRaises(SystemExit):
            self.updater.get_scholar_citations()
        self.assertEqual(before, self.output.read_bytes())

    def test_network_failure_preserves_file(self):
        self.seed(papers={'old': {'citations': 2}})
        before = self.output.read_bytes()
        self.client.search_author_id.side_effect = RuntimeError('Network failure')
        with self.assertRaises(SystemExit):
            self.updater.get_scholar_citations()
        self.assertEqual(before, self.output.read_bytes())

    def test_serialization_failure_preserves_file(self):
        self.seed(papers={'old': {'citations': 2}})
        before = self.output.read_bytes()
        with patch.object(self.updater.yaml, 'dump', side_effect=OSError('Disk full')):
            with self.assertRaises(SystemExit):
                self.updater.get_scholar_citations()
        self.assertEqual(before, self.output.read_bytes())
        self.assertEqual(sorted(p.name for p in Path('_data').iterdir()), ['citations.yml', 'socials.yml'])

    def test_unchanged_counts_refresh_success_date(self):
        self.updater.get_scholar_citations()
        data = yaml.safe_load(self.output.read_text())
        self.seed(papers=data['papers'])
        self.updater.get_scholar_citations()
        self.assertEqual(yaml.safe_load(self.output.read_text())['metadata']['last_updated'], datetime.now().strftime('%Y-%m-%d'))

    def test_corrupt_yaml_is_replaced_after_success(self):
        self.output.write_text('bad: [')
        self.updater.get_scholar_citations()
        self.assertTrue(yaml.safe_load(self.output.read_text())['papers'])


if __name__ == '__main__':
    unittest.main()
