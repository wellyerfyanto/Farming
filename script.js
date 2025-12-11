// Global variables
let statsInterval;
let devicesInterval;
let currentScenario = null;

// Add log entry
function addLog(message, type = 'info') {
    const logContainer = document.getElementById('logContainer');
    const timestamp = new Date().toLocaleTimeString();
    
    let icon = 'ℹ️';
    if (type === 'error') icon = '❌';
    else if (type === 'success') icon = '✅';
    else if (type === 'warning') icon = '⚠️';
    
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry fade-in';
    logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${icon} ${message}`;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Show/hide scenario configuration
function showScenarioConfig() {
    // Hide all config sections first
    document.querySelectorAll('.scenario-config').forEach(el => {
        el.style.display = 'none';
    });
    
    const scenarioType = document.getElementById('scenarioType').value;
    if (scenarioType) {
        document.getElementById(scenarioType + 'Config').style.display = 'block';
        updateGoogleAccountsNotice(scenarioType);
    }
}

// Save scenario configuration
function saveScenarioConfig() {
    const scenarioType = document.getElementById('scenarioType').value;
    
    if (!scenarioType) {
        alert('Please select a scenario type first!');
        return;
    }

    let scenarioConfig = {
        type: scenarioType,
        name: document.getElementById('scenarioType').options[document.getElementById('scenarioType').selectedIndex].text,
        timestamp: new Date().toISOString()
    };

    switch (scenarioType) {
        case 'youtube':
            scenarioConfig.urls = document.getElementById('youtubeUrls').value.split('\n').filter(url => url.trim());
            scenarioConfig.minTime = parseInt(document.getElementById('youtubeMinTime').value);
            scenarioConfig.maxTime = parseInt(document.getElementById('youtubeMaxTime').value);
            scenarioConfig.autoLike = document.getElementById('youtubeLike').checked;
            scenarioConfig.autoSubscribe = document.getElementById('youtubeSubscribe').checked;
            
            if (scenarioConfig.urls.length === 0) {
                alert('Please add at least one YouTube URL!');
                return;
            }
            break;
            
        case 'traffic':
            scenarioConfig.urls = document.getElementById('trafficUrls').value.split('\n').filter(url => url.trim());
            scenarioConfig.duration = parseInt(document.getElementById('trafficDuration').value);
            scenarioConfig.pagesPerSession = parseInt(document.getElementById('trafficPages').value);
            scenarioConfig.randomClick = document.getElementById('trafficRandomClick').checked;
            scenarioConfig.randomScroll = document.getElementById('trafficScroll').checked;
            
            if (scenarioConfig.urls.length === 0) {
                alert('Please add at least one target URL!');
                return;
            }
            break;
            
        case 'search':
            scenarioConfig.engine = document.getElementById('searchEngine').value;
            scenarioConfig.mode = document.getElementById('searchMode').value;
            
            if (scenarioConfig.mode === 'manual') {
                scenarioConfig.keywords = document.getElementById('searchKeywords').value.split('\n').filter(kw => kw.trim());
            } else if (scenarioConfig.mode === 'auto') {
                scenarioConfig.category = document.getElementById('keywordCategory').value;
                scenarioConfig.keywordCount = parseInt(document.getElementById('keywordCount').value);
                // Auto keywords will be generated at runtime
                scenarioConfig.keywords = document.getElementById('searchKeywords').value.split('\n').filter(kw => kw.trim());
            }
            
            scenarioConfig.targetUrls = document.getElementById('targetUrls').value.split('\n').filter(url => url.trim());
            scenarioConfig.searchesPerDevice = parseInt(document.getElementById('searchCount').value);
            scenarioConfig.minClicks = parseInt(document.getElementById('searchMinClick').value);
            scenarioConfig.maxClicks = parseInt(document.getElementById('searchMaxClick').value);
            scenarioConfig.behavior = {
                minReadTime: parseInt(document.getElementById('minReadTime').value),
                maxReadTime: parseInt(document.getElementById('maxReadTime').value),
                scrollSpeed: document.getElementById('scrollSpeed').value,
                clickPattern: document.getElementById('clickPattern').value,
                useCtrlF: document.getElementById('useCtrlF').checked,
                randomNavigation: document.getElementById('randomNavigation').checked,
                returnToHome: document.getElementById('returnToHome').checked
            };
            
            if (scenarioConfig.mode === 'manual' && scenarioConfig.keywords.length === 0) {
                alert('Please add at least one search keyword!');
                return;
            }
            break;
            
        case 'custom':
            try {
                scenarioConfig.custom = JSON.parse(document.getElementById('customJson').value);
            } catch (e) {
                alert('Invalid JSON format! Please check your configuration.');
                return;
            }
            break;
    }

    // Save to localStorage and global variable
    localStorage.setItem('currentScenario', JSON.stringify(scenarioConfig));
    currentScenario = scenarioConfig;
    
    // Save to server
    saveScenarioToServer(scenarioConfig);
    
    addLog(`Scenario "${scenarioConfig.name}" configuration saved`, 'success');
}

// Save scenario to server
async function saveScenarioToServer(scenarioConfig) {
    try {
        const response = await fetch('/api/scenario/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(scenarioConfig)
        });
        
        const data = await response.json();
        if (data.status !== 'success') {
            console.warn('Failed to save scenario to server:', data.message);
        }
    } catch (error) {
        console.error('Error saving scenario to server:', error);
    }
}

// Load scenario preset
function loadScenarioPreset() {
    const scenarioType = document.getElementById('scenarioType').value;
    
    if (!scenarioType) {
        alert('Please select a scenario type first!');
        return;
    }

    switch (scenarioType) {
        case 'youtube':
            document.getElementById('youtubeUrls').value = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=JGwWNGJdvx8';
            document.getElementById('youtubeMinTime').value = '60';
            document.getElementById('youtubeMaxTime').value = '180';
            document.getElementById('youtubeLike').checked = true;
            document.getElementById('youtubeSubscribe').checked = false;
            break;
            
        case 'traffic':
            document.getElementById('trafficUrls').value = 'https://example.com\nhttps://example.com/blog\nhttps://example.com/products';
            document.getElementById('trafficDuration').value = '120';
            document.getElementById('trafficPages').value = '5';
            document.getElementById('trafficRandomClick').checked = true;
            document.getElementById('trafficScroll').checked = true;
            break;
            
        case 'search':
            document.getElementById('searchEngine').value = 'google';
            document.getElementById('searchMode').value = 'manual';
            document.getElementById('searchKeywords').value = 'artificial intelligence\nmachine learning\ndeep learning\nneural networks\nAI applications';
            document.getElementById('targetUrls').value = 'https://example.com/ai-research\nhttps://example.com/tech-news';
            document.getElementById('searchCount').value = '5';
            document.getElementById('searchMinClick').value = '2';
            document.getElementById('searchMaxClick').value = '4';
            document.getElementById('minReadTime').value = '30';
            document.getElementById('maxReadTime').value = '90';
            document.getElementById('scrollSpeed').value = 'medium';
            document.getElementById('clickPattern').value = 'normal';
            document.getElementById('useCtrlF').checked = true;
            document.getElementById('randomNavigation').checked = true;
            document.getElementById('returnToHome').checked = false;
            // Update UI for mode
            toggleKeywordMode();
            break;
            
        case 'custom':
            document.getElementById('customJson').value = `{
  "tasks": [
    {
      "type": "website_visit",
      "urls": ["https://example.com", "https://example.com/blog"],
      "duration": 120,
      "random_click": true
    },
    {
      "type": "search_engine", 
      "engine": "google",
      "keywords": ["technology", "innovation"],
      "max_results": 5
    }
  ]
}`;
            break;
    }
    
    addLog(`Loaded preset for ${scenarioType} scenario`, 'info');
}

// Update Google accounts requirement notice
function updateGoogleAccountsNotice(scenarioType) {
    const accountsTextarea = document.getElementById('googleAccounts');
    const label = accountsTextarea.closest('.row').querySelector('.form-label');
    
    if (scenarioType === 'youtube') {
        label.innerHTML = 'Google Accounts <span class="text-danger">*Required for YouTube*</span>';
        accountsTextarea.placeholder = 'YouTube scenario requires Google accounts!\nFormat: email:password\naccount1@gmail.com:password1\naccount2@gmail.com:password2';
    } else {
        label.innerHTML = 'Google Accounts';
        accountsTextarea.placeholder = 'Format: email:password\naccount1@gmail.com:password1\naccount2@gmail.com:password2';
    }
}

// Toggle keyword input mode
function toggleKeywordMode() {
    const mode = document.getElementById('searchMode').value;
    
    // Hide all sections first
    document.getElementById('manualKeywordsSection').style.display = 'none';
    document.getElementById('autoKeywordsSection').style.display = 'none';
    document.getElementById('fileKeywordsSection').style.display = 'none';
    
    // Show the selected section
    if (mode === 'manual') {
        document.getElementById('manualKeywordsSection').style.display = 'block';
    } else if (mode === 'auto') {
        document.getElementById('autoKeywordsSection').style.display = 'block';
        // Load auto keywords if textarea is empty
        if (!document.getElementById('searchKeywords').value.trim()) {
            loadAutoKeywords();
        }
    } else if (mode === 'file') {
        document.getElementById('fileKeywordsSection').style.display = 'block';
    }
}

// Load auto-generated keywords
function loadAutoKeywords() {
    const category = document.getElementById('keywordCategory').value;
    const count = parseInt(document.getElementById('keywordCount').value);
    
    const keywordLists = {
        technology: [
            "artificial intelligence", "machine learning", "data science", "cloud computing",
            "cybersecurity", "blockchain", "IoT devices", "5G technology", "quantum computing",
            "virtual reality", "augmented reality", "robotics", "automation", "big data",
            "edge computing", "devops", "microservices", "API development", "web3", "metaverse"
        ],
        news: [
            "breaking news", "world politics", "economic trends", "climate change",
            "health updates", "science discoveries", "technology innovations", "sports events",
            "entertainment news", "business developments", "stock market", "crypto news",
            "space exploration", "environmental issues", "social media trends"
        ],
        sports: [
            "football highlights", "basketball scores", "tennis tournaments", "Olympics 2024",
            "sports injuries", "team transfers", "championship results", "athlete interviews",
            "fitness tips", "sports technology", "esports tournaments", "fantasy sports",
            "sports betting", "nutrition for athletes", "training techniques"
        ],
        entertainment: [
            "movie reviews", "celebrity news", "music releases", "TV show ratings",
            "gaming updates", "streaming services", "box office results", "award shows",
            "book releases", "theater performances", "art exhibitions", "festival news",
            "social media influencers", "podcast recommendations", "comedy specials"
        ],
        education: [
            "online learning", "educational technology", "teaching methods", "student resources",
            "STEM education", "language learning", "career development", "university rankings",
            "scholarship opportunities", "research papers", "academic conferences",
            "learning psychology", "education reform", "homeschooling tips", "educational apps"
        ],
        business: [
            "startup funding", "market analysis", "leadership skills", "digital marketing",
            "remote work", "entrepreneurship", "business strategy", "financial planning",
            "supply chain", "customer experience", "innovation management", "mergers acquisitions",
            "brand building", "sales techniques", "economic indicators"
        ]
    };
    
    const selectedList = keywordLists[category] || keywordLists.technology;
    const shuffled = [...selectedList].sort(() => 0.5 - Math.random());
    const selectedKeywords = shuffled.slice(0, Math.min(count, shuffled.length));
    
    document.getElementById('searchKeywords').value = selectedKeywords.join('\n');
    addLog(`Loaded ${selectedKeywords.length} auto-generated keywords for ${category} category`, 'info');
}

// Read keywords from uploaded file
function readKeywordsFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const content = e.target.result;
            let keywords = [];
            
            // Try different formats
            if (file.name.endsWith('.json')) {
                try {
                    const data = JSON.parse(content);
                    if (Array.isArray(data)) {
                        keywords = data;
                    } else if (data.keywords && Array.isArray(data.keywords)) {
                        keywords = data.keywords;
                    }
                } catch (error) {
                    // If JSON fails, try text format
                    keywords = content.split('\n').filter(k => k.trim());
                }
            } else {
                // Text or CSV file
                keywords = content.split('\n')
                    .map(line => line.split(',').map(k => k.trim()))
                    .flat()
                    .filter(k => k && !k.startsWith('#'));
            }
            
            resolve(keywords);
        };
        
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

// Start bot farm dengan better error handling
async function startFarm() {
    const startBtn = event.target;
    const originalText = startBtn.innerHTML;
    
    try {
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting...';
        startBtn.disabled = true;
        
        const scenarioConfig = JSON.parse(localStorage.getItem('currentScenario') || '{}');
        
        if (!scenarioConfig.type) {
            alert('Please configure a scenario first!');
            return;
        }

        const accountsText = document.getElementById('googleAccounts').value;
        const accounts = parseGoogleAccounts(accountsText);
        
        if (scenarioConfig.type === 'youtube' && accounts.length === 0) {
            alert('YouTube scenario requires Google accounts! Please add Google accounts first.');
            return;
        }

        const devicesConfig = generateDevicesConfig(accounts.length);
        const tasksConfig = generateTasksFromScenario(scenarioConfig, accounts);

        addLog(`Starting bot farm with ${scenarioConfig.name} scenario...`, 'info');
        
        const response = await fetch('/api/farm/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                devices: devicesConfig,
                tasks: tasksConfig
            })
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            addLog(`Bot farm started successfully with ${scenarioConfig.name} scenario!`, 'success');
            startMonitoring();
        } else {
            addLog('Failed to start bot farm: ' + data.message, 'error');
            
            // Coba force stop jika gagal
            if (data.message.includes('already running')) {
                addLog('Attempting force cleanup...', 'warning');
                await fetch('/api/farm/force-stop', { method: 'POST' });
                setTimeout(startFarm, 2000); // Retry setelah cleanup
            }
        }
    } catch (error) {
        addLog('Error starting bot farm: ' + error.message, 'error');
    } finally {
        startBtn.innerHTML = originalText;
        startBtn.disabled = false;
    }
}

// Stop bot farm
async function stopFarm() {
    try {
        addLog('Stopping bot farm...', 'warning');
        const response = await fetch('/api/farm/stop');
        const data = await response.json();
        
        if (data.status === 'success') {
            addLog('Bot farm stopped successfully.', 'success');
            stopMonitoring();
        }
    } catch (error) {
        addLog('Error stopping bot farm: ' + error.message, 'error');
    }
}

// Force stop bot farm
async function forceStopFarm() {
    if (!confirm('Force stop will immediately terminate all sessions. Continue?')) {
        return;
    }
    
    try {
        addLog('Force stopping bot farm...', 'warning');
        const response = await fetch('/api/farm/force-stop', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            addLog('Bot farm force stopped successfully.', 'success');
            stopMonitoring();
            updateStats(); // Refresh stats
        }
    } catch (error) {
        addLog('Error force stopping bot farm: ' + error.message, 'error');
    }
}

// Update Google accounts
async function updateGoogleAccounts() {
    const accountsText = document.getElementById('googleAccounts').value;
    const accounts = parseGoogleAccounts(accountsText);
    
    try {
        const response = await fetch('/api/google/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accounts: accounts })
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            addLog(`Updated ${accounts.length} Google accounts`, 'success');
        }
    } catch (error) {
        addLog('Error updating accounts: ' + error.message, 'error');
    }
}

// Parse Google accounts from text
function parseGoogleAccounts(text) {
    const accounts = [];
    const lines = text.split('\n');
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue;
        
        const [email, password] = trimmedLine.split(':').map(s => s.trim());
        if (email && password && email.includes('@')) {
            accounts.push({ 
                email: email, 
                password: password,
                device_id: `device_${accounts.length + 1}`
            });
        }
    }
    
    return accounts;
}

// Generate devices configuration
function generateDevicesConfig(count) {
    const devices = [];
    const deviceTypes = ['desktop', 'mobile'];
    
    for (let i = 0; i < count; i++) {
        devices.push({
            id: `device_${i + 1}`,
            name: `Device ${i + 1}`,
            type: deviceTypes[i % deviceTypes.length],
            headless: false,
            proxy_enabled: true,
            max_session_duration: 3600,
            save_session: true
        });
    }
    
    // If no accounts, create at least one device
    if (devices.length === 0) {
        devices.push({
            id: 'device_1',
            name: 'Device 1',
            type: 'desktop',
            headless: false,
            proxy_enabled: true,
            max_session_duration: 3600,
            save_session: true
        });
    }
    
    return devices;
}

// Generate tasks from scenario configuration
function generateTasksFromScenario(scenarioConfig, accounts) {
    let tasks = [];
    
    switch (scenarioConfig.type) {
        case 'youtube':
            tasks = generateYouTubeTasks(scenarioConfig, accounts);
            break;
        case 'traffic':
            tasks = generateTrafficTasks(scenarioConfig, accounts);
            break;
        case 'search':
            tasks = generateEnhancedSearchTasks(scenarioConfig, accounts);
            break;
        case 'custom':
            tasks = scenarioConfig.custom.tasks || [];
            break;
    }
    
    addLog(`Generated ${tasks.length} tasks for ${scenarioConfig.name} scenario`, 'info');
    return { tasks: tasks };
}

// Generate YouTube tasks
function generateYouTubeTasks(config, accounts) {
    const tasks = [];
    let taskId = 1;
    
    accounts.forEach((account, index) => {
        config.urls.forEach(url => {
            tasks.push({
                id: `task_${taskId++}`,
                type: 'youtube',
                device_id: `device_${index + 1}`,
                video_url: url,
                watch_time_min: config.minTime,
                watch_time_max: config.maxTime,
                auto_like: config.autoLike,
                auto_subscribe: config.autoSubscribe,
                priority: 'high'
            });
        });
    });
    
    return tasks;
}

// Generate traffic tasks
function generateTrafficTasks(config, accounts) {
    const tasks = [];
    let taskId = 1;
    
    accounts.forEach((account, index) => {
        tasks.push({
            id: `task_${taskId++}`,
            type: 'website_visit',
            device_id: `device_${index + 1}`,
            urls: config.urls,
            visit_duration: config.duration,
            pages_per_session: config.pagesPerSession,
            random_click: config.randomClick,
            random_scroll: config.randomScroll,
            priority: 'medium'
        });
    });
    
    return tasks;
}

// Generate enhanced search tasks
function generateEnhancedSearchTasks(config, accounts) {
    const tasks = [];
    let taskId = 1;
    
    // Get behavior settings
    const behavior = config.behavior || {};
    
    // Helper functions for variation
    function randomVariation(range) {
        return Math.floor(Math.random() * range * 2) - range;
    }
    
    function randomChoice(options) {
        return options[Math.floor(Math.random() * options.length)];
    }
    
    accounts.forEach((account, index) => {
        const deviceId = `device_${index + 1}`;
        
        // Calculate per-device variations
        const perDeviceVariation = {
            min_read_time: Math.max(10, (behavior.minReadTime || 30) + randomVariation(5)),
            max_read_time: (behavior.maxReadTime || 90) + randomVariation(10),
            scroll_speed: behavior.scrollSpeed || 'medium',
            click_pattern: behavior.clickPattern || 'normal',
            use_ctrl_f: behavior.useCtrlF !== false, // default true
            random_navigation: behavior.randomNavigation !== false, // default true
            return_to_home: behavior.returnToHome || false
        };
        
        tasks.push({
            id: `enhanced_search_${taskId++}`,
            type: 'enhanced_search',
            device_id: deviceId,
            engine: config.engine || 'google',
            keywords: config.keywords || [],
            target_urls: config.targetUrls || [],
            searches_per_device: config.searchesPerDevice || 5,
            min_result_clicks: config.minClicks || 2,
            max_result_clicks: config.maxClicks || 4,
            behavior: perDeviceVariation,
            priority: 'medium',
            session_variation: {
                read_time_multiplier: 0.8 + (Math.random() * 0.4), // 0.8-1.2x
                activity_intensity: randomChoice(['low', 'medium', 'high']),
                navigation_style: randomChoice(['direct', 'explorative', 'casual'])
            }
        });
    });
    
    return tasks;
}

// Load sample accounts
function loadSampleAccounts() {
    const sampleAccounts = `example1@gmail.com:password1\nexample2@gmail.com:password2\nexample3@gmail.com:password3`;
    document.getElementById('googleAccounts').value = sampleAccounts;
    addLog('Loaded sample accounts format', 'info');
}

// Update statistics
async function updateStats() {
    try {
        const response = await fetch('/api/farm/stats');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayStats(data.data);
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

// Display statistics
function displayStats(stats) {
    const statsSection = document.getElementById('statsSection');
    
    const formatTime = (seconds) => {
        if (!seconds) return '0m';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    };
    
    const statsHTML = `
        <div class="col-md-3">
            <div class="card stat-card ${stats.is_running ? 'status-online' : 'status-offline'}">
                <div class="card-body text-center">
                    <h3>${stats.is_running ? '🟢' : '🔴'}</h3>
                    <h5 class="card-title">${stats.is_running ? 'Running' : 'Stopped'}</h5>
                    <h2 class="text-primary">${formatTime(stats.uptime)}</h2>
                    <small class="text-muted">Uptime</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3>📱</h3>
                    <h5 class="card-title">Devices</h5>
                    <h2 class="text-info">${stats.active_devices || 0}/${stats.total_devices || 0}</h2>
                    <small class="text-muted">Active/Total</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3>✅</h3>
                    <h5 class="card-title">Tasks Completed</h5>
                    <h2 class="text-success">${stats.total_tasks_completed || 0}</h2>
                    <small class="text-muted">Total</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3>🔐</h3>
                    <h5 class="card-title">Google Logins</h5>
                    <h2 class="${(stats.google_logins_successful || 0) > 0 ? 'text-success' : 'text-warning'}">
                        ${stats.google_logins_successful || 0}/${(stats.google_logins_successful || 0) + (stats.google_logins_failed || 0)}
                    </h2>
                    <small class="text-muted">Success/Total</small>
                </div>
            </div>
        </div>
    `;
    
    statsSection.innerHTML = statsHTML;
}

// Update devices display
async function updateDevices() {
    try {
        const response = await fetch('/api/devices');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayDevices(data.data);
        }
    } catch (error) {
        console.error('Error fetching devices:', error);
    }
}

// Display devices
function displayDevices(devices) {
    const devicesGrid = document.getElementById('devicesGrid');
    
    if (!devices || Object.keys(devices).length === 0) {
        devicesGrid.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle me-2"></i>No devices active. Start the farm to see devices.
                </div>
            </div>
        `;
        return;
    }
    
    let devicesHTML = '';
    
    Object.entries(devices).forEach(([deviceId, device]) => {
        const statusClass = device.is_active ? 
            (device.google_login_success ? 'status-online' : 'status-working') : 
            'status-offline';
        
        const statusIcon = device.is_active ? 
            (device.google_login_success ? '🟢' : '🟡') : '🔴';
        
        const sessionDuration = device.session_duration ? Math.floor(device.session_duration / 60) : 0;
        
        devicesHTML += `
            <div class="col-md-4">
                <div class="card device-card ${statusClass}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="card-title mb-0">
                                <i class="fas fa-mobile-alt me-2"></i>${deviceId}
                            </h6>
                            <span class="fs-5">${statusIcon}</span>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">
                                ${device.is_active ? 'Active' : 'Inactive'} • 
                                ${sessionDuration}m session
                            </small>
                        </div>
                        ${device.google_login_success ? 
                            '<span class="google-badge mt-2 d-inline-block">Google ✓</span>' : 
                            '<span class="badge bg-warning mt-2">Google ✗</span>'
                        }
                        ${device.current_task ? `
                            <div class="mt-2">
                                <small class="text-muted">Task: ${device.current_task.type}</small>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    devicesGrid.innerHTML = devicesHTML;
}

// Profile Management Functions
async function loadProfilesList() {
    try {
        const response = await fetch('/api/profiles/list');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayProfilesList(data.data);
            updateExportDeviceList(data.data);
        }
    } catch (error) {
        console.error('Error loading profiles:', error);
    }
}

function displayProfilesList(profiles) {
    const profilesList = document.getElementById('profilesList');
    
    if (!profiles || Object.keys(profiles).length === 0) {
        profilesList.innerHTML = '<div class="alert alert-info">No profiles found</div>';
        return;
    }
    
    let html = '';
    Object.entries(profiles).forEach(([deviceId, profile]) => {
        const loginStatus = profile.google_logged_in ? 
            `<span class="badge bg-success">Google: ${profile.google_email}</span>` :
            `<span class="badge bg-warning">Not Logged In</span>`;
        
        const lastLogin = profile.last_login ? 
            new Date(profile.last_login * 1000).toLocaleString() : 'Never';
        
        html += `
            <div class="card device-card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${deviceId}</strong>
                            <div class="mt-1">
                                ${loginStatus}
                                <small class="text-muted ms-2">Last: ${lastLogin}</small>
                            </div>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteProfile('${deviceId}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    profilesList.innerHTML = html;
}

function updateExportDeviceList(profiles) {
    const exportSelect = document.getElementById('exportDevice');
    exportSelect.innerHTML = '<option value="">Select Device</option>';
    
    Object.keys(profiles).forEach(deviceId => {
        const option = document.createElement('option');
        option.value = deviceId;
        option.textContent = deviceId;
        exportSelect.appendChild(option);
    });
}

async function exportProfile() {
    const deviceId = document.getElementById('exportDevice').value;
    
    if (!deviceId) {
        alert('Please select a device to export');
        return;
    }
    
    try {
        const response = await fetch(`/api/profiles/export/${deviceId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // Create download link
            const profileData = data.data;
            const blob = new Blob([JSON.stringify(profileData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `profile_${deviceId}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            addLog(`Exported profile for ${deviceId}`, 'success');
        } else {
            alert('Failed to export profile: ' + data.message);
        }
    } catch (error) {
        addLog('Error exporting profile: ' + error.message, 'error');
    }
}

async function importProfile() {
    const fileInput = document.getElementById('importFile');
    const deviceId = document.getElementById('importDeviceId').value;
    
    if (!fileInput.files.length || !deviceId) {
        alert('Please select a file and enter device ID');
        return;
    }
    
    try {
        const file = fileInput.files[0];
        const fileText = await file.text();
        const profileData = JSON.parse(fileText);
        
        const response = await fetch('/api/profiles/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: deviceId,
                profile_data: profileData.data
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            addLog(`Imported profile for ${deviceId}`, 'success');
            loadProfilesList();
            // Clear form
            fileInput.value = '';
            document.getElementById('importDeviceId').value = '';
        } else {
            alert('Failed to import profile: ' + data.message);
        }
    } catch (error) {
        addLog('Error importing profile: ' + error.message, 'error');
    }
}

async function deleteProfile(deviceId) {
    if (!confirm(`Are you sure you want to delete profile for ${deviceId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/profiles/delete/${deviceId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            addLog(`Deleted profile for ${deviceId}`, 'success');
            loadProfilesList();
        } else {
            alert('Failed to delete profile: ' + data.message);
        }
    } catch (error) {
        addLog('Error deleting profile: ' + error.message, 'error');
    }
}

// Start monitoring
function startMonitoring() {
    stopMonitoring(); // Clear existing intervals
    
    statsInterval = setInterval(updateStats, 3000);
    devicesInterval = setInterval(updateDevices, 5000);
    
    updateStats();
    updateDevices();
    addLog('Started real-time monitoring', 'info');
}

// Stop monitoring
function stopMonitoring() {
    if (statsInterval) clearInterval(statsInterval);
    if (devicesInterval) clearInterval(devicesInterval);
    
    statsInterval = null;
    devicesInterval = null;
}

// Load saved scenario on page load
function loadSavedScenario() {
    const savedScenario = localStorage.getItem('currentScenario');
    if (savedScenario) {
        const scenario = JSON.parse(savedScenario);
        document.getElementById('scenarioType').value = scenario.type;
        showScenarioConfig();
        
        // If search scenario, set the mode and update UI
        if (scenario.type === 'search' && scenario.mode) {
            document.getElementById('searchMode').value = scenario.mode;
            toggleKeywordMode();
            
            // Load saved values
            if (scenario.keywords) {
                document.getElementById('searchKeywords').value = scenario.keywords.join('\n');
            }
            if (scenario.targetUrls) {
                document.getElementById('targetUrls').value = scenario.targetUrls.join('\n');
            }
            if (scenario.behavior) {
                const b = scenario.behavior;
                document.getElementById('minReadTime').value = b.minReadTime || 30;
                document.getElementById('maxReadTime').value = b.maxReadTime || 90;
                document.getElementById('scrollSpeed').value = b.scrollSpeed || 'medium';
                document.getElementById('clickPattern').value = b.clickPattern || 'normal';
                document.getElementById('useCtrlF').checked = b.useCtrlF !== false;
                document.getElementById('randomNavigation').checked = b.randomNavigation !== false;
                document.getElementById('returnToHome').checked = b.returnToHome || false;
            }
        }
        
        addLog(`Loaded saved scenario: ${scenario.name}`, 'info');
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    addLog('Dashboard initialized successfully');
    loadSavedScenario();
    updateStats();
    loadProfilesList();
    
    // Add event listener for keywords file upload
    const keywordsFileInput = document.getElementById('keywordsFile');
    if (keywordsFileInput) {
        keywordsFileInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            try {
                const keywords = await readKeywordsFile(file);
                document.getElementById('searchKeywords').value = keywords.join('\n');
                addLog(`Loaded ${keywords.length} keywords from ${file.name}`, 'success');
            } catch (error) {
                addLog(`Error reading keywords file: ${error.message}`, 'error');
            }
        });
    }
    
    // Add some sample data for demo
    if (!localStorage.getItem('currentScenario')) {
        addLog('Select a scenario and configure it to get started', 'info');
    }
});