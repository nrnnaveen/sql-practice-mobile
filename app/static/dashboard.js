/* dashboard.js – greeting animation & profile dropdown */
(function () {
    "use strict";

    /* ── Profile avatar dropdown ── */
    var avatarBtn = document.getElementById("avatarBtn");
    var dropdown  = document.getElementById("profileDropdown");

    if (avatarBtn && dropdown) {
        avatarBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            var isOpen = dropdown.classList.toggle("open");
            avatarBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        document.addEventListener("click", function () {
            dropdown.classList.remove("open");
            avatarBtn.setAttribute("aria-expanded", "false");
        });

        dropdown.addEventListener("click", function (e) {
            e.stopPropagation();
        });

        // Keyboard accessibility
        avatarBtn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                avatarBtn.click();
            }
        });
    }

    /* ── Greeting bubble (dashboard page only) ── */
    var bubble = document.getElementById("greetingBubble");
    if (bubble) {
        // Show after a short delay then fade out
        setTimeout(function () {
            bubble.classList.add("show");
        }, 400);

        setTimeout(function () {
            bubble.classList.remove("show");
            bubble.classList.add("hide");
        }, 4000);
    }

}());
