document.addEventListener("DOMContentLoaded", function () {

    // Automatically remove flash messages
    setTimeout(function () {

        const flashes = document.querySelectorAll(".flash");

        flashes.forEach(function (flash) {

            flash.style.opacity = "0";

            setTimeout(function () {
                flash.remove();
            }, 500);

        });

    }, 4000);


    // Video story validation
    const videoInputs =
        document.querySelectorAll(
            'input[type="file"][accept*="video"]'
        );

    videoInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            const file = input.files[0];

            if (!file) {
                return;
            }

            const video =
                document.createElement("video");

            video.preload = "metadata";

            video.onloadedmetadata = function () {

                window.URL.revokeObjectURL(
                    video.src
                );

                if (video.duration > 30) {

                    alert(
                        "Videos used for Stories must be 30 seconds or shorter."
                    );

                    input.value = "";

                }

            };

            video.src =
                URL.createObjectURL(file);

        });

    });


    // Image size validation
    const imageInputs =
        document.querySelectorAll(
            'input[type="file"][accept*="image"]'
        );

    imageInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            const file = input.files[0];

            if (!file) {
                return;
            }

            const maxSize =
                2 * 1024 * 1024;

            if (file.size > maxSize) {

                alert(
                    "Images must be 2 MB or smaller."
                );

                input.value = "";

            }

        });

    });

});