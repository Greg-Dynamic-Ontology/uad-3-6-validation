"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const disclosure = document.getElementById("demo-mode-disclosure");
    const runValidation = document.getElementById("run-validation-action");
    const continueDemo = document.getElementById("continue-demo-mode");

    if (
        !(disclosure instanceof HTMLDialogElement)
        || !runValidation
        || !continueDemo
    ) {
        return;
    }

    let requestedDestination = null;

    function showDisclosure() {
        disclosure.returnValue = "";

        if (typeof disclosure.showModal === "function") {
            if (disclosure.open) {
                disclosure.close();
            }
            disclosure.showModal();
        } else {
            disclosure.setAttribute("open", "");
        }
    }

    runValidation.addEventListener("click", (event) => {
        if (runValidation.dataset.demoConsentRequired !== "true") {
            return;
        }

        event.preventDefault();
        requestedDestination = runValidation.getAttribute("href");
        showDisclosure();
    });

    disclosure.addEventListener("close", () => {
        // Ignore a close event caused by reopening the initial dialog.
        if (disclosure.open) {
            return;
        }

        if (disclosure.returnValue !== "continue") {
            requestedDestination = null;
            return;
        }

        const destination = (
            requestedDestination
            || continueDemo.dataset.demoDestination
            || "/validation/"
        );
        window.location.assign(destination);
    });

    if (disclosure.open) {
        showDisclosure();
    }
});