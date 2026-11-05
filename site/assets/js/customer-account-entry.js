"use strict";

document.addEventListener("DOMContentLoaded", async () => {
    let context;
    try {
        const response = await fetch("/account/context", {
            credentials: "same-origin", headers: {Accept: "application/json"},
        });
        if (response.status === 401) return;
        if (!response.ok) {
            const error = await response.json();
            const notice = document.getElementById("account-entry-notice");
            notice.textContent = error.detail || "Customer account access could not be loaded.";
            notice.hidden = false;
            return;
        }
        context = await response.json();
    } catch (_) {
        const notice = document.getElementById("account-entry-notice");
        notice.textContent = "Customer account access could not be loaded.";
        notice.hidden = false;
        return;
    }
    const panel = document.getElementById("authenticated-account-entry");
    const user = document.getElementById("authenticated-user");
    user.dataset.userAccountId = context.user_account_id;
    user.textContent = `Signed in as ${context.display_name}`;
    const mode = document.getElementById("operating-mode");
    mode.dataset.operatingMode = context.operating_mode;
    mode.textContent = `${context.operating_mode} mode`;
    panel.hidden = false;

    if (context.operating_mode !== "demo") {
        document.querySelectorAll(".demo-mode-indicator").forEach(item => {
            item.hidden = true;
            item.style.display = "none";
        });
        const disclosure = document.getElementById("demo-mode-disclosure");
        if (disclosure.open) disclosure.close("authenticated");
    }
    const accounts = context.accounts.filter(account => account.can_validate);
    const links = document.getElementById("customer-validation-accounts");
    for (const account of accounts) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.textContent = account.label;
        link.href = `/validation/?${new URLSearchParams({customer_account_id: account.customer_account_id})}`;
        item.append(link);
        links.append(item);
    }
    if (accounts.length) {
        const action = document.getElementById("run-validation-action");
        action.dataset.demoConsentRequired = "false";
        action.href = accounts.length === 1
            ? `/validation/?${new URLSearchParams({customer_account_id: accounts[0].customer_account_id})}`
            : "#authenticated-account-entry";
    }
});
