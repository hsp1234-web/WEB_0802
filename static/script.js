// --- 善狼 - 模擬數據 ---
// 模擬從後端取得的因子數據，將來可替換為實際 API
const factorsData = [
    { category: '市場情緒', name: 'VIX 恐慌指數', value: '13.5', change: -5.2, trend: [] },
    { category: '市場情緒', name: 'Put/Call Ratio', value: '0.85', change: 10.1, trend: [] },
    { category: '市場情緒', name: 'IV Skew 波動率偏斜', value: '115.2', change: 3.1, trend: [] },
    { category: '宏觀經濟', name: '美國十年債利率', value: '4.21%', change: -0.9, trend: [] },
    { category: '籌碼面 (台股)', name: '外資期貨未平倉', value: '-8,500', change: 25.1, trend: [] },
    { category: '技術分析', name: '台指 RSI (14D)', value: '58.2', change: 12.5, trend: [] },
];

// 模擬 yfinance 數據
function mockYFinanceData(factorName, startDate, endDate) {
    const days = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    const data = [];
    let lastValue = parseFloat(factorsData.find(f => f.name === factorName)?.value) || 50;

    for (let i = 0; i < days; i++) {
        // 模擬數據變化
        lastValue += (Math.random() - 0.5) * (i / days) * 10;
        data.push(lastValue);
    }
    return data;
}

const weeklyRawContent = {
    "2025年第14週": `**作者**：善甲狼a機智生活\n**標題**：買黃金跟債券避險\n**日期**：2025-03-31\n**文章內容**：\n買黃金跟債券避險\n484不如買 #VIX 阿?\n\n[交易數據]\n.VIX 標普500波動率指數\n現價: 23.91 ↑ (+2.26, +10.44%)\n\n歷史數據 (近5日圖表資訊):\n日期 數值 漲跌幅\n03/25 15.57 -10.93%\n03/26 18.05 3.29%\n03/27 20.54 17.51%\n03/28 23.03 31.72%\n03/31 25.51 45.94%`,
    "2025年第13週": `**作者**：善甲狼a機智生活\n**標題**：風平浪靜的一週\n**日期**：2025-03-24\n**文章內容**：\n本週市場波瀾不驚，指數在狹幅區間震盪。適合泡杯咖啡，靜待市場給出更明確的方向。`
};

const masterInsights = {
    '交易醫生': '核心策略: 跳空SOP1(逆勢封閉缺口), 跳空SOP2(順勢追擊)。\n觀點: 跳空日傳統技術指標易失真，傾向觀察K棒與價格行為。',
    '刀疤老二': '核心策略: 順勢而為，在上升趨勢中的回檔買進。\n觀點: 紀律至上，耐心等待高勝算機會，嚴控單筆風險(1-2%)。',
    'Vincent余鄭文': '核心策略: 投資框架三部曲(選對公司、等對價格、計劃下注)。\n觀點: 超額報酬源於「預期差」，從市價反推市場預期。',
    'Comemail': '核心策略: 逆向思考與價值挖掘("買冷賣熱")。\n觀點: 發掘市場關注度低、因短期非基本面因素被低估的股票。'
};

const factorStoreData = [
    { id: 'momentum', name: '動量因子', type: '技術', description: '衡量資產價格在一段時間內的變化速度。通常用於追隨趨勢策略。', calculation: '收盤價 / N日前的收盤價 - 1', source: '自訂計算', last_updated: '2025-07-18' },
    { id: 'value', name: '價值因子', type: '基本面', description: '衡量股票相對於其基本面（如每股收益、帳面價值）的估值。常用於價值投資策略。', calculation: '例如：本益比(PE Ratio)、股價淨值比(PB Ratio)的倒數。', source: '公司財報數據', last_updated: '2025-07-17' },
    { id: 'volatility_factor', name: '波動率因子', type: '風險', description: '衡量資產價格的變動程度。高波動率可能代表高風險或高機會。', calculation: '對數報酬率的滾動標準差，通常年化。', source: 'OHLCV數據', last_updated: '2025-07-18' },
    { id: 'liquidity_spread', name: '買賣價差因子', type: '市場微觀結構', description: '衡量市場的流動性和交易成本。高價差通常意味著流動性差。', calculation: '從OHLC數據估計買賣價差。', source: 'OHLC數據, bidask 函式庫', last_updated: '2025-07-18' },
    { id: 'sentiment_pcr', name: '買賣權比率 (PCR)', type: '情緒', description: '衡量市場情緒的逆向指標。高PCR表示市場看跌情緒較重。', calculation: '買賣權交易量 / 買入權交易量', source: '選擇權鏈數據', last_updated: '2025-07-16' },
    { id: 'alpha', name: 'Alpha', type: '績效', description: '衡量策略相對於市場基準的超額報酬。正 Alpha 表示策略表現優於市場。', calculation: '策略報酬 - (無風險報酬 + Beta * (市場報酬 - 無風險報酬))', source: '回測結果', last_updated: '2025-07-18' },
    { id: 'beta', name: 'Beta', type: '績效', description: '衡量策略與市場整體波動的相關性。Beta > 1 表示比市場更具波動性。', calculation: '策略與市場共變異數 / 市場變異數', source: '回測結果', last_updated: '2025-07-18' },
    // 新增的項目
    { id: 'dealer_stress_index', name: '一級交易商壓力指數', type: '系統性風險', description: '綜合多個指標（如 SOFR、利差、交易商部位）來衡量金融體系的總體壓力。數值越高代表金融系統壓力越大。', calculation: '多個因子的滾動百分位排名加權平均。', source: 'NY Fed, FRED', last_updated: '2025-07-18' },
    { id: 'risk_evaluation', name: '風險評估 (SML)', type: '風險', description: '這是多個風險模型（短期、中期、長期）的綜合結果，用於衡量在不同時間週期內資產的風險水平。分數越高，代表風險越高。', calculation: '多個指標（如乖離率、歷史波動率、VIX）的聚合風險分數。', source: 'YFinance, FRED', last_updated: '2025-07-18' },
];

const strategyExamples = {
    'ma_crossover': `# 範例策略: 移動平均線交叉
# 當短期均線向上穿越長期均線時買入
# 當短期均線向下穿越長期均線時賣出

def initialize(context):
    context.asset = sid(846) # 台指期
    context.fast_ma_length = 5
    context.slow_ma_length = 20
    # 這裡可以加入更多因子...

def handle_data(context, data):
    fast_ma = data.history(context.asset, 'price', context.fast_ma_length, '1d').mean()
    slow_ma = data.history(context.asset, 'price', context.slow_ma_length, '1d').mean()

    if fast_ma > slow_ma and context.portfolio.positions[context.asset] == 0:
        order_target_percent(context.asset, 1) # 全倉買入
    elif fast_ma < slow_ma and context.portfolio.positions[context.asset] > 0:
        order_target_percent(context.asset, 0) # 平倉
`,
    'maa_strategy': `# 範例策略: 最大幅度分析法 (MAA)
# 根據過去N天最大漲跌幅的機率分佈進行進場判斷

def initialize(context):
    context.asset = sid(2330) # 台積電
    context.window = 20 # 過去20天

def handle_data(context, data):
    # 這裡的邏輯需要外部資料來判斷MAA分佈
    # 假設我們有一個預先計算好的 'maa_signal' 因子
    maa_signal = data.get_current('maa_signal', context.asset)

    if maa_signal == 'buy':
        order_target_percent(context.asset, 0.5)
    elif maa_signal == 'sell':
        order_target_percent(context.asset, 0)
`,
    'volatility_entry': `# 範例策略: 進場波動率策略
# 在股票波動較小時進場，避免追高
# 限定股票交易量，傾向選擇較冷門的股票

def initialize(context):
    context.min_volume = 10000 # 最小成交量
    context.volatility_rank_threshold = 0.5 # 波動率排名前50%的股票

def handle_data(context, data):
    # 獲取所有股票的波動率
    volatilities = data.history(data.all_assets(), 'volatility', 20, '1d').iloc[-1]

    # 獲取所有股票的成交量
    volumes = data.history(data.all_assets(), 'volume', 1, '1d').iloc[-1]

    # 篩選出波動率低且成交量足夠的股票
    low_volatility_assets = volatilities[volatilities.rank(pct=True) < context.volatility_rank_threshold].index
    tradable_assets = volumes[volumes > context.min_volume].index

    buy_list = low_volatility_assets.intersection(tradable_assets)

    # 這裡的邏輯可以根據回測框架做更詳細的實現
    for asset in buy_list:
        order_target_percent(asset, 0.05) # 少量建倉
`
};

const strategyDescriptions = {
    'ma_crossover': {
        title: '移動平均線交叉策略',
        description: '這是一個經典的趨勢追隨策略。當短期移動平均線（快線）向上穿越長期移動平均線（慢線）時，被視為買入訊號；當快線向下穿越慢線時，則被視為賣出訊號。這個策略的核心思想是捕捉市場趨勢的變化。',
        details: [
            { label: '核心原理', value: '通過比較兩個不同週期的移動平均線來判斷市場趨勢。' },
            { label: '進場條件', value: '短期均線 > 長期均線' },
            { label: '出場條件', value: '短期均線 < 長期均線' },
            { label: '優點', value: '易於理解和實現，在趨勢明顯的市場中表現良好。' },
            { label: '缺點', value: '在震盪盤中容易產生頻繁的假訊號，導致虧損。' },
        ]
    },
    'maa_strategy': {
        title: '最大幅度分析法 (MAA) 策略',
        description: '最大幅度分析法（MAA）是一種用於判斷進場時機的進階方法。它基於對歷史價格在特定週期內最大漲跌幅的分佈進行分析，以預測未來潛在的漲跌幅度。策略會根據這個分析結果，在認為風險報酬比合適的時機進行交易。',
        details: [
            { label: '核心原理', value: '分析歷史價格變動的機率分佈，找出高勝算進場時機。' },
            { label: '進場條件', value: '當MAA訊號顯示當前處於潛在的上漲初期或止跌訊號出現時。' },
            { label: '出場條件', value: '當達到預期的獲利或止損點位時。' },
            { label: '優點', value: '有助於建立「人造的盤感」，提供更科學的進出場依據。' },
            { label: '缺點', value: '需要大量歷史數據進行分析，且對模型的準確性要求高。' },
        ]
    },
    'volatility_entry': {
        title: '進場波動率策略',
        description: '這個策略的核心思想是在股票波動性較小的時候進場，以避免在股價高點追高。同時，它也會限定股票的交易量，傾向選擇流動性足夠但又相對冷門的股票，以尋求超額報酬（Alpha）。這是一個反向思考的價值投資與波段交易結合的策略。',
        details: [
            { label: '核心原理', value: '「不要追高」並尋找市場關注度較低但體質良好的股票。' },
            { label: '進場條件', value: '股票波動率低於市場平均水平，且交易量符合特定門檻。' },
            { label: '出場條件', value: '當波動率顯著增加或達到預設的獲利/止損點。' },
            { label: '優點', value: '有助於控制風險，並可能在冷門股中找到潛在的超額報酬。' },
            { label: '缺點', value: '可能錯過快速上漲的股票，且需要更精細的篩選條件。' },
        ]
    }
};

// --- DOM 元素 ---
const htmlEl = document.documentElement;
const themeToggleBtn = document.getElementById('theme-toggle');
const fontIncreaseBtn = document.getElementById('font-increase');
const fontDecreaseBtn = document.getElementById('font-decrease');
const tabsContainer = document.getElementById('tabs');
const tabContents = document.querySelectorAll('.tab-content');
const weekSelector = document.getElementById('week-selector');
const rawContentContainer = document.getElementById('raw-content');
const masterSelectorContainer = document.getElementById('master-insights-selector');
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const factorsListContainer = document.getElementById('factors-list');
const strategySelector = document.getElementById('strategy-selector');
const strategyEditor = document.getElementById('strategy-editor');
const factorStoreContainer = document.getElementById('factor-store');
const strategyInfoContainer = document.getElementById('strategy-info');
const pipelineSelector = document.getElementById('pipeline-selector');
const runPipelineBtn = document.getElementById('run-pipeline-btn');
const yfinanceStatusEl = document.getElementById('yfinance-status');
const fredStatusEl = document.getElementById('fred-status');
const factorTableBody = document.getElementById('factor-table-body');
const dateRangeStartEl = document.getElementById('date-range-start');
const dateRangeEndEl = document.getElementById('date-range-end');
const applyDateRangeBtn = document.getElementById('apply-date-range-btn');
let backtestChartInstance = null;

// 鳳凰轉錄儀的 DOM 元素
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const logContainer = document.getElementById('log-container');
const cpuUsageEl = document.getElementById('cpu-usage');
const gpuUsageEl = document.getElementById('gpu-usage');
const resultSection = document.getElementById('result-section');
const standbySection = document.getElementById('standby-section');
const transcriptOutput = document.getElementById('transcript-output');
const copyBtn = document.getElementById('copy-btn');
const downloadBtn = document.getElementById('download-btn');
const systemStatusEl = document.getElementById('system-status');

// --- 通用核心函式 ---
function applyTheme(theme) {
    htmlEl.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('color-theme', theme);
    if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}
function setFontSize(size) {
    const newSize = Math.max(12, Math.min(size, 20));
    htmlEl.style.fontSize = `${newSize}px`;
    localStorage.setItem('fontSize', newSize);
}

// --- 善狼 - 核心功能 ---
function renderMasterSelector() {
    masterSelectorContainer.innerHTML = '';
    for (const master in masterInsights) {
        masterSelectorContainer.innerHTML += `
            <label class="flex items-center space-x-2 text-sm">
                <input type="checkbox" name="master" value="${master}" class="rounded">
                <span>${master}</span>
            </label>
        `;
    }
}

function updateShanJiaLangContent() {
    const selectedWeek = weekSelector.value;
    rawContentContainer.textContent = weeklyRawContent[selectedWeek] || "查無此週次資料。";
    resetAndStartChat();
}

function addChatMessage(role, content) {
    const bubbleClass = role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai';
    const messageDiv = document.createElement('div');
    messageDiv.className = `${bubbleClass} p-4 rounded-lg max-w-full`;
    let htmlContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    htmlContent = htmlContent.replace(/\n/g, '<br>');
    messageDiv.innerHTML = `<div class="prose prose-sm dark:prose-invert max-w-none">${htmlContent}</div>`;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function resetAndStartChat() {
    chatWindow.innerHTML = '';
    const initialAIResponse = `**AI 助理初步分析 (${weekSelector.value})**\n研究員您好，已載入本週文本，初步分析如下：\n\n**A. 善甲狼核心觀點：**\n本週市場情緒極度恐慌，善甲狼透過VIX上漲的貼文，暗示避險情緒高漲。他對盲目抄底的行為提出質疑，並強調在這種時刻應「認真上班」，保持冷靜。\n\n**B. 市場重點回顧：**\nVIX指數從15.57飆升至25.51，週漲幅驚人，顯示市場出現重大利空或不確定性。\n\n**C. 看到->想到->做到：**\n* **看到：** VIX連續大漲，市場恐慌。\n* **想到：** 傳統避險策略可能失效，直接交易波動率成為選項。\n* **做到：** 若判斷恐慌將持續，可小倉位佈局VIX相關產品；若判斷恐慌見頂，可等待賣出波動率的機會。\n\n請勾選您想融入的大師觀點，或直接下達指令以進行下一步分析。`;
    addChatMessage('ai', initialAIResponse);
}

function handleSendInstruction() {
    const userInput = chatInput.value.trim();
    if (!userInput) return;
    addChatMessage('user', userInput);
    chatInput.value = '';
    const selectedMasters = Array.from(document.querySelectorAll('input[name="master"]:checked')).map(cb => cb.value);
    setTimeout(() => {
        const aiFinalResponse = `**綜合分析報告與量化建議**\n\n研究員您好，根據您的指令，並融合 **${selectedMasters.length > 0 ? selectedMasters.join('、') : '預設'}** 的觀點，我已完成深度分析。\n\n**質化洞察總結:**\n市場處於由VIX飆升引發的極度恐慌中。善甲狼建議保守，而交易醫生的「跳空逆勢」與刀疤老二的「順勢回檔」策略在此刻出現分歧。這表明市場可能存在短線反彈（逆勢）與趨勢延續（順勢）的雙重機會，關鍵在於識別訊號的強度。\n\n**可量化策略方向建議 (供策略回測中心參考):**\n\n**策略一：恐慌頂部反轉 (逆勢，參考交易醫生)**\n* **進場條件:**\n    1.  **VIX > 30** (定義極度恐慌)\n    2.  **當日K線收盤價 > 開盤價** (出現初步止穩信號)\n    3.  **成交量 > 20日均量 * 1.2** (放量止跌)\n* **出場條件:**\n    * **停利:** **獲利達 5%** 或 **RSI(14) > 60**\n    * **停損:** **跌破進場K線的最低價**\n\n**策略二：恐慌趨勢跟隨 (順勢，參考刀疤老二)**\n* **進場條件 (放空):**\n    1.  **收盤價 < 20日均線** (確認空頭趨勢)\n    2.  **當日反彈未站上5日均線** (回檔無力)\n    3.  **VIX 週變動率 > 20%** (恐慌加劇)\n* **出場條件:**
    * **停利:** **風險報酬比 1:3**
    * **停損:** **收盤價站上10日均線**
\n請指示是否將以上任一策略參數化並送入「策略回測中心」進行回測。`;
        addChatMessage('ai', aiFinalResponse);
    }, 1000);
}

function renderFactorsList(startDate, endDate) {
    if (!factorsListContainer) return;
    factorsListContainer.innerHTML = '';

    factorsData.forEach((factor, index) => {
        // 模擬獲取趨勢數據
        const trendData = mockYFinanceData(factor.name, startDate, endDate);
        const startValue = trendData[0];
        const endValue = trendData[trendData.length - 1];
        const change = ((endValue - startValue) / startValue * 100).toFixed(1);
        const isUp = change > 0;
        const changeColorClass = isUp ? 'change-up' : 'change-down';
        const changeIcon = isUp ? '▲' : '▼';

        const factorRow = `
            <div class="flex items-center justify-between p-3 rounded-lg transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-gray-800/50">
                <div class="w-1/3"><p class="font-semibold">${factor.name}</p><p class="text-xs text-gray-500 dark:text-gray-400">${factor.category}</p></div>
                <div class="w-1/4 h-8"><canvas id="chart-${index}" height="32"></canvas></div>
                <div class="w-1/3 text-right"><p class="font-bold text-lg">${endValue.toFixed(2)}</p><p class="text-sm font-semibold ${changeColorClass}">${change > 0 ? '+' : ''}${change}% ${changeIcon}</p></div>
            </div>`;
        factorsListContainer.insertAdjacentHTML('beforeend', factorRow);

        // 將趨勢數據存回 factorsData 以便繪圖
        factor.trend = trendData;
    });
    renderAllSparklines();
}

function renderAllSparklines() {
    const isDarkMode = document.documentElement.classList.contains('dark');
    factorsData.forEach((factor, index) => {
        const ctx = document.getElementById(`chart-${index}`)?.getContext('2d');
        if (!ctx) return;
        const chartId = `sparkline_${index}`;
        if (window[chartId]) window[chartId].destroy();
        const isUp = factor.trend[factor.trend.length - 1] > factor.trend[0];
        const chartColor = isUp ? (isDarkMode ? '#F28B82' : '#EA4335') : (isDarkMode ? '#81C995' : '#34A853');
        window[chartId] = new Chart(ctx, {
            type: 'line',
            data: { labels: Array(factor.trend.length).fill(''), datasets: [{ data: factor.trend, borderColor: chartColor, borderWidth: 2, tension: 0.3 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { x: { display: false }, y: { display: false } }, plugins: { legend: { display: false }, tooltip: { enabled: false } }, elements: { point: { radius: 0 } } }
        });
    });
}

function applyDateRange() {
    const startDate = new Date(dateRangeStartEl.value);
    const endDate = new Date(dateRangeEndEl.value);

    if (!startDate.getTime() || !endDate.getTime()) {
        alert('請選擇有效的日期範圍。');
        return;
    }

    if (startDate > endDate) {
        alert('起始日期不能晚於結束日期。');
        return;
    }

    renderFactorsList(startDate, endDate);
}

function renderFactorsStore() {
    if (!factorStoreContainer) return;
    factorStoreContainer.innerHTML = '';
    factorStoreData.forEach(factor => {
        const factorCard = `
            <div class="gemini-panel rounded-xl p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors">
                <h3 class="font-bold text-lg gemini-gradient-text">${factor.name}</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-2">${factor.type} 因子</p>
                <p class="text-sm line-clamp-3">${factor.description}</p>
                <button onclick="showFactorDetails('${factor.id}')" class="mt-2 text-sm text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">查看詳細</button>
            </div>
        `;
        factorStoreContainer.insertAdjacentHTML('beforeend', factorCard);
    });
}

function showFactorDetails(factorId) {
    const factor = factorStoreData.find(f => f.id === factorId);
    if (!factor) return;

    const modalContent = `
        <h3 class="font-bold text-2xl gemini-gradient-text mb-2">${factor.name}</h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">${factor.type} 因子</p>
        <div class="space-y-4 text-left">
            <div>
                <p class="font-semibold">描述：</p>
                <p class="text-gray-700 dark:text-gray-300">${factor.description}</p>
            </div>
            <div>
                <p class="font-semibold">計算方式：</p>
                <p class="text-gray-700 dark:text-gray-300">${factor.calculation}</p>
            </div>
            <div>
                <p class="font-semibold">資料來源：</p>
                <p class="text-gray-700 dark:text-gray-300">${factor.source}</p>
            </div>
        </div>
        <div class="mt-6 flex justify-end">
            <button onclick="closeModal()" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg font-bold hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors">關閉</button>
        </div>
    `;

    showModal(modalContent);
}

function showModal(content) {
    const modal = document.createElement('div');
    modal.id = 'info-modal';
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
    modal.innerHTML = `
        <div class="gemini-panel rounded-xl p-6 w-full max-w-lg mx-4">
            ${content}
        </div>
    `;
    document.body.appendChild(modal);
}

function closeModal() {
    const modal = document.getElementById('info-modal');
    if (modal) modal.remove();
}

function loadStrategyExample() {
    const selectedStrategy = strategySelector.value;
    strategyEditor.value = strategyExamples[selectedStrategy];
    renderStrategyInfo(selectedStrategy);
}

function renderStrategyInfo(strategyId) {
    const info = strategyDescriptions[strategyId];
    if (!info) {
        strategyInfoContainer.innerHTML = `<p class="text-gray-500">此策略無詳細說明。</p>`;
        return;
    }

    let detailsHtml = info.details.map(d => `
        <div>
            <p class="font-semibold text-gray-500 dark:text-gray-400">${d.label}</p>
            <p>${d.value}</p>
        </div>
    `).join('');

    strategyInfoContainer.innerHTML = `
        <h4 class="font-bold text-xl gemini-gradient-text mb-2">${info.title}</h4>
        <p class="mb-4">${info.description}</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            ${detailsHtml}
        </div>
    `;
}

function renderBacktestChart() {
    if (backtestChartInstance) backtestChartInstance.destroy();
    const ctx = document.getElementById('backtestChart')?.getContext('2d');
    if (!ctx) return;
    const isDarkMode = document.documentElement.classList.contains('dark');
    backtestChartInstance = new Chart(ctx, {
        type: 'line',
        data: { labels: ['一月', '二月', '三月', '四月', '五月', '六月'], datasets: [{ label: '權益曲線', data: [100, 110, 105, 125, 130, 145], borderColor: '#4285F4', backgroundColor: 'rgba(66, 133, 244, 0.1)', fill: true, tension: 0.3 }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { display: false }, grid: { display: false } }, y: { ticks: { display: false }, grid: { color: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' } } }, plugins: { legend: { display: false } }, elements: { point: { radius: 1 } } }
    });
}

function addSystemLog(level, message) {
    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    const levelColor = { '系統': 'text-sky-400', '成功': 'text-green-400', '錯誤': 'text-red-400', '進度': 'text-yellow-400' }[level] || 'text-gray-400';
    const logContainer = document.querySelector('#tab-content-system .h-48');

    const logEntry = document.createElement('p');
    logEntry.innerHTML = `<span class="${levelColor}">[${level}]</span> [${timestamp}] ${message}`;
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function runPipeline() {
    const pipeline = pipelineSelector.value;
    const pipelineMap = {
        'p4_stock_factor_generation': '生成股票相關因子的生產線',
        'p5_crypto_factor_generation': '生成加密貨幣相關因子的生產線',
        'p6_simulation_training': '訓練因子模擬器的管線'
    };

    addSystemLog('進度', `開始運行管線: ${pipelineMap[pipeline]}...`);

    // 模擬異步運行
    yfinanceStatusEl.textContent = '獲取數據中...';
    fredStatusEl.textContent = '待機中...';

    setTimeout(() => {
        addSystemLog('成功', `${pipelineMap[pipeline]} 執行完成。`);
        yfinanceStatusEl.textContent = '連線成功';
        fredStatusEl.textContent = '待機中...';

        // 模擬更新因子庫
        renderFactorTable();
    }, 3000);
}

function renderFactorTable() {
    if (!factorTableBody) return;
    factorTableBody.innerHTML = '';
    factorStoreData.forEach(factor => {
        const row = `
            <tr class="hover:bg-gray-100 dark:hover:bg-gray-800/50 cursor-pointer" onclick="showFactorDetails('${factor.id}')">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">${factor.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${factor.type}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${factor.last_updated}</td>
            </tr>
        `;
        factorTableBody.insertAdjacentHTML('beforeend', row);
    });
}

// --- 鳳凰轉錄儀 - 核心功能 ---
const addLog = (level, message) => {
    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    const levelColor = { '系統': 'text-sky-400', '成功': 'text-green-400', '錯誤': 'text-red-400', '進度': 'text-yellow-400' }[level] || 'text-gray-400';

    const logEntry = document.createElement('div');
    logEntry.className = 'phoenix-log-entry p-2 rounded-md';
    logEntry.innerHTML = `
        <div>
            <span class="text-gray-500 mr-2">[${timestamp}]</span>
            <span class="${levelColor}">[${level}]</span>
            <span class="ml-2 text-[color:var(--text-color)]">${message}</span>
        </div>`;
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
    return logEntry;
};

const updateProgressBar = (logEntry, progress) => {
    let bar = logEntry.querySelector('.phoenix-progress-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.className = 'phoenix-progress-bar';
        bar.innerHTML = `<div class="phoenix-progress-bar-fill"></div>`;
        logEntry.appendChild(bar);
    }
    bar.querySelector('.phoenix-progress-bar-fill').style.width = `${progress}%`;
};

const handleFiles = (files) => {
    if (files.length === 0) return;
    transcriptOutput.textContent = '';
    addLog('系統', `收到 ${files.length} 個檔案，準備加入佇列。`);
    Array.from(files).forEach(uploadAndProcessFile);
};

const uploadAndProcessFile = async (file) => {
    const logEntry = addLog('進度', `開始上傳檔案: ${file.name}`);
    const formData = new FormData();
    formData.append('file', file);

    try {
        // Step 1: Upload the file and get a task ID
        const uploadResponse = await fetch('/transcription/upload', {
            method: 'POST',
            body: formData,
        });

        if (!uploadResponse.ok) {
            throw new Error(`上傳失敗: ${uploadResponse.statusText}`);
        }

        const uploadData = await uploadResponse.json();
        const taskId = uploadData.task_id;
        logEntry.dataset.taskId = taskId;
        updateLogMessage(logEntry, '進度', `上傳成功，任務ID: ${taskId}。正在等待處理...`);

        // Step 2: Start polling for the result
        pollStatus(taskId, logEntry);

    } catch (error) {
        console.error('上傳或處理過程中發生錯誤:', error);
        updateLogMessage(logEntry, '錯誤', `處理失敗: ${error.message}`);
    }
};

const pollStatus = (taskId, logEntry) => {
    const intervalId = setInterval(async () => {
        try {
            const statusResponse = await fetch(`/transcription/status/${taskId}`);
            if (!statusResponse.ok) {
                // Stop polling on server error
                clearInterval(intervalId);
                updateLogMessage(logEntry, '錯誤', `無法獲取狀態: ${statusResponse.statusText}`);
                return;
            }

            const statusData = await statusResponse.json();

            switch (statusData.status) {
                case 'pending':
                    updateLogMessage(logEntry, '進度', '任務排隊中...');
                    break;
                case 'processing':
                    updateLogMessage(logEntry, '進度', '正在轉錄中，請稍候...');
                    // Here you could add a more detailed progress bar if the backend provided it
                    updateProgressBar(logEntry, 50); // Simulate 50% progress
                    break;
                case 'completed':
                    clearInterval(intervalId);
                    updateLogMessage(logEntry, '成功', '轉錄完成！');
                    updateProgressBar(logEntry, 100);

                    // Append result to the main output
                    const existingText = transcriptOutput.textContent;
                    const newTranscript = `--- ${logEntry.dataset.fileName || '未知檔案'} ---\n${statusData.result_text}\n\n`;
                    transcriptOutput.textContent = existingText + newTranscript;

                    // Show the result section
                    standbySection.classList.add('opacity-0', 'pointer-events-none');
                    resultSection.classList.remove('opacity-0', 'pointer-events-none');
                    break;
                case 'failed':
                    clearInterval(intervalId);
                    updateLogMessage(logEntry, '錯誤', `轉錄失敗: ${statusData.error_message}`);
                    break;
            }

        } catch (error) {
            clearInterval(intervalId);
            console.error('輪詢狀態時發生錯誤:', error);
            updateLogMessage(logEntry, '錯誤', '輪詢時發生網路錯誤。');
        }
    }, 2000); // Poll every 2 seconds
};

const updateLogMessage = (logEntry, level, message) => {
    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    const levelColor = { '系統': 'text-sky-400', '成功': 'text-green-400', '錯誤': 'text-red-400', '進度': 'text-yellow-400' }[level] || 'text-gray-400';
    const firstChild = logEntry.querySelector('div');
    if(firstChild) {
         firstChild.innerHTML = `
            <span class="text-gray-500 mr-2">[${timestamp}]</span>
            <span class="${levelColor}">[${level}]</span>
            <span class="ml-2 text-[color:var(--text-color)]">${message}</span>`;
    }
};

// --- 事件監聽器綁定 ---

// 主題切換
themeToggleBtn.addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('color-theme', isDark ? 'dark' : 'light');
    applyTheme(isDark ? 'dark' : 'light');

    // 重新渲染圖表以適應新主題
    applyDateRange(); // 呼叫新的函式
    renderBacktestChart();
});

// 字體大小
fontIncreaseBtn.addEventListener('click', () => setFontSize(parseFloat(getComputedStyle(htmlEl).fontSize) + 1));
fontDecreaseBtn.addEventListener('click', () => setFontSize(parseFloat(getComputedStyle(htmlEl).fontSize) - 1));

// 策略選擇
strategySelector.addEventListener('change', loadStrategyExample);

// 運行管線
runPipelineBtn.addEventListener('click', runPipeline);

// 日期範圍選擇
applyDateRangeBtn.addEventListener('click', applyDateRange);

// Tab 選單
tabsContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('tab')) {
        const targetTab = e.target.dataset.tab;
        tabsContainer.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        e.target.classList.add('active');
        tabContents.forEach(content => {
            content.id === `tab-content-${targetTab}` ? content.classList.remove('hidden') : content.classList.add('hidden');
        });
        if(targetTab === 'lab') {
            renderBacktestChart();
            loadStrategyExample();
        }
        if(targetTab === 'snapshot') applyDateRange(); // 啟用時載入預設日期範圍
        if(targetTab === 'factors') renderFactorsStore();
        if(targetTab === 'transcription') {
            // 轉錄儀分頁啟用時，初始化其狀態
            standbySection.classList.remove('opacity-0', 'pointer-events-none');
            resultSection.classList.add('opacity-0', 'pointer-events-none');
            logContainer.innerHTML = '';
            transcriptOutput.textContent = '';
        }
        if(targetTab === 'db_management') {
            renderFactorTable();
        }
    }
});

// 善狼功能事件監聽
weekSelector.addEventListener('change', updateShanJiaLangContent);
sendButton.addEventListener('click', handleSendInstruction);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendInstruction();
    }
});

// 鳳凰轉錄儀功能事件監聽
uploadArea.addEventListener('click', () => fileInput.click());
['dragenter', 'dragover'].forEach(e => uploadArea.addEventListener(e, (evt) => {
    evt.preventDefault();
    uploadArea.classList.add('border-sky-400');
}));
['dragleave', 'drop'].forEach(e => uploadArea.addEventListener(e, (evt) => {
    evt.preventDefault();
    uploadArea.classList.remove('border-sky-400');
}));
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
uploadArea.addEventListener('drop', (e) => handleFiles(e.dataTransfer.files));

// 複製按鈕功能
copyBtn.addEventListener('click', () => {
    if (!transcriptOutput.textContent) return;
    const textarea = document.createElement('textarea');
    textarea.value = transcriptOutput.textContent;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    const originalHTML = copyBtn.innerHTML;
    copyBtn.innerHTML = `<i data-lucide="check" class="lucide lucide-check mr-2"></i><span>已複製！</span>`;
    if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
    setTimeout(() => {
        copyBtn.innerHTML = originalHTML;
        if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
            lucide.createIcons();
        }
    }, 2000);
});

// 下載按鈕功能
downloadBtn.addEventListener('click', () => {
    if (!transcriptOutput.textContent) return;
    const blob = new Blob([transcriptOutput.textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

// --- 初始化應用程式 ---
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('color-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(savedTheme || (prefersDark ? 'dark' : 'light'));
    const savedFontSize = localStorage.getItem('fontSize');
    if (savedFontSize) setFontSize(parseFloat(savedFontSize));

    // 設定預設日期範圍
    const today = new Date();
    const lastMonth = new Date();
    lastMonth.setMonth(today.getMonth() - 1);
    dateRangeStartEl.value = lastMonth.toISOString().slice(0, 10);
    dateRangeEndEl.value = today.toISOString().slice(0, 10);

    // 初始化善狼頁面
    renderMasterSelector();
    updateShanJiaLangContent();
    loadStrategyExample(); // 載入預設策略範例
    applyDateRange(); // 載入預設日期範圍的趨勢圖

    // 模擬系統監控數據
    setInterval(() => {
        if (document.getElementById('tab-content-system').classList.contains('hidden')) return;
        cpuUsageEl.textContent = `${(Math.random() * 20 + 10).toFixed(1)}%`;
        gpuUsageEl.textContent = `${(Math.random() * 30 + 15).toFixed(1)}%`;
    }, 2000);
});
