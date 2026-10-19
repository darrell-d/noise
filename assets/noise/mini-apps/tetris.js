(function (window) {
    'use strict';

    var MANUAL_IDLE_MS = 15000;
    var AI_GAME_OVER_DELAY_MS = 2400;
    var MANUAL_GAME_OVER_DELAY_MS = 5000;
    var SCORE_SAVED_DELAY_MS = 1800;
    var START_SPEED = 8;
    var MAX_SPEED = 30;
    var SCORE_SPEED_STEP = 800;
    var TAP_DELAY_MS = 260;
    var SWIPE_THRESHOLD = 26;

    var TETRIS_STYLES = [
        ':host { display: block; min-height: 540px; contain: content; outline: none; touch-action: none; }',
        '.shell { position: relative; display: grid; place-items: center; min-height: 540px; padding: 18px; overflow: hidden; background: #101c2c; cursor: pointer; }',
        '.frame { position: relative; width: min(100%, 264px); aspect-ratio: 1 / 2; border: 1px solid #304966; background: #0b1524; box-shadow: 8px 8px 0 rgba(5, 13, 24, 0.32); transition: border-color 100ms linear, box-shadow 100ms linear; }',
        ':host(:focus-visible) .frame, :host([data-mode="manual"]) .frame { border-color: #f2a950; box-shadow: 8px 8px 0 rgba(5, 13, 24, 0.32), 0 0 0 2px rgba(242, 169, 80, 0.24); }',
        '.game, .blockrain-game-holder, canvas { width: 100% !important; height: 100% !important; }',
        '.blockrain-score-holder { top: 10px; right: 10px; color: #eef3f9; font-family: "Silkscreen", monospace; text-shadow: 1px 1px #0b1524; }',
        '.blockrain-score-msg { color: #6f89a6; font-size: 9px; }',
        '.blockrain-score-num { font-size: 13px; }',
        '.blockrain-start-holder, .blockrain-game-over-holder, .blockrain-touch { display: none !important; }',
        '.message { position: absolute; z-index: 4; left: 50%; display: none; width: max-content; max-width: calc(100% - 24px); transform: translateX(-50%); border: 1px solid #304966; background: rgba(11, 21, 36, 0.94); color: #eef3f9; font-family: "IBM Plex Mono", monospace; font-size: 10px; font-weight: 600; line-height: 1.35; letter-spacing: 0; text-align: center; }',
        '.takeover { bottom: 30px; padding: 10px 13px; color: #f2a950; }',
        '.manual-prompt { top: 12px; padding: 7px 10px; pointer-events: none; }',
        '.game-over { top: 50%; min-width: 190px; padding: 18px; transform: translate(-50%, -50%); cursor: default; }',
        '.game-over strong, .game-over span { display: block; }',
        '.game-over strong { margin-bottom: 8px; color: #f2a950; font-family: "Silkscreen", monospace; font-size: 15px; }',
        '.game-over span { color: #8da3bc; }',
        '.game-over button, .scores-toggle, .leaderboard button { padding: 8px 11px; border: 1px solid #f2a950; border-radius: 0; background: #0b1524; color: #f2a950; font: inherit; cursor: pointer; }',
        '.game-over > button { margin-top: 14px; }',
        '.score-form { display: none; margin-top: 14px; }',
        '.score-form.is-visible { display: grid; gap: 8px; }',
        '.score-form label { color: #8da3bc; font-size: 9px; text-align: left; }',
        '.score-form input { box-sizing: border-box; width: 100%; margin-top: 4px; padding: 8px; border: 1px solid #304966; border-radius: 0; outline: 0; background: #101c2c; color: #eef3f9; font: inherit; text-transform: uppercase; }',
        '.score-form input:focus { border-color: #f2a950; }',
        '.high-score { position: absolute; z-index: 3; top: 10px; left: 10px; color: #6f89a6; font-family: "Silkscreen", monospace; font-size: 9px; }',
        '.scores-toggle { position: absolute; z-index: 3; bottom: 8px; left: 8px; padding: 6px 8px; border-color: #304966; color: #8da3bc; font-size: 9px; }',
        '.leaderboard { position: absolute; z-index: 6; inset: 18px; display: none; padding: 16px; border: 1px solid #304966; background: rgba(11, 21, 36, 0.98); color: #eef3f9; cursor: default; }',
        ':host([data-scores-open]) .leaderboard { display: block; }',
        '.leaderboard header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; color: #f2a950; font-family: "Silkscreen", monospace; font-size: 14px; }',
        '.leaderboard button { padding: 4px 7px; }',
        '.leaderboard ol { margin: 0; padding: 0; list-style: none; counter-reset: rank; font-family: "IBM Plex Mono", monospace; font-size: 10px; }',
        '.leaderboard li { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 8px; padding: 5px 0; border-bottom: 1px solid rgba(48, 73, 102, 0.45); counter-increment: rank; }',
        '.leaderboard li::before { content: counter(rank, decimal-leading-zero); color: #6f89a6; }',
        '.leaderboard li span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }',
        '.leaderboard li strong { color: #f2a950; font-weight: 500; }',
        '.leaderboard-empty { color: #6f89a6; font-family: "IBM Plex Mono", monospace; font-size: 10px; }',
        ':host([data-state="playing"][data-mode="ai"]) .takeover, :host([data-state="playing"][data-mode="manual"]) .manual-prompt, :host([data-state="game-over"]) .game-over { display: block; }',
        '@media (max-width: 520px) { :host, .shell { min-height: 470px; } .frame { width: min(100%, 220px); } }'
    ].join('');

    var TETRIS_THEME = {
        background: '#0b1524',
        backgroundGrid: '#14243a',
        primary: null,
        secondary: null,
        stroke: '#0b1524',
        innerStroke: '#24364e',
        blocks: {
            line: '#4f8fc4',
            square: '#d6ad45',
            arrow: '#d35d72',
            rightHook: '#c97852',
            leftHook: '#6f89a6',
            rightZag: '#4da864',
            leftZag: '#f2a950'
        }
    };

    class NoiseTetrisApp extends HTMLElement {
        constructor() {
            super();
            this._game = null;
            this._instance = null;
            this._observer = null;
            this._manualTimer = null;
            this._gameOverTimer = null;
            this._dropTimer = null;
            this._tapTimer = null;
            this._pointer = null;
            this._scores = [];
            this._scoresUrl = '';
            this._isVisible = false;
            this._isManual = false;
            this._reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            this._handleKeyDown = this._handleKeyDown.bind(this);
            this._handleKeyUp = this._handleKeyUp.bind(this);
            this._handlePointerDown = this._handlePointerDown.bind(this);
            this._handlePointerUp = this._handlePointerUp.bind(this);
            this._handlePointerCancel = this._handlePointerCancel.bind(this);
            this._handleVisibility = this._handleVisibility.bind(this);
            this._handleRestartClick = this._handleRestartClick.bind(this);
            this._handleScoresToggle = this._handleScoresToggle.bind(this);
            this._handleScoreSubmit = this._handleScoreSubmit.bind(this);
        }

        connectedCallback() {
            if (this.shadowRoot) {
                return;
            }

            this.tabIndex = 0;
            this.setAttribute('role', 'application');
            this.setAttribute('data-mode', 'ai');
            this.setAttribute('data-state', 'playing');
            this.setAttribute('aria-label', 'AI playing Tetris. Focus to take control.');

            var shadow = this.attachShadow({mode: 'open'});
            shadow.innerHTML = '<style>' + TETRIS_STYLES + '</style><section class="shell"><div class="frame"><div class="game"></div><span class="high-score" data-high-score>HI 000000</span><button class="scores-toggle" type="button" data-scores-toggle data-ignore-takeover>TOP 10</button><div class="message takeover">CLICK TO PLAY</div><div class="message manual-prompt">YOUR TURN &middot; WASD / ARROWS &middot; SPACE ROTATES</div><div class="message game-over"><strong>GAME OVER</strong><span data-game-over-message>REBOOTING AI</span><form class="score-form" data-score-form data-ignore-takeover><label>NAME<input name="name" maxlength="16" autocomplete="nickname" required></label><button type="submit">SAVE SCORE</button></form><button type="button" data-restart data-ignore-takeover>PLAY AGAIN</button></div><section class="leaderboard" data-leaderboard data-ignore-takeover><header><span>TOP 10</span><button type="button" data-scores-toggle data-ignore-takeover aria-label="Close high scores">X</button></header><ol data-scores-list></ol><p class="leaderboard-empty" data-scores-empty>NO SCORES YET</p></section></div></section>';
            var game = shadow.querySelector('.game');
            this._scoresUrl = this.getAttribute('data-scores-url') || '';

            if (!window.jQuery || typeof window.jQuery.fn.blockrain !== 'function') {
                this.setAttribute('data-mini-app-error', 'engine-unavailable');
                return;
            }

            this._game = window.jQuery(game);
            this._game.blockrain({
                autoplay: true,
                autoplayRestart: false,
                showFieldOnStart: true,
                theme: TETRIS_THEME,
                difficulty: 'normal',
                speed: START_SPEED,
                scoreText: 'SCORE',
                onGameOver: this._handleGameOver.bind(this),
                onLine: function (_lines, _points, score) {
                    this._setSpeedFromScore(score);
                }.bind(this)
            });
            this._instance = this._game.blockrain('instance');
            this._installSevenBag();
            this._instance._board.next = null;
            this._game.blockrain('restart');

            this.addEventListener('pointerdown', this._handlePointerDown);
            this.addEventListener('pointerup', this._handlePointerUp);
            this.addEventListener('pointercancel', this._handlePointerCancel);
            shadow.querySelector('[data-restart]').addEventListener('click', this._handleRestartClick);
            shadow.querySelectorAll('[data-scores-toggle]').forEach(function (button) {
                button.addEventListener('click', this._handleScoresToggle);
            }.bind(this));
            shadow.querySelector('[data-score-form]').addEventListener('submit', this._handleScoreSubmit);
            document.addEventListener('visibilitychange', this._handleVisibility);
            this._loadScores();

            if ('IntersectionObserver' in window) {
                this._observer = new IntersectionObserver(function (entries) {
                    this._isVisible = entries[0].isIntersecting;
                    this._syncPlayback();
                }.bind(this), {rootMargin: '120px'});
                this._observer.observe(this);
            } else {
                this._isVisible = true;
            }
            this._syncPlayback();
        }

        disconnectedCallback() {
            if (this._observer) {
                this._observer.disconnect();
            }
            window.clearTimeout(this._manualTimer);
            window.clearTimeout(this._gameOverTimer);
            window.clearTimeout(this._tapTimer);
            window.clearInterval(this._dropTimer);
            document.removeEventListener('visibilitychange', this._handleVisibility);
            window.removeEventListener('keydown', this._handleKeyDown);
            window.removeEventListener('keyup', this._handleKeyUp);
            this.removeEventListener('pointerdown', this._handlePointerDown);
            this.removeEventListener('pointerup', this._handlePointerUp);
            this.removeEventListener('pointercancel', this._handlePointerCancel);
            if (this._game) {
                this._game.blockrain('pause');
            }
        }

        _board() {
            return this._instance && this._instance._board;
        }

        _currentPiece() {
            var board = this._board();
            return board && !board.gameover ? board.cur : null;
        }

        _installSevenBag() {
            if (!this._instance || !this._instance._shapeFactory) {
                return;
            }
            var factories = this._instance._shapeFactory;
            var bag = [];
            this._instance._randomShapes = function () {
                if (!bag.length) {
                    bag = Object.keys(factories);
                    for (var index = bag.length - 1; index > 0; index -= 1) {
                        var swapIndex = Math.floor(Math.random() * (index + 1));
                        var key = bag[index];
                        bag[index] = bag[swapIndex];
                        bag[swapIndex] = key;
                    }
                }
                return factories[bag.pop()];
            };
        }

        _setMode(mode) {
            var manual = mode === 'manual';
            this._isManual = manual;
            this.setAttribute('data-mode', mode);
            this.setAttribute('aria-label', manual ? 'Tetris under your control.' : 'AI playing Tetris. Focus to take control.');
            var card = this.closest('[data-noise-mini-app="tetris"]');
            var label = card && card.querySelector('[data-tetris-mode]');
            if (label) {
                label.textContent = manual ? 'MANUAL' : 'AI';
            }
        }

        _setSpeedFromScore(score) {
            if (!this._game) {
                return START_SPEED;
            }
            var level = Math.floor(Math.max(0, Number(score) || 0) / SCORE_SPEED_STEP);
            var speed = Math.min(MAX_SPEED, START_SPEED + level * 2);
            this._game.blockrain('option', 'speed', speed);
            return speed;
        }

        _activateManual() {
            if (!this._game) {
                return;
            }
            if (!this._isManual) {
                this._game.blockrain('autoplay', false);
                this._game.blockrain('controls', false);
                this._setMode('manual');
                window.addEventListener('keydown', this._handleKeyDown);
                window.addEventListener('keyup', this._handleKeyUp);
                this._game.blockrain('restart');
                this._setSpeedFromScore(0);
                this.setAttribute('data-state', 'playing');
            }
            this._resetManualTimer();
        }

        _resumeAI(restart) {
            if (!this._game) {
                return;
            }
            window.clearTimeout(this._manualTimer);
            window.clearTimeout(this._gameOverTimer);
            this._clearHeldControls();
            window.removeEventListener('keydown', this._handleKeyDown);
            window.removeEventListener('keyup', this._handleKeyUp);
            this._game.blockrain('autoplay', true);
            if (restart) {
                this._game.blockrain('restart');
                this._setSpeedFromScore(0);
            }
            this._setMode('ai');
            this.setAttribute('data-state', 'playing');
            this._syncPlayback();
        }

        _handleGameOver(score) {
            var wasManual = this._isManual;
            var message = this.shadowRoot && this.shadowRoot.querySelector('[data-game-over-message]');
            var form = this.shadowRoot && this.shadowRoot.querySelector('[data-score-form]');
            this.setAttribute('data-state', 'game-over');
            window.clearTimeout(this._manualTimer);
            window.removeEventListener('keydown', this._handleKeyDown);
            window.removeEventListener('keyup', this._handleKeyUp);
            if (form) {
                form.classList.remove('is-visible');
                form.dataset.score = String(score || 0);
            }
            if (message) {
                message.textContent = wasManual ? 'SCORE ' + String(score || 0) + ' · AI RESUMES IN 5 SECONDS' : 'REBOOTING AI';
            }
            window.clearTimeout(this._gameOverTimer);
            if (wasManual && this._qualifiesForHighScore(score)) {
                if (message) {
                    message.textContent = 'TOP 10 · ENTER YOUR NAME';
                }
                if (form) {
                    form.classList.add('is-visible');
                    window.setTimeout(function () {
                        form.querySelector('input').focus({preventScroll: true});
                    }, 0);
                }
                return;
            }
            this._gameOverTimer = window.setTimeout(function () {
                this._resumeAI(true);
            }.bind(this), wasManual ? MANUAL_GAME_OVER_DELAY_MS : AI_GAME_OVER_DELAY_MS);
        }

        _handleRestartClick(event) {
            event.stopPropagation();
            window.clearTimeout(this._gameOverTimer);
            this._game.blockrain('autoplay', false);
            this._game.blockrain('restart');
            this._setSpeedFromScore(0);
            this.setAttribute('data-state', 'playing');
            this._activateManual();
            this.focus({preventScroll: true});
        }

        _qualifiesForHighScore(score) {
            var value = Number(score) || 0;
            return value > 0 && (this._scores.length < 10 || value > this._scores[this._scores.length - 1].score);
        }

        _loadScores() {
            if (!this._scoresUrl || typeof window.fetch !== 'function') {
                return Promise.resolve([]);
            }
            return window.fetch(this._scoresUrl, {credentials: 'same-origin'})
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Could not load Tetris scores.');
                    }
                    return response.json();
                })
                .then(function (payload) {
                    this._scores = Array.isArray(payload.scores) ? payload.scores : [];
                    this._renderScores();
                    return this._scores;
                }.bind(this))
                .catch(function () {
                    return [];
                });
        }

        _renderScores() {
            if (!this.shadowRoot) {
                return;
            }
            var list = this.shadowRoot.querySelector('[data-scores-list]');
            var empty = this.shadowRoot.querySelector('[data-scores-empty]');
            var high = this.shadowRoot.querySelector('[data-high-score]');
            list.replaceChildren();
            this._scores.forEach(function (entry) {
                var item = document.createElement('li');
                var name = document.createElement('span');
                var score = document.createElement('strong');
                name.textContent = entry.name;
                score.textContent = String(entry.score).padStart(6, '0');
                item.append(name, score);
                list.appendChild(item);
            });
            empty.hidden = this._scores.length > 0;
            high.textContent = 'HI ' + String(this._scores.length ? this._scores[0].score : 0).padStart(6, '0');
        }

        _handleScoresToggle(event) {
            event.stopPropagation();
            if (this.hasAttribute('data-scores-open')) {
                this.removeAttribute('data-scores-open');
            } else {
                this.setAttribute('data-scores-open', '');
                this._loadScores();
            }
        }

        _csrfToken() {
            var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
            return match ? decodeURIComponent(match[1]) : '';
        }

        _handleScoreSubmit(event) {
            event.preventDefault();
            var form = event.currentTarget;
            var input = form.querySelector('input');
            var message = this.shadowRoot.querySelector('[data-game-over-message]');
            var body = new URLSearchParams();
            body.set('name', input.value);
            body.set('score', form.dataset.score || '0');
            window.fetch(this._scoresUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'X-CSRFToken': this._csrfToken()},
                body: body
            }).then(function (response) {
                return response.json().then(function (payload) {
                    if (!response.ok) {
                        throw new Error(payload.error || 'Could not save score.');
                    }
                    return payload;
                });
            }).then(function (payload) {
                this._scores = payload.scores || [];
                this._renderScores();
                form.classList.remove('is-visible');
                message.textContent = payload.position ? 'SAVED AT #' + payload.position : 'SCORE SAVED';
                this._gameOverTimer = window.setTimeout(function () {
                    this._resumeAI(true);
                }.bind(this), SCORE_SAVED_DELAY_MS);
            }.bind(this)).catch(function (error) {
                message.textContent = error.message;
            });
        }

        _resetManualTimer() {
            window.clearTimeout(this._manualTimer);
            this._manualTimer = window.setTimeout(function () {
                this._resumeAI(false);
            }.bind(this), MANUAL_IDLE_MS);
        }

        _clearHeldControls() {
            window.clearInterval(this._dropTimer);
            this._dropTimer = null;
        }

        _syncPlayback() {
            if (!this._game) {
                return;
            }
            var shouldPlay = this._isVisible && !document.hidden && !this._reducedMotion;
            this._game.blockrain(shouldPlay ? 'resume' : 'pause');
        }

        _handleVisibility() {
            this._syncPlayback();
        }

        _move(direction, count) {
            var piece = this._currentPiece();
            if (!piece) {
                return;
            }
            for (var step = 0; step < (count || 1); step += 1) {
                piece[direction < 0 ? 'moveLeft' : 'moveRight']();
            }
        }

        _rotate() {
            var piece = this._currentPiece();
            if (piece) {
                piece.rotate('right');
            }
        }

        _softDrop(count) {
            var board = this._board();
            if (!this._currentPiece() || !board) {
                return;
            }
            for (var step = 0; step < (count || 1); step += 1) {
                board.dropCount = board.dropDelay;
            }
        }

        _hardDrop() {
            var piece = this._currentPiece();
            var board = this._board();
            if (!piece || !board) {
                return;
            }
            while (!this._instance._checkCollisions(piece.x, piece.y + 1, piece.getBlocks(), true)) {
                piece.y += 1;
            }
            board.dropCount = board.dropDelay;
        }

        _handleKeyDown(event) {
            if (event.composedPath && event.composedPath().some(function (node) {
                return node.tagName === 'INPUT' || node.tagName === 'BUTTON';
            })) {
                return;
            }
            var key = event.key.toLowerCase();
            var handled = ['a', 'd', 's', 'w', ' ', 'arrowleft', 'arrowright', 'arrowdown', 'arrowup'].includes(key);
            if (!handled) {
                return;
            }
            event.preventDefault();
            this._activateManual();

            if (!this._board()) {
                return;
            }
            if (key === 'a' || key === 'arrowleft') {
                this._move(-1);
            } else if (key === 'd' || key === 'arrowright') {
                this._move(1);
            } else if (key === 's' || key === 'arrowdown') {
                this._softDrop(1);
                if (!this._dropTimer) {
                    this._dropTimer = window.setInterval(function () {
                        this._softDrop(1);
                    }.bind(this), 45);
                }
            } else {
                this._rotate();
            }
        }

        _handleKeyUp(event) {
            var key = event.key.toLowerCase();
            if (key !== 's' && key !== 'arrowdown') {
                return;
            }
            event.preventDefault();
            window.clearInterval(this._dropTimer);
            this._dropTimer = null;
            this._resetManualTimer();
        }

        _handlePointerDown(event) {
            if (event.composedPath && event.composedPath().some(function (node) {
                return node.hasAttribute && node.hasAttribute('data-ignore-takeover');
            })) {
                return;
            }
            this.focus({preventScroll: true});
            this._activateManual();
            this._pointer = {
                id: event.pointerId,
                type: event.pointerType,
                x: event.clientX,
                y: event.clientY,
                started: Date.now()
            };
            if (this.setPointerCapture) {
                this.setPointerCapture(event.pointerId);
            }
        }

        _handlePointerUp(event) {
            var pointer = this._pointer;
            this._pointer = null;
            if (!pointer || pointer.id !== event.pointerId || pointer.type === 'mouse') {
                return;
            }

            event.preventDefault();
            var deltaX = event.clientX - pointer.x;
            var deltaY = event.clientY - pointer.y;
            var horizontal = Math.abs(deltaX) > Math.abs(deltaY);
            var distance = Math.max(Math.abs(deltaX), Math.abs(deltaY));

            if (distance >= SWIPE_THRESHOLD) {
                window.clearTimeout(this._tapTimer);
                if (horizontal) {
                    this._move(deltaX < 0 ? -1 : 1, Math.min(4, Math.max(1, Math.round(Math.abs(deltaX) / 38))));
                } else if (deltaY > 0) {
                    this._softDrop(Math.min(6, Math.max(1, Math.round(deltaY / 34))));
                } else {
                    this._rotate();
                }
                this._resetManualTimer();
                return;
            }

            if (this._tapTimer) {
                window.clearTimeout(this._tapTimer);
                this._tapTimer = null;
                this._hardDrop();
            } else {
                this._tapTimer = window.setTimeout(function () {
                    this._tapTimer = null;
                    this._rotate();
                }.bind(this), TAP_DELAY_MS);
            }
            this._resetManualTimer();
        }

        _handlePointerCancel() {
            this._pointer = null;
            this._clearHeldControls();
        }
    }

    if (!window.customElements.get('noise-tetris-app')) {
        window.customElements.define('noise-tetris-app', NoiseTetrisApp);
    }
}(window));
