(function () {
    'use strict';

    document.documentElement.classList.add('js-noise-layout');

    var layoutTimer = null;
    var PARAMOUR_BACKGROUND_RANDOMIZATION = {
        xMin: 42,
        xSpan: 35,
        yMin: 38,
        ySpan: 40,
        rotationMinMagnitude: 15,
        rotationSpanMagnitude: 31,
        scaleMin: 0.78,
        scaleSpan: 0.48
    };

    function debounce(fn, wait) {
        var timeout = null;
        return function () {
            var args = arguments;
            window.clearTimeout(timeout);
            timeout = window.setTimeout(function () {
                fn.apply(null, args);
            }, wait);
        };
    }

    function getNoiseColumnCount() {
        var width = window.innerWidth || document.documentElement.clientWidth;
        if (width <= 760) {
            return 1;
        }
        if (width <= 1200) {
            return 2;
        }
        return 3;
    }

    function formatBytes(bytes) {
        var size = Number(bytes) || 0;
        var gib = Math.pow(1024, 3);
        var mib = Math.pow(1024, 2);
        var value = size >= gib ? size / gib : size / mib;
        var unit = size >= gib ? 'GiB' : 'MiB';
        return (Math.round(value * 10) / 10) + ' ' + unit;
    }

    function hashNoiseWindow(source, index, salt) {
        var hash = 2166136261 ^ salt;
        var length = source.length;

        if (!length) {
            return hash >>> 0;
        }

        for (var offset = 0; offset < 11; offset += 1) {
            var charCode = source.charCodeAt((index + offset * 17 + salt) % length);
            hash ^= charCode + offset + salt;
            hash = Math.imul(hash, 16777619);
        }
        return hash >>> 0;
    }

    function noiseColor(hash) {
        var palette = [28, 12, 130, 210, 45, 350, 278, 185];
        var hue = palette[hash % palette.length];
        var saturation = 68 + ((hash >>> 8) % 25);
        var lightness = 48 + ((hash >>> 16) % 18);
        return 'hsl(' + hue + ' ' + saturation + '% ' + lightness + '%)';
    }

    function drawNoiseValueStrip(canvas) {
        var context = canvas.getContext('2d');
        var rect = canvas.getBoundingClientRect();
        var pixelRatio = window.devicePixelRatio || 1;
        var width = Math.max(1, Math.floor(rect.width * pixelRatio));
        var height = Math.max(1, Math.floor(rect.height * pixelRatio));
        var source = canvas.getAttribute('data-noise-value') || 'NOISE';
        var columnWidth = Math.max(2, Math.round(4 * pixelRatio));

        if (canvas.width !== width || canvas.height !== height) {
            canvas.width = width;
            canvas.height = height;
        }

        context.clearRect(0, 0, width, height);
        for (var x = 0; x < width; x += columnWidth) {
            var sourceIndex = Math.floor((x / width) * source.length);
            var hash = hashNoiseWindow(source, sourceIndex, x);
            context.fillStyle = noiseColor(hash);
            context.fillRect(x, 0, Math.min(columnWidth, width - x), height);
        }
    }

    function drawNoiseHeartStrip(strip) {
        var rect = strip.getBoundingClientRect();
        var width = Math.max(1, Math.floor(rect.width || 280));
        var source = strip.getAttribute('data-noise-value') || 'NOISE';
        var heartWidth = 14;
        var count = Math.max(1, Math.ceil(width / heartWidth));
        var html = '';

        for (var index = 0; index < count; index += 1) {
            var sourceIndex = Math.floor((index / count) * source.length);
            var hash = hashNoiseWindow(source, sourceIndex, index * 31);
            var color = noiseColor(hash);
            html += '<svg viewBox="0 0 16 16" focusable="false" aria-hidden="true" style="color:' + color + '">' +
                '<path fill="currentColor" d="M8 14.2 6.9 13.1C2.8 9.4 1 7.7 1 5.1 1 3 2.6 1.4 4.7 1.4c1.2 0 2.4.6 3.1 1.5.7-.9 1.9-1.5 3.1-1.5C13 1.4 14.6 3 14.6 5.1c0 2.6-1.8 4.3-5.9 8L8 14.2Z"/>' +
                '</svg>';
        }

        strip.innerHTML = html;
    }

    function randomizeParamourCard(card) {
        var background = card.querySelector('.noise-paramour-background');
        if (!background) {
            return;
        }
        var source = card.getAttribute('data-noise-date') || card.id || 'paramour';
        var nowSalt = Date.now() + Math.floor(Math.random() * 100000);
        var hash = hashNoiseWindow(source, 0, nowSalt);
        var rotationDirection = (hash >>> 7) % 2 === 0 ? -1 : 1;
        var rotationMagnitude = PARAMOUR_BACKGROUND_RANDOMIZATION.rotationMinMagnitude +
            ((hash >>> 16) % PARAMOUR_BACKGROUND_RANDOMIZATION.rotationSpanMagnitude);
        var x = PARAMOUR_BACKGROUND_RANDOMIZATION.xMin +
            (hash % PARAMOUR_BACKGROUND_RANDOMIZATION.xSpan);
        var y = PARAMOUR_BACKGROUND_RANDOMIZATION.yMin +
            ((hash >>> 8) % PARAMOUR_BACKGROUND_RANDOMIZATION.ySpan);
        var rotation = rotationDirection * rotationMagnitude;
        var scale = PARAMOUR_BACKGROUND_RANDOMIZATION.scaleMin +
            (((hash >>> 24) % 100) / 100) * PARAMOUR_BACKGROUND_RANDOMIZATION.scaleSpan;

        background.style.setProperty('--noise-paramour-bg-x', x + '%');
        background.style.setProperty('--noise-paramour-bg-y', y + '%');
        background.style.setProperty('--noise-paramour-bg-rotate', rotation + 'deg');
        background.style.setProperty('--noise-paramour-bg-scale', scale.toFixed(2));
    }

    function initNoiseValueStrips() {
        var valueStrips = Array.prototype.slice.call(document.querySelectorAll('canvas[data-noise-value]'));
        var heartStrips = Array.prototype.slice.call(document.querySelectorAll('[data-noise-heart-strip]'));
        var paramourCards = Array.prototype.slice.call(document.querySelectorAll('.noise-card--paramour'));

        if (!valueStrips.length && !heartStrips.length && !paramourCards.length) {
            return;
        }

        function drawAll() {
            valueStrips.forEach(drawNoiseValueStrip);
            heartStrips.forEach(drawNoiseHeartStrip);
        }

        paramourCards.forEach(randomizeParamourCard);
        drawAll();
        window.addEventListener('resize', debounce(drawAll, 120));
    }

    function readNoiseLifeSeeds() {
        var element = document.getElementById('noise-life-seeds');
        if (!element) {
            return [];
        }
        try {
            var seeds = JSON.parse(element.textContent || '[]');
            return Array.isArray(seeds) ? seeds.filter(function (seed) {
                return typeof seed === 'string' && seed.length;
            }).slice(0, 3) : [];
        } catch (error) {
            return [];
        }
    }

    function initNoiseLifeBackground() {
        var canvas = document.querySelector('[data-noise-life]');
        var counter = document.querySelector('[data-noise-generation]');
        if (!canvas || typeof window.startNoiseLife !== 'function') {
            return;
        }

        var stop = null;
        var seeds = readNoiseLifeSeeds();
        function updateGeneration(generation) {
            if (!counter) {
                return;
            }
            var hex = Math.max(0, generation).toString(16).toUpperCase();
            counter.textContent = '0x' + hex.padStart(4, '0');
        }
        function sizeAndStart() {
            if (stop) {
                stop();
            }
            canvas.width = Math.max(1, window.innerWidth);
            canvas.height = Math.max(1, window.innerHeight);
            stop = window.startNoiseLife(canvas, {
                cell: 24,
                seeds: seeds,
                step: 260,
                settleDelay: 2500,
                onGeneration: updateGeneration
            });
        }

        sizeAndStart();
        window.addEventListener('resize', debounce(sizeAndStart, 180));
        window.addEventListener('pagehide', function () {
            if (stop) {
                stop();
            }
        }, {once: true});
    }

    function layoutNoiseRoll(roll) {
        var cards = Array.prototype.slice.call(roll.children).filter(function (child) {
            return child.classList && child.classList.contains('noise-card');
        });
        if (!cards.length) {
            roll.classList.add('is-ready');
            return;
        }

        var computed = window.getComputedStyle(roll);
        var rowHeight = parseFloat(computed.getPropertyValue('--noise-row-height')) || 8;
        var rowGap = parseFloat(computed.rowGap || computed.gap || 0) || 0;
        roll.style.setProperty('--noise-columns', getNoiseColumnCount());

        cards.forEach(function (card) {
            card.style.gridRowEnd = 'span 1';
        });
        roll.offsetHeight;

        cards.forEach(function (card) {
            var inner = card.querySelector('.noise-card-inner') || card;
            var height = inner.scrollHeight || inner.getBoundingClientRect().height || 0;
            var span = Math.max(1, Math.ceil((height + rowGap) / (rowHeight + rowGap)));
            card.style.gridRowEnd = 'span ' + span;
        });

        roll.classList.add('is-ready');
    }

    function layoutNoiseRolls() {
        Array.prototype.slice.call(document.querySelectorAll('.noise-roll')).forEach(layoutNoiseRoll);
    }

    function scheduleLayout() {
        window.clearTimeout(layoutTimer);
        layoutTimer = window.setTimeout(layoutNoiseRolls, 50);
    }

    function wireMedia(roll) {
        Array.prototype.slice.call(roll.querySelectorAll('img, video')).forEach(function (media) {
            media.addEventListener('load', scheduleLayout);
            media.addEventListener('loadedmetadata', scheduleLayout);
            if (media.tagName === 'IMG' && media.complete) {
                scheduleLayout();
            }
            if (media.tagName === 'VIDEO' && media.readyState >= 1) {
                scheduleLayout();
            }
        });
    }

    function revealLazyMedia(media) {
        media.classList.add('is-loaded');
        scheduleLayout();
    }

    function loadLazyMedia(media) {
        var src = media.getAttribute('data-noise-lazy-src');
        if (!src) {
            revealLazyMedia(media);
            return;
        }

        if (media.tagName === 'VIDEO') {
            media.addEventListener('loadedmetadata', function () { revealLazyMedia(media); }, {once: true});
            media.addEventListener('error', function () { revealLazyMedia(media); }, {once: true});
            media.src = src;
            media.removeAttribute('data-noise-lazy-src');
            media.load();
            return;
        }

        media.addEventListener('load', function () { revealLazyMedia(media); }, {once: true});
        media.addEventListener('error', function () { revealLazyMedia(media); }, {once: true});
        media.src = src;
        media.removeAttribute('data-noise-lazy-src');
        if (media.complete) {
            revealLazyMedia(media);
        }
    }

    function initLazyMedia() {
        var lazyMedia = Array.prototype.slice.call(document.querySelectorAll('.noise-lazy[data-noise-lazy-src]'));
        if (!lazyMedia.length) {
            return;
        }

        if (!('IntersectionObserver' in window)) {
            lazyMedia.forEach(loadLazyMedia);
            return;
        }

        var observer = new IntersectionObserver(function (entries, currentObserver) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    loadLazyMedia(entry.target);
                    currentObserver.unobserve(entry.target);
                }
            });
        }, {rootMargin: '300px 0px'});

        lazyMedia.forEach(function (media) {
            observer.observe(media);
        });
    }

    function previewUploadedMedia() {
        var input = document.getElementById('id_media');
        var preview = document.getElementById('uploaded_media');
        var type = document.getElementById('id_noise_content_type');

        if (!input) {
            return;
        }

        input.addEventListener('change', function () {
            var file = input.files && input.files[0];
            if (!file) {
                return;
            }

            var maxUpload = parseInt(input.getAttribute('data-max-upload-bytes'), 10);
            if (maxUpload && file.size > maxUpload) {
                var maxUploadLabel = input.getAttribute('data-max-upload-label') || formatBytes(maxUpload);
                window.alert('Noise uploads are limited to ' + maxUploadLabel + '. This file is ' + formatBytes(file.size) + '.');
                input.value = '';
                if (preview) {
                    preview.style.display = 'none';
                    preview.removeAttribute('src');
                }
                return;
            }

            var extension = file.name.split('.').pop().toLowerCase();
            if (type) {
                if (['jpeg', 'jpg', 'gif', 'png', 'bmp', 'tif', 'tiff', 'webp'].includes(extension)) {
                    type.value = 'image';
                } else if (['mp4', 'mov', 'm4v', 'webm', 'avi', 'mkv'].includes(extension)) {
                    type.value = 'video';
                } else if (['pdf', 'zip', 'rar', '7z', 'txt', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(extension)) {
                    type.value = 'downloadable';
                }
            }

            if (!preview || !file.type.startsWith('image/')) {
                if (preview) {
                    preview.style.display = 'none';
                    preview.removeAttribute('src');
                }
                return;
            }

            var reader = new FileReader();
            reader.onload = function (event) {
                preview.src = event.target.result;
                preview.style.width = '300px';
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    function initLoginDialog() {
        var dialog = document.querySelector('[data-noise-login-dialog]');
        var openButtons = document.querySelectorAll('[data-noise-login-open]');
        if (!dialog || !openButtons.length) {
            return;
        }

        var closeButton = dialog.querySelector('[data-noise-login-close]');
        var status = dialog.querySelector('[data-noise-login-status]');

        openButtons.forEach(function (openButton) {
            openButton.addEventListener('click', function () {
                if (typeof dialog.showModal === 'function') {
                    dialog.showModal();
                } else {
                    dialog.setAttribute('open', '');
                }
            });
        });

        function closeDialog() {
            if (typeof dialog.close === 'function') {
                dialog.close();
            } else {
                dialog.removeAttribute('open');
            }
            if (status) {
                status.textContent = '';
            }
        }

        if (closeButton) {
            closeButton.addEventListener('click', closeDialog);
        }

        dialog.addEventListener('click', function (event) {
            if (event.target === dialog) {
                closeDialog();
            }
        });

        if (status && status.textContent.trim()) {
            if (typeof dialog.showModal === 'function') {
                dialog.showModal();
            } else {
                dialog.setAttribute('open', '');
            }
        }
    }

    function init() {
        previewUploadedMedia();
        initLoginDialog();
        initNoiseLifeBackground();
        initNoiseValueStrips();

        var rolls = Array.prototype.slice.call(document.querySelectorAll('.noise-roll'));
        rolls.forEach(wireMedia);
        initLazyMedia();
        layoutNoiseRolls();

        window.addEventListener('resize', debounce(layoutNoiseRolls, 150));
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(scheduleLayout).catch(function () {});
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
