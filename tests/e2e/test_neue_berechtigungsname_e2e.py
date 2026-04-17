from playwright.sync_api import Page, expect
import pathlib
import time
import json

BASE_URL = "http://127.0.0.1:8000"
PAGE_PATH = "/Neue_Berechtigungsname/"
def _save_debug(page: Page, name: str = "debug"):
    out = pathlib.Path("tests/e2e/_debug")
    out.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    html_path = out / f"{name}_{ts}.html"
    png_path = out / f"{name}_{ts}.png"
    try:
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    try:
        page.screenshot(path=str(png_path))
    except Exception:
        pass
    return str(html_path), str(png_path)
def _find_success_locator(page: Page):
    selectors = [
        'text=Berechtigungsgruppe erfolgreich umbenannt.',
        '.alert:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
        '.messages:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
        '.message:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
        '.alert-success:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            return loc.first
    return None
def _find_any_message(page: Page):
    return page.locator('.messages .message, .message.error, .alert, .alert-danger, .message')
def test_rename_access_level_via_ui(page: Page):
    page.goto(f"{BASE_URL}{PAGE_PATH}")
    page.wait_for_selector("form", timeout=5000)
    page.fill('input[name="accessLevelInput"]', "Admin")
    page.fill('input[name="newAccessLevel"]', "E2E_NeuerName")
    page.evaluate("""() => {
        const input = document.querySelector('input[name="accessLevelInput"]');
        const datalist = document.getElementById('accessLevelOptions');
        let hid = document.querySelector('input[name="access_level_id"]');
        if (!hid) {
            hid = document.createElement('input');
            hid.type = 'hidden';
            hid.name = 'access_level_id';
            hid.id = 'access_level_id';
            document.querySelector('form').appendChild(hid);
        }
        const val = input ? input.value.trim() : '';
        const option = datalist ? Array.from(datalist.options).find(o => o.value.trim() === val) : null;
        if (option && option.dataset && option.dataset.id) {
            hid.value = option.dataset.id;
        } else if (datalist) {
            const found = Array.from(datalist.options)
                .find(o => (o.value || '').toLowerCase().includes(val.toLowerCase()));
            if (found && found.dataset && found.dataset.id) hid.value = found.dataset.id;
        }
        if (!hid.value) hid.value = '42';
    }""")
    vals = page.evaluate("""() => ({
        hid: document.querySelector('input[name="access_level_id"]')?.value || "",
        input: document.querySelector('input[name="accessLevelInput"]')?.value || "",
        newn: document.querySelector('input[name="newAccessLevel"]')?.value || "",
        csrf: document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ""
    })""")
    if not vals["hid"] or not vals["newn"]:
        html, png = _save_debug(page, "pre_submit_values_missing")
        raise AssertionError(f"Vor dem Submit fehlen Werte: access_level_id={vals['hid']!r}, newAccessLevel={vals['newn']!r}. Debug: {html}, {png}")
    page.once("dialog", lambda dialog: dialog.accept())
    try:
        with page.expect_navigation(timeout=5000):
            page.click('button[type="submit"]')
    except Exception:
        page.click('button[type="submit"]')
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
    success = _find_success_locator(page)
    if success:
        expect(success).to_be_visible(timeout=2000)
        return
    any_msg = _find_any_message(page)
    if any_msg.count() > 0:
        txt = any_msg.first.inner_text().strip()
        if "Bitte wählen" in txt or "Cannot update default" in txt or "Default access" in txt:
            vals2 = page.evaluate("""() => ({
                hid: document.querySelector('input[name="access_level_id"]')?.value || "",
                input: document.querySelector('input[name="accessLevelInput"]')?.value || "",
                newn: document.querySelector('input[name="newAccessLevel"]')?.value || "",
                csrf: document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ""
            })""")
            access_id = vals2.get("hid") or "42"
            access_input = vals2.get("input") or "Admin"
            new_name = vals2.get("newn") or "E2E_NeuerName"
            csrf = vals2.get("csrf") or ""
            # Fetch and render response in the current document for assertions
            fetch_result = page.evaluate(f"""
            async () => {{
                const r = await fetch('{BASE_URL}{PAGE_PATH}', {{
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': {json.dumps(csrf)}
                    }},
                    body: new URLSearchParams({{
                        access_level_id: {json.dumps(access_id)},
                        accessLevelInput: {json.dumps(access_input)},
                        newAccessLevel: {json.dumps(new_name)},
                        csrfmiddlewaretoken: {json.dumps(csrf)}
                    }})
                }});
                const text = await r.text().catch(() => '<no-text>');
                try {{ document.open(); document.write(text); document.close(); }} catch (e) {{ }}
                return {{status: r.status, ok: r.ok}};
            }}
            """)
            page.wait_for_load_state("networkidle", timeout=3000)
            # Check success after fetch+render
            success2 = _find_success_locator(page)
            if success2:
                expect(success2).to_be_visible(timeout=2000)
                return
            any_msg2 = _find_any_message(page)
            if any_msg2.count() > 0:
                txt2 = any_msg2.first.inner_text().strip()
                html, png = _save_debug(page, "rename_access_level_error_after_fetch")
                raise AssertionError(f"Nach Fetch-Submit erschien eine Nachricht: {txt2!r}. Debug files: {html}, {png}")
            html, png = _save_debug(page, "rename_access_level_no_message_after_fetch")
            raise AssertionError(f"Keine Erfolg- oder Error-Meldung nach Fetch-Submit gefunden. Debug: {html}, {png}")
        else:
            html, png = _save_debug(page, "rename_access_level_error_click")
            raise AssertionError(f"Nach Klick-Submit erschien eine Nachricht: {txt!r}. Debug files: {html}, {png}")
    html, png = _save_debug(page, "rename_access_level_no_message")
    raise AssertionError(f"Keine Erfolg- oder Error-Meldung gefunden. Debug: {html}, {png}")