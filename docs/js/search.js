/**
 * Keyword Search with Autocomplete
 */

class KeywordSearch {
    constructor(inputId, resultsId, onSelect) {
        this.input = document.getElementById(inputId);
        this.resultsContainer = this.createResultsContainer(resultsId);
        this.onSelect = onSelect;
        this.keywords = [];
        this.currentVenue = null;
        this.selectedIndex = -1;
        
        this.setupEventListeners();
    }
    
    createResultsContainer(id) {
        let container = document.getElementById(id);
        if (!container) {
            container = document.createElement('div');
            container.id = id;
            container.className = 'autocomplete-results';
            this.input.parentNode.style.position = 'relative';
            this.input.parentNode.appendChild(container);
        }
        return container;
    }
    
    setupEventListeners() {
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.handleInput({ target: this.input }));
        
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.resultsContainer.contains(e.target)) {
                this.hideResults();
            }
        });
    }
    
    async loadKeywords(venue) {
        if (this.currentVenue === venue && this.keywords.length > 0) {
            return;
        }
        
        this.currentVenue = venue;
        
        try {
            await API.detectMode();
            
            if (API.isStatic && venue) {
                const data = await API.getStatic(`./data/venues/venue_${venue}_keywords_index.json`);
                this.keywords = data;
            } else if (venue) {
                const topKeywords = await API.getTopKeywords({ venue, limit: 500 });
                this.keywords = topKeywords.map(item => item.keyword);
            } else {
                this.keywords = [];
            }
        } catch (error) {
            console.error('Failed to load keywords:', error);
            this.keywords = [];
        }
    }
    
    handleInput(e) {
        const query = e.target.value.trim().toLowerCase();
        
        if (query.length < 2) {
            this.hideResults();
            return;
        }
        
        const matches = this.keywords
            .filter(kw => kw.toLowerCase().includes(query))
            .slice(0, 10);
        
        this.showResults(matches, query);
    }
    
    handleKeydown(e) {
        const items = this.resultsContainer.querySelectorAll('.autocomplete-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
            this.updateSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
            this.updateSelection(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                items[this.selectedIndex].click();
            } else if (this.input.value.trim()) {
                this.selectKeyword(this.input.value.trim());
            }
        } else if (e.key === 'Escape') {
            this.hideResults();
        }
    }
    
    updateSelection(items) {
        items.forEach((item, index) => {
         if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    showResults(matches, query) {
        if (matches.length === 0) {
            this.hideResults();
            return;
        }
        
        this.resultsContainer.innerHTML = matches
            .map((kw, index) => {
                const highlighted = this.highlightMatch(kw, query);
                return `<div class="autocomplete-item" data-index="${index}" data-keyword="${kw}">${highlighted}</div>`;
            })
            .join('');
        
        this.resultsContainer.style.display = 'block';
        this.selectedIndex = -1;
        
        this.resultsContainer.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectKeyword(item.dataset.keyword);
            });
        });
    }
    
    highlightMatch(text, query) {
        const index = text.toLowerCase().indexOf(query);
        if (index === -1) return text;
        
        const before = text.substring(0, index);
        const match = text.substring(index, index + query.length);
        const after = text.substring(index + query.length);
        
        return `${before}<strong>${match}</strong>${after}`;
    }
    
    hideResults() {
        this.resultsContainer.style.display = 'none';
        this.resultsContainer.innerHTML = '';
        this.selectedIndex = -1;
    }
    
    selectKeyword(keyword) {
        this.input.value = keyword;
        this.hideResults();
        
        if (this.onSelect) {
            this.onSelect(keyword);
        }
    }
    
    clear() {
        this.input.value = '';
        this.hideResults();
    }
}

window.KeywordSearch = KeywordSearch;
