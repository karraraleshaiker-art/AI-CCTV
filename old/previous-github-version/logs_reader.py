#!/usr/bin/env python3
"""
AI-CCTV Logs Reader
A lightweight local web server to view and inspect logs.md with a modern UI.
Zero external dependencies (uses standard library http.server and webbrowser).
"""

import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS_FILE = ROOT / "logs.md"
PORT = 8808

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-CCTV — System Logs & Changelog Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(59, 130, 246, 0.4);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-purple: #8b5cf6;
            --accent-red: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.6;
            padding: 0;
            margin: 0;
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 5rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .brand-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(6, 182, 212, 0.3);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .title {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #ffffff 30%, #93c5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-secondary);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--accent-blue);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border-color: #3b82f6;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }

        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .stat-label {
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #ffffff;
            display: flex;
            align-items: baseline;
            gap: 0.4rem;
        }

        .stat-subtext {
            font-size: 0.78rem;
            color: var(--accent-cyan);
        }

        /* Tabs & Controls */
        .controls-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 2rem;
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            padding: 0.75rem 1rem;
            border-radius: 10px;
        }

        .search-box {
            position: relative;
            flex: 1;
            max-width: 400px;
        }

        .search-input {
            width: 100%;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.55rem 1rem 0.55rem 2.4rem;
            color: #fff;
            font-size: 0.88rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-input:focus {
            border-color: var(--accent-blue);
        }

        .search-icon {
            position: absolute;
            left: 0.8rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .filter-buttons {
            display: flex;
            gap: 0.5rem;
        }

        .filter-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-btn.active, .filter-btn:hover {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-cyan);
            border-color: rgba(59, 130, 246, 0.3);
        }

        /* Overview Accordion */
        .info-accordion {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 2.5rem;
            overflow: hidden;
        }

        .accordion-header {
            padding: 1.25rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
            background: rgba(255, 255, 255, 0.02);
            font-weight: 600;
            font-size: 1.05rem;
        }

        .accordion-header:hover {
            background: rgba(255, 255, 255, 0.04);
        }

        .accordion-content {
            padding: 1.5rem;
            border-top: 1px solid var(--border);
            display: none;
        }

        .accordion-content.open {
            display: block;
        }

        .prose h1, .prose h2, .prose h3 {
            color: #fff;
            margin: 1.2rem 0 0.6rem;
        }
        .prose p {
            color: #d1d5db;
            margin-bottom: 0.8rem;
        }
        .prose ul, .prose ol {
            padding-left: 1.5rem;
            color: #d1d5db;
            margin-bottom: 0.8rem;
        }
        .prose li {
            margin-bottom: 0.4rem;
        }
        .prose code {
            font-family: 'Fira Code', monospace;
            background: rgba(0, 0, 0, 0.4);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.88em;
            color: #93c5fd;
        }
        .prose pre {
            background: #050811;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid var(--border);
            margin: 1rem 0;
        }
        .prose pre code {
            background: transparent;
            padding: 0;
            color: #e2e8f0;
        }

        /* Changelog Cards */
        .cards-list {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .log-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            position: relative;
            transition: all 0.25s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .log-card:hover {
            border-color: var(--border-highlight);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .badge-author-ali {
            background: rgba(59, 130, 246, 0.18);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.35);
        }

        .badge-author-karrar {
            background: rgba(16, 185, 129, 0.18);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
        }

        .badge-agent {
            background: rgba(139, 92, 246, 0.18);
            color: #c084fc;
            border: 1px solid rgba(139, 92, 246, 0.35);
        }

        .badge-time {
            background: rgba(255, 255, 255, 0.06);
            color: #9ca3af;
            border: 1px solid var(--border);
        }

        .card-meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.2rem;
            margin: 1.2rem 0;
            background: rgba(0, 0, 0, 0.25);
            padding: 1.2rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
        }

        .meta-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }

        .meta-content {
            font-size: 0.9rem;
            color: #e5e7eb;
        }

        .file-tag {
            display: inline-block;
            font-family: 'Fira Code', monospace;
            font-size: 0.78rem;
            padding: 0.18rem 0.5rem;
            border-radius: 4px;
            margin: 0.2rem 0.2rem 0.2rem 0;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border);
        }

        .tag-added { color: var(--accent-green); border-color: rgba(16, 185, 129, 0.3); }
        .tag-modified { color: var(--accent-amber); border-color: rgba(245, 158, 11, 0.3); }
        .tag-deleted { color: var(--accent-red); border-color: rgba(239, 68, 68, 0.3); }

        .line-diffs {
            margin-top: 1rem;
            background: #060913;
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 1rem;
            font-family: 'Fira Code', monospace;
            font-size: 0.82rem;
            color: #94a3b8;
            max-height: 250px;
            overflow-y: auto;
        }

        .line-diff-item {
            padding: 0.35rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #cbd5e1;
        }
        .line-diff-item:last-child {
            border-bottom: none;
        }

        /* Pulse indicator */
        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-green);
            display: inline-block;
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.7; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.7; }
        }

        footer {
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <div class="brand-badge">
                    <span class="live-dot"></span> Solar Panel Factory AI CCTV
                </div>
                <h1 class="title">System Logs & Changelog</h1>
                <p class="subtitle">Engineering audit trail & collaboration registry between Ali Nasser & Karrar Haider</p>
            </div>
            <div class="header-actions">
                <button class="btn" onclick="fetchLogs()">
                    Refresh
                </button>
                <a href="https://github.com/karraraleshaiker-art/AI-CCTV" target="_blank" class="btn btn-primary">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                    GitHub Repo
                </a>
            </div>
        </header>

        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Log Entries</div>
                <div class="stat-value" id="stat-total-logs">--</div>
                <div class="stat-subtext">Verified Changelog Records</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Engineers</div>
                <div class="stat-value" style="font-size: 1.3rem;">Ali & Karrar</div>
                <div class="stat-subtext">Single-Session Isolation</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Last Log Update</div>
                <div class="stat-value" id="stat-last-time" style="font-size: 1.1rem; line-height: 1.4;">--</div>
                <div class="stat-subtext" id="stat-last-author">Author: --</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">CCTV Scale</div>
                <div class="stat-value">40–45</div>
                <div class="stat-subtext">Solar Factory Camera Streams</div>
            </div>
        </div>

        <!-- Project Overview Accordion -->
        <div class="info-accordion">
            <div class="accordion-header" onclick="toggleAccordion('overview-content', this)">
                <span>Section 1 & 2: Factory Context & Engineering Rules</span>
                <span id="accordion-arrow">[v]</span>
            </div>
            <div id="overview-content" class="accordion-content prose">
                <div id="markdown-overview">Loading overview...</div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls-bar">
            <div class="search-box">
                <span class="search-icon"></span>
                <input type="text" id="searchInput" class="search-input" placeholder="Search logs by keyword, author, file..." oninput="filterCards()">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="setAuthorFilter('ALL', this)">All Logs</button>
                <button class="filter-btn" onclick="setAuthorFilter('Ali Nasser', this)">Ali Nasser</button>
                <button class="filter-btn" onclick="setAuthorFilter('Karrar Haider', this)">Karrar Haider</button>
            </div>
        </div>

        <!-- Changelog Cards Container -->
        <div class="cards-list" id="cardsContainer">
            <div style="text-align: center; padding: 3rem; color: var(--text-muted);">Loading changelog entries...</div>
        </div>

        <footer>
            AI-CCTV Factory Monitoring Platform — Automated Changelog & Activity Dashboard
        </footer>
    </div>

    <script>
        let logsData = null;
        let currentAuthorFilter = 'ALL';

        function toggleAccordion(id, btn) {
            const content = document.getElementById(id);
            content.classList.toggle('open');
            const arrow = btn.querySelector('#accordion-arrow');
            arrow.textContent = content.classList.contains('open') ? '[^]' : '[v]';
        }

        function setAuthorFilter(author, btn) {
            currentAuthorFilter = author;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterCards();
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs?t=' + Date.now());
                logsData = await res.json();
                renderUI();
            } catch (err) {
                console.error('Failed to load logs:', err);
                document.getElementById('cardsContainer').innerHTML = 
                    `<div style="color: var(--accent-red); text-align: center; padding: 2rem;">Error reading logs.md: ${err.message}</div>`;
            }
        }

        function renderUI() {
            if (!logsData) return;

            // Render Overview
            if (logsData.overview_raw) {
                document.getElementById('markdown-overview').innerHTML = marked.parse(logsData.overview_raw);
            }

            // Stats
            document.getElementById('stat-total-logs').textContent = logsData.cards.length;
            if (logsData.cards.length > 0) {
                const latest = logsData.cards[logsData.cards.length - 1];
                document.getElementById('stat-last-time').textContent = latest.timestamp || 'N/A';
                document.getElementById('stat-last-author').textContent = 'By ' + (latest.author || 'Unknown');
            }

            filterCards();
        }

        function filterCards() {
            if (!logsData || !logsData.cards) return;
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const container = document.getElementById('cardsContainer');

            const filtered = logsData.cards.filter(c => {
                const matchAuthor = (currentAuthorFilter === 'ALL') || 
                    (c.author && c.author.toLowerCase().includes(currentAuthorFilter.toLowerCase()));
                
                const searchStr = `${c.id} ${c.title} ${c.author} ${c.agent} ${(c.purpose_list || []).join(' ')} ${c.files.join(' ')} ${c.diffs.join(' ')}`.toLowerCase();
                const matchQuery = !query || searchStr.includes(query);

                return matchAuthor && matchQuery;
            });

            if (filtered.length === 0) {
                container.innerHTML = `<div style="text-align: center; padding: 3rem; color: var(--text-muted); background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">No matching changelog entries found.</div>`;
                return;
            }

            // Render cards in reverse chronological order (newest first)
            container.innerHTML = filtered.slice().reverse().map(c => {
                const isAli = c.author && c.author.includes('Ali');
                const authorBadgeClass = isAli ? 'badge-author-ali' : 'badge-author-karrar';

                const filesHtml = c.files.map(f => {
                    let cls = 'tag-modified';
                    if (f.includes('[ADDED]')) cls = 'tag-added';
                    else if (f.includes('[DELETED]')) cls = 'tag-deleted';
                    return `<span class="file-tag ${cls}">${escapeHtml(f)}</span>`;
                }).join('');

                const purposeList = (c.purpose_list && c.purpose_list.length > 0) ? c.purpose_list : (c.purpose ? [c.purpose] : []);
                const purposeHtml = purposeList.map(p => `<li style="margin-bottom: 0.35rem;">${escapeHtml(p)}</li>`).join('');

                const diffsHtml = c.diffs.map(d => `<div class="line-diff-item">* ${escapeHtml(d)}</div>`).join('');

                return `
                    <div class="log-card">
                        <div class="card-header">
                            <div class="card-title">
                                <span>[${escapeHtml(c.id)}] - ${escapeHtml(c.title)}</span>
                            </div>
                            <div class="badges">
                                <span class="badge ${authorBadgeClass}">Author: ${escapeHtml(c.author || 'Unknown')}</span>
                                <span class="badge badge-agent">Agent: ${escapeHtml(c.agent || 'AI')}</span>
                                <span class="badge badge-time">Time: ${escapeHtml(c.timestamp || 'N/A')}</span>
                            </div>
                        </div>

                        <div class="card-meta-grid">
                            <div class="meta-item" style="grid-column: 1 / -1;">
                                <div class="meta-label">Objective / Purpose</div>
                                <div class="meta-content">
                                    <ul style="padding-left: 1.2rem; margin-top: 0.3rem; color: #e2e8f0; line-height: 1.5;">
                                        ${purposeHtml || '<li>None specified</li>'}
                                    </ul>
                                </div>
                            </div>
                            <div class="meta-item" style="grid-column: 1 / -1;">
                                <div class="meta-label">Affected Files (${c.files.length})</div>
                                <div class="meta-content" style="margin-top: 0.3rem;">${filesHtml || 'None specified'}</div>
                            </div>
                        </div>

                        ${diffsHtml ? `
                            <div style="margin-top: 0.8rem;">
                                <div class="meta-label" style="margin-bottom: 0.4rem;">Line Changes & Scope</div>
                                <div class="line-diffs">${diffsHtml}</div>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Auto fetch on load
        fetchLogs();
        // Auto refresh every 5 seconds
        setInterval(fetchLogs, 5000);
    </script>
</body>
</html>
"""

def parse_logs_md():
    if not LOGS_FILE.exists():
        return {"overview_raw": "logs.md not found", "cards": []}

    content = LOGS_FILE.read_text(encoding="utf-8")
    lines = content.splitlines()

    cards = []
    current_card = None
    section = None
    overview_lines = []
    in_section_3 = False

    for line in lines:
        stripped = line.strip()

        if not in_section_3:
            if "Section 3:" in stripped or "# Section 3" in stripped:
                in_section_3 = True
            else:
                overview_lines.append(line)
            continue

        if not stripped or stripped == "---":
            continue

        card_match = re.match(r"^###\s*.*\[(Log\s*#?[^\]]+)\]\s*-\s*(.+)", stripped)
        if card_match:
            if current_card:
                cards.append(current_card)
            current_card = {
                "id": card_match.group(1).strip(),
                "title": card_match.group(2).strip(),
                "author": "",
                "timestamp": "",
                "agent": "",
                "purpose_list": [],
                "files": [],
                "diffs": []
            }
            section = None
            continue

        if not current_card:
            continue

        if stripped.startswith("- **Author**:"):
            current_card["author"] = stripped.split(":", 1)[1].strip()
            section = None
        elif stripped.startswith("- **Timestamp**:"):
            current_card["timestamp"] = stripped.split(":", 1)[1].strip()
            section = None
        elif stripped.startswith("- **AI Agent**:"):
            current_card["agent"] = stripped.split(":", 1)[1].strip()
            section = None
        elif stripped.startswith("- **Objective / Purpose**:"):
            inline_val = stripped.split(":", 1)[1].strip()
            if inline_val:
                current_card["purpose_list"].append(inline_val)
            section = "purpose"
        elif stripped.startswith("- **Affected Files**:"):
            section = "files"
        elif stripped.startswith("- **Line Changes Breakdown**:"):
            section = "diffs"
        else:
            item_text = re.sub(r"^\s*[-*]\s*", "", stripped)
            if section == "purpose":
                if item_text:
                    current_card["purpose_list"].append(item_text)
            elif section == "files":
                clean_f = item_text.replace("`", "").strip()
                if clean_f:
                    current_card["files"].append(clean_f)
            elif section == "diffs":
                clean_d = item_text.replace("`", "").strip()
                if clean_d:
                    current_card["diffs"].append(clean_d)

    if current_card:
        cards.append(current_card)

    return {
        "overview_raw": "\n".join(overview_lines),
        "cards": cards
    }


class LogsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/logs":
            data = parse_logs_md()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

    def log_message(self, format, *args):
        # Silent logs for cleaner terminal output
        pass


def run_server(port=PORT):
    actual_port = port
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), LogsHandler)
            actual_port = p
            break
        except OSError:
            continue
    else:
        print(f"[LOGS READER] Error: All ports from {port} to {port+20} are busy.")
        return

    url = f"http://127.0.0.1:{actual_port}"
    print(f"\n==========================================")
    print(f"  AI-CCTV Logs Reader is running at:")
    print(f"  {url}")
    print(f"==========================================\n")
    
    # Open browser automatically
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[LOGS READER] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    run_server()
