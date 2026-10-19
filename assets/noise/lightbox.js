(function () {
    'use strict';

    var MIN_ZOOM = 1;
    var MAX_ZOOM = 6;
    var ZOOM_STEP = 0.28;
    var modal;
    var card;
    var stage;
    var media;
    var image;
    var text;
    var locationLabel;
    var pulseCanvas;
    var closeButton;
    var lastFocus;
    var scale = 1;
    var panX = 0;
    var panY = 0;
    var dragging = false;
    var dragMoved = false;
    var dragStartX = 0;
    var dragStartY = 0;
    var startPanX = 0;
    var startPanY = 0;

    function applyTransform() {
        image.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + scale + ')';
        image.classList.toggle('is-zoomed', scale > 1);
        media.classList.toggle('is-pannable', scale > 1);
    }

    function resetZoom() {
        scale = 1;
        panX = 0;
        panY = 0;
        dragMoved = false;
        applyTransform();
    }

    function setZoom(nextScale, originX, originY) {
        var previousScale = scale;
        scale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, nextScale));

        if (originX !== undefined && originY !== undefined && previousScale !== scale) {
            var rect = image.getBoundingClientRect();
            var offsetX = originX - rect.left - rect.width / 2;
            var offsetY = originY - rect.top - rect.height / 2;
            var ratio = scale / previousScale;
            panX -= offsetX * (ratio - 1);
            panY -= offsetY * (ratio - 1);
        }

        if (scale === MIN_ZOOM) {
            panX = 0;
            panY = 0;
        }
        applyTransform();
    }

    function copyPulse(sourceCard) {
        var sourceCanvas = sourceCard.querySelector('.noise-value-strip');
        var context = pulseCanvas.getContext('2d');

        pulseCanvas.width = sourceCanvas ? sourceCanvas.width : 1;
        pulseCanvas.height = sourceCanvas ? sourceCanvas.height : 1;
        context.clearRect(0, 0, pulseCanvas.width, pulseCanvas.height);
        if (sourceCanvas) {
            context.drawImage(sourceCanvas, 0, 0);
        }
    }

    function openLightbox(trigger) {
        var sourceCard = trigger.closest('.noise-card');
        var kind = trigger.getAttribute('data-noise-lightbox-kind') || 'text';
        var sourceLocation = sourceCard.querySelector('.noise-location-label');
        var sourceCopy = sourceCard.querySelector('.noise-lightbox-copy');
        var accent = window.getComputedStyle(sourceCard).getPropertyValue('--noise-card-accent');

        lastFocus = document.activeElement;
        card.style.setProperty('--noise-modal-accent', accent);
        locationLabel.textContent = sourceLocation ? sourceLocation.textContent : '';
        text.replaceChildren();
        if (sourceCopy) {
            text.appendChild(sourceCopy.content.cloneNode(true));
        }
        copyPulse(sourceCard);

        modal.classList.toggle('is-image', kind === 'image');
        modal.classList.toggle('is-text', kind === 'text');
        if (kind === 'image') {
            image.src = trigger.getAttribute('data-noise-lightbox-image') || trigger.href;
            var preview = trigger.querySelector('img') || sourceCard.querySelector('.noise-media');
            image.alt = preview ? preview.alt : '';
        } else {
            image.removeAttribute('src');
            image.alt = '';
        }

        resetZoom();
        modal.hidden = false;
        document.body.classList.add('noise-lightbox-open');
        closeButton.focus();
    }

    function closeLightbox() {
        if (!modal || modal.hidden) {
            return;
        }
        modal.hidden = true;
        document.body.classList.remove('noise-lightbox-open');
        image.removeAttribute('src');
        text.replaceChildren();
        if (lastFocus && lastFocus.focus) {
            lastFocus.focus();
        }
    }

    function onModalClick(event) {
        var actionButton = event.target.closest('[data-noise-lightbox-action]');
        if (event.target === modal) {
            closeLightbox();
            return;
        }
        if (!actionButton) {
            return;
        }

        var action = actionButton.getAttribute('data-noise-lightbox-action');
        if (action === 'close') {
            closeLightbox();
        } else if (action === 'zoom-in') {
            setZoom(scale + ZOOM_STEP);
        } else if (action === 'zoom-out') {
            setZoom(scale - ZOOM_STEP);
        } else if (action === 'reset') {
            resetZoom();
        }
    }

    function onWheel(event) {
        if (modal.hidden || !modal.classList.contains('is-image')) {
            return;
        }
        event.preventDefault();
        setZoom(scale + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), event.clientX, event.clientY);
    }

    function onImageClick(event) {
        event.stopPropagation();
        if (dragMoved) {
            dragMoved = false;
            return;
        }
        setZoom(scale < 1.8 ? 2 : 1, event.clientX, event.clientY);
    }

    function onPointerDown(event) {
        if (scale <= 1 || !modal.classList.contains('is-image')) {
            return;
        }
        event.preventDefault();
        dragging = true;
        dragMoved = false;
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        startPanX = panX;
        startPanY = panY;
        stage.setPointerCapture(event.pointerId);
    }

    function onPointerMove(event) {
        if (!dragging) {
            return;
        }
        event.preventDefault();
        panX = startPanX + event.clientX - dragStartX;
        panY = startPanY + event.clientY - dragStartY;
        dragMoved = Math.abs(event.clientX - dragStartX) + Math.abs(event.clientY - dragStartY) > 4;
        applyTransform();
    }

    function onPointerUp() {
        dragging = false;
    }

    function trapFocus(event) {
        var controls = Array.prototype.slice.call(modal.querySelectorAll('button:not([hidden])')).filter(function (button) {
            return window.getComputedStyle(button).display !== 'none';
        });
        if (!controls.length) {
            return;
        }
        var currentIndex = controls.indexOf(document.activeElement);
        var nextIndex = event.shiftKey ? currentIndex - 1 : currentIndex + 1;
        if (nextIndex < 0) {
            nextIndex = controls.length - 1;
        } else if (nextIndex >= controls.length) {
            nextIndex = 0;
        }
        event.preventDefault();
        controls[nextIndex].focus();
    }

    function onKeyDown(event) {
        if (!modal || modal.hidden) {
            return;
        }
        if (event.key === 'Escape') {
            closeLightbox();
        } else if (event.key === 'Tab') {
            trapFocus(event);
        } else if (modal.classList.contains('is-image') && (event.key === '+' || event.key === '=')) {
            setZoom(scale + ZOOM_STEP);
        } else if (modal.classList.contains('is-image') && event.key === '-') {
            setZoom(scale - ZOOM_STEP);
        } else if (modal.classList.contains('is-image') && event.key === '0') {
            resetZoom();
        }
    }

    function init() {
        modal = document.querySelector('[data-noise-lightbox]');
        if (!modal) {
            return;
        }

        card = modal.querySelector('.noise-lightbox-card');
        stage = modal.querySelector('.noise-lightbox-stage');
        media = modal.querySelector('.noise-lightbox-media');
        image = modal.querySelector('.noise-lightbox-image');
        text = modal.querySelector('.noise-lightbox-text');
        locationLabel = modal.querySelector('.noise-lightbox-location');
        pulseCanvas = modal.querySelector('.noise-lightbox-pulse canvas');
        closeButton = modal.querySelector('[data-noise-lightbox-action="close"]');

        document.addEventListener('click', function (event) {
            var trigger = event.target.closest('.noise-lightbox-trigger');
            if (!trigger) {
                return;
            }
            event.preventDefault();
            openLightbox(trigger);
        });
        modal.addEventListener('click', onModalClick);
        modal.addEventListener('wheel', onWheel, {passive: false});
        media.addEventListener('pointerdown', onPointerDown);
        image.addEventListener('click', onImageClick);
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('keydown', onKeyDown);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
