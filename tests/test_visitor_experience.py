"""Visitor-first layout and read-only saved-view gesture regressions."""
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class VisitorExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()

    def page(self, name='index', width=1200, height=900, **options):
        page = self.browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce', **options)
        self.errors = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))
        page.goto((ROOT / 'site' / f'{name}.html').as_uri())
        self.addCleanup(page.close)
        return page

    def points(self, page):
        return page.locator('#arrangementFaces polygon').first.evaluate('(e)=>[...e.points].map(p=>[p.x,p.y])')

    def test_first_actions_are_visible_on_small_phones_and_desktop(self):
        for width, height in [(320, 740), (390, 844), (1440, 1000)]:
            for name, selector in [('fences', '#fenceSvg'), ('beaver', '#step')]:
                with self.subTest(width=width, page=name):
                    page = self.page(name, width, height)
                    box = page.locator(selector).bounding_box()
                    self.assertLess(box['y'] + min(box['height'], 44), height)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    self.assertFalse(self.errors)

    def test_visual_entries_work_offline_and_details_are_optional(self):
        page = self.page(width=390, height=844)
        images = page.locator('.playground-preview img')
        self.assertEqual(images.count(), 2)
        self.assertTrue(images.evaluate_all('(imgs)=>imgs.every(i=>i.complete&&i.naturalWidth>0)'))
        self.assertEqual(page.locator('.playground-preview').evaluate_all('(a)=>a.map(x=>x.getAttribute("href"))'), ['fences.html', 'beaver.html'])
        self.assertEqual(page.locator('.research-detail[open],.evidence-details[open]').count(), 0)
        self.assertLess(page.evaluate('document.documentElement.scrollHeight'), 7000)
        page.locator('#search > details > summary').click()
        self.assertTrue(page.locator('#runRows').is_visible())
        page.locator('.evidence-details > summary').click()
        self.assertTrue(page.locator('#sourceList').is_visible())
        self.assertFalse(self.errors)

    def test_story_wheel_pan_pinch_anchor_and_reset_preserve_saved_data(self):
        page = self.page()
        svg = page.locator('#arrangement')
        svg.scroll_into_view_if_needed()
        data = page.evaluate('JSON.stringify(window.LEARNING_DATA)')
        self.assertEqual(page.locator('#faceCount').inner_text(), '93')
        before = self.points(page)
        svg.dispatch_event('wheel', {'deltaX': 40, 'deltaY': 0, 'clientX': 350, 'clientY': 450, 'cancelable': True})
        self.assertNotEqual(before, self.points(page))
        page.locator('#resetGeometry').click()
        self.assertEqual(before, self.points(page))
        anchor = svg.evaluate('e=>{const p=document.querySelector("#arrangementFaces polygon").points[0];return new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM()).toJSON()}')
        svg.dispatch_event('wheel', {'deltaY': -20, 'ctrlKey': True, 'clientX': anchor['x'], 'clientY': anchor['y'], 'cancelable': True})
        after = self.points(page)
        # WheelEvent client coordinates are integer CSS pixels. An anchor
        # measured at a fractional pixel may differ by under one screen pixel.
        scale = svg.evaluate('(e)=>e.getScreenCTM().a')
        self.assertLess(abs(before[0][0] - after[0][0]) * scale, 1)
        self.assertLess(abs(before[0][1] - after[0][1]) * scale, 1)
        self.assertNotEqual(before[1], after[1])
        self.assertEqual(data, page.evaluate('JSON.stringify(window.LEARNING_DATA)'))
        self.assertEqual(page.locator('#faceCount').inner_text(), '93')
        self.assertFalse(self.errors)

    def test_robot_focus_moves_to_back_when_step_finishes(self):
        page = self.page('beaver')
        step = page.locator('#step')
        step.focus()
        for _ in range(6):
            page.keyboard.press('Enter')
        self.assertTrue(step.is_disabled())
        self.assertEqual(page.evaluate('document.activeElement.id'), 'back')
        self.assertFalse(self.errors)

    def test_story_allows_page_scroll_until_view_is_zoomed(self):
        page = self.page(width=390, height=844, has_touch=True)
        svg = page.locator('#arrangement')
        svg.scroll_into_view_if_needed()
        box = svg.bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        before = page.evaluate('scrollY')
        page.mouse.move(x, y)
        page.mouse.wheel(0, 190)
        page.wait_for_function('(before) => scrollY > before', arg=before, timeout=2500)
        self.assertGreater(page.evaluate('scrollY'), before)
        page.locator('#resetGeometry').click()
        self.assertIn('pan-y', svg.evaluate('e=>getComputedStyle(e).touchAction'))
        self.assertFalse(self.errors)

    def test_story_phone_swipe_scrolls_page_before_zoom(self):
        page = self.page(width=390, height=844, has_touch=True, is_mobile=True)
        svg = page.locator('#arrangement')
        svg.scroll_into_view_if_needed()
        box = svg.bounding_box()
        x = box['x'] + box['width'] / 2
        y = box['y'] + box['height'] * .7
        before = page.evaluate('scrollY')
        session = page.context.new_cdp_session(page)
        def touch(kind, y_pos=None):
            points = [] if y_pos is None else [{'x': x, 'y': y_pos, 'id': 0}]
            session.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': points})
            page.evaluate('() => new Promise(done => requestAnimationFrame(done))')
        touch('touchStart', y)
        for distance in (25, 70, 120, 180):
            touch('touchMove', y - distance)
        touch('touchEnd')
        page.wait_for_function('(before) => scrollY > before', arg=before, timeout=2500)
        self.assertFalse(self.errors)

    def test_story_switching_saved_drawings_restores_page_scroll(self):
        page = self.page(width=390, height=844, has_touch=True)
        svg = page.locator('#arrangement')
        page.locator('#zoomIn').click()
        self.assertEqual(svg.evaluate('e=>getComputedStyle(e).touchAction'), 'none')
        page.locator('#snapshotPicker button').first.click()
        self.assertEqual(svg.evaluate('e=>getComputedStyle(e).touchAction'), 'pan-y')
        self.assertFalse(self.errors)

    def test_story_keyboard_selection_preserves_board_focus(self):
        page = self.page()
        page.locator('#faceList button').first.click()
        face = page.locator('.arrangement-face.is-selected')
        face.focus()
        page.keyboard.press('ArrowRight')
        self.assertEqual(page.locator('#arrangement').evaluate('(e)=>document.activeElement===e'), True)
        page.keyboard.press('ArrowRight')
        self.assertIn('Yard 3', page.locator('#faceExplanation').inner_text())
        self.assertFalse(self.errors)

    def test_story_drag_does_not_select_but_click_and_keyboard_do(self):
        page = self.page()
        svg = page.locator('#arrangement'); svg.scroll_into_view_if_needed()
        box = svg.bounding_box(); x, y = box['x']+20, box['y']+30
        before = self.points(page)
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x+70, y+40, steps=5); page.mouse.up()
        self.assertNotEqual(before, self.points(page))
        self.assertEqual(page.locator('.arrangement-face.is-selected').count(), 0)
        page.locator('#resetGeometry').click()
        page.locator('#faceList button').first.click()
        page.locator('#zoomFace').click()
        svg.scroll_into_view_if_needed()
        center = page.locator('#arrangementFaces polygon').first.evaluate('(e)=>{const p=[...e.points];return new DOMPoint(p.reduce((s,v)=>s+v.x,0)/3,p.reduce((s,v)=>s+v.y,0)/3).matrixTransform(e.getScreenCTM()).toJSON()}')
        page.mouse.click(center['x'],center['y'])
        self.assertEqual(page.locator('.arrangement-face.is-selected').count(), 1)
        svg.focus(); page.keyboard.press('ArrowRight')
        self.assertIn('Yard 2',page.locator('#faceExplanation').inner_text())
        self.assertFalse(self.errors)

    def test_story_real_touch_pinch_keeps_geometry_and_restores(self):
        page = self.page(width=390,height=844,has_touch=True)
        svg=page.locator('#arrangement');svg.scroll_into_view_if_needed()
        box=svg.bounding_box(); x,y=box['x']+box['width']/2,box['y']+box['height']/2
        before=self.points(page)
        session=page.context.new_cdp_session(page)
        def touch(kind, distance):
            points=[] if kind=='touchEnd' else [{'x':x-distance,'y':y,'id':0},{'x':x+distance,'y':y,'id':1}]
            session.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
        touch('touchStart',35);touch('touchMove',60);touch('touchEnd',0)
        self.assertNotEqual(before,self.points(page))
        self.assertEqual(page.locator('#faceCount').inner_text(),'93')
        self.assertEqual(page.locator('.arrangement-face.is-selected').count(),0)
        page.locator('#resetGeometry').click()
        self.assertEqual(before,self.points(page))
        self.assertFalse(self.errors)


if __name__ == '__main__':
    unittest.main()
