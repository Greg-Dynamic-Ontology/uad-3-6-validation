"""Acceptance test for IT-25R1S4 cancelling Demo-mode entry."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@dataclass(frozen=True)
class DialogButton:
    label: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class DialogForm:
    attributes: dict[str, str]
    buttons: tuple[DialogButton, ...]
    file_input_count: int


class DemoDialogFormParser(HTMLParser):
    """Collect forms and buttons inside the Demo disclosure dialog."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[DialogForm] = []
        self._inside_dialog = False
        self._inside_form = False
        self._form_attributes: dict[str, str] = {}
        self._buttons: list[DialogButton] = []
        self._inside_button = False
        self._button_attributes: dict[str, str] = {}
        self._button_text: list[str] = []
        self._file_input_count = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "dialog" and attributes.get("id") == (
            "demo-mode-disclosure"
        ):
            self._inside_dialog = True
        elif tag == "form" and self._inside_dialog:
            self._inside_form = True
            self._form_attributes = attributes
            self._buttons = []
            self._file_input_count = 0
        elif tag == "button" and self._inside_form:
            self._inside_button = True
            self._button_attributes = attributes
            self._button_text = []
        elif (
            tag == "input"
            and self._inside_form
            and attributes.get("type") == "file"
        ):
            self._file_input_count += 1

    def handle_data(self, data: str) -> None:
        if self._inside_button:
            self._button_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._inside_button:
            self._buttons.append(
                DialogButton(
                    label=" ".join(
                        "".join(self._button_text).split()
                    ),
                    attributes=self._button_attributes,
                )
            )
            self._inside_button = False
        elif tag == "form" and self._inside_form:
            self.forms.append(
                DialogForm(
                    attributes=self._form_attributes,
                    buttons=tuple(self._buttons),
                    file_input_count=self._file_input_count,
                )
            )
            self._inside_form = False
        elif tag == "dialog" and self._inside_dialog:
            self._inside_dialog = False


def _demo_dialog_forms(html: str) -> tuple[DialogForm, ...]:
    parser = DemoDialogFormParser()
    parser.feed(html)
    return tuple(parser.forms)


def test_it_25_r1_s4_cancels_entry_into_demo_mode() -> None:
    """Close locally without uploading, validating, or navigating."""

    response = client.get("/")

    assert response.status_code == 200
    forms = _demo_dialog_forms(response.text)
    assert len(forms) == 1, (
        "IT-25R1S4 requires the disclosure actions in one dialog form."
    )
    dialog_form = forms[0]
    assert dialog_form.attributes.get("method") == "dialog"
    assert dialog_form.attributes.get("action", "") == ""
    cancel_buttons = tuple(
        button
        for button in dialog_form.buttons
        if button.label == "Cancel"
    )
    assert len(cancel_buttons) == 1
    cancel = cancel_buttons[0]
    assert cancel.attributes.get("type") == "submit"
    assert cancel.attributes.get("value") == "cancel"
    assert "formaction" not in cancel.attributes
    assert dialog_form.file_input_count == 0
