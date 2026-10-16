"""Capture the real playgrounds for the home page and README.

Run with Python Playwright and its Chromium browser installed. No network
requests are needed. This writes only the two site/previews PNGs.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'site' / 'previews'
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1100, 'height': 1000}, reduced_motion='reduce')
        page.goto((ROOT / 'site/fences.html').as_uri())
        page.locator('#liveScore').filter(has_text='triangular yards').wait_for()
        page.locator('#viewerShell').screenshot(path=str(output / 'fences.png'))
        page.goto((ROOT / 'site/beaver.html').as_uri())
        page.locator('[data-predict="HALTED"]').click()
        page.locator('#step').click()
        page.locator('#workbench').screenshot(path=str(output / 'robot.png'))
        browser.close()
    print('Captured the fence board and the robot after one step in site/previews/.')


if __name__ == '__main__':
    main()
