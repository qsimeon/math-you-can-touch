"""Browser regressions for trackpad and touch navigation on the fence board.

Navigation must move only the view: exact equations, counts and undo stay put.
"""
import math
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

EQUATIONS = '(nodes) => nodes.map(n => n.dataset.equation)'
POLYGONS = '(nodes) => nodes.map(n => [...n.points].map(p => [p.x, p.y]))'
TO_SVG = '([x, y]) => { const p = new DOMPoint(x, y).matrixTransform(document.querySelector("#fenceSvg").getScreenCTM().inverse()); return [p.x, p.y]; }'
TO_SCREEN = '([x, y]) => { const p = new DOMPoint(x, y).matrixTransform(document.querySelector("#fenceSvg").getScreenCTM()); return [p.x, p.y]; }'
WHEEL = '''([x, y, deltaX, deltaY, deltaMode, ctrlKey]) => document.querySelector("#fenceSvg").dispatchEvent(
    new WheelEvent("wheel", {clientX:x, clientY:y, deltaX, deltaY, deltaMode, ctrlKey, bubbles:true, cancelable:true}))'''
# A screen point that hits fence `index`'s wide hit stroke, offset from the line, inside or outside every yard.
FENCE_POINT = '''([insideYard, skip]) => {
    const svg = document.querySelector("#fenceSvg"), yards = [...document.querySelectorAll("#fenceFaces polygon")];
    for (const fence of document.querySelectorAll(".fence")) {
        const index = +fence.dataset.index;
        if (index === skip) continue;
        const [x1, y1, x2, y2] = ["x1", "y1", "x2", "y2"].map(name => +fence.getAttribute(name)), length = Math.hypot(x2 - x1, y2 - y1);
        const nx = -(y2 - y1) / length, ny = (x2 - x1) / length;
        for (let t = .05; t < .95; t += .01) for (const offset of [6, -6, 10, -10]) {
            const point = new DOMPoint(x1 + (x2 - x1) * t + nx * offset, y1 + (y2 - y1) * t + ny * offset);
            if (yards.some(yard => yard.isPointInFill(point)) !== insideYard) continue;
            const screen = point.matrixTransform(svg.getScreenCTM()), hit = document.elementFromPoint(screen.x, screen.y);
            if (hit?.classList.contains("fence-hit") && +hit.dataset.index === index) return { index, x:screen.x, y:screen.y, nx, ny };
        }
    }
    return null;
}'''
COUNT_SCORES = '() => { window.scoreCalls = 0; const score = FenceGeometry.score; FenceGeometry.score = (...args) => { window.scoreCalls += 1; return score(...args); }; }'


def centroid(points):
    return [sum(p[0] for p in points) / 3, sum(p[1] for p in points) / 3]


def edge(points):
    return math.dist(points[0], points[1])


class FenceGestureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.errors = []

    def open(self, touch=False):
        options = {'viewport': {'width': 390, 'height': 844}, 'is_mobile': True, 'has_touch': True} if touch else {'viewport': {'width': 1440, 'height': 1100}}
        page = self.browser.new_page(reduced_motion='reduce', **options)
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto((ROOT / 'site/fences.html').as_uri())
        page.locator('#fenceSvg').wait_for()
        self.addCleanup(page.close)
        return page

    def snapshot(self, page):
        return {
            'equations': page.locator('#fenceList button').evaluate_all(EQUATIONS),
            'score': page.locator('#liveScore').inner_text(),
            'readout': page.locator('#recordReadout').inner_text(),
            'yards': page.locator('#fenceFaces polygon').count(),
            'undo_disabled': page.locator('#undoFence').is_disabled(),
        }

    def polygons(self, page):
        return page.locator('#fenceFaces polygon').evaluate_all(POLYGONS)

    def assert_points_close(self, actual, expected, places=3):
        self.assertEqual(len(actual), len(expected))
        for got, want in zip(actual, expected):
            self.assertAlmostEqual(got[0], want[0], places=places)
            self.assertAlmostEqual(got[1], want[1], places=places)

    def board(self, page):
        page.locator('#fenceSvg').scroll_into_view_if_needed()
        return page.locator('#fenceSvg').bounding_box()

    def touch(self, page):
        client = page.context.new_cdp_session(page)
        def send(kind, *points):
            client.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [{'x': x, 'y': y, 'id': i} for i, (x, y) in enumerate(points)]})
            # Chromium dispatches touch pointermove on animation frames.
            page.evaluate('() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))')
        return send

    def test_trackpad_scroll_pans_view_with_delta_mode_normalized(self):
        page = self.open()
        page.locator('#editPublished').click()
        box = self.board(page)
        before, start = self.snapshot(page), self.polygons(page)
        scroll = page.evaluate('scrollY')
        units = 720 / box['width']
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.wheel(0, 60)
        page.wait_for_function('(y) => scrollY !== y', arg=scroll)
        self.assertEqual(start, self.polygons(page))
        box = self.board(page)
        scroll = page.evaluate('scrollY')
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.wheel(60, 20)
        page.wait_for_function('(x) => document.querySelector("#fenceFaces polygon").points[0].x !== x', arg=start[0][0][0])
        moved = self.polygons(page)
        self.assertAlmostEqual(moved[0][0][0] - start[0][0][0], -60 * units, places=3)
        self.assertAlmostEqual(moved[0][0][1] - start[0][0][1], -20 * units, places=3)
        self.assertEqual(scroll, page.evaluate('scrollY'))
        page.locator('#panMode').click()
        for mode, delta, expected in ((1, 3, 48 * units), (2, 1, 480), (0, 48, 48 * units)):
            previous = self.polygons(page)[0][0][1]
            page.evaluate(WHEEL, [box['x'] + 50, box['y'] + 50, 0, delta, mode, False])
            self.assertAlmostEqual(previous - self.polygons(page)[0][0][1], expected, places=2)
        self.assertEqual(before, self.snapshot(page))
        page.locator('#fitView').click()
        self.assert_points_close(self.polygons(page)[0], start[0])
        self.assertEqual(self.errors, [])

    def test_phone_swipe_on_open_board_scrolls_and_handle_drag_still_edits(self):
        page = self.open(touch=True)
        box = self.board(page)
        before = self.snapshot(page)
        session = page.context.new_cdp_session(page)
        def send(kind, x=None, y=None):
            points = [] if x is None else [{'x': x, 'y': y, 'id': 0}]
            session.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': points})
            page.evaluate('() => new Promise(done => requestAnimationFrame(done))')
        x, y = box['x'] + box['width'] * .8, box['y'] + box['height'] * .78
        page.evaluate('([x,y])=>{const el=document.elementFromPoint(x,y);if(el?.classList.contains("fence-hit")||el?.classList.contains("handle-hit"))throw Error("not an open part of the board")}', [x,y])
        scroll = page.evaluate('scrollY')
        send('touchStart', x, y)
        for delta in (30, 70, 125, 170):
            send('touchMove', x, y - delta)
        send('touchEnd')
        page.wait_for_function('(old) => scrollY > old', arg=scroll)
        self.assertEqual(before, self.snapshot(page))
        box = self.board(page)
        hit = page.locator('.move-hit').bounding_box()
        x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
        send('touchStart', x, y)
        send('touchMove', x + 25, y + 20)
        send('touchEnd')
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        self.assertEqual(self.errors, [])

    def test_ctrl_wheel_pinch_zooms_around_cursor_within_limits(self):
        page = self.open()
        page.locator('#editPublished').click()
        self.board(page)
        before, start = self.snapshot(page), self.polygons(page)
        cursor = [round(value) for value in page.evaluate(TO_SCREEN, centroid(start[0]))]
        page.mouse.move(*cursor)
        page.keyboard.down('Control')
        page.mouse.wheel(0, -40)
        page.keyboard.up('Control')
        page.wait_for_function('(y) => document.querySelector("#fenceFaces polygon").points[0].y !== y', arg=start[0][0][1])
        anchor = page.evaluate(TO_SVG, cursor)
        about = lambda points, ratio: [[anchor[0] + (x - anchor[0]) * ratio, anchor[1] + (y - anchor[1]) * ratio] for x, y in points]
        zoomed = self.polygons(page)
        self.assert_points_close(zoomed[0], about(start[0], math.exp(.4)))
        page.evaluate(WHEEL, [*cursor, 0, -1, 1, True])
        self.assert_points_close(self.polygons(page)[0], about(zoomed[0], math.exp(.16)))
        for _ in range(80):
            page.evaluate(WHEEL, [*cursor, 0, -1000, 0, True])
        self.assertAlmostEqual(edge(self.polygons(page)[0]) / edge(start[0]), 64, places=3)
        for _ in range(80):
            page.evaluate(WHEEL, [*cursor, 0, 1000, 0, True])
        self.assertAlmostEqual(edge(self.polygons(page)[0]) / edge(start[0]), .25, places=5)
        self.assertEqual(before, self.snapshot(page))
        page.locator('#fitView').click()
        self.assert_points_close(self.polygons(page)[0], start[0])
        self.assertEqual(self.errors, [])

    def test_two_finger_pinch_and_pan_change_only_the_view(self):
        page = self.open(touch=True)
        page.locator('#editPublished').click()
        box = self.board(page)
        before, start = self.snapshot(page), self.polygons(page)
        send = self.touch(page)
        a, b = (box['x'] + box['width'] * .35, box['y'] + box['height'] * .5), (box['x'] + box['width'] * .55, box['y'] + box['height'] * .5)
        send('touchStart', a, b)
        for _ in range(6):
            a = (a[0] - 5 + 3, a[1] + 4)
            b = (b[0] + 5 + 3, b[1] + 4)
            send('touchMove', a, b)
        mid0 = page.evaluate(TO_SVG, [box['x'] + box['width'] * .45, box['y'] + box['height'] * .5])
        mid1 = page.evaluate(TO_SVG, [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
        ratio = math.dist(a, b) / (box['width'] * .2)
        moved = self.polygons(page)
        expected = [[mid1[0] + (x - mid0[0]) * ratio, mid1[1] + (y - mid0[1]) * ratio] for x, y in start[0]]
        self.assert_points_close(moved[0], expected, places=2)
        send('touchEnd')
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual('Pick a yard', page.locator('#faceTitle').inner_text())
        page.locator('#fitView').click()
        self.assert_points_close(self.polygons(page)[0], start[0])
        self.assertEqual(self.errors, [])

    def test_second_finger_reverts_tentative_drag_and_fresh_touch_still_edits(self):
        page = self.open(touch=True)
        page.locator('#snapshotPicker button').nth(0).click()
        box = self.board(page)
        before = self.snapshot(page)
        hit = page.locator('.move-hit').bounding_box()
        finger = (hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2)
        other = (box['x'] + 30, box['y'] + 30)
        send = self.touch(page)
        send('touchStart', finger)
        send('touchMove', (finger[0] + 40, finger[1] + 25))
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        self.assertIn('Your edit of saved Starter', page.locator('#liveScore').inner_text())
        send('touchStart', (finger[0] + 40, finger[1] + 25), other)
        self.assertEqual(before, self.snapshot(page))
        send('touchMove', (finger[0] + 80, finger[1] + 60), (other[0] - 10, other[1]))
        send('touchEnd')
        self.assertEqual(before, self.snapshot(page))
        page.locator('#fitView').click()
        hit = page.locator('.move-hit').bounding_box()
        finger = (hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2)
        send('touchStart', finger)
        send('touchMove', (finger[0] + 40, finger[1] + 25))
        send('touchEnd')
        after = self.snapshot(page)
        self.assertNotEqual(before['equations'], after['equations'])
        self.assertEqual(before['equations'][1:], after['equations'][1:])
        self.assertFalse(after['undo_disabled'])
        page.locator('#undoFence').click()
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual(self.errors, [])

    def test_real_touch_cancel_reverts_and_pinch_keeps_the_selected_fence(self):
        page = self.open(touch=True)
        page.locator('#snapshotPicker button').nth(0).click()
        box = self.board(page)
        before = self.snapshot(page)
        pressed = lambda: page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.getAttribute("aria-pressed"))').index('true')
        hit = page.locator('.move-hit').bounding_box()
        finger, other = (hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2), (box['x'] + 30, box['y'] + 30)
        send = self.touch(page)
        send('touchStart', finger)
        send('touchMove', (finger[0] + 40, finger[1] + 25))
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        send('touchCancel')
        self.assertEqual(before, self.snapshot(page))
        send('touchStart', finger, other)
        send('touchMove', (finger[0] + 30, finger[1]), (other[0] - 30, other[1]))
        send('touchCancel')
        self.assertEqual(before, self.snapshot(page))
        page.locator('#fitView').click()
        target = page.evaluate(FENCE_POINT, [False, 0])
        on_fence = (target['x'], target['y'])
        self.assertEqual(0, pressed())
        send('touchStart', on_fence)
        self.assertEqual(target['index'], pressed())
        send('touchStart', on_fence, other)
        self.assertEqual(0, pressed())
        send('touchMove', (on_fence[0] + 20, on_fence[1]), (other[0] - 20, other[1]))
        send('touchEnd')
        self.assertEqual(0, pressed())
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual(self.errors, [])

    def test_finger_left_after_pinch_does_not_edit_until_a_fresh_touch(self):
        page = self.open(touch=True)
        self.board(page)
        before = self.snapshot(page)
        hit = page.locator('.move-hit').bounding_box()
        x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
        # CDP cannot lift one of two touches, so dispatch the touch pointer stream directly.
        page.evaluate('''([x, y]) => {
            const svg = document.querySelector("#fenceSvg");
            window.touchPointer = (type, id, px, py, target = svg) => target.dispatchEvent(new PointerEvent(type,
                {pointerId:id, pointerType:"touch", isPrimary:id === 11, clientX:px, clientY:py, button:type === "pointermove" ? -1 : 0, bubbles:true, cancelable:true}));
            window.atPoint = (px, py) => document.elementFromPoint(px, py);
        }''', [x, y])
        pointer = lambda kind, pid, px, py, at=False: page.evaluate(
            '([kind, pid, px, py, at]) => touchPointer(kind, pid, px, py, at ? atPoint(px, py) : undefined)', [kind, pid, px, py, at])
        pointer('pointerdown', 11, x, y, True)
        pointer('pointermove', 11, x + 40, y)
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        pointer('pointerdown', 12, x + 120, y + 60)
        self.assertEqual(before, self.snapshot(page))
        pointer('pointermove', 12, x + 160, y + 80)
        pointer('pointerup', 12, x + 160, y + 80)
        start = self.polygons(page)
        for step in range(1, 5):
            pointer('pointermove', 11, x + 40 + step * 30, y + step * 10)
        self.assertEqual(start, self.polygons(page))
        pointer('pointerup', 11, x + 160, y + 40)
        self.assertEqual(before, self.snapshot(page))
        hit = page.locator('.move-hit').bounding_box()
        x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
        pointer('pointerdown', 11, x, y, True)
        pointer('pointermove', 11, x + 40, y)
        pointer('pointerup', 11, x + 40, y)
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        self.assertFalse(page.locator('#undoFence').is_disabled())
        self.assertEqual(self.errors, [])

    def test_view_only_navigation_reuses_the_exact_count(self):
        page = self.open(touch=True)
        page.locator('#editPublished').click()
        box = self.board(page)
        before = self.snapshot(page)
        page.evaluate(COUNT_SCORES)
        center = [box['x'] + box['width'] / 2, box['y'] + box['height'] / 2]
        page.evaluate(WHEEL, [*center, 10, 20, 0, False])
        page.evaluate(WHEEL, [*center, 0, -30, 0, True])
        send = self.touch(page)
        send('touchStart', (center[0] - 40, center[1]), (center[0] + 40, center[1]))
        send('touchMove', (center[0] - 60, center[1] + 5), (center[0] + 60, center[1] + 5))
        send('touchEnd')
        page.locator('#zoomIn').click()
        page.locator('#zoomOut').click()
        page.locator('#panMode').click()
        page.mouse.move(*center)
        page.mouse.down()
        page.mouse.move(center[0] + 40, center[1] + 20, steps=4)
        page.mouse.up()
        self.assertEqual(0, page.evaluate('scoreCalls'))
        self.assertEqual(before, self.snapshot(page))
        page.locator('#editMode').click()
        page.locator('#slideRight').click()
        self.assertGreater(page.evaluate('scoreCalls'), 0)
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        self.assertEqual(self.errors, [])

    def test_small_jitter_neither_moves_nor_turns_a_fence(self):
        page = self.open(touch=True)
        page.locator('#editPublished').click()
        self.board(page)
        before = self.snapshot(page)
        send = self.touch(page)
        for selector in ('.move-hit', '.turn-hit'):
            hit = page.locator(selector).bounding_box()
            x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
            send('touchStart', (x, y))
            for dx, dy in ((2, 0), (0, -2), (-2, 2), (6, 7)):
                send('touchMove', (x + dx, y + dy))
            send('touchEnd')
            self.assertEqual(before, self.snapshot(page))
        hit = page.locator('.move-hit').bounding_box()
        x, y = hit['x'] + hit['width'] / 2, hit['y'] + hit['height'] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 2, y + 2)
        page.mouse.move(x + 3, y - 2)
        page.mouse.up()
        self.assertEqual(before, self.snapshot(page))
        send('touchStart', (x, y))
        send('touchMove', (x + 12, y + 9))
        send('touchMove', (x + 30, y + 25))
        send('touchEnd')
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        page.locator('#undoFence').click()
        self.assertEqual(before, self.snapshot(page))
        self.board(page)
        yards = self.polygons(page)
        largest = max(range(len(yards)), key=lambda i: edge(yards[i]) * math.dist(yards[i][1], yards[i][2]))
        center = page.evaluate(TO_SCREEN, centroid(yards[largest]))
        send('touchStart', center)
        send('touchMove', (center[0] + 2, center[1] - 2))
        send('touchEnd')
        self.assertEqual(f'Yard {largest + 1}', page.locator('#faceTitle').inner_text())
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual(self.errors, [])

    def test_drag_from_inside_a_yard_moves_the_pressed_fence_and_tap_picks_the_yard(self):
        page = self.open()
        page.locator('#editPublished').click()
        self.board(page)
        before = self.snapshot(page)
        target = page.evaluate(FENCE_POINT, [True, 0])
        self.assertIsNotNone(target)
        selected = lambda: page.locator('#fenceList button').evaluate_all('(nodes) => nodes.map(n => n.getAttribute("aria-pressed"))').index('true')
        page.mouse.click(target['x'], target['y'])
        self.assertTrue(page.locator('#faceTitle').inner_text().startswith('Yard '))
        self.assertEqual(0, selected())
        self.assertEqual(before, self.snapshot(page))
        page.mouse.move(target['x'], target['y'])
        page.mouse.down()
        page.mouse.move(target['x'] + target['nx'] * 30, target['y'] + target['ny'] * 30, steps=5)
        page.mouse.up()
        after = self.snapshot(page)
        changed = [i for i, (old, new) in enumerate(zip(before['equations'], after['equations'])) if old != new]
        self.assertEqual([target['index']], changed)
        self.assertEqual(target['index'], selected())
        self.assertFalse(after['undo_disabled'])
        page.locator('#undoFence').click()
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual(self.errors, [])

    def test_zoom_after_pan_keeps_view_center_and_cursor_fixed(self):
        page = self.open()
        page.locator('#editPublished').click()
        box = self.board(page)
        page.evaluate(WHEEL, [box['x'] + 40, box['y'] + 40, 70, -45, 0, False])
        page.locator('#panMode').click()
        page.mouse.move(box['x'] + 200, box['y'] + 200)
        page.mouse.down()
        page.mouse.move(box['x'] + 260, box['y'] + 170, steps=4)
        page.mouse.up()
        page.locator('#editMode').click()
        before, start = self.snapshot(page), self.polygons(page)[0]
        about = lambda points, anchor, ratio: [[anchor[0] + (x - anchor[0]) * ratio, anchor[1] + (y - anchor[1]) * ratio] for x, y in points]
        page.locator('#zoomIn').click()
        self.assert_points_close(self.polygons(page)[0], about(start, [360, 240], 1.5))
        page.locator('#zoomOut').click()
        self.assert_points_close(self.polygons(page)[0], start)
        cursor = [round(box['x'] + box['width'] * .7), round(box['y'] + box['height'] * .3)]
        anchor = page.evaluate(TO_SVG, cursor)
        page.evaluate(WHEEL, [*cursor, 0, -25, 0, True])
        self.assert_points_close(self.polygons(page)[0], about(start, anchor, math.exp(.25)))
        self.assertEqual(before, self.snapshot(page))
        self.assertEqual(self.errors, [])

    def test_keyboard_turn_from_fence_list_keeps_focus(self):
        page = self.open()
        before = self.snapshot(page)
        page.locator('#fenceList button').nth(2).focus()
        page.keyboard.press('e')
        self.assertNotEqual(before['equations'], self.snapshot(page)['equations'])
        self.assertEqual('Fence 3', page.evaluate('document.activeElement.textContent'))
        self.assertEqual(self.errors, [])

    def test_reset_is_undoable_and_command_or_control_z_undoes(self):
        page = self.open()
        page.locator('#snapshotPicker button').nth(0).click()
        original = self.snapshot(page)
        page.locator('#slideRight').click()
        first = self.snapshot(page)
        page.locator('#slideRight').click()
        second = self.snapshot(page)
        page.locator('#resetFence').click()
        self.assertEqual(original['equations'], self.snapshot(page)['equations'])
        self.assertIn('Saved Starter', page.locator('#liveScore').inner_text())
        self.assertFalse(page.locator('#undoFence').is_disabled())
        page.locator('#fenceSvg').focus()
        page.keyboard.press('Meta+z')
        self.assertEqual(second, self.snapshot(page))
        page.keyboard.press('Control+z')
        self.assertEqual(first, self.snapshot(page))
        page.keyboard.press('Control+Shift+z')
        page.keyboard.press('Control+Alt+z')
        self.assertEqual(first, self.snapshot(page))
        page.locator('#undoFence').click()
        self.assertEqual(original, self.snapshot(page))
        page.locator('#resetFence').click()
        self.assertTrue(page.locator('#undoFence').is_disabled())
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()
