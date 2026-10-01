let currentRandomId = null;
let currentItems = [];
let currentAngle = 0;
let isSpinning = false;
const colors = ['#818cf8', '#c084fc', '#f472b6', '#38bdf8', '#4ade80', '#facc15', '#fb923c'];

function handleRouletteClick(btn) {
    const id = btn.getAttribute('data-id');
    const title = btn.getAttribute('data-title');
    const items = JSON.parse(btn.getAttribute('data-items'));
    
    openRoulette(id, title, items);
}

function openRoulette(id, title, items) {
    currentRandomId = id;
    currentItems = items;
    document.getElementById('rouletteTitle').innerText = "🎰 " + title;
    document.getElementById('rouletteModal').style.display = 'flex';
    document.getElementById('spinBtn').disabled = false;
    document.getElementById('spinBtn').innerText = "START!";
    currentAngle = 0;
    drawRoulette();
}

function drawRoulette() {
    const canvas = document.getElementById('rouletteCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const numItems = currentItems.length;
    const arc = (2 * Math.PI) / numItems;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(150, 150);
    ctx.rotate(currentAngle);

    for (let i = 0; i < numItems; i++) {
        const angle = i * arc;
        ctx.beginPath();
        ctx.fillStyle = colors[i % colors.length];
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, 140, angle, angle + arc);
        ctx.fill();
        ctx.stroke();

        ctx.save();
        ctx.fillStyle = "white";
        ctx.font = "bold 14px Pretendard, sans-serif";
        ctx.textAlign = "right";
        ctx.rotate(angle + arc / 2);
        ctx.fillText(currentItems[i].item_title, 120, 5);
        ctx.restore();
    }
    ctx.restore();
}

function spinWheel() {
    if (isSpinning) return;
    isSpinning = true;
    document.getElementById('spinBtn').disabled = true;

    const startAngle = currentAngle;
    const spinAngle = (Math.floor(Math.random() * 5) + 5) * 2 * Math.PI + Math.random() * 2 * Math.PI;
    const duration = 3000;
    const startTime = performance.now();

    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        currentAngle = startAngle + spinAngle * easeOut;

        drawRoulette();

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            isSpinning = false;
            setTimeout(() => {
                const form = document.getElementById('realBuyForm');
                form.action = '/buy_random/' + currentRandomId;
                form.submit();
            }, 500);
        }
    }

    requestAnimationFrame(animate);
}