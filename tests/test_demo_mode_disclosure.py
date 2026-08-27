"""Acceptance test for IT-25R1S3 Demo-mode disclosure."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@dataclass(frozen=True)
class DisclosureDialog:
    attributes: dict[str, str]
    text: str
    button_labels: tuple[str, ...]


class DisclosureDialogParser(HTMLParser):
    """Collect the Demo disclosure and the actions presented inside it."""

    def __init__(self) -> None:
        super().__init__()
        self.dialogs: list[DisclosureDialog] = []
        self._dialog_depth = 0
        self._dialog_attributes: dict[str, str] = {}
        self._dialog_text: list[str] = []
        self._button_depth = 0
        self._button_text: list[str] = []
        self._button_labels: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "dialog" and attributes.get("id") == (
            "demo-mode-disclosure"
        ):
            self._dialog_depth = 1
            self._dialog_attributes = attributes
            self._dialog_text = []
            self._button_labels = []
            return
        if not self._dialog_depth:
            return
        self._dialog_depth += 1
        if tag == "button":
            self._button_depth = 1
            self._button_text = []
        elif self._button_depth:
            self._button_depth += 1

    def handle_data(self, data: str) -> None:
        if self._dialog_depth:
            self._dialog_text.append(data)
        if self._button_depth:
            self._button_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._dialog_depth:
            return
        if self._button_depth:
            self._button_depth -= 1
            if not self._button_depth:
                self._button_labels.append(
                    " ".join("".join(self._button_text).split())
                )
        self._dialog_depth -= 1
        if self._dialog_depth:
            return
        self.dialogs.append(
            DisclosureDialog(
                attributes=self._dialog_attributes,
                text=" ".join("".join(self._dialog_text).split()),
                button_labels=tuple(self._button_labels),
            )
        )


def _disclosure_dialogs(html: str) -> tuple[DisclosureDialog, ...]:
    parser = DisclosureDialogParser()
    parser.feed(html)
    return tuple(parser.dialogs)


def test_it_25_r1_s3_explains_demo_mode_limitations() -> None:
    """Require informed consent before unauthenticated Demo-mode entry."""

    response = client.get("/")

    assert response.status_code == 200
    dialogs = _disclosure_dialogs(response.text)
    assert len(dialogs) == 1, (
        "IT-25R1S3 requires one Demo-mode disclosure dialog."
    )
    dialog = dialogs[0]
    assert "open" in dialog.attributes
    assert dialog.attributes.get("aria-modal") == "true"
    disclosure_text = dialog.text.casefold()
    assert "customer-owned validation cycles" in disclosure_text
    assert "account validation history" in disclosure_text
    assert (
        "corrected submissions within an existing cycle"
        in disclosure_text
    )
    assert (
        "purchase, hold, or consume account credits"
        in disclosure_text
    )
    assert dialog.button_labels == (
        "Cancel",
        "Continue in Demo Mode",
    )
