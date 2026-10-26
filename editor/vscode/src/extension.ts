import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;

/** Walk up from `startDir` looking for a virtualenv's python. */
function findVenv(startDir: string): string | undefined {
  let dir = startDir;
  for (let depth = 0; depth < 6; depth++) {
    const candidates = [
      path.join(dir, ".venv", "Scripts", "python.exe"),
      path.join(dir, ".venv", "bin", "python"),
      path.join(dir, "venv", "Scripts", "python.exe"),
      path.join(dir, "venv", "bin", "python"),
    ];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) return candidate;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return undefined;
}

function resolvePython(context: vscode.ExtensionContext): string {
  const configured = vscode.workspace
    .getConfiguration("donky")
    .get<string>("pythonPath", "");
  if (configured && configured.trim() !== "") return configured;

  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    const found = findVenv(folder.uri.fsPath);
    if (found) return found;
  }
  const nearExtension = findVenv(context.extensionPath);
  if (nearExtension) return nearExtension;

  return "python";
}

function resolveServerScript(
  context: vscode.ExtensionContext
): string | undefined {
  const candidates = [
    // Dev mode: extension is at <repo>/editor/vscode, server at <repo>/editor/lsp
    path.join(context.extensionPath, "..", "lsp", "donky_lsp.py"),
    // Packaged: server copied into the extension under lsp/
    path.join(context.extensionPath, "lsp", "donky_lsp.py"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return path.resolve(candidate);
  }
  return undefined;
}

export function activate(context: vscode.ExtensionContext): void {
  const script = resolveServerScript(context);
  if (!script) {
    vscode.window.showErrorMessage(
      "Donky: cannot find donky_lsp.py. Looked in ../lsp and ./lsp relative to the extension."
    );
    return;
  }

  const python = resolvePython(context);
  const output = vscode.window.createOutputChannel("Donky Language Server");
  output.appendLine(`python:  ${python}`);
  output.appendLine(`server:  ${script}`);

  const serverOptions: ServerOptions = {
    run: { command: python, args: [script], transport: TransportKind.stdio },
    debug: { command: python, args: [script], transport: TransportKind.stdio },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "donky" }],
    outputChannel: output,
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.donk"),
    },
  };

  client = new LanguageClient(
    "donky",
    "Donky Language Server",
    serverOptions,
    clientOptions
  );

  client.start();
  context.subscriptions.push({ dispose: () => void client?.stop() });
}

export function deactivate(): Thenable<void> | undefined {
  return client?.stop();
}