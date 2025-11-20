/**
 * Data visualization module for recon-again extension
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// Global SQL instance (initialized in extension.ts)
let globalSQL: any = null;

export function setGlobalSQL(sql: any) {
    globalSQL = sql;
}

export function getGlobalSQL(): any {
    return globalSQL;
}

export class VisualizationPanel {
    public static currentPanel: VisualizationPanel | undefined;
    private static readonly viewType = 'reconAgainVisualization';
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionPath: string;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionPath: string, context: vscode.ExtensionContext) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it
        if (VisualizationPanel.currentPanel) {
            VisualizationPanel.currentPanel._panel.reveal(column);
            return;
        }

        // Otherwise, create a new panel
        const panel = vscode.window.createWebviewPanel(
            VisualizationPanel.viewType,
            'Recon-Again Visualization',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [
                    vscode.Uri.file(path.join(extensionPath, 'media'))
                ],
                retainContextWhenHidden: true
            }
        );

        VisualizationPanel.currentPanel = new VisualizationPanel(panel, extensionPath, context);
    }

    private constructor(panel: vscode.WebviewPanel, extensionPath: string, context: vscode.ExtensionContext) {
        this._panel = panel;
        this._extensionPath = extensionPath;

        // Set the webview's initial html content
        this._update();

        // Listen for when the panel is disposed
        // This happens when the user closes the panel or when the panel is closed programmatically
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'refresh':
                        this._update();
                        return;
                    case 'viewSession':
                        vscode.commands.executeCommand('recon-again.viewResults', { sessionId: message.sessionId });
                        return;
                }
            },
            null,
            this._disposables
        );
    }

    public dispose() {
        VisualizationPanel.currentPanel = undefined;

        // Clean up our resources
        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        // Get data from database
        const data = this._getVisualizationData();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recon-Again Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            padding: 20px;
            line-height: 1.6;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--vscode-panel-border);
        }
        
        h1 {
            color: var(--vscode-textLink-foreground);
            font-size: 24px;
        }
        
        .refresh-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .refresh-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: var(--vscode-textLink-foreground);
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        
        .stat:last-child {
            border-bottom: none;
        }
        
        .stat-label {
            color: var(--vscode-descriptionForeground);
        }
        
        .stat-value {
            font-weight: bold;
            font-size: 18px;
            color: var(--vscode-textLink-foreground);
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .risk-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .risk-low { background: #4caf50; color: white; }
        .risk-medium { background: #ff9800; color: white; }
        .risk-high { background: #f44336; color: white; }
        .risk-critical { background: #9c27b0; color: white; }
        
        .session-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .session-item {
            padding: 12px;
            margin-bottom: 10px;
            background: var(--vscode-list-hoverBackground);
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .session-item:hover {
            background: var(--vscode-list-activeSelectionBackground);
        }
        
        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .session-target {
            font-weight: bold;
            color: var(--vscode-textLink-foreground);
        }
        
        .session-time {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        
        .session-tools {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        
        .tool-badge {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Recon-Again Data Visualization</h1>
        <button class="refresh-btn" onclick="refresh()">🔄 Refresh</button>
    </div>
    
    <div class="dashboard">
        ${this._renderStatsCards(data)}
        ${this._renderCharts(data)}
        ${this._renderSessionsList(data)}
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        
        function refresh() {
            vscode.postMessage({ command: 'refresh' });
        }
        
        function viewSession(sessionId) {
            vscode.postMessage({ command: 'viewSession', sessionId: sessionId });
        }
        
        ${this._renderChartScripts(data)}
    </script>
</body>
</html>`;
    }

    private _getVisualizationData(): any {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return { error: 'No workspace folder' };
        }

        const dbPath = path.join(workspaceFolder.uri.fsPath, 'data', 'recon_again.db');
        if (!fs.existsSync(dbPath)) {
            return { error: 'Database not found at data/recon_again.db' };
        }

        try {
            // Use the global SQL instance
            let SQL = globalSQL || getGlobalSQL();
            
            if (!SQL) {
                // Try to get it from the extension module
                try {
                    // Dynamic import to avoid circular dependency
                    const extModule = require('../out/extension');
                    SQL = extModule.getGlobalSQL();
                } catch (e) {
                    // If that fails, try direct require
                    try {
                        const sqljs = require('sql.js');
                        const initFn = sqljs.default || sqljs;
                        
                        if (typeof initFn === 'function') {
                            // It's the init function, we can't use it synchronously here
                            throw new Error('SQL.js needs to be initialized. Please wait a moment and try again.');
                        } else if (initFn && initFn.Database) {
                            SQL = initFn;
                        } else {
                            throw new Error('SQL.js Database constructor not found');
                        }
                    } catch (e2) {
                        throw new Error('SQL.js not available. Please ensure the extension is properly activated.');
                    }
                }
            }
            
            if (!SQL || !SQL.Database) {
                throw new Error('SQL.js not properly initialized. Please restart VSCode.');
            }
            
            const buffer = fs.readFileSync(dbPath);
            const db = new SQL.Database(buffer);

            // Get total sessions
            const sessionsStmt = db.prepare('SELECT COUNT(*) as count FROM sessions');
            const sessionsResult: any[] = [];
            while (sessionsStmt.step()) {
                sessionsResult.push(sessionsStmt.getAsObject());
            }
            sessionsStmt.free();
            const totalSessions = sessionsResult[0]?.count || 0;

            // Get total targets
            const targetsStmt = db.prepare('SELECT COUNT(*) as count FROM targets');
            const targetsResult: any[] = [];
            while (targetsStmt.step()) {
                targetsResult.push(targetsStmt.getAsObject());
            }
            targetsStmt.free();
            const totalTargets = targetsResult[0]?.count || 0;

            // Get session status counts
            const statusStmt = db.prepare(`
                SELECT status, COUNT(*) as count 
                FROM sessions 
                GROUP BY status
            `);
            const statusCounts: any = {};
            while (statusStmt.step()) {
                const row = statusStmt.getAsObject();
                statusCounts[row.status] = row.count;
            }
            statusStmt.free();

            // Get tool statistics
            const toolStmt = db.prepare(`
                SELECT 
                    tool_name,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(execution_time) as avg_time
                FROM tool_results
                GROUP BY tool_name
                ORDER BY count DESC
            `);
            const toolStats: any = {};
            while (toolStmt.step()) {
                const row = toolStmt.getAsObject();
                toolStats[row.tool_name] = {
                    count: row.count,
                    success: row.success_count,
                    avgTime: row.avg_time || 0
                };
            }
            toolStmt.free();

            // Get recent sessions with details
            const recentStmt = db.prepare(`
                SELECT 
                    s.session_id,
                    s.status,
                    s.start_time,
                    s.tools_executed,
                    t.target,
                    a.risk_level
                FROM sessions s
                JOIN targets t ON s.target_id = t.id
                LEFT JOIN ai_analysis a ON s.session_id = a.session_id
                ORDER BY s.start_time DESC
                LIMIT 10
            `);
            const recentSessions: any[] = [];
            while (recentStmt.step()) {
                const row = recentStmt.getAsObject();
                recentSessions.push({
                    session_id: row.session_id,
                    target: row.target,
                    status: row.status,
                    start_time: row.start_time,
                    tools: row.tools_executed ? JSON.parse(row.tools_executed) : [],
                    risk_level: row.risk_level || 'low'
                });
            }
            recentStmt.free();

            // Get risk level distribution
            const riskStmt = db.prepare(`
                SELECT risk_level, COUNT(*) as count
                FROM ai_analysis
                WHERE risk_level IS NOT NULL
                GROUP BY risk_level
            `);
            const riskLevels: any = {};
            while (riskStmt.step()) {
                const row = riskStmt.getAsObject();
                riskLevels[row.risk_level] = row.count;
            }
            riskStmt.free();

            db.close();

            return {
                totalSessions,
                totalTargets,
                completedSessions: statusCounts.completed || 0,
                runningSessions: statusCounts.running || 0,
                failedSessions: statusCounts.failed || 0,
                toolStats,
                recentSessions,
                riskLevels
            };
        } catch (error: any) {
            console.error('Error fetching visualization data:', error);
            return { error: `Failed to load data: ${error.message}` };
        }
    }

    private _renderStatsCards(data: any): string {
        if (data.error) {
            return `<div class="card full-width"><div class="loading">${data.error}</div></div>`;
        }

        return `
        <div class="card">
            <h2>📈 Overview</h2>
            <div class="stat">
                <span class="stat-label">Total Sessions</span>
                <span class="stat-value">${data.totalSessions || 0}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Total Targets</span>
                <span class="stat-value">${data.totalTargets || 0}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Completed</span>
                <span class="stat-value">${data.completedSessions || 0}</span>
            </div>
            <div class="stat">
                <span class="stat-label">Running</span>
                <span class="stat-value">${data.runningSessions || 0}</span>
            </div>
        </div>
        `;
    }

    private _renderCharts(data: any): string {
        return `
        <div class="card full-width">
            <h2>🔧 Tool Performance</h2>
            <div class="chart-container">
                <canvas id="toolChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h2>⚡ Execution Times</h2>
            <div class="chart-container">
                <canvas id="timeChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h2>🎯 Success Rate</h2>
            <div class="chart-container">
                <canvas id="successChart"></canvas>
            </div>
        </div>
        `;
    }

    private _renderSessionsList(data: any): string {
        if (!data.recentSessions || data.recentSessions.length === 0) {
            return `<div class="card full-width"><div class="loading">No sessions found</div></div>`;
        }

        const sessionsHtml = data.recentSessions.map((session: any) => `
            <div class="session-item" onclick="viewSession('${session.session_id}')">
                <div class="session-header">
                    <span class="session-target">${session.target}</span>
                    <span class="risk-badge risk-${session.risk_level || 'low'}">${session.risk_level || 'N/A'}</span>
                </div>
                <div class="session-time">${new Date(session.start_time).toLocaleString()}</div>
                <div class="session-tools">
                    ${(session.tools || []).map((tool: string) => `<span class="tool-badge">${tool}</span>`).join('')}
                </div>
            </div>
        `).join('');

        return `
        <div class="card full-width">
            <h2>📋 Recent Sessions</h2>
            <div class="session-list">
                ${sessionsHtml}
            </div>
        </div>
        `;
    }

    private _renderChartScripts(data: any): string {
        const toolNames = Object.keys(data.toolStats || {});
        const toolCounts = toolNames.map((name: string) => (data.toolStats[name]?.count || 0));
        const toolSuccess = toolNames.map((name: string) => (data.toolStats[name]?.success || 0));
        const toolTimes = toolNames.map((name: string) => (data.toolStats[name]?.avgTime || 0));

        return `
        // Tool Performance Chart
        const toolCtx = document.getElementById('toolChart');
        if (toolCtx && ${toolNames.length} > 0) {
            new Chart(toolCtx, {
                type: 'bar',
                data: {
                    labels: ${JSON.stringify(toolNames)},
                    datasets: [{
                        label: 'Total Executions',
                        data: ${JSON.stringify(toolCounts)},
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }, {
                        label: 'Successful',
                        data: ${JSON.stringify(toolSuccess)},
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        title: { display: true, text: 'Tool Execution Statistics' }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        // Execution Time Chart
        const timeCtx = document.getElementById('timeChart');
        if (timeCtx && ${toolNames.length} > 0) {
            new Chart(timeCtx, {
                type: 'line',
                data: {
                    labels: ${JSON.stringify(toolNames)},
                    datasets: [{
                        label: 'Avg Execution Time (s)',
                        data: ${JSON.stringify(toolTimes)},
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        // Success Rate Chart
        const successCtx = document.getElementById('successChart');
        if (successCtx && ${toolNames.length} > 0) {
            const successRates = ${JSON.stringify(toolNames)}.map((name, i) => {
                const total = ${JSON.stringify(toolCounts)}[i] || 1;
                const success = ${JSON.stringify(toolSuccess)}[i] || 0;
                return total > 0 ? (success / total * 100).toFixed(1) : 0;
            });
            
            new Chart(successCtx, {
                type: 'doughnut',
                data: {
                    labels: ${JSON.stringify(toolNames)},
                    datasets: [{
                        label: 'Success Rate %',
                        data: successRates,
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(255, 206, 86, 0.6)',
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(153, 102, 255, 0.6)',
                            'rgba(255, 159, 64, 0.6)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'right' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.label + ': ' + context.parsed + '%';
                                }
                            }
                        }
                    }
                }
            });
        }
        `;
    }
}

