/**
 * 主程序入口
 */

// 全局状态
const state = {
    venue: '',
    year: '',
    venues: [],
    years: []
};

/**
 * 初始化
 */
async function init() {
    console.log('🚀 DeepTrender Dashboard 初始化中...');

    try {
        await loadOverview();
        await loadFilters();
        await refreshData();
        await loadVenueCards();

        console.log('✅ 初始化完成');
        
        if (window.Toast) {
            Toast.success('数据加载完成', 2000);
        }
    } catch (error) {
        console.error('❌ 初始化失败:', error);
        
        if (window.Toast) {
            Toast.error('初始化失败，请刷新页面重试');
        }
    }
}

/**
 * 加载总览统计
 */
async function loadOverview() {
    try {
        const overview = await API.getOverview();

        document.getElementById('stat-papers').textContent =
            overview.total_papers.toLocaleString();
        document.getElementById('stat-keywords').textContent =
            overview.total_keywords.toLocaleString();
        document.getElementById('stat-venues').textContent =
            overview.total_venues;
        document.getElementById('stat-years').textContent =
            overview.year_range;

        state.venues = overview.venues;
        state.years = overview.years;
    } catch (error) {
        console.error('加载总览失败:', error);
    }
}

/**
 * 加载筛选选项
 */
async function loadFilters() {
    const venueSelect = document.getElementById('filter-venue');
    const yearSelect = document.getElementById('filter-year');

    // 填充会议选项
    state.venues.forEach(venue => {
        const option = document.createElement('option');
        option.value = venue;
        option.textContent = venue;
        venueSelect.appendChild(option);
    });

    // 填充年份选项（降序）
    [...state.years].sort((a, b) => b - a).forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    });

    // 绑定事件
    venueSelect.addEventListener('change', () => {
        state.venue = venueSelect.value;
        refreshData();
    });

    yearSelect.addEventListener('change', () => {
        state.year = yearSelect.value;
        refreshData();
    });
}

/**
 * 刷新所有数据
 */
async function refreshData() {
    await Promise.all([
        loadWordcloud(),
        loadTopKeywords(),
        loadTrends()
    ]);
}

/**
 * 加载词云
 */
async function loadWordcloud() {
    const containerId = 'chart-wordcloud';
    Charts.showLoading(containerId);

    try {
        const data = await API.getWordcloudData(
            state.venue || null,
            state.year || null,
            100
        );
        
        if (!data || data.length === 0) {
            Charts.showEmpty(containerId, '暂无关键词数据');
            return;
        }
        
        Charts.renderWordcloud(containerId, data);
    } catch (error) {
        console.error('加载词云失败:', error);
        Charts.showError(containerId, '词云加载失败，请重试');
    } finally {
        Charts.hideLoading(containerId);
    }
}

/**
 * 加载 Top 关键词
 */
async function loadTopKeywords() {
    const containerId = 'chart-top-keywords';
    Charts.showLoading(containerId);

    try {
        const data = await API.getTopKeywords({
            venue: state.venue || null,
            year: state.year || null,
            limit: 20
        });
        
        if (!data || data.length === 0) {
            Charts.showEmpty(containerId, '暂无关键词数据');
            return;
        }
        
        Charts.renderBarChart(containerId, data);
    } catch (error) {
        console.error('加载 Top 关键词失败:', error);
        Charts.showError(containerId, 'Top 关键词加载失败，请重试');
    } finally {
        Charts.hideLoading(containerId);
    }
}

/**
 * 加载趋势图
 */
async function loadTrends() {
    const containerId = 'chart-trends';
    Charts.showLoading(containerId);

    try {
        const trends = await API.getKeywordTrends([], state.venue || null);
        
        if (!trends || trends.length === 0) {
            Charts.showEmpty(containerId, '暂无趋势数据');
            return;
        }
        
        Charts.renderTrendChart(containerId, trends);
    } catch (error) {
        console.error('加载趋势失败:', error);
        Charts.showError(containerId, '趋势数据加载失败，请重试');
    } finally {
        Charts.hideLoading(containerId);
    }
}

/**
 * 加载会议卡片
 */
async function loadVenueCards() {
    const container = document.getElementById('venues-grid');
    if (!container) return;

    try {
        const venues = await API.getVenues();

        container.innerHTML = venues.map(venue => `
            <div class="venue-card" onclick="goToVenue('${venue.name}')">
                <div class="venue-card-header">
                    <span class="venue-name">${venue.name}</span>
                    <span class="venue-count">${venue.paper_count} 篇</span>
                </div>
                <div class="venue-keywords" id="venue-kw-${venue.name}">
                    <span class="keyword-tag">加载中...</span>
                </div>
            </div>
        `).join('');

        // 异步加载每个会议的关键词
        for (const venue of venues) {
            loadVenueKeywords(venue.name);
        }
    } catch (error) {
        console.error('加载会议卡片失败:', error);
    }
}

/**
 * 加载会议关键词标签
 */
async function loadVenueKeywords(venueName) {
    try {
        const keywords = await API.getTopKeywords({ venue: venueName, limit: 5 });
        const container = document.getElementById(`venue-kw-${venueName}`);
        if (container && keywords.length > 0) {
            container.innerHTML = keywords.map(k =>
                `<span class="keyword-tag">${k.keyword}</span>`
            ).join('');
        }
    } catch (error) {
        console.error(`加载 ${venueName} 关键词失败:`, error);
    }
}

/**
 * 跳转到会议详情
 */
function goToVenue(venueName) {
    window.location.href = `/venue.html?venue=${venueName}`;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
