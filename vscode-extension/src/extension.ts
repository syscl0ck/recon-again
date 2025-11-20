/**
 * recon-again VSCode Extension
 * Provides UI for running reconnaissance and viewing results
 */

import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs';
import { VisualizationPanel } from './visualization';

// Try to import sql.js, but make it optional
let initSqlJs: any = null;

try {
    // Use require with error handling
    const sqljs = require('sql.js');
    // sql.js exports initSqlJs as default
    initSqlJs = sqljs.default || sqljs;
    // If it's an object with initSqlJs method, use that
    if (initSqlJs && typeof initSqlJs.initSqlJs === 'function') {
        initSqlJs = initSqlJs.initSqlJs;
    }
} catch (error: any) {
    console.error('Failed to load sql.js module:', error.message);
    console.error('This may be because sql.js is not bundled with the extension.');
    console.error('Database viewing features will not be available.');
}

const execAsync = promisify(exec);

interface Session {
    id: number;
    session_id: string;
    target_id: number;
    status: string;
    start_time: string;
    end_time: string | null;
    tools_executed: string | null;
}

interface Target {
    id: number;
    target: string;
    target_type: string | null;
    created_at: string;
}

interface ToolResult {
    id: number;
    session_id: string;
    tool_name: string;
    target: string;
    success: number;
    data: string | null;
    error: string | null;
    execution_time: number;
    timestamp: string;
}

interface AIAnalysis {
    id: number;
    session_id: string;
    target: string;
    summary: string | null;
    key_findings: string | null;
    recommendations: string | null;
    risk_level: string | null;
    interesting_targets: string | null;
    analysis_data: string | null;
}

function getDatabasePath(workspaceFolder?: vscode.WorkspaceFolder): string | null {
    if (!workspaceFolder) {
        return null;
    }
    const dbPath = path.join(workspaceFolder.uri.fsPath, 'data', 'recon_again.db');
    if (fs.existsSync(dbPath)) {
        return dbPath;
    }
    return null;
}

let SQL: any = null;

async function initSQL(): Promise<void> {
    if (!SQL && initSqlJs) {
        try {
            SQL = await initSqlJs();
            // Store the SQL instance globally for use in visualization
            try {
                const { setGlobalSQL } = await import('./visualization');
                setGlobalSQL(SQL);
            } catch (e) {
                console.warn('Could not set global SQL in visualization module:', e);
            }
        } catch (error) {
            console.error('Failed to initialize SQL.js:', error);
            throw error;
        }
    } else if (!initSqlJs) {
        throw new Error('sql.js module not available. Please reinstall the extension dependencies.');
    }
}

export function getGlobalSQL(): any {
    return SQL;
}

function getDatabase(dbPath: string | null): any {
    if (!dbPath || !fs.existsSync(dbPath)) {
        return null;
    }
    try {
        if (!SQL || !SQL.Database) {
            return null;
        }
        const buffer = fs.readFileSync(dbPath);
        return new SQL.Database(buffer);
    } catch (error) {
        console.error('Failed to open database:', error);
        return null;
    }
}

// Global reference to results provider for refreshing
let resultsProvider: ReconResultsProvider | null = null;

export async function activate(context: vscode.ExtensionContext) {
    console.log('recon-again extension is now active!');
    
    try {
        // Initialize SQL.js (don't fail if this doesn't work)
        try {
            await initSQL();
        } catch (error) {
            console.warn('Failed to initialize SQL.js:', error);
            // Continue anyway - commands should still work
        }

        // Register results tree view first (needed for refresh)
        resultsProvider = new ReconResultsProvider(context);
        const treeView = vscode.window.createTreeView('recon-again-results', {
            treeDataProvider: resultsProvider
        });
        
        // Register refresh command
        const refreshCommand = vscode.commands.registerCommand('recon-again.refreshResults', () => {
            if (resultsProvider) {
                resultsProvider.refresh();
            }
        });
        context.subscriptions.push(refreshCommand);

        // Register commands - do this synchronously to ensure they're registered
        const runReconCommand = vscode.commands.registerCommand('recon-again.runRecon', async () => {
            await runReconnaissance();
            // Refresh tree view after recon completes
            if (resultsProvider) {
                resultsProvider.refresh();
            }
        });

        const listToolsCommand = vscode.commands.registerCommand('recon-again.listTools', async () => {
            await listTools();
        });

        const viewResultsCommand = vscode.commands.registerCommand('recon-again.viewResults', async (item?: any, ...args: any[]) => {
            // Handle different ways the command can be called
            let sessionId: string | undefined;
            
            // Check arguments array first (VSCode sometimes passes arguments this way)
            if (args && args.length > 0 && args[0]) {
                const arg = args[0];
                if (typeof arg === 'object' && 'sessionId' in arg) {
                    sessionId = arg.sessionId;
                } else if (typeof arg === 'string') {
                    sessionId = arg;
                }
            }
            
            // Check item parameter
            if (!sessionId && item) {
                // Check if item has sessionId property (works for both SessionItem, ToolResultItem, and plain objects)
                if (typeof item === 'object') {
                    if ('sessionId' in item && item.sessionId) {
                        sessionId = item.sessionId;
                    }
                } else if (typeof item === 'string') {
                    sessionId = item;
                }
            }
            
            if (sessionId) {
                await viewSessionResults(sessionId);
            } else {
                // No session ID provided, show session picker
                await selectAndViewResult();
            }
        });

    const runToolCommand = vscode.commands.registerCommand('recon-again.runTool', async () => {
        await runSpecificTool();
    });

    const showVisualizationCommand = vscode.commands.registerCommand('recon-again.showVisualization', () => {
        const extensionPath = context.extensionPath;
        VisualizationPanel.createOrShow(extensionPath, context);
    });

    context.subscriptions.push(runReconCommand, listToolsCommand, viewResultsCommand, runToolCommand, showVisualizationCommand);
        
        // Verify commands are registered
        const registeredCommands = await vscode.commands.getCommands();
        const ourCommands = registeredCommands.filter(cmd => cmd.startsWith('recon-again.'));
        console.log('recon-again extension commands registered:', ourCommands);
        
        if (!ourCommands.includes('recon-again.viewResults')) {
            console.error('WARNING: recon-again.viewResults command was not registered!');
            vscode.window.showErrorMessage('Failed to register recon-again commands. Check the Developer Console for details.');
        }
    } catch (error) {
        console.error('Error activating recon-again extension:', error);
        vscode.window.showErrorMessage(`Failed to activate recon-again extension: ${error}`);
    }

    // Watch for database changes
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const dbPath = getDatabasePath(workspaceFolder);
        if (dbPath) {
            const watcher = vscode.workspace.createFileSystemWatcher(
                new vscode.RelativePattern(workspaceFolder, 'data/recon_again.db')
            );
            watcher.onDidChange(() => {
                if (resultsProvider) {
                    resultsProvider.refresh();
                }
            });
            watcher.onDidCreate(() => {
                if (resultsProvider) {
                    resultsProvider.refresh();
                }
            });
            context.subscriptions.push(watcher);
        }
    }
}

function getPythonCommand(): string {
    // Check user configuration first
    const config = vscode.workspace.getConfiguration('recon-again');
    const configuredPath = config.get<string>('pythonPath', '');
    if (configuredPath) {
        return configuredPath;
    }

    // Try to find Python executable
    // First check if we're in a virtual environment
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const venvPath = path.join(workspaceFolder.uri.fsPath, 'venv', 'bin', 'python');
        if (fs.existsSync(venvPath)) {
            return venvPath;
        }
        // Also check .venv
        const dotVenvPath = path.join(workspaceFolder.uri.fsPath, '.venv', 'bin', 'python');
        if (fs.existsSync(dotVenvPath)) {
            return dotVenvPath;
        }
    }
    // Try common Python commands
    return 'python3';
}

async function runReconnaissance() {
    const target = await vscode.window.showInputBox({
        prompt: 'Enter target (domain, IP, or identifier)',
        placeHolder: 'example.com'
    });

    if (!target) {
        return;
    }

    const config = vscode.workspace.getConfiguration('recon-again');
    const configPath = config.get<string>('configPath', '');
    const enableAI = config.get<boolean>('enableAI', true);

    const args = [target];
    if (configPath) {
        args.push('-c', configPath);
    }
    if (!enableAI) {
        args.push('--no-ai');
    }

    const outputChannel = vscode.window.createOutputChannel('recon-again');
    outputChannel.show();
    outputChannel.appendLine(`Starting reconnaissance on: ${target}`);
    outputChannel.appendLine('');

    const pythonCmd = getPythonCommand();
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder?.uri.fsPath || process.cwd();

    try {
        // Try using python -m recon_again.cli first (more reliable)
        let command = `${pythonCmd} -m recon_again.cli ${args.join(' ')}`;
        let { stdout, stderr } = await execAsync(command, {
            cwd: workspacePath,
            timeout: 3600000 // 1 hour timeout
        }).catch(async (error: any) => {
            // If that fails, try the recon-again command
            outputChannel.appendLine(`Note: Trying alternative command...`);
            try {
                return await execAsync(`recon-again ${args.join(' ')}`, {
                    cwd: workspacePath,
                    timeout: 3600000
                });
            } catch (err2: any) {
                throw new Error(`Failed to run recon-again. Make sure it's installed:\n  pip install -e .\n\nOriginal error: ${error.message}`);
            }
        });

        outputChannel.append(stdout);
        if (stderr) {
            outputChannel.append(stderr);
        }

        // Refresh tree view after recon completes
        if (resultsProvider) {
            resultsProvider.refresh();
        }

        vscode.window.showInformationMessage(`Reconnaissance completed for ${target}`);
    } catch (error: any) {
        outputChannel.appendLine(`Error: ${error.message}`);
        vscode.window.showErrorMessage(`Reconnaissance failed: ${error.message}`);
    }
}

async function listTools() {
    const pythonCmd = getPythonCommand();
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder?.uri.fsPath || process.cwd();

    try {
        // Try using python -m recon_again.cli first
        let stdout: string;
        try {
            const result = await execAsync(`${pythonCmd} -m recon_again.cli --list-tools`, {
                cwd: workspacePath
            });
            stdout = result.stdout;
        } catch (error: any) {
            // Fallback to recon-again command
            const result = await execAsync('recon-again --list-tools', {
                cwd: workspacePath
            });
            stdout = result.stdout;
        }

        const outputChannel = vscode.window.createOutputChannel('recon-again Tools');
        outputChannel.show();
        outputChannel.append(stdout);
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to list tools: ${error.message}\n\nMake sure recon-again is installed: pip install -e .`);
    }
}

async function runSpecificTool() {
    const pythonCmd = getPythonCommand();
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const workspacePath = workspaceFolder?.uri.fsPath || process.cwd();

    // First get list of tools
    try {
        let stdout: string;
        try {
            const result = await execAsync(`${pythonCmd} -m recon_again.cli --list-tools`, {
                cwd: workspacePath
            });
            stdout = result.stdout;
        } catch (error: any) {
            // Fallback to recon-again command
            const result = await execAsync('recon-again --list-tools', {
                cwd: workspacePath
            });
            stdout = result.stdout;
        }

        // Parse tools from output (simplified - would need better parsing)
        const toolMatch = stdout.match(/Available Tools:[\s\S]*/);
        if (!toolMatch) {
            vscode.window.showWarningMessage('Could not parse tool list');
            return;
        }

        const target = await vscode.window.showInputBox({
            prompt: 'Enter target',
            placeHolder: 'example.com'
        });

        if (!target) {
            return;
        }

        const tools = await vscode.window.showQuickPick(
            ['crt_sh', 'urlscan', 'hibp', 'sublist3r', 'dnsrecon', 'wayback', 'sherlock'],
            {
                placeHolder: 'Select tool to run'
            }
        );

        if (!tools) {
            return;
        }

        const outputChannel = vscode.window.createOutputChannel('recon-again');
        outputChannel.show();

        try {
            let command = `${pythonCmd} -m recon_again.cli ${target} -t ${tools}`;
            let toolOutput: string;
            try {
                const result = await execAsync(command, {
                    cwd: workspacePath,
                    timeout: 3600000
                });
                toolOutput = result.stdout;
            } catch (error: any) {
                // Fallback to recon-again command
                const result = await execAsync(`recon-again ${target} -t ${tools}`, {
                    cwd: workspacePath,
                    timeout: 3600000
                });
                toolOutput = result.stdout;
            }

            outputChannel.append(toolOutput);
            
            // Refresh tree view after tool completes
            if (resultsProvider) {
                resultsProvider.refresh();
            }

            vscode.window.showInformationMessage(`Tool ${tools} completed`);
        } catch (error: any) {
            outputChannel.appendLine(`Error: ${error.message}`);
            vscode.window.showErrorMessage(`Tool execution failed: ${error.message}`);
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to get tool list: ${error.message}\n\nMake sure recon-again is installed: pip install -e .`);
    }
}

async function viewSessionResults(sessionId: string) {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const dbPath = getDatabasePath(workspaceFolder);
    if (!dbPath) {
        vscode.window.showErrorMessage('Database not found at data/recon_again.db');
        return;
    }

    const db = getDatabase(dbPath);
    if (!db) {
        vscode.window.showErrorMessage('Failed to open database');
        return;
    }

    try {
        // Get session info
        const sessionStmt = db.prepare('SELECT * FROM sessions WHERE session_id = ?');
        sessionStmt.bind([sessionId]);
        const sessionRows: any[] = [];
        while (sessionStmt.step()) {
            sessionRows.push(sessionStmt.getAsObject());
        }
        sessionStmt.free();
        
        if (sessionRows.length === 0) {
            vscode.window.showErrorMessage('Session not found');
            db.close();
            return;
        }
        const sessionRow = sessionRows[0];
        const session: Session = {
            id: sessionRow.id,
            session_id: sessionRow.session_id,
            target_id: sessionRow.target_id,
            status: sessionRow.status,
            start_time: sessionRow.start_time,
            end_time: sessionRow.end_time,
            tools_executed: sessionRow.tools_executed
        };

        // Get target info
        const targetStmt = db.prepare('SELECT * FROM targets WHERE id = ?');
        targetStmt.bind([session.target_id]);
        const targetRows: any[] = [];
        while (targetStmt.step()) {
            targetRows.push(targetStmt.getAsObject());
        }
        targetStmt.free();
        
        let target: Target | undefined;
        if (targetRows.length > 0) {
            const targetRow = targetRows[0];
            target = {
                id: targetRow.id,
                target: targetRow.target,
                target_type: targetRow.target_type,
                created_at: targetRow.created_at
            };
        }

        // Get tool results
        const toolResultsStmt = db.prepare('SELECT * FROM tool_results WHERE session_id = ? ORDER BY timestamp');
        toolResultsStmt.bind([sessionId]);
        const toolResults: ToolResult[] = [];
        while (toolResultsStmt.step()) {
            const row = toolResultsStmt.getAsObject();
            toolResults.push({
                id: row.id,
                session_id: row.session_id,
                tool_name: row.tool_name,
                target: row.target,
                success: row.success,
                data: row.data,
                error: row.error,
                execution_time: row.execution_time,
                timestamp: row.timestamp
            });
        }
        toolResultsStmt.free();

        // Get AI analysis if available
        const aiAnalysisStmt = db.prepare('SELECT * FROM ai_analysis WHERE session_id = ?');
        aiAnalysisStmt.bind([sessionId]);
        const aiAnalysisRows: any[] = [];
        while (aiAnalysisStmt.step()) {
            aiAnalysisRows.push(aiAnalysisStmt.getAsObject());
        }
        aiAnalysisStmt.free();
        
        let aiAnalysis: AIAnalysis | undefined;
        if (aiAnalysisRows.length > 0) {
            const aiRow = aiAnalysisRows[0];
            aiAnalysis = {
                id: aiRow.id,
                session_id: aiRow.session_id,
                target: aiRow.target,
                summary: aiRow.summary,
                key_findings: aiRow.key_findings,
                recommendations: aiRow.recommendations,
                risk_level: aiRow.risk_level,
                interesting_targets: aiRow.interesting_targets,
                analysis_data: aiRow.analysis_data
            };
        }

        db.close();

        // Create a temporary JSON file to display
        const resultData: any = {
            session_id: session.session_id,
            target: target?.target || 'Unknown',
            target_type: target?.target_type || null,
            status: session.status,
            start_time: session.start_time,
            end_time: session.end_time,
            tools_executed: session.tools_executed ? JSON.parse(session.tools_executed) : [],
            results: {} as any
        };

        // Add tool results
        for (const toolResult of toolResults) {
            resultData.results[toolResult.tool_name] = {
                success: toolResult.success === 1,
                data: toolResult.data ? JSON.parse(toolResult.data) : null,
                error: toolResult.error,
                execution_time: toolResult.execution_time,
                timestamp: toolResult.timestamp
            };
        }

        // Add AI analysis
        if (aiAnalysis) {
            resultData.results.ai_analysis = {
                summary: aiAnalysis.summary,
                key_findings: aiAnalysis.key_findings ? JSON.parse(aiAnalysis.key_findings) : [],
                recommendations: aiAnalysis.recommendations ? JSON.parse(aiAnalysis.recommendations) : [],
                risk_level: aiAnalysis.risk_level,
                interesting_targets: aiAnalysis.interesting_targets ? JSON.parse(aiAnalysis.interesting_targets) : [],
                analysis_data: aiAnalysis.analysis_data ? JSON.parse(aiAnalysis.analysis_data) : null
            };
        }

        // Display in output channel
        const outputChannel = vscode.window.createOutputChannel('recon-again Results');
        outputChannel.show();
        outputChannel.clear();
        outputChannel.appendLine(`Target: ${resultData.target}`);
        outputChannel.appendLine(`Session ID: ${resultData.session_id}`);
        outputChannel.appendLine(`Status: ${resultData.status}`);
        outputChannel.appendLine(`Start Time: ${resultData.start_time}`);
        if (resultData.end_time) {
            outputChannel.appendLine(`End Time: ${resultData.end_time}`);
        }
        outputChannel.appendLine(`Tools Executed: ${resultData.tools_executed.join(', ')}`);
        outputChannel.appendLine('');

        // Show tool results
        for (const [toolName, toolResult] of Object.entries(resultData.results)) {
            const toolResultData: any = toolResult;
            if (toolName === 'ai_analysis') {
                outputChannel.appendLine('🤖 AI Analysis:');
                if (toolResultData.summary) {
                    outputChannel.appendLine(`  Summary: ${toolResultData.summary}`);
                }
                if (toolResultData.risk_level) {
                    outputChannel.appendLine(`  Risk Level: ${toolResultData.risk_level}`);
                }
                if (toolResultData.key_findings && toolResultData.key_findings.length > 0) {
                    outputChannel.appendLine(`  Key Findings: ${toolResultData.key_findings.join(', ')}`);
                }
            } else {
                outputChannel.appendLine(`🔧 ${toolName}:`);
                if (toolResultData.success) {
                    outputChannel.appendLine(`  Status: Success`);
                    if (toolResultData.data) {
                        outputChannel.appendLine(`  Data: ${JSON.stringify(toolResultData.data, null, 2)}`);
                    }
                } else {
                    outputChannel.appendLine(`  Status: Failed`);
                    if (toolResultData.error) {
                        outputChannel.appendLine(`  Error: ${toolResultData.error}`);
                    }
                }
                if (toolResultData.execution_time) {
                    outputChannel.appendLine(`  Execution Time: ${toolResultData.execution_time}s`);
                }
            }
            outputChannel.appendLine('');
        }

        // Also open as JSON document
        const jsonContent = JSON.stringify(resultData, null, 2);
        const doc = await vscode.workspace.openTextDocument({
            content: jsonContent,
            language: 'json'
        });
        await vscode.window.showTextDocument(doc);
    } catch (error: any) {
        db.close();
        vscode.window.showErrorMessage(`Failed to view session: ${error.message}`);
    }
}

async function selectAndViewResult() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const dbPath = getDatabasePath(workspaceFolder);
    if (!dbPath) {
        vscode.window.showWarningMessage('Database not found at data/recon_again.db');
        return;
    }

    const db = getDatabase(dbPath);
    if (!db) {
        vscode.window.showErrorMessage('Failed to open database');
        return;
    }

    try {
        // Get all sessions with target info
        const sessionsStmt = db.prepare(`
            SELECT s.*, t.target, t.target_type
            FROM sessions s
            JOIN targets t ON s.target_id = t.id
            ORDER BY s.start_time DESC
            LIMIT 50
        `);
        
        const sessions: any[] = [];
        while (sessionsStmt.step()) {
            const row = sessionsStmt.getAsObject();
            sessions.push({
                session_id: row.session_id,
                target_id: row.target_id,
                status: row.status,
                start_time: row.start_time,
                end_time: row.end_time,
                tools_executed: row.tools_executed,
                target: row.target,
                target_type: row.target_type
            });
        }
        sessionsStmt.free();

        db.close();

        if (sessions.length === 0) {
            vscode.window.showInformationMessage('No sessions found in database');
            return;
        }

        const sessionItems = sessions.map(s => ({
            label: `${s.target} (${s.status})`,
            description: `Session: ${s.session_id.substring(0, 8)}... | ${new Date(s.start_time).toLocaleString()}`,
            sessionId: s.session_id
        }));

        const selected = await vscode.window.showQuickPick(sessionItems, {
            placeHolder: 'Select session to view'
        });

        if (selected) {
            await viewSessionResults(selected.sessionId);
        }
    } catch (error: any) {
        db.close();
        vscode.window.showErrorMessage(`Failed to list sessions: ${error.message}`);
    }
}

class ReconResultsProvider implements vscode.TreeDataProvider<SessionItem | ToolResultItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<SessionItem | ToolResultItem | undefined | null | void> = new vscode.EventEmitter<SessionItem | ToolResultItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<SessionItem | ToolResultItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private context: vscode.ExtensionContext) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: SessionItem | ToolResultItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: SessionItem | ToolResultItem): Thenable<SessionItem[] | ToolResultItem[]> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return Promise.resolve([]);
        }

        const dbPath = getDatabasePath(workspaceFolder);
        if (!dbPath) {
            return Promise.resolve([]);
        }

        const db = getDatabase(dbPath);
        if (!db) {
            return Promise.resolve([]);
        }

        try {
            if (!element) {
                // Root level - show sessions
                const sessionsStmt = db.prepare(`
                    SELECT s.*, t.target, t.target_type
                    FROM sessions s
                    JOIN targets t ON s.target_id = t.id
                    ORDER BY s.start_time DESC
                    LIMIT 50
                `);
                
                const sessions: any[] = [];
                while (sessionsStmt.step()) {
                    const row = sessionsStmt.getAsObject();
                    sessions.push({
                        session_id: row.session_id,
                        target_id: row.target_id,
                        status: row.status,
                        start_time: row.start_time,
                        end_time: row.end_time,
                        tools_executed: row.tools_executed,
                        target: row.target,
                        target_type: row.target_type
                    });
                }
                sessionsStmt.free();

                const sessionItems = sessions.map(s => {
                    const startTime = new Date(s.start_time);
                    return new SessionItem(
                        `${s.target} (${s.status})`,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        s.session_id,
                        s.target,
                        s.status,
                        startTime
                    );
                });

                db.close();
                return Promise.resolve(sessionItems);
            } else if (element instanceof SessionItem) {
                // Show tool results for this session
                const toolResultsStmt = db.prepare(`
                    SELECT tool_name, success, timestamp
                    FROM tool_results
                    WHERE session_id = ?
                    ORDER BY timestamp
                `);
                toolResultsStmt.bind([element.sessionId]);
                
                const toolResults: any[] = [];
                while (toolResultsStmt.step()) {
                    const row = toolResultsStmt.getAsObject();
                    toolResults.push({
                        tool_name: row.tool_name,
                        success: row.success,
                        timestamp: row.timestamp
                    });
                }
                toolResultsStmt.free();

                const aiAnalysisStmt = db.prepare(`
                    SELECT session_id
                    FROM ai_analysis
                    WHERE session_id = ?
                `);
                aiAnalysisStmt.bind([element.sessionId]);
                const aiAnalysisRows: any[] = [];
                while (aiAnalysisStmt.step()) {
                    aiAnalysisRows.push(aiAnalysisStmt.getAsObject());
                }
                aiAnalysisStmt.free();

                const items: ToolResultItem[] = [];

                // Add tool results
                for (const tr of toolResults) {
                    items.push(new ToolResultItem(
                        tr.tool_name,
                        vscode.TreeItemCollapsibleState.None,
                        element.sessionId,
                        tr.tool_name,
                        tr.success === 1
                    ));
                }

                // Add AI analysis if available
                if (aiAnalysisRows.length > 0) {
                    items.push(new ToolResultItem(
                        'AI Analysis',
                        vscode.TreeItemCollapsibleState.None,
                        element.sessionId,
                        'ai_analysis',
                        true
                    ));
                }

                db.close();
                return Promise.resolve(items);
            }

            db.close();
            return Promise.resolve([]);
        } catch (error) {
            db.close();
            console.error('Error loading tree data:', error);
            return Promise.resolve([]);
        }
    }
}

class SessionItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly sessionId: string,
        public readonly target: string,
        public readonly status: string,
        public readonly startTime: Date
    ) {
        super(label, collapsibleState);
        this.tooltip = `Target: ${target}\nStatus: ${status}\nStart Time: ${startTime.toLocaleString()}\nSession ID: ${sessionId}`;
        this.contextValue = 'session';
        this.iconPath = new vscode.ThemeIcon(status === 'completed' ? 'check' : status === 'running' ? 'sync~spin' : 'error');
        // Allow clicking on session items to view results
        this.command = {
            command: 'recon-again.viewResults',
            title: 'View Session Results',
            arguments: [{ sessionId: this.sessionId }]
        };
    }
}

class ToolResultItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly sessionId: string,
        public readonly toolName: string,
        public readonly success: boolean
    ) {
        super(label, collapsibleState);
        this.tooltip = `Tool: ${toolName}\nStatus: ${success ? 'Success' : 'Failed'}`;
        this.contextValue = 'result';
        this.command = {
            command: 'recon-again.viewResults',
            title: 'View Result',
            arguments: [{ sessionId: this.sessionId }]
        };
        this.iconPath = new vscode.ThemeIcon(success ? 'check' : 'error');
    }
}

export function deactivate() {}
