/**
 * API 调用模块
 */

const API = {
    baseUrl: '',
    
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                if (Array.isArray(value)) {
                    value.forEach(v => url.searchParams.append(key, v));
                } else {
                    url.searchParams.set(key, value);
                }
            }
        });
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },
    
    // 总览统计
    async getOverview() {
        return this.get('/api/stats/overview');
    },
    
    // 各会议统计
    async getVenues() {
        return this.get('/api/stats/venues');
    },
    
    // 单会议详情
    async getVenueDetail(venue) {
        return this.get(`/api/stats/venue/${venue}`);
    },
    
    // Top 关键词
    async getTopKeywords(params = {}) {
        return this.get('/api/keywords/top', params);
    },
    
    // 关键词趋势
    async getKeywordTrends(keywords = [], venue = null) {
        return this.get('/api/keywords/trends', { keyword: keywords, venue });
    },
    
    // 会议对比
    async getComparison(year = null, limit = 10) {
        return this.get('/api/keywords/comparison', { year, limit });
    },
    
    // 词云数据
    async getWordcloudData(venue = null, year = null, limit = 100) {
        return this.get('/api/keywords/wordcloud', { venue, year, limit });
    },
    
    // 新兴关键词
    async getEmergingKeywords() {
        return this.get('/api/keywords/emerging');
    }
};

// 导出供其他模块使用
window.API = API;
