const nav = document.querySelector('.navbar');
const hamburger = document.querySelector('.hamburger');
const navMenu = document.querySelector('.nav-menu');
const navLinks = document.querySelectorAll('.nav-link');

const categoryIcons = {
    Week: 'fa-calendar-week',
    Assessment: 'fa-clipboard-check',
    Reference: 'fa-book',
    Reading: 'fa-glasses',
};

document.addEventListener('DOMContentLoaded', async function() {
    initializeNavigation();
    initializeScrollEffects();
    await loadSiteContext();
});

function initializeNavigation() {
    hamburger?.addEventListener('click', toggleMobileMenu);
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href') || '';
            if (!href.startsWith('#')) {
                return;
            }
            e.preventDefault();
            const targetId = href.substring(1);
            scrollToSection(targetId);
            if (navMenu.classList.contains('active')) {
                toggleMobileMenu();
            }
        });
    });
    window.addEventListener('scroll', handleNavbarScroll);
}

function toggleMobileMenu() {
    hamburger.classList.toggle('active');
    navMenu.classList.toggle('active');
}

function handleNavbarScroll() {
    if (window.scrollY > 50) {
        nav.style.background = 'rgba(255, 255, 255, 0.95)';
        nav.style.backdropFilter = 'blur(10px)';
        nav.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    } else {
        nav.style.background = 'var(--bg-primary)';
        nav.style.boxShadow = 'none';
    }
}

function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    const offsetTop = section.offsetTop - 70;
    window.scrollTo({ top: offsetTop, behavior: 'smooth' });
}

function initializeScrollEffects() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px',
    };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    document.querySelectorAll('.content-card, .example-card, .resource-card').forEach(el => observer.observe(el));
}

async function loadSiteContext() {
    const workspaceId = getWorkspaceId();
    try {
        const response = await fetch(`api/site_context${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''}`);
        const context = await response.json();
        applyWorkspaceLinks(context.workspace_id || workspaceId || '');
        renderHome(context);
    } catch (error) {
        console.error('Failed to load site context', error);
        renderError();
    }
}

function getWorkspaceId() {
    return new URLSearchParams(window.location.search).get('workspace_id') || '';
}

function applyWorkspaceLinks(workspaceId) {
    const suffix = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
    document.getElementById('wikiNavLink').href = `wiki.html${suffix}`;
    document.getElementById('openWikiButton').href = `wiki.html${suffix}`;
    document.getElementById('footerWikiLink').href = `wiki.html${suffix}`;
}

function renderHome(context) {
    const workspaceTitle = context.workspace_title || 'Local Knowledge Wiki';
    document.title = `${workspaceTitle} — Local Knowledge Wiki`;
    document.getElementById('siteTitle').textContent = workspaceTitle;
    document.getElementById('heroTitle').textContent = workspaceTitle;
    document.getElementById('heroSubtitle').textContent =
        context.source_root
            ? 'Your local folder is being turned into a structured, browsable knowledge base.'
            : 'Connect a folder, generate Markdown pages, and browse them through a polished local reader.';
    document.getElementById('heroMeta').textContent =
        context.source_root
            ? `Source folder: ${context.source_root}`
            : 'No source folder connected yet.';

    document.getElementById('statPages').textContent = String(context.page_count || 0);
    document.getElementById('statCategories').textContent = String(context.category_count || 0);
    document.getElementById('statSources').textContent = String(context.source_file_count || 0);
    document.getElementById('statTopTag').textContent = topTagLabel(context.tags || {});

    document.getElementById('sourceRootDisplay').textContent = context.source_root || 'No source folder connected.';
    document.getElementById('footerStatus').textContent = context.last_scan_at
        ? `Last scan: ${context.last_scan_at} · Build status: ${context.last_build_status}`
        : 'No build has run yet.';

    renderCategories(context.categories || {}, context.workspace_id || '');
    renderFeatured(context.featured || [], context.workspace_id || '');
    renderRecent(context.recent || [], context.workspace_id || '');
}

function renderCategories(categories, workspaceId) {
    const container = document.getElementById('categoryCards');
    const entries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) {
        container.innerHTML = emptyCard('No categories yet', 'Scan a source folder to populate your wiki.');
        return;
    }
    container.innerHTML = entries.map(([name, count]) => `
        <a class="content-card knowledge-link-card" href="wiki.html?workspace_id=${encodeURIComponent(workspaceId)}#category/${encodeURIComponent(name)}">
            <div class="card-icon"><i class="fas ${categoryIcons[name] || 'fa-folder-open'}"></i></div>
            <h3>${escapeHtml(name)}</h3>
            <p>${count} generated page${count === 1 ? '' : 's'}</p>
        </a>
    `).join('');
}

function renderFeatured(featured, workspaceId) {
    const container = document.getElementById('featuredGrid');
    if (!featured.length) {
        container.innerHTML = emptyExample('No featured pages yet', 'Generate a wiki first to highlight key pages.');
        return;
    }
    container.innerHTML = featured.map(page => `
        <a class="example-card knowledge-link-card" href="wiki.html?workspace_id=${encodeURIComponent(workspaceId)}#article/${encodeURIComponent(slugForPage(page))}">
            <h3>${escapeHtml(page.title || 'Untitled')}</h3>
            <p>${escapeHtml(page.summary || '')}</p>
            <div class="knowledge-meta">
                <span>${escapeHtml(page.kind || 'page')}</span>
                <span>${escapeHtml(page.category || 'Reference')}</span>
                <span>${escapeHtml(page.difficulty || 'Intermediate')}</span>
            </div>
        </a>
    `).join('');
}

function renderRecent(recent, workspaceId) {
    const container = document.getElementById('recentGrid');
    if (!recent.length) {
        container.innerHTML = `
            <div class="resource-card">
                <div class="resource-icon"><i class="fas fa-clock"></i></div>
                <h3>No recent updates</h3>
                <ul><li>Scan or rebuild the wiki to see recent changes.</li></ul>
            </div>
        `;
        return;
    }
    container.innerHTML = recent.map(page => `
        <a class="resource-card knowledge-link-card" href="wiki.html?workspace_id=${encodeURIComponent(workspaceId)}#article/${encodeURIComponent(slugForPage(page))}">
            <div class="resource-icon"><i class="fas fa-file-lines"></i></div>
            <h3>${escapeHtml(page.title || 'Untitled')}</h3>
            <ul>
                <li>${escapeHtml(page.category || 'Reference')} · ${escapeHtml(page.kind || 'page')}</li>
                <li>${escapeHtml(page.updated_at || 'Unknown update time')}</li>
                <li>${escapeHtml(page.summary || '')}</li>
            </ul>
        </a>
    `).join('');
}

function topTagLabel(tags) {
    const entries = Object.entries(tags).sort((a, b) => b[1] - a[1]);
    return entries.length ? entries[0][0] : '—';
}

function slugForPage(page) {
    const base = `${page.kind || 'page'}-${page.title || page.path || 'untitled'}`;
    return base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function emptyCard(title, description) {
    return `
        <div class="content-card">
            <div class="card-icon"><i class="fas fa-circle-info"></i></div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(description)}</p>
        </div>
    `;
}

function emptyExample(title, description) {
    return `
        <div class="example-card">
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(description)}</p>
        </div>
    `;
}

function renderError() {
    document.getElementById('heroTitle').textContent = 'Unable to load workspace';
    document.getElementById('heroSubtitle').textContent = 'The front-end shell is available, but the local wiki context could not be loaded.';
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const style = document.createElement('style');
style.textContent = `
    .animate-in {
        animation: fadeInUp 0.6s ease-out;
    }

    .hero-meta {
        margin-top: 1rem;
        color: var(--text-secondary);
        font-size: 0.95rem;
    }

    .knowledge-link-card {
        text-decoration: none;
        color: inherit;
        display: block;
    }

    .knowledge-meta {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
