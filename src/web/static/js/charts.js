/**
 * ECharts 图表模块
 */

// 主题配置
const CHART_THEME = {
    backgroundColor: 'transparent',
    textStyle: {
        color: '#e6edf3'
    },
    title: {
        textStyle: {
            color: '#e6edf3'
        }
    },
    legend: {
        textStyle: {
            color: '#8b949e'
        }
    },
    tooltip: {
        backgroundColor: 'rgba(22, 27, 34, 0.95)',
        borderColor: '#30363d',
        textStyle: {
            color: '#e6edf3'
        }
    },
    // 调色板
    color: [
        '#58a6ff', '#3fb950', '#d29922', '#f85149',
        '#a371f7', '#79c0ff', '#56d364', '#e3b341',
        '#ff7b72', '#bc8cff'
    ]
};

// 注册主题
echarts.registerTheme('dark', CHART_THEME);

/**
 * 图表管理器
 */
const Charts = {
    instances: {},

    // 初始化图表实例
    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container not found: ${containerId}`);
            return null;
        }

        if (this.instances[containerId]) {
            this.instances[containerId].dispose();
        }

        const chart = echarts.init(container, 'dark');
        this.instances[containerId] = chart;

        // 响应式调整
        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    },

    // 获取实例
    get(containerId) {
        return this.instances[containerId];
    },

    // 显示加载状态
    showLoading(containerId) {
        const chart = this.get(containerId);
        if (chart) {
            chart.showLoading({
                text: '加载中...',
                color: '#58a6ff',
                textColor: '#8b949e',
                maskColor: 'rgba(13, 17, 23, 0.8)'
            });
        }
    },

    // 隐藏加载状态
    hideLoading(containerId) {
        const chart = this.get(containerId);
        if (chart) {
            chart.hideLoading();
        }
    },

    /**
     * 词云图
     */
    renderWordcloud(containerId, data) {
        const chart = this.init(containerId);
        if (!chart || !data || data.length === 0) return;

        // 计算最大值用于缩放
        const maxValue = Math.max(...data.map(d => d.value));

        const option = {
            tooltip: {
                show: true,
                formatter: params => {
                    return `<strong>${params.name}</strong><br/>出现次数: ${params.value}`;
                }
            },
            series: [{
                type: 'wordCloud',
                shape: 'circle',
                left: 'center',
                top: 'center',
                width: '90%',
                height: '90%',
                sizeRange: [14, 60],
                rotationRange: [-45, 45],
                rotationStep: 15,
                gridSize: 8,
                drawOutOfBound: false,
                textStyle: {
                    fontFamily: 'sans-serif',
                    fontWeight: 'bold',
                    color: function () {
                        const colors = [
                            '#58a6ff', '#79c0ff', '#3fb950', '#56d364',
                            '#d29922', '#e3b341', '#a371f7', '#bc8cff'
                        ];
                        return colors[Math.floor(Math.random() * colors.length)];
                    }
                },
                emphasis: {
                    textStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(88, 166, 255, 0.5)'
                    }
                },
                data: data.map(item => ({
                    name: item.name,
                    value: item.value
                }))
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 水平柱状图（Top 关键词）
     */
    renderBarChart(containerId, data, options = {}) {
        const chart = this.init(containerId);
        if (!chart || !data || data.length === 0) return;

        // 反转数据使最高的在上面
        const reversed = [...data].reverse();

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                }
            },
            grid: {
                left: '3%',
                right: '10%',
                bottom: '3%',
                top: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#30363d' } },
                axisLabel: { color: '#8b949e' },
                splitLine: { lineStyle: { color: '#21262d' } }
            },
            yAxis: {
                type: 'category',
                data: reversed.map(d => d.keyword),
                axisLine: { lineStyle: { color: '#30363d' } },
                axisLabel: {
                    color: '#e6edf3',
                    fontSize: 12
                }
            },
            series: [{
                type: 'bar',
                data: reversed.map(d => d.count),
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: '#667eea' },
                        { offset: 1, color: '#764ba2' }
                    ]),
                    borderRadius: [0, 4, 4, 0]
                },
                emphasis: {
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            { offset: 0, color: '#764ba2' },
                            { offset: 1, color: '#667eea' }
                        ])
                    }
                },
                label: {
                    show: true,
                    position: 'right',
                    color: '#8b949e',
                    fontSize: 11
                }
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 趋势折线图
     */
    renderTrendChart(containerId, trends) {
        const chart = this.init(containerId);
        if (!chart || !trends || trends.length === 0) return;

        // 收集所有年份
        const allYears = new Set();
        trends.forEach(t => t.years.forEach(y => allYears.add(y)));
        const years = Array.from(allYears).sort();

        const option = {
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: trends.map(t => t.keyword),
                top: 0,
                textStyle: { color: '#8b949e' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '50px',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: years,
                axisLine: { lineStyle: { color: '#30363d' } },
                axisLabel: { color: '#8b949e' }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#30363d' } },
                axisLabel: { color: '#8b949e' },
                splitLine: { lineStyle: { color: '#21262d' } }
            },
            series: trends.map((trend, idx) => ({
                name: trend.keyword,
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                data: years.map(year => {
                    const index = trend.years.indexOf(year);
                    return index >= 0 ? trend.counts[index] : null;
                }),
                lineStyle: {
                    width: 3
                },
                emphasis: {
                    focus: 'series'
                }
            }))
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 会议对比雷达图
     */
    renderComparisonRadar(containerId, comparison) {
        const chart = this.init(containerId);
        if (!chart || !comparison) return;

        const venues = Object.keys(comparison.venues);

        // 收集所有关键词
        const allKeywords = new Set();
        venues.forEach(venue => {
            comparison.venues[venue].slice(0, 8).forEach(k => {
                allKeywords.add(k.keyword);
            });
        });
        const keywords = Array.from(allKeywords).slice(0, 8);

        const option = {
            tooltip: {},
            legend: {
                data: venues,
                top: 0,
                textStyle: { color: '#8b949e' }
            },
            radar: {
                indicator: keywords.map(k => ({
                    name: k,
                    max: 500
                })),
                center: ['50%', '55%'],
                radius: '65%',
                axisName: {
                    color: '#8b949e'
                },
                splitArea: {
                    areaStyle: {
                        color: ['rgba(88, 166, 255, 0.05)', 'transparent']
                    }
                },
                splitLine: {
                    lineStyle: { color: '#30363d' }
                },
                axisLine: {
                    lineStyle: { color: '#30363d' }
                }
            },
            series: [{
                type: 'radar',
                data: venues.map(venue => ({
                    name: venue,
                    value: keywords.map(kw => {
                        const found = comparison.venues[venue].find(k => k.keyword === kw);
                        return found ? found.count : 0;
                    }),
                    areaStyle: { opacity: 0.2 }
                }))
            }]
        };

        chart.setOption(option);
        return chart;
    }
};

// 导出
window.Charts = Charts;
