"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const node_1 = require("vscode-languageclient/node");
let client;
/** Walk up from `startDir` looking for a virtualenv's python. */
function findVenv(startDir) {
    let dir = startDir;
    for (let depth = 0; depth < 6; depth++) {
        const candidates = [
            path.join(dir, ".venv", "Scripts", "python.exe"),
            path.join(dir, ".venv", "bin", "python"),
            path.join(dir, "venv", "Scripts", "python.exe"),
            path.join(dir, "venv", "bin", "python"),
        ];
        for (const candidate of candidates) {
            if (fs.existsSync(candidate))
                return candidate;
        }
        const parent = path.dirname(dir);
        if (parent === dir)
            break;
        dir = parent;
    }
    return undefined;
}
function resolvePython(context) {
    const configured = vscode.workspace
        .getConfiguration("donky")
        .get("pythonPath", "");
    if (configured && configured.trim() !== "")
        return configured;
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        const found = findVenv(folder.uri.fsPath);
        if (found)
            return found;
    }
    const nearExtension = findVenv(context.extensionPath);
    if (nearExtension)
        return nearExtension;
    return "python";
}
function resolveServerScript(context) {
    const candidates = [
        // Dev mode: extension is at <repo>/editor/vscode, server at <repo>/editor/lsp
        path.join(context.extensionPath, "..", "lsp", "donky_lsp.py"),
        // Packaged: server copied into the extension under lsp/
        path.join(context.extensionPath, "lsp", "donky_lsp.py"),
    ];
    for (const candidate of candidates) {
        if (fs.existsSync(candidate))
            return path.resolve(candidate);
    }
    return undefined;
}
function activate(context) {
    const script = resolveServerScript(context);
    if (!script) {
        vscode.window.showErrorMessage("Donky: cannot find donky_lsp.py. Looked in ../lsp and ./lsp relative to the extension.");
        return;
    }
    const python = resolvePython(context);
    const output = vscode.window.createOutputChannel("Donky Language Server");
    output.appendLine(`python:  ${python}`);
    output.appendLine(`server:  ${script}`);
    const serverOptions = {
        run: { command: python, args: [script], transport: node_1.TransportKind.stdio },
        debug: { command: python, args: [script], transport: node_1.TransportKind.stdio },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "donky" }],
        outputChannel: output,
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher("**/*.donk"),
        },
    };
    client = new node_1.LanguageClient("donky", "Donky Language Server", serverOptions, clientOptions);
    client.start();
    context.subscriptions.push({ dispose: () => void client?.stop() });
}
function deactivate() {
    return client?.stop();
}
//# sourceMappingURL=extension.js.map