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
        cls.browser = cls.playwright.chromium.launch(headless=True, args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def page(self):
        page = self.browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
        self.errors = []
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto((ROOT / 'site/3d.html').as_uri())
        page.locator('#fenceSvg').wait_for()
        page.locator('canvas').wait_for()
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

    def test_webgl_keyboard_camera_and_face_click(self):
        page = self.page()
        page.locator('#editPublished').click()
        canvas = page.locator('canvas')
        before = page.screenshot()
        page.locator('#webglStage').focus()
        page.keyboard.press('ArrowRight')
        page.keyboard.press('+')
        page.keyboard.press('t')
        page.locator('#orbitLeft').click()
        after = page.screenshot()
        self.assertNotEqual(before, after)
        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        selected = False
        for vertical in (.35, .42, .49, .56, .63):
            for horizontal in (.35, .42, .49, .56, .63):
                page.mouse.click(box['x'] + box['width'] * horizontal, box['y'] + box['height'] * vertical)
                if page.locator('#supportLines li').count() == 3:
                    selected = True
                    break
            if selected:
                break
        self.assertTrue(selected, 'a click on the rendered tabletop must raycast-select a raised face tile')
        self.assertIn('Face ', page.locator('#faceTitle').inner_text())
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
        page.mouse.move(box['x'] + 4, box['y'] + 4)
        page.mouse.down()
        page.mouse.move(box['x'] + 4, box['y'] - 150)
        page.locator('#fenceSvg').dispatch_event('pointercancel', {'pointerId': 1, 'clientX': box['x'] + 4, 'clientY': box['y'] - 150})
        page.mouse.up()
        self.assertEqual(page.locator('#fenceList button').all_inner_texts(), before)
        self.assertTrue(page.locator('#undoFence').is_disabled())
        page.locator('#fenceList button').nth(0).click()
        box = page.locator('.fence-handle').bounding_box()
        page.mouse.move(box['x'] + 4, box['y'] + 4)
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
