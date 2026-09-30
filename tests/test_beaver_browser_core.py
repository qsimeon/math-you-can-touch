"""Bounded independent Python/Bun verification and headless offline UI checks.

No research worker, downloads, external network, output artifacts or screenshots.
"""
import json
from collections import Counter
import subprocess
import unittest
from pathlib import Path

from busybeaver.core import enumerate_tables, simulate_dict, simulate_set

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'site' / 'beaver-core.js'
PAGE = (ROOT / 'site' / 'beaver.html').as_uri()


def bun_core(tables):
    script = """const core=require(process.argv[1]);let text='';
process.stdin.on('data',part=>text+=part);
process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(text).map(table=>core.simulate(table)))));"""
    result = subprocess.run(['bun', '-e', script, str(CORE)], input=json.dumps(tables),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=90, check=True)
    return json.loads(result.stdout)


class BeaverCoreTests(unittest.TestCase):
    def test_all_20736_tables_agree_with_two_python_implementations(self):
        tables = list(enumerate_tables())
        self.assertEqual(20736, len(tables))
        browser_results = bun_core(tables)
        self.assertEqual(len(tables), len(browser_results))
        statuses = Counter()
        for index, (table, browser) in enumerate(zip(tables, browser_results)):
            expected = simulate_set(table, step_limit=100)
            self.assertEqual(expected, simulate_dict(table, step_limit=100), f'Python disagreement at {index}')
            self.assertEqual(expected, browser, f'JS disagreement at {index}: {table}')
            statuses[browser['status']] += 1
        self.assertEqual({'HALTED': 9784, 'NONHALTING_BY_TRANSLATION_CYCLE': 5040, 'UNKNOWN_AT_LIMIT': 5912}, statuses)

    def test_step_level_state_and_repeat_witness(self):
        script = """const C=require(process.argv[1]);
const {halt,cycle,unknown}=C.PRESETS;
let old=C.initial(), next=C.advance(halt.table,old);
if(old.step!==0||old.ones.length!==0||old.seen['A|'][0]!==0)throw Error('mutated previous frame');
if(next.step!==1||next.head!==1||next.state!=='B'||next.ones[0]!==0||JSON.stringify(next.action)!==JSON.stringify({from:'A',read:0,write:1,move:'R',next:'B',at:0,head:1}))throw Error('first action mismatch');
if(C.simulate(halt.table).steps!==6||C.simulate(halt.table).ones!==4)throw Error('halting mismatch');
if(C.simulate(cycle.table).repeat.shift!==1||C.simulate(cycle.table).repeat.period!==1)throw Error('repeat mismatch');
if(!unknown.table.flat().some(rule=>rule[2]==='H'))throw Error('cutoff preset needs a halt rule');
if(C.simulate(unknown.table).status!=='UNKNOWN_AT_LIMIT')throw Error('cutoff conflated with proof');
for(const value of [0,-1,101,1.1]){try{C.advance(halt.table,old,value);throw Error('invalid bound accepted')}catch(e){if(e.message==='invalid bound accepted')throw e;}}
console.log('step contract passed');"""
        result = subprocess.run(['bun', '-e', script, str(CORE)], capture_output=True,
                                text=True, timeout=15, check=True)
        self.assertIn('step contract passed', result.stdout)


class BeaverPageTests(unittest.TestCase):
    def test_controls_presets_flat_tape_and_local_assets(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 390, 'height': 850}, reduced_motion='reduce')
            page.clock.install()
            errors, requests = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            page.goto(PAGE)
            self.assertEqual(4, page.locator('#ruleRows tr').count())
            self.assertEqual(0, page.locator('canvas').count())
            self.assertEqual(12, page.locator('#ruleRows select').count())
            self.assertEqual(9, page.locator('#tape .tape-cell').count())
            self.assertIn('BB(6)', page.locator('.scope').inner_text())
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
            self.assertEqual('static', page.locator('.scope').evaluate('(e) => getComputedStyle(e).position'))
            self.assertEqual('static', page.locator('#viewNote').evaluate('(e) => getComputedStyle(e).position'))
            self.assertIn('nine squares of an infinite tape', page.locator('#viewNote').inner_text())
            for width in (320, 390, 640, 740):
                page.set_viewport_size({'width': width, 'height': 850})
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                self.assertEqual(page.locator('#tape .tape-cell').count(), 9)
            page.set_viewport_size({'width': 390, 'height': 850})
            page.locator('[data-predict="HALTED"]').click()
            page.locator('#step').click()
            self.assertEqual(['Read 0', 'Write 1', '← Move left', 'Use state A'], page.locator('#actionStrip span').all_inner_texts())
            self.assertEqual(1, page.locator('.tape-cell.just-written').count())
            self.assertIn('read 0 at square 0', page.locator('#narration').inner_text())
            self.assertIn('wrote 1, moved right to square 1', page.locator('#narration').inner_text())
            self.assertIn('state B', page.locator('#stepReadout').inner_text())
            self.assertIn('STATE B', page.locator('#robotBadge').inner_text())
            self.assertTrue(page.locator('[data-predict="HALTED"]').is_disabled())
            page.locator('#back').click()
            self.assertFalse(page.locator('[data-predict="HALTED"]').is_disabled())
            self.assertIn('Step 0', page.locator('#stepReadout').inner_text())
            page.locator('#run').click()
            page.clock.run_for(3000)
            self.assertIn('Step 6', page.locator('#stepReadout').inner_text())
            self.assertIn('Halted at step 6', page.locator('#outcome').inner_text())
            self.assertIn('has stopped', page.locator('#actionStrip').inner_text())
            self.assertIn('prediction matched', page.locator('#predictionFeedback').inner_text())
            self.assertTrue(page.locator('#step').is_disabled())
            page.locator('#back').click()
            self.assertFalse(page.locator('#step').is_disabled())
            page.locator('#reset').click()
            page.locator('#preset').select_option('cycle')
            page.locator('#step').click()
            outcome = page.locator('#outcome').inner_text()
            self.assertIn('Proved repeat: steps 0 and 1', outcome)
            self.assertIn('will not halt', page.locator('#actionStrip').inner_text())
            self.assertIn('same complete set of 1s', outcome)
            self.assertIn('identical rules apply after translation', outcome)
            self.assertTrue(page.locator('#cycleCompare').is_visible())
            self.assertIn('Step 0 · state A · head 0', page.locator('#previousLabel').inner_text())
            self.assertIn('Step 1 · state A · head 1', page.locator('#currentLabel').inner_text())
            self.assertEqual(9, page.locator('#previousTape span').count())
            self.assertEqual(page.locator('#previousTape').inner_text(), page.locator('#currentTape').inner_text())
            self.assertIn('complete set of marked offsets', page.locator('#compareDetail').inner_text())
            self.assertIn('Both entire tapes are blank; no square is marked.', page.locator('#compareDetail').inner_text())
            self.assertNotIn('marked cells outside', page.locator('#compareDetail').inner_text())
            page.locator('#preset').select_option('unknown')
            page.locator('[data-predict="UNKNOWN_AT_LIMIT"]').click()
            page.locator('#run').click()
            page.clock.run_for(50000)
            self.assertIn('Step 100', page.locator('#stepReadout').inner_text())
            self.assertIn('Unresolved by this checker at step 100', page.locator('#outcome').inner_text())
            self.assertIn('known two-state result', page.locator('#actionStrip').inner_text())
            self.assertIn('known two-state theorem shows this robot never halts', page.locator('#outcome').inner_text())
            self.assertIn('The checker does not use that theorem', page.locator('.explanation').inner_text())
            self.assertIn('100 marked squares', page.locator('#tapeSummary').inner_text())
            page.locator('#ruleRows tr').first.locator('select').first.select_option('0')
            self.assertIn('Step 0', page.locator('#stepReadout').inner_text())
            self.assertIn('0 marked squares', page.locator('#tapeSummary').inner_text())
            self.assertEqual('custom', page.locator('#preset').input_value())
            self.assertEqual('false', page.locator('[data-predict="UNKNOWN_AT_LIMIT"]').get_attribute('aria-pressed'))
            self.assertFalse(errors, errors)
            self.assertTrue(all(url.startswith('file://') or url.startswith('data:') for url in requests), requests)
            page.close()
            browser.close()
