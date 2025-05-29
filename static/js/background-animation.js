document.addEventListener('DOMContentLoaded', function() {
    // 配置参数
    const config = {
        pacmanCount: 3,          // 背景吃豆人数量
        dotCount: 15,           // 豆子数量
        pacmanSpeed: 1.5,       // 吃豆人移动速度（降低速度使动画更柔和）
        dotRespawnTime: 3000,   // 豆子重生时间(毫秒)
    };

    // 游戏区域
    const gameArea = document.body;
    const gameWidth = window.innerWidth;
    const gameHeight = window.innerHeight;
    
    // 存储游戏元素
    const pacmen = [];
    const dots = [];
    
    // 初始化游戏
    function initGame() {
        // 创建吃豆人
        for (let i = 0; i < config.pacmanCount; i++) {
            createPacman();
        }
        
        // 创建豆子
        for (let i = 0; i < config.dotCount; i++) {
            createDot();
        }
        
        // 开始游戏循环
        requestAnimationFrame(gameLoop);
    }
    
    // 创建吃豆人
    function createPacman() {
        const pacman = document.createElement('div');
        pacman.className = 'bean-character';
        
        // 随机位置
        const x = Math.random() * (gameWidth - 40);
        const y = Math.random() * (gameHeight - 40);
        
        // 随机方向
        const angle = Math.random() * Math.PI * 2;
        const speed = config.pacmanSpeed;
        
        // 设置初始位置和样式
        pacman.style.left = `${x}px`;
        pacman.style.top = `${y}px`;
        
        // 存储吃豆人数据
        const pacmanData = {
            element: pacman,
            x: x,
            y: y,
            angle: angle,
            speed: speed,
            targetX: null,
            targetY: null,
            targetDot: null,
            lastDotEaten: 0
        };
        
        pacmen.push(pacmanData);
        gameArea.appendChild(pacman);
        
        // 更新吃豆人朝向
        updatePacmanRotation(pacmanData);
    }
    
    // 创建豆子
    function createDot() {
        const dot = document.createElement('div');
        dot.className = 'candy';
        
        // 随机位置
        const x = Math.random() * (gameWidth - 10);
        const y = Math.random() * (gameHeight - 10);
        
        // 设置位置
        dot.style.left = `${x}px`;
        dot.style.top = `${y}px`;
        
        // 存储豆子数据
        const dotData = {
            element: dot,
            x: x,
            y: y,
            active: true
        };
        
        dots.push(dotData);
        gameArea.appendChild(dot);
    }
    
    // 更新吃豆人朝向
    function updatePacmanRotation(pacman) {
        const degrees = (pacman.angle * 180 / Math.PI);
        pacman.element.style.transform = `rotate(${degrees}deg)`;
    }
    
    // 寻找最近的豆子
    function findNearestDot(pacman) {
        let nearestDot = null;
        let minDistance = Infinity;
        
        for (const dot of dots) {
            if (!dot.active) continue;
            
            const dx = dot.x - pacman.x;
            const dy = dot.y - pacman.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < minDistance) {
                minDistance = distance;
                nearestDot = dot;
            }
        }
        
        return nearestDot;
    }
    
    // 检测吃豆人是否吃到豆子
    function checkDotCollision(pacman) {
        const pacmanRadius = 20; // 吃豆人半径
        const dotRadius = 4;     // 豆子半径
        
        for (const dot of dots) {
            if (!dot.active) continue;
            
            const dx = dot.x - pacman.x;
            const dy = dot.y - pacman.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            // 如果距离小于两者半径之和，则发生碰撞
            if (distance < pacmanRadius + dotRadius) {
                eatDot(pacman, dot);
                return true;
            }
        }
        
        return false;
    }
    
    // 吃豆子效果
    function eatDot(pacman, dot) {
        // 标记豆子为非活动状态
        dot.active = false;
        dot.element.style.opacity = '0';
        
        // 显示得分效果
        showScoreEffect(dot.x, dot.y);
        
        // 记录最后吃豆子的时间
        pacman.lastDotEaten = Date.now();
        pacman.targetDot = null;
        
        // 设置豆子重生
        setTimeout(() => {
            // 重新定位豆子
            dot.x = Math.random() * (gameWidth - 10);
            dot.y = Math.random() * (gameHeight - 10);
            
            // 更新豆子位置
            dot.element.style.left = `${dot.x}px`;
            dot.element.style.top = `${dot.y}px`;
            
            // 重新激活豆子
            dot.active = true;
            dot.element.style.opacity = '1';
        }, config.dotRespawnTime);
    }
    
    // 显示得分效果
    function showScoreEffect(x, y) {
        const scoreEffect = document.createElement('div');
        scoreEffect.className = 'eat-effect';
        
        // 随机选择得分值
        const scoreIndex = Math.floor(Math.random() * config.scoreValues.length);
        const score = config.scoreValues[scoreIndex];
        
        scoreEffect.textContent = score;
        scoreEffect.style.left = `${x}px`;
        scoreEffect.style.top = `${y}px`;
        
        gameArea.appendChild(scoreEffect);
        
        // 动画结束后移除元素
        setTimeout(() => {
            gameArea.removeChild(scoreEffect);
        }, 800);
    }
    
    // 游戏主循环
    function gameLoop() {
        // 更新每个吃豆人
        for (const pacman of pacmen) {
            // 如果没有目标豆子或目标豆子不活跃，寻找新的目标
            if (!pacman.targetDot || !pacman.targetDot.active) {
                pacman.targetDot = findNearestDot(pacman);
            }
            
            if (pacman.targetDot) {
                // 计算到目标豆子的方向
                const dx = pacman.targetDot.x - pacman.x;
                const dy = pacman.targetDot.y - pacman.y;
                pacman.angle = Math.atan2(dy, dx);
                
                // 更新吃豆人朝向
                updatePacmanRotation(pacman);
            }
            
            // 移动吃豆人
            pacman.x += Math.cos(pacman.angle) * pacman.speed;
            pacman.y += Math.sin(pacman.angle) * pacman.speed;
            
            // 边界检查
            if (pacman.x < 0) pacman.x = 0;
            if (pacman.y < 0) pacman.y = 0;
            if (pacman.x > gameWidth - 40) pacman.x = gameWidth - 40;
            if (pacman.y > gameHeight - 40) pacman.y = gameHeight - 40;
            
            // 更新吃豆人位置
            pacman.element.style.left = `${pacman.x}px`;
            pacman.element.style.top = `${pacman.y}px`;
            
            // 检测碰撞
            checkDotCollision(pacman);
        }
        
        // 继续游戏循环
        requestAnimationFrame(gameLoop);
    }
    
    // 窗口大小改变时重新计算游戏区域
    window.addEventListener('resize', function() {
        const newWidth = window.innerWidth;
        const newHeight = window.innerHeight;
        
        // 更新游戏区域尺寸
        gameWidth = newWidth;
        gameHeight = newHeight;
    });
    
    // 启动游戏
    initGame();
});