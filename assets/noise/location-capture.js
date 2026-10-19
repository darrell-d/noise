(function () {
    'use strict';

    function isNoiseAddPage() {
        var body = document.body;
        if (!body) {
            return false;
        }
        if (body.classList.contains('change-form')) {
            return body.classList.contains('app-noise')
                && body.classList.contains('model-noise')
                && body.classList.contains('add-form');
        }
        return Boolean(document.querySelector('.noise-editor-journal form.noise-edit-form'))
            && !document.querySelector('#noise-delete-form');
    }

    function setStatus(field, message) {
        var status = document.querySelector('[data-noise-location-status]');
        if (!status) {
            status = document.createElement('small');
            status.setAttribute('data-noise-location-status', '');
            status.setAttribute('aria-live', 'polite');
            status.className = 'noise-location-capture-status';
            field.insertAdjacentElement('afterend', status);
        }
        status.textContent = message;
    }

    function ensureRefreshControl(field, checked) {
        var existing = document.querySelector('[data-noise-location-refresh]');
        if (existing) {
            return existing;
        }

        var control = document.createElement('label');
        var checkbox = document.createElement('input');
        var label = document.createElement('span');
        control.className = 'noise-location-refresh-control';
        control.setAttribute('data-noise-location-refresh-control', '');
        checkbox.type = 'checkbox';
        checkbox.checked = checked;
        checkbox.setAttribute('data-noise-location-refresh', '');
        label.textContent = 'Update location from this device';
        control.appendChild(checkbox);
        control.appendChild(label);
        field.insertAdjacentElement('afterend', control);
        return checkbox;
    }

    function captureLocation(field, checkbox) {
        if (!field) {
            return;
        }
        if (!navigator.geolocation) {
            setStatus(field, 'Device location is unavailable in this browser.');
            checkbox.checked = false;
            return;
        }

        var previousValue = field.value;
        setStatus(field, 'Waiting for device location...');
        navigator.geolocation.getCurrentPosition(
            function (position) {
                var latitude = position.coords.latitude;
                var longitude = position.coords.longitude;
                var invalid = !Number.isFinite(latitude)
                    || !Number.isFinite(longitude)
                    || latitude < -90
                    || latitude > 90
                    || longitude < -180
                    || longitude > 180
                    || (Math.abs(latitude) < 0.0001 && Math.abs(longitude) < 0.0001);
                if (invalid) {
                    field.value = previousValue;
                    checkbox.checked = false;
                    setStatus(field, 'The device returned an invalid location. The existing fallback will be used.');
                    return;
                }
                field.value = latitude.toFixed(6) + ',' + longitude.toFixed(6);
                field.dispatchEvent(new Event('change', {bubbles: true}));
                setStatus(field, 'Device location captured. Image EXIF GPS takes priority.');
            },
            function () {
                checkbox.checked = false;
                setStatus(field, 'Device location was not shared. The existing fallback will be used.');
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000
            }
        );
    }

    function initLocationCapture() {
        var field = document.getElementById('id_location');
        if (!field) {
            return;
        }

        var addPage = isNoiseAddPage();
        var checkbox = ensureRefreshControl(field, addPage);
        checkbox.addEventListener('change', function () {
            if (checkbox.checked) {
                captureLocation(field, checkbox);
            }
        });
        if (addPage) {
            captureLocation(field, checkbox);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLocationCapture);
    } else {
        initLocationCapture();
    }
}());
