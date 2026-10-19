(function (window) {
    'use strict';

    function hashString(value) {
        var hash = 2166136261;
        for (var index = 0; index < value.length; index += 1) {
            hash ^= value.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
        }
        return hash >>> 0;
    }

    function mixSeeds(seeds) {
        var values = seeds.length ? seeds : ['NOISE'];
        var longest = values.reduce(function (length, value) {
            return Math.max(length, value.length);
        }, 0);
        var mixed = '';

        for (var index = 0; index < longest; index += 1) {
            values.forEach(function (value) {
                if (value.length) {
                    mixed += value.charAt(index % value.length);
                }
            });
        }
        return mixed;
    }

    function startNoiseLife(canvas, opts) {
        var options = opts || {};
        var context = canvas.getContext('2d');
        var cellSize = options.cell || 24;
        var columns = Math.max(1, Math.floor(canvas.width / cellSize));
        var rows = Math.max(1, Math.floor(canvas.height / cellSize));
        var palette = options.hues || [28, 12, 130, 210, 45, 350];
        var mixedSeed = mixSeeds(options.seeds || []);
        var randomState = hashString(mixedSeed) || 20260726;
        var board = new Uint8Array(columns * rows);
        var ages = new Uint16Array(columns * rows);
        var generation = 0;
        var animationFrame = null;
        var lastStep = 0;
        var stepInterval = options.step || 260;
        var settleDelay = options.settleDelay || 2500;
        var onGeneration = typeof options.onGeneration === 'function' ? options.onGeneration : function () {};
        var protectedCells = new Uint8Array(columns * rows);
        var protectedUntil = 0;
        var activePointer = null;

        function setGeneration(value) {
            generation = value;
            onGeneration(generation);
        }

        function random() {
            randomState += 0x6D2B79F5;
            var value = randomState;
            value = Math.imul(value ^ value >>> 15, value | 1);
            value ^= value + Math.imul(value ^ value >>> 7, value | 61);
            return ((value ^ value >>> 14) >>> 0) / 4294967296;
        }

        function boardIndex(x, y) {
            return ((y + rows) % rows) * columns + ((x + columns) % columns);
        }

        function seedBoard() {
            for (var index = 0; index < board.length; index += 1) {
                board[index] = random() < 0.22 ? 1 : 0;
                ages[index] = board[index] ? 1 : 0;
            }
        }

        function countNeighbors(x, y) {
            var count = 0;
            for (var offsetY = -1; offsetY <= 1; offsetY += 1) {
                for (var offsetX = -1; offsetX <= 1; offsetX += 1) {
                    if (offsetX || offsetY) {
                        count += board[boardIndex(x + offsetX, y + offsetY)];
                    }
                }
            }
            return count;
        }

        function evolve() {
            var next = new Uint8Array(board.length);
            var nextAges = new Uint16Array(board.length);
            var living = 0;
            var cellsAreProtected = Date.now() < protectedUntil;

            for (var y = 0; y < rows; y += 1) {
                for (var x = 0; x < columns; x += 1) {
                    var index = boardIndex(x, y);
                    var neighbors = countNeighbors(x, y);
                    var alive = board[index] === 1;
                    next[index] = cellsAreProtected && protectedCells[index]
                        ? 1
                        : (neighbors === 3 || (alive && neighbors === 2) ? 1 : 0);
                    if (next[index]) {
                        nextAges[index] = alive ? Math.min(ages[index] + 1, 65535) : 1;
                    }
                    living += next[index];
                }
            }

            board = next;
            ages = nextAges;
            if (!cellsAreProtected) {
                protectedCells.fill(0);
            }
            setGeneration(generation + 1);
            if (!living) {
                seedBoard();
                setGeneration(0);
            }
        }

        function draw() {
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.save();
            context.beginPath();
            context.lineWidth = 1;
            context.strokeStyle = 'rgba(111, 137, 166, 0.075)';
            for (var gridX = 0; gridX <= canvas.width; gridX += cellSize) {
                context.moveTo(gridX + 0.5, 0);
                context.lineTo(gridX + 0.5, canvas.height);
            }
            for (var gridY = 0; gridY <= canvas.height; gridY += cellSize) {
                context.moveTo(0, gridY + 0.5);
                context.lineTo(canvas.width, gridY + 0.5);
            }
            context.stroke();
            context.restore();
            context.lineWidth = 1.5;

            for (var y = 0; y < rows; y += 1) {
                for (var x = 0; x < columns; x += 1) {
                    if (!board[boardIndex(x, y)]) {
                        continue;
                    }
                    var colorHash = hashString(mixedSeed + ':' + x + ':' + y);
                    var hue = palette[colorHash % palette.length];
                    var age = ages[boardIndex(x, y)];
                    var persistence = Math.min(age / 24, 1);
                    var alpha = 0.2 + ((colorHash >>> 8) % 12) / 100 + persistence * 0.48;
                    context.strokeStyle = 'hsl(' + hue + ' 65% 58% / ' + alpha + ')';
                    context.shadowColor = 'hsl(' + hue + ' 72% 62% / ' + (persistence * 0.55) + ')';
                    context.shadowBlur = persistence * 9;
                    context.strokeRect(x * cellSize + 1, y * cellSize + 1, cellSize - 4, cellSize - 4);
                }
            }
            context.shadowBlur = 0;
        }

        function addCell(event) {
            var bounds = canvas.getBoundingClientRect();
            var x = Math.floor((event.clientX - bounds.left) * canvas.width / bounds.width / cellSize);
            var y = Math.floor((event.clientY - bounds.top) * canvas.height / bounds.height / cellSize);
            if (x < 0 || x >= columns || y < 0 || y >= rows) {
                return;
            }
            var index = boardIndex(x, y);
            board[index] = 1;
            protectedCells[index] = 1;
            ages[index] = Math.max(ages[index], 1);
            protectedUntil = Date.now() + settleDelay;
            draw();
        }

        function handlePointerDown(event) {
            activePointer = event.pointerId;
            if (canvas.setPointerCapture) {
                canvas.setPointerCapture(event.pointerId);
            }
            addCell(event);
            event.preventDefault();
        }

        function handlePointerMove(event) {
            if (activePointer !== event.pointerId) {
                return;
            }
            addCell(event);
            event.preventDefault();
        }

        function handlePointerEnd(event) {
            if (activePointer === event.pointerId) {
                activePointer = null;
            }
        }

        function tick(timestamp) {
            if (!lastStep || timestamp - lastStep >= stepInterval) {
                if (lastStep) {
                    evolve();
                }
                draw();
                lastStep = timestamp;
            }
            animationFrame = window.requestAnimationFrame(tick);
        }

        seedBoard();
        setGeneration(0);
        draw();
        canvas.addEventListener('pointerdown', handlePointerDown);
        canvas.addEventListener('pointermove', handlePointerMove);
        canvas.addEventListener('pointerup', handlePointerEnd);
        canvas.addEventListener('pointercancel', handlePointerEnd);
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            animationFrame = window.requestAnimationFrame(tick);
        }

        return function stopNoiseLife() {
            if (animationFrame !== null) {
                window.cancelAnimationFrame(animationFrame);
            }
            canvas.removeEventListener('pointerdown', handlePointerDown);
            canvas.removeEventListener('pointermove', handlePointerMove);
            canvas.removeEventListener('pointerup', handlePointerEnd);
            canvas.removeEventListener('pointercancel', handlePointerEnd);
        };
    }

    window.startNoiseLife = startNoiseLife;
}(window));
