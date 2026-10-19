(function () {
    'use strict';

    function closeYearMenus(except) {
        document.querySelectorAll('[data-year-menu]').forEach(function (menu) {
            if (menu !== except) {
                menu.hidden = true;
                var toggle = menu.parentElement.querySelector('[data-year-menu-toggle]');
                if (toggle) {
                    toggle.setAttribute('aria-expanded', 'false');
                }
            }
        });
    }

    function initYearMenus() {
        document.querySelectorAll('[data-year-menu-toggle]').forEach(function (toggle) {
            var menu = toggle.parentElement.querySelector('[data-year-menu]');
            if (!menu) {
                return;
            }
            toggle.addEventListener('click', function (event) {
                event.stopPropagation();
                var opening = menu.hidden;
                closeYearMenus(opening ? menu : null);
                menu.hidden = !opening;
                toggle.setAttribute('aria-expanded', String(opening));
                if (opening) {
                    var first = menu.querySelector('a');
                    if (first) {
                        first.focus({preventScroll: true});
                    }
                }
            });
            menu.addEventListener('click', function (event) {
                var link = event.target.closest('a[href^="#"]');
                if (link) {
                    var target = document.querySelector(link.getAttribute('href'));
                    if (target) {
                        event.preventDefault();
                        var previousBehavior = document.documentElement.style.scrollBehavior;
                        document.documentElement.style.scrollBehavior = 'auto';
                        target.scrollIntoView({block: 'start'});
                        document.dispatchEvent(new CustomEvent('archive:jump', {
                            detail: {target: target}
                        }));
                        window.requestAnimationFrame(function () {
                            document.documentElement.style.scrollBehavior = previousBehavior;
                        });
                        if (window.history && window.history.replaceState) {
                            window.history.replaceState(null, '', link.getAttribute('href'));
                        }
                    }
                }
                menu.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
            });
        });
        document.addEventListener('click', function () { closeYearMenus(); });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeYearMenus();
            }
        });
    }

    function initTopButton() {
        var button = document.querySelector('[data-back-to-top]');
        if (!button) {
            return;
        }
        function update() {
            button.classList.toggle('is-visible', window.scrollY > 500);
        }
        button.addEventListener('click', function () {
            window.scrollTo({top: 0, behavior: 'smooth'});
        });
        window.addEventListener('scroll', update, {passive: true});
        update();
    }

    function initLifeOnly() {
        var journal = document.querySelector('.noise-journal');
        var enter = document.querySelector('[data-noise-life-only]');
        var exit = document.querySelector('[data-noise-life-exit]');
        if (!journal || !enter || !exit) {
            return;
        }
        function setLifeOnly(enabled) {
            journal.classList.toggle('is-life-only', enabled);
            exit.hidden = !enabled;
            document.body.classList.toggle('noise-life-only-open', enabled);
            if (enabled) {
                exit.focus();
            } else {
                enter.focus();
            }
        }
        enter.addEventListener('click', function () { setLifeOnly(true); });
        exit.addEventListener('click', function () { setLifeOnly(false); });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && journal.classList.contains('is-life-only')) {
                setLifeOnly(false);
            }
        });
    }

    function init() {
        initYearMenus();
        initTopButton();
        initLifeOnly();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
