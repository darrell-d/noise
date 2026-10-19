(function () {
    'use strict';

    function updateMediaPreview(input) {
        var preview = document.querySelector('[data-noise-upload-preview]');
        var file = input.files && input.files[0];
        if (!preview || !file || !file.type.startsWith('image/')) {
            if (preview) {
                preview.hidden = true;
                preview.removeAttribute('src');
            }
            return;
        }
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
    }

    document.addEventListener('DOMContentLoaded', function () {
        var media = document.getElementById('id_media');
        if (media) {
            media.addEventListener('change', function () { updateMediaPreview(media); });
        }
    });
}());
