# from playwright.sync_api import Page, expect
# import pathlib
# import time

# BASE_URL = "http://127.0.0.1:8000"
# PAGE_PATH = "/Neue_Berechtigungsname/"  # ggf. anpassen


# def _save_debug(page: Page, name: str = "debug"):
#     out = pathlib.Path("Neue_Berechtigungsname/_debug")
#     out.mkdir(parents=True, exist_ok=True)
#     ts = int(time.time())
#     html_path = out / f"{name}_{ts}.html"
#     png_path = out / f"{name}_{ts}.png"
#     html_path.write_text(page.content(), encoding="utf-8")
#     page.screenshot(path=str(png_path))
#     return str(html_path), str(png_path)


# def test_rename_access_level_via_ui(page: Page):
#     url = f"{BASE_URL}{PAGE_PATH}"

#     page.goto(url)
#     page.wait_for_selector("form", timeout=5000)

#     page.fill('input[name="accessLevelInput"]', "Admin")
#     page.fill('input[name="newAccessLevel"]', "E2E_NeuerName")

#     try:
#         with page.expect_navigation(timeout=5000):
#             page.click('button[type="submit"]')
#     except Exception:
#         page.click('button[type="submit"]')
#         page.wait_for_load_state("networkidle", timeout=5000)

#     selectors = [
#         'text=Berechtigungsgruppe erfolgreich umbenannt.',
#         '.alert:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
#         '.messages:has-text("Berechtigungsgruppe erfolgreich umbenannt.")',
#     ]

#     found = False
#     for sel in selectors:
#         locator = page.locator(sel)
#         try:
#             if locator.count() > 0:
#                 expect(locator).to_be_visible(timeout=3000)
#                 found = True
#                 break
#         except Exception:
#             continue

#     if not found:
#         html_path, png_path = _save_debug(page, "rename_access_level_failure_app")
#         raise AssertionError(
#             "Success message not found. Saved debug files: "
#             f"{html_path}, {png_path}"
#         )