"""Optional real-browser smoke test; requires Playwright + local Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path(__file__).resolve().parents[1]/'web-v040-preview.png'
static=Path(__file__).resolve().parents[1]/'paperstudio'/'web_static'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1360,'height':1020},device_scale_factor=1)
        html=(static/'index.html').read_text(encoding='utf-8').replace('<link rel="stylesheet" href="/static/style.css"/>','').replace('<script src="/static/app.js"></script>','')
        page.set_content(html)
        page.add_style_tag(content=(static/'style.css').read_text(encoding='utf-8'))
        page.add_script_tag(content=(static/'app.js').read_text(encoding='utf-8'))
        assert page.locator('#engine').count() == 1
        page.locator('#engine').select_option('deepseek')
        assert page.locator('#model').input_value() == 'deepseek-flash'
        assert page.locator('#api_url').input_value() == 'https://api.deepseek.com'
        assert page.locator('#key-row').is_visible()
        page.locator('#api_key').fill('DUMMY-NOT-A-REAL-KEY')
        page.locator('#engine').select_option('argos')
        assert not page.locator('#key-row').is_visible()
        assert page.locator('#api_key').input_value() == ''
        page.locator('#engine').select_option('libretranslate')
        assert page.locator('#api_url').input_value() == 'http://127.0.0.1:5000'
        page.locator('#engine').select_option('deepseek')
        page.screenshot(path=str(out),full_page=True)
        assert page.locator('#test-engine').is_visible()
        browser.close()
    print('CHROMIUM BROWSER SMOKE PASS: controls, models, URLs, secret reset; screenshot: '+str(out))
finally:
    pass
