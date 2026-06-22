/* profile.js – live avatar preview on file selection */
(function () {
    "use strict";

    var fileInput     = document.getElementById("avatar");
    var previewImg    = document.getElementById("avatarPreviewImg");
    var previewInit   = document.getElementById("avatarPreviewInitials");

    if (!fileInput) { return; }

    fileInput.addEventListener("change", function () {
        var file = fileInput.files && fileInput.files[0];
        if (!file) { return; }

        // Basic client-side type check
        if (!file.type.startsWith("image/")) {
            alert("Please select an image file.");
            fileInput.value = "";
            return;
        }

        var reader = new FileReader();
        reader.onload = function (e) {
            if (previewInit) { previewInit.style.display = "none"; }
            if (previewImg) {
                previewImg.src = e.target.result;
                previewImg.style.display = "block";
            } else {
                // Create the img element if it didn't exist
                var img = document.createElement("img");
                img.id = "avatarPreviewImg";
                img.src = e.target.result;
                img.alt = "Profile picture";
                var wrapper = document.getElementById("avatarPreview");
                if (wrapper) { wrapper.appendChild(img); }
            }
        };
        reader.readAsDataURL(file);
    });

}());
