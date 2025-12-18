/**
 * API client for K-Pop Concert Tracker
 */

const API_BASE = '/api/v1';

class ConcertAPI {
    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options,
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        const response = await fetch(url, config);

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `API Error: ${response.status}`);
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    // Artists API
    async getArtists(favoritesOnly = false) {
        const params = favoritesOnly ? '?favorites_only=true' : '';
        return this.request(`/artists${params}`);
    }

    async getArtist(id) {
        return this.request(`/artists/${id}`);
    }

    async createArtist(data) {
        return this.request('/artists', {
            method: 'POST',
            body: data,
        });
    }

    async updateArtist(id, data) {
        return this.request(`/artists/${id}`, {
            method: 'PUT',
            body: data,
        });
    }

    async deleteArtist(id) {
        return this.request(`/artists/${id}`, {
            method: 'DELETE',
        });
    }

    // Tours API
    async getTours(artistId = null) {
        const params = artistId ? `?artist_id=${artistId}` : '';
        return this.request(`/tours${params}`);
    }

    async getTour(id) {
        return this.request(`/tours/${id}`);
    }

    async createTour(data) {
        return this.request('/tours', {
            method: 'POST',
            body: data,
        });
    }

    async updateTour(id, data) {
        return this.request(`/tours/${id}`, {
            method: 'PUT',
            body: data,
        });
    }

    async addTourDate(tourId, data) {
        return this.request(`/tours/${tourId}/dates`, {
            method: 'POST',
            body: data,
        });
    }

    // Concerts API
    async getConcerts(filters = {}) {
        const params = new URLSearchParams();

        if (filters.artistIds?.length) {
            params.set('artist_ids', filters.artistIds.join(','));
        }
        if (filters.cities?.length) {
            params.set('cities', filters.cities.join(','));
        }
        if (filters.countries?.length) {
            params.set('countries', filters.countries.join(','));
        }
        if (filters.dateFrom) {
            params.set('date_from', filters.dateFrom);
        }
        if (filters.dateTo) {
            params.set('date_to', filters.dateTo);
        }
        if (filters.includePast !== undefined) {
            params.set('include_past', filters.includePast);
        }
        if (filters.includeTbd !== undefined) {
            params.set('include_tbd', filters.includeTbd);
        }
        if (filters.seoulOnly) {
            params.set('seoul_only', 'true');
        }
        if (filters.encoreOnly) {
            params.set('encore_only', 'true');
        }
        if (filters.sortBy) {
            params.set('sort_by', filters.sortBy);
        }
        if (filters.sortOrder) {
            params.set('sort_order', filters.sortOrder);
        }
        if (filters.page) {
            params.set('page', filters.page);
        }
        if (filters.pageSize) {
            params.set('page_size', filters.pageSize);
        }

        const queryString = params.toString();
        return this.request(`/concerts${queryString ? '?' + queryString : ''}`);
    }

    async getUpcomingConcerts(limit = 20) {
        return this.request(`/concerts/upcoming?limit=${limit}`);
    }

    async getHighlights() {
        return this.request('/concerts/highlights');
    }

    // Dashboard API
    async getDashboardSummary() {
        return this.request('/dashboard/summary');
    }

    // Twitter API
    async getTwitterStatus() {
        return this.request('/twitter/status');
    }

    async refreshTwitter(artistIds = null, force = false) {
        return this.request('/twitter/refresh', {
            method: 'POST',
            body: { artist_ids: artistIds, force },
        });
    }

    async getAnnouncements(options = {}) {
        const params = new URLSearchParams();
        if (options.artistId) params.set('artist_id', options.artistId);
        if (options.processed !== undefined) params.set('processed', options.processed);
        if (options.officialOnly) params.set('official_only', 'true');
        if (options.limit) params.set('limit', options.limit);
        if (options.offset) params.set('offset', options.offset);

        const queryString = params.toString();
        return this.request(`/twitter/announcements${queryString ? '?' + queryString : ''}`);
    }

    async testParseTweet(tweetText) {
        return this.request('/twitter/parse-test', {
            method: 'POST',
            body: { tweet_text: tweetText },
        });
    }
}

// Export singleton instance
window.api = new ConcertAPI();
