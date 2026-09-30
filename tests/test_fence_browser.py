"""Focused browser regressions for the exact interactive fence tabletop."""
import json
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'site' / 'data.js').read_text()[len('window.LEARNING_DATA = '):-2])


class FenceBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def page(self):
        page = self.browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
        self.errors = []
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto((ROOT / 'site/fences.html').as_uri())
        page.locator('#fenceSvg').wait_for()
        return page

    def assert_clean(self):
        self.assertEqual(self.errors, [])

    def test_intro_matches_warmup_and_offers_navigation_before_play(self):
        page = self.page()
        self.assertEqual(page.locator('#fenceList button').count(), 4)
        deck = page.locator('.page-head .deck').inner_text()
        self.assertIn('Start with four', deck)
        self.assertIn('Choose any fence', deck)
        self.assertIn('not a proof of the maximum', deck)
        nav = page.get_by_role('navigation', name='Explore the project')
        self.assertEqual(nav.get_by_role('link', name='Experiment story').get_attribute('href'), 'index.html')
        self.assertEqual(nav.get_by_role('link', name='Tape robot').get_attribute('href'), 'beaver.html')
        self.assertLess(nav.bounding_box()['y'], page.locator('#viewerShell').bounding_box()['y'])
        self.assert_clean()
        page.close()

    def test_motion_frame_renders_its_exact_geometry_and_frame_readout(self):
        page = self.page()
        self.assertEqual(page.locator('#fenceList button').count(), 4)
        self.assertEqual(page.locator('#tableTitle').inner_text(), '4 fences. A small warm-up.')
        self.assertIn('Live warm-up', page.locator('#recordReadout').inner_text())
        frame = DATA['kobon']['motion']['frames'][0]
        page.locator('#motionSlider').fill('0')
        self.assertEqual(page.locator('#motionFrameReadout').inner_text(), '-40')
        self.assertEqual(page.locator('#motionScore').inner_text(), str(frame['score']))
        self.assertEqual(page.locator('#fenceList button').count(), 18)
        self.assertEqual(page.locator('#fenceFaces polygon').count(), frame['score'])
        self.assertIn('Saved frame -40', page.locator('#liveScore').inner_text())
        self.assertIn('offset -40', page.locator('#recordReadout').inner_text())
        page.locator('#motionSlider').fill('20')
        self.assertEqual(page.locator('#fenceFaces polygon').count(), 93)
        self.assert_clean()
        page.close()

    def test_picker_updates_editable_copy_labels_aria_and_reset(self):
        page = self.page()
        buttons = page.locator('#snapshotPicker button')
        buttons.nth(0).click()
        self.assertEqual(buttons.nth(0).get_attribute('aria-pressed'), 'true')
        self.assertEqual(buttons.nth(1).get_attribute('aria-pressed'), 'false')
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())
        self.assertIn('Reset saved Starter', page.locator('#resetFence').inner_text())
        self.assertEqual(page.locator('#fenceFaces polygon').count(), 16)
        buttons.nth(2).click()
        self.assertEqual(buttons.nth(2).get_attribute('aria-pressed'), 'true')
        self.assertIn('Saved Published construction', page.locator('#liveScore').inner_text())
        self.assertIn('Reset saved Published construction', page.locator('#resetFence').inner_text())
        self.assertNotIn('published construction:', page.locator('#recordReadout').inner_text().lower())
        self.assert_clean()
        page.close()

    def test_planar_selection_zoom_pan_and_keyboard_do_not_change_geometry(self):
        page = self.page()
        before = page.locator('#fenceList button').all_inner_texts()
        center = page.locator('#fenceFaces polygon').first.evaluate('(e) => { const p = [...e.points]; return new DOMPoint(p.reduce((s,p)=>s+p.x,0)/3,p.reduce((s,p)=>s+p.y,0)/3).matrixTransform(e.getScreenCTM()).toJSON(); }')
        page.mouse.click(center['x'], center['y'])
        self.assertEqual(page.locator('#supportLines li').count(), 3)
        self.assertEqual(page.locator('.yard.is-selected').count(), 1)
        self.assertEqual(page.locator('.fence.is-support').count(), 3)
        page.locator('#focusFace').click()
        page.locator('#zoomIn').click()
        page.locator('#zoomOut').click()
        page.locator('#panMode').click()
        box = page.locator('#fenceSvg').bounding_box()
        page.mouse.move(box['x'] + 20, box['y'] + 20)
        page.mouse.down()
        page.mouse.move(box['x'] + 80, box['y'] + 50)
        page.mouse.up()
        page.locator('#fitView').click()
        self.assertEqual(before, page.locator('#fenceList button').all_inner_texts())
        page.locator('#editMode').click()
        page.locator('#fenceSvg').focus()
        page.keyboard.press('ArrowRight')
        self.assertEqual(page.locator('#fenceList button').nth(1).get_attribute('aria-pressed'), 'true')
        page.keyboard.press(']')
        self.assertNotEqual(before, page.locator('#fenceList button').all_inner_texts())
        page.keyboard.press('z')
        self.assertEqual(before, page.locator('#fenceList button').all_inner_texts())
        self.assertEqual(page.locator('canvas').count(), 0)
        self.assert_clean()
        page.close()

    def test_published_fit_frames_all_counted_faces(self):
        page = self.page()
        page.locator('#editPublished').click()
        bounds = page.locator('#fenceFaces').evaluate('(g) => { const r=g.getBBox(); return {x:r.x,y:r.y,width:r.width,height:r.height}; }')
        self.assertGreater(bounds['width'], 250)
        self.assertGreater(bounds['height'], 250)
        self.assertGreaterEqual(bounds['x'], 0)
        self.assertGreaterEqual(bounds['y'], 0)
        self.assertLessEqual(bounds['x'] + bounds['width'], 720)
        self.assertLessEqual(bounds['y'] + bounds['height'], 480)
        for width in (320, 390, 768):
            page.set_viewport_size({'width':width, 'height':850})
            page.wait_for_function('document.documentElement.scrollWidth <= innerWidth')
        self.assert_clean()
        page.close()

    def test_slide_buttons_exact_download_and_return_to_warmup(self):
        from tempfile import TemporaryDirectory
        from kobon.io import load_solution
        from kobon.geometry import triangles_by_adjacency
        page = self.page()
        page.locator('#editPublished').click()
        self.assertEqual(page.locator('#fenceFaces polygon').count(), 93)
        before = page.locator('#fenceList button').all_inner_texts()
        page.locator('#slideRight').click()
        self.assertNotEqual(before, page.locator('#fenceList button').all_inner_texts())
        with TemporaryDirectory() as directory:
            with page.expect_download() as event:
                page.locator('#downloadFence').click()
            target = Path(directory) / 'lines.json'
            event.value.save_as(target)
            self.assertEqual(len(triangles_by_adjacency(load_solution(target))), page.locator('#fenceFaces polygon').count())
        page.locator('#undoFence').click()
        self.assertEqual(before, page.locator('#fenceList button').all_inner_texts())
        page.locator('#warmup').click()
        self.assertEqual(page.locator('#fenceList button').count(), 4)
        self.assertEqual(page.locator('#fenceFaces polygon').count(), 2)
        self.assert_clean()
        page.close()

    def test_first_nudge_enables_undo_and_restore_saved_identities(self):
        page = self.page()
        warmup = page.locator('#fenceList button').all_inner_texts()
        page.locator('#turnRight').click()
        self.assertFalse(page.locator('#undoFence').is_disabled())
        self.assertNotEqual(page.locator('#fenceList button').all_inner_texts(), warmup)
        page.locator('#undoFence').click()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), warmup)

        page.locator('#snapshotPicker button').nth(0).click()
        snapshot = page.locator('#fenceList button').all_inner_texts()
        page.locator('#turnRight').click()
        self.assertIn('Edited copy of saved Starter', page.locator('#liveScore').inner_text())
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())
        page.locator('#turnRight').click()
        page.locator('#resetFence').click()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), snapshot)
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())

        page.locator('#motionSlider').fill('0')
        motion = page.locator('#fenceList button').all_inner_texts()
        page.locator('#turnRight').click()
        self.assertIn('Edited copy of saved frame -40', page.locator('#liveScore').inner_text())
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertIn('Saved frame -40', page.locator('#liveScore').inner_text())
        page.locator('#turnRight').click()
        page.locator('#resetFence').click()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), motion)
        self.assertIn('Saved frame -40', page.locator('#liveScore').inner_text())
        self.assert_clean()
        page.close()

    def test_handle_only_cancel_and_rejected_move_keep_undo_consistent(self):
        page = self.page()
        before = page.locator('#fenceList button').all_inner_texts()
        svg = page.locator('#fenceSvg')
        svg.dispatch_event('pointerdown', {'pointerId': 7, 'clientX': 100, 'clientY': 100})
        svg.dispatch_event('pointermove', {'pointerId': 7, 'clientX': 450, 'clientY': 350})
        svg.dispatch_event('pointerup', {'pointerId': 7, 'clientX': 450, 'clientY': 350})
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), before)
        self.assertTrue(page.locator('#undoFence').is_disabled())
        page.locator('#fenceList button').nth(3).click()
        handle = page.locator('.fence-handle')
        box = handle.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] - 150)
        page.locator('#fenceSvg').dispatch_event('pointercancel', {'pointerId': 1, 'clientX': box['x'] + box['width'] / 2, 'clientY': box['y'] - 150})
        page.mouse.up()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), before)
        self.assertTrue(page.locator('#undoFence').is_disabled())
        page.locator('#fenceList button').nth(0).click()
        box = page.locator('.fence-handle').bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(box['x'] + 80, box['y'] + 30)
        page.mouse.up()
        changed = page.locator('#fenceList button').all_inner_texts()
        self.assertNotEqual(changed, before)
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), before)
        self.assert_clean()
        page.close()


if __name__ == '__main__':
    unittest.main()
