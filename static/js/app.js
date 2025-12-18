/**
 * Main application JavaScript for K-Pop Concert Tracker
 */

class ConcertTracker {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 50;
        this.filters = {
            artistIds: [],
            includePast: false,
            includeTbd: true,
            seoulOnly: false,
            encoreOnly: false,
            sortBy: 'date',
            sortOrder: 'asc',
        };
        this.artists = [];
        this.concerts = [];
        this.totalConcerts = 0;

        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadInitialData();
        this.updateTwitterStatus();

        // Auto-refresh every 5 minutes
        setInterval(() => this.updateTwitterStatus(), 300000);
    }

    bindEvents() {
        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => this.refreshData());

        // Filter controls
        document.getElementById('apply-filters')?.addEventListener('click', () => this.applyFilters());
        document.getElementById('clear-filters')?.addEventListener('click', () => this.clearFilters());

        // Sort controls
        document.getElementById('sort-by')?.addEventListener('change', (e) => {
            this.filters.sortBy = e.target.value;
            this.loadConcerts();
        });
        document.getElementById('sort-order')?.addEventListener('change', (e) => {
            this.filters.sortOrder = e.target.value;
            this.loadConcerts();
        });

        // Show filters
        document.getElementById('show-past')?.addEventListener('change', (e) => {
            this.filters.includePast = e.target.checked;
        });
        document.getElementById('show-tbd')?.addEventListener('change', (e) => {
            this.filters.includeTbd = e.target.checked;
        });
        document.getElementById('seoul-only')?.addEventListener('change', (e) => {
            this.filters.seoulOnly = e.target.checked;
        });
        document.getElementById('encore-only')?.addEventListener('change', (e) => {
            this.filters.encoreOnly = e.target.checked;
        });

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => this.prevPage());
        document.getElementById('next-page')?.addEventListener('click', () => this.nextPage());

        // Add Artist Modal
        document.getElementById('add-artist-btn')?.addEventListener('click', () => this.showAddArtistModal());
        document.getElementById('add-artist-form')?.addEventListener('submit', (e) => this.handleAddArtist(e));

        // Modal close buttons
        document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
            btn.addEventListener('click', () => this.closeModals());
        });

        // Close modal on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeModals();
            });
        });
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadArtists(),
                this.loadSummary(),
                this.loadConcerts(),
                this.loadHighlights(),
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load data. Please refresh the page.');
        }
    }

    async loadArtists() {
        try {
            const response = await api.getArtists(true);
            this.artists = response.artists || [];
            this.renderArtistFilters();
        } catch (error) {
            console.error('Error loading artists:', error);
        }
    }

    renderArtistFilters() {
        const container = document.getElementById('artist-filters');
        if (!container) return;

        if (this.artists.length === 0) {
            container.innerHTML = '<div class="empty-state">No artists added yet. Click + to add.</div>';
            return;
        }

        container.innerHTML = this.artists.map(artist => `
            <label class="checkbox-item">
                <input type="checkbox" data-artist-id="${artist.id}" checked>
                <span>${artist.name}${artist.korean_name ? ` (${artist.korean_name})` : ''}</span>
            </label>
        `).join('');

        // Bind change events
        container.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                this.updateArtistFilter();
            });
        });
    }

    updateArtistFilter() {
        const checkboxes = document.querySelectorAll('#artist-filters input:checked');
        this.filters.artistIds = Array.from(checkboxes).map(cb => parseInt(cb.dataset.artistId));
    }

    async loadSummary() {
        try {
            const summary = await api.getDashboardSummary();

            document.getElementById('total-upcoming').textContent = summary.total_upcoming_concerts || 0;
            document.getElementById('seoul-upcoming').textContent = summary.seoul_shows_upcoming || 0;
            document.getElementById('encore-upcoming').textContent = summary.encore_shows_upcoming || 0;
            document.getElementById('artists-tracked').textContent = summary.total_artists_tracked || 0;

            if (summary.last_twitter_update) {
                const date = new Date(summary.last_twitter_update);
                document.getElementById('last-updated').textContent = `Last updated: ${date.toLocaleString()}`;
            }
        } catch (error) {
            console.error('Error loading summary:', error);
        }
    }

    async loadConcerts() {
        const container = document.getElementById('concert-list');
        if (!container) return;

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading concerts...</p></div>';

        try {
            const response = await api.getConcerts({
                ...this.filters,
                page: this.currentPage,
                pageSize: this.pageSize,
            });

            this.concerts = response.concerts || [];
            this.totalConcerts = response.total_count || 0;

            this.renderConcerts();
            this.updatePagination(response);
            this.updateLastUpdated(response.last_updated);
        } catch (error) {
            console.error('Error loading concerts:', error);
            container.innerHTML = '<div class="empty-state">Failed to load concerts.</div>';
        }
    }

    renderConcerts() {
        const container = document.getElementById('concert-list');
        if (!container) return;

        if (this.concerts.length === 0) {
            container.innerHTML = '<div class="empty-state">No concerts found. Add some artists to start tracking!</div>';
            return;
        }

        container.innerHTML = this.concerts.map(concert => this.renderConcertCard(concert)).join('');
    }

    renderConcertCard(concert) {
        const classes = ['concert-card'];
        const badges = [];

        // Apply special styling
        if (concert.is_past) {
            classes.push('past');
            badges.push('<span class="badge badge-past">Past</span>');
        } else if (concert.is_today) {
            classes.push('today');
            badges.push('<span class="badge badge-today">Today!</span>');
        }

        if (concert.is_seoul_kickoff) {
            classes.push('seoul-kickoff');
            badges.push('<span class="badge badge-seoul">Seoul Kickoff</span>');
        }

        if (concert.is_encore) {
            classes.push('encore');
            badges.push('<span class="badge badge-encore">Encore</span>');
        }

        if (concert.is_finale) {
            classes.push('finale');
            badges.push('<span class="badge badge-finale">Finale</span>');
        }

        if (!concert.date) {
            badges.push('<span class="badge badge-tbd">Date TBD</span>');
        }

        // Days until
        let daysUntilHtml = '';
        if (concert.days_until !== null && concert.days_until >= 0) {
            const isSoon = concert.days_until <= 7;
            daysUntilHtml = `<div class="days-until ${isSoon ? 'soon' : ''}">${concert.days_until === 0 ? 'Today!' : `${concert.days_until} days away`}</div>`;
        }

        // TBD notice
        let tbdNotice = '';
        if (concert.has_tbd_in_tour && !concert.is_past) {
            tbdNotice = '<div class="tbd-notice">More dates to be announced for this tour</div>';
        }

        return `
            <div class="${classes.join(' ')}">
                <div class="concert-header">
                    <div>
                        <span class="concert-artist">${this.escapeHtml(concert.artist_name)}</span>
                        ${concert.artist_korean_name ? `<span class="concert-korean-name">${this.escapeHtml(concert.artist_korean_name)}</span>` : ''}
                    </div>
                    <div class="badges">${badges.join('')}</div>
                </div>
                <div class="concert-tour">${this.escapeHtml(concert.tour_name)}</div>
                <div class="concert-details">
                    <div class="concert-location">
                        <strong>${this.escapeHtml(concert.city)}</strong>, ${this.escapeHtml(concert.country)}
                    </div>
                    <div class="concert-date ${!concert.date ? 'tbd' : ''}">
                        ${concert.date_display}
                        ${concert.end_date ? ` - ${new Date(concert.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : ''}
                    </div>
                    ${concert.venue ? `<div class="concert-venue">${this.escapeHtml(concert.venue)}</div>` : ''}
                </div>
                ${daysUntilHtml}
                ${tbdNotice}
                ${concert.ticket_url ? `<a href="${concert.ticket_url}" target="_blank" class="btn btn-secondary" style="margin-top: 0.5rem; font-size: 0.75rem;">Buy Tickets</a>` : ''}
            </div>
        `;
    }

    async loadHighlights() {
        try {
            const highlights = await api.getHighlights();

            this.renderHighlightList('seoul-kickoffs', highlights.seoul_kickoffs || []);
            this.renderHighlightList('encore-shows', highlights.encore_shows || []);
        } catch (error) {
            console.error('Error loading highlights:', error);
        }
    }

    renderHighlightList(containerId, items) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">None scheduled</div>';
            return;
        }

        container.innerHTML = items.slice(0, 5).map(item => `
            <div class="highlight-item">
                <strong>${this.escapeHtml(item.artist_name)}</strong><br>
                <small>${this.escapeHtml(item.city)} - ${item.date_display}</small>
            </div>
        `).join('');
    }

    updatePagination(response) {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
        if (nextBtn) nextBtn.disabled = !response.has_more_pages;

        const totalPages = Math.ceil(this.totalConcerts / this.pageSize);
        if (pageInfo) pageInfo.textContent = `Page ${this.currentPage} of ${totalPages || 1}`;
    }

    updateLastUpdated(timestamp) {
        if (timestamp) {
            const date = new Date(timestamp);
            document.getElementById('last-updated').textContent = `Last updated: ${date.toLocaleString()}`;
        }
    }

    async updateTwitterStatus() {
        try {
            const status = await api.getTwitterStatus();
            const statusEl = document.getElementById('twitter-status');
            if (statusEl) {
                if (status.connected) {
                    statusEl.textContent = `Twitter: Connected (${status.rate_limit_remaining}/${status.rate_limit_max} requests)`;
                    statusEl.style.color = '#22c55e';
                } else {
                    statusEl.textContent = 'Twitter: Not configured';
                    statusEl.style.color = '#f59e0b';
                }
            }
        } catch (error) {
            console.error('Error checking Twitter status:', error);
        }
    }

    applyFilters() {
        this.currentPage = 1;
        this.updateArtistFilter();

        // Get date range
        const dateFrom = document.getElementById('date-from')?.value;
        const dateTo = document.getElementById('date-to')?.value;
        if (dateFrom) this.filters.dateFrom = dateFrom;
        else delete this.filters.dateFrom;
        if (dateTo) this.filters.dateTo = dateTo;
        else delete this.filters.dateTo;

        this.loadConcerts();
    }

    clearFilters() {
        // Reset checkboxes
        document.querySelectorAll('#artist-filters input').forEach(cb => cb.checked = true);
        document.getElementById('show-past').checked = false;
        document.getElementById('show-tbd').checked = true;
        document.getElementById('seoul-only').checked = false;
        document.getElementById('encore-only').checked = false;
        document.getElementById('date-from').value = '';
        document.getElementById('date-to').value = '';

        // Reset filters
        this.filters = {
            artistIds: [],
            includePast: false,
            includeTbd: true,
            seoulOnly: false,
            encoreOnly: false,
            sortBy: 'date',
            sortOrder: 'asc',
        };

        this.currentPage = 1;
        this.loadConcerts();
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadConcerts();
        }
    }

    nextPage() {
        this.currentPage++;
        this.loadConcerts();
    }

    async refreshData() {
        const btn = document.getElementById('refresh-btn');
        if (btn) {
            btn.classList.add('loading');
            btn.disabled = true;
        }

        try {
            // Try to refresh from Twitter if configured
            try {
                await api.refreshTwitter();
            } catch (e) {
                // Twitter not configured, that's okay
                console.log('Twitter refresh skipped:', e.message);
            }

            // Reload all data
            await this.loadInitialData();
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showError('Failed to refresh data');
        } finally {
            if (btn) {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }
    }

    showAddArtistModal() {
        document.getElementById('add-artist-modal')?.classList.remove('hidden');
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
    }

    async handleAddArtist(e) {
        e.preventDefault();

        const name = document.getElementById('artist-name')?.value;
        const koreanName = document.getElementById('korean-name')?.value;
        const twitterHandle = document.getElementById('twitter-handle')?.value;

        if (!name) {
            this.showError('Artist name is required');
            return;
        }

        try {
            await api.createArtist({
                name,
                korean_name: koreanName || null,
                twitter_handle: twitterHandle || null,
            });

            this.closeModals();
            document.getElementById('add-artist-form')?.reset();
            await this.loadInitialData();
        } catch (error) {
            console.error('Error adding artist:', error);
            this.showError(error.message || 'Failed to add artist');
        }
    }

    showError(message) {
        // Simple alert for now, could be improved with toast notifications
        alert(message);
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ConcertTracker();
});
