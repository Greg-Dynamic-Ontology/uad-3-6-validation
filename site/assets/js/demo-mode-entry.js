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

    if (typeof disclosure.showModal === "function") {
        if (disclosure.open) {
            disclosure.close();
        }
        disclosure.showModal();
    }

    runValidation.addEventListener("click", (event) => {
        if (disclosure.open) {
            event.preventDefault();
        }
    });

    disclosure.addEventListener("close", () => {
        if (disclosure.returnValue !== "continue") {
            return;
        }
        const continueDestination = continueDemo.dataset.demoDestination;
        if (continueDestination) {
            window.location.assign(continueDestination);
        }
    });
});
