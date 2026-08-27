"""Acceptance test for IT-25R1S5 continuing in Demo mode."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@dataclass(frozen=True)
class IdentifiedElement:
    tag: str
    attributes: dict[str, str]
    text: str = ""


class DemoWorkflowParser(HTMLParser):
    """Collect identified controls used by the Demo entry workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: dict[str, IdentifiedElement] = {}
        self.customer_account_fields = 0
        self._active_id: str | None = None
        self._active_tag = ""
        self._active_attributes: dict[str, str] = {}
        self._text_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if attributes.get("name") == "customer_account_id":
            self.customer_account_fields += 1
        element_id = attributes.get("id")
        if element_id is None:
            return
        if tag in {"input", "fieldset"}:
            self.elements[element_id] = IdentifiedElement(
                tag=tag,
                attributes=attributes,
            )
            return
        self._active_id = element_id
        self._active_tag = tag
        self._active_attributes = attributes
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_id is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._active_id is None or tag != self._active_tag:
            return
        self.elements[self._active_id] = IdentifiedElement(
            tag=tag,
            attributes=self._active_attributes,
            text=" ".join("".join(self._text_parts).split()),
        )
        self._active_id = None
        self._active_tag = ""
        self._active_attributes = {}
        self._text_parts = []


def _workflow_markup(html: str) -> DemoWorkflowParser:
    parser = DemoWorkflowParser()
    parser.feed(html)
    return parser


def test_it_25_r1_s5_continues_with_demo_mode_services() -> None:
    """Enter validation without creating or implying an account."""

    landing_response = client.get("/")

    assert landing_response.status_code == 200
    landing = _workflow_markup(landing_response.text)
    continue_action = landing.elements["continue-demo-mode"]
    assert continue_action.text == "Continue in Demo Mode"
    assert continue_action.attributes.get("value") == "continue"
    assert continue_action.attributes.get("data-demo-destination") == (
        "/validation/"
    ), "IT-25R1S5 requires Continue to make validation available."

    script_response = client.get("/assets/js/demo-mode-entry.js")
    assert script_response.status_code == 200
    assert re.search(
        r"addEventListener\(\s*[\"']close[\"']",
        script_response.text,
    ), "IT-25R1S5 requires handling the dialog's Continue result."
    assert "window.location.assign" in script_response.text

    validation_response = client.get(
        continue_action.attributes["data-demo-destination"]
    )

    assert validation_response.status_code == 200
    assert "Demo Mode" in validation_response.text
    validation = _workflow_markup(validation_response.text)
    technical_options = validation.elements[
        "technical-pipeline-selection"
    ]
    assert "hidden" in technical_options.attributes
    appraisal_file = validation.elements["appraisal-file"]
    assert "required" in appraisal_file.attributes
    assert "disabled" not in appraisal_file.attributes
    validate = validation.elements["validate-button"]
    assert validate.text == "Validate Appraisal"
    assert "disabled" not in validate.attributes
    assert validation.customer_account_fields == 0
