/**
 * recon-again VSCode Extension
 * Provides UI for running reconnaissance and viewing results
 */

import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs';

const execAsync = promisify(exec);

interface ReconResult {
    session_id: string;
    target: string;
    status: string;
    results: any;
    start_time: string;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('recon-again extension is now active!');

    // Register commands
    const runReconCommand = vscode.commands.registerCommand('recon-again.runRecon', async () => {
        await runReconnaissance();
    });

    const listToolsCommand = vscode.commands.registerCommand('recon-again.listTools', async () => {
        await listTools();
    });

    const viewResultsCommand = vscode.commands.registerCommand('recon-again.viewResults', async (item?: any) => {
        if (item && item.resourceUri) {
            await viewResultFile(item.resourceUri.fsPath);
        } else {
            await selectAndViewResult();
        }
    });

    const runToolCommand = vscode.commands.registerCommand('recon-again.runTool', async () => {
        await runSpecificTool();
    });

    context.subscriptions.push(runReconCommand, listToolsCommand, viewResultsCommand, runToolCommand);

    // Register results tree view
    const resultsProvider = new ReconResultsProvider(context);
    vscode.window.createTreeView('recon-again-results', {
        treeDataProvider: resultsProvider
    });

    // Watch for new result files
    const resultsDir = path.join(context.workspaceState.get('workspaceFolder', ''), 'results');
    if (fs.existsSync(resultsDir)) {
        const watcher = vscode.workspace.createFileSystemWatcher(
            new vscode.RelativePattern(resultsDir, '*.json')
        );
        watcher.onDidCreate(() => resultsProvider.refresh());
        watcher.onDidChange(() => resultsProvider.refresh());
        context.subscriptions.push(watcher);
    }
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

    try {
        const { stdout, stderr } = await execAsync(`recon-again ${args.join(' ')}`, {
            cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
            timeout: 3600000 // 1 hour timeout
        });

        outputChannel.append(stdout);
        if (stderr) {
            outputChannel.append(stderr);
        }

        vscode.window.showInformationMessage(`Reconnaissance completed for ${target}`);
    } catch (error: any) {
        outputChannel.appendLine(`Error: ${error.message}`);
        vscode.window.showErrorMessage(`Reconnaissance failed: ${error.message}`);
    }
}

async function listTools() {
    try {
        const { stdout } = await execAsync('recon-again --list-tools', {
            cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
        });

        const outputChannel = vscode.window.createOutputChannel('recon-again Tools');
        outputChannel.show();
        outputChannel.append(stdout);
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to list tools: ${error.message}`);
    }
}

async function runSpecificTool() {
    // First get list of tools
    try {
        const { stdout } = await execAsync('recon-again --list-tools', {
            cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
        });

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
            ['crt_sh', 'urlscan', 'hibp', 'sublist3r', 'dnsrecon', 'dirsearch', 'wayback', 'sherlock'],
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
            const { stdout: toolOutput } = await execAsync(`recon-again ${target} -t ${tools}`, {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                timeout: 3600000
            });

            outputChannel.append(toolOutput);
            vscode.window.showInformationMessage(`Tool ${tools} completed`);
        } catch (error: any) {
            outputChannel.appendLine(`Error: ${error.message}`);
            vscode.window.showErrorMessage(`Tool execution failed: ${error.message}`);
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to get tool list: ${error.message}`);
    }
}

async function viewResultFile(filePath: string) {
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const result: ReconResult = JSON.parse(content);

        const doc = await vscode.workspace.openTextDocument(
            vscode.Uri.file(filePath)
        );
        await vscode.window.showTextDocument(doc);

        // Show summary in output
        const outputChannel = vscode.window.createOutputChannel('recon-again Results');
        outputChannel.show();
        outputChannel.appendLine(`Target: ${result.target}`);
        outputChannel.appendLine(`Session ID: ${result.session_id}`);
        outputChannel.appendLine(`Status: ${result.status}`);
        outputChannel.appendLine('');

        for (const [tool, toolResult] of Object.entries(result.results)) {
            if (tool === 'ai_analysis') {
                outputChannel.appendLine('🤖 AI Analysis:');
            } else {
                outputChannel.appendLine(`🔧 ${tool}:`);
            }
            outputChannel.appendLine(JSON.stringify(toolResult, null, 2));
            outputChannel.appendLine('');
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to view result: ${error.message}`);
    }
}

async function selectAndViewResult() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const resultsDir = path.join(workspaceFolder.uri.fsPath, 'results');
    if (!fs.existsSync(resultsDir)) {
        vscode.window.showWarningMessage('No results directory found');
        return;
    }

    const files = fs.readdirSync(resultsDir)
        .filter(f => f.endsWith('.json'))
        .map(f => ({
            label: f,
            description: path.join(resultsDir, f)
        }));

    if (files.length === 0) {
        vscode.window.showInformationMessage('No result files found');
        return;
    }

    const selected = await vscode.window.showQuickPick(files, {
        placeHolder: 'Select result file to view'
    });

    if (selected) {
        await viewResultFile(selected.description!);
    }
}

class ReconResultsProvider implements vscode.TreeDataProvider<ResultItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ResultItem | undefined | null | void> = new vscode.EventEmitter<ResultItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<ResultItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private context: vscode.ExtensionContext) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: ResultItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ResultItem): Thenable<ResultItem[]> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return Promise.resolve([]);
        }

        const resultsDir = path.join(workspaceFolder.uri.fsPath, 'results');
        if (!fs.existsSync(resultsDir)) {
            return Promise.resolve([]);
        }

        if (!element) {
            // Root level - show result files
            const files = fs.readdirSync(resultsDir)
                .filter(f => f.endsWith('.json'))
                .map(f => {
                    const filePath = path.join(resultsDir, f);
                    const stat = fs.statSync(filePath);
                    return new ResultItem(
                        f,
                        vscode.TreeItemCollapsibleState.None,
                        vscode.Uri.file(filePath),
                        stat.mtime
                    );
                });

            return Promise.resolve(files.sort((a, b) => b.modified.getTime() - a.modified.getTime()));
        }

        return Promise.resolve([]);
    }
}

class ResultItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly resourceUri: vscode.Uri,
        public readonly modified: Date
    ) {
        super(label, collapsibleState);
        this.tooltip = `Modified: ${modified.toLocaleString()}`;
        this.command = {
            command: 'recon-again.viewResults',
            title: 'View Result',
            arguments: [this]
        };
    }

    iconPath = new vscode.ThemeIcon('file-code');
}

export function deactivate() {}

