"""Capture the actual offline report with Playwright, using a local Chromium executable."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", type=Path, required=True)
    p = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets/web"
    assets.mkdir(parents=True, exist_ok=True)
    report = root / "reports/release/policy_report.html"
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(p.browser), headless=True)
        page = browser.new_page(viewport={"width": 1360, "height": 900}, device_scale_factor=1)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(report.as_uri())
        page.get_by_role("heading", name="¿Qué cuentas entran en revisión?").wait_for()
        page.screenshot(path=assets / "decision.png")
        page.get_by_role("link", name="Modelos", exact=True).click()
        assert page.locator("#comparacion tbody tr").count() == 4
        page.screenshot(path=assets / "modelos.png")
        page.get_by_role("link", name="Capacidad", exact=True).click()
        page.get_by_text("Ver calibración por banda", exact=True).click()
        page.locator("#capacidad").evaluate("(el) => el.scrollIntoView()")
        assert page.locator("#capacidad details[open] tbody tr").count() == 10
        page.screenshot(path=assets / "capacidad.png")
        page.get_by_role("link", name="Auditoría", exact=True).click()
        page.get_by_text("Inspeccionar grupos y tamaños", exact=True).click()
        page.locator("#auditoria").evaluate("(el) => el.scrollIntoView()")
        page.screenshot(path=assets / "auditoria.png")
        page.get_by_role("link", name="Seguimiento", exact=True).click()
        assert page.get_by_text("shift:LIMIT_BAL", exact=True).is_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(report.as_uri())
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=assets / "movil.png")
        assert not overflow and not errors
        evidence = {
            "browser": browser.version,
            "mobile_horizontal_overflow": overflow,
            "js_errors": errors,
            "checked": [
                "navigation",
                "4 baselines/models",
                "10 calibration bands",
                "audit",
                "shift alert",
            ],
        }
        (root / "reports/browser.json").write_text(json.dumps(evidence, indent=2), encoding="utf8")
        browser.close()


if __name__ == "__main__":
    run()
