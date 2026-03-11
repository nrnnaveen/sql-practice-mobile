/* sql_animation.js – SQL Authentication Terminal
 * Handles:
 *   1. Canvas falling SQL/binary stream background
 *   2. Boot-sequence typing animation
 *   3. Login form SQL query animation with AJAX submission
 */

(function () {
    "use strict";

    /* ── 1. CANVAS: falling SQL / binary stream ── */
    var canvas = document.getElementById("sql-canvas");
    var ctx = canvas.getContext("2d");
    var fontSize = 16;
    var columns, drops;

    var sqlFragments = [
        "SELECT", "FROM", "WHERE", "JOIN", "INSERT", "UPDATE", "DELETE",
        "CREATE", "DROP", "ALTER", "INDEX", "TABLE", "VALUES", "INTO",
        "users", "orders", "logs", "sessions", "auth", "email", "id",
        "COUNT(*)", "LIMIT", "GROUP BY", "ORDER BY", "HAVING", "NULL",
        "PRIMARY KEY", "FOREIGN KEY", "NOT NULL", "DEFAULT", "UNIQUE",
        "1", "0", "AND", "OR", "TRUE", "FALSE", ">=", "!=", "=", ";"
    ];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        columns = Math.floor(canvas.width / fontSize);
        drops = [];
        for (var i = 0; i < columns; i++) {
            drops[i] = Math.floor(Math.random() * -canvas.height / fontSize);
        }
    }

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    function drawCanvas() {
        ctx.fillStyle = "rgba(13, 17, 23, 0.2)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.font = fontSize + "px 'Fira Mono', 'Consolas', monospace";
        ctx.shadowColor = "#00ff90";
        ctx.shadowBlur = 8;

        for (var i = 0; i < columns; i++) {
            // Mostly binary chars, occasionally an SQL word
            var text = Math.random() < 0.08
                ? sqlFragments[Math.floor(Math.random() * sqlFragments.length)]
                : (Math.random() < 0.5 ? "1" : "0");

            // Leading character is bright, rest fade
            ctx.fillStyle = drops[i] > 0 ? "#00ff90" : "rgba(0,255,144,0.4)";
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);

            drops[i]++;
            if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                drops[i] = Math.floor(Math.random() * -20);
            }
        }
    }

    setInterval(drawCanvas, 50);

    /* ── 2. BOOT SEQUENCE typing animation ── */
    var bootLines = [
        "Initializing SQL Engine...",
        "Loading Tables...",
        "  users \u2713",
        "  orders \u2713",
        "  transactions \u2713",
        "  logs \u2713",
        "Connecting to Database Server...",
        "Connection Established",
        "Authentication Required"
    ];

    var bootElem = document.getElementById("boot-sequence");
    var loginForm = document.getElementById("login-form");
    var sqlAnimElem = document.getElementById("sql-animation");

    function typeLine(text, container, delay, onDone) {
        var div = document.createElement("div");
        container.appendChild(div);
        var idx = 0;

        function tick() {
            if (idx < text.length) {
                div.textContent += text[idx];
                idx++;
                setTimeout(tick, delay + Math.random() * 20);
            } else {
                setTimeout(onDone, 180);
            }
        }
        tick();
    }

    function runBootSequence(step) {
        if (step < bootLines.length) {
            typeLine(bootLines[step], bootElem, 28, function () {
                runBootSequence(step + 1);
            });
        } else {
            setTimeout(function () {
                bootElem.classList.add("hidden");
                loginForm.classList.remove("hidden");
                var emailInput = document.getElementById("email");
                if (emailInput) { emailInput.focus(); }
            }, 500);
        }
    }

    window.addEventListener("load", function () {
        runBootSequence(0);
    });

    /* ── 3. LOGIN: SQL query animation then AJAX submit ── */
    loginForm.addEventListener("submit", function (e) {
        e.preventDefault();

        var email = document.getElementById("email").value;
        var password = document.getElementById("password").value;
        var maskedPass = "*".repeat(Math.min(password.length, 12));

        loginForm.classList.add("hidden");
        sqlAnimElem.innerHTML = "";
        sqlAnimElem.classList.remove("hidden");

        var queryLines = [
            "SELECT id, email FROM users",
            "WHERE email = '" + email + "'",
            "AND password_hash = '" + maskedPass + "';",
            "",
            "Executing Query...",
            "Checking Credentials..."
        ];

        var lineIdx = 0;

        function typeQueryLines() {
            if (lineIdx < queryLines.length) {
                typeLine(queryLines[lineIdx], sqlAnimElem, 26, function () {
                    lineIdx++;
                    typeQueryLines();
                });
            } else {
                // Submit credentials via AJAX after animation finishes
                setTimeout(submitCredentials, 500);
            }
        }

        typeQueryLines();

        function submitCredentials() {
            var formData = new FormData(loginForm);
            fetch(loginForm.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(function (res) { return res.json(); })
            .then(function (data) { showResult(data.success); })
            .catch(function () { showResult(false); });
        }
    });

    function showResult(success) {
        var resultDiv = document.createElement("div");
        resultDiv.className = success ? "terminal-success" : "terminal-fail";
        sqlAnimElem.appendChild(resultDiv);

        var message = success
            ? "ACCESS GRANTED\nRedirecting to dashboard..."
            : "ERROR 1045: Access denied for user";

        var idx = 0;

        function tick() {
            if (idx < message.length) {
                // Preserve newlines
                resultDiv.textContent = message.slice(0, idx + 1);
                idx++;
                setTimeout(tick, 24 + Math.random() * 16);
            } else if (success) {
                var dashboardUrl = loginForm.dataset.dashboardUrl || "/dashboard";
                setTimeout(function () {
                    window.location.href = dashboardUrl;
                }, 1200);
            } else {
                setTimeout(function () {
                    sqlAnimElem.classList.add("hidden");
                    loginForm.classList.remove("hidden");
                    var emailInput = document.getElementById("email");
                    if (emailInput) { emailInput.focus(); }
                }, 2000);
            }
        }
        tick();
    }

}());
