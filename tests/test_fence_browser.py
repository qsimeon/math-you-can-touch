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

    def page(self, **context_options):
        page = self.browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce', **context_options)
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
        self.assertIn('Saved position -40', page.locator('#liveScore').inner_text())
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
        self.assertIn('Saved Bader’s 93-yard construction', page.locator('#liveScore').inner_text())
        self.assertIn('Reset saved Bader’s 93-yard construction', page.locator('#resetFence').inner_text())
        self.assertIn('Saved Bader’s 93-yard construction', page.locator('#recordReadout').inner_text())
        self.assert_clean()
        page.close()

    def test_planar_selection_zoom_pan_and_keyboard_do_not_change_geometry(self):
        page = self.page()
        before = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
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
        self.assertEqual(before, page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'))
        page.locator('#editMode').click()
        page.locator('#fenceList button').first.click()
        page.keyboard.press('ArrowRight')
        self.assertEqual(page.locator('#fenceList button').nth(1).get_attribute('aria-pressed'), 'true')
        page.keyboard.press(']')
        self.assertNotEqual(before, page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'))
        page.keyboard.press('z')
        self.assertEqual(before, page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'))
        self.assertEqual(page.locator('canvas').count(), 0)
        self.assert_clean()
        page.close()

    def test_every_published_yard_centroid_selects_through_fence_hits(self):
        for desktop, options in ((True, {}), (False, {'is_mobile': True, 'has_touch': True})):
            page = self.page(**options)
            page.set_viewport_size({'width': 1440 if desktop else 390, 'height': 1100})
            page.locator('#editPublished').click()
            page.locator('#fenceSvg').scroll_into_view_if_needed()
            equations = lambda: page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
            before = equations()
            centers = page.locator('#fenceFaces polygon').evaluate_all('''(nodes) => nodes.map((node) => {
                const points = [...node.points], x = points.reduce((sum, point) => sum + point.x, 0) / 3, y = points.reduce((sum, point) => sum + point.y, 0) / 3;
                return new DOMPoint(x, y).matrixTransform(node.getScreenCTM()).toJSON();
            })''')
            self.assertEqual(len(centers), 93)
            for index, center in enumerate(centers):
                if desktop:
                    page.mouse.click(center['x'], center['y'])
                else:
                    page.touchscreen.tap(center['x'], center['y'])
                self.assertEqual(page.locator('#faceTitle').inner_text(), f'Yard {index + 1}')
                self.assertEqual(page.locator('#supportLines li').count(), 3)
            self.assertEqual(page.locator('#fenceFaces polygon').count(), 93)
            self.assertEqual(equations(), before)
            page.locator('#panMode').click()
            center = centers[-1]
            if desktop:
                page.mouse.click(center['x'], center['y'])
            else:
                page.touchscreen.tap(center['x'], center['y'])
            self.assertEqual(page.locator('#faceTitle').inner_text(), 'Yard 93')
            self.assertEqual(page.locator('#fenceFaces polygon').count(), 93)
            self.assert_clean()
            page.close()

    def test_published_fit_frames_all_counted_faces(self):
        page = self.page()
        page.locator('#editPublished').click()
        self.assertIn('Your copy of Bader’s 93', page.locator('#liveScore').inner_text())
        self.assertIn('Your copy of Bader’s 93', page.locator('#recordReadout').inner_text())
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
        before = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        page.locator('#slideRight').click()
        self.assertNotEqual(before, page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'))
        with TemporaryDirectory() as directory:
            with page.expect_download() as event:
                page.locator('#downloadFence').click()
            target = Path(directory) / 'lines.json'
            event.value.save_as(target)
            self.assertEqual(len(triangles_by_adjacency(load_solution(target))), page.locator('#fenceFaces polygon').count())
        page.locator('#undoFence').click()
        self.assertEqual(before, page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'))
        page.locator('#warmup').click()
        self.assertEqual(page.locator('#fenceList button').count(), 4)
        self.assertEqual(page.locator('#fenceFaces polygon').count(), 2)
        self.assert_clean()
        page.close()

    def test_first_nudge_enables_undo_and_restore_saved_identities(self):
        page = self.page()
        warmup = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        page.locator('#turnRight').click()
        self.assertFalse(page.locator('#undoFence').is_disabled())
        self.assertNotEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), warmup)
        page.locator('#undoFence').click()
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), warmup)

        page.locator('#snapshotPicker button').nth(0).click()
        snapshot = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        page.locator('#turnRight').click()
        self.assertIn('Your edit of saved Starter', page.locator('#liveScore').inner_text())
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())
        page.locator('#turnRight').click()
        page.locator('#resetFence').click()
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), snapshot)
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())

        page.locator('#motionSlider').fill('0')
        motion = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        page.locator('#turnRight').click()
        self.assertIn('Edited copy of saved position -40', page.locator('#liveScore').inner_text())
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertIn('Saved position -40', page.locator('#liveScore').inner_text())
        page.locator('#turnRight').click()
        page.locator('#resetFence').click()
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), motion)
        self.assertIn('Saved position -40', page.locator('#liveScore').inner_text())
        self.assert_clean()
        page.close()

    def test_background_drag_cancel_and_undo_keep_geometry_consistent(self):
        page = self.page()
        before = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        svg = page.locator('#fenceSvg')
        svg.dispatch_event('pointerdown', {'pointerId': 7, 'clientX': 100, 'clientY': 100})
        svg.dispatch_event('pointermove', {'pointerId': 7, 'clientX': 450, 'clientY': 350})
        svg.dispatch_event('pointerup', {'pointerId': 7, 'clientX': 450, 'clientY': 350})
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), before)
        self.assertTrue(page.locator('#undoFence').is_disabled())
        page.locator('#fenceList button').nth(3).click()
        handle = page.locator('.fence-handle')
        box = handle.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] - 150)
        page.locator('#fenceSvg').dispatch_event('pointercancel', {'pointerId': 1, 'clientX': box['x'] + box['width'] / 2, 'clientY': box['y'] - 150})
        page.mouse.up()
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), before)
        self.assertTrue(page.locator('#undoFence').is_disabled())
        page.locator('#fenceList button').nth(0).click()
        box = page.locator('.fence-handle').bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(box['x'] + 80, box['y'] + 30)
        page.mouse.up()
        changed = page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)')
        self.assertNotEqual(changed, before)
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#undoFence').click()
        self.assertEqual(page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.dataset.equation)'), before)
        self.assert_clean()
        page.close()

    def test_clockwise_turn_stays_on_visible_pivot_and_handles_many_turns(self):
        page = self.page()
        pivot = page.locator('.fence-handle').evaluate('(e)=>[+e.getAttribute("cx"),+e.getAttribute("cy")]')
        for _ in range(40):
            page.locator('#turnRight').click()
            line = page.locator('.fence.is-selected').evaluate('(e)=>["x1","y1","x2","y2"].map(k=>+e.getAttribute(k))')
            x1,y1,x2,y2 = line
            distance = abs((y2-y1)*pivot[0]-(x2-x1)*pivot[1]+x2*y1-y2*x1)/((y2-y1)**2+(x2-x1)**2)**.5
            self.assertLess(distance, .01)
            self.assertNotIn('rejected', page.locator('#liveScore').inner_text())
        page.locator('#resetFence').click()
        page.locator('#turnRight').click()
        x1,y1,x2,y2 = page.locator('.fence.is-selected').evaluate('(e)=>["x1","y1","x2","y2"].map(k=>+e.getAttribute(k))')
        self.assertGreater((x2-x1)/(y1-y2), .15)
        page.locator('#undoFence').click()
        page.locator('#fenceSvg').focus(); page.keyboard.press('q')
        self.assertFalse(page.locator('#undoFence').is_disabled())
        self.assert_clean(); page.close()

    def test_direct_line_drag_and_turn_handle_have_one_undo_each(self):
        page = self.page()
        equations = lambda: page.locator('#fenceList button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.equation)')
        original = equations()
        line = page.locator('.fence.is-selected').evaluate('(e)=>new DOMPoint(+e.getAttribute("x1"),400).matrixTransform(e.getScreenCTM()).toJSON()')
        page.mouse.move(line['x'],line['y']); page.mouse.down(); page.mouse.move(line['x']+40,line['y'],steps=5); page.mouse.up()
        self.assertNotEqual(original[0],equations()[0]); self.assertEqual(original[1:],equations()[1:])
        page.locator('#undoFence').click(); self.assertEqual(original,equations()); self.assertTrue(page.locator('#undoFence').is_disabled())
        pivot = page.locator('.fence-handle').evaluate('(e)=>new DOMPoint(+e.getAttribute("cx"),+e.getAttribute("cy")).matrixTransform(e.getScreenCTM()).toJSON()')
        turn = page.locator('.turn-handle').bounding_box(); x=turn['x']+turn['width']/2; y=turn['y']+turn['height']/2
        page.mouse.move(x,y); page.mouse.down(); page.mouse.move(pivot['x']-70,pivot['y']+40,steps=8); page.mouse.up()
        self.assertNotEqual(original[0],equations()[0]); self.assertEqual(original[1:],equations()[1:])
        page.locator('#undoFence').click(); self.assertEqual(original,equations()); self.assertTrue(page.locator('#undoFence').is_disabled())
        self.assert_clean(); page.close()


    def test_refused_drag_feedback_clears_on_edit_reset_and_load(self):
        page = self.page()
        def refuse_overlap():
            page.locator('#fenceList button').nth(3).click()
            pivot = page.locator('.fence-handle').bounding_box()
            target_y = page.locator('.fence[data-index="1"]').evaluate(
                '(e)=>new DOMPoint(0,+e.getAttribute("y1")).matrixTransform(e.getScreenCTM()).y')
            x, y = pivot['x'] + pivot['width']/2, pivot['y'] + pivot['height']/2
            before = page.locator('#selectedEquation').inner_text()
            page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x, target_y); page.mouse.up()
            self.assertEqual(before, page.locator('#selectedEquation').inner_text())
            self.assertIn('two fences on the same line', page.locator('#dragHint').inner_text())
        for next_action in ('slideRight', 'resetFence', 'warmup'):
            page.locator('#warmup').click()
            refuse_overlap()
            page.locator('#' + next_action).click()
            self.assertNotIn('unchanged', page.locator('#dragHint').inner_text())
            self.assertIn('Drag a fence', page.locator('#dragHint').inner_text())
        self.assert_clean(); page.close()

    def test_offscreen_turn_explains_and_modified_shortcuts_leave_geometry(self):
        page = self.page()
        equations = lambda: page.locator('#fenceList button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.equation)')
        before = equations()
        for modifier in ('metaKey', 'ctrlKey', 'altKey'):
            for key in ('[', ']', 'q', 'e', 'ArrowRight'):
                page.locator('#fenceSvg').dispatch_event('keydown', {'key':key, modifier:True})
                self.assertEqual(before, equations())
                self.assertEqual('true', page.locator('#fenceList button').first.get_attribute('aria-pressed'))
        for _ in range(12):
            page.locator('#zoomIn').click()
        self.assertEqual(0, page.locator('.fence.is-selected').count())
        page.locator('#turnRight').click()
        self.assertIn('outside the view', page.locator('#dragHint').inner_text())
        self.assertEqual(before, equations())
        page.locator('#fitView').click(); page.locator('#turnRight').click()
        self.assertNotEqual(before, equations())
        self.assertNotIn('outside the view', page.locator('#dragHint').inner_text())
        self.assert_clean(); page.close()

    def test_home_first_arrow_and_consistent_yard_labels(self):
        page = self.page()
        page.goto((ROOT / 'site/index.html').as_uri())
        page.locator('#arrangement').focus(); page.keyboard.press('ArrowRight')
        self.assertIn('Yard 1 is', page.locator('#faceExplanation').inner_text())
        self.assertIn('Fences ', page.locator('#faceList button').first.inner_text())
        self.assertTrue(all(text.startswith('Fence ') for text in page.locator('#supportLines li').all_inner_texts()))
        page.keyboard.press('ArrowLeft')
        self.assertIn('Yard 76 is', page.locator('#faceExplanation').inner_text())
        page.locator('#faceToggle').click()
        self.assertEqual('Show shading', page.locator('#faceToggle').inner_text())
        page.locator('#faceToggle').click()
        self.assertEqual('Hide shading', page.locator('#faceToggle').inner_text())
        self.assertIn('unresolved by our checker', page.locator('#busy-beaver .scope-note').inner_text())
        self.assertIn('unresolved by this checker', page.locator('.halt-note').inner_text())
        self.assertIn('standard two-state result settles nonhalting only when applied separately', page.locator('.halt-note').inner_text())
        self.assertEqual('https://oeis.org/A060843', page.locator('#busy-beaver .scope-note a').first.get_attribute('href'))
        self.assert_clean(); page.close()

    def test_compact_handles_keep_touch_targets_and_rotate_after_resize(self):
        page = self.page()
        equations = lambda: page.locator('#fenceList button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.equation)')
        for width in (1440, 390, 320, 768):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.locator('#quickWarmup').click()
            page.wait_for_function('Math.abs(document.querySelector(".turn-handle").getBoundingClientRect().width - 26) < 1')
            self.assertLessEqual(page.locator('.fence-handle').bounding_box()['width'], 12.1)
            self.assertLessEqual(page.locator('.turn-handle').bounding_box()['width'], 28.1)
            self.assertEqual(page.locator('.turn-guide').count(), 0)
            for selector in ('.move-hit', '.turn-hit'):
                self.assertAlmostEqual(page.locator(selector).bounding_box()['width'], 44, delta=1)
            before = equations()
            page.locator('#fenceSvg').scroll_into_view_if_needed()
            box = page.locator('.turn-hit').bounding_box()
            x, y = box['x'] + box['width']/2 + 18, box['y'] + box['height']/2
            self.assertEqual('handle-hit turn-hit', page.evaluate('([x,y])=>document.elementFromPoint(x,y).getAttribute("class")', [x,y]))
            page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x-30,y+40,steps=8); page.mouse.up()
            self.assertNotEqual(before[0], equations()[0])
            self.assertEqual(before[1:], equations()[1:])
            page.locator('#undoFence').click()
            self.assertEqual(before, equations())
            page.locator('#panMode').click()
            page.wait_for_function('getComputedStyle(document.querySelector(".turn-handle")).visibility === "hidden"')
            page.locator('#editMode').click()
            page.wait_for_function('getComputedStyle(document.querySelector(".turn-handle")).visibility === "visible"')
        self.assert_clean(); page.close()

    def test_prediction_precedes_tape_and_rule_edit_restarts_robot(self):
        page = self.page()
        page.goto((ROOT / 'site/beaver.html').as_uri())
        self.assertLess(page.locator('.prediction').bounding_box()['y'], page.locator('#tape').bounding_box()['y'])
        page.locator('[data-predict="HALTED"]').click()
        for _ in range(6):
            page.locator('#step').click()
        self.assertIn('Halted at step 6', page.locator('#outcome').inner_text())
        self.assertIn('4 marked squares', page.locator('#outcome').inner_text())
        self.assertEqual('Your prediction matched.', page.locator('#predictionFeedback').inner_text())
        page.get_by_label('State A, reads 0: Next').select_option('H')
        self.assertIn('Step 0', page.locator('#stepReadout').inner_text())
        page.locator('#step').click()
        self.assertIn('Halted at step 1', page.locator('#outcome').inner_text())
        page.locator('#preset').select_option('cycle')
        page.locator('#step').click()
        self.assertIn('stayed in state A', page.locator('#narration').inner_text())
        self.assertIn('repeat this step forever', page.locator('#outcome').inner_text())
        self.assert_clean(); page.close()


if __name__ == '__main__':
    unittest.main()
