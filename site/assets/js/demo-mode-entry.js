"use strict";

const demoModeDisclosure = document.getElementById("demo-mode-disclosure");
const continueDemoMode = document.getElementById("continue-demo-mode");
const runValidationAction = document.getElementById("run-validation-action");

let requestedDestination = null;

function demoDestination() {
    if (requestedDestination) {
        return requestedDestination;
    }

    if (continueDemoMode) {
        const destination = continueDemoMode.dataset.demoDestination;
        if (destination) {
            return destination;
        }
    }

    return "/validation/";
}

function showDemoModeDisclosure() {
    if (!demoModeDisclosure) {
        return;
    }

    if (typeof demoModeDisclosure.showModal === "function") {
        if (!demoModeDisclosure.open) {
            demoModeDisclosure.showModal();
        }
        return;
    }

    demoModeDisclosure.setAttribute("open", "");
}

if (runValidationAction) {
    runValidationAction.addEventListener("click", (event) => {
        if (runValidationAction.dataset.demoConsentRequired !== "true") {
            return;
        }

        event.preventDefault();
        requestedDestination = runValidationAction.getAttribute("href");
        showDemoModeDisclosure();
    });
}

if (demoModeDisclosure) {
    demoModeDisclosure.addEventListener("close", () => {
        if (demoModeDisclosure.returnValue !== "continue") {
            requestedDestination = null;
            return;
        }

        window.location.assign(demoDestination());
    });
}