/* ============================================
   AGENTIC AI WIKI — JavaScript
   Knowledge Base Engine
   ============================================ */

(function() {
    'use strict';

    // ====== STATE ======
    const state = {
        articles: [],
        categories: {},
        allTags: {},
        currentView: 'home',
        currentArticle: null,
        sidebarOpen: true,
        darkMode: false,
        currentFilter: null,
        workspaceId: '',
        siteContext: null,
    };

    // ====== CATEGORY CONFIG ======
    const categoryConfig = {
        'Week':         { icon: 'fa-calendar-week',     color: '#6366f1', desc: 'Weekly course materials and seminar content' },
        'Assessment':   { icon: 'fa-clipboard-check',   color: '#f59e0b', desc: 'Assessment briefs, guides, and marking context' },
        'Reference':    { icon: 'fa-book',              color: '#10b981', desc: 'Reference materials and course-level documents' },
        'Reading':      { icon: 'fa-glasses',           color: '#06b6d4', desc: 'Assigned readings and supporting references' },
        'General':      { icon: 'fa-folder-open',       color: '#8b5cf6', desc: 'Additional knowledge pages' },
    };

    // ====== INIT ======
    async function init() {
        state.workspaceId = getWorkspaceId();
        initTheme();
        await Promise.all([loadSiteContext(), loadArticles()]);
        buildSidebar();
        renderHomeView();
        bindEvents();
        handleHashNavigation();
    }

    function getWorkspaceId() {
        return new URLSearchParams(window.location.search).get('workspace_id') || '';
    }

    function withWorkspace(path) {
        if (!state.workspaceId) return path;
        const separator = path.includes('?') ? '&' : '?';
        return `${path}${separator}workspace_id=${encodeURIComponent(state.workspaceId)}`;
    }

    function getCategoryConfig(category) {
        return categoryConfig[category] || { icon: 'fa-folder-open', color: '#6b7280', desc: 'Generated knowledge pages' };
    }

    async function loadSiteContext() {
        try {
            const response = await fetch(withWorkspace('api/site_context'));
            state.siteContext = await response.json();
            applyWorkspaceContext();
        } catch (e) {
            console.error('Failed to load site context:', e);
            state.siteContext = null;
        }
    }

    function applyWorkspaceContext() {
        if (!state.siteContext) return;
        const title = state.siteContext.workspace_title || 'Local Knowledge';
        document.title = `${title} — Local Knowledge Wiki`;
        document.getElementById('wikiBrandTitle').textContent = title;
        document.getElementById('wikiHeroTitle').textContent = title;
        document.getElementById('wikiHeroDescription').textContent = state.siteContext.source_root
            ? `Knowledge base generated from ${state.siteContext.source_root}`
            : 'A local-first knowledge base generated from your own folders, notes, and PDFs.';
        document.getElementById('wikiBrandLink').href = withWorkspace('wiki.html');
        document.getElementById('mainSiteLink').href = withWorkspace('index.html');
    }

    // ====== DATA LOADING ======
    async function loadArticles() {
        try {
            const response = await fetch(withWorkspace('tables/wiki_articles?limit=500'));
            const result = await response.json();
            state.articles = result.data || [];

            // Build category counts
            state.categories = {};
            state.allTags = {};
            state.articles.forEach(article => {
                const cat = article.category || 'Uncategorized';
                state.categories[cat] = (state.categories[cat] || 0) + 1;

                if (article.tags) {
                    const tags = Array.isArray(article.tags) ? article.tags : 
                        (typeof article.tags === 'string' ? JSON.parse(article.tags) : []);
                    tags.forEach(tag => {
                        state.allTags[tag] = (state.allTags[tag] || 0) + 1;
                    });
                }
            });

            // Update stats
            document.getElementById('articleCount').textContent = state.articles.length;
            document.getElementById('categoryCount').textContent = Object.keys(state.categories).length;
        } catch(e) {
            console.error('Failed to load articles:', e);
            state.articles = [];
        }
    }

    // ====== SIDEBAR ======
    function buildSidebar() {
        // Categories
        const categoryList = document.getElementById('categoryList');
        categoryList.innerHTML = '';
        Object.entries(state.categories).sort((a,b) => b[1] - a[1]).forEach(([cat, count]) => {
            const conf = getCategoryConfig(cat);
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'category-item';
            item.dataset.category = cat;
            item.innerHTML = `
                <span class="category-item-left">
                    <span class="category-dot" style="background:${conf.color}"></span>
                    ${cat}
                </span>
                <span class="category-count">${count}</span>
            `;
            item.addEventListener('click', (e) => {
                e.preventDefault();
                filterByCategory(cat);
            });
            categoryList.appendChild(item);
        });

        // Tags
        const tagCloud = document.getElementById('tagCloud');
        tagCloud.innerHTML = '';
        const sortedTags = Object.entries(state.allTags).sort((a,b) => b[1] - a[1]).slice(0, 20);
        sortedTags.forEach(([tag, count]) => {
            const pill = document.createElement('a');
            pill.href = '#';
            pill.className = 'tag-pill';
            pill.textContent = tag;
            pill.title = `${count} article(s)`;
            pill.addEventListener('click', (e) => {
                e.preventDefault();
                filterByTag(tag);
            });
            tagCloud.appendChild(pill);
        });
        renderGraphLegend();
    }

    // ====== VIEWS ======
    function showView(viewName) {
        document.querySelectorAll('.wiki-view').forEach(v => v.classList.add('hidden'));
        const viewEl = document.getElementById(viewName + 'View');
        if (viewEl) {
            viewEl.classList.remove('hidden');
        }

        // Update sidebar nav
        document.querySelectorAll('.sidebar-link[data-view]').forEach(l => l.classList.remove('active'));
        const activeLink = document.querySelector(`.sidebar-link[data-view="${viewName}"]`);
        if (activeLink) activeLink.classList.add('active');

        state.currentView = viewName;

        // Close mobile sidebar
        closeMobileSidebar();
    }

    // ====== HOME VIEW ======
    function renderHomeView() {
        // Stats
        document.getElementById('homeArticleCount').textContent = state.articles.length;
        document.getElementById('homeCategoryCount').textContent = Object.keys(state.categories).length;
        const totalWords = state.articles.reduce((sum, a) => sum + (a.word_count || 0), 0);
        document.getElementById('homeWordCount').textContent = totalWords.toLocaleString();
        const totalBacklinks = state.articles.reduce((sum, a) => {
            const bl = parseArray(a.backlinks);
            return sum + bl.length;
        }, 0);
        document.getElementById('homeBacklinkCount').textContent = totalBacklinks;

        // Category cards
        const grid = document.getElementById('homeCategoriesGrid');
        grid.innerHTML = '';
        Object.entries(state.categories).sort((a,b) => b[1] - a[1]).forEach(([cat, count]) => {
            const conf = getCategoryConfig(cat);
            const card = document.createElement('div');
            card.className = 'home-category-card';
            card.style.cssText = `--cat-color: ${conf.color}`;
            card.innerHTML = `
                <div style="position:absolute;top:0;left:0;right:0;height:3px;background:${conf.color}"></div>
                <h3><i class="fas ${conf.icon}" style="color:${conf.color};margin-right:8px"></i>${cat}</h3>
                <p>${conf.desc}</p>
                <div class="home-category-count">${count} article${count > 1 ? 's' : ''}</div>
            `;
            card.addEventListener('click', () => filterByCategory(cat));
            grid.appendChild(card);
        });

        // Recent articles
        const recent = [...state.articles].sort((a, b) => {
            return (b.last_edited || '').localeCompare(a.last_edited || '');
        }).slice(0, 5);
        const recentList = document.getElementById('homeRecentList');
        recentList.innerHTML = '';
        recent.forEach(article => {
            recentList.appendChild(createArticleListItem(article));
        });

        // Featured articles (pick Beginner + high word count)
        const featured = [...state.articles]
            .sort((a, b) => (b.word_count || 0) - (a.word_count || 0))
            .slice(0, 4);
        const featuredGrid = document.getElementById('homeFeaturedGrid');
        featuredGrid.innerHTML = '';
        featured.forEach(article => {
            const card = document.createElement('div');
            card.className = 'featured-card';
            const conf = getCategoryConfig(article.category);
            card.innerHTML = `
                <h3>${article.title}</h3>
                <p>${article.summary || ''}</p>
                <div class="featured-card-meta">
                    <span class="meta-category" style="background:${conf.color}15;color:${conf.color}">${article.category}</span>
                    <span><i class="fas fa-signal"></i> ${article.difficulty}</span>
                    <span><i class="fas fa-font"></i> ${(article.word_count || 0).toLocaleString()} words</span>
                </div>
            `;
            card.addEventListener('click', () => openArticle(article.slug));
            featuredGrid.appendChild(card);
        });

        showView('home');
    }

    // ====== ARTICLE LIST ======
    function renderArticleList(articles, title) {
        document.getElementById('listTitle').textContent = title || 'All Articles';
        const list = document.getElementById('articleList');
        list.innerHTML = '';

        if (articles.length === 0) {
            list.innerHTML = '<div class="no-results"><i class="fas fa-search"></i><p>No articles found.</p></div>';
        } else {
            articles.forEach(article => {
                list.appendChild(createArticleListItem(article));
            });
        }
        showView('list');
    }

    function createArticleListItem(article) {
        const item = document.createElement('div');
        item.className = 'article-list-item';
        const conf = getCategoryConfig(article.category);
        item.innerHTML = `
            <div class="article-list-icon" style="background:${conf.color}15;color:${conf.color}">
                <i class="fas ${conf.icon}"></i>
            </div>
            <div class="article-list-body">
                <div class="article-list-title">${article.title}</div>
                <div class="article-list-summary">${article.summary || ''}</div>
                <div class="article-list-meta">
                    <span class="meta-category" style="background:${conf.color}15;color:${conf.color}">${article.category}</span>
                    <span class="meta-difficulty"><i class="fas fa-signal"></i> ${article.difficulty}</span>
                    <span><i class="fas fa-font"></i> ${(article.word_count || 0).toLocaleString()} words</span>
                    <span><i class="fas fa-calendar"></i> ${article.last_edited || ''}</span>
                </div>
            </div>
        `;
        item.addEventListener('click', () => openArticle(article.slug));
        return item;
    }

    // ====== FILTERS ======
    function filterByCategory(cat) {
        state.currentFilter = { type: 'category', value: cat };
        // Highlight sidebar
        document.querySelectorAll('.category-item').forEach(i => i.classList.remove('active'));
        const activeItem = document.querySelector(`.category-item[data-category="${cat}"]`);
        if (activeItem) activeItem.classList.add('active');

        const filtered = state.articles.filter(a => a.category === cat);
        renderArticleList(filtered, `Category: ${cat}`);
        window.location.hash = `category/${cat}`;
    }

    function filterByTag(tag) {
        state.currentFilter = { type: 'tag', value: tag };
        const filtered = state.articles.filter(a => {
            const tags = parseArray(a.tags);
            return tags.includes(tag);
        });
        renderArticleList(filtered, `Tag: ${tag}`);
        window.location.hash = `tag/${tag}`;
    }

    function filterByDifficulty(diff) {
        state.currentFilter = { type: 'difficulty', value: diff };
        const filtered = state.articles.filter(a => a.difficulty === diff);
        renderArticleList(filtered, `Difficulty: ${diff}`);
        window.location.hash = `difficulty/${diff}`;
    }

    // ====== ARTICLE VIEW ======
    function openArticle(slug) {
        const article = state.articles.find(a => a.slug === slug);
        if (!article) {
            // Try to find by title partial
            const titleMatch = state.articles.find(a => 
                a.title.toLowerCase().includes(slug.replace(/-/g, ' '))
            );
            if (titleMatch) {
                openArticle(titleMatch.slug);
                return;
            }
            console.warn('Article not found:', slug);
            return;
        }

        state.currentArticle = article;
        window.location.hash = `article/${slug}`;

        const content = document.getElementById('articleContent');
        const conf = getCategoryConfig(article.category);

        // Process markdown content with wiki links
        let processedContent = processWikiLinks(article.content || '');
        processedContent = processInternalMarkdownLinks(processedContent, article.path || '');
        const htmlContent = marked.parse(processedContent);

        content.innerHTML = `
            <nav class="article-breadcrumb">
                <a href="#" data-nav="home"><i class="fas fa-house"></i></a>
                <span class="separator"><i class="fas fa-chevron-right"></i></span>
                <a href="#" data-nav="category" data-category="${article.category}">${article.category}</a>
                <span class="separator"><i class="fas fa-chevron-right"></i></span>
                <span>${article.title}</span>
            </nav>

            <header class="article-header">
                <h1 class="article-title">${article.title}</h1>
                <div class="article-meta-bar">
                    <span style="color:${conf.color}"><i class="fas ${conf.icon}"></i> ${article.category}</span>
                    <span class="difficulty-indicator ${(article.difficulty || '').toLowerCase()}">${article.difficulty}</span>
                    <span><i class="fas fa-font"></i> ${(article.word_count || 0).toLocaleString()} words</span>
                    <span><i class="fas fa-calendar"></i> ${article.last_edited || ''}</span>
                </div>
                <div class="article-tags">
                    ${parseArray(article.tags).map(t => `<a href="#" class="article-tag" data-tag="${t}">${t}</a>`).join('')}
                </div>
            </header>

            <div class="article-body">${htmlContent}</div>

            ${renderBacklinks(article)}
        `;

        // Bind breadcrumb navigation
        content.querySelectorAll('[data-nav="home"]').forEach(el => {
            el.addEventListener('click', (e) => { e.preventDefault(); renderHomeView(); });
        });
        content.querySelectorAll('[data-nav="category"]').forEach(el => {
            el.addEventListener('click', (e) => { e.preventDefault(); filterByCategory(el.dataset.category); });
        });
        content.querySelectorAll('.article-tag').forEach(el => {
            el.addEventListener('click', (e) => { e.preventDefault(); filterByTag(el.dataset.tag); });
        });

        // Bind wiki links in article body
        content.querySelectorAll('.wiki-link').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const targetSlug = el.dataset.slug;
                if (targetSlug) openArticle(targetSlug);
            });
        });

        content.querySelectorAll('.article-body a[data-slug]').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const targetSlug = el.dataset.slug;
                if (targetSlug) openArticle(targetSlug);
            });
        });

        // Bind backlink clicks
        content.querySelectorAll('.backlink-item').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                openArticle(el.dataset.slug);
            });
        });

        // Build ToC
        buildTableOfContents();

        showView('article');

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function processWikiLinks(markdown) {
        // Convert [[Title]] or [[slug|Title]] to clickable links
        return markdown.replace(/\[\[([^\]]+)\]\]/g, (match, inner) => {
            let title, slug;
            if (inner.includes('|')) {
                const parts = inner.split('|');
                slug = parts[0].trim();
                title = parts[1].trim();
            } else {
                title = inner;
                slug = inner;
            }
            // Convert title to slug
            const targetSlug = titleToSlug(slug);
            const exists = state.articles.some(a => a.slug === targetSlug);
            const cssClass = exists ? 'wiki-link' : 'wiki-link broken';
            return `<a href="#article/${targetSlug}" class="${cssClass}" data-slug="${targetSlug}">${title}</a>`;
        });
    }

    function processInternalMarkdownLinks(markdown, currentPath) {
        return markdown.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, href) => {
            if (/^(https?:|mailto:|#)/i.test(href)) return match;
            const normalized = normalizePath(currentPath, href);
            const target = state.articles.find(article => article.path === normalized);
            if (!target) return match;
            return `<a href="#article/${target.slug}" class="wiki-link" data-slug="${target.slug}">${label}</a>`;
        });
    }

    function normalizePath(currentPath, href) {
        const baseParts = (currentPath || '').split('/').slice(0, -1);
        const hrefParts = href.split('/');
        const stack = [...baseParts];
        hrefParts.forEach(part => {
            if (!part || part === '.') return;
            if (part === '..') {
                stack.pop();
                return;
            }
            stack.push(part);
        });
        return stack.join('/');
    }

    function titleToSlug(title) {
        return title.toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
    }

    function renderBacklinks(article) {
        // Find articles that link TO this article
        const incomingLinks = parseArray(article.backlinks)
            .map(slug => state.articles.find(a => a.slug === slug))
            .filter(Boolean);
        const outgoingLinks = parseArray(article.links_to)
            .map(slug => state.articles.find(a => a.slug === slug))
            .filter(Boolean);

        if (incomingLinks.length === 0 && outgoingLinks.length === 0) return '';

        let html = '<div class="article-backlinks">';
        
        if (outgoingLinks.length > 0) {
            html += `<h3><i class="fas fa-arrow-right-from-bracket"></i> Links To (${outgoingLinks.length})</h3>`;
            html += '<div class="backlink-list">';
            outgoingLinks.forEach(a => {
                const conf = getCategoryConfig(a.category);
                html += `<a href="#" class="backlink-item" data-slug="${a.slug}">
                    <i class="fas fa-link" style="color:${conf.color}"></i> ${a.title}
                </a>`;
            });
            html += '</div>';
        }

        if (incomingLinks.length > 0) {
            html += `<h3 style="margin-top:16px"><i class="fas fa-arrow-right-to-bracket"></i> Linked From (${incomingLinks.length})</h3>`;
            html += '<div class="backlink-list">';
            incomingLinks.forEach(a => {
                const conf = getCategoryConfig(a.category);
                html += `<a href="#" class="backlink-item" data-slug="${a.slug}">
                    <i class="fas fa-link" style="color:${conf.color}"></i> ${a.title}
                </a>`;
            });
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    function buildTableOfContents() {
        const sidebar = document.getElementById('articleSidebar');
        const articleBody = document.querySelector('.article-body');
        if (!articleBody || !sidebar) return;

        const headings = articleBody.querySelectorAll('h2, h3, h4');
        if (headings.length === 0) {
            sidebar.innerHTML = '';
            return;
        }

        let tocHTML = `<div class="toc-title"><i class="fas fa-list"></i> On This Page</div><ul class="toc-list">`;
        headings.forEach((h, i) => {
            const id = 'heading-' + i;
            h.id = id;
            const level = h.tagName.toLowerCase();
            tocHTML += `<li><a href="#${id}" class="toc-${level}">${h.textContent}</a></li>`;
        });
        tocHTML += '</ul>';

        // Article info box
        if (state.currentArticle) {
            const a = state.currentArticle;
            tocHTML += `
                <div class="article-info-box">
                    <h4>Article Info</h4>
                    <div class="info-row"><span class="label">Category</span><span>${a.category}</span></div>
                    <div class="info-row"><span class="label">Difficulty</span><span>${a.difficulty}</span></div>
                    <div class="info-row"><span class="label">Words</span><span>${(a.word_count || 0).toLocaleString()}</span></div>
                    <div class="info-row"><span class="label">Status</span><span>${a.status || 'Published'}</span></div>
                    <div class="info-row"><span class="label">Updated</span><span>${a.last_edited || 'N/A'}</span></div>
                </div>
            `;
        }

        sidebar.innerHTML = tocHTML;

        // Bind ToC clicks
        sidebar.querySelectorAll('.toc-list a').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.getElementById(a.getAttribute('href').slice(1));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    // ====== GRAPH VIEW ======
    function renderGraphView() {
        showView('graph');
        setTimeout(() => drawGraph(), 100);
    }

    function drawGraph() {
        const canvas = document.getElementById('graphCanvas');
        const container = document.getElementById('graphContainer');
        if (!canvas || !container) return;

        const rect = container.getBoundingClientRect();
        canvas.width = rect.width * 2;
        canvas.height = rect.height * 2;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';

        const ctx = canvas.getContext('2d');
        ctx.scale(2, 2);
        const W = rect.width;
        const H = rect.height;

        // Prepare nodes
        const nodes = state.articles.map((article, i) => {
            const conf = getCategoryConfig(article.category);
            const angle = (2 * Math.PI * i) / state.articles.length;
            const rx = W * 0.35;
            const ry = H * 0.35;
            return {
                x: W / 2 + rx * Math.cos(angle) + (Math.random() - 0.5) * 40,
                y: H / 2 + ry * Math.sin(angle) + (Math.random() - 0.5) * 40,
                slug: article.slug,
                title: article.title,
                color: conf.color,
                radius: 6 + Math.min(parseArray(article.backlinks).length * 2, 12),
                article: article,
            };
        });

        // Prepare edges
        const edges = [];
        state.articles.forEach(article => {
            const linksTo = parseArray(article.links_to);
            linksTo.forEach(targetSlug => {
                const sourceNode = nodes.find(n => n.slug === article.slug);
                const targetNode = nodes.find(n => n.slug === targetSlug);
                if (sourceNode && targetNode) {
                    edges.push({ source: sourceNode, target: targetNode });
                }
            });
        });

        // Simple force-directed layout (a few iterations)
        for (let iter = 0; iter < 100; iter++) {
            // Repulsion between all nodes
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    let dx = nodes[j].x - nodes[i].x;
                    let dy = nodes[j].y - nodes[i].y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let force = 800 / (dist * dist);
                    let fx = (dx / dist) * force;
                    let fy = (dy / dist) * force;
                    nodes[i].x -= fx;
                    nodes[i].y -= fy;
                    nodes[j].x += fx;
                    nodes[j].y += fy;
                }
            }

            // Attraction along edges
            edges.forEach(edge => {
                let dx = edge.target.x - edge.source.x;
                let dy = edge.target.y - edge.source.y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                let force = (dist - 100) * 0.01;
                let fx = (dx / dist) * force;
                let fy = (dy / dist) * force;
                edge.source.x += fx;
                edge.source.y += fy;
                edge.target.x -= fx;
                edge.target.y -= fy;
            });

            // Center gravity
            nodes.forEach(n => {
                n.x += (W / 2 - n.x) * 0.01;
                n.y += (H / 2 - n.y) * 0.01;
                // Keep in bounds
                n.x = Math.max(40, Math.min(W - 40, n.x));
                n.y = Math.max(40, Math.min(H - 40, n.y));
            });
        }

        // Draw edges
        ctx.lineWidth = 1;
        edges.forEach(edge => {
            ctx.beginPath();
            ctx.moveTo(edge.source.x, edge.source.y);
            ctx.lineTo(edge.target.x, edge.target.y);
            ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border-primary').trim() || '#e5e7eb';
            ctx.globalAlpha = 0.4;
            ctx.stroke();
            ctx.globalAlpha = 1;
        });

        // Draw nodes
        nodes.forEach(node => {
            // Glow
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius + 4, 0, Math.PI * 2);
            ctx.fillStyle = node.color + '20';
            ctx.fill();

            // Node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
            ctx.fillStyle = node.color;
            ctx.fill();
            ctx.strokeStyle = node.color;
            ctx.lineWidth = 2;
            ctx.stroke();

            // Label
            ctx.font = '500 11px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#111827';
            
            // Truncate long titles
            let label = node.title.length > 22 ? node.title.slice(0, 20) + '…' : node.title;
            ctx.fillText(label, node.x, node.y + node.radius + 6);
        });

        // Click handler for nodes
        canvas.onclick = (e) => {
            const canvasRect = canvas.getBoundingClientRect();
            const mx = e.clientX - canvasRect.left;
            const my = e.clientY - canvasRect.top;
            for (const node of nodes) {
                const dx = mx - node.x;
                const dy = my - node.y;
                if (dx * dx + dy * dy < (node.radius + 6) * (node.radius + 6)) {
                    openArticle(node.slug);
                    return;
                }
            }
        };

        // Hover cursor
        canvas.onmousemove = (e) => {
            const canvasRect = canvas.getBoundingClientRect();
            const mx = e.clientX - canvasRect.left;
            const my = e.clientY - canvasRect.top;
            let hovering = false;
            for (const node of nodes) {
                const dx = mx - node.x;
                const dy = my - node.y;
                if (dx * dx + dy * dy < (node.radius + 6) * (node.radius + 6)) {
                    hovering = true;
                    canvas.title = node.title;
                    break;
                }
            }
            canvas.style.cursor = hovering ? 'pointer' : 'grab';
            if (!hovering) canvas.title = '';
        };
    }

    // ====== RECENT VIEW ======
    function renderRecentView() {
        const sorted = [...state.articles].sort((a, b) => {
            return (b.last_edited || '').localeCompare(a.last_edited || '');
        });
        const list = document.getElementById('recentList');
        list.innerHTML = '';
        sorted.forEach(article => {
            list.appendChild(createArticleListItem(article));
        });
        showView('recent');
    }

    // ====== SEARCH ======
    function handleSearch(query) {
        const resultsEl = document.getElementById('searchResults');
        if (!query || query.trim().length < 2) {
            resultsEl.classList.remove('active');
            resultsEl.innerHTML = '';
            return;
        }

        const q = query.toLowerCase().trim();
        const matches = state.articles.filter(a => {
            return (a.title || '').toLowerCase().includes(q) ||
                   (a.summary || '').toLowerCase().includes(q) ||
                   (a.content || '').toLowerCase().includes(q) ||
                   parseArray(a.tags).some(t => t.toLowerCase().includes(q));
        }).slice(0, 8);

        if (matches.length === 0) {
            resultsEl.innerHTML = '<div class="search-result-item"><div class="search-result-title">No results found</div></div>';
        } else {
            resultsEl.innerHTML = matches.map(a => {
                const conf = getCategoryConfig(a.category);
                return `
                    <div class="search-result-item" data-slug="${a.slug}">
                        <div class="search-result-title">${highlightMatch(a.title, q)}</div>
                        <div class="search-result-summary">${highlightMatch(a.summary || '', q)}</div>
                        <div class="search-result-meta">
                            <span style="color:${conf.color}">${a.category}</span>
                            <span>${a.difficulty}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        resultsEl.classList.add('active');

        // Bind click on results
        resultsEl.querySelectorAll('.search-result-item[data-slug]').forEach(item => {
            item.addEventListener('click', () => {
                openArticle(item.dataset.slug);
                resultsEl.classList.remove('active');
                document.getElementById('searchInput').value = '';
            });
        });
    }

    function highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // ====== EVENTS ======
    function bindEvents() {
        // Workspace controls
        const sourceEl = document.getElementById('workspaceSource');
        if (sourceEl) {
            const src = state.siteContext && state.siteContext.source_root;
            sourceEl.textContent = src || 'No source folder connected';
        }
        const rescanBtn = document.getElementById('rescanBtn');
        if (rescanBtn) {
            rescanBtn.addEventListener('click', async () => {
                const status = document.getElementById('rescanStatus');
                rescanBtn.disabled = true;
                status.className = 'workspace-status';
                status.textContent = 'Scanning…';
                try {
                    const url = state.workspaceId
                        ? `api/rescan?workspace_id=${encodeURIComponent(state.workspaceId)}`
                        : 'api/rescan';
                    const res = await fetch(url, { method: 'POST' });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.error || 'Rescan failed');
                    status.className = 'workspace-status success';
                    status.textContent = `Scanned ${data.scanned_file_count ?? '?'} files`;
                    setTimeout(() => window.location.reload(), 800);
                } catch (e) {
                    status.className = 'workspace-status error';
                    status.textContent = e.message;
                    rescanBtn.disabled = false;
                }
            });
        }

        // Sidebar nav
        document.querySelectorAll('.sidebar-link[data-view]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.dataset.view;
                if (view === 'home') {
                    renderHomeView();
                    window.location.hash = '';
                } else if (view === 'all') {
                    renderArticleList(state.articles, 'All Articles');
                    window.location.hash = 'all';
                } else if (view === 'graph') {
                    renderGraphView();
                    window.location.hash = 'graph';
                } else if (view === 'recent') {
                    renderRecentView();
                    window.location.hash = 'recent';
                }
            });
        });

        // Difficulty filter
        document.querySelectorAll('.difficulty-badge').forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                filterByDifficulty(badge.dataset.difficulty);
            });
        });

        // Sort select
        document.getElementById('sortSelect').addEventListener('change', (e) => {
            const sortBy = e.target.value;
            let sorted;
            if (state.currentFilter) {
                if (state.currentFilter.type === 'category') {
                    sorted = state.articles.filter(a => a.category === state.currentFilter.value);
                } else if (state.currentFilter.type === 'tag') {
                    sorted = state.articles.filter(a => parseArray(a.tags).includes(state.currentFilter.value));
                } else if (state.currentFilter.type === 'difficulty') {
                    sorted = state.articles.filter(a => a.difficulty === state.currentFilter.value);
                } else {
                    sorted = [...state.articles];
                }
            } else {
                sorted = [...state.articles];
            }

            if (sortBy === 'title') sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
            else if (sortBy === 'date') sorted.sort((a, b) => (b.last_edited || '').localeCompare(a.last_edited || ''));
            else if (sortBy === 'category') sorted.sort((a, b) => (a.category || '').localeCompare(b.category || ''));
            else if (sortBy === 'difficulty') {
                const order = { 'Beginner': 0, 'Intermediate': 1, 'Advanced': 2 };
                sorted.sort((a, b) => (order[a.difficulty] || 0) - (order[b.difficulty] || 0));
            }

            const title = document.getElementById('listTitle').textContent;
            const list = document.getElementById('articleList');
            list.innerHTML = '';
            sorted.forEach(a => list.appendChild(createArticleListItem(a)));
        });

        // Search
        const searchInput = document.getElementById('searchInput');
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => handleSearch(e.target.value), 200);
        });

        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) {
                handleSearch(searchInput.value);
            }
        });

        // Close search results on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                document.getElementById('searchResults').classList.remove('active');
            }
        });

        // Ctrl+K shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
            if (e.key === 'Escape') {
                document.getElementById('searchResults').classList.remove('active');
                searchInput.blur();
            }
        });

        // Sidebar toggle
        document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);

        // Mobile overlay
        document.getElementById('sidebarOverlay').addEventListener('click', closeMobileSidebar);

        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', toggleTheme);

        // Hash navigation
        window.addEventListener('hashchange', handleHashNavigation);

        // Resize graph
        window.addEventListener('resize', () => {
            if (state.currentView === 'graph') {
                drawGraph();
            }
        });
    }

    // ====== SIDEBAR TOGGLE ======
    function toggleSidebar() {
        const sidebar = document.getElementById('wikiSidebar');
        const main = document.querySelector('.wiki-main');
        const overlay = document.getElementById('sidebarOverlay');

        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('mobile-open');
            overlay.classList.toggle('active');
        } else {
            sidebar.classList.toggle('collapsed');
            main.classList.toggle('expanded');
            state.sidebarOpen = !sidebar.classList.contains('collapsed');
        }
    }

    function closeMobileSidebar() {
        document.getElementById('wikiSidebar').classList.remove('mobile-open');
        document.getElementById('sidebarOverlay').classList.remove('active');
    }

    // ====== THEME ======
    function initTheme() {
        const saved = localStorage.getItem('wiki-theme');
        if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.setAttribute('data-theme', 'dark');
            state.darkMode = true;
            updateThemeIcon();
        }
    }

    function toggleTheme() {
        state.darkMode = !state.darkMode;
        document.documentElement.setAttribute('data-theme', state.darkMode ? 'dark' : 'light');
        localStorage.setItem('wiki-theme', state.darkMode ? 'dark' : 'light');
        updateThemeIcon();
        // Redraw graph if visible
        if (state.currentView === 'graph') {
            setTimeout(() => drawGraph(), 100);
        }
    }

    function updateThemeIcon() {
        const icon = document.querySelector('#themeToggle i');
        icon.className = state.darkMode ? 'fas fa-sun' : 'fas fa-moon';
    }

    // ====== HASH NAVIGATION ======
    function handleHashNavigation() {
        const hash = window.location.hash.slice(1);
        if (!hash) return;

        const parts = hash.split('/');
        const type = parts[0];
        const value = decodeURIComponent(parts.slice(1).join('/'));

        if (type === 'article' && value) {
            openArticle(value);
        } else if (type === 'category' && value) {
            filterByCategory(value);
        } else if (type === 'tag' && value) {
            filterByTag(value);
        } else if (type === 'difficulty' && value) {
            filterByDifficulty(value);
        } else if (type === 'all') {
            renderArticleList(state.articles, 'All Articles');
        } else if (type === 'graph') {
            renderGraphView();
        } else if (type === 'recent') {
            renderRecentView();
        }
    }

    // ====== UTILITIES ======
    function parseArray(val) {
        if (Array.isArray(val)) return val;
        if (typeof val === 'string') {
            try { return JSON.parse(val); } catch(e) { return []; }
        }
        return [];
    }

    function renderGraphLegend() {
        const legend = document.getElementById('graphLegend');
        if (!legend) return;
        legend.innerHTML = Object.entries(state.categories)
            .sort((a, b) => b[1] - a[1])
            .map(([category]) => {
                const conf = getCategoryConfig(category);
                return `<span class="legend-item"><span class="legend-dot" style="background:${conf.color}"></span> ${category}</span>`;
            })
            .join('');
    }

    // ====== START ======
    document.addEventListener('DOMContentLoaded', init);

})();
