"""Acceptance test for IT-25R1S1 initial landing-page actions."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@dataclass(frozen=True)
class PageAction:
    element: str
    label: str
    attributes: dict[str, str]


class PageActionParser(HTMLParser):
    """Collect visible link and button labels with their attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.actions: list[PageAction] = []
        self._element: str | None = None
        self._attributes: dict[str, str] = {}
        self._label_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag not in {"a", "button"}:
            return
        self._element = tag
        self._attributes = {
            name: value or "" for name, value in attrs
        }
        self._label_parts = []

    def handle_data(self, data: str) -> None:
        if self._element is not None:
            self._label_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self._element:
            return
        self.actions.append(
            PageAction(
                element=tag,
                label=" ".join("".join(self._label_parts).split()),
                attributes=self._attributes,
            )
        )
        self._element = None
        self._attributes = {}
        self._label_parts = []


def _page_actions(html: str) -> tuple[PageAction, ...]:
    parser = PageActionParser()
    parser.feed(html)
    return tuple(parser.actions)


def _action_with_label(
    actions: tuple[PageAction, ...],
    label: str,
) -> PageAction:
    matches = tuple(action for action in actions if action.label == label)
    assert len(matches) == 1, (
        f'IT-25R1S1 requires exactly one "{label}" action.'
    )
    return matches[0]


def test_it_25_r1_s1_presents_the_initial_landing_page_actions() -> None:
    """Present primary and secondary actions and reach validation."""

    landing_response = client.get("/")

    assert landing_response.status_code == 200
    landing_actions = _page_actions(landing_response.text)
    run_validation = _action_with_label(
        landing_actions,
        "Run Validation",
    )
    documentation = _action_with_label(
        landing_actions,
        "Documentation",
    )
    assert "service-button--primary" in run_validation.attributes.get(
        "class",
        "",
    ).split()
    assert run_validation.attributes.get("href") == "/validation/"
    assert "service-button--secondary" in documentation.attributes.get(
        "class",
        "",
    ).split()

    validation_response = client.get(
        run_validation.attributes["href"]
    )

    assert validation_response.status_code == 200
    validate = _action_with_label(
        _page_actions(validation_response.text),
        "Validate Appraisal",
    )
    assert validate.element == "button"
