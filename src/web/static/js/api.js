/**
 * API 调用模块
 * 
 * 支持两种模式：
 * 1. API 模式：从 Flask 后端 /api/* 读取数据
 * 2. 静态模式：从 ./data/*.json 读取预导出的数据
 */

const API = {
    baseUrl: '',
    isStatic: false,
    staticDetected: false,
    
    async detectMode() {
        if (this.staticDetected) return this.isStatic;
        
        try {
            const response = await fetch('/api/health', { method: 'HEAD', cache: 'no-cache' });
            this.isStatic = !response.ok;
        } catch (e) {
            this.isStatic = true;
        }
        
        this.staticDetected = true;
        console.log(`🌐 运行模式: ${this.isStatic ? '静态 (GitHub Pages)' : 'API (Flask)'}`);
        return this.isStatic;
    },
    
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
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
                throw new Error(errorMessage);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            
            if (window.Toast) {
                if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                    Toast.error('网络连接失败，请检查网络设置');
                } else if (error.message.includes('404')) {
                    Toast.error('请求的资源不存在');
                } else if (error.message.includes('500')) {
                    Toast.error('服务器错误，请稍后重试');
                } else {
                    Toast.error(`请求失败: ${error.message}`);
                }
            }
            
            throw error;
        }
    },
    
    async getStatic(path) {
        try {
            const response = await fetch(path);
            if (!response.ok) {
                throw new Error(`Failed to load ${path}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Static data error [${path}]:`, error);
         throw error;
        }
    },
    
    async getOverview() {
        await this.detectMode();
        
        if (this.isStatic) {
            const venues = await this.getStatic('./data/venues/venues_index.json');
            const totalPapers = venues.reduce((sum, v) => sum + v.paper_count, 0);
            const totalKeywords = new Set();
            venues.forEach(v => v.top_keywords.forEach(k => totalKeywords.add(k.keyword)));
            const years = [...new Set(venues.flatMap(v => v.years_available))].sort();
            
            return {
                total_papers: totalPapers,
                total_keywords: totalKeywords.size,
                total_venues: venues.length,
                venues: venues.map(v => v.name),
                years: years,
                year_range: years.length > 0 ? `${Math.min(...years)}-${Math.max(...years)}` : 'N/A'
            };
        }
        
        return this.get('/api/stats/overview');
    },
    
    async getVenues() {
        await this.detectMode();
        
        if (this.isStatic) {
            const venues = await this.getStatic('./data/venues/venues_index.json');
            return venues.map(v => ({
                name: v.name,
                paper_count: v.paper_count,
                years: v.years_available
            }));
        }
        
        return this.get('/api/stats/venues');
    },
    
    async getVenueDetail(venue) {
        await this.detectMode();
        
        if (this.isStatic) {
            const venuesIndex = await this.getStatic('./data/venues/venues_index.json');
            const venueInfo = venuesIndex.find(v => v.name === venue);
            
            if (!venueInfo) {
                throw new Error(`Venue ${venue} not found`);
            }
            
            const topKeywords = await this.getStatic(`./data/venues/venue_${venue}_top_keywords.json`);
            
            const yearlyStats = Object.entries(topKeywords).map(([year, keywords]) => ({
                year: parseInt(year),
                paper_count: keywords.reduce((sum, k) => sum + k.count, 0),
                top_keywords: keywords.slice(0, 10)
            })).sort((a, b) => b.year - a.year);
            
            return {
                venue: venue,
                total_papers: venueInfo.paper_count,
                years: venueInfo.years_available,
                yearly_stats: yearlyStats
            };
        }
        
        return this.get(`/api/stats/venue/${venue}`);
    },
    
    async getTopKeywords(params = {}) {
        await this.detectMode();
        
        if (this.isStatic && params.venue) {
            const topKeywords = await this.getStatic(`./data/venues/venue_${params.venue}_top_keywords.json`);
            
            if (params.year) {
                return topKeywords[params.year] || [];
            }
            
            const allKeywords = {};
            Object.values(topKeywords).forEach(yearData => {
                yearData.forEach(item => {
                    if (!allKeywords[item.keyword]) {
                        allKeywords[item.keyword] = 0;
                    }
                    allKeywords[item.keyword] += item.count;
                });
            });
            
            return Object.entries(allKeywords)
                .map(([keyword, count]) => ({ keyword, count }))
                .sort((a, b) => b.count - a.count)
                .slice(0, params.limit || 50);
        }
        
        return this.get('/api/keywords/top', params);
    },
    
    async getKeywordTrends(keywords = [], venue = null) {
        await this.detectMode();
        
        if (this.isStatic && venue) {
            const trends = await this.getStatic(`./data/venues/venue_${venue}_keyword_trends.json`);
            
            const result = [];
            keywords.forEach(kw => {
                if (trends[kw]) {
                    const years = trends[kw].map(d => d.year);
                    const counts = trends[kw].map(d => d.count);
                    result.push({ keyword: kw, years, counts });
                }
            });
            
            return result;
        }
        
        return this.get('/api/keywords/trends', { keyword: keywords, venue });
    },
    
    async getComparison(year = null, limit = 10) {
        await this.detectMode();
        
        if (this.isStatic) {
            const venuesIndex = await this.getStatic('./data/venues/venues_index.json');
            const result = { year: year, venues: {} };
            
            for (const venueInfo of venuesIndex) {
                try {
                    const topKeywords = await this.getStatic(`./data/venues/venue_${venueInfo.name}_top_keywords.json`);
                    
                    if (year && topKeywords[year]) {
                        result.venues[venueInfo.name] = topKeywords[year].slice(0, limit);
                    } else if (!year) {
                        const latestYear = Math.max(...Object.keys(topKeywords).map(Number));
                        result.venues[venueInfo.name] = topKeywords[latestYear].slice(0, limit);
                    }
                } catch (e) {
                    console.warn(`Failed to load data for ${venueInfo.name}`);
                }
            }
            
            return result;
        }
        
        return this.get('/api/keywords/comparison', { year, limit });
    },
    
    async getWordcloudData(venue = null, year = null, limit = 100) {
        await this.detectMode();
        
        if (this.isStatic && venue) {
            const topKeywords = await this.getStatic(`./data/venues/venue_${venue}_top_keywords.json`);
            
            let data = [];
            if (year && topKeywords[year]) {
                data = topKeywords[year];
            } else {
                const allKeywords = {};
                Object.values(topKeywords).forEach(yearData => {
                    yearData.forEach(item => {
                        if (!allKeywords[item.keyword]) {
                            allKeywords[item.keyword] = 0;
                        }
                        allKeywords[item.keyword] += item.count;
                    });
                });
                data = Object.entries(allKeywords).map(([keyword, count]) => ({ keyword, count }));
            }
            
            return data
                .sort((a, b) => b.count - a.count)
                .slice(0, limit)
                .map(item => ({ name: item.keyword, value: item.count }));
        }
        
        return this.get('/api/keywords/wordcloud', { venue, year, limit });
    },
    
    async getEmergingKeywords() {
        await this.detectMode();
        
        if (this.isStatic) {
            return [];
        }
        
        return this.get('/api/keywords/emerging');
    }
};

// 导出供其他模块使用
window.API = API;
