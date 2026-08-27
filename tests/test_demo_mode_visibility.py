"""Acceptance tests for IT-25R1S2 Demo-mode visibility."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@dataclass(frozen=True)
class DemoModeIndicator:
    text: str
    attributes: dict[str, str]


class DemoModeIndicatorParser(HTMLParser):
    """Collect elements explicitly presented as Demo-mode indicators."""

    def __init__(self) -> None:
        super().__init__()
        self.indicators: list[DemoModeIndicator] = []
        self._depth = 0
        self._attributes: dict[str, str] = {}
        self._text_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = attributes.get("class", "").split()
        if self._depth:
            self._depth += 1
        elif "demo-mode-indicator" in classes:
            self._depth = 1
            self._attributes = attributes
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._depth:
            return
        self._depth -= 1
        if self._depth:
            return
        self.indicators.append(
            DemoModeIndicator(
                text=" ".join("".join(self._text_parts).split()),
                attributes=self._attributes,
            )
        )
        self._attributes = {}
        self._text_parts = []


def _demo_mode_indicators(html: str) -> tuple[DemoModeIndicator, ...]:
    parser = DemoModeIndicatorParser()
    parser.feed(html)
    return tuple(parser.indicators)


@pytest.mark.parametrize(
    "service_page",
    ["/", "/validation/"],
    ids=["landing-page", "report-validation-page"],
)
def test_it_25_r1_s2_makes_demo_mode_visible_on_each_service_page(
    service_page: str,
) -> None:
    """Keep a prominent Demo-mode indicator visible without a dialog."""

    response = client.get(service_page)

    assert response.status_code == 200
    indicators = _demo_mode_indicators(response.text)
    assert len(indicators) == 1, (
        "IT-25R1S2 requires exactly one prominent Demo Mode indicator "
        f"on {service_page}."
    )
    indicator = indicators[0]
    assert indicator.text == "Demo Mode"
    assert "hidden" not in indicator.attributes
    assert indicator.attributes.get("aria-hidden") != "true"
    assert indicator.attributes.get("role") in {"status", "banner"}
